import { expect, test } from "@playwright/test";

const user = {
  id: 1,
  username: "operador",
  display_name: "Victor",
  theme: "light",
  collection_time: "06:00",
};

const item = {
  id: 1,
  identificador_pje: "29908000",
  tipo_pendencia: "ciencia",
  tipo_pendencia_label: "Pendente de ciência",
  acao_pje: "tomar_ciencia",
  acao_pje_label: "Tomar ciência",
  caixa: "Pendentes",
  destinatario: "Município",
  tipo_documento: "Intimação",
  meio_comunicacao: "Diário eletrônico",
  data_expedicao: "2026-08-25T08:00:00Z",
  prazo_texto: "3 dias",
  status_prazo_fatal: "calculado",
  status_prazo_fatal_label: "Calculado",
  prazo_fatal: "2026-08-28T08:00:00Z",
  ciencia_texto: "",
  capturado_em: "2026-08-25T08:00:00Z",
  atualizado_em: "2026-08-25T08:00:00Z",
  ativo: true,
  arquivado_em: null,
  unread: true,
  source: { code: "pje-tjrn", system: "PJe", tribunal: "TJRN" },
  processo: {
    id: 1,
    numero: "0800000-00.2026.8.20.0001",
    tribunal: "TJRN",
    classe: "Procedimento",
    assunto: "Obrigação de fazer",
    partes_texto: "PARTE A X MUNICÍPIO",
    unidade_judiciaria: "1ª Vara",
  },
  latest_event: {
    id: 1,
    kind: "new",
    kind_label: "Novo",
    changes: {},
    created_at: "2026-08-25T08:00:00Z",
    read_at: null,
  },
};

