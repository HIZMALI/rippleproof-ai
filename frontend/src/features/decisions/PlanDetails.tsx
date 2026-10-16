import type { DecisionPreview } from "../../api/contracts";
import { Badge } from "../../components/ui";
import { calendar, decimal, policyName, units } from "../../lib/format";

export function PlanDetails({ preview }: { preview: DecisionPreview }) {
  return (
    <>
      <div className="review-summary">
        <div>
          <span className="eyebrow">
            {policyName(preview.mitigation_plan_id)}
          </span>
          <strong>
            {decimal(preview.estimated_additional_procurement_cost)}
            <small>gross additional synthetic cost units</small>
          </strong>
        </div>
        <div>
          <Badge tone="positive">
            {preview.restored_orders.length} newly at-risk orders restored
          </Badge>
          <p>
            {preview.restored_orders.join(" · ") ||
              "No newly at-risk orders restored"}
          </p>
        </div>
      </div>
      <section className="review-section">
        <h3>Full proposed schedule</h3>
        <p className="muted small">
          Optional new supply only. These are not booked shipments or purchase
          orders.
        </p>
        <div
          className="table-scroll"
          role="region"
          aria-label="Proposed schedule"
          tabIndex={0}
        >
          <table>
            <thead>
              <tr>
                <th>Supplier / part</th>
                <th className="numeric">Quantity</th>
                <th>Dispatch</th>
                <th>Arrival</th>
                <th className="numeric">Unit cost</th>
                <th className="numeric">Additional cost</th>
              </tr>
            </thead>
            <tbody>
              {preview.proposed_shipments.map((shipment) => (
                <tr key={shipment.id}>
                  <td>
                    <strong className="mono">{shipment.supplier_id}</strong>
                    <span className="cell-secondary mono">
                      {shipment.part_id}
                    </span>
                  </td>
                  <td className="numeric">{units(shipment.quantity)} units</td>
                  <td>{calendar(shipment.dispatch_date)}</td>
                  <td>{calendar(shipment.arrival_date)}</td>
                  <td className="numeric">{decimal(shipment.unit_cost)}</td>
                  <td className="numeric">
                    {decimal(shipment.estimated_additional_procurement_cost)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!preview.proposed_shipments.length && (
          <p className="notice">
            This policy proposes no additional procurement.
          </p>
        )}
      </section>
      <section className="review-section">
        <h3>Arrival-date certification evidence</h3>
        {preview.proposed_shipments.map((shipment) => (
          <div key={shipment.id} className="review-certificates">
            <strong>
              {shipment.supplier_id} / {shipment.part_id} · arrival{" "}
              {calendar(shipment.arrival_date)}
            </strong>
            {(shipment.certificate_checks ?? []).map((check) => (
              <div key={check.certificate_id}>
                <Badge tone={check.status === "valid" ? "positive" : "risk"}>
                  {check.certificate_id} · {check.status}
                </Badge>
                <span>Valid through {calendar(check.valid_until)}</span>
                <code>{check.requirement_ref}</code>
                <code>{check.holding_ref ?? "No verified holding"}</code>
              </div>
            ))}
          </div>
        ))}
      </section>
      <section className="review-section">
        <h3>Source revision</h3>
        <dl className="revision-list">
          <div>
            <dt>Scenario</dt>
            <dd>{preview.scenario_id}</dd>
          </div>
          <div>
            <dt>Operational fingerprint</dt>
            <dd>{preview.operational_fingerprint}</dd>
          </div>
          <div>
            <dt>Plan revision</dt>
            <dd>{preview.plan_revision}</dd>
          </div>
          <div>
            <dt>As-of / outage</dt>
            <dd>
              {preview.scenario.as_of} / [{preview.scenario.outage_start},{" "}
              {preview.scenario.outage_end_exclusive})
            </dd>
          </div>
        </dl>
        <p className="small muted">
          No fixed preview expiry is provided. The backend recalculates and
          checks source and plan revisions on approval.
        </p>
      </section>
      <details className="review-section">
        <summary>
          All model assumptions and limitations ({preview.limitations.length})
        </summary>
        <ul className="assumption-list">
          {preview.limitations.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </details>
      <details className="review-section">
        <summary>
          Returned plan evidence references ({preview.evidence_refs.length})
        </summary>
        <ul className="reference-list">
          {preview.evidence_refs.map((ref) => (
            <li key={ref}>
              <code>{ref}</code>
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}
