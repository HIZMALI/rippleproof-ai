"""Reproducible synthetic input, used ONLY by the explicit seed command.

The API never imports this module. Runtime answers come from FalkorDB.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from random import Random
from typing import Any

REFERENCE_DATE = date(2026, 10, 15)
RANDOM_SEED = 20261015


@dataclass(frozen=True)
class SyntheticDataset:
    nodes: dict[str, list[dict[str, Any]]]
    relationships: dict[str, list[dict[str, Any]]]


def build_dataset() -> SyntheticDataset:
    rng = Random(RANDOM_SEED)
    nodes = {
        "Supplier": [
            {
                "id": f"S-{i:02d}",
                "name": f"Synthetic Supplier {i:02d}",
                "region": ("North", "South", "East", "West")[(i - 1) % 4],
                "status": "active",
            }
            for i in range(1, 13)
        ],
        "Part": [
            {
                "id": f"P-{i:02d}",
                "name": f"Synthetic Part {i:02d}",
                "stock_on_hand": rng.randint(0, 90),
            }
            for i in [*range(1, 16), 22]
        ],
        "Product": [
            {
                "id": f"PR-{i:02d}",
                "name": f"Synthetic Product {i:02d}",
                "production_days": 1 + i % 4,
            }
            for i in range(1, 9)
        ],
        "Order": [
            {
                "id": f"O-{101 + i}",
                "customer_name": f"Synthetic Customer {i + 1:02d}",
                "deadline": (REFERENCE_DATE + timedelta(days=3 + i % 12)).isoformat(),
                "priority": 1 + i % 3,
                "status": "closed" if i > 0 and i % 6 == 0 else "open",
            }
            for i in range(24)
        ],
        "Certificate": [
            {"id": "C-01", "name": "Synthetic Quality Standard"},
            {"id": "C-02", "name": "Synthetic Material Safety Standard"},
            {"id": "C-03", "name": "Synthetic Handling Standard"},
        ],
    }
    relationships = {
        name: [] for name in ("SUPPLIES", "USES", "CONTAINS", "REQUIRES_CERT", "HOLDS_CERT")
    }

    def add(relation: str, source: str, target: str, **properties: Any) -> None:
        relationships[relation].append(
            {
                "source_id": source,
                "target_id": target,
                "properties": {"id": f"{relation}:{source}:{target}", **properties},
            }
        )

    for i in [*range(1, 16), 22]:
        part_id = f"P-{i:02d}"
        primary_id = "S-04" if i == 22 else f"S-{1 + (i - 1) % 8:02d}"
        add(
            "SUPPLIES",
            primary_id,
            part_id,
            unit_cost=round(10 + i * 0.7, 2),
            lead_days=2 + i % 5,
            daily_capacity=30 + i,
            is_primary=True,
        )
        required_ids = ("C-01", "C-02") if i == 22 else (f"C-{1 + i % 3:02d}",)
        for certificate_id in required_ids:
            add("REQUIRES_CERT", part_id, certificate_id)

    for supplier_id, part_id, cost, lead, capacity in (
        ("S-09", "P-22", 14.5, 3, 60),
        ("S-10", "P-22", 8.5, 2, 80),
        ("S-11", "P-22", 11.0, 4, 45),
        ("S-08", "P-22", 15.0, 5, 40),
        ("S-09", "P-03", 12.0, 3, 50),
        ("S-09", "P-06", 13.0, 4, 50),
        ("S-10", "P-02", 8.0, 2, 70),
        ("S-10", "P-12", 9.0, 2, 70),
    ):
        add(
            "SUPPLIES",
            supplier_id,
            part_id,
            unit_cost=cost,
            lead_days=lead,
            daily_capacity=capacity,
            is_primary=False,
        )

    bill_of_materials = {
        "PR-01": (1, 2, 3),
        "PR-02": (3, 4, 5),
        "PR-03": (6, 7, 8),
        "PR-04": (8, 9, 10),
        "PR-05": (22, 4, 7),
        "PR-06": (10, 11, 12),
        "PR-07": (12, 13, 22),
        "PR-08": (13, 14, 15),
    }
    for product_id, parts in bill_of_materials.items():
        for part_number in parts:
            add("USES", product_id, f"P-{part_number:02d}", units_per_product=rng.randint(1, 4))

    for i in range(24):
        product_number = 5 if i == 0 else 1 + i % 8
        add("CONTAINS", f"O-{101 + i}", f"PR-{product_number:02d}", quantity=rng.randint(5, 25))
        if i % 5 == 0:
            extra_product = 1 + product_number % 8
            add("CONTAINS", f"O-{101 + i}", f"PR-{extra_product:02d}", quantity=rng.randint(2, 10))

    for i in range(1, 13):
        for j in range(1, 4):
            # S-10 lacks the required C-02; S-11's C-02 is expired.
            if (i == 10 and j == 2) or (i == 12 and j != 1):
                continue
            expiry = "2027-10-15"
            if i == 11 and j == 2:
                expiry = "2026-10-14"
            if i == 8 and j == 2:
                expiry = REFERENCE_DATE.isoformat()
            add("HOLDS_CERT", f"S-{i:02d}", f"C-{j:02d}", valid_until=expiry)
    return SyntheticDataset(nodes=nodes, relationships=relationships)
