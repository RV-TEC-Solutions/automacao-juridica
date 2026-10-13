import { expect, test } from "@playwright/test";

for (const source of [
  { code: "trt21", group: "TRT21", label: "1º Grau", name: "TRT21 · 1º Grau", href: "https://pje.trt21.jus.br/primeirograu/login.seam" },
  { code: "tre-rn-2g", group: "Justiça Eleitoral", label: "TRE-RN · 2º Grau", name: "TRE-RN · 2º Grau", href: "https://www.tre-rn.jus.br/servicos-judiciais/processos/processo-judicial-eletronico" },
  { code: "djen", group: "DJEN", label: "Publicações nacionais", name: "DJEN", href: "https://comunica.pje.jus.br/" },
]) {
  test(`failed ${source.code} opens orchestration and offers manual consultation`, async ({ page }) => {
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("auth/me/")) return route.fulfill({ json: { id: 1, display_name: "Operador", theme: "light" } });
      if (path.endsWith("dashboard/")) return route.fulfill({ json: {
        display_name: "Operador", today: { new: 0, updated: 0, unread: 0, urgent: 0, next_week: 0, calculating: 0, discardable: 0 },
        collection_pipeline: { status: "failed", active: false, completed: 0, total: 1, finished_at: null, current_step: null,
          steps: [{ ...source, status: "failed", run_id: 1, error: "Falha de autenticação", message: "" }] },
      } });
      if (path.endsWith("automation/history/")) return route.fulfill({ json: { days: [] } });
      if (path.endsWith("expedientes/") || path.endsWith("notices/")) return route.fulfill({ json: { count: 0, results: [] } });
      return route.fulfill({ json: { available: true } });
    });
    await page.goto("/");
    await page.getByRole("link", { name: `Ver falha de ${source.group} · ${source.label} no histórico de coletas` }).click();
    await expect(page.getByRole("heading", { name: "Histórico", exact: true })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Orquestração de coletas" })).toHaveAttribute("aria-selected", "true");
    const link = page.getByRole("link", { name: `Clique aqui para acessar ${source.name}`, exact: false });
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", source.href);
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(page.getByText(/Você pode consultar os expedientes manualmente/)).toBeVisible();
    await expect(page).toHaveURL(/\/historico\?tab=orquestracao$/);
    await page.getByRole("button", { name: "Fechar aviso de atenção" }).click();
    await page.reload();
    await expect(page.getByRole("tab", { name: "Orquestração de coletas" })).toHaveAttribute("aria-selected", "true");
    await expect(link).toHaveCount(0);
  });
}
