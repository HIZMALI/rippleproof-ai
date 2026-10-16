import {
  ArrowRight,
  CalendarDays,
  GitBranch,
  LoaderCircle,
} from "lucide-react";
import type { EvidenceNode, ScenarioRequest } from "../../api/contracts";
import { validateScenario } from "../../lib/format";
import { Badge } from "../../components/ui";

export function ScenarioForm({
  draft,
  onChange,
  onRun,
  onCancel,
  pending,
  suppliers,
  supplier,
  ready,
}: {
  draft: ScenarioRequest;
  onChange: (value: ScenarioRequest) => void;
  onRun: () => void;
  onCancel: () => void;
  pending: boolean;
  suppliers: EvidenceNode[];
  supplier?: EvidenceNode;
  ready: boolean;
}) {
  const errors = validateScenario(draft);
  return (
    <section className="panel scenario-form-panel">
      <header className="panel-header">
        <div>
          <span className="eyebrow">Scenario parameters</span>
          <h2>Model an outage</h2>
        </div>
        <CalendarDays size={18} />
      </header>
      <form
        className="scenario-form"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          if (!Object.keys(errors).length) onRun();
        }}
      >
        <label className="field">
          <span>Supplier</span>
          <input
            aria-label="Supplier"
            list="supplier-list"
            value={draft.supplier_id}
            onChange={(event) =>
              onChange({ ...draft, supplier_id: event.target.value })
            }
            maxLength={7}
            aria-invalid={!!errors.supplier_id}
            aria-describedby={
              errors.supplier_id ? "supplier-error" : "supplier-help"
            }
          />
          <datalist id="supplier-list">
            {suppliers.map((node) => (
              <option key={node.id} value={node.id}>
                {String(node.properties.name ?? node.id)}
              </option>
            ))}
          </datalist>
          {errors.supplier_id ? (
            <small id="supplier-error" className="field-error">
              {errors.supplier_id}
            </small>
          ) : (
            <small id="supplier-help">
              Select a known ID or enter another supplier.
            </small>
          )}
        </label>
        {supplier && (
          <div className="supplier-context">
            <GitBranch size={16} />
            <div>
              <strong>{String(supplier.properties.name ?? supplier.id)}</strong>
              <span>
                {String(supplier.properties.region ?? "Region unknown")} ·{" "}
                {String(supplier.properties.status ?? "Status unknown")}
              </span>
            </div>
          </div>
        )}
        {(["as_of", "outage_start", "outage_end_exclusive"] as const).map(
          (key) => (
            <label className="field" key={key}>
              <span>
                {key === "as_of"
                  ? "As-of date"
                  : key === "outage_start"
                    ? "Outage start"
                    : "Outage end · exclusive"}
              </span>
              <input
                type="date"
                value={draft[key]}
                onChange={(event) =>
                  onChange({ ...draft, [key]: event.target.value })
                }
                aria-invalid={!!errors[key]}
                aria-describedby={`${key}-help`}
              />
              <small
                id={`${key}-help`}
                className={errors[key] ? "field-error" : ""}
              >
                {errors[key] ??
                  (key === "as_of"
                    ? "Inventory is available from this date."
                    : key === "outage_end_exclusive"
                      ? "Dispatch may resume on this date."
                      : "Planned dispatches in the window are delayed.")}
              </small>
            </label>
          ),
        )}
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={draft.include_mitigation}
            onChange={(event) =>
              onChange({ ...draft, include_mitigation: event.target.checked })
            }
          />
          <span>
            Evaluate mitigation
            <small>Respect lead time, capacity and certificates.</small>
          </span>
        </label>
        <div className="form-actions">
          {pending ? (
            <>
              <button
                type="button"
                className="primary-button full-width"
                disabled
              >
                <LoaderCircle size={16} className="spin" />
                Calculating from graph…
              </button>
              <button type="button" className="text-button" onClick={onCancel}>
                Cancel calculation
              </button>
            </>
          ) : (
            <button
              type="submit"
              className="primary-button full-width"
              disabled={!ready || !!Object.keys(errors).length}
            >
              Run scenario <ArrowRight size={16} />
            </button>
          )}
        </div>
        <div className="reference-inputs">
          <Badge>Synthetic reference inputs</Badge>
          <p>Dates and supplier can be changed. Results are never preloaded.</p>
        </div>
      </form>
    </section>
  );
}
