import { describe, expect, it } from "vitest";
import {
  calendar,
  decimal,
  operationalCounts,
  validateScenario,
} from "../src/lib/format";
import {
  isLoopback,
  ApiError,
  errorCopy,
  safeReadRetry,
  sourceUnavailable,
} from "../src/api/client";
import type { ScenarioRequest } from "../src/api/contracts";

const scenario: ScenarioRequest = {
  supplier_id: "S-04",
  as_of: "2026-10-15",
  outage_start: "2026-10-16",
  outage_end_exclusive: "2026-10-24",
  include_mitigation: true,
};
describe("deterministic display and input validation", () => {
  it("invalidates source on proxy timeout but preserves an approval configuration boundary", () => {
    expect(sourceUnavailable(new ApiError(504, "invalid_contract"))).toBe(true);
    expect(errorCopy(new ApiError(504, "invalid_contract"))).toContain(
      "Data source unavailable",
    );
    expect(
      sourceUnavailable(new ApiError(503, "approval_not_configured")),
    ).toBe(false);
  });
  it.each([
    ["1364.00", "1,364.00"],
    ["999999999999999999.123", "999,999,999,999,999,999.123"],
    ["0", "0.00"],
    [null, "Unknown"],
  ])("preserves decimal money %s", (input, output) =>
    expect(decimal(input)).toBe(output),
  );
  it("formats dates without local timezone drift", () =>
    expect(calendar("2026-10-15")).toBe("15 Oct 2026"));
  it("accepts a valid window", () =>
    expect(validateScenario(scenario)).toEqual({}));
  it.each([
    { outage_end_exclusive: "2026-10-16" },
    { outage_end_exclusive: "2026-10-10" },
    { outage_start: "2026-02-30" },
    { as_of: "" },
    { supplier_id: "S-04 MATCH(n)" },
    { outage_end_exclusive: "2030-01-01" },
  ])("rejects invalid inputs %o", (value) =>
    expect(
      Object.keys(validateScenario({ ...scenario, ...value })).length,
    ).toBeGreaterThan(0),
  );
  it("keeps memory out of operational counts", () =>
    expect(
      operationalCounts({
        graph: "test",
        node_count: 5,
        relationship_count: 5,
        nodes_by_label: { Supplier: 1, Evidence: 4 },
        relationships_by_type: { SUPPLIES: 2, REFERENCES: 3 },
      }),
    ).toEqual({ nodes: 1, edges: 2 }));
  it.each([
    "localhost.evil.test",
    "192.168.0.2",
    "0.0.0.0",
    "rippleproof.example",
  ])("disables browser approval on %s", (hostname) =>
    expect(isLoopback(hostname)).toBe(false),
  );
  it.each(["localhost", "127.0.0.1", "[::1]", "::1"])(
    "recognizes exact loopback %s",
    (hostname) => expect(isLoopback(hostname)).toBe(true),
  );
  it.each([401, 404, 409, 422, 503])(
    "safe copy contains no backend secret for %s",
    (status) =>
      expect(
        errorCopy(new ApiError(status, "private-token-value")),
      ).not.toContain("private-token-value"),
  );
  it("only retries transient reads once", () => {
    expect(safeReadRetry(0, new ApiError(503, "database_unavailable"))).toBe(
      true,
    );
    expect(safeReadRetry(1, new ApiError(503, "database_unavailable"))).toBe(
      false,
    );
    expect(safeReadRetry(0, new ApiError(401, "unauthorized"))).toBe(false);
  });
});
