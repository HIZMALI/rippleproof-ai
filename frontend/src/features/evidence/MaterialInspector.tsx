import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Check,
  CircleAlert,
  Database,
  ShieldCheck,
} from "lucide-react";
import { api, safeReadRetry } from "../../api/client";
import type {
  CandidateEvaluation,
  ScenarioResponse,
} from "../../api/contracts";
import {
  Badge,
  EmptyState,
  ErrorNotice,
  Loading,
  PropertyList,
  Status,
} from "../../components/ui";
import { calendar, codeLabel, decimal, units } from "../../lib/format";
import type { EvidenceFact } from "./EvidenceExplorer";

function Candidate({
  candidate,
  onRef,
}: {
  candidate: CandidateEvaluation;
  onRef: (ref: string) => void;
}) {
  return (
    <article className="candidate-card">
      <div className="candidate-title">
        <button
          className="text-button mono"
          onClick={() => onRef(candidate.offer_ref)}
        >
          {candidate.supplier_id}
          <ArrowUpRight size={13} />
        </button>
        <Badge
          tone={
            candidate.status === "eligible"
              ? "positive"
              : candidate.status === "rejected"
                ? "risk"
                : "neutral"
          }
        >
          {candidate.status === "eligible" ? (
            <Check size={11} />
          ) : (
            <CircleAlert size={11} />
          )}
          {candidate.status === "eligible"
            ? "Eligible"
            : candidate.status === "rejected"
              ? "Not eligible"
              : "Unknown"}
        </Badge>
      </div>
      <div className="candidate-terms">
        <span>
          {decimal(candidate.unit_cost)}
          <small> / unit</small>
        </span>
        <span>
          {units(candidate.lead_days)}
          <small> lead days</small>
        </span>
        <span>
          {units(candidate.daily_capacity)}
          <small> units/day</small>
        </span>
      </div>
      <p className="arrival-line">
        Projected arrival{" "}
        <strong>{calendar(candidate.earliest_arrival_date)}</strong>
      </p>
      {candidate.reason_codes
        .filter((code) => code !== "ELIGIBLE_AT_EARLIEST_ARRIVAL")
        .map((code) => (
          <p className="rejection-reason" key={code}>
            {codeLabel(code)}
          </p>
        ))}
      <ul className="certificate-list">
        {candidate.certificate_checks.map((check) => (
          <li key={check.certificate_id}>
            <span>
              {check.status === "valid" ? (
                <ShieldCheck size={13} />
              ) : (
                <CircleAlert size={13} />
              )}
              <button
                onClick={() => onRef(check.requirement_ref)}
                className="text-button mono"
              >
                {check.certificate_id}
              </button>
            </span>
            <strong
              className={
                check.status === "valid" ? "text-positive" : "text-risk"
              }
            >
              {check.status === "valid"
                ? "Valid on arrival"
                : check.status === "missing"
                  ? "Not held"
                  : check.status === "expired"
                    ? "Expired at arrival"
                    : "Unknown"}
            </strong>
            <small>
              {check.valid_until
                ? `Valid through ${calendar(check.valid_until)}`
                : "No verified holding"}
              {check.holding_ref && (
                <button
                  className="inline-ref"
                  onClick={() => onRef(check.holding_ref!)}
                >
                  View holding <ArrowUpRight size={11} />
                </button>
              )}
            </small>
          </li>
        ))}
      </ul>
      {!candidate.certificate_checks.length && (
        <p className="muted small">
          No certificate checks returned. Qualification is limited to modeled
          requirements.
        </p>
      )}
      {!!candidate.booked_dispatches.length && (
        <details>
          <summary>
            Booked capacity ({candidate.booked_dispatches.length} dispatches)
          </summary>
          <PropertyList
            properties={{ dispatches: candidate.booked_dispatches }}
          />
        </details>
      )}
    </article>
  );
}

