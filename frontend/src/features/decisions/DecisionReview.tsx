import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, Check, LockKeyhole, ShieldCheck } from "lucide-react";
import { api, ApiError, isLoopback } from "../../api/client";
import type {
  ApprovalRequest,
  DecisionPreview,
  DecisionRecord,
  PrepareRequest,
  ScenarioResponse,
} from "../../api/contracts";
import { ErrorNotice, Loading, Modal } from "../../components/ui";
import { timestamp } from "../../lib/format";
import { PlanDetails } from "./PlanDetails";

export function DecisionReview({
  request,
  onClose,
  onSaved,
  onLedger,
  onSourceChanged,
}: {
  request: PrepareRequest;
  onClose: () => void;
  onSaved: (record: DecisionRecord, checked?: ScenarioResponse) => void;
  onLedger: (id: string) => void;
  onSourceChanged: () => void;
}) {
  const [preview, setPreview] = useState<DecisionPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [reviewed, setReviewed] = useState(false);
  const [authorize, setAuthorize] = useState(false);
  const [pending, setPending] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [operator, setOperator] = useState("");
  const [rationale, setRationale] = useState("");
  const [tokenPresent, setTokenPresent] = useState(false);
  const [stale, setStale] = useState(false);
  const [record, setRecord] = useState<DecisionRecord | null>(null);
  const [postCheck, setPostCheck] = useState("");
  const token = useRef<HTMLInputElement>(null);
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const intent = useRef<{ signature: string; body: ApprovalRequest } | null>(
    null,
  );
  const local = isLoopback(window.location.hostname);

  const clearInputs = useCallback(() => {
    if (token.current) token.current.value = "";
    setTokenPresent(false);
    setConfirmation("");
    setOperator("");
    setRationale("");
    setAuthorize(false);
    setReviewed(false);
    intent.current = null;
  }, []);
  const load = useCallback(async () => {
    controller.current?.abort();
    controller.current = new AbortController();
    setLoading(true);
    setError(null);
    setPreview(null);
    clearInputs();
    try {
      const value = await api.prepare(request, controller.current.signal);
      if (mounted.current) setPreview(value);
    } catch (error) {
      if (mounted.current && !controller.current.signal.aborted)
        setError(error);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [request, clearInputs]);
  useEffect(() => {
    mounted.current = true;
    void load();
    return () => {
      mounted.current = false;
      controller.current?.abort();
      if (token.current) token.current.value = "";
    };
  }, [load]);

  async function approve() {
    if (
      !preview ||
      !local ||
      !reviewed ||
      confirmation !== "APPROVE INTERNAL" ||
      !token.current?.value ||
      pending
    )
      return;
    const signature = JSON.stringify({
      revision: preview.plan_revision,
      operator,
      rationale,
    });
    if (!intent.current || intent.current.signature !== signature) {
      intent.current = {
        signature,
        body: {
          scenario: preview.scenario,
          mitigation_plan_id: preview.mitigation_plan_id,
          expected_scenario_id: preview.scenario_id,
          expected_operational_fingerprint: preview.operational_fingerprint,
          expected_plan_revision: preview.plan_revision,
          idempotency_key: crypto.randomUUID().replaceAll("-", ""),
          operator_id: operator,
          rationale,
          confirm_internal_decision: true,
        },
      };
    }
    // The credential never enters React state, Query cache, storage, URLs or logs.
    const attemptToken = token.current.value;
    token.current.value = "";
    setTokenPresent(false);
    setPending(true);
    setError(null);
    try {
      const saved = await api.approve(intent.current.body, attemptToken);
      if (!mounted.current) return;
      setRecord(saved);
      clearInputs();
      let checked: ScenarioResponse | undefined;
      try {
        const current = await api.simulate(saved.preview.scenario);
        if (
          current.scenario_id === saved.preview.scenario_id &&
          current.snapshot_fingerprint === saved.preview.operational_fingerprint
        ) {
          checked = current;
          setPostCheck(
            "Verified after saving: scenario ID and operational fingerprint are unchanged.",
          );
        } else {
          setPostCheck(
            "Record saved. Current source data differs; refresh your analysis.",
          );
          onSourceChanged();
        }
      } catch {
        setPostCheck(
          "Record saved. Current source verification is unavailable; check it again before relying on the analysis.",
        );
      }
      onSaved(saved, checked);
    } catch (error) {
      if (!mounted.current) return;
      if (error instanceof ApiError && error.status === 409) {
        clearInputs();
        setStale(true);
        onSourceChanged();
        await load();
      } else setError(error);
    } finally {
      if (mounted.current) {
        setPending(false);
        if (token.current) token.current.value = "";
        setTokenPresent(false);
      }
    }
  }
  return (
    <Modal
      title={
        record
          ? "Internal decision recorded"
          : "Review internal planning record"
      }
      subtitle="No purchase is placed. No inventory is reserved. No supplier is contacted."
      onClose={onClose}
      busy={pending}
      wide
    >
      {loading && (
        <Loading label="Recalculating the selected plan from fresh graph data…" />
      )}
      {!!error && (
        <ErrorNotice
          error={error}
          onRetry={!preview ? () => void load() : undefined}
        />
      )}
      {stale && (
        <div className="notice notice-error" role="alert">
          Preview is stale. Approval inputs were discarded. Review the
          recalculated plan and confirm again.
        </div>
      )}
      {record ? (
        <>
          <div className="notice notice-positive">
            <ShieldCheck size={22} />
            <div>
              <strong>Saved as an internal decision</strong>
              <p>{record.decision_id}</p>
              <p>{timestamp(record.created_at)}</p>
            </div>
          </div>
          <p className="notice">
            {postCheck || "Checking the operational source after persistence…"}
          </p>
          <div className="review-footer">
            <button className="secondary-button" onClick={onClose}>
              Close review
            </button>
            <button
              className="primary-button"
              onClick={() => onLedger(record.decision_id)}
            >
              View persisted record <ArrowRight size={16} />
            </button>
          </div>
        </>
      ) : (
        preview && (
          <>
            <PlanDetails preview={preview} />
            <div className="approval-boundary">
              <LockKeyhole size={18} />
              <div>
                <strong>Human approval boundary</strong>
                <p>
                  This records an internal plan only. The AI and MCP tools
                  cannot authorize it. One-worker local operation requires
                  external graph writers to be serialized.
                </p>
              </div>
            </div>
            {!local ? (
              <p className="notice">
                Browser approval is disabled on this origin. Preview and history
                remain available. Use trusted localhost or the documented
                operator CLI flow.
              </p>
            ) : (
              <>
                <label className="checkbox-field review-ack">
                  <input
                    type="checkbox"
                    checked={reviewed}
                    onChange={(event) => {
                      setReviewed(event.target.checked);
                      if (!event.target.checked) {
                        setAuthorize(false);
                        if (token.current) token.current.value = "";
                        setTokenPresent(false);
                      }
                    }}
                  />
                  <span>
                    I have reviewed the full schedule, certification evidence,
                    cost and limitations.
                  </span>
                </label>
                {!authorize ? (
                  <button
                    className="primary-button full-width"
                    disabled={!reviewed}
                    onClick={() => setAuthorize(true)}
                  >
                    Continue to manual approval <ArrowRight size={16} />
                  </button>
                ) : (
                  <form
                    className="authorization-form"
                    autoComplete="off"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void approve();
                    }}
                  >
                    <div className="form-grid">
                      <label className="field">
                        <span>Operator pseudonym</span>
                        <input
                          value={operator}
                          onChange={(event) => setOperator(event.target.value)}
                          pattern="[A-Za-z][A-Za-z0-9_-]{2,39}"
                          maxLength={40}
                          required
                          placeholder="demo-operator"
                          disabled={pending}
                        />
                      </label>
                      <label className="field">
                        <span>Local operator token</span>
                        <input
                          ref={token}
                          type="password"
                          autoComplete="off"
                          maxLength={256}
                          required
                          onInput={(event) =>
                            setTokenPresent(!!event.currentTarget.value)
                          }
                          disabled={pending}
                          data-lpignore="true"
                        />
                      </label>
                    </div>
                    <label className="field">
                      <span>Decision rationale</span>
                      <textarea
                        value={rationale}
                        onChange={(event) => setRationale(event.target.value)}
                        maxLength={1000}
                        required
                        rows={2}
                        disabled={pending}
                      />
                    </label>
                    <label className="field">
                      <span>Type APPROVE INTERNAL to confirm</span>
                      <input
                        value={confirmation}
                        onChange={(event) =>
                          setConfirmation(event.target.value)
                        }
                        autoComplete="off"
                        spellCheck={false}
                        disabled={pending}
                        required
                      />
                    </label>
                    <p className="small muted">
                      The token is cleared for each attempt and when this dialog
                      closes. After an uncertain network outcome, retry this
                      exact action here with the same intent, or check the
                      ledger before starting another approval.
                    </p>
                    <button
                      className="primary-button full-width"
                      type="submit"
                      disabled={
                        pending ||
                        !reviewed ||
                        !tokenPresent ||
                        confirmation !== "APPROVE INTERNAL" ||
                        !/^[A-Za-z][A-Za-z0-9_-]{2,39}$/.test(operator) ||
                        !rationale.trim()
                      }
                    >
                      {pending ? (
                        "Recording internal decision…"
                      ) : (
                        <>
                          <Check size={16} />
                          Approve internal planning record
                        </>
                      )}
                    </button>
                  </form>
                )}
              </>
            )}
          </>
        )
      )}
    </Modal>
  );
}
