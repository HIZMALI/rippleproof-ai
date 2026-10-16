import json
import secrets
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from rippleproof.app import create_app
from rippleproof.config import Phase3Settings
from rippleproof.decisions import ApprovalRequest, DecisionService, digest
from rippleproof.errors import OperationError
from rippleproof.inbound_data import build_inbound_extension
from rippleproof.tools import GraphTools
from tests.integration.test_graph import snapshot as physical_properties
from tests.simulation_helpers import request

pytestmark = pytest.mark.integration


@pytest.fixture
def decision_context(repository):
    repository.migrate_inbound(build_inbound_extension())
    token = secrets.token_urlsafe(32)
    settings = Phase3Settings(_env_file=None, approval_secret=token)
    service = DecisionService(repository, settings)
    with TestClient(create_app(repository.settings, settings)) as client:
        yield repository, service, client, {"Authorization": "Bearer " + token}


def prepare_body(**overrides):
    return {
        "scenario": request().model_dump(mode="json"),
        "mitigation_plan_id": "cost_first",
        **overrides,
    }


def approve_body(preview, **overrides):
    return {
        "scenario": preview["scenario"],
        "mitigation_plan_id": preview["mitigation_plan_id"],
        "expected_scenario_id": preview["scenario_id"],
        "expected_operational_fingerprint": preview["operational_fingerprint"],
        "expected_plan_revision": preview["plan_revision"],
        "idempotency_key": "verification-key-0001",
        "operator_id": "test-harness",
        "rationale": "Synthetic integration test, not a real operator approval or purchase.",
        "confirm_internal_decision": True,
        **overrides,
    }


def prepared(client, **overrides):
    result = client.post("/api/decisions/prepare", json=prepare_body(**overrides))
    assert result.status_code == 200, result.text
    return result.json()


def test_http_history_accepts_bounded_integer_query_strings(decision_context):
    _, _, client, headers = decision_context
    preview = prepared(client)
    ids = []
    for index in range(2):
        record = client.post(
            "/api/decisions/approve",
            json=approve_body(preview, idempotency_key=f"phase4-pagination-{index:04d}"),
            headers=headers,
        )
        assert record.status_code == 200
        ids.append(record.json()["decision_id"])
    first = client.get("/api/decisions?offset=0&limit=1")
    assert first.status_code == 200
    assert first.json()["total"] == 2
    assert first.json()["next_offset"] == 1
    second = client.get("/api/decisions?offset=1&limit=1")
    assert second.status_code == 200
    assert second.json()["next_offset"] is None
    assert {
        first.json()["items"][0]["decision_id"],
        second.json()["items"][0]["decision_id"],
    } == set(ids)
    assert (
        client.get(
            "/api/decisions",
            params={"scenario_id": preview["scenario_id"], "offset": 0, "limit": 5},
        ).json()["total"]
        == 2
    )


def test_http_history_rejects_noninteger_and_out_of_range_paging(decision_context):
    _, _, client, _ = decision_context
    for query in ("limit=0", "limit=11", "offset=-1", "limit=1.0", "limit=1e0", "offset=no"):
        assert client.get("/api/decisions?" + query).status_code == 422


def test_prepare_is_read_only_and_plan_variants_are_authoritative(decision_context):
    repository, _, client, _ = decision_context
    before = physical_properties(repository)
    main = prepared(client)
    assert main["estimated_additional_procurement_cost"] == "1364.00"
    assert sum(p["quantity"] for p in main["proposed_shipments"]) == 132
    alternate = prepared(client, mitigation_plan_id="supplier:S-09")
    assert alternate["estimated_additional_procurement_cost"] == "391.50"
    assert alternate["restored_orders"] == ["O-105"]
    assert physical_properties(repository) == before


def test_internal_approval_atomic_links_replay_and_fingerprint(decision_context):
    repository, _, client, headers = decision_context
    facts = GraphTools(repository).snapshot()
    before = client.post("/api/scenarios/simulate", json=request().model_dump(mode="json")).json()
    preview = prepared(client)
    body = approve_body(preview)
    first = client.post("/api/decisions/approve", json=body, headers=headers)
    assert first.status_code == 200, first.text
    record = first.json()
    assert record["status"] == "APPROVED_INTERNAL"
    assert record["preview"] == preview
    assert client.get("/api/decisions/" + record["decision_id"]).json() == record
    assert client.post("/api/decisions/approve", json=body, headers=headers).json() == record
    summary = repository.summary()
    assert summary.node_count == 147 and summary.relationship_count == 441
    assert summary.nodes_by_label["Decision"] == summary.nodes_by_label["Evidence"] == 1
    assert summary.relationships_by_type["REFERENCES"] == 145
    assert summary.relationships_by_type["SELECTS"] == summary.relationships_by_type["AFFECTS"] == 2
    assert GraphTools(repository).snapshot() == facts
    assert (
        client.post("/api/scenarios/simulate", json=request().model_dump(mode="json")).json()
        == before
    )
    archived = repository.memory_node(record["evidence_ref"], evidence=True)
    snapshot = json.loads(archived["snapshot_json"])
    assert set(snapshot["nodes"]) == set(facts.nodes)
    assert set(snapshot["relationships"]) == set(facts.relationships)
    with repository.connect() as db:
        linked = (
            db.select_graph(repository.settings.graph)
            .ro_query(
                "MATCH (:Decision {id: $id})-[:SUPPORTED_BY]->(:Evidence)-[:REFERENCES]->(n) "
                "RETURN n.id ORDER BY n.id",
                {"id": record["decision_id"]},
            )
            .result_set
        )
    assert [r[0] for r in linked] == sorted(facts.nodes)
    # A new service/app instance has no local decision cache and replays from DB.
    with TestClient(create_app(repository.settings, client.app.state.phase3_settings)) as fresh:
        assert fresh.get("/api/decisions/" + record["decision_id"]).json() == record
        assert fresh.post("/api/decisions/approve", json=body, headers=headers).json() == record
    assert client.get("/api/decisions").json()["total"] == 1
    history = GraphTools(repository).dispatch("get_decision_history", {}).data
    assert history["items"][0]["evidence_ref"] == record["evidence_ref"]
    page = (
        GraphTools(repository)
        .dispatch(
            "resolve_evidence",
            {"ref": record["evidence_ref"], "expected_fingerprint": facts.fingerprint, "limit": 2},
        )
        .data
    )
    assert page["kind"] == "archived_snapshot" and page["total"] == 436 and page["truncated"]
    conflict = client.post(
        "/api/decisions/approve",
        headers=headers,
        json=approve_body(preview, rationale="different payload"),
    )
    assert conflict.status_code == 409
    assert repository.summary() == summary


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_approval_requires_token(decision_context, headers):
    repository, _, client, _ = decision_context
    response = client.post(
        "/api/decisions/approve", json=approve_body(prepared(client)), headers=headers
    )
    assert response.status_code == 401
    assert repository.summary().node_count == 145