export function MaterialInspector({
  result,
  selectedPart,
  selectedOrder,
  asOf,
  ready,
  onPart,
  inspected,
  onInspect,
  clearInspect,
}: {
  result?: ScenarioResponse;
  selectedPart: string;
  selectedOrder?: string;
  asOf: string;
  ready: boolean;
  onPart: (part: string) => void;
  inspected: EvidenceFact | null;
  onInspect: (fact: EvidenceFact) => void;
  clearInspect: () => void;
}) {
  const [fallbackPart, setFallbackPart] = useState("P-22");
  const part = selectedPart || fallbackPart;
  const candidates =
    result?.candidate_evaluations.filter(
      (candidate) => candidate.part_id === part,
    ) ?? [];
  const parts = result
    ? [
        ...new Set(
          result.order_demands.flatMap((order) =>
            order.parts.map((item) => item.part_id),
          ),
        ),
      ].sort()
    : [];
  const alternatives = useQuery({
    queryKey: ["alternatives", part, asOf],
    queryFn: ({ signal }) => api.alternatives(part, asOf, signal),
    enabled:
      ready &&
      !result &&
      /^P-[0-9]{2,5}$/.test(part) &&
      /^\d{4}-\d{2}-\d{2}$/.test(asOf),
    retry: safeReadRetry,
  });
  const order = result?.disrupted.orders.find(
    (order) => order.order_id === selectedOrder,
  );
  const material = order?.materials.find(
    (material) => material.part_id === part,
  );
  const onRef = (ref: string) => {
    const fact =
      result?.evidence_relationships[ref] ?? result?.evidence_nodes[ref];
    if (fact) onInspect(fact);
  };
  return (
    <aside
      className="panel inspector-panel"
      aria-label="Material and evidence inspector"
    >
      <header className="panel-header">
        <div>
          <span className="eyebrow">Evidence inspector</span>
          <h2>{inspected ? "Source record" : "Material constraints"}</h2>
        </div>
        <Database size={17} />
      </header>
      <div className="inspector-toggle">
        <button aria-pressed={!inspected} onClick={clearInspect}>
          Material
        </button>
        <button aria-pressed={!!inspected} disabled={!inspected}>
          Source properties
        </button>
      </div>
      <div className="inspector-content">
        {inspected ? (
          <div className="source-inspector">
            <Badge tone="accent">Stored graph fact</Badge>
            <h3 className="mono">{inspected.id}</h3>
            <p className="muted">
              {"label" in inspected ? inspected.label : inspected.type}
            </p>
            {"source_id" in inspected && (
              <p className="source-direction">
                {inspected.source_id} → {inspected.target_id}
              </p>
            )}
            <PropertyList properties={inspected.properties} />
            <p className="context-note">
              Read from the graph response for this scope. Proposed shipments
              are not stored source records.
            </p>
            <button
              className="secondary-button full-width"
              onClick={clearInspect}
            >
              Return to material constraints
            </button>
          </div>
        ) : (
          <>
            <label className="field inspector-part">
              <span>Part in focus</span>
              {result ? (
                <select
                  value={part}
                  onChange={(event) => onPart(event.target.value)}
                >
                  {parts.map((id) => (
                    <option key={id}>{id}</option>
                  ))}
                </select>
              ) : (
                <input
                  value={fallbackPart}
                  onChange={(event) => {
                    setFallbackPart(event.target.value);
                    onPart(event.target.value);
                  }}
                  maxLength={7}
                />
              )}
            </label>
            {material && order ? (
              <section className="material-coverage">
                <div>
                  <strong>{order.order_id}</strong>
                  <Status value={order.status} />
                </div>
                <dl>
                  <div>
                    <dt>Required</dt>
                    <dd>{units(material.required_quantity)} units</dd>
                  </div>
                  <div>
                    <dt>Available by deadline</dt>
                    <dd>{units(material.available_by_deadline)} units</dd>
                  </div>
                  <div>
                    <dt>Allocated</dt>
                    <dd>{units(material.allocated_quantity)} units</dd>
                  </div>
                  <div>
                    <dt>Shortfall</dt>
                    <dd
                      className={
                        (material.shortfall_quantity ?? 0) > 0
                          ? "text-risk"
                          : ""
                      }
                    >
                      {units(material.shortfall_quantity)} units
                    </dd>
                  </div>
                </dl>
                <p>Disruption plan · {calendar(order.deadline)} deadline</p>
              </section>
            ) : (
              result && (
                <p className="context-note">
                  Choose an order path using this part to inspect its material
                  coverage.
                </p>
              )
            )}
            <div className="inspector-section-heading">
              <h3>Alternative sources</h3>
              <span>
                {result
                  ? candidates.length
                  : (alternatives.data?.candidates.length ?? "—")}
              </span>
            </div>
            <p className="small muted">
              Suitability is per part and arrival date. Certificates do not
              approve a supplier globally.
            </p>
            {result ? (
              candidates.length ? (
                candidates.map((candidate) => (
                  <Candidate
                    key={candidate.offer_ref}
                    candidate={candidate}
                    onRef={onRef}
                  />
                ))
              ) : (
                <EmptyState title="No alternative offers">
                  The scenario returned no alternative evaluations for this
                  part.
                </EmptyState>
              )
            ) : alternatives.isPending && ready ? (
              <Loading />
            ) : alternatives.isError ? (
              <ErrorNotice
                error={alternatives.error}
                onRetry={() => void alternatives.refetch()}
              />
            ) : alternatives.data ? (
              <>
                <p className="context-note">
                  Certificate-only checks as of {calendar(asOf)}. Run a scenario
                  for arrival, lead-time and capacity feasibility.
                </p>
                {alternatives.data.candidates.map((candidate) => (
                  <article
                    className="candidate-card"
                    key={candidate.supplier.id}
                  >
                    <div className="candidate-title">
                      <strong className="mono">{candidate.supplier.id}</strong>
                      <Badge
                        tone={
                          candidate.certifications_valid ? "positive" : "risk"
                        }
                      >
                        {candidate.certifications_valid
                          ? "Certs valid"
                          : "Cert issue"}
                      </Badge>
                    </div>
                    <p className="small muted">
                      {decimal(candidate.supply_terms.unit_cost)} / unit ·{" "}
                      {candidate.supply_terms.lead_days} lead days
                    </p>
                    <ul className="certificate-list">
                      {candidate.certificate_checks.map((check) => (
                        <li key={check.certificate_id}>
                          <span className="mono">{check.certificate_id}</span>
                          <strong>
                            {check.status === "missing"
                              ? "Not held"
                              : codeLabel(check.status)}
                          </strong>
                          <small>
                            {check.valid_until
                              ? `Through ${calendar(check.valid_until)}`
                              : "Holding absent"}
                          </small>
                        </li>
                      ))}
                    </ul>
                    <button
                      className="text-button"
                      onClick={() => onInspect(candidate.supplies_relationship)}
                    >
                      Inspect offer <ArrowUpRight size={12} />
                    </button>
                  </article>
                ))}
              </>
            ) : (
              <p className="context-note">
                Connect to the backend to inspect stored offers.
              </p>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
