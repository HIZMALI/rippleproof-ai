/** Actual provider-disabled UI and accessibility checks; sends no model intent. */
import { chromium, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir, writeFile } from "node:fs/promises";

const folder = "../docs/verification/phase5a/agent-layouts";
const browser = await chromium.launch();
const results = [];
const agentRequests = [];
try {
  await mkdir(folder, { recursive: true });
  for (const width of [1440, 1024, 768, 390]) {
    const context = await browser.newContext({
      viewport: { width, height: 1000 },
    });
    const page = await context.newPage();
    page.on("request", (r) => {
      if (r.url().endsWith("/api/agent/run")) agentRequests.push(r.url());
    });
    await page.goto("http://127.0.0.1:18080/#/workbench");
    await page.getByRole("button", { name: "Guided MCP tools" }).click();
    const button = page.getByRole("button", { name: "Run real agent" });
    await expect(button).toBeDisabled();
    await expect(page.getByText(/Bounds: 6 model requests/)).toBeVisible();
    await button.scrollIntoViewIfNeeded();
    const axe = await new AxeBuilder({ page }).include("dialog").analyze();
    if (axe.violations.length)
      throw new Error(`Accessibility failure at ${width}px`);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    if (overflow) throw new Error(`Horizontal overflow at ${width}px`);
    await page.screenshot({ path: `${folder}/agent-disabled-${width}.png` });
    results.push({
      width,
      disabled: true,
      axe_violations: 0,
      horizontal_overflow: false,
    });
    await context.close();
  }
  if (agentRequests.length) throw new Error("Unexpected model intent");
  const report = {
    actual_production_ui: true,
    agent_post_requests: 0,
    results,
  };
  await writeFile(`${folder}/checks.json`, JSON.stringify(report, null, 2));
  process.stdout.write(JSON.stringify(report));
} finally {
  await browser.close();
}
