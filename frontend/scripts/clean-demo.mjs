/** Read-only browser walkthrough of a fresh isolated Docker installation. */
import { chromium, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
const [origin, folder] = process.argv.slice(2);
if (!origin || !folder)
  throw new Error("Provide isolated web origin and output directory");
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (e) => {
  if (e.type() === "error") errors.push(e.text());
});
try {
  await mkdir(folder, { recursive: true });
  await page.goto(`${origin}/#/workbench`);
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  await expect(page.getByTestId("baseline-count")).toHaveText("19");
  await expect(page.getByTestId("disruption-count")).toHaveText("18");
  await expect(page.getByTestId("mitigation-count")).toHaveText("20");
  await expect(
    page.getByRole("img", { name: /^Graph evidence:/ }),
  ).toBeVisible();
  await page.getByLabel("Part in focus").selectOption("P-22");
  const inspector = page.getByRole("complementary", {
    name: "Material and evidence inspector",
  });
  await expect(
    inspector
      .locator(".candidate-card")
      .filter({ has: page.getByRole("button", { name: "S-10", exact: true }) }),
  ).toContainText("Not held");
  await page.getByLabel("Part in focus").selectOption("P-12");
  await expect(
    inspector
      .locator(".candidate-card")
      .filter({ has: page.getByRole("button", { name: "S-10", exact: true }) }),
  ).toContainText("Valid on arrival");
  await page.getByRole("button", { name: "Guided MCP tools" }).click();
  await expect(
    page.getByRole("button", { name: "Run real agent" }),
  ).toBeDisabled();
  const reply = page.waitForResponse((r) => r.url().endsWith("/api/agent/run"));
  await page.getByRole("button", { name: "Run guided tools" }).click();
  const guided = await (await reply).json();
  if (guided.model_requests !== 0 || guided.mode !== "guided_walkthrough")
    throw new Error("Unexpected model invocation");
  await expect(page.locator(".tool-timeline>li")).toHaveCount(4);
  await page.screenshot({ path: `${folder}/clean-guided.png` });
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Review internal plan" }).click();
  await expect(page.getByRole("dialog")).toContainText("1,364.00");
  await expect(
    page.getByRole("button", { name: "Continue to manual approval" }),
  ).toBeDisabled();
  await page.keyboard.press("Escape");
  await page
    .getByRole("link", { name: "Decision Ledger", exact: true })
    .click();
  await expect(page.getByText("No internal decisions yet")).toBeVisible();
  if (errors.length) throw new Error(`Browser errors: ${errors.length}`);
  process.stdout.write(
    JSON.stringify({
      passed: true,
      coverage: [19, 18, 20],
      graph: true,
      per_part_certificates: true,
      guided_mcp_steps: 4,
      model_requests: 0,
      read_only_preview: true,
      ledger_empty: true,
      console_errors: errors,
    }),
  );
} finally {
  await browser.close();
}
