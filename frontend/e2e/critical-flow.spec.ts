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
      return route.fulfill({
        json: {
          display_name: "Victor",
          today: { new: 1, updated: 0, unread: 1, urgent: 0, calculating: 0 },
          since_last_visit: { since: null, new: 1, updated: 0, resolved: 0 },
          latest_run: null,
          recent: [item],
        },
      });
    }
    if (path.endsWith("dashboard/")) {
      return route.fulfill({ json: { visited_at: new Date().toISOString() } });
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
  await expect(page.getByTestId("clock-face")).toBeVisible();
  await page.getByText("0800000-00.2026.8.20.0001").click();
  await expect(page.getByRole("dialog")).toContainText("Obrigação de fazer");
});
