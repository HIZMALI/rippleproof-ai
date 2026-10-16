import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { ScenarioResponseSchema } from "../src/api/contracts";

test("actual Docker backend stop/start: no stale success, recovery and source persistence", async ({
  page,
}) => {
  test.setTimeout(90000);
  const docker = (...args: string[]) =>
    execFileSync("docker", ["compose", ...args], {
      cwd: "..",
      stdio: "pipe",
      timeout: 25000,
    });
  await page.goto("/#/workbench");
  const firstResponse = page.waitForResponse((r) =>
    r.url().endsWith("/api/scenarios/simulate"),
  );
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  const firstHttp = await firstResponse;
  expect(firstHttp.status()).toBe(200);
  const first = ScenarioResponseSchema.parse(
    await (
      await page.request.post("/api/scenarios/simulate", {
        data: firstHttp.request().postDataJSON(),
      })
    ).json(),
  );
  await expect(page.getByTestId("mitigation-count")).toBeVisible();
  const before = await (await page.request.get("/api/graph/summary")).json();
  try {
    docker("stop", "--timeout", "3", "backend");
    await page.getByRole("button", { name: "Rerun current scenario" }).click();
    await expect(
      page.getByText("Backend unavailable", { exact: true }),
    ).toBeVisible();
    await expect(page.getByTestId("baseline-count")).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Run scenario", exact: true }),
    ).toBeDisabled();
  } finally {
    docker("start", "backend");
  }
  await expect(page.getByText("Backend ready", { exact: true })).toBeVisible({
    timeout: 25000,
  });
  await expect(page.getByTestId("baseline-count")).toHaveCount(0);
  const secondResponse = page.waitForResponse((r) =>
    r.url().endsWith("/api/scenarios/simulate"),
  );
  await page.getByRole("button", { name: "Run scenario", exact: true }).click();
  const secondHttp = await secondResponse;
  expect(secondHttp.status()).toBe(200);
  const second = ScenarioResponseSchema.parse(
    await (
      await page.request.post("/api/scenarios/simulate", {
        data: secondHttp.request().postDataJSON(),
      })
    ).json(),
  );
  await expect(page.getByTestId("mitigation-count")).toHaveText(
    String(second.mitigated!.on_time_orders.length),
  );
  const after = await (await page.request.get("/api/graph/summary")).json();
  expect(after).toEqual(before);
  expect(second).toEqual(first);
  await writeFile(
    `${process.env.EVIDENCE_DIRECTORY ?? "../docs/verification/phase4"}/production-restart.json`,
    JSON.stringify(
      {
        services:
          "actual Docker Compose backend stopped and started; FalkorDB volume untouched",
        before,
        after,
        scenario_id: second.scenario_id,
        snapshot_fingerprint: second.snapshot_fingerprint,
        outcomesEqual: true,
        staleAnalysisHiddenDuringOutage: true,
        recoveredWithoutReseeding: true,
      },
      null,
      2,
    ),
  );
});
