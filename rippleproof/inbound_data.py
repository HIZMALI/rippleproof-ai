"""Additive, synthetic planned receipts. Never imported by the simulation API."""

from datetime import timedelta

from rippleproof.seed_data import REFERENCE_DATE


def build_inbound_extension() -> list[dict]:
    rows = []

    def add(identity, supplier, part, quantity, dispatch, arrival, status="PLANNED"):
        rows.append(
            {
                "supplier_id": supplier,
                "part_id": part,
                "properties": {
                    "id": identity,
                    "quantity": quantity,
                    "dispatch_date": dispatch.isoformat(),
                    "expected_arrival_date": arrival.isoformat(),
                    "status": status,
                },
                "fulfills_id": f"FULFILLS:{supplier}:{identity}",
                "for_part_id": f"FOR_PART:{identity}:{part}",
            }
        )

    for number in [*range(1, 16), 22]:
        part = f"P-{number:02d}"
        supplier = "S-04" if number == 22 else f"S-{1 + (number - 1) % 8:02d}"
        offsets = (0, 1, 3, 5, 9) if supplier == "S-04" else (0, 2, 4, 6, 8)
        for sequence, offset in enumerate(offsets, 1):
            dispatch = REFERENCE_DATE + timedelta(days=offset)
            transit = 2 if number in (12, 22) else 1
            quantity = 10 if number == 22 and sequence == 1 else min(30 + number, 50)
            # These existing synthetic commitments were dispatched as of the
            # reference date, before the demo outage starts on October 16.
            status = "DISPATCHED" if supplier == "S-04" and sequence == 1 else "PLANNED"
            add(
                f"IN-{part}-{sequence:02d}",
                supplier,
                part,
                quantity,
                dispatch,
                dispatch + timedelta(days=transit),
                status,
            )
    add(
        "IN-CANCELLED-22",
        "S-04",
        "P-22",
        50,
        REFERENCE_DATE + timedelta(days=1),
        REFERENCE_DATE + timedelta(days=3),
        "CANCELLED",
    )
    add("IN-ALT-03", "S-09", "P-03", 20, REFERENCE_DATE, REFERENCE_DATE + timedelta(days=3))
    return rows
