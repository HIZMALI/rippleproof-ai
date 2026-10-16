import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { ApprovalRequest } from "../src/api/contracts";
import { HistorySchema } from "../src/api/client";

const base = "http://127.0.0.1:18081";
const python = resolve(
  "..",
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const artifact =
  process.env.EVIDENCE_DIRECTORY ?? "../.local/verification/browser";
function control(action: string) {
  execFileSync(python, ["../scripts/phase4_test_backend.py", action], {
    stdio: "pipe",
    timeout: 30000,
  });
}
async function token(): Promise<string> {
  // Node-side test runner only; never a Vite environment variable or trace.
  return JSON.parse(
    await readFile("../.local/phase4-browser-state.json", "utf8"),
  ).token;
}
async function review(page: Page) {
  await page.goto(`${base}/#/workbench`);
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  await expect(page.getByTestId("mitigation-count")).toBeVisible();
  await page.getByRole("button", { name: "Review internal plan" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Full proposed schedule",
  );
}
async function authorize(page: Page, value: string) {
  await page
    .getByLabel("I have reviewed the full schedule", { exact: false })
    .check();
  await page
    .getByRole("button", { name: "Continue to manual approval" })
    .click();
  await page.getByLabel("Operator pseudonym").fill("browser-test-harness");
  await page
    .getByLabel("Decision rationale")
    .fill(
      "Isolated automated browser acceptance; not a human approval or purchase.",
    );
  await page
    .getByLabel("Type APPROVE INTERNAL to confirm")
    .fill("APPROVE INTERNAL");
  await page.getByLabel("Local operator token").fill(value);
}
test.beforeEach(() => {
  control("normal");
  control("restore");
});
test.afterEach(() => {
  control("restore");
  control("normal");
});

test("isolated real persistence, lost-response retry, exact intent key and restart", async ({
  page,
}) => {
  const before = await (await page.request.get(`${base}/api/decisions`)).json();
  const sourceBefore = await (
    await page.request.get(`${base}/api/graph/summary`)
  ).json();
  await review(page);
  const preview = await (
    await page.request.post(`${base}/api/decisions/prepare`, {
      data: {
        scenario: {
          supplier_id: "S-04",
          as_of: "2026-10-15",
          outage_start: "2026-10-16",
          outage_end_exclusive: "2026-10-24",
          include_mitigation: true,
        },
        mitigation_plan_id: "cost_first",
      },
    })
  ).json();
  let first: ApprovalRequest | undefined;
  let second: ApprovalRequest | undefined;
  let actualRecord: { decision_id: string } | undefined;
  // Inject a lost browser response AFTER the real backend commits successfully.
  // No fake result: replay must retrieve that actual FalkorDB decision.
  await page.route(
    "**/api/decisions/approve",
    async (route) => {
      first = route.request().postDataJSON();
      const response = await route.fetch();
      expect(response.status()).toBe(200);
      actualRecord = await response.json();
      await route.abort("connectionreset");
    },
    { times: 1 },
  );
  await authorize(page, await token());
  await page
    .getByRole("button", {
      name: "Approve internal planning record",
      exact: true,
    })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Data source unavailable",
  );
  await expect(page.getByLabel("Local operator token")).toHaveValue("");
  const afterLostResponse = await (
    await page.request.get(`${base}/api/decisions`)
  ).json();
  expect(afterLostResponse.total).toBe(before.total + 1);
  page.on("request", (request) => {
    if (request.url().endsWith("/api/decisions/approve"))
      second = request.postDataJSON();
  });
  await page.getByLabel("Local operator token").fill(await token());
  await page
    .getByRole("button", {
      name: "Approve internal planning record",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Internal decision recorded" }),
  ).toBeVisible();
  await expect(
    page.getByText("Verified after saving:", { exact: false }),
  ).toBeVisible();
  expect(second).toEqual(first);
  const after = await (await page.request.get(`${base}/api/decisions`)).json();
  expect(after.total).toBe(before.total + 1);
  const sourceAfter = await (
    await page.request.get(`${base}/api/graph/summary`)
  ).json();
  expect(sourceAfter.node_count).toBe(sourceBefore.node_count + 2);
  expect(sourceAfter.relationship_count).toBe(
    sourceBefore.relationship_count + 150,
  );
  const stored = await (
    await page.request.get(`${base}/api/decisions/${actualRecord!.decision_id}`)
  ).json();
  expect(stored.preview.scenario_id).toBe(preview.scenario_id);
  expect(stored.preview.operational_fingerprint).toBe(
    preview.operational_fingerprint,
  );
  await page.getByRole("button", { name: "View persisted record" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    actualRecord!.decision_id,
  );
  await page.getByRole("button", { name: "Check current source" }).click();
  await expect(
    page.getByText("Current source and plan revisions match this record."),
  ).toBeVisible();
  await mkdir(artifact, { recursive: true });
  await page.screenshot({ path: `${artifact}/isolated-persisted-record.png` });
  const storage = await page.evaluate(() => ({
    local: { ...localStorage },
    session: { ...sessionStorage },
    cookies: document.cookie,
    url: location.href,
  }));
  expect(JSON.stringify(storage)).not.toContain(await token());
  expect(storage.local).toEqual({});
  expect(storage.session).toEqual({});
  control("restart");
  await page.reload();
  await expect(page.getByRole("dialog")).toContainText(
    actualRecord!.decision_id,
  );
  const replay = await (
    await page.request.get(`${base}/api/decisions/${actualRecord!.decision_id}`)
  ).json();
  expect(replay).toEqual(stored);
  await writeFile(
    `${artifact}/isolated-persistence.json`,
    JSON.stringify(
      {
        testOnly: true,
        operator: "browser-test-harness",
        decision_id: actualRecord!.decision_id,
        scenario_id: preview.scenario_id,
        operational_fingerprint: preview.operational_fingerprint,
        before: {
          nodes: sourceBefore.node_count,
          relationships: sourceBefore.relationship_count,
        },
        after: {
          nodes: sourceAfter.node_count,
          relationships: sourceAfter.relationship_count,
        },
        oneRecordDespiteLostResponse: true,
        exactIntentReplay: first?.idempotency_key === second?.idempotency_key,
        retrievedAfterBackendRestart: true,
        browserStorageEmpty: true,
      },
      null,
      2,
    ),
  );
});

test("isolated stale source returns 409, erases inputs and forces fresh review", async ({
  page,
}) => {
  await review(page);
  await authorize(page, await token());
  control("stale");
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/decisions/approve"),
  );
  await page
    .getByRole("button", {
      name: "Approve internal planning record",
      exact: true,
    })
    .click();
  expect((await response).status()).toBe(409);
  await expect(page.getByRole("dialog")).toContainText(
    "Approval inputs were discarded.",
  );
  await expect(
    page.getByLabel("I have reviewed the full schedule", { exact: false }),
  ).not.toBeChecked();
  await expect(
    page.getByRole("button", { name: "Continue to manual approval" }),
  ).toBeDisabled();
  await expect(page.getByLabel("Local operator token")).toHaveCount(0);
  await expect(page.getByTestId("baseline-count")).toHaveCount(0);
  await page.screenshot({ path: `${artifact}/isolated-stale-preview.png` });
});

test("real 401 clears the transient credential and close/navigation discard it", async ({
  page,
}) => {
  await review(page);
  await authorize(page, "invalid-test-token");
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/decisions/approve"),
  );
  await page
    .getByRole("button", {
      name: "Approve internal planning record",
      exact: true,
    })
    .click();
  expect((await response).status()).toBe(401);
  await expect(page.getByRole("dialog")).toContainText(
    "Authorization was not accepted.",
  );
  await expect(page.getByLabel("Local operator token")).toHaveValue("");
  await page.getByLabel("Local operator token").fill(await token());
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Review internal plan" }).click();
  await expect(page.getByLabel("Local operator token")).toHaveCount(0);
  await authorize(page, await token());
  await page.evaluate(() => {
    window.location.hash = "/decisions";
  });
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("real validation 422 on a tampered wire request is safe and clears token", async ({
  page,
}) => {
  await review(page);
  await authorize(page, await token());
  await page.route(
    "**/api/decisions/approve",
    async (route) => {
      const body = {
        ...route.request().postDataJSON(),
        confirm_internal_decision: false,
      };
      const response = await route.fetch({ postData: JSON.stringify(body) });
      expect(response.status()).toBe(422);
      await route.fulfill({ response });
    },
    { times: 1 },
  );
  await page
    .getByRole("button", {
      name: "Approve internal planning record",
      exact: true,
    })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "The request could not be validated.",
  );
  await expect(page.getByLabel("Local operator token")).toHaveValue("");
});

test("real disabled approval and unauthorized provider return 503 without a model call", async ({
  page,
}) => {
  control("approval-disabled");
  await review(page);
  await authorize(page, "test-token-not-configured");
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/decisions/approve"),
  );
  await page
    .getByRole("button", {
      name: "Approve internal planning record",
      exact: true,
    })
    .click();
  expect((await response).status()).toBe(503);
  await expect(page.getByRole("dialog")).toContainText("Approval unavailable.");
  await expect(page.getByLabel("Local operator token")).toHaveValue("");
  const provider = await page.request.post(`${base}/api/agent/run`, {
    data: {
      mode: "agent",
      question: "test authorization gate",
      scenario: {
        supplier_id: "S-04",
        as_of: "2026-10-15",
        outage_start: "2026-10-16",
        outage_end_exclusive: "2026-10-24",
        include_mitigation: true,
      },
    },
  });
  expect(provider.status()).toBe(503);
  expect((await provider.json()).model_requests).toBe(0);
});

test("real empty graph, unavailable database and backend restart hide stale calculations", async ({
  page,
}) => {
  control("empty");
  await page.goto(`${base}/#/workbench`);
  await expect(page.getByText("Backend ready · graph empty")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run scenario", exact: true }),
  ).toBeDisabled();
  await expect(page.getByTestId("baseline-count")).toHaveCount(0);
  control("normal");
  await page.reload();
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  await expect(page.getByTestId("mitigation-count")).toHaveText("20");
  control("unavailable");
  await expect(
    page.getByText("Backend unavailable", { exact: true }),
  ).toBeVisible({ timeout: 25000 });
  await expect(page.getByTestId("baseline-count")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Run scenario", exact: true }),
  ).toBeDisabled();
  await page.screenshot({ path: `${artifact}/isolated-unavailable.png` });
  control("normal");
  await expect(page.getByText("Backend ready", { exact: true })).toBeVisible({
    timeout: 25000,
  });
  await expect(page.getByTestId("baseline-count")).toHaveCount(0);
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  await expect(page.getByTestId("mitigation-count")).toHaveText("20");
});

test("isolated ledger shows actual paged records, filters and historical details", async ({
  page,
}) => {
  const history = HistorySchema.parse(
    await (await page.request.get(`${base}/api/decisions`)).json(),
  );
  const record = await (
    await page.request.get(
      `${base}/api/decisions/${history.items[0]!.decision_id}`,
    )
  ).json();
  const preview = record.preview;
  for (let index = 0; index < 6; index++) {
    const saved = await page.request.post(`${base}/api/decisions/approve`, {
      headers: { Authorization: `Bearer ${await token()}` },
      data: {
        scenario: preview.scenario,
        mitigation_plan_id: preview.mitigation_plan_id,
        expected_scenario_id: preview.scenario_id,
        expected_operational_fingerprint: preview.operational_fingerprint,
        expected_plan_revision: preview.plan_revision,
        idempotency_key: `phase4-ledger-paging-${index}`,
        operator_id: "browser-test-harness",
        rationale:
          "Isolated automated paging test, not human approval or procurement.",
        confirm_internal_decision: true,
      },
    });
    expect(saved.status()).toBe(200);
  }
  await page.goto(`${base}/#/decisions`);
  await expect(page.locator(".ledger-row")).toHaveCount(5);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".ledger-row")).toHaveCount(2);
  await page.getByRole("button", { name: "Previous", exact: true }).click();
  await expect(page.locator(".ledger-row")).toHaveCount(5);
  await page
    .getByLabel("Filter by scenario ID")
    .fill("SC-00000000000000000000");
  await page.getByRole("button", { name: "Apply filter" }).click();
  await expect(page.getByText("No decisions for this scenario")).toBeVisible();
  await page.getByRole("button", { name: "All records" }).click();
  await expect(page.locator(".ledger-row")).toHaveCount(5);
  await page.screenshot({
    path: `${artifact}/isolated-decision-ledger.png`,
    fullPage: true,
  });
});
