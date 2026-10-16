import type {
  GraphSummary,
  ScenarioRequest,
  ScenarioResponse,
} from "../api/contracts";

export const units = (value: number | null | undefined): string =>
  value == null ? "Unknown" : new Intl.NumberFormat("en-US").format(value);
export function decimal(value: string | number | null | undefined): string {
  if (value == null) return "Unknown";
  const text = String(value);
  if (!/^\d+(\.\d+)?$/.test(text)) return text;
  const [integer = "", fraction = ""] = text.split(".");
  // Preserve decimal text exactly; never recompute/round money using binary floats.
  return `${integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${fraction.padEnd(2, "0")}`;
}
export function calendar(value: string | null | undefined): string {
  if (!value) return "Unknown";
  const time = new Date(value.length === 10 ? `${value}T00:00:00Z` : value);
  return Number.isNaN(time.getTime())
    ? value
    : new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      }).format(time);
}
export function timestamp(value: string | number): string {
  const time = new Date(value);
  return Number.isNaN(time.getTime())
    ? "Unknown"
    : `${new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "medium", timeZone: "UTC" }).format(time)} UTC`;
}
export const policyName = (value: string): string =>
  ({
    cost_first: "Cost-first recovery",
    lead_first: "Lead-first recovery",
    no_procurement: "No additional procurement",
  })[value] ?? `Single supplier · ${value.replace("supplier:", "")}`;
export const codeLabel = (value: string): string =>
  value.toLowerCase().replaceAll("_", " ");
export function operationalCounts(summary: GraphSummary) {
  const nodeTypes = [
    "Supplier",
    "Part",
    "Product",
    "Order",
    "Certificate",
    "InboundShipment",
  ];
  const edgeTypes = [
    "SUPPLIES",
    "USES",
    "CONTAINS",
    "REQUIRES_CERT",
    "HOLDS_CERT",
    "FULFILLS",
    "FOR_PART",
  ];
  return {
    nodes: nodeTypes.reduce(
      (sum, type) => sum + (summary.nodes_by_label[type] ?? 0),
      0,
    ),
    edges: edgeTypes.reduce(
      (sum, type) => sum + (summary.relationships_by_type[type] ?? 0),
      0,
    ),
  };
}
export function validateScenario(
  draft: ScenarioRequest,
): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!/^S-[0-9]{2,5}$/.test(draft.supplier_id))
    errors.supplier_id = "Use a supplier ID such as S-04.";
  for (const key of [
    "as_of",
    "outage_start",
    "outage_end_exclusive",
  ] as const) {
    const text = draft[key];
    const parsed = new Date(`${text}T00:00:00Z`);
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(text) ||
      Number.isNaN(parsed.getTime()) ||
      parsed.toISOString().slice(0, 10) !== text
    )
      errors[key] = "Enter a valid calendar date.";
  }
  if (
    !errors.outage_start &&
    !errors.outage_end_exclusive &&
    draft.outage_end_exclusive <= draft.outage_start
  )
    errors.outage_end_exclusive =
      "The exclusive end must be later than the start.";
  if (!Object.keys(errors).length) {
    const asOf = Date.parse(draft.as_of);
    if (
      [draft.outage_start, draft.outage_end_exclusive].some(
        (d) => Math.abs(Date.parse(d) - asOf) > 366 * 86400000,
      )
    )
      errors.outage_end_exclusive =
        "Outage boundaries must be within 366 days of the as-of date.";
  }
  return errors;
}
export function initialPart(result: ScenarioResponse): string {
  for (const order of result.disrupted.orders) {
    if (result.newly_at_risk_orders.includes(order.order_id)) {
      const material = order.materials.find(
        (m) => (m.shortfall_quantity ?? 0) > 0,
      );
      if (material) return material.part_id;
    }
  }
  return result.dependency_paths[0]?.nodes[1]?.id ?? "";
}
