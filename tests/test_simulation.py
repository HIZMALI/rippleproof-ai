from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from rippleproof.app import create_app
from rippleproof.config import Settings
from rippleproof.simulation.engine import simulate
from tests.simulation_helpers import GraphBuilder, request


def run(graph, **overrides):
    return simulate(graph.snapshot(), request(**overrides))


def test_shared_stock_and_failed_order_rollback():
    graph = GraphBuilder(stock=10).order("O-02", quantity=6).order("O-01", quantity=6)
    result = run(graph, include_mitigation=False)
    assert result.baseline.on_time_orders == ["O-01"]
    assert result.baseline.at_risk_orders == ["O-02"]
    first, second = result.baseline.orders
    assert first.materials[0].allocated_quantity == 6
    assert second.materials[0].available_by_deadline == 4
    assert second.materials[0].allocated_quantity == 0
    assert second.materials[0].shortfall_quantity == 2
    assert result.baseline.ledger[0].remaining_quantity == 4


def test_failed_complete_bom_does_not_reserve_other_parts():
    graph = GraphBuilder(stock=5).order("O-01", quantity=5)
    graph.node(
        "Part", "P-01", stock_on_hand=0, inbound_schedule_complete=True, certification_policy="none"
    )
    graph.edge("USES", "PR-01", "P-01", units_per_product=1)
    graph.order("O-02", quantity=5, product="PR-02")
    result = run(graph, include_mitigation=False)
    assert result.baseline.on_time_orders == ["O-02"]
    assert not any(m.allocations for m in result.baseline.orders[0].materials)


def test_stable_deadline_priority_and_identity_ordering():
    graph = GraphBuilder(stock=3).order("O-03", quantity=1, priority=1)
    graph.order("O-02", quantity=1, priority=3).order("O-01", quantity=1, priority=3)
    first = run(graph)
    assert [o.order_id for o in first.baseline.orders] == ["O-01", "O-02", "O-03"]
    assert first.model_dump_json() == run(graph).model_dump_json()


def test_repeated_parts_are_summed_with_individual_bom_evidence():
    graph = GraphBuilder(stock=100).order(quantity=8, units=4)
    graph.node("Product", "PR-02", production_days=2)
    graph.edge("CONTAINS", "O-01", "PR-02", quantity=3)
    graph.edge("USES", "PR-02", "P-22", units_per_product=2)
    demand = run(graph).order_demands[0].parts[0]
    assert demand.quantity == 38
    assert [line.quantity for line in demand.lines] == [32, 6]
    assert len(demand.lines[0].evidence.relationships) == 2


def test_initial_stock_remains_available_and_non_dependent_orders_stay_independent():
    graph = GraphBuilder(stock=10).order(quantity=5).shipment()
    graph.node(
        "Part", "P-01", stock_on_hand=5, inbound_schedule_complete=True, certification_policy="none"
    )
    graph.order("O-02", quantity=5, part="P-01", product="PR-02")
    result = run(graph)
    assert result.dependent_orders == ["O-01"]
    assert result.baseline.on_time_orders == result.disrupted.on_time_orders == ["O-01", "O-02"]
    assert result.newly_at_risk_orders == []


@pytest.mark.parametrize(
    "dispatch,status,arrival,expected,reason",
    [
        ("2026-10-16", "PLANNED", "2026-10-18", "2026-10-26", "OUTAGE_DELAYED"),
        ("2026-10-15", "DISPATCHED", "2026-10-18", "2026-10-18", "ALREADY_DISPATCHED"),
        ("2026-10-24", "PLANNED", "2026-10-26", "2026-10-26", "PLANNED_UNCHANGED"),
        ("2026-10-15", "PLANNED", "2026-10-18", "2026-10-18", "PLANNED_UNCHANGED"),
    ],
)
def test_shipment_outage_and_exclusive_end(dispatch, status, arrival, expected, reason):
    result = run(GraphBuilder().order().shipment(dispatch=dispatch, arrival=arrival, status=status))
    event = result.shipment_timing[0]
    assert event.arrival_date.isoformat() == expected
    assert event.reason_code == reason


def test_late_receipts_cannot_fulfill_early_order_and_baseline_risk_is_separate():
    graph = GraphBuilder().order("O-01", deadline="2026-10-18").shipment(arrival="2026-10-19")
    result = run(graph, include_mitigation=False)
    assert result.baseline_at_risk_orders == result.disrupted_at_risk_orders == ["O-01"]
    assert result.newly_at_risk_orders == []
    assert "RECEIPT_AFTER_DEADLINE" in result.baseline.orders[0].materials[0].reason_codes


