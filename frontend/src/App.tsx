import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  Database,
  FileCheck2,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  Play,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import {
  api,
  isLoopback,
  safeReadRetry,
  sourceUnavailable,
} from "./api/client";
import type {
  DecisionRecord,
  EvidencePath,
  PrepareRequest,
  ScenarioRequest,
  ScenarioResponse,
} from "./api/contracts";
import {
  Badge,
  EmptyState,
  ErrorNotice,
  Modal,
  SectionHeading,
} from "./components/ui";
import { useMediaQuery } from "./lib/useMediaQuery";
import {
  calendar,
  initialPart,
  policyName,
  timestamp,
  validateScenario,
} from "./lib/format";
import { Overview } from "./features/overview/Overview";
import { ScenarioForm } from "./features/scenarios/ScenarioForm";
import { Comparison } from "./features/scenarios/Comparison";
import { OutcomeDetails } from "./features/scenarios/OutcomeDetails";
import {
  EvidenceExplorer,
  pathKey,
  type EvidenceFact,
} from "./features/evidence/EvidenceExplorer";
import { MaterialInspector } from "./features/evidence/MaterialInspector";
import { AgentPanel } from "./features/agent/AgentPanel";
import { DecisionReview } from "./features/decisions/DecisionReview";
import { Ledger } from "./features/decisions/Ledger";