test("login, dashboard and reading a new expediente", async ({ page }) => {
  let authenticated = false;
  let collectionRequests = 0;
  let activeDashboardRequests = 0;

  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("auth/csrf/")) return route.fulfill({ json: { detail: "ok" } });
    if (path.endsWith("auth/me/")) {
      return authenticated
        ? route.fulfill({ json: user })
        : route.fulfill({ status: 403, json: { detail: "auth" } });
    }
    if (path.endsWith("auth/login/")) {
      authenticated = true;
      return route.fulfill({ json: user });
    }
    if (path.endsWith("dashboard/") && route.request().method() === "GET") {
      const cycleStatus = collectionRequests > 0 && ++activeDashboardRequests === 1 ? "pending" : "success";
      const latestRun = collectionRequests === 0 ? null : {
        id: 1, status: cycleStatus, trigger: "manual",
        started_at: "2026-08-25T08:00:00Z",
        finished_at: cycleStatus === "pending" ? null : "2026-08-25T08:01:00Z",
        found: 1, created: 1, updated: 0, resolved: 0, error: "", message: "", source: "PJe / TJRN",
      };
      const pipelineSources = [
        ["pje-tjrn", "TJRN", "1º Grau"], ["pje2g-tjrn", "TJRN", "2º Grau"],
        ["tre-rn-1g", "Justiça Eleitoral", "TRE-RN · 1º Grau"], ["tre-rn-2g", "Justiça Eleitoral", "TRE-RN · 2º Grau"],
        ["tse-3g", "Justiça Eleitoral", "TSE · 3º Grau"], ["trt21", "TRT21", "1º Grau"],
        ["trt21-2g", "TRT21", "2º Grau"], ["trf5-2g-tru", "TRF5", "2º Grau / TRU"],
        ["varas-justica-comum", "TRF5", "Varas federais"], ["jef-5-regiao", "TRF5", "JEF · 5ª Região"],
        ["trs-5-regiao", "TRF5", "Turmas recursais"], ["tru-5-regiao", "TRF5", "TRU · perfil alternativo"],
      ];
      const collectionPipeline = {
        cycle_id: collectionRequests ? "cycle-1" : null,
        status: collectionRequests === 0 ? "idle" : cycleStatus === "pending" ? "running" : "success",
        active: cycleStatus === "pending", completed: cycleStatus === "success" && collectionRequests ? 12 : 0, total: 12,
        started_at: collectionRequests ? "2026-08-25T08:00:00Z" : null,
        finished_at: cycleStatus === "success" && collectionRequests ? "2026-08-25T08:01:00Z" : null,
        current_step: cycleStatus === "pending" ? "pje-tjrn" : null,
        steps: pipelineSources.map(([code, group, label], index) => ({
          code, group, label, run_id: index === 0 ? 1 : null, error: "", message: "",
          status: collectionRequests === 0 ? "pending" : cycleStatus === "pending" ? (index === 0 ? "pending" : "pending") : "success",
        })),
      };
      return route.fulfill({
        json: {
          display_name: "Victor",
          today: { new: 1, updated: 0, resolved: 0, discardable: 1, unread: 1, urgent: 0, calculating: 0 },
          since_last_visit: { since: null, new: 1, updated: 0, resolved: 0 },
          latest_run: latestRun,
          collection_pipeline: collectionPipeline,
          recent: [item],
          notices: { unread: 0, recent: [] },
        },
      });
    }
    if (path.endsWith("expedientes/")) {
      return route.fulfill({ json: { count: 1, next: null, previous: null, results: [item] } });
    }
    if (path.endsWith("automation/history/")) {
      return route.fulfill({ json: { period_start: "2026-08-27", period_end: "2026-09-25", days: [{ date: "2026-09-25", runs: [{ id: 1, cycle_id: "cycle-1", status: "success", status_label: "Sucesso", trigger: "manual", trigger_label: "Manual", created_at: "2026-09-25T08:00:00Z", started_at: "2026-09-25T08:00:00Z", finished_at: "2026-09-25T08:01:00Z", duration_seconds: 60, found: 1, created: 1, updated: 0, resolved: 0, error: "", message: "", source: { code: "pje-tjrn", system: "PJe", tribunal: "TJRN" } }] }] } });
    }
    if (path.endsWith("history/")) {
      return route.fulfill({ json: { period_start: "2026-08-27", period_end: "2026-09-25", count: 1, page: 1, page_size: 50, days: [{ date: "2026-09-25", new_count: 1, items: [{ event: item.latest_event, expediente: item }] }] } });
    }
    if (path.endsWith("dashboard/")) {
      return route.fulfill({ json: { visited_at: new Date().toISOString() } });
    }
    if (path.endsWith("automation/runs/")) {
      collectionRequests += 1;
      return route.fulfill({ json: { id: 1, status: "pending" } });
    }
    if (path.endsWith("/read/")) {
      return route.fulfill({ json: { events_marked: 1 } });
    }
    return route.fulfill({ json: {} });
  });

  await page.goto("/login");
  await page.getByLabel("Usuário").fill("operador");
  await page.getByLabel("Senha").fill("senha-segura");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Bo(m dia|a tarde|a noite), Victor\./ })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: "Mudar para tema escuro" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Mudar para tema claro" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page.getByTestId("clock-face")).toBeVisible();
  await expect(page.getByRole("link", { name: "Expedientes", exact: true }).first()).toBeVisible();
  await expect(page.getByTestId("pipeline-scroll-region")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await expect(page.getByTestId("pipeline-scroll-region")).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByRole("button", { name: "Executar coleta" }).click();
  await expect.poll(() => collectionRequests).toBe(1);
  await expect(page.getByText("12 de 12 fontes concluídas", { exact: false }).first()).toBeVisible();
  await page.getByText("0800000-00.2026.8.20.0001").click();
  await expect(page.getByRole("dialog")).toContainText("Obrigação de fazer");
  await page.getByLabel("Fechar").click();
  await page.getByRole("link", { name: "Expedientes", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Expedientes" })).toBeVisible();
  await page.getByRole("link", { name: "Histórico", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Histórico" })).toBeVisible();
  await expect(page.getByText("PJe · TJRN").first()).toBeVisible();
  await page.getByRole("tab", { name: "Orquestração de coletas" }).click();
  await expect(page.getByText("Manual").first()).toBeVisible();
});
