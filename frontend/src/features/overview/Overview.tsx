import {
  ArrowRight,
  Database,
  Fingerprint,
  GitBranch,
  ShieldCheck,
} from "lucide-react";
import type { GraphSummary, ScenarioResponse } from "../../api/contracts";
import { Badge, EmptyState, SectionHeading } from "../../components/ui";
import {
  calendar,
  operationalCounts,
  timestamp,
  units,
} from "../../lib/format";
import { Comparison } from "../scenarios/Comparison";

export function Overview({
  summary,
  result,
  readAt,
  ready,
  onWorkbench,
}: {
  summary?: GraphSummary;
  result?: ScenarioResponse;
  readAt?: number;
  ready: boolean;
  onWorkbench: () => void;
}) {
  const counts = summary ? operationalCounts(summary) : null;
  return (
    <div className="page overview-page">
      <div className="page-title">
        <div>
          <span className="eyebrow">Operations / command center</span>
          <h1>
            Decisions that hold up
            <br className="desktop-break" /> under disruption.
          </h1>
          <p>Trace the dependency. Test the recovery. Keep the proof.</p>
        </div>
        <Badge tone="accent">Graph Hacks 2026 · Track 1</Badge>
      </div>
      <div className="overview-grid">
        <section className="panel overview-main">
          <div className="panel-topline">
            <span className="eyebrow">Material intelligence</span>
            <GitBranch size={20} />
          </div>
          {result ? (
            <>
              <Badge tone="risk">Evaluated supplier outage</Badge>
              <h2>
                {result.request.supplier_id}
                <span>Supply interruption</span>
              </h2>
              <p className="hero-window">
                {calendar(result.request.outage_start)} <ArrowRight size={18} />{" "}
                {calendar(result.request.outage_end_exclusive)}{" "}
                <small>end exclusive</small>
              </p>
              <p>
                {result.dependent_orders.length} connected open orders.{" "}
                {result.newly_at_risk_orders.length} newly at risk after stock
                and receipt allocation.
              </p>
              <button className="primary-button" onClick={onWorkbench}>
                Open this analysis <ArrowRight size={16} />
              </button>
            </>
          ) : (
            <>
              <h2>
                Follow the impact.
                <br />
                <span>Before you commit.</span>
              </h2>
              <p>
                Connect a supplier outage to actual materials and orders.
                Compare a graph-backed recovery plan with its sources in view.
              </p>
              <button className="primary-button" onClick={onWorkbench}>
                Open scenario workbench <ArrowRight size={16} />
              </button>
              <p className="subtle-caption">
                Synthetic reference inputs are ready. Results are calculated
                only when you run.
              </p>
            </>
          )}
          <div className="process-line">
            <span>
              <i>01</i>Trace
            </span>
            <ArrowRight size={13} />
            <span>
              <i>02</i>Compare
            </span>
            <ArrowRight size={13} />
            <span>
              <i>03</i>Review
            </span>
          </div>
        </section>
        <aside className="panel source-panel">
          <div className="panel-topline">
            <span className="eyebrow">Canonical data source</span>
            <Database size={18} />
          </div>
          <h2>Connected in FalkorDB</h2>
          <p className="muted">
            Operational facts and internal decision memory, counted separately.
          </p>
          {counts && ready ? (
            <>
              <div className="source-counts">
                <div>
                  <strong>{units(counts.nodes)}</strong>
                  <span>operational nodes</span>
                </div>
                <div>
                  <strong>{units(counts.edges)}</strong>
                  <span>operational edges</span>
                </div>
              </div>
              <dl className="source-types">
                {[
                  "Supplier",
                  "Part",
                  "Product",
                  "Order",
                  "Certificate",
                  "InboundShipment",
                ].map((type) => (
                  <div key={type}>
                    <dt>
                      {type === "InboundShipment"
                        ? "Inbound shipments"
                        : `${type}s`}
                    </dt>
                    <dd>{units(summary?.nodes_by_label[type] ?? 0)}</dd>
                  </div>
                ))}
              </dl>
              <div className="physical-counts">
                Physical graph: {units(summary?.node_count)} nodes /{" "}
                {units(summary?.relationship_count)} edges
                <span>
                  {units(summary?.nodes_by_label.Decision ?? 0)} decisions ·{" "}
                  {units(summary?.nodes_by_label.Evidence ?? 0)} archived
                  snapshots
                </span>
              </div>
            </>
          ) : (
            <p className="notice">
              {ready
                ? "Reading graph counts…"
                : "Graph counts are unavailable until the backend responds."}
            </p>
          )}
        </aside>
      </div>
      <section>
        <SectionHeading
          eyebrow="Cause and effect"
          title="A fair comparison, one shared inventory."
        />
        {result ? (
          <Comparison result={result} compact />
        ) : (
          <div className="panel setup-comparison">
            <EmptyState title="No scenario has been evaluated">
              Run an outage scenario to compare baseline, disruption and
              mitigation. No forecast figures are preloaded.
            </EmptyState>
          </div>
        )}
      </section>
      <div className="overview-assurance">
        <div>
          <GitBranch size={20} />
          <h3>Evidence you can follow</h3>
          <p>
            {result
              ? `${result.dependency_paths.length} connected paths from the actual graph. Select any path to inspect its source properties.`
              : "Supplier → part ← product ← order. Connected paths are returned by the graph, with stable source references."}
          </p>
        </div>
        <div>
          <ShieldCheck size={20} />
          <h3>Constraints before confidence</h3>
          <p>
            Shared stock, booked capacity, lead days and certificates valid on
            arrival. Unknown data stays unknown.
          </p>
        </div>
        <div>
          <Fingerprint size={20} />
          <h3>A human decision boundary</h3>
          <p>
            Review a fresh computed plan before approving an internal record. No
            purchase is placed and no supplier is contacted.
          </p>
        </div>
      </div>
      {readAt && result && (
        <p className="snapshot-footnote">
          Current analysis read {timestamp(readAt)} · {result.scenario_id}
        </p>
      )}
    </div>
  );
}
