"""Serialize actual graph objects, preserving stored edge directions and IDs."""

from falkordb.edge import Edge
from falkordb.node import Node
from falkordb.path import Path

from rippleproof.errors import GraphQueryError
from rippleproof.models import EvidenceNode, EvidencePath, EvidenceRelationship


def node_evidence(node: Node) -> EvidenceNode:
    if not node.labels or "id" not in node.properties:
        raise GraphQueryError("Graph node is missing its label or stable ID")
    return EvidenceNode(id=node.properties["id"], label=node.labels[0], properties=node.properties)


def relationship_evidence(edge: Edge, source: Node, target: Node) -> EvidenceRelationship:
    if "id" not in edge.properties or edge.src_node != source.id or edge.dest_node != target.id:
        raise GraphQueryError("Graph relationship has invalid identity or endpoints")
    return EvidenceRelationship(
        id=edge.properties["id"],
        type=edge.relation,
        source_id=source.properties["id"],
        target_id=target.properties["id"],
        properties=edge.properties,
    )


def path_evidence(path: Path) -> EvidencePath:
    raw_nodes = path.nodes()
    nodes = [node_evidence(node) for node in raw_nodes]
    by_native_id = {node.id: node for node in raw_nodes}
    relationships = [
        relationship_evidence(edge, by_native_id[edge.src_node], by_native_id[edge.dest_node])
        for edge in path.edges()
    ]
    readable = f"{nodes[0].label} {nodes[0].id}"
    for index, edge in enumerate(relationships):
        next_node = nodes[index + 1]
        arrow = (
            f" -[{edge.type}]-> " if edge.source_id == nodes[index].id else f" <-[{edge.type}]- "
        )
        readable += arrow + f"{next_node.label} {next_node.id}"
    return EvidencePath(nodes=nodes, relationships=relationships, human_readable=readable)