const DEMO_INPUT: ScenarioRequest = {
  supplier_id: "S-04",
  as_of: "2026-10-15",
  outage_start: "2026-10-16",
  outage_end_exclusive: "2026-10-24",
  include_mitigation: true,
};
type Page = "overview" | "workbench" | "decisions";
const readRoute = () => {
  const segments = window.location.hash.replace(/^#\//, "").split("/");
  const page: Page =
    segments[0] === "workbench" || segments[0] === "decisions"
      ? segments[0]
      : "overview";
  return {
    page,
    decisionId:
      page === "decisions" && /^D-[a-f0-9]{24}$/.test(segments[1] ?? "")
        ? segments[1]
        : undefined,
  };
};

export default function App() {
  const queryClient = useQueryClient();
  const [route, setRoute] = useState(readRoute);
  const [draft, setDraft] = useState<ScenarioRequest>(DEMO_INPUT);
  const [calculation, setCalculation] = useState<{
    result: ScenarioResponse;
    readAt: number;
  } | null>(null);
  const [pending, setPending] = useState(false);
  const [calculationError, setCalculationError] = useState<unknown>(null);
  const [failureAt, setFailureAt] = useState(0);
  const [selectedPart, setSelectedPart] = useState("");
  const [selectedPathKey, setSelectedPathKey] = useState("");
  const [inspected, setInspected] = useState<EvidenceFact | null>(null);
  const [policy, setPolicy] = useState("cost_first");
  const [agentOpen, setAgentOpen] = useState(false);
  const [review, setReview] = useState<PrepareRequest | null>(null);
  const [notification, setNotification] = useState("");
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [mobileInspectorOpen, setMobileInspectorOpen] = useState(false);
  const tablet = useMediaQuery("(min-width: 768px) and (max-width: 1279px)");
  const mobile = useMediaQuery("(max-width: 767px)");
  const controller = useRef<AbortController | null>(null);
  const evidenceSection = useRef<HTMLDivElement>(null);
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => api.health(signal),
    refetchInterval: 10000,
    retry: safeReadRetry,
  });
  const summary = useQuery({
    queryKey: ["summary"],
    queryFn: ({ signal }) => api.summary(signal),
    refetchInterval: 15000,
    retry: safeReadRetry,
  });
  const ready =
    health.isSuccess &&
    !health.isError &&
    health.data.status === "ready" &&
    summary.isSuccess &&
    !summary.isError &&
    health.dataUpdatedAt > failureAt;
  const graphEmpty =
    health.data?.graph_exists === false || summary.data?.node_count === 0;
  const usable = ready && !graphEmpty && health.data?.graph_exists === true;
  const result = usable ? calculation?.result : undefined;
  const impact = useQuery({
    queryKey: ["impact", draft.supplier_id],
    queryFn: ({ signal }) => api.impact(draft.supplier_id, signal),
    enabled: usable && /^S-[0-9]{2,5}$/.test(draft.supplier_id),
    retry: safeReadRetry,
  });
  const paths = useMemo(
    () =>
      !usable
        ? []
        : (result?.dependency_paths ??
          impact.data?.paths.map((path) => path.evidence) ??
          []),
    [usable, result, impact.data],
  );
  const selectedPath =
    paths.find((path) => pathKey(path) === selectedPathKey) ??
    paths.find((path) => path.nodes[1]?.id === selectedPart) ??
    paths[0];
  const focusedPart = selectedPart || selectedPath?.nodes[1]?.id || "";
  const suppliers = useMemo(
    () =>
      result
        ? Object.values(result.evidence_nodes).filter(
            (node) => node.label === "Supplier",
          )
        : (paths[0]?.nodes.filter((node) => node.label === "Supplier") ?? []),
    [result, paths],
  );
  const supplier = suppliers.find((node) => node.id === draft.supplier_id);

  useEffect(() => {
    const changed = () => {
      setRoute(readRoute());
      setAgentOpen(false);
      setReview(null);
      setInspectorOpen(false);
    };
    window.addEventListener("hashchange", changed);
    return () => {
      window.removeEventListener("hashchange", changed);
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (health.isError || summary.isError) {
      setCalculation(null);
      setInspected(null);
    }
  }, [health.isError, summary.isError]);
  useEffect(() => {
    document.title = `${route.page === "overview" ? "Overview" : route.page === "workbench" ? "Scenario Workbench" : "Decision Ledger"} · RippleProof`;
    window.scrollTo({ top: 0, behavior: "instant" });
    document.getElementById("main-content")?.focus({ preventScroll: true });
  }, [route.page]);

  const navigate = (page: Page, id?: string) => {
    window.location.hash = `/${page}${id ? `/${id}` : ""}`;
  };
  function changeDraft(value: ScenarioRequest) {
    controller.current?.abort();
    setPending(false);
    setDraft(value);
    setCalculation(null);
    setCalculationError(null);
    setInspected(null);
    setSelectedPathKey("");
    setSelectedPart("");
    setReview(null);
    setAgentOpen(false);
    setNotification("");
  }
  function invalidateSource() {
    setCalculation(null);
    setInspected(null);
  }
  function failedSource(error: unknown) {
    if (sourceUnavailable(error)) {
      setCalculation(null);
      setFailureAt(Date.now());
      void queryClient.invalidateQueries({ queryKey: ["health"] });
      void queryClient.invalidateQueries({ queryKey: ["summary"] });
    }
  }
  async function runScenario() {
    if (Object.keys(validateScenario(draft)).length) return;
    controller.current?.abort();
    const operation = new AbortController();
    controller.current = operation;
    setPending(true);
    setCalculation(null);
    setCalculationError(null);
    setInspected(null);
    setNotification("");
    try {
      const response = await api.simulate(draft, operation.signal);
      if (operation.signal.aborted) return;
      setCalculation({ result: response, readAt: Date.now() });
      const part = initialPart(response);
      setSelectedPart(part);
      const path =
        response.dependency_paths.find((path) => path.nodes[1]?.id === part) ??
        response.dependency_paths[0];
      setSelectedPathKey(path ? pathKey(path) : "");
      setPolicy(
        response.mitigation_plans.find((plan) => plan.selected)?.id ??
          "cost_first",
      );
    } catch (error) {
      if (!operation.signal.aborted) {
        setCalculationError(error);
        failedSource(error);
      }
    } finally {
      if (controller.current === operation) setPending(false);
    }
  }
  const selectPath = useCallback((path: EvidencePath) => {
    setSelectedPathKey(pathKey(path));
    setSelectedPart(path.nodes[1]?.id ?? "");
    setInspected(null);
  }, []);
  function selectPart(part: string) {
    setSelectedPart(part);
    setInspected(null);
    const path = paths.find((path) => path.nodes[1]?.id === part);
    if (path) setSelectedPathKey(pathKey(path));
  }
  function focusOrder(id: string) {
    const part = result?.disrupted.orders
      .find((order) => order.order_id === id)
      ?.materials.find(
        (material) => (material.shortfall_quantity ?? 0) > 0,
      )?.part_id;
    const path =
      paths.find(
        (path) => path.nodes.at(-1)?.id === id && path.nodes[1]?.id === part,
      ) ?? paths.find((path) => path.nodes.at(-1)?.id === id);
    if (path) selectPath(path);
    evidenceSection.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "start",
    });
  }
  function inspectFact(fact: EvidenceFact) {
    setInspected(fact);
    if (tablet) setInspectorOpen(true);
    if (mobile) setMobileInspectorOpen(true);
  }
  function inspectRef(ref: string) {
    const fact =
      result?.evidence_relationships[ref] ?? result?.evidence_nodes[ref];
    if (fact) inspectFact(fact);
  }
  function saved(record: DecisionRecord, checked?: ScenarioResponse) {
    void queryClient.invalidateQueries({ queryKey: ["decisions"] });
    void queryClient.invalidateQueries({ queryKey: ["summary"] });
    if (checked) setCalculation({ result: checked, readAt: Date.now() });
    setNotification(
      `Internal record ${record.decision_id} saved. No purchase was placed.`,
    );
  }
  const title =
    route.page === "overview"
      ? "Overview"
      : route.page === "workbench"
        ? "Scenario Workbench"
        : "Decision Ledger";
  const connectionError = health.error ?? summary.error;
  const inspector = (
    <MaterialInspector
      result={result}
      selectedPart={focusedPart}
      selectedOrder={
        selectedPath?.nodes[1]?.id === focusedPart
          ? selectedPath.nodes.at(-1)?.id
          : undefined
      }
      asOf={draft.as_of}
      ready={usable}
      onPart={selectPart}
      inspected={inspected}
      onInspect={inspectFact}
      clearInspect={() => setInspected(null)}
    />
  );
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        Skip to content
      </a>
      <aside className="sidebar">
        <a
          href="#/overview"
          className="brand"
          aria-label="RippleProof Decision intelligence overview"
        >
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <path d="M7 24V8h9a6 6 0 0 1 0 12h-4m5-1 8 5" />
            <circle cx="7" cy="24" r="2" />
          </svg>
          <span>
            RippleProof <small>Decision intelligence</small>
          </span>
        </a>
        <span className="nav-caption">Workspace</span>
        <nav aria-label="Primary navigation">
          {[
            {
              page: "overview" as const,
              label: "Overview",
              Icon: LayoutDashboard,
            },
            {
              page: "workbench" as const,
              label: "Scenario Workbench",
              Icon: GitBranch,
            },
            {
              page: "decisions" as const,
              label: "Decision Ledger",
              Icon: FileCheck2,
            },
          ].map(({ page, label, Icon }) => (
            <a
              key={page}
              href={`#/${page}`}
              aria-label={label}
              aria-current={route.page === page ? "page" : undefined}
              className={route.page === page ? "nav-active" : ""}
            >
              <Icon size={18} />
              <span>{label}</span>
              {route.page === page && <i />}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="synthetic-badge">
            <FlaskConical size={14} />
            Synthetic decision demo
          </span>
          <p>
            Evidence first.
            <br />
            Human decisions, always.
          </p>
          <div className="powered-by">
            <Database size={13} />
            Canonical data in FalkorDB
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> <strong>{title}</strong>
          </div>
          <div className="topbar-meta">
            <span
              className={`connection ${ready ? "connection-ready" : health.isError || summary.isError || failureAt > health.dataUpdatedAt ? "connection-error" : ""}`}
              role="status"
            >
              <i />
              {ready
                ? health.data?.graph_exists
                  ? "Backend ready"
                  : "Backend ready · graph empty"
                : health.isPending
                  ? "Checking backend"
                  : "Backend unavailable"}
            </span>
            <span className="scope-label" title={summary.data?.graph}>
              <Database size={13} />
              {ready ? summary.data?.graph : "Source offline"}
            </span>
            <span className="local-context">
              {isLoopback(window.location.hostname)
                ? "Local demo"
                : "Read-only origin"}
            </span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          {!!connectionError && (
            <div className="global-notice">
              <ErrorNotice
                error={connectionError}
                onRetry={() => {
                  void health.refetch();
                  void summary.refetch();
                }}
              />
            </div>
          )}
          {ready && graphEmpty && (
            <div className="global-notice">
              <p className="notice">
                The backend is reachable, but no operational graph exists. No
                fixture data is substituted. Ask the local operator to
                initialize a fresh graph.
              </p>
            </div>
          )}
          {route.page === "overview" && (
            <Overview
              summary={ready ? summary.data : undefined}
              result={result}
              ready={ready}
              readAt={calculation?.readAt}
              onWorkbench={() => navigate("workbench")}
            />
          )}
          {route.page === "decisions" && (
            <Ledger
              currentScenario={result?.scenario_id}
              selectedId={route.decisionId}
              onSelect={(id) => navigate("decisions", id)}
              onWorkbench={() => navigate("workbench")}
            />
          )}
          {route.page === "workbench" && (
            <div className="page workbench-page">
              <div className="page-title workbench-title">
                <div>
                  <span className="eyebrow">Scenario workbench</span>
                  <h1>See the ripple. Test the response.</h1>
                  <p>
                    One connected source. Every material constraint in view.
                  </p>
                </div>
                <button
                  className="secondary-button"
                  disabled={
                    !usable || !!Object.keys(validateScenario(draft)).length
                  }
                  onClick={() => setAgentOpen(true)}
                >
                  <Play size={15} />
                  Guided MCP tools
                </button>
              </div>
              {result ? (
                <div className="active-scenario">
                  <div className="scenario-marker">
                    <Activity size={20} />
                  </div>
                  <div>
                    <span className="eyebrow">Evaluated disruption</span>
                    <strong>
                      {result.request.supplier_id} <span>Supplier outage</span>
                    </strong>
                  </div>
                  <div className="active-window">
                    <span>
                      {calendar(result.request.outage_start)} →{" "}
                      {calendar(result.request.outage_end_exclusive)}
                    </span>
                    <small>
                      End exclusive · as of {calendar(result.request.as_of)}
                    </small>
                  </div>
                  <div className="active-risk">
                    <Badge tone="risk">
                      {result.newly_at_risk_orders.length} newly at risk
                    </Badge>
                    <span>
                      {result.dependent_orders.length} connected orders
                    </span>
                  </div>
                  <button
                    className="icon-button"
                    aria-label="Rerun current scenario"
                    title="Rerun current scenario"
                    onClick={() => void runScenario()}
                  >
                    <RefreshCw size={16} />
                  </button>
                </div>
              ) : (
                <div className="scenario-context">
                  <FlaskConical size={16} />
                  <span>
                    Start with the synthetic reference scenario, or change the
                    inputs. Evidence is read from FalkorDB; risk is calculated
                    on request.
                  </span>
                </div>
              )}
              {!!calculationError && (
                <ErrorNotice
                  error={calculationError}
                  onRetry={usable ? () => void runScenario() : undefined}
                />
              )}
              {!!notification && (
                <p className="notice notice-positive" role="status">
                  {notification}
                </p>
              )}
              <div className="workbench-grid" ref={evidenceSection}>
                <ScenarioForm
                  draft={draft}
                  onChange={changeDraft}
                  onRun={() => void runScenario()}
                  onCancel={() => {
                    controller.current?.abort();
                    setPending(false);
                  }}
                  pending={pending}
                  suppliers={suppliers}
                  supplier={supplier}
                  ready={usable}
                />
                {mobile && result && (
                  <div className="mobile-comparison">
                    <span className="eyebrow">
                      Calculated material coverage
                    </span>
                    <Comparison result={result} />
                  </div>
                )}
                <div className="evidence-column">
                  {impact.isError && !result && usable && (
                    <ErrorNotice
                      error={impact.error}
                      onRetry={() => void impact.refetch()}
                    />
                  )}
                  <EvidenceExplorer
                    paths={paths}
                    result={result}
                    selectedPath={selectedPath}
                    onPath={selectPath}
                    onInspect={inspectFact}
                    inspectedId={inspected?.id}
                  />
                </div>
                {tablet ? (
                  <div className="inspector-launch panel">
                    <div>
                      <span className="eyebrow">
                        Material and evidence inspector
                      </span>
                      <strong>
                        {focusedPart || "Select a source"} · Constraints and
                        source properties
                      </strong>
                    </div>
                    <button
                      className="secondary-button"
                      onClick={() => setInspectorOpen(true)}
                    >
                      Open material inspector <ArrowRight size={14} />
                    </button>
                  </div>
                ) : mobile ? (
                  <details
                    className="mobile-inspector"
                    open={mobileInspectorOpen}
                    onToggle={(event) =>
                      setMobileInspectorOpen(event.currentTarget.open)
                    }
                  >
                    <summary>
                      Material constraints and source properties ·{" "}
                      {focusedPart || "Select a part"}
                    </summary>
                    {inspector}
                  </details>
                ) : (
                  inspector
                )}
              </div>
              {result ? (
                <>
                  <SectionHeading
                    eyebrow="Scenario outcomes"
                    title="From exposure to material recovery."
                  >
                    <Badge tone={result.incomplete_data ? "risk" : "positive"}>
                      {result.incomplete_data ? (
                        "Incomplete source data"
                      ) : (
                        <>
                          <ShieldCheck size={12} />
                          Modeled facts verified
                        </>
                      )}
                    </Badge>
                  </SectionHeading>
                  {!mobile && <Comparison result={result} />}
                  <section className="plan-selection panel">
                    <div>
                      <span className="eyebrow">Internal decision review</span>
                      <h2>Choose the plan to put on record.</h2>
                      <p>
                        Comparison above uses the engine-selected plan. Other
                        policies are freshly recalculated for review.
                      </p>
                    </div>
                    <div>
                      <label className="field">
                        <span>Policy to review</span>
                        <select
                          value={policy}
                          onChange={(event) => setPolicy(event.target.value)}
                          disabled={!result.request.include_mitigation}
                        >
                          {result.mitigation_plans.map((plan) => (
                            <option key={plan.id} value={plan.id}>
                              {policyName(plan.id)} ·{" "}
                              {plan.restored_orders.length} restored
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        className="primary-button"
                        disabled={
                          !result.request.include_mitigation ||
                          result.incomplete_data
                        }
                        onClick={() =>
                          setReview({
                            scenario: result.request,
                            mitigation_plan_id: policy,
                          })
                        }
                      >
                        Review internal plan <ArrowRight size={16} />
                      </button>
                    </div>
                  </section>
                  <OutcomeDetails
                    key={result.scenario_id}
                    result={result}
                    onOrder={focusOrder}
                  />
                  <p className="snapshot-footnote">
                    Analysis read {timestamp(calculation!.readAt)} ·{" "}
                    {result.scenario_id} · Material coverage, not guaranteed
                    shipping.
                  </p>
                </>
              ) : (
                <section className="panel analysis-empty">
                  <EmptyState
                    title={
                      pending
                        ? "Calculating material coverage"
                        : "A connected path is the beginning, not the verdict."
                    }
                  >
                    {pending
                      ? "The backend is allocating shared stock, adjusting planned arrivals and checking alternative constraints."
                      : "Run the scenario to reveal baseline, disruption, certified recovery and a proposed arrival schedule."}
                  </EmptyState>
                </section>
              )}
            </div>
          )}
        </main>
        <footer className="app-footer">
          <span>RippleProof · Supply Chain Decision Intelligence</span>
          <span>Graph evidence / deterministic constraints / human review</span>
        </footer>
      </div>
      {mobile && route.page === "workbench" && (
        <div
          className="mobile-action-bar"
          role="region"
          aria-label="Current scenario action"
        >
          <div>
            <strong>{draft.supplier_id || "Supplier outage"}</strong>
            <span>Current scenario inputs</span>
          </div>
          <button
            className="primary-button"
            disabled={
              !usable ||
              pending ||
              !!Object.keys(validateScenario(draft)).length
            }
            onClick={() => void runScenario()}
          >
            {pending ? "Calculating…" : "Evaluate outage"}
            <ArrowRight size={15} />
          </button>
        </div>
      )}
      {tablet && inspectorOpen && (
        <Modal
          title="Material and evidence inspector"
          onClose={() => setInspectorOpen(false)}
        >
          <div className="inspector-drawer">{inspector}</div>
        </Modal>
      )}
      {agentOpen && (
        <AgentPanel
          scenario={draft}
          scenarioId={result?.scenario_id}
          onClose={() => setAgentOpen(false)}
          onRef={inspectRef}
        />
      )}
      {review && (
        <DecisionReview
          request={review}
          onClose={() => setReview(null)}
          onSaved={saved}
          onLedger={(id) => {
            setReview(null);
            navigate("decisions", id);
          }}
          onSourceChanged={invalidateSource}
        />
      )}
    </div>
  );
}
