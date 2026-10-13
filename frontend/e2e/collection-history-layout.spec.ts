import { expect, test } from "@playwright/test";

test("expanding a long collection error preserves table and column widths", async ({ page }) => {
  const error = `Autenticação: Locator.wait_for: strict mode violation\n${"Texto de diagnóstico extenso. ".repeat(80)}\nhttps://pje1g.tjrn.jus.br/${"recurso-sem-espacos".repeat(150)}`;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("auth/me/")) return route.fulfill({ json: { id: 1, display_name: "Operador", theme: "light" } });
    if (path.endsWith("automation/history/")) return route.fulfill({ json: {
      days: [{ date: "2026-10-13", runs: [{
        id: 12, status: "failed", status_label: "Erro", trigger_label: "Manual",
        created_at: "2026-10-13T10:00:00Z", started_at: "2026-10-13T10:00:00Z", duration_seconds: 60,
        found: 0, created: 0, updated: 0, resolved: 0, error,
        source: { code: "pje-tjrn", system: "PJe 1º Grau", tribunal: "TJRN" },
      }] }],
    } });
    if (path.endsWith("notices/")) return route.fulfill({ json: { count: 0, results: [] } });
    return route.fulfill({ json: { available: true } });
  });
  await page.goto("/historico?tab=orquestracao");
  const toggle = page.getByRole("button", { name: "Ver erro" });
  await expect(toggle).toBeVisible();
  const table = page.getByRole("table");
  const measure = () => table.evaluate((element) => ({
    width: element.getBoundingClientRect().width,
    scrollWidth: element.parentElement!.scrollWidth,
    columns: Array.from(element.querySelectorAll("th"), (cell) => ({
      left: cell.getBoundingClientRect().left - element.getBoundingClientRect().left,
      width: cell.getBoundingClientRect().width,
    })),
  }));
  const before = await measure();
  await toggle.click();
  const alert = page.getByRole("alert").filter({ hasText: "Locator.wait_for" });
  await expect(alert).toHaveText(error);
  await expect.poll(measure).toEqual(before);
  expect(await alert.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  await toggle.click();
  await expect(alert).toHaveCount(0);
  expect(await measure()).toEqual(before);
});
