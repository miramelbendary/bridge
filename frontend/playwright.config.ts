import path from "node:path";
import os from "node:os";

import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against a real backend (fresh SQLite database + demo data, mock AI) and the
 * production frontend build. Run `npm run build` first.
 *
 *   BRIDGE_PYTHON      Python with backend dependencies installed (default: "python")
 *   BRIDGE_BACKEND_DIR path to ../backend (default: ../backend)
 *   PW_CHANNEL         e.g. "msedge" or "chrome" to use an installed browser instead of
 *                      Playwright's own Chromium (useful on Windows without `playwright install`)
 */
const python = process.env.BRIDGE_PYTHON ?? "python";
const backendDir = process.env.BRIDGE_BACKEND_DIR ?? path.resolve(__dirname, "../backend");
const dbFile = path.join(os.tmpdir(), `bridge-e2e-${process.pid}.db`).replace(/\\/g, "/");

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:3101",
    trace: "retain-on-failure",
    ...(process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {}),
  },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"], channel: process.env.PW_CHANNEL } }],
  webServer: [
    {
      command: `"${python}" -m app.cli setup && "${python}" -m uvicorn app.main:create_app --factory --port 8101`,
      cwd: backendDir,
      url: "http://127.0.0.1:8101/health/ready",
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        DATABASE_URL: `sqlite:///${dbFile}`,
        LOCAL_JWT_SECRET: "e2e-only-secret-0123456789-abcdefghijklmnopqrstuv",
        ENVIRONMENT: "development",
        AI_PROVIDER: "mock",
        AUTH_RATE_LIMIT_ATTEMPTS: "1000",
      },
    },
    {
      command: "npm run start -- -p 3101",
      url: "http://127.0.0.1:3101/login",
      timeout: 120_000,
      reuseExistingServer: false,
      env: { BRIDGE_API_URL: "http://127.0.0.1:8101", BRIDGE_DEMO_MODE: "1", NEXT_TELEMETRY_DISABLED: "1" },
    },
  ],
});
