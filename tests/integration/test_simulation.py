import pytest
from fastapi.testclient import TestClient

from rippleproof.app import create_app
from rippleproof.errors import GraphQueryError
from rippleproof.inbound_data import build_inbound_extension
from rippleproof.simulation.snapshot import normalize
from tests.integration.test_graph import snapshot as graph_properties
from tests.simulation_helpers import request

pytestmark = pytest.mark.integration


@pytest.fixture
def migrated(repository):
    repository.migrate_inbound(build_inbound_extension())
    return repository


def post(repository, **overrides):
    with TestClient(create_app(repository.settings)) as client:
        response = client.post(
            "/api/scenarios/simulate", json=request(**overrides).model_dump(mode="json")
        )
    assert response.status_code == 200, response.text
    return response.json()


def test_additive_migration_is_idempotent_and_preserves_base_graph(repository):
    original_nodes, original_edges = graph_properties(repository)
    repository.migrate_inbound(build_inbound_extension())
    first = graph_properties(repository)
    summary = repository.summary()
    assert summary.node_count == 145
    assert summary.relationship_count == 291
    assert summary.nodes_by_label["InboundShipment"] == 82
    assert (
        summary.relationships_by_type["FULFILLS"] == summary.relationships_by_type["FOR_PART"] == 82
    )
    new_nodes = {n["id"]: n for n in first[0]}
    new_edges = {e["id"]: e for e in first[1]}
    assert all(new_nodes[n["id"]] == n for n in original_nodes)
    assert all(new_edges[e["id"]] == e for e in original_edges)
    repository.migrate_inbound(build_inbound_extension())
    assert graph_properties(repository) == first


def test_migration_preserves_existing_shipment_edits(migrated):
    with migrated.connect() as db:
        db.select_graph(migrated.settings.graph).query(
            "MATCH (s:InboundShipment {id: $id}) SET s.quantity = $quantity",
            {"id": "IN-P-22-01", "quantity": 9},
        )
    before = graph_properties(migrated)
    migrated.migrate_inbound(build_inbound_extension())
    assert graph_properties(migrated) == before


def test_migration_refuses_conflicting_endpoints_before_writes(repository):
    with repository.connect() as db:
        db.select_graph(repository.settings.graph).query(
            "MATCH (s:Supplier {id: $supplier}) CREATE (s)-[:FULFILLS {id: $edge}]->"
            "(:InboundShipment {id: $shipment})",
            {"supplier": "S-10", "edge": "FULFILLS:conflict", "shipment": "IN-P-22-01"},
        )
    before = graph_properties(repository)
    with pytest.raises(GraphQueryError):
        repository.migrate_inbound(build_inbound_extension())
    assert graph_properties(repository) == before


def test_live_demo_exact_demands_risk_and_mitigation(migrated):
    body = post(migrated)
    assert body["incomplete_data"] is False
    assert body["newly_at_risk_orders"] == ["O-105", "O-106"]
    assert body["baseline_at_risk_orders"] == ["O-122", "O-123"]
    assert body["disrupted_at_risk_orders"] == ["O-105", "O-106", "O-123"]
    assert body["restored_orders"] == ["O-105", "O-106"]
    assert body["estimated_additional_procurement_cost"] == "1364.00"
    assert sum(p["quantity"] for p in body["proposed_shipments"]) == 132
    assert body["baseline"]["on_time_orders"] == sorted(body["baseline"]["on_time_orders"])
    assert "O-101" in body["disrupted"]["on_time_orders"]
    demand = next(o for o in body["order_demands"] if o["order_id"] == "O-101")
    part = next(p for p in demand["parts"] if p["part_id"] == "P-22")
    assert part["quantity"] == 32
    assert part["lines"][0]["product_quantity"] == 8
    assert part["lines"][0]["units_per_product"] == 4
    assert len(body["dependent_orders"]) == 11
    assert set(body["newly_at_risk_orders"]) < set(body["dependent_orders"])
    path = next(
        p
        for p in body["dependency_paths"]
        if [n["id"] for n in p["nodes"]] == ["S-04", "P-22", "PR-05", "O-101"]
    )
    assert [r["id"] for r in path["relationships"]] == [
        "SUPPLIES:S-04:P-22",
        "USES:PR-05:P-22",
        "CONTAINS:O-101:PR-05",
    ]


