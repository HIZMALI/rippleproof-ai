import pytest
from falkordb.edge import Edge
from falkordb.node import Node
from falkordb.path import Path

from rippleproof.errors import GraphQueryError
from rippleproof.evidence import path_evidence, relationship_evidence


def test_evidence_preserves_reverse_traversal_and_stored_identity():
    part = Node(node_id=1, labels="Part", properties={"id": "P-77"})
    product = Node(node_id=2, labels="Product", properties={"id": "PR-18"})
    uses = Edge(
        2, "USES", 1, edge_id=99, properties={"id": "USES:PR-18:P-77", "units_per_product": 3}
    )
    result = path_evidence(Path([part, product], [uses]))
    assert result.human_readable == "Part P-77 <-[USES]- Product PR-18"
    assert result.relationships[0].id == "USES:PR-18:P-77"
    assert result.relationships[0].source_id == "PR-18"
    assert result.relationships[0].target_id == "P-77"


def test_evidence_rejects_invented_endpoints_or_missing_stable_identity():
    source = Node(node_id=1, labels="Supplier", properties={"id": "S-04"})
    target = Node(node_id=2, labels="Part", properties={"id": "P-22"})
    with pytest.raises(GraphQueryError):
        relationship_evidence(Edge(1, "SUPPLIES", 3, properties={"id": "bad"}), source, target)
    with pytest.raises(GraphQueryError):
        relationship_evidence(Edge(1, "SUPPLIES", 2), source, target)
