"""Deterministic interpretation of graph facts; no scenario simulation or LLM."""

from datetime import date

from rippleproof.evidence import node_evidence, path_evidence, relationship_evidence
from rippleproof.models import (
    AlternativesResponse,
    AlternativeSupplier,
    CertificateCheck,
    CertificateRequirement,
    ImpactPath,
    ImpactResponse,
    SupplyTerms,
)
from rippleproof.repository import GraphRepository


class GraphService:
    def __init__(self, repository: GraphRepository):
        self.repository = repository

    def impact(self, supplier_id: str) -> ImpactResponse:
        paths = []
        for raw_path in self.repository.impact_paths(supplier_id):
            supplier, part, product, order = raw_path.nodes()
            _, uses, contains = raw_path.edges()
            quantity = contains.properties["quantity"]
            units_per_product = uses.properties["units_per_product"]
            paths.append(
                ImpactPath(
                    supplier_id=supplier.properties["id"],
                    part_id=part.properties["id"],
                    product_id=product.properties["id"],
                    order_id=order.properties["id"],
                    order_deadline=order.properties["deadline"],
                    order_quantity=quantity,
                    units_per_product=units_per_product,
                    part_units_required=quantity * units_per_product,
                    evidence=path_evidence(raw_path),
                )
            )
        return ImpactResponse(
            supplier_id=supplier_id,
            order_ids=sorted({path.order_id for path in paths}),
            paths=paths,
        )

    def alternatives(self, part_id: str, as_of: date) -> AlternativesResponse:
        facts = self.repository.alternative_facts(part_id)
        requirements = [
            CertificateRequirement(
                certificate_id=certificate.properties["id"],
                name=certificate.properties["name"],
                certificate=node_evidence(certificate),
                relationship=relationship_evidence(requires, part, certificate),
            )
            for part, requires, certificate in facts.requirements
        ]
        candidates: dict[str, AlternativeSupplier] = {}
        holdings = {}
        for supplier, supplies, part, holds, certificate in facts.offers:
            supplier_id = supplier.properties["id"]
            if supplier_id not in candidates:
                candidates[supplier_id] = AlternativeSupplier(
                    supplier=node_evidence(supplier),
                    supply_terms=SupplyTerms.model_validate(supplies.properties),
                    supplies_relationship=relationship_evidence(supplies, supplier, part),
                    certifications_valid=False,
                    certificate_checks=[],
                )
                holdings[supplier_id] = {}
            if holds is not None:
                holdings[supplier_id][certificate.properties["id"]] = relationship_evidence(
                    holds, supplier, certificate
                )

        for supplier_id, candidate in candidates.items():
            checks = []
            for requirement in requirements:
                holding = holdings[supplier_id].get(requirement.certificate_id)
                valid_until = (
                    date.fromisoformat(holding.properties["valid_until"]) if holding else None
                )
                status = (
                    "missing" if holding is None else "valid" if valid_until >= as_of else "expired"
                )
                checks.append(
                    CertificateCheck(
                        certificate_id=requirement.certificate_id,
                        name=requirement.name,
                        status=status,
                        valid_until=valid_until,
                        requirement=requirement.relationship,
                        holding=holding,
                    )
                )
            candidate.certificate_checks = checks
            # If the part has no requirements, there are no modeled cert failures.
            candidate.certifications_valid = all(check.status == "valid" for check in checks)
        return AlternativesResponse(
            part=node_evidence(facts.part),
            as_of=as_of,
            required_certificates=requirements,
            candidates=[candidates[key] for key in sorted(candidates)],
        )