def test_live_certificate_rejections_and_arrival_dates(migrated):
    body = post(migrated)
    candidates = {
        c["supplier_id"]: c for c in body["candidate_evaluations"] if c["part_id"] == "P-22"
    }
    assert candidates["S-09"]["status"] == "eligible"
    assert "MISSING_REQUIRED_CERTIFICATE" in candidates["S-10"]["reason_codes"]
    assert "CERTIFICATE_EXPIRED_AT_ARRIVAL" in candidates["S-11"]["reason_codes"]
    assert candidates["S-08"]["earliest_arrival_date"] == "2026-10-20"
    assert "CERTIFICATE_EXPIRED_AT_ARRIVAL" in candidates["S-08"]["reason_codes"]
    for shipment in body["proposed_shipments"]:
        assert all(
            c["status"] == "valid" and c["valid_until"] >= shipment["arrival_date"]
            for c in shipment["certificate_checks"]
        )


def test_live_receipt_status_and_end_boundary(migrated):
    events = {e["shipment_id"]: e for e in post(migrated)["shipment_timing"]}
    assert events["IN-P-22-01"]["reason_code"] == "ALREADY_DISPATCHED"
    assert events["IN-P-22-02"]["arrival_date"] == "2026-10-26"
    assert events["IN-P-22-05"]["dispatch_date"] == "2026-10-24"
    assert events["IN-P-22-05"]["reason_code"] == "PLANNED_UNCHANGED"
    assert events["IN-CANCELLED-22"]["included"] is False


def test_live_simulation_repeatability_no_persistence_of_proposals(migrated):
    before = graph_properties(migrated)
    first, second = post(migrated), post(migrated)
    assert first == second
    assert graph_properties(migrated) == before
    assert migrated.summary().nodes_by_label["InboundShipment"] == 82


def test_live_graph_change_changes_cost_and_snapshot_fingerprint(migrated):
    before = post(migrated)
    with migrated.connect() as db:
        db.select_graph(migrated.settings.graph).query(
            "MATCH (p:Part {id: $id}) SET p.stock_on_hand = $quantity",
            {"id": "P-22", "quantity": 100},
        )
    after = post(migrated)
    assert before["snapshot_fingerprint"] != after["snapshot_fingerprint"]
    assert after["estimated_additional_procurement_cost"] == "1074.00"


def test_live_missing_bom_is_unresolved(migrated):
    with migrated.connect() as db:
        db.select_graph(migrated.settings.graph).query(
            "MATCH (:Order {id: $id})-[c:CONTAINS]->() REMOVE c.quantity", {"id": "O-101"}
        )
    body = post(migrated)
    assert body["incomplete_data"] is True
    assert "O-101" in body["baseline"]["unresolved_orders"]


def test_base_graph_without_receipts_reports_insufficient_data(repository):
    body = post(repository)
    assert body["incomplete_data"] is True
    assert len(body["baseline"]["unresolved_orders"]) == 21


def test_no_dependency_supplier_and_optional_mitigation(migrated):
    body = post(migrated, supplier_id="S-12", include_mitigation=False)
    assert body["dependent_orders"] == body["dependency_paths"] == []
    assert body["baseline_at_risk_orders"] == body["disrupted_at_risk_orders"]
    assert body["newly_at_risk_orders"] == []
    assert body["mitigated"] is None


def test_simulation_unknown_supplier_and_phase1_compatibility(migrated):
    with TestClient(create_app(migrated.settings)) as client:
        body = request(supplier_id="S-99").model_dump(mode="json")
        assert client.post("/api/scenarios/simulate", json=body).status_code == 404
        assert client.get("/health").status_code == 200
        summary = client.get("/api/graph/summary").json()
        assert summary["node_count"] == 145 and summary["relationship_count"] == 291
        assert "O-101" in client.get("/api/impact-paths?supplier_id=S-04").json()["order_ids"]
        alt = client.get("/api/alternatives?part_id=P-22&as_of=2026-10-15").json()
        assert (
            next(c for c in alt["candidates"] if c["supplier"]["id"] == "S-09")[
                "certifications_valid"
            ]
            is True
        )


def test_snapshot_uses_live_connected_graph_facts(migrated):
    nodes, edges = migrated.snapshot_facts("S-04")
    snapshot = normalize(nodes, edges)
    assert len(snapshot.nodes) == 145
    assert len(snapshot.relationships) == 291
    assert len(snapshot.shipments) == 82
    assert snapshot.issues == []
