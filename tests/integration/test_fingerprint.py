import pytest

from rippleproof.simulation.engine import simulate
from rippleproof.simulation.snapshot import normalize
from tests.integration.test_simulation import migrated  # noqa: F401
from tests.simulation_helpers import request

pytestmark = pytest.mark.integration


def result(repository):
    return simulate(normalize(*repository.snapshot_facts("S-04")), request())


def test_memory_only_does_not_change_material_snapshot_or_scenario(migrated):  # noqa: F811
    before = result(migrated)
    with migrated.connect() as db:
        db.select_graph(migrated.settings.graph).query(
            "CREATE (:Decision {id: 'D-regression'})-[:SUPPORTED_BY {id: 'SB-regression'}]"
            "->(:Evidence {id: 'E-regression'})"
        )
    assert result(migrated) == before


@pytest.mark.parametrize(
    "query",
    [
        "MATCH (n:Part {id: 'P-22'}) SET n.stock_on_hand = 100",
        "MATCH (n:Supplier {id: 'S-09'}) SET n.status = 'inactive'",
        "MATCH (:Supplier {id: 'S-09'})-[r:SUPPLIES]->(:Part {id: 'P-22'}) SET r.unit_cost = 15.5",
        "MATCH (n:Order {id: 'O-105'}) SET n.deadline = '2026-10-19'",
        "MATCH (:Supplier {id: 'S-09'})-[r:HOLDS_CERT]->(:Certificate {id: 'C-02'}) "
        "SET r.valid_until = '2026-10-16'",
        "MATCH (n:InboundShipment {id: 'IN-P-22-02'}) SET n.expected_arrival_date = '2026-10-19'",
    ],
)
def test_each_operational_revision_invalidates_scenario(migrated, query):  # noqa: F811
    before = result(migrated)
    with migrated.connect() as db:
        db.select_graph(migrated.settings.graph).query(query)
    after = result(migrated)
    assert before.snapshot_fingerprint != after.snapshot_fingerprint
    assert before.scenario_id != after.scenario_id
