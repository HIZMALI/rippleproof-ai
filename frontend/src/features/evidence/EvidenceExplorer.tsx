import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { GitBranch, RotateCcw, ScanLine, Search } from "lucide-react";
import type {
  EvidenceNode,
  EvidencePath,
  EvidenceRelationship,
  ScenarioResponse,
} from "../../api/contracts";
import { Badge, EmptyState, Loading, Pagination } from "../../components/ui";

const GraphCanvas = lazy(() => import("./GraphCanvas"));
export type EvidenceFact = EvidenceNode | EvidenceRelationship;
export const pathKey = (path: EvidencePath): string =>
  path.relationships.map((r) => r.id).join("|");

export function EvidenceExplorer({
  paths,
  result,
  selectedPath,
  onPath,
  onInspect,
  inspectedId,
}: {
  paths: EvidencePath[];
  result?: ScenarioResponse;
  selectedPath?: EvidencePath;
  onPath: (path: EvidencePath) => void;
  onInspect: (fact: EvidenceFact) => void;
  inspectedId?: string;
}) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [offset, setOffset] = useState(0);
  const [fit, setFit] = useState(0);
  const filtered = useMemo(
    () =>
      paths.filter((path) => {
        const order = path.nodes.at(-1)?.id ?? "";
        const matchesFilter =
          filter === "all" ||
          (filter === "new"
            ? result?.newly_at_risk_orders
            : result?.restored_orders
          )?.includes(order);
        return (
          matchesFilter &&
          path.nodes.some((node) =>
            node.id.toLowerCase().includes(search.toLowerCase()),
          )
        );
      }),
    [paths, filter, search, result],
  );
  const visiblePath =
    selectedPath &&
    filtered.some((path) => pathKey(path) === pathKey(selectedPath))
      ? selectedPath
      : filtered[0];
  useEffect(() => {
    if (
      visiblePath &&
      (!selectedPath || pathKey(visiblePath) !== pathKey(selectedPath))
    )
      onPath(visiblePath);
  }, [visiblePath, selectedPath, onPath]);
  const order = visiblePath?.nodes.at(-1)?.id;
  const status = result?.disrupted.orders.find(
    (item) => item.order_id === order,
  )?.status;
  return (
    <section
      className="panel evidence-panel"
      aria-labelledby="evidence-heading"
    >
      <header className="panel-header">
        <div>
          <span className="eyebrow">Connected evidence</span>
          <h2 id="evidence-heading">Follow the material path</h2>
        </div>
        <div className="inline-actions">
          <button
            className="icon-button"
            title="Fit evidence graph"
            aria-label="Fit evidence graph"
            onClick={() => setFit((v) => v + 1)}
            disabled={!visiblePath}
          >
            <ScanLine size={17} />
          </button>
          <button
            className="icon-button"
            title="Reset evidence view"
            aria-label="Reset evidence view"
            onClick={() => {
              setSearch("");
              setFilter("all");
              setOffset(0);
              setFit((v) => v + 1);
            }}
          >
            <RotateCcw size={16} />
          </button>
        </div>
      </header>
      <div className="evidence-toolbar">
        <label className="search-field">
          <Search size={14} />
          <span className="sr-only">Search evidence</span>
          <input
            value={search}
            placeholder="Find S-04, P-22, O-105…"
            onChange={(event) => {
              setSearch(event.target.value);
              setOffset(0);
            }}
          />
        </label>
        <div className="filter-chips" aria-label="Evidence filters">
          {[
            { id: "all", label: "All paths" },
            { id: "new", label: "Newly at risk" },
            { id: "restored", label: "Restored" },
          ].map((item) => (
            <button
              key={item.id}
              disabled={item.id !== "all" && !result}
              aria-pressed={filter === item.id}
              onClick={() => {
                setFilter(item.id);
                setOffset(0);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
      {visiblePath ? (
        <>
          <div className="graph-stage">
            <div className="graph-scope">
              <Badge tone="accent">
                <GitBranch size={12} />
                Selected chain
              </Badge>
              <span>
                {visiblePath.nodes.length} source nodes ·{" "}
                {visiblePath.relationships.length} edges
              </span>
            </div>
            <Suspense fallback={<Loading label="Loading evidence canvas…" />}>
              <GraphCanvas
                path={visiblePath}
                selectedId={inspectedId}
                onSelect={onInspect}
                fitVersion={fit}
                orderStatus={status}
              />
            </Suspense>
            <div className="graph-legend">
              <span>
                <i className="legend-supply" />
                SUPPLIES
              </span>
              <span>
                <i className="legend-uses" />
                USES
              </span>
              <span>
                <i className="legend-contains" />
                CONTAINS
              </span>
            </div>
          </div>
          <div className="source-reference-list">
            <span className="eyebrow">
              Keyboard-accessible source references
            </span>
            <div>
              {visiblePath.nodes.map((node) => (
                <button
                  key={node.id}
                  className="source-ref"
                  onClick={() => onInspect(node)}
                  aria-pressed={inspectedId === node.id}
                >
                  {node.id}
                  <span>{node.label}</span>
                </button>
              ))}
              {visiblePath.relationships.map((edge) => (
                <button
                  key={edge.id}
                  className="edge-ref"
                  onClick={() => onInspect(edge)}
                  aria-pressed={inspectedId === edge.id}
                >
                  {edge.type}
                  <span className="sr-only"> {edge.id}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="path-list" aria-label="Connected evidence paths">
            {filtered.slice(offset, offset + 3).map((path) => (
              <button
                key={pathKey(path)}
                className={
                  pathKey(path) === pathKey(visiblePath)
                    ? "path-row selected"
                    : "path-row"
                }
                onClick={() => onPath(path)}
              >
                <span className="path-order">{path.nodes.at(-1)?.id}</span>
                <span>
                  {path.nodes[0]?.id} <span aria-hidden="true">→</span>{" "}
                  {path.nodes[1]?.id} <span aria-hidden="true">←</span>{" "}
                  {path.nodes[2]?.id}
                </span>
                <span className="path-status">
                  {result
                    ? result.newly_at_risk_orders.includes(
                        path.nodes.at(-1)?.id ?? "",
                      )
                      ? "New risk"
                      : "Connected"
                    : "Dependency"}
                </span>
              </button>
            ))}
          </div>
          <Pagination
            total={filtered.length}
            offset={offset}
            size={3}
            onChange={setOffset}
            label="paths"
          />
        </>
      ) : (
        <EmptyState
          title={
            paths.length
              ? "No paths match this filter"
              : "No connected order paths"
          }
        >
          {paths.length
            ? "Try another identifier or reset the evidence view."
            : "Inspect a supplier to load its actual dependency evidence. An empty path set does not imply material risk."}
        </EmptyState>
      )}
      <p className="panel-footnote">
        Stored edge direction is preserved. A connected order is not
        automatically late.
      </p>
    </section>
  );
}
