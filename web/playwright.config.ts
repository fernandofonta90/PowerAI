import { defineConfig, devices } from "@playwright/test";

// E2E del frontend. Requiere el backend corriendo en :8000 con el FakeProvider y
// los datos de demo (ver evals/README y la guía de demo). Playwright solo levanta
// el frontend. No corre en CI (orquestar el stack completo es manual/pre-release).
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  // Holgado para la compilación on-demand de rutas en `next dev` en el primer hit.
  expect: { timeout: 35_000 },
  use: {
    baseURL: process.env.POWERAI_WEB_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev",
    url: process.env.POWERAI_WEB_URL ?? "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
