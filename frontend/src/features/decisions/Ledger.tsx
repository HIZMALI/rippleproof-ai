import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, FileCheck2, Fingerprint, RefreshCw } from "lucide-react";
import { api, safeReadRetry } from "../../api/client";
import type { DecisionPreview } from "../../api/contracts";
import {
  Badge,
  EmptyState,
  ErrorNotice,
  Loading,
  Modal,
} from "../../components/ui";
import { decimal, policyName, timestamp } from "../../lib/format";
import { PlanDetails } from "./PlanDetails";

function RecordDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const record = useQuery({
    queryKey: ["decision", id],
    queryFn: ({ signal }) => api.decision(id, signal),
    retry: safeReadRetry,
  });
  const [current, setCurrent] = useState<DecisionPreview | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [evidence, setEvidence] = useState(false);
  async function check() {
    if (!record.data) return;
    setChecking(true);
    setError(null);
    try {
      setCurrent(
        await api.prepare({
          scenario: record.data.preview.scenario,
          mitigation_plan_id: record.data.preview.mitigation_plan_id,
        }),
      );
    } catch (error) {
      setError(error);
    } finally {
      setChecking(false);
    }
  }
  return (
    <Modal
      title="Persisted internal decision"
      subtitle="Historical planning record, retrieved from FalkorDB."
      onClose={onClose}
      wide
    >
      {record.isPending ? (
        <Loading />
      ) : record.isError ? (
        <ErrorNotice
          error={record.error}
          onRetry={() => void record.refetch()}
        />
      ) : (
        <>
          <div className="ledger-record-heading">
            <Badge tone="positive">
              <FileCheck2 size={12} />
              Approved internal record
            </Badge>
            <code>{record.data.decision_id}</code>
            <p>
              {timestamp(record.data.created_at)} · {record.data.operator_id}
            </p>
            <p>{record.data.rationale}</p>
          </div>
          <div className="record-freshness">
            <div>
              <Fingerprint size={18} />
              <p>
                {current
                  ? current.operational_fingerprint ===
                      record.data.preview.operational_fingerprint &&
                    current.plan_revision === record.data.preview.plan_revision
                    ? "Current source and plan revisions match this record."
                    : "Source or plan revision has changed. This record remains historical; prepare a new plan before another decision."
                  : "Historical snapshot. Current source validity has not been checked."}
              </p>
            </div>
            <button
              className="secondary-button"
              disabled={checking}
              onClick={() => void check()}
            >
              <RefreshCw size={14} />
              {checking ? "Checking…" : "Check current source"}
            </button>
          </div>
          {!!error && <ErrorNotice error={error} />}
          <PlanDetails preview={record.data.preview} />
          <section className="review-section">
            <h3>Archived evidence</h3>
            <button
              className="text-button mono"
              onClick={() => setEvidence((value) => !value)}
              aria-expanded={evidence}
            >
              {record.data.evidence_ref} <ArrowRight size={14} />
            </button>
            {evidence && (
              <div className="archive-detail">
                <p>
                  The backend links this archived operational snapshot to its
                  actual source nodes. The returned plan citations are listed
                  below; the full archive remains in FalkorDB.
                </p>
                <ul className="reference-list">
                  {record.data.preview.evidence_refs.map((ref) => (
                    <li key={ref}>
                      <code>{ref}</code>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        </>
      )}
    </Modal>
  );
}

export function Ledger({
  currentScenario,
  selectedId,
  onSelect,
  onWorkbench,
}: {
  currentScenario?: string;
  selectedId?: string;
  onSelect: (id?: string) => void;
  onWorkbench: () => void;
}) {
  const [filter, setFilter] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [lookup, setLookup] = useState("");
  const valid = !query || /^SC-[a-f0-9]{20}$/.test(query);
  const history = useQuery({
    queryKey: ["decisions", query, offset],
    queryFn: ({ signal }) => api.history(query, offset, signal),
    enabled: valid,
    retry: safeReadRetry,
  });
  return (
    <div className="page ledger-page">
      <div className="page-title">
        <div>
          <span className="eyebrow">Decision memory</span>
          <h1>
            The record behind
            <br className="desktop-break" /> every internal decision.
          </h1>
          <p>Who reviewed it, which plan, and the graph evidence they used.</p>
        </div>
        <Badge tone="accent">Stored in FalkorDB</Badge>
      </div>
      <div className="notice">
        <FileCheck2 size={18} />
        <p>
          These are internal planning records. They do not represent purchases,
          reservations or supplier communications.
        </p>
      </div>
      <section className="panel ledger-panel">
        <div className="ledger-toolbar">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              setQuery(filter.trim());
              setOffset(0);
            }}
          >
            <label className="field">
              <span>Filter by scenario ID</span>
              <input
                placeholder="SC-…"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
                maxLength={23}
              />
            </label>
            <button className="secondary-button" type="submit">
              Apply filter
            </button>
          </form>
          <div className="inline-actions">
            <button
              className="text-button"
              onClick={() => {
                setFilter("");
                setQuery("");
                setOffset(0);
              }}
            >
              All records
            </button>
            <button
              className="text-button"
              disabled={!currentScenario}
              onClick={() => {
                setFilter(currentScenario!);
                setQuery(currentScenario!);
                setOffset(0);
              }}
            >
              Current scenario
            </button>
            <button
              className="icon-button"
              aria-label="Refresh decision history"
              onClick={() => void history.refetch()}
              disabled={!valid}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
        {!valid && (
          <p className="field-error" role="alert">
            Enter a full scenario ID: SC- followed by 20 hexadecimal characters.
          </p>
        )}
        {history.isPending && valid ? (
          <Loading label="Retrieving internal decision history…" />
        ) : history.isError ? (
          <ErrorNotice
            error={history.error}
            onRetry={() => void history.refetch()}
          />
        ) : (
          history.data &&
          (history.data.total ? (
            <>
              <div className="ledger-list">
                {history.data.items.map((item) => (
                  <article key={item.decision_id} className="ledger-row">
                    <div className="ledger-icon">
                      <FileCheck2 size={22} />
                    </div>
                    <div>
                      <div className="ledger-row-title">
                        <h2>{policyName(item.plan_id)}</h2>
                        <Badge tone="positive">Approved internal</Badge>
                      </div>
                      <p>{timestamp(item.created_at)}</p>
                      <code>{item.scenario_id}</code>
                      <span className="ledger-record-id">
                        {item.decision_id}
                      </span>
                    </div>
                    <div className="ledger-row-cost">
                      <strong>
                        {decimal(item.estimated_additional_procurement_cost)}
                      </strong>
                      <span>synthetic cost units</span>
                      <button
                        className="text-button"
                        onClick={() => onSelect(item.decision_id)}
                      >
                        View record <ArrowRight size={14} />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
              <nav
                className="pagination"
                aria-label="Decision history pagination"
              >
                <span>
                  {history.data.offset + 1}–
                  {history.data.offset + history.data.items.length} of{" "}
                  {history.data.total} records
                </span>
                <div>
                  <button
                    className="secondary-button small-button"
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - 5))}
                  >
                    Previous
                  </button>
                  <button
                    className="secondary-button small-button"
                    disabled={history.data.next_offset === null}
                    onClick={() => setOffset(history.data!.next_offset!)}
                  >
                    Next
                  </button>
                </div>
              </nav>
            </>
          ) : (
            <EmptyState
              title={
                query
                  ? "No decisions for this scenario"
                  : "No internal decisions yet"
              }
            >
              A reviewed and explicitly approved plan will appear here with its
              source revision and archived evidence.
              <button className="primary-button" onClick={onWorkbench}>
                Review a scenario <ArrowRight size={16} />
              </button>
            </EmptyState>
          ))
        )}
        <form
          className="decision-lookup"
          onSubmit={(event) => {
            event.preventDefault();
            if (/^D-[a-f0-9]{24}$/.test(lookup)) onSelect(lookup);
          }}
        >
          <label className="field">
            <span>Open a known decision ID</span>
            <input
              value={lookup}
              onChange={(event) => setLookup(event.target.value)}
              placeholder="D-…"
              maxLength={26}
            />
          </label>
          <button
            type="submit"
            className="secondary-button"
            disabled={!/^D-[a-f0-9]{24}$/.test(lookup)}
          >
            Open record
          </button>
        </form>
      </section>
      {selectedId && (
        <RecordDetail id={selectedId} onClose={() => onSelect(undefined)} />
      )}
    </div>
  );
}
