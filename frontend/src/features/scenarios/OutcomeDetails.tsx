import { useMemo, useState } from "react";
import { ArrowUpRight } from "lucide-react";
import type { ScenarioResponse } from "../../api/contracts";
import {
  Badge,
  EmptyState,
  Pagination,
  SectionHeading,
  Status,
} from "../../components/ui";
import { calendar, decimal, units } from "../../lib/format";

export function OutcomeDetails({
  result,
  onOrder,
}: {
  result: ScenarioResponse;
  onOrder: (id: string) => void;
}) {
  const [filter, setFilter] = useState("new");
  const [offset, setOffset] = useState(0);
  const filtered = useMemo(
    () =>
      result.disrupted.orders.filter(
        (order) =>
          filter === "all" ||
          (filter === "new"
            ? result.newly_at_risk_orders
            : filter === "restored"
              ? result.restored_orders
              : result.dependent_orders
          ).includes(order.order_id),
      ),
    [result, filter],
  );
  return (
    <>
      <section className="panel order-panel">
        <SectionHeading
          eyebrow="Material coverage"
          title="Which orders need attention?"
        >
          <div className="filter-chips" aria-label="Order filters">
            {[
              { id: "new", label: "Newly at risk" },
              { id: "restored", label: "Restored" },
              { id: "connected", label: "Connected" },
              { id: "all", label: "All open orders" },
            ].map((item) => (
              <button
                key={item.id}
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
        </SectionHeading>
        {filtered.length ? (
          <>
            <div
              className="table-scroll"
              role="region"
              aria-label="Order material coverage"
              tabIndex={0}
            >
              <table>
                <thead>
                  <tr>
                    <th>Order / deadline</th>
                    <th>Disrupted coverage</th>
                    <th>Material shortfall</th>
                    <th>Mitigated coverage</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(offset, offset + 6).map((order) => {
                    const shortages = order.materials.filter(
                      (material) => (material.shortfall_quantity ?? 0) > 0,
                    );
                    const mitigated = result.mitigated?.orders.find(
                      (value) => value.order_id === order.order_id,
                    );
                    return (
                      <tr key={order.order_id}>
                        <td>
                          <button
                            className="text-button mono"
                            onClick={() => onOrder(order.order_id)}
                          >
                            {order.order_id}
                          </button>
                          <span className="cell-secondary">
                            {calendar(order.deadline)}
                          </span>
                        </td>
                        <td>
                          <Status value={order.status} />
                        </td>
                        <td>
                          {shortages.length
                            ? shortages.map((material) => (
                                <span
                                  className="material-shortfall"
                                  key={material.part_id}
                                >
                                  <strong>{material.part_id}</strong>
                                  {units(material.shortfall_quantity)} units
                                  short
                                  <span>
                                    {units(material.available_by_deadline)}{" "}
                                    available /{" "}
                                    {units(material.required_quantity)} required
                                  </span>
                                </span>
                              ))
                            : order.status === "insufficient_data"
                              ? "Unknown — incomplete source data"
                              : "Complete BOM covered"}
                        </td>
                        <td>
                          {mitigated ? (
                            <Status value={mitigated.status} />
                          ) : (
                            "Not evaluated"
                          )}
                        </td>
                        <td>
                          <button
                            className="secondary-button small-button"
                            onClick={() => onOrder(order.order_id)}
                          >
                            Inspect path <ArrowUpRight size={13} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <Pagination
              total={filtered.length}
              offset={offset}
              size={6}
              onChange={setOffset}
              label="orders"
            />
          </>
        ) : (
          <EmptyState title="No orders in this set">
            The current simulation returned no matching orders. Connected,
            at-risk and restored sets remain distinct.
          </EmptyState>
        )}
        <p className="panel-footnote">
          Quantities reflect shared, all-or-nothing allocation in the disruption
          plan. Failed orders reserve no stock.
        </p>
      </section>
      <section className="panel schedule-panel">
        <SectionHeading
          eyebrow="Optional recovery"
          title="Proposed arrival schedule"
        >
          <Badge tone="accent">Internal proposal only</Badge>
        </SectionHeading>
        <p className="muted">
          Engine-selected mitigation. Capacity is evaluated per supplier, part
          and dispatch day; certificates must cover arrival.
        </p>
        {result.proposed_shipments.length ? (
          <div
            className="table-scroll"
            role="region"
            aria-label="Engine-selected proposal schedule"
            tabIndex={0}
          >
            <table>
              <thead>
                <tr>
                  <th>Supplier / part</th>
                  <th className="numeric">New units</th>
                  <th>Dispatch</th>
                  <th>Arrival</th>
                  <th>Certification</th>
                  <th className="numeric">Gross additional cost</th>
                </tr>
              </thead>
              <tbody>
                {result.proposed_shipments.map((shipment) => (
                  <tr key={shipment.id}>
                    <td>
                      <strong className="mono">{shipment.supplier_id}</strong>
                      <span className="cell-secondary mono">
                        {shipment.part_id}
                      </span>
                    </td>
                    <td className="numeric">
                      {units(shipment.quantity)} units
                    </td>
                    <td>{calendar(shipment.dispatch_date)}</td>
                    <td>{calendar(shipment.arrival_date)}</td>
                    <td>
                      <Badge
                        tone={
                          (shipment.certificate_checks ?? []).every(
                            (check) => check.status === "valid",
                          )
                            ? "positive"
                            : "risk"
                        }
                      >
                        {(shipment.certificate_checks ?? []).length} arrival
                        checks
                      </Badge>
                    </td>
                    <td className="numeric">
                      {decimal(shipment.estimated_additional_procurement_cost)}
                      <span className="cell-secondary">
                        synthetic cost units
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No new shipments proposed">
            Mitigation is disabled or no atomic recovery was feasible for newly
            at-risk orders.
          </EmptyState>
        )}
      </section>
      <details className="panel assumptions">
        <summary>Model boundaries, data issues and source revision</summary>
        <p className="mono hash-value">
          {result.scenario_id} · {result.snapshot_fingerprint}
        </p>
        {result.incomplete_data && (
          <div className="notice notice-error">
            Data is incomplete. {result.data_issues.length} source issues were
            returned; affected classifications remain unresolved.
          </div>
        )}
        <ul className="assumption-list">
          {result.assumptions.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
        {!!result.data_issues.length && (
          <ul className="assumption-list">
            {result.data_issues.slice(0, 20).map((issue, index) => (
              <li key={index}>
                {issue.entity_id} · {issue.code} · {issue.detail}
              </li>
            ))}
          </ul>
        )}
        <p className="small muted">
          Showing up to 20 source issues. Full details are available from the
          scenario API; raw graph archives are not rendered by default.
        </p>
      </details>
    </>
  );
}
