/** Capture the actual production workspace; no DOM/content or image editing. */
import { chromium, expect } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

const directory =
  process.env.EVIDENCE_DIRECTORY ?? "../.local/verification/browser";
const origin = process.env.WEB_ORIGIN ?? "http://127.0.0.1:18080";
const browser = await chromium.launch();
const errors = [];
await mkdir(directory, { recursive: true });
async function top(page) {
  // Axe may leave a skip link focused; capture the neutral pointer state.
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement)
      document.activeElement.blur();
    window.scrollTo(0, 0);
  });
}
try {
  for (const width of [1440, 1024, 768, 390]) {
    const page = await browser.newPage({
      viewport: { width, height: 1000 },
      reducedMotion: "reduce",
    });
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    await page.goto(`${origin}/#/workbench`);
    await page
      .getByRole("button", { name: "Run scenario", exact: true })
      .click();
    await expect(page.getByTestId("mitigation-count")).toBeVisible();
    await expect(
      page.getByRole("img", { name: /^Graph evidence:/ }),
    ).toBeVisible();
    await top(page);
    await page.screenshot({
      path: `${directory}/workbench-${width}.png`,
      fullPage: true,
    });
    await page.screenshot({
      path: `${directory}/workbench-${width}-viewport.png`,
    });
    if (width === 1024) {
      await page
        .getByRole("button", { name: "Open material inspector" })
        .click();
      await page.screenshot({ path: `${directory}/tablet-inspector.png` });
      await page.keyboard.press("Escape");
    }
    if (width === 390) {
      await page
        .getByRole("region", { name: "Follow the material path" })
        .evaluate((element) => element.scrollIntoView({ block: "start" }));
      await page.screenshot({ path: `${directory}/mobile-evidence.png` });
    }
    await page.getByRole("link", { name: "Overview", exact: true }).click();
    await expect(page.getByText("Supply interruption")).toBeVisible();
    await top(page);
    await page.screenshot({
      path: `${directory}/overview-${width}.png`,
      fullPage: true,
    });
    await page.screenshot({
      path: `${directory}/overview-${width}-viewport.png`,
    });
    await page.close();
  }
  if (errors.length)
    throw new Error(`Browser reported ${errors.length} errors`);
  await writeFile(
    `${directory}/visual-review.json`,
    JSON.stringify(
      {
        origin,
        widths: [1440, 1024, 768, 390],
        viewportHeight: 1000,
        browser: browser.version(),
        consoleErrors: errors,
        pageErrors: [],
        content:
          "Actual API-connected production UI, no image/DOM content substitution",
      },
      null,
      2,
    ),
  );
  process.stdout.write(
    "Captured actual production layouts at 1440 / 1024 / 768 / 390 px; zero console/page errors.\n",
  );
} finally {
  await browser.close();
}
