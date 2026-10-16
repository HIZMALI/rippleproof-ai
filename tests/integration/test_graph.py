import pytest
from fastapi.testclient import TestClient

from rippleproof.app import create_app
from rippleproof.seed_data import build_dataset

pytestmark = pytest.mark.integration


def snapshot(repository):
    with repository.connect() as db:
        graph = db.select_graph(repository.settings.graph)
        nodes = graph.ro_query("MATCH (n) RETURN n ORDER BY n.id").result_set
        edges = graph.ro_query("MATCH ()-[r]->() RETURN r ORDER BY r.id").result_set
        return ([row[0].properties for row in nodes], [row[0].properties for row in edges])


def test_seed_idempotency_restores_properties_without_multiplication(repository):
    first = repository.summary()
    original = snapshot(repository)
    assert first.node_count == sum(len(rows) for rows in build_dataset().nodes.values())
    assert first.relationship_count == sum(
        len(rows) for rows in build_dataset().relationships.values()
    )
    with repository.connect() as db:
        graph = db.select_graph(repository.settings.graph)
        graph.query(
            "MATCH (p:Part {id: $id}) SET p.stock_on_hand = $stock", {"id": "P-22", "stock": -1}
        )
        graph.query(
            "MATCH (:Supplier {id: $id})-[r:SUPPLIES]->(:Part {id: $part}) SET r.lead_days = $lead",
            {"id": "S-09", "part": "P-22", "lead": 999},
        )
    second = repository.seed(build_dataset())
    assert second == first
    assert snapshot(repository) == original
    repository.seed(build_dataset())
    assert snapshot(repository) == original


def test_readiness_and_empty_graph(empty_repository):
    with TestClient(create_app(empty_repository.settings)) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["graph_exists"] is False
        response = client.get("/api/graph/summary")
        assert response.status_code == 200
        assert response.json()["node_count"] == response.json()["relationship_count"] == 0
        assert all(count == 0 for count in response.json()["nodes_by_label"].values())
        assert all(count == 0 for count in response.json()["relationships_by_type"].values())
        assert client.get("/api/impact-paths?supplier_id=S-04").status_code == 404
        assert client.get("/api/alternatives?part_id=P-22&as_of=2026-10-15").status_code == 404
    # Reading an empty graph must not create it as a side effect.
    assert empty_repository.ready() is False


def test_existing_empty_graph_has_zero_counts(empty_repository):
    with empty_repository.connect() as db:
        # Create the graph through a real write, then remove its only node.
        # RETURN 1 creates a key without an AOF write in FalkorDB 4.22.1;
        # deleting that key during teardown causes an invalid DELETE on replay.
        graph = db.select_graph(empty_repository.settings.graph)
        graph.query("CREATE (:EmptyGraphProbe {id: $id})", {"id": "empty-graph-probe"})
        graph.query("MATCH (n:EmptyGraphProbe {id: $id}) DELETE n", {"id": "empty-graph-probe"})
    assert empty_repository.ready() is True
    summary = empty_repository.summary()
    assert summary.node_count == summary.relationship_count == 0
    assert not any(summary.nodes_by_label.values())
    assert not any(summary.relationships_by_type.values())


def test_impact_three_hop_path_with_real_evidence(client, repository):
    response = client.get("/api/impact-paths?supplier_id=S-04")
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_type"] == "dependency_only"
    assert "O-101" in body["order_ids"]
    path = next(
        path
        for path in body["paths"]
        if (path["order_id"], path["part_id"], path["product_id"]) == ("O-101", "P-22", "PR-05")
    )
    assert [node["id"] for node in path["evidence"]["nodes"]] == ["S-04", "P-22", "PR-05", "O-101"]
    assert [edge["type"] for edge in path["evidence"]["relationships"]] == [
        "SUPPLIES",
        "USES",
        "CONTAINS",
    ]
    assert path["evidence"]["relationships"][1]["source_id"] == "PR-05"
    assert path["part_units_required"] == path["order_quantity"] * path["units_per_product"]
    # Independently verify every returned ID/property/direction against the DB.
    with repository.connect() as db:
        graph = db.select_graph(repository.settings.graph)
        for item in body["paths"]:
            assert item["evidence"]["nodes"][-1]["properties"]["status"] == "open"
            assert item["evidence"]["relationships"][0]["properties"]["is_primary"] is True
            for edge in item["evidence"]["relationships"]:
                rows = graph.ro_query(
                    "MATCH (s)-[r {id: $id}]->(t) RETURN s.id, t.id, r", {"id": edge["id"]}
                ).result_set
                assert len(rows) == 1
                assert rows[0][:2] == [edge["source_id"], edge["target_id"]]
                assert rows[0][2].properties == edge["properties"]


