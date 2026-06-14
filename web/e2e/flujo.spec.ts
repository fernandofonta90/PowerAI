import { expect, test } from "@playwright/test";

// Flujo feliz + RBAC. Requiere backend en :8000 (FakeProvider) con datos de demo
// (uv run python -m app.scripts.seed_demo). El FakeProvider en modo demo ejecuta
// "saldo por cliente", de modo que el contenido cambia según el alcance del usuario.

const SELECTOR_USUARIO = "Seleccionar usuario de prueba";

async function elegirUsuario(page: import("@playwright/test").Page, email: string) {
  await page.getByLabel(SELECTOR_USUARIO).selectOption(email);
}

test("flujo feliz: usuario MX → home → chip → respuesta con citación", async ({ page }) => {
  await page.goto("/");
  await elegirUsuario(page, "uploader.mx@powerai.dev");

  // Click en el primer chip de pregunta sugerida.
  await page.locator("button.rounded-pill").filter({ hasText: "cartera" }).first().click();

  // Llega a la conversación: respuesta del asistente con bloque de citación.
  await expect(page).toHaveURL(/\/chat\//);
  await expect(page.getByText("Fuentes", { exact: false })).toBeVisible();
  // Datos de MX: GLOBEX es cliente de México.
  await expect(page.getByText("GLOBEX")).toBeVisible();
});

test("RBAC: al cambiar a usuario CO, los datos de MX ya no son visibles", async ({ page }) => {
  await page.goto("/");
  await elegirUsuario(page, "consulta.co@powerai.dev");

  await page.locator("button.rounded-pill").filter({ hasText: "cartera" }).first().click();
  await expect(page).toHaveURL(/\/chat\//);
  await expect(page.getByText("Fuentes", { exact: false })).toBeVisible();

  // El usuario de CO ve clientes de Colombia, nunca los de México.
  await expect(page.getByText("CONACO")).toBeVisible();
  await expect(page.getByText("GLOBEX")).toHaveCount(0);
});
