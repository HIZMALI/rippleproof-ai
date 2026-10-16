"""Pure deterministic material simulation. No database access or fixture imports."""

import hashlib
import json
from collections import defaultdict
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext

from rippleproof.models import strict_iso_date
from rippleproof.simulation.models import (
    Allocation,
    ArrivalCertificateCheck,
    CandidateEvaluation,
    DataIssue,
    GraphSnapshot,
    LotBalance,
    MaterialResult,
    MitigationPlanSummary,
    OfferFact,
    OrderResult,
    PendingReceipt,
    PlanResult,
    Receipt,
    ScenarioRequest,
    ScenarioResponse,
)
from rippleproof.simulation.snapshot import dependencies, sorted_orders

ENGINE_VERSION = "phase2-materials-v1"
ASSUMPTIONS = [
    "Materials-only on-time feasibility: complete BOM available by the customer deadline. "
    "Production duration, factory capacity, weekends and transport costs are not scheduled.",
    "Orders sort by earliest deadline, higher numeric priority, then lexical order ID. "
    "Allocation is all-or-nothing; failed orders reserve no inventory.",
    "Stock is available as of the request date. Receipts are consumed oldest-arrival first "
    "and only if arrival is on or before the order deadline; quantities are globally conserved.",
    "A PLANNED dispatch in [outage_start, outage_end_exclusive) moves to the exclusive end, "
    "preserving its documented transit interval. DISPATCHED and CANCELLED facts are not shifted.",
    "Existing booked receipts are committed facts. Outage backlog dispatch smoothing and "
    "revalidation of historical procurement certificates are not modeled.",
    "New proposals start no earlier than as_of, use per-part shipping capacity after booked "
    "dispatches, and arrive dispatch + lead_days. All required certificates must cover arrival.",
    "The provided inbound schedule is treated as exhaustive only for parts with shipment "
    "records or an explicit inbound_schedule_complete flag. Missing vital facts are unresolved.",
    "Mitigation is a bounded greedy heuristic, not a proven global optimum. Compare mixed "
    "cost-first, mixed lead-first and single-supplier policies. Maximize restored newly-at-risk "
    "orders, minimize unused new units, then gross additional cost, then stable supplier IDs. "
    "Plans cannot make an already on-time disrupted order worse.",
    "The additional-procurement search horizon is capped at 366 calendar days from as_of.",
    "Gross additional procurement cost is new proposed quantity times graph unit cost, "
    "rounded per shipment to 2 decimals with ROUND_HALF_UP. Cancellation fees, sunk commitments, "
    "labor, taxes and transport are excluded. Proposals are not persisted or placed.",
    "A comparison may indirectly change unrelated order allocation through shared stock. "
    "Direct dependency paths and newly-at-risk status are reported separately.",
]


