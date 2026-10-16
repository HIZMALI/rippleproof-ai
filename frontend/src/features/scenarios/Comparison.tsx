import { ArrowRight, CircleAlert, ShieldCheck } from "lucide-react";
import type { PlanResult, ScenarioResponse } from "../../api/contracts";
import { decimal, units } from "../../lib/format";
import { Badge } from "../../components/ui";

export function Comparison({
  result,
  compact = false,
}: {
  result: ScenarioResponse;
  compact?: boolean;
}) {
  const columns: {
    title: string;
    description: string;
    plan: PlanResult | null;
    className: string;
  }[] = [
    {
      title: "Baseline",
      description: "Original supply schedule",
      plan: result.baseline,
      className: "baseline",
    },
    {
      title: "Disruption",
      description: "Outage-adjusted arrivals",
      plan: result.disrupted,
      className: "disruption",
    },
    {
      title: "Mitigation",
      description: "Engine-selected recovery",
      plan: result.mitigated,
      className: "mitigation",
    },
  ];
  const overBaseline =
    result.mitigated &&
    result.mitigated.on_time_orders.length >
      result.baseline.on_time_orders.length;
  return (
    <section
      className={`comparison ${compact ? "comparison-compact" : ""}`}
      aria-label="Scenario comparison"
    >
      <div className="comparison-grid">
        {columns.map(({ title, description, plan, className }, index) => (
          <article className={`comparison-card ${className}`} key={title}>
            <header>
              <span className="stage-number">0{index + 1}</span>
              <h3>{title}</h3>
              {index < 2 && <ArrowRight size={16} aria-hidden="true" />}
            </header>
            <p className="muted">{description}</p>
            {plan ? (
              <>
                <div className="coverage-number">
                  <strong data-testid={`${className}-count`}>
                    {units(plan.on_time_orders.length)}
                  </strong>
                  <span>
                    of {units(plan.orders.length)} orders
                    <br />
                    material-covered
                  </span>
                </div>
                <div className="coverage-bar" aria-hidden="true">
                  <span
                    style={{
                      width: `${plan.orders.length ? (plan.on_time_orders.length / plan.orders.length) * 100 : 0}%`,
                    }}
                  />
                </div>
                <div className="comparison-foot">
                  <span>
                    <CircleAlert size={13} />
                    {plan.at_risk_orders.length} at risk
                  </span>
                  <span>{plan.unresolved_orders.length} unresolved</span>
                </div>
                {!compact && (
                  <p className="order-set">
                    <span>At-risk set</span>
                    {plan.at_risk_orders.join(" · ") || "None"}
                  </p>
                )}
              </>
            ) : (
              <div className="no-mitigation">
                Mitigation disabled
                <br />
                <span>Enable it to compare recovery.</span>
              </div>
            )}
          </article>
        ))}
      </div>
      {!compact && (
        <div className="recovery-strip">
          <div>
            <Badge tone="risk">
              <CircleAlert size={12} />
              Newly at risk
            </Badge>
            <strong>{result.newly_at_risk_orders.join(", ") || "None"}</strong>
          </div>
          <div>
            <Badge tone="positive">
              <ShieldCheck size={12} />
              Restored
            </Badge>
            <strong>{result.restored_orders.join(", ") || "None"}</strong>
          </div>
          <div className="procurement-total">
            <span>Gross additional procurement</span>
            <strong>
              {decimal(result.estimated_additional_procurement_cost)}{" "}
              <small>synthetic cost units</small>
            </strong>
          </div>
        </div>
      )}
      {overBaseline && (
        <p className="context-note">
          Mitigation covers more orders than baseline. Shared-material
          reallocation also resolves a pre-existing baseline shortfall; this is
          not a delivery guarantee.
        </p>
      )}
    </section>
  );
}
