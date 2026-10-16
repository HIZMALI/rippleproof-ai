"""The only domain datastore boundary: the official FalkorDB client.

Connections and Graph/schema objects are scoped to an operation so requests do
not share mutable schema caches. No connection is attempted during app import.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from falkordb import FalkorDB
from falkordb.graph import Graph
from falkordb.node import Node
from falkordb.path import Path
from redis import ConnectionPool
from redis.backoff import NoBackoff
from redis.exceptions import RedisError, ResponseError
from redis.retry import Retry

from rippleproof import queries
from rippleproof.config import Settings
from rippleproof.errors import DatabaseUnavailable, EntityNotFound, GraphQueryError, OperationError
from rippleproof.models import GraphSummary

if TYPE_CHECKING:
    from rippleproof.seed_data import SyntheticDataset


@dataclass(frozen=True)
class AlternativeFacts:
    part: Node
    requirements: list[list[Any]]
    offers: list[list[Any]]


class GraphRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    @contextmanager
    def connect(self) -> Iterator[FalkorDB]:
        # Owning the pool also lets us close it if FalkorDB's constructor fails
        # during its server-mode probe. Bound every network attempt; no retries.
        pool = ConnectionPool(
            host=self.settings.host,
            port=self.settings.port,
            decode_responses=True,
            socket_connect_timeout=self.settings.connect_timeout_s,
            socket_timeout=self.settings.socket_timeout_s,
            retry=Retry(NoBackoff(), 0),
            max_connections=4,
            client_name="rippleproof-phase1",
        )
        try:
            with FalkorDB(connection_pool=pool) as db:
                yield db
        except ResponseError as exc:
            raise GraphQueryError("FalkorDB rejected a graph command") from exc
        except RedisError as exc:
            raise DatabaseUnavailable("FalkorDB is unavailable") from exc
        finally:
            pool.disconnect()

    def _read(
        self, graph: Graph, query: str, params: dict[str, Any] | None = None
    ) -> list[list[Any]]:
        if query not in queries.READ_QUERIES:
            raise ValueError("Query is not in the reviewed read allowlist")
        return graph.ro_query(
            query, params=params, timeout=self.settings.query_timeout_ms
        ).result_set

    def ready(self) -> bool:
        """GRAPH.LIST checks the graph module even before the first seed."""
        with self.connect() as db:
            exists = self.settings.graph in db.list_graphs()
            if exists:
                self._read(db.select_graph(self.settings.graph), queries.READINESS)
            return exists

    def snapshot_facts(self, supplier_id: str) -> tuple[list[Node], list[Any]]:
        """Fetch all simulation facts atomically in a single read-only query."""
        with self.connect() as db:
            if self.settings.graph not in db.list_graphs():
                raise EntityNotFound("Supplier", supplier_id)
            graph = db.select_graph(self.settings.graph)
            if not self._read(graph, queries.SUPPLIER_EXISTS, {"id": supplier_id}):
                raise EntityNotFound("Supplier", supplier_id)
            return self._operational_read(graph)

    def _operational_read(self, graph):
        nodes, edges = self._read(
            graph,
            queries.OPERATIONAL_SNAPSHOT,
            {
                "labels": sorted(queries.OPERATIONAL_LABELS),
                "types": sorted(queries.OPERATIONAL_RELATIONSHIPS),
            },
        )[0]
        if len(nodes) > 2000 or len(edges) > 4000:
            raise OperationError(
                413, "graph_budget_exceeded", "Operational graph exceeds demo limits"
            )
        return nodes, edges

    def operational_facts(self):
        with self.connect() as db:
            if self.settings.graph not in db.list_graphs():
                return [], []
            return self._operational_read(db.select_graph(self.settings.graph))

    def memory_node(self, identity: str, *, evidence=False):
        with self.connect() as db:
            if self.settings.graph not in db.list_graphs():
                return None
            rows = self._read(
                db.select_graph(self.settings.graph),
                queries.MEMORY_EVIDENCE if evidence else queries.DECISION,
                {"id": identity},
            )
            return rows[0][0].properties if rows else None

    def decision_history(self, scenario_id, offset, limit):
        with self.connect() as db:
            if self.settings.graph not in db.list_graphs():
                return 0, []
            graph = db.select_graph(self.settings.graph)
            params = {"scenario_id": scenario_id, "offset": offset, "limit": limit}
            total = self._read(graph, queries.DECISION_COUNT, params)[0][0]
            rows = self._read(graph, queries.DECISION_HISTORY, params)
            return total, [r[0].properties for r in rows]

    def save_decision(self, params):
        with self.connect() as db:
            result = (
                db.select_graph(self.settings.graph)
                .query(queries.SAVE_DECISION, params, self.settings.query_timeout_ms)
                .result_set
            )
            if len(result) != 1:
                raise OperationError(
                    409, "approval_conflict", "Approval identities or sources changed"
                )
            return result[0][0].properties

    def migrate_inbound(self, rows: list[dict[str, Any]]) -> GraphSummary:
        """Add missing shipment fixtures only; never replace existing facts."""
        with self.connect() as db:
            if self.settings.graph not in db.list_graphs():
                raise GraphQueryError("Seed the base graph before adding inbound shipments")
            graph = db.select_graph(self.settings.graph)
            # Preflight all endpoints so a missing base entity cannot silently
            # produce a partially populated migration.
            nodes, edges = self._read(graph, queries.SNAPSHOT)[0]
            suppliers = {n.properties.get("id") for n in nodes if "Supplier" in n.labels}
            parts = {n.properties.get("id") for n in nodes if "Part" in n.labels}
            if any(r["supplier_id"] not in suppliers or r["part_id"] not in parts for r in rows):
                raise GraphQueryError(
                    "Inbound migration requires its existing supplier/part endpoints"
                )
            by_id = {n.properties.get("id"): n for n in nodes}
            native_ids = {n.id: n.properties.get("id") for n in nodes}
            for row in rows:
                existing = by_id.get(row["properties"]["id"])
                if existing is None:
                    continue
                if "InboundShipment" not in existing.labels:
                    raise GraphQueryError("Migration ID collides with an existing entity")
                wrong_supplier = any(
                    e.relation == "FULFILLS"
                    and e.dest_node == existing.id
                    and native_ids[e.src_node] != row["supplier_id"]
                    for e in edges
                )
                wrong_part = any(
                    e.relation == "FOR_PART"
                    and e.src_node == existing.id
                    and native_ids[e.dest_node] != row["part_id"]
                    for e in edges
                )
                if wrong_supplier or wrong_part:
                    raise GraphQueryError("Existing shipment endpoints conflict with migration")
            graph.query(queries.MIGRATE_INBOUND, {"rows": rows}, self.settings.query_timeout_ms)
        return self.summary()

    def summary(self) -> GraphSummary:
        label_counts = dict.fromkeys(queries.NODE_LABELS, 0)
        relationship_counts = dict.fromkeys(queries.RELATIONSHIP_TYPES, 0)
        node_count = 0
        with self.connect() as db:
            if self.settings.graph in db.list_graphs():
                graph = db.select_graph(self.settings.graph)
                for labels, count in self._read(graph, queries.NODE_COUNTS):
                    node_count += count
                    for label in labels:
                        label_counts[label] = label_counts.get(label, 0) + count
                for relation, count in self._read(graph, queries.RELATIONSHIP_COUNTS):
                    relationship_counts[relation] = count
        return GraphSummary(
            graph=self.settings.graph,
            node_count=node_count,
            relationship_count=sum(relationship_counts.values()),
            nodes_by_label=label_counts,
            relationships_by_type=relationship_counts,
        )

    def impact_paths(self, supplier_id: str) -> list[Path]:
        with self.connect() as db:
            if self.settings.graph not in db.list_graphs():
                raise EntityNotFound("Supplier", supplier_id)
            graph = db.select_graph(self.settings.graph)
            if not self._read(graph, queries.SUPPLIER_EXISTS, {"id": supplier_id}):
                raise EntityNotFound("Supplier", supplier_id)
            return [
                row[0]
                for row in self._read(
                    graph,
                    queries.IMPACT_PATHS,
                    {"supplier_id": supplier_id, "order_status": "open"},
                )
            ]

    def alternative_facts(self, part_id: str) -> AlternativeFacts:
        with self.connect() as db:
            if self.settings.graph not in db.list_graphs():
                raise EntityNotFound("Part", part_id)
            graph = db.select_graph(self.settings.graph)
            parts = self._read(graph, queries.PART, {"id": part_id})
            if not parts:
                raise EntityNotFound("Part", part_id)
            return AlternativeFacts(
                part=parts[0][0],
                requirements=self._read(graph, queries.REQUIRED_CERTIFICATES, {"part_id": part_id}),
                offers=self._read(graph, queries.ALTERNATIVE_SUPPLIERS, {"part_id": part_id}),
            )

    def seed(self, dataset: SyntheticDataset) -> GraphSummary:
        """CLI-only writes; no seed or unrestricted query HTTP endpoint.

        Each batch is atomic on the server. An interrupted sequence can be
        repaired by rerunning; seeding should run before serving demo traffic.
        """
        with self.connect() as db:
            graph = db.select_graph(self.settings.graph)
            for label, query in queries.SEED_NODES.items():
                graph.query(
                    query,
                    params={"rows": dataset.nodes[label]},
                    timeout=self.settings.query_timeout_ms,
                )
            for relation, query in queries.SEED_RELATIONSHIPS.items():
                graph.query(
                    query,
                    params={"rows": dataset.relationships[relation]},
                    timeout=self.settings.query_timeout_ms,
                )
        return self.summary()
