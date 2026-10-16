import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from rippleproof.app import create_app
from rippleproof.config import Settings
from rippleproof.models import AlternativesQuery


@pytest.fixture
def client():
    # Invalid requests must fail before any DB access; port 1 is never used.
    with TestClient(create_app(Settings(_env_file=None, port=1))) as client:
        yield client


@pytest.mark.parametrize("supplier_id", ["", "s-04", "S-4", "S-04' OR 1=1", "S-04\n", "S-123456"])
def test_invalid_supplier_ids(client, supplier_id):
    response = client.get("/api/impact-paths", params={"supplier_id": supplier_id})
    assert response.status_code == 422


@pytest.mark.parametrize("part_id", ["", "p-22", "P-2", "P-22' MATCH (n)", "P-22\n", "P-123456"])
def test_invalid_part_ids(client, part_id):
    response = client.get("/api/alternatives", params={"part_id": part_id, "as_of": "2026-10-15"})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "as_of",
    ["20261015", "15-10-2026", "2026-02-30", "2026-10-15T00:00:00", "", "today", "2026-1-5"],
)
def test_invalid_dates(client, as_of):
    response = client.get("/api/alternatives", params={"part_id": "P-22", "as_of": as_of})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "path", ["/api/impact-paths", "/api/alternatives", "/api/alternatives?part_id=P-22"]
)
def test_required_parameters(client, path):
    assert client.get(path).status_code == 422


def test_unknown_query_parameters_rejected(client):
    assert client.get("/api/impact-paths?supplier_id=S-04&cypher=DELETE").status_code == 422


def test_valid_ids_and_explicit_date_contract():
    value = AlternativesQuery(part_id="P-22", as_of="2026-10-15")
    assert value.as_of.isoformat() == "2026-10-15"
    assert value.part_id == "P-22"


@pytest.mark.parametrize(
    "values", [{"port": 0}, {"port": 65536}, {"graph": "bad graph"}, {"socket_timeout_s": 0}]
)
def test_invalid_settings_fail_fast(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_openapi_has_typed_endpoints(client):
    schema = client.get("/openapi.json").json()
    assert set(schema["paths"]) == {
        "/health",
        "/api/graph/summary",
        "/api/impact-paths",
        "/api/alternatives",
        "/api/scenarios/simulate",
        "/api/agent/run",
        "/api/agent/capabilities",
        "/api/decisions/prepare",
        "/api/decisions/approve",
        "/api/decisions/{decision_id}",
        "/api/decisions",
    }
    assert schema["paths"]["/api/impact-paths"]["get"]["responses"]["503"]
