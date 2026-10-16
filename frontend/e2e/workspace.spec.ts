import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir, writeFile } from "node:fs/promises";
import {
  ScenarioResponseSchema,
  GraphSummarySchema,
} from "../src/api/contracts";

const captures =
  process.env.EVIDENCE_DIRECTORY ?? "../.local/verification/browser";
async function simulate(page: Page) {
  await page.goto("/#/workbench");
  const response = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/scenarios/simulate") &&
      r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  const http = await response;
  expect(http.status()).toBe(200);
  // Chromium may evict streamed no-store bodies from DevTools. Validate an
  // identical read-only HTTP calculation and compare its values to the real UI.
  const result = ScenarioResponseSchema.parse(
    await (
      await page.request.post("/api/scenarios/simulate", {
        data: http.request().postDataJSON(),
      })
    ).json(),
  );
  await expect(page.getByTestId("mitigation-count")).toHaveText(
    String(result.mitigated!.on_time_orders.length),
  );
  return result;
}
test("live API contracts, full workbench, per-part certificates, graph and guided MCP", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  const networkFailures: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (e) => {
    if (e.type() === "error") errors.push(e.text());
  });
  page.on("requestfailed", (r) => {
    if (r.failure()?.errorText !== "net::ERR_ABORTED")
      networkFailures.push(r.url());
  });
  const summary = GraphSummarySchema.parse(
    await (await request.get("/api/graph/summary")).json(),
  );
  await page.goto("/");
  await expect(page.getByText("Backend ready", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Physical graph:", { exact: false }),
  ).toContainText(
    `${summary.node_count} nodes / ${summary.relationship_count} edges`,
  );
  await expect(page.getByText("No scenario has been evaluated")).toBeVisible();
  const result = await simulate(page);
  expect(result.baseline.on_time_orders.length).toBe(19);
  expect(result.disrupted.on_time_orders.length).toBe(18);
  expect(result.mitigated!.on_time_orders.length).toBe(20);
  expect(result.estimated_additional_procurement_cost).toBe("1364.00");
  await expect(page.getByText("1,364.00").first()).toBeVisible();
  const graph = page.getByRole("region", { name: "Follow the material path" });
  const actualPath = result.dependency_paths.find(
    (path) => path.nodes.map((n) => n.id).join(",") === "S-04,P-22,PR-05,O-101",
  )!;
  expect(actualPath.relationships.map((edge) => edge.source_id)).toEqual([
    "S-04",
    "PR-05",
    "O-101",
  ]);
  await graph.getByRole("button", { name: "O-101 Order", exact: true }).click();
  await expect(
    page.getByRole("complementary", {
      name: "Material and evidence inspector",
    }),
  ).toContainText("Source record");
  await page
    .getByRole("button", { name: "Return to material constraints" })
    .click();
  await page.getByLabel("Part in focus").selectOption("P-22");
  const inspector = page.getByRole("complementary", {
    name: "Material and evidence inspector",
  });
  const rejected = inspector
    .locator(".candidate-card")
    .filter({ has: page.getByRole("button", { name: "S-10", exact: true }) });
  await expect(rejected).toContainText("Not eligible");
  await expect(rejected).toContainText("C-02");
  await expect(rejected).toContainText("Not held");
  const accepted = inspector
    .locator(".candidate-card")
    .filter({ has: page.getByRole("button", { name: "S-09", exact: true }) });
  await expect(accepted).toContainText("Eligible");
  await page.getByLabel("Part in focus").selectOption("P-12");
  await expect(
    inspector
      .locator(".candidate-card")
      .filter({ has: page.getByRole("button", { name: "S-10", exact: true }) }),
  ).toContainText("Valid on arrival");
  await page.getByLabel("Part in focus").selectOption("P-22");
  await graph.getByRole("button", { name: "Next paths" }).click();
  await expect(graph).toContainText("4–6 of");
  await graph.getByLabel("Search evidence").fill("O-105");
  await expect(graph.locator(".path-list")).toContainText("O-105");
  await graph.getByRole("button", { name: "Fit evidence graph" }).click();
  await graph.getByRole("button", { name: "Reset evidence view" }).click();
  await page.getByRole("button", { name: "Guided MCP tools" }).click();
  await expect(
    page.getByText("Real AI agent not configured for this interface"),
  ).toBeVisible();
  const guidedResponse = page.waitForResponse((r) =>
    r.url().endsWith("/api/agent/run"),
  );
  await page.getByRole("button", { name: "Run guided tools" }).click();
  const guided = await (await guidedResponse).json();
  expect(guided.mode).toBe("guided_walkthrough");
  expect(guided.model_requests).toBe(0);
  expect(guided.tool_trace.length).toBeGreaterThan(0);
  await writeFile(
    `${captures}/live-api-evidence.json`,
    JSON.stringify(
      {
        graph: summary,
        scenario_id: result.scenario_id,
        snapshot_fingerprint: result.snapshot_fingerprint,
        request: result.request,
        materialCovered: {
          baseline: result.baseline.on_time_orders.length,
          disrupted: result.disrupted.on_time_orders.length,
          mitigated: result.mitigated!.on_time_orders.length,
        },
        dependent_orders: result.dependent_orders,
        newly_at_risk_orders: result.newly_at_risk_orders,
        restored_orders: result.restored_orders,
        additional_cost: result.estimated_additional_procurement_cost,
        actualPath,
        candidates: result.candidate_evaluations.filter(
          (c) =>
            ["P-22", "P-12"].includes(c.part_id) &&
            ["S-09", "S-10"].includes(c.supplier_id),
        ),
        proposed_shipments: result.proposed_shipments,
        guided: {
          mode: guided.mode,
          status: guided.status,
          model_requests: guided.model_requests,
          response: guided.response,
          tool_trace: guided.tool_trace,
        },
      },
      null,
      2,
    ),
  );
  await expect(page.locator(".tool-timeline>li")).toHaveCount(
    guided.tool_trace.length,
  );
  await expect(
    page.getByText(/Guided walkthrough · real MCP tools · 0 model calls/),
  ).toBeVisible();
  await mkdir(captures, { recursive: true });
  await page.screenshot({
    path: `${captures}/guided-mcp-desktop.png`,
    fullPage: false,
  });
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Review internal plan" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    result.snapshot_fingerprint,
  );
  await expect(page.getByRole("dialog")).toContainText("1,364.00");
  await expect(
    page.getByRole("button", { name: "Continue to manual approval" }),
  ).toBeDisabled();
  await page.keyboard.press("Shift+Tab");
  expect(
    await page.evaluate(() => !!document.activeElement?.closest("dialog")),
  ).toBe(true);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({
    path: `${captures}/decision-preview-desktop.png`,
    fullPage: false,
  });
  await page.keyboard.press("Escape");
  await page
    .getByRole("link", { name: "Decision Ledger", exact: true })
    .click();
  await expect(page.getByText("No internal decisions yet")).toBeVisible();
  expect(errors).toEqual([]);
  expect(networkFailures).toEqual([]);
});