def money(quantity: int, unit_cost: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 50
        return (quantity * unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def total_cost(receipts: list[Receipt]) -> Decimal:
    with localcontext() as context:
        context.prec = 50
        return sum((r.estimated_additional_procurement_cost for r in receipts), Decimal("0.00"))


def timeline(snapshot: GraphSnapshot, request: ScenarioRequest, disrupted: bool):
    receipts, events, issues = [], [], []
    for part in snapshot.parts.values():
        if part.stock_on_hand is not None:
            receipts.append(
                Receipt(
                    id=f"STOCK:{part.id}",
                    part_id=part.id,
                    quantity=part.stock_on_hand,
                    arrival_date=request.as_of,
                    kind="initial_stock",
                    evidence_refs=[part.id],
                )
            )
    for shipment in sorted(snapshot.shipments, key=lambda s: s.id):
        dispatch = shipment.dispatch_date
        arrival = shipment.expected_arrival_date
        reasons = []
        included = shipment.status != "CANCELLED"
        if not included:
            reasons.append("CANCELLED")
        elif (
            arrival < request.as_of
            or (shipment.status == "PLANNED" and dispatch < request.as_of)
            or (shipment.status == "DISPATCHED" and dispatch > request.as_of)
        ):
            included = False
            reasons.append("INCONSISTENT_AS_OF_SHIPMENT")
            issues.append(
                DataIssue(
                    entity_id=shipment.part_id,
                    code="INCONSISTENT_AS_OF_SHIPMENT",
                    detail=shipment.id,
                )
            )
        elif shipment.status == "DISPATCHED":
            reasons.append("ALREADY_DISPATCHED")
        elif (
            disrupted
            and shipment.supplier_id == request.supplier_id
            and request.outage_start <= dispatch < request.outage_end_exclusive
        ):
            transit = arrival - dispatch
            dispatch = request.outage_end_exclusive
            try:
                arrival = dispatch + transit
                reasons.append("OUTAGE_DELAYED")
            except OverflowError:
                included = False
                reasons.append("OUTAGE_TIMING_UNRESOLVED")
                issues.append(
                    DataIssue(
                        entity_id=shipment.part_id,
                        code="OUTAGE_TIMING_UNRESOLVED",
                        detail=shipment.id,
                    )
                )
        else:
            reasons.append("PLANNED_UNCHANGED")
        events.append(
            {
                "shipment_id": shipment.id,
                "supplier_id": shipment.supplier_id,
                "part_id": shipment.part_id,
                "quantity": shipment.quantity,
                "status": shipment.status,
                "original_dispatch_date": shipment.dispatch_date.isoformat(),
                "original_arrival_date": shipment.expected_arrival_date.isoformat(),
                "dispatch_date": dispatch.isoformat(),
                "arrival_date": arrival.isoformat(),
                "included": included,
                "reason_code": reasons[0],
            }
        )
        if included:
            receipts.append(
                Receipt(
                    id=shipment.id,
                    supplier_id=shipment.supplier_id,
                    part_id=shipment.part_id,
                    quantity=shipment.quantity,
                    dispatch_date=dispatch,
                    arrival_date=arrival,
                    original_arrival_date=shipment.expected_arrival_date,
                    kind="planned",
                    reason_codes=reasons,
                    evidence_refs=shipment.evidence_refs,
                )
            )
    return receipts, events, issues


def allocate(
    snapshot: GraphSnapshot,
    request: ScenarioRequest,
    receipts: list[Receipt],
    name: str,
    context_issues: list[DataIssue] | None = None,
) -> PlanResult:
    ordered = sorted(receipts, key=lambda r: (r.arrival_date, r.id))
    receipt_kinds = {r.id: r.kind for r in ordered}
    remaining = {r.id: r.quantity for r in ordered}
    by_part = defaultdict(list)
    for receipt in ordered:
        by_part[receipt.part_id].append(receipt)
    contextual_bad_parts = {i.entity_id for i in context_issues or []}
    results = []
    for order in sorted_orders(snapshot):
        invalid = bool(order.issues or not order.parts or snapshot.global_supply_unknown)
        overdue = order.deadline is not None and order.deadline < request.as_of
        materials = []
        for demand in order.parts:
            part = snapshot.parts.get(demand.part_id)
            unknown = (
                part is None
                or part.stock_on_hand is None
                or bool(part.issues)
                or demand.part_id in contextual_bad_parts
            )
            invalid = invalid or unknown
            available = (
                None
                if unknown or order.deadline is None
                else sum(
                    remaining[r.id]
                    for r in by_part[demand.part_id]
                    if r.arrival_date <= order.deadline
                )
            )
            shortfall = None if available is None else max(demand.quantity - available, 0)
            reasons = []
            if unknown:
                reasons.append("INSUFFICIENT_DATA")
            elif shortfall:
                reasons.append("MATERIAL_SHORTFALL")
                if any(
                    r.arrival_date > order.deadline and remaining[r.id] > 0
                    for r in by_part[demand.part_id]
                ):
                    reasons.append("RECEIPT_AFTER_DEADLINE")
            materials.append(
                MaterialResult(
                    part_id=demand.part_id,
                    required_quantity=demand.quantity,
                    available_by_deadline=available,
                    allocated_quantity=0,
                    shortfall_quantity=shortfall,
                    allocations=[],
                    late_receipts=[
                        PendingReceipt(
                            receipt_id=r.id,
                            quantity=remaining[r.id],
                            arrival_date=r.arrival_date,
                            evidence_refs=r.evidence_refs,
                        )
                        for r in by_part[demand.part_id]
                        if order.deadline is not None
                        and r.arrival_date > order.deadline
                        and remaining[r.id] > 0
                    ],
                    reason_codes=reasons,
                )
            )
        feasible = (
            not invalid
            and not overdue
            and order.deadline is not None
            and all(m.shortfall_quantity == 0 for m in materials)
        )
        if feasible:
            for material in materials:
                needed = material.required_quantity
                for receipt in by_part[material.part_id]:
                    if receipt.arrival_date > order.deadline:
                        continue
                    quantity = min(needed, remaining[receipt.id])
                    if quantity:
                        remaining[receipt.id] -= quantity
                        needed -= quantity
                        material.allocations.append(
                            Allocation(
                                receipt_id=receipt.id,
                                quantity=quantity,
                                arrival_date=receipt.arrival_date,
                                evidence_refs=receipt.evidence_refs,
                            )
                        )
                    if needed == 0:
                        break
                material.allocated_quantity = material.required_quantity
            reason = (
                "ON_TIME_WITH_RECEIPTS"
                if any(
                    receipt_kinds[a.receipt_id] != "initial_stock"
                    for m in materials
                    for a in m.allocations
                )
                else "ON_TIME_USING_STOCK"
            )
        else:
            reason = (
                "INSUFFICIENT_DATA"
                if invalid
                else "DEADLINE_BEFORE_AS_OF"
                if overdue
                else "MATERIAL_SHORTFALL"
            )
        arrivals = [a.arrival_date for m in materials for a in m.allocations]
        results.append(
            OrderResult(
                order_id=order.order_id,
                deadline=order.deadline,
                priority=order.priority,
                status="on_time" if feasible else "insufficient_data" if invalid else "at_risk",
                materials=materials,
                latest_arriving_input=max(arrivals) if arrivals else None,
                reason_codes=[reason],
            )
        )
    return PlanResult(
        name=name,
        orders=results,
        receipts=ordered,
        on_time_orders=sorted(o.order_id for o in results if o.status == "on_time"),
        at_risk_orders=sorted(o.order_id for o in results if o.status == "at_risk"),
        unresolved_orders=sorted(o.order_id for o in results if o.status == "insufficient_data"),
        ledger=[
            LotBalance(
                receipt_id=r.id,
                part_id=r.part_id,
                arrival_date=r.arrival_date,
                received_quantity=r.quantity,
                allocated_quantity=r.quantity - remaining[r.id],
                remaining_quantity=remaining[r.id],
            )
            for r in ordered
        ],
        estimated_additional_procurement_cost=total_cost(ordered),
    )


def certificate_checks(snapshot: GraphSnapshot, offer: OfferFact, arrival):
    part = snapshot.parts[offer.part_id]
    checks = []
    for ref in part.requirement_edges:
        requirement = snapshot.relationships[ref]
        holdings = [
            r
            for r in snapshot.relationships.values()
            if r.type == "HOLDS_CERT"
            and r.source_id == offer.supplier_id
            and r.target_id == requirement.target_id
        ]
        expiry, holding_ref, status = None, None, "missing"
        if holdings:
            holding_ref = holdings[0].id
            try:
                if len(holdings) != 1:
                    raise ValueError("Ambiguous certificate holdings")
                expiry = strict_iso_date(holdings[0].properties.get("valid_until"))
                status = "valid" if expiry >= arrival else "expired"
            except (TypeError, ValueError):
                status = "unknown"
        checks.append(
            ArrivalCertificateCheck(
                certificate_id=requirement.target_id,
                arrival_date=arrival,
                status=status,
                valid_until=expiry,
                requirement_ref=ref,
                holding_ref=holding_ref,
            )
        )
    return checks


def bookings(receipts: list[Receipt]):
    result = defaultdict(int)
    for receipt in receipts:
        if receipt.supplier_id and receipt.dispatch_date:
            result[receipt.supplier_id, receipt.part_id, receipt.dispatch_date] += receipt.quantity
    return result


def eligible_offer(snapshot: GraphSnapshot, request: ScenarioRequest, offer: OfferFact):
    supplier = snapshot.nodes.get(offer.supplier_id)
    part = snapshot.parts.get(offer.part_id)
    if (
        offer.issues
        or not part
        or part.issues
        or supplier is None
        or supplier.properties.get("status") is None
    ):
        return ["INSUFFICIENT_DATA"]
    if supplier.properties["status"] != "active":
        return ["SUPPLIER_NOT_ACTIVE"]
    if offer.supplier_id == request.supplier_id:
        return ["DISRUPTED_SUPPLIER_EXCLUDED"]
    if offer.is_primary is not False:
        return ["NOT_AN_ALTERNATIVE_OFFER"]
    if offer.daily_capacity == 0:
        return ["ZERO_DAILY_CAPACITY"]
    return []


def evaluate_candidates(snapshot, request, receipts, relevant_parts):
    booked = bookings(receipts)
    deadlines = [o.deadline for o in snapshot.orders if o.deadline is not None]
    horizon = min(max(deadlines, default=request.as_of), request.as_of + timedelta(days=366))
    evaluations = []
    for offer in sorted(snapshot.offers, key=lambda o: (o.part_id, o.supplier_id)):
        if offer.part_id not in relevant_parts or offer.is_primary is not False:
            continue
        reasons = eligible_offer(snapshot, request, offer)
        first_dispatch = first_arrival = None
        checks = []
        if not reasons:
            too_late = offer.lead_days > (horizon - request.as_of).days
            last_dispatch = request.as_of if too_late else horizon - timedelta(days=offer.lead_days)
            day = request.as_of
            while not too_late and day <= last_dispatch:
                if booked[offer.supplier_id, offer.part_id, day] < offer.daily_capacity:
                    first_dispatch, first_arrival = day, day + timedelta(days=offer.lead_days)
                    break
                day += timedelta(days=1)
            if first_dispatch is None:
                reasons.append(
                    "LEAD_TIME_MISSES_DEADLINE" if too_late else "NO_CAPACITY_BEFORE_DEADLINE"
                )
            else:
                checks = certificate_checks(snapshot, offer, first_arrival)
                reasons += sorted(
                    {
                        {
                            "missing": "MISSING_REQUIRED_CERTIFICATE",
                            "expired": "CERTIFICATE_EXPIRED_AT_ARRIVAL",
                            "unknown": "INSUFFICIENT_DATA",
                        }[c.status]
                        for c in checks
                        if c.status != "valid"
                    }
                )
        evaluations.append(
            CandidateEvaluation(
                supplier_id=offer.supplier_id,
                part_id=offer.part_id,
                offer_ref=offer.id,
                status="insufficient_data"
                if "INSUFFICIENT_DATA" in reasons
                else "rejected"
                if reasons
                else "eligible",
                unit_cost=offer.unit_cost,
                lead_days=offer.lead_days,
                daily_capacity=offer.daily_capacity,
                earliest_dispatch_date=first_dispatch,
                earliest_arrival_date=first_arrival,
                booked_dispatches=[
                    {
                        "shipment_id": r.id,
                        "quantity": r.quantity,
                        "dispatch_date": r.dispatch_date.isoformat(),
                    }
                    for r in receipts
                    if r.supplier_id == offer.supplier_id
                    and r.part_id == offer.part_id
                    and r.dispatch_date
                ],
                certificate_checks=checks,
                reason_codes=reasons or ["ELIGIBLE_AT_EARLIEST_ARRIVAL"],
            )
        )
    return evaluations


def propose(snapshot, request, receipts, failed_order, policy, proposal_prefix):
    booked = bookings(receipts)
    proposals = []
    for material in failed_order.materials:
        needed = material.shortfall_quantity
        if needed is None:
            return None
        if needed <= 0:
            continue
        offers = [
            o
            for o in snapshot.offers
            if o.part_id == material.part_id
            and not eligible_offer(snapshot, request, o)
            and (not policy.startswith("supplier:") or o.supplier_id == policy.split(":")[1])
        ]
        if policy == "lead_first":
            offers.sort(key=lambda o: (o.lead_days, o.unit_cost, o.supplier_id))
        else:
            offers.sort(key=lambda o: (o.unit_cost, o.lead_days, o.supplier_id))
        for offer in offers:
            horizon = min(failed_order.deadline, request.as_of + timedelta(days=366))
            if offer.lead_days > (horizon - request.as_of).days:
                continue
            last = horizon - timedelta(days=offer.lead_days)
            day = request.as_of
            while day <= last and needed:
                arrival = day + timedelta(days=offer.lead_days)
                checks = certificate_checks(snapshot, offer, arrival)
                if any(check.status != "valid" for check in checks):
                    # Expiry can only get worse at later arrival dates.
                    break
                available = max(
                    offer.daily_capacity - booked[offer.supplier_id, offer.part_id, day], 0
                )
                quantity = min(needed, available)
                if quantity:
                    identity = f"PROPOSED:{proposal_prefix}:{len(proposals) + 1}"
                    proposals.append(
                        Receipt(
                            id=identity,
                            supplier_id=offer.supplier_id,
                            part_id=offer.part_id,
                            quantity=quantity,
                            dispatch_date=day,
                            arrival_date=arrival,
                            kind="proposed",
                            evidence_refs=[offer.id]
                            + [c.requirement_ref for c in checks]
                            + [c.holding_ref for c in checks if c.holding_ref],
                            unit_cost=offer.unit_cost,
                            estimated_additional_procurement_cost=money(quantity, offer.unit_cost),
                            certificate_checks=checks,
                            reason_codes=["OPTIONAL_ADDITIONAL_PROCUREMENT"],
                        )
                    )
                    booked[offer.supplier_id, offer.part_id, day] += quantity
                    needed -= quantity
                day += timedelta(days=1)
            if not needed:
                break
        if needed:
            return None  # Atomic order attempt: discard every provisional part/day.
    return proposals


def mitigate(snapshot, request, receipts, disrupted, newly, issues, scenario_id, policy_id=None):
    suppliers = sorted({o.supplier_id for o in snapshot.offers if o.is_primary is False})
    policies = ["cost_first", "lead_first"] + [f"supplier:{s}" for s in suppliers]
    trials = [("no_procurement", disrupted.model_copy(update={"name": "mitigated"}), [])]
    protected = set(disrupted.on_time_orders)
    for policy in policies:
        proposals = []
        current = allocate(snapshot, request, receipts, "mitigated", issues)
        for demand in sorted_orders(snapshot):
            if demand.order_id not in newly:
                continue
            failed = next(o for o in current.orders if o.order_id == demand.order_id)
            if failed.status != "at_risk":
                continue
            additions = propose(
                snapshot,
                request,
                receipts + proposals,
                failed,
                policy,
                f"{scenario_id}:{policy}:{demand.order_id}",
            )
            if not additions:
                continue
            trial = allocate(
                snapshot, request, receipts + proposals + additions, "mitigated", issues
            )
            restored_before = newly & set(current.on_time_orders)
            restored_after = newly & set(trial.on_time_orders)
            if protected <= set(trial.on_time_orders) and restored_before < restored_after:
                proposals += additions
                current = trial
        # Remove new units the exact final allocator did not reserve. This is
        # not extra inventory and cannot exceed any original capacity booking.
        used = {lot.receipt_id: lot.allocated_quantity for lot in current.ledger}
        proposals = [
            p.model_copy(
                update={
                    "quantity": used[p.id],
                    "estimated_additional_procurement_cost": money(used[p.id], p.unit_cost),
                }
            )
            for p in proposals
            if used[p.id] > 0
        ]
        current = allocate(snapshot, request, receipts + proposals, "mitigated", issues)
        trials.append((policy, current, proposals))

    def rank(trial):
        policy, plan, proposals = trial
        used = {lot.receipt_id: lot.allocated_quantity for lot in plan.ledger}
        unused = sum(p.quantity - used[p.id] for p in proposals)
        return (
            -len(newly & set(plan.on_time_orders)),
            unused,
            plan.estimated_additional_procurement_cost,
            tuple(sorted({p.supplier_id for p in proposals})),
            policy,
        )

    trials.sort(key=rank)
    if policy_id is not None:
        matching = [t for t in trials if t[0] == policy_id]
        if not matching:
            raise ValueError("Unknown mitigation policy")
        trials = matching + [t for t in trials if t[0] != policy_id]
    selected_policy, selected_plan, selected_shipments = trials[0]
    summaries = [
        MitigationPlanSummary(
            id=policy,
            restored_orders=sorted(newly & set(plan.on_time_orders)),
            additional_units=sum(p.quantity for p in proposals),
            unused_additional_units=rank((policy, plan, proposals))[1],
            estimated_additional_procurement_cost=plan.estimated_additional_procurement_cost,
            selected=policy == selected_policy,
            reason_codes=[
                "NO_FEASIBLE_ATOMIC_RECOVERY"
                if not proposals and newly
                else "GREEDY_HEURISTIC_EVALUATED"
            ],
        )
        for policy, plan, proposals in trials
    ]
    return selected_plan, selected_shipments, summaries


def scenario_identity(fingerprint: str, request: ScenarioRequest) -> str:
    return (
        "SC-"
        + hashlib.sha256(
            (
                ENGINE_VERSION
                + fingerprint
                + json.dumps(request.model_dump(mode="json"), sort_keys=True)
            ).encode()
        ).hexdigest()[:20]
    )


def simulate(
    snapshot: GraphSnapshot, request: ScenarioRequest, *, policy_id: str | None = None
) -> ScenarioResponse:
    baseline_receipts, _, baseline_issues = timeline(snapshot, request, False)
    disrupted_receipts, events, disrupted_issues = timeline(snapshot, request, True)
    issues = list(
        {
            (i.entity_id, i.code, i.detail): i
            for i in snapshot.issues + baseline_issues + disrupted_issues
        }.values()
    )
    baseline = allocate(snapshot, request, baseline_receipts, "baseline", baseline_issues)
    disrupted = allocate(snapshot, request, disrupted_receipts, "disrupted", disrupted_issues)
    newly = set(disrupted.at_risk_orders) - set(baseline.at_risk_orders)
    paths = dependencies(snapshot, request.supplier_id)
    scenario_id = scenario_identity(snapshot.fingerprint, request)
    affected_parts = {o.part_id for o in snapshot.offers if o.supplier_id == request.supplier_id}
    affected_parts.update(
        p.part_id for o in snapshot.orders if o.order_id in newly for p in o.parts
    )
    candidates = evaluate_candidates(snapshot, request, disrupted_receipts, affected_parts)
    mitigated, proposals, plans = None, [], []
    if request.include_mitigation:
        mitigated, proposals, plans = mitigate(
            snapshot,
            request,
            disrupted_receipts,
            disrupted,
            newly,
            disrupted_issues,
            scenario_id,
            policy_id,
        )
    return ScenarioResponse(
        scenario_id=scenario_id,
        snapshot_fingerprint=snapshot.fingerprint,
        request=request,
        assumptions=ASSUMPTIONS,
        shipment_timing=events,
        incomplete_data=bool(
            issues
            or baseline.unresolved_orders
            or disrupted.unresolved_orders
            or any(c.status == "insufficient_data" for c in candidates)
        ),
        data_issues=sorted(issues, key=lambda i: (i.entity_id, i.code, i.detail)),
        dependent_orders=sorted({p.nodes[-1].id for p in paths}),
        dependency_paths=paths,
        order_demands=sorted_orders(snapshot),
        baseline=baseline,
        disrupted=disrupted,
        mitigated=mitigated,
        baseline_at_risk_orders=baseline.at_risk_orders,
        disrupted_at_risk_orders=disrupted.at_risk_orders,
        newly_at_risk_orders=sorted(newly),
        restored_orders=sorted(newly & set(mitigated.on_time_orders)) if mitigated else [],
        candidate_evaluations=candidates,
        mitigation_plans=plans,
        proposed_shipments=proposals,
        estimated_additional_procurement_cost=mitigated.estimated_additional_procurement_cost
        if mitigated
        else Decimal("0.00"),
        evidence_nodes=snapshot.nodes,
        evidence_relationships=snapshot.relationships,
    )
