import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";

const python = resolve(
  "..",
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90000,
  expect: { timeout: 15000 },
  reporter: [["list"], ["json", { outputFile: "test-results/results.json" }]],
  use: {
    baseURL: process.env.WEB_ORIGIN ?? "http://127.0.0.1:18080",
    browserName: "chromium",
    viewport: { width: 1440, height: 1100 },
    // Approval credentials must never enter Playwright traces, HAR or video.
    trace: "off",
    screenshot: "off",
    video: "off",
  },
  webServer: [
    {
      command: `"${python}" ../scripts/phase4_test_backend.py serve`,
      url: "http://127.0.0.1:18001/health",
      reuseExistingServer: false,
      timeout: 45000,
    },
    {
      command: "npm run dev -- --port 18081",
      url: "http://127.0.0.1:18081",
      env: { BACKEND_ORIGIN: "http://127.0.0.1:18001" },
      reuseExistingServer: false,
    },
  ],
});