def test_existing_supplier_with_no_dependencies(client):
    response = client.get("/api/impact-paths?supplier_id=S-12")
    assert response.status_code == 200
    assert response.json()["paths"] == response.json()["order_ids"] == []


@pytest.mark.parametrize(
    "path",
    ["/api/impact-paths?supplier_id=S-99", "/api/alternatives?part_id=P-99&as_of=2026-10-15"],
)
def test_nonexistent_ids(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "entity_not_found"


def test_alternatives_certificates_and_expiry_boundary(client):
    response = client.get("/api/alternatives?part_id=P-22&as_of=2026-10-15")
    assert response.status_code == 200
    body = response.json()
    assert {cert["certificate_id"] for cert in body["required_certificates"]} == {"C-01", "C-02"}
    candidates = {candidate["supplier"]["id"]: candidate for candidate in body["candidates"]}
    assert set(candidates) == {"S-08", "S-09", "S-10", "S-11"}
    assert candidates["S-09"]["certifications_valid"] is True
    assert candidates["S-10"]["certifications_valid"] is False
    assert (
        candidates["S-10"]["supply_terms"]["unit_cost"]
        < candidates["S-09"]["supply_terms"]["unit_cost"]
    )
    checks = {check["certificate_id"]: check for check in candidates["S-10"]["certificate_checks"]}
    assert checks["C-02"]["status"] == "missing"
    assert checks["C-02"]["holding"] is None
    assert checks["C-02"]["requirement"]["id"] == "REQUIRES_CERT:P-22:C-02"
    assert candidates["S-11"]["certifications_valid"] is False
    assert (
        next(
            check
            for check in candidates["S-11"]["certificate_checks"]
            if check["certificate_id"] == "C-02"
        )["status"]
        == "expired"
    )
    assert candidates["S-08"]["certifications_valid"] is True
    tomorrow = client.get("/api/alternatives?part_id=P-22&as_of=2026-10-16").json()
    assert (
        next(c for c in tomorrow["candidates"] if c["supplier"]["id"] == "S-08")[
            "certifications_valid"
        ]
        is False
    )


def test_other_parts_and_no_alternatives(client):
    response = client.get("/api/alternatives?part_id=P-03&as_of=2026-10-15")
    assert response.status_code == 200
    assert [candidate["supplier"]["id"] for candidate in response.json()["candidates"]] == ["S-09"]
    response = client.get("/api/alternatives?part_id=P-01&as_of=2026-10-15")
    assert response.status_code == 200
    assert response.json()["candidates"] == []


def test_reads_repeat_exactly_and_do_not_mutate_graph(client, repository):
    before = snapshot(repository)
    for path in (
        "/health",
        "/api/graph/summary",
        "/api/impact-paths?supplier_id=S-04",
        "/api/alternatives?part_id=P-22&as_of=2026-10-15",
    ):
        first, second = client.get(path), client.get(path)
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
    assert snapshot(repository) == before


def test_graph_changes_change_answers(client, repository):
    with repository.connect() as db:
        graph = db.select_graph(repository.settings.graph)
        graph.query(
            "MATCH (:Supplier {id: $supplier})-[r:SUPPLIES]->(:Part {id: $part}) "
            "SET r.is_primary = false",
            {"supplier": "S-04", "part": "P-22"},
        )
        graph.query(
            "MATCH (:Supplier {id: $supplier})-[r:HOLDS_CERT]->(:Certificate {id: $cert}) "
            "SET r.valid_until = $expiry",
            {"supplier": "S-09", "cert": "C-02", "expiry": "2026-10-14"},
        )
    impact = client.get("/api/impact-paths?supplier_id=S-04").json()
    assert all(path["part_id"] != "P-22" for path in impact["paths"])
    alternatives = client.get("/api/alternatives?part_id=P-22&as_of=2026-10-15").json()
    candidate = next(c for c in alternatives["candidates"] if c["supplier"]["id"] == "S-09")
    assert candidate["certifications_valid"] is False