def test_cancelled_receipt_never_supplies_stock_or_books_capacity():
    graph = GraphBuilder(capacity=2, lead=1).order().shipment()
    graph.shipment(
        "IN-CANCEL",
        supplier="S-09",
        quantity=100,
        dispatch="2026-10-15",
        arrival="2026-10-16",
        status="CANCELLED",
    )
    result = run(graph)
    assert result.newly_at_risk_orders == ["O-01"]
    assert sum(s.quantity for s in result.proposed_shipments) == 5
    assert result.proposed_shipments[0].dispatch_date == date(2026, 10, 15)
    assert "IN-CANCEL" not in {r.id for r in result.baseline.receipts}


def test_capacity_lead_and_decimal_cost_over_multiple_days():
    result = run(GraphBuilder(capacity=2, lead=1, price="0.10").order().shipment())
    assert result.restored_orders == ["O-01"]
    assert [
        (s.dispatch_date.isoformat(), s.arrival_date.isoformat(), s.quantity)
        for s in result.proposed_shipments
    ] == [
        ("2026-10-15", "2026-10-16", 2),
        ("2026-10-16", "2026-10-17", 2),
        ("2026-10-17", "2026-10-18", 1),
    ]
    assert result.estimated_additional_procurement_cost == Decimal("0.50")
    assert '"estimated_additional_procurement_cost":"0.50"' in result.model_dump_json()
    assert result.evidence_relationships["SUPPLIES:S-09:P-22"].properties["unit_cost"] == "0.10"
    assert sum(s.quantity for s in result.proposed_shipments) == 5
    assert all(p.unused_additional_units == 0 for p in result.mitigation_plans)


def test_booked_alternative_capacity_and_receipt_not_counted_twice():
    graph = GraphBuilder(capacity=2, lead=1).order(quantity=5).shipment()
    graph.shipment(
        "IN-BOOKED", supplier="S-09", quantity=2, dispatch="2026-10-15", arrival="2026-10-16"
    )
    result = run(graph)
    assert result.restored_orders == ["O-01"]
    assert sum(s.quantity for s in result.proposed_shipments) == 3
    assert min(s.dispatch_date for s in result.proposed_shipments) == date(2026, 10, 16)
    candidate = next(c for c in result.candidate_evaluations if c.supplier_id == "S-09")
    assert candidate.booked_dispatches[0]["quantity"] == 2


@pytest.mark.parametrize(
    "supplier,lead,expiry,status,reason",
    [
        ("S-08", 0, "2026-10-15", "eligible", None),
        ("S-08", 1, "2026-10-15", "rejected", "CERTIFICATE_EXPIRED_AT_ARRIVAL"),
        ("S-10", 1, None, "rejected", "MISSING_REQUIRED_CERTIFICATE"),
        ("S-11", 1, None, "rejected", "CERTIFICATE_EXPIRED_AT_ARRIVAL"),
    ],
)
def test_certificates_are_checked_at_arrival(supplier, lead, expiry, status, reason):
    graph = GraphBuilder().order().shipment().offer(supplier, lead=lead, price="1.00")
    if expiry:
        for cert in ("C-01", "C-02"):
            graph.edge("HOLDS_CERT", supplier, cert, valid_until=expiry)
    result = run(graph)
    candidate = next(c for c in result.candidate_evaluations if c.supplier_id == supplier)
    assert candidate.status == status
    if reason:
        assert reason in candidate.reason_codes
    else:
        assert result.proposed_shipments[0].supplier_id == supplier
        assert all(c.status == "valid" for c in result.proposed_shipments[0].certificate_checks)


def test_long_lead_and_zero_capacity_cannot_create_inventory():
    graph = GraphBuilder(lead=20).order().shipment().offer("S-08", capacity=0)
    result = run(graph)
    assert result.newly_at_risk_orders == ["O-01"]
    assert result.restored_orders == result.proposed_shipments == []
    assert result.mitigated.at_risk_orders == result.disrupted.at_risk_orders


def test_extreme_but_valid_graph_lead_is_infeasible_without_calendar_overflow():
    result = run(GraphBuilder(lead=10**9).order().shipment())
    assert result.proposed_shipments == []
    assert "LEAD_TIME_MISSES_DEADLINE" in result.candidate_evaluations[0].reason_codes