test("changing inputs clears old outcomes and mitigation off is honored by real engine", async ({
  page,
}) => {
  await simulate(page);
  await page.getByLabel("Evaluate mitigation", { exact: false }).uncheck();
  await expect(page.getByTestId("baseline-count")).toHaveCount(0);
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/scenarios/simulate"),
  );
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  const responseHttp = await response;
  expect(responseHttp.status()).toBe(200);
  const result = ScenarioResponseSchema.parse(
    await (
      await page.request.post("/api/scenarios/simulate", {
        data: responseHttp.request().postDataJSON(),
      })
    ).json(),
  );
  expect(result.mitigated).toBeNull();
  await expect(
    page.getByText("Mitigation disabled", { exact: false }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Review internal plan" }),
  ).toBeDisabled();
});

for (const width of [1440, 1024, 768, 390]) {
  test(`real workbench layout ${width}px, accessibility and keyboard evidence`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await simulate(page);
    await expect(
      page.getByRole("img", { name: /^Graph evidence:/ }),
    ).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(overflow).toBe(false);
    if (width >= 768 && width < 1280) {
      await page
        .getByRole("button", { name: "Open material inspector" })
        .click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.keyboard.press("Escape");
    }
    const accessibility = await new AxeBuilder({ page }).analyze();
    expect(accessibility.violations).toEqual([]);
    await page.screenshot({
      path: `${captures}/workbench-${width}.png`,
      fullPage: true,
    });
    await page.getByRole("link", { name: "Overview", exact: true }).click();
    await expect(page.getByText("Supply interruption")).toBeVisible();
    await page.screenshot({
      path: `${captures}/overview-${width}.png`,
      fullPage: true,
    });
  });
}

test("live invalid dates, unknown supplier and missing decision are safe", async ({
  page,
}) => {
  await page.goto("/#/workbench");
  await page.getByLabel("Outage end · exclusive").fill("2026-10-16");
  await expect(
    page.getByText("The exclusive end must be later than the start."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run scenario", exact: true }),
  ).toBeDisabled();
  await page.getByLabel("Outage end · exclusive").fill("2026-10-24");
  await page.getByLabel("Supplier", { exact: true }).fill("S-999");
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  await expect(
    page.getByText("No matching record was found.", { exact: false }).first(),
  ).toBeVisible();
  await expect(page.getByTestId("baseline-count")).toHaveCount(0);
  await page.goto("/#/decisions/D-000000000000000000000000");
  await expect(page.getByRole("dialog")).toContainText(
    "No matching record was found.",
  );
});
