import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, CircleAlert, GitBranch, Play, Square } from "lucide-react";
import { api, ApiError, isLoopback } from "../../api/client";
import type { AgentResponse, ScenarioRequest } from "../../api/contracts";
import { Badge, ErrorNotice, Loading, Modal } from "../../components/ui";
import { codeLabel, timestamp } from "../../lib/format";

export function AgentPanel({
  scenario,
  scenarioId,
  onClose,
  onRef,
}: {
  scenario: ScenarioRequest;
  scenarioId?: string;
  onClose: () => void;
  onRef: (ref: string) => void;
}) {
  const [question, setQuestion] = useState(
    "Which orders need help, why, and what internal plan restores them?",
  );
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const [authorized, setAuthorized] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const [activeMode, setActiveMode] = useState<"guided" | "agent">("guided");
  const [executionKind, setExecutionKind] = useState("disabled");
  const running = useRef(false);
  const capability = useQuery({
    queryKey: ["agent-capabilities"],
    queryFn: ({ signal }) => api.capabilities(signal),
    retry: false,
    staleTime: 0,
  });
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function run(mode: "guided" | "agent" = "guided") {
    if (
      running.current ||
      (mode === "agent" &&
        (!authorized ||
          attempted ||
          !capability.data?.agent_available ||
          !isLoopback(window.location.hostname)))
    )
      return;
    running.current = true;
    setActiveMode(mode);
    controller.current?.abort();
    controller.current = new AbortController();
    setPending(true);
    setError(null);
    setResult(null);
    setCancelled(false);
    try {
      if (mode === "agent") {
        // Recheck current server configuration and graph before any model intent.
        const current = await api.capabilities(controller.current.signal);
        const health = await api.health(controller.current.signal);
        if (
          !current.agent_available ||
          health.status !== "ready" ||
          !health.graph_exists
        )
          throw new ApiError(503, "provider_not_authorized");
        setAttempted(true);
        setExecutionKind(current.execution_kind);
        setAuthorized(false);
        setResult(
          await api.agent(
            question.trim(),
            scenario,
            current,
            controller.current.signal,
          ),
        );
      } else
        setResult(
          await api.guided(
            question.trim(),
            scenario,
            controller.current.signal,
          ),
        );
    } catch (error) {
      if (controller.current.signal.aborted) setCancelled(true);
      else setError(error);
    } finally {
      running.current = false;
      setPending(false);
    }
  }
  const sameSnapshot = !!scenarioId && result?.scenario_id === scenarioId;
  return (
    <Modal
      title="Guided graph walkthrough"
      subtitle="An operations trace, backed by actual MCP tools."
      onClose={onClose}
      wide
    >
      <div className="notice notice-accent">
        <GitBranch size={19} />
        <div>
          <strong>
            {result?.mode === "agent"
              ? executionKind === "controlled"
                ? "Controlled provider simulation · real MCP tools"
                : "Agent provider response · real MCP tools"
              : activeMode === "agent"
                ? pending
                  ? "Explicit agent attempt · awaiting verified response"
                  : "Agent attempt · no verified result"
                : "Guided walkthrough · real MCP tools"}
            {result ? ` · ${result.model_requests} model calls` : ""}
          </strong>
          <p>
            {result?.mode === "agent"
              ? `Provider: ${result.provider}. Tool actions and facts are verified by the backend. No purchase or approval tool exists.`
              : "A deterministic tool sequence. This is not an autonomous AI agent."}
          </p>
        </div>
      </div>
      <label className="field">
        <span>Planning question</span>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={2000}
          rows={2}
          disabled={pending}
        />
      </label>
      <div className="agent-action">
        <span className="small muted">
          {scenario.supplier_id} · {scenario.outage_start} →{" "}
          {scenario.outage_end_exclusive} (exclusive)
        </span>
        {pending ? (
          <button
            className="secondary-button"
            onClick={() => controller.current?.abort()}
          >
            <Square size={14} />
            Stop waiting
          </button>
        ) : (
          <button
            className="primary-button"
            onClick={() => void run()}
            disabled={!question.trim()}
          >
            <Play size={15} />
            Run guided tools
          </button>
        )}
      </div>
      {pending && (
        <Loading
          label={
            activeMode === "agent"
              ? "Waiting for bounded agent execution. No progress or tool choices are simulated…"
              : "Executing MCP tools against the graph. Trace appears when the backend returns…"
          }
        />
      )}
      {cancelled && (
        <p className="notice" role="status">
          Stopped waiting. Read-only tools may finish on the backend; no
          approval was requested.{" "}
          {activeMode === "agent" &&
            "Cancelling the wait does not guarantee cancellation of a provider charge."}
        </p>
      )}
      {!!error && (
        <ErrorNotice
          error={error}
          onRetry={activeMode === "guided" ? () => void run() : undefined}
        />
      )}
      {result && (
        <>
          <section className="agent-answer">
            <Badge tone={result.status === "completed" ? "positive" : "risk"}>
              {codeLabel(result.status)}
            </Badge>
            <h3>Computed response</h3>
            <p>{result.response}</p>
            {!sameSnapshot && (
              <p className="notice">
                The source revision differs from the open analysis. Rerun the
                scenario before inspecting these references as current.
              </p>
            )}
          </section>
          <ol className="tool-timeline">
            {(result.tool_trace ?? []).map((trace, index) => (
              <li key={`${trace.name}-${index}`}>
                <span className="timeline-step">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <div className="tool-step-title">
                    <h4>{codeLabel(trace.name)}</h4>
                    <Badge tone={trace.status === "ok" ? "positive" : "risk"}>
                      {trace.status === "ok" ? (
                        <Check size={11} />
                      ) : (
                        <CircleAlert size={11} />
                      )}
                      {trace.status}
                    </Badge>
                  </div>
                  <code>{trace.name}</code>
                  <p className="small muted">
                    {timestamp(trace.started_at)} ·{" "}
                    {Math.max(
                      0,
                      Date.parse(trace.finished_at) -
                        Date.parse(trace.started_at),
                    )}{" "}
                    ms · {trace.output_bytes.toLocaleString()} bytes
                  </p>
                  <div className="trace-refs">
                    {trace.evidence_refs.map((ref) => (
                      <button
                        key={ref}
                        className="edge-ref"
                        disabled={!sameSnapshot}
                        onClick={() => {
                          onRef(ref);
                          onClose();
                        }}
                      >
                        {ref}
                      </button>
                    ))}
                  </div>
                  <details>
                    <summary>Validated tool arguments and output hash</summary>
                    <pre>{JSON.stringify(trace.arguments, null, 2)}</pre>
                    <code className="hash-value">{trace.output_sha256}</code>
                  </details>
                </div>
              </li>
            ))}
          </ol>
          {(result.warnings ?? []).map((warning) => (
            <p className="notice" key={warning}>
              {warning}
            </p>
          ))}
          <details>
            <summary>Model assumptions and limitations</summary>
            <ul className="assumption-list">
              {(result.assumptions ?? []).map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          </details>
        </>
      )}
      <div className="provider-boundary">
        <CircleAlert size={17} />
        <div>
          <strong>
            {capability.data?.agent_available
              ? capability.data.execution_kind === "controlled"
                ? "Controlled provider simulation — not a remote LLM"
                : "Remote provider configured — separate authorization required"
              : "Real AI agent not configured for this interface"}
          </strong>
          <p>
            {capability.data?.agent_available
              ? "This configuration check makes no model call. Invoke only after the operator has separately approved provider, model, spend limit and number of runs. Resource bounds do not enforce a currency budget."
              : "Remote model calls are disabled. Provider setup and separately authorized real-provider verification remain operator actions. Guided MCP needs no API key."}
          </p>
          {!!capability.error && (
            <p>Capability unavailable. Agent invocation stays disabled.</p>
          )}
          {capability.data && (
            <p>
              Bounds: {capability.data.limits.max_model_requests} model requests
              · {capability.data.limits.max_tool_calls} tools ·{" "}
              {capability.data.limits.model_timeout_seconds}s per model request
              · {capability.data.limits.run_timeout_seconds}s per run ·{" "}
              {capability.data.limits.max_output_tokens_per_request} output
              tokens per request.{" "}
              {capability.data.model
                ? `Configured model: ${capability.data.model}.`
                : ""}
            </p>
          )}
          {capability.data?.agent_available && (
            <label className="checkbox-field review-ack">
              <input
                type="checkbox"
                checked={authorized}
                disabled={pending || attempted}
                onChange={(e) => setAuthorized(e.target.checked)}
              />
              <span>
                {capability.data.execution_kind === "controlled"
                  ? "I understand this is a controlled model simulator, not a remote LLM."
                  : "I have separate operator authorization for this remote model run."}
              </span>
            </label>
          )}
          <button
            className="secondary-button"
            disabled={
              pending ||
              attempted ||
              !authorized ||
              !capability.data?.agent_available ||
              capability.isError ||
              !question.trim() ||
              !isLoopback(window.location.hostname)
            }
            onClick={() => void run("agent")}
          >
            {capability.data?.execution_kind === "controlled"
              ? "Run controlled test agent"
              : "Run real agent"}
          </button>
          {attempted && (
            <p>
              One agent attempt was sent from this review. Check its outcome
              before starting another. Closing/reopening is not a server-side
              spend limit.
            </p>
          )}
          {!isLoopback(window.location.hostname) && (
            <p>
              Agent invocation is disabled on this origin. Use trusted
              localhost.
            </p>
          )}
        </div>
      </div>
    </Modal>
  );
}