def test_proposed_capacity_conserves_stock_across_multiple_orders():
    graph = GraphBuilder(capacity=2, lead=1).order("O-01", quantity=3).order("O-02", quantity=3)
    graph.shipment(quantity=6)
    result = run(graph)
    assert result.restored_orders == ["O-01", "O-02"]
    by_day = defaultdict(int)
    for shipment in result.proposed_shipments:
        by_day[shipment.supplier_id, shipment.part_id, shipment.dispatch_date] += shipment.quantity
    assert max(by_day.values()) <= 2
    assert sum(s.quantity for s in result.proposed_shipments) == 6
    for lot in result.mitigated.ledger:
        assert lot.received_quantity == lot.allocated_quantity + lot.remaining_quantity


def test_failed_multipart_procurement_attempt_is_atomic():
    graph = GraphBuilder().order().shipment()
    graph.node(
        "Part", "P-01", stock_on_hand=0, inbound_schedule_complete=True, certification_policy="none"
    )
    graph.edge("USES", "PR-01", "P-01", units_per_product=1)
    graph.shipment("IN-OTHER", part="P-01")
    graph.offer("S-04", part="P-01", primary=True)
    result = run(graph)
    assert result.proposed_shipments == []
    assert result.estimated_additional_procurement_cost == Decimal("0.00")


@pytest.mark.parametrize(
    "entity,field,value",
    [
        ("P-22", "stock_on_hand", -1),
        ("P-22", "stock_on_hand", None),
        ("O-01", "deadline", "2026-02-30"),
        ("O-01", "priority", -1),
        ("IN-01", "quantity", 0),
        ("IN-01", "status", "UNKNOWN"),
        ("IN-01", "dispatch_date", "invalid"),
    ],
)
def test_invalid_graph_facts_are_explicitly_unresolved(entity, field, value):
    graph = GraphBuilder().order().shipment()
    graph.nodes[entity][1][field] = value
    result = run(graph)
    assert result.incomplete_data is True
    assert result.data_issues
    assert result.disrupted.unresolved_orders == ["O-01"]


@pytest.mark.parametrize(
    "relation,field,value",
    [
        ("SUPPLIES:S-09:P-22", "unit_cost", "-0.01"),
        ("SUPPLIES:S-09:P-22", "daily_capacity", -1),
        ("SUPPLIES:S-09:P-22", "lead_days", None),
        ("USES:PR-01:P-22", "units_per_product", 0),
        ("CONTAINS:O-01:PR-01", "quantity", -1),
    ],
)
def test_bad_bom_and_supplier_terms_never_enable_recovery(relation, field, value):
    graph = GraphBuilder().order().shipment()
    graph.edges[relation][3][field] = value
    result = run(graph)
    assert result.incomplete_data is True
    assert result.proposed_shipments == []


def test_missing_requirements_or_supply_schedule_are_not_assumed_empty():
    graph = GraphBuilder().order()
    del graph.nodes["P-22"][1]["inbound_schedule_complete"]
    del graph.edges["REQUIRES_CERT:P-22:C-02"]
    del graph.edges["REQUIRES_CERT:P-22:C-01"]
    result = run(graph)
    assert result.incomplete_data is True
    assert result.disrupted.unresolved_orders == ["O-01"]


def test_no_mutation_of_snapshot_and_optional_mitigation():
    snapshot = GraphBuilder().order().shipment().snapshot()
    before = snapshot.model_dump_json()
    result = simulate(snapshot, request(include_mitigation=False))
    assert result.mitigated is None and result.proposed_shipments == []
    assert snapshot.model_dump_json() == before


@pytest.mark.parametrize(
    "overrides",
    [
        {"supplier_id": ""},
        {"supplier_id": "S-04' DELETE"},
        {"as_of": "20261015"},
        {"outage_end_exclusive": "2026-10-16"},
        {"outage_end_exclusive": "2026-10-15"},
        {"include_mitigation": "yes"},
        {"outage_start": "2026-02-30"},
        {"as_of": None},
    ],
)
def test_invalid_simulation_requests_return_422_without_db(overrides):
    body = request().model_dump(mode="json") | overrides
    with TestClient(create_app(Settings(_env_file=None, port=1))) as client:
        assert client.post("/api/scenarios/simulate", json=body).status_code == 422
