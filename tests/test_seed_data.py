from collections import Counter
from datetime import date

from rippleproof.seed_data import REFERENCE_DATE, build_dataset


def test_seed_is_repeatable_and_meets_sizes():
    first, second = build_dataset(), build_dataset()
    assert first == second
    assert REFERENCE_DATE == date(2026, 10, 15)
    minimums = {"Supplier": 10, "Part": 15, "Product": 6, "Order": 20, "Certificate": 3}
    for label, minimum in minimums.items():
        ids = [node["id"] for node in first.nodes[label]]
        assert len(ids) >= minimum
        assert len(ids) == len(set(ids))


def test_all_relationships_have_unique_stable_ids_and_valid_endpoints():
    dataset = build_dataset()
    labels = {node["id"]: label for label, nodes in dataset.nodes.items() for node in nodes}
    expected = {
        "SUPPLIES": ("Supplier", "Part"),
        "USES": ("Product", "Part"),
        "CONTAINS": ("Order", "Product"),
        "REQUIRES_CERT": ("Part", "Certificate"),
        "HOLDS_CERT": ("Supplier", "Certificate"),
    }
    ids = []
    for relation, rows in dataset.relationships.items():
        for row in rows:
            assert (labels[row["source_id"]], labels[row["target_id"]]) == expected[relation]
            identity = f"{relation}:{row['source_id']}:{row['target_id']}"
            assert row["properties"]["id"] == identity
            ids.append(identity)
    assert len(ids) == len(set(ids))
    primary_sources = Counter(
        row["target_id"]
        for row in dataset.relationships["SUPPLIES"]
        if row["properties"]["is_primary"]
    )
    assert set(primary_sources) == {part["id"] for part in dataset.nodes["Part"]}
    assert all(count == 1 for count in primary_sources.values())


def test_scenario_invariants_and_nontrivial_topology():
    dataset = build_dataset()
    edges = {
        relation: {(row["source_id"], row["target_id"]): row["properties"] for row in rows}
        for relation, rows in dataset.relationships.items()
    }
    assert edges["SUPPLIES"]["S-04", "P-22"]["is_primary"] is True
    assert ("PR-05", "P-22") in edges["USES"]
    assert ("O-101", "PR-05") in edges["CONTAINS"]
    assert ("S-10", "C-02") not in edges["HOLDS_CERT"]
    assert ("P-22", "C-02") in edges["REQUIRES_CERT"]
    assert (
        edges["SUPPLIES"]["S-10", "P-22"]["unit_cost"]
        < edges["SUPPLIES"]["S-09", "P-22"]["unit_cost"]
    )
    for certificate in ("C-01", "C-02"):
        assert (
            date.fromisoformat(edges["HOLDS_CERT"]["S-09", certificate]["valid_until"])
            >= REFERENCE_DATE
        )
    assert not any(row["source_id"] == "S-12" for row in dataset.relationships["SUPPLIES"])
    assert (
        len(
            {
                row["source_id"]
                for row in dataset.relationships["USES"]
                if row["target_id"] == "P-22"
            }
        )
        > 1
    )
    assert {order["status"] for order in dataset.nodes["Order"]} == {"open", "closed"}


def test_numeric_values_and_dates_are_well_formed():
    dataset = build_dataset()
    for part in dataset.nodes["Part"]:
        assert isinstance(part["stock_on_hand"], int) and part["stock_on_hand"] >= 0
    for product in dataset.nodes["Product"]:
        assert product["production_days"] > 0
    for order in dataset.nodes["Order"]:
        assert date.fromisoformat(order["deadline"]) >= REFERENCE_DATE
    for relation, rows in dataset.relationships.items():
        for row in rows:
            props = row["properties"]
            if relation == "SUPPLIES":
                assert (
                    props["unit_cost"] > 0
                    and props["lead_days"] >= 0
                    and props["daily_capacity"] > 0
                )
            if relation == "CONTAINS":
                assert props["quantity"] > 0
            if relation == "USES":
                assert props["units_per_product"] > 0
            if relation == "HOLDS_CERT":
                date.fromisoformat(props["valid_until"])
