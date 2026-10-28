import { expect, test } from "@playwright/test";

test("both attorneys remain visible with individual collection states", async ({ page }) => {
  const requests: unknown[] = [];
  let started = false;
  const collectors = [
    { code: "murilo", label: "DR. MURILO", enabled: true, pin_configured: true, totp_configured: true, state: "success", last_success_at: "2026-10-26T10:00:00Z", error: "" },
    { code: "cristiano", label: "DR. CRISTIANO", enabled: true, pin_configured: true, totp_configured: true, state: "blocked", last_success_at: null, error: "PIN rejeitado" },
  ];
  const currentCollectors = () => collectors.map((collector) => started && collector.code === "cristiano"
    ? { ...collector, state: "pending", error: "" } : collector);
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("automation/runs/") && route.request().method() === "POST") {
      requests.push(route.request().postDataJSON());
      started = true;
      return route.fulfill({ status: 202, json: { id: 10, status: "pending" } });
    }
    if (path.endsWith("auth/me/")) return route.fulfill({ json: { id: 1, display_name: "Operador", theme: "light" } });
    if (path.endsWith("dashboard/")) return route.fulfill({ json: {
      display_name: "Operador", today: { new: 0, updated: 0, unread: 0, urgent: 0, next_week: 0, calculating: 0, discardable: 0 },
      collection_pipeline: {
        collectors: currentCollectors(), collector_scope: started ? "cristiano" : null,
        status: started ? "running" : "failed", active: started, completed: 1, total: 2,
        finished_at: null, current_step: started ? "pje-tjrn" : null, current_collector: started ? "cristiano" : null,
        steps: [
          { code: "pje-tjrn", collector: "murilo", group: "DR. MURILO · TJRN", label: "DR. MURILO · 1º Grau", status: "success", run_id: 1, error: "", message: "" },
          { code: "pje-tjrn", collector: "cristiano", group: "DR. CRISTIANO · TJRN", label: "DR. CRISTIANO · 1º Grau", status: started ? "pending" : "failed", run_id: started ? 10 : 2, error: "", message: "" },
        ],
      },
    } });
    if (path.endsWith("settings/")) return route.fulfill({ json: { display_name: "Operador", theme: "light", collection_time: "06:00", credential_status: { credential_file: true }, collectors: currentCollectors() } });
    if (path.endsWith("sources/")) return route.fulfill({ json: [] });
    if (path.endsWith("expedientes/") || path.endsWith("notices/")) return route.fulfill({ json: { count: 0, results: [] } });
    return route.fulfill({ json: { available: true } });
  });
  await page.goto("/");
  await expect(page.getByLabel("Titulares de coleta").getByText("DR. MURILO", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Titulares de coleta").getByText("DR. CRISTIANO", { exact: true })).toBeVisible();
  await expect(page.getByText("Credencial suspensa neste ciclo", { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 375, height: 812 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await expect(page.getByRole("button", { name: "Executar coleta" })).toBeDisabled();
  await page.getByRole("combobox", { name: "Coletar para" }).selectOption("cristiano");
  await page.getByRole("button", { name: "Executar coleta" }).click();
  await expect.poll(() => requests.length).toBe(1);
  expect(requests).toEqual([{ source: "pje-tjrn", collector: "cristiano" }]);
  await expect(page.getByText("Ciclo individual: DR. CRISTIANO.", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Titulares de coleta").getByText("Na fila", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Titulares de coleta").getByText("Última fonte concluída", { exact: true })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Coletar para" })).toBeDisabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await page.screenshot({ path: `test-results/collector-scope-${test.info().project.name}.png`, fullPage: true });
  await page.goto("/configuracoes");
  await expect(page.getByText("DR. CRISTIANO", { exact: true })).toBeVisible();
  await expect(page.getByText("Nenhuma fonte concluída para este titular.", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});
