import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { mkdir, writeFile } from "node:fs/promises";

const python = resolve(
  "..",
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const artifact =
  process.env.EVIDENCE_DIRECTORY ?? "../docs/verification/phase5a";
function control(action: string) {
  execFileSync(python, ["../scripts/phase4_test_backend.py", action], {
    stdio: "pipe",
    timeout: 30000,
  });
}
test.afterEach(() => control("normal"));
test("disabled provider browser gate makes zero agent POSTs", async ({
  page,
}) => {
  const modes: string[] = [];
  page.on("request", (r) => {
    if (r.url().endsWith("/api/agent/run")) modes.push(r.postDataJSON().mode);
  });
  await page.goto("/#/workbench");
  await page.getByRole("button", { name: "Guided MCP tools" }).click();
  await expect(
    page.getByRole("button", { name: "Run real agent" }),
  ).toBeDisabled();
  const response = await page.request.get("/api/agent/capabilities");
  expect((await response.json()).execution_kind).toBe("disabled");
  expect(modes).toEqual([]);
});
test("controlled model simulator selects actual MCP tools from an isolated graph; no remote LLM", async ({
  page,
}) => {
  control("controlled-agent");
  await page.goto("http://127.0.0.1:18081/#/workbench");
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  await expect(page.getByTestId("mitigation-count")).toHaveText("20");
  await page.getByRole("button", { name: "Guided MCP tools" }).click();
  await expect(
    page.getByText("Controlled provider simulation — not a remote LLM"),
  ).toBeVisible();
  await page
    .getByLabel(
      "I understand this is a controlled model simulator, not a remote LLM.",
    )
    .check();
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/agent/run"),
  );
  await page.getByRole("button", { name: "Run controlled test agent" }).click();
  const result = await (await response).json();
  expect(result.mode).toBe("agent");
  expect(result.provider).toBe("mock-provider");
  expect(result.model_requests).toBe(4);
  expect(result.tool_trace.map((t: { name: string }) => t.name)).toEqual([
    "trace_supplier_impact",
    "simulate_supply_disruption",
    "evaluate_part_alternatives",
  ]);
  await expect(
    page.getByText(
      /Controlled provider simulation · real MCP tools · 4 model calls/,
    ),
  ).toBeVisible();
  await expect(page.locator(".tool-timeline>li")).toHaveCount(3);
  await expect(
    page.getByRole("button", { name: "Run controlled test agent" }),
  ).toBeDisabled();
  await mkdir(artifact, { recursive: true });
  await page.screenshot({
    path: `${artifact}/controlled-agent-test.png`,
  });
  await writeFile(
    `${artifact}/controlled-agent-test.json`,
    JSON.stringify(
      { kind: "MODEL SIMULATOR, NOT REMOTE LLM", ...result },
      null,
      2,
    ),
  );
});