@pytest.mark.parametrize(
    "tampering",
    [
        {"quantity": 1},
        {"estimated_additional_procurement_cost": "0.00"},
        {"supplier_id": "S-10"},
        {"evidence_refs": ["FAKE"]},
        {"confirm_internal_decision": False},
        {"confirm_internal_decision": 1},
        {"idempotency_key": "short"},
    ],
)
def test_untrusted_approval_fields_rejected(decision_context, tampering):
    repository, _, client, headers = decision_context
    response = client.post(
        "/api/decisions/approve", headers=headers, json=approve_body(prepared(client), **tampering)
    )
    assert response.status_code == 422
    assert repository.summary().node_count == 145


@pytest.mark.parametrize(
    "change",
    [
        "MATCH (n:Part {id:'P-22'}) SET n.stock_on_hand=100",
        "MATCH (:Supplier {id:'S-09'})-[r:HOLDS_CERT]->(:Certificate {id:'C-02'}) "
        "SET r.valid_until='2026-10-16'",
        "MATCH (:Supplier {id:'S-09'})-[r:SUPPLIES]->(:Part {id:'P-22'}) SET r.unit_cost=100",
        "MATCH (n:InboundShipment {id:'IN-P-22-02'}) SET n.expected_arrival_date='2026-10-20'",
    ],
)
def test_stale_preview_conflicts_after_real_source_changes(decision_context, change):
    repository, _, client, headers = decision_context
    body = approve_body(prepared(client))
    with repository.connect() as db:
        db.select_graph(repository.settings.graph).query(change)
    response = client.post("/api/decisions/approve", json=body, headers=headers)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "stale_preview"
    assert repository.summary().nodes_by_label["Decision"] == 0


def test_preview_tamper_and_unknown_plan(decision_context):
    _, _, client, headers = decision_context
    preview = prepared(client)
    for changes in (
        {"expected_plan_revision": "0" * 64},
        {"expected_scenario_id": "SC-" + "0" * 20},
        {"mitigation_plan_id": "lead_first"},
    ):
        assert (
            client.post(
                "/api/decisions/approve", headers=headers, json=approve_body(preview, **changes)
            ).status_code
            == 409
        )
    assert (
        client.post(
            "/api/decisions/prepare", json=prepare_body(mitigation_plan_id="supplier:S-99")
        ).status_code
        == 422
    )


def test_concurrent_replay_creates_only_one_decision(decision_context):
    repository, service, client, headers = decision_context
    body = ApprovalRequest.model_validate(approve_body(prepared(client)))

    def approve(_):
        return service.approve(body, headers["Authorization"])

    with ThreadPoolExecutor(max_workers=6) as executor:
        records = list(executor.map(approve, range(6)))
    assert all(r == records[0] for r in records)
    assert repository.summary().node_count == 147


def test_write_guard_leaves_no_partial_nodes_when_sources_missing(decision_context):
    repository, _, _, _ = decision_context
    before = physical_properties(repository)
    with pytest.raises(OperationError):
        repository.save_decision(
            {
                "source_ids": ["MISSING"],
                "source_count": 1,
                "supplier_ids": [],
                "order_ids": [],
                "decision_id": "D-never-written",
                "decision": {"id": "D-never-written"},
                "evidence_id": "E-never-written",
                "evidence": {"id": "E-never-written"},
                "request_digest": "none",
            }
        )
    assert physical_properties(repository) == before


def test_existing_unrelated_archive_cannot_poison_new_approval(decision_context):
    repository, _, client, headers = decision_context
    body = approve_body(prepared(client))
    identity = digest({"graph": repository.settings.graph, "key": body["idempotency_key"]})[:24]
    with repository.connect() as db:
        db.select_graph(repository.settings.graph).query(
            "CREATE (:Evidence {id:$id, kind:'untrusted_collision'})", {"id": "E-" + identity}
        )
    before = physical_properties(repository)
    result = client.post("/api/decisions/approve", json=body, headers=headers)
    assert result.status_code == 409
    assert physical_properties(repository) == before
    assert repository.summary().nodes_by_label["Decision"] == 0
