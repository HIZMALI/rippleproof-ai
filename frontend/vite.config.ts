import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const target = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:18000";
// These are server-only proxy settings. No backend/provider secrets are loaded.
const proxy = {
  "/api": { target },
  "/health": { target },
  "/openapi.json": { target },
};

export default defineConfig({
  plugins: [react()],
  server: { proxy, forwardConsole: false },
  preview: { proxy },
  build: { sourcemap: false },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
