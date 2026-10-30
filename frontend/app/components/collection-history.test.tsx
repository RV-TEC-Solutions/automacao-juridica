import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const { api } = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../lib/api", () => ({
  api,
  formatDateTime: (value: string | null) => value ? value.slice(11, 16) : "—",
}));

import { CollectionHistoryPanel } from "./collection-history";
import { NotificationsProvider } from "./notifications";

describe("CollectionHistoryPanel", () => {
  it("renders grouped runs and expands an error log", async () => {
    api.mockResolvedValueOnce({
      period_start: "2026-08-30", period_end: "2026-09-28",
      days: [{ date: "2026-09-28", runs: [{
        id: 12, cycle_id: "cycle", status: "failed", status_label: "Erro", collector: "cristiano", collector_label: "DR. CRISTIANO",
        trigger: "rerun", trigger_label: "Reexecução de fonte",
        created_at: "2026-09-28T10:00:00Z", started_at: "2026-09-28T10:00:00Z", finished_at: "2026-09-28T10:01:00Z", duration_seconds: 60,
        found: 3, created: 1, updated: 1, resolved: 0, error: "Falha de autenticação", message: "",
        source: { code: "pje-tjrn", system: "PJe 1º Grau", tribunal: "TJRN" },
      }] }],
    });
    render(<NotificationsProvider><CollectionHistoryPanel /></NotificationsProvider>);

    expect(await screen.findByText("PJe 1º Grau")).toBeVisible();
    expect(screen.getByText("DR. CRISTIANO")).toBeVisible();
    const details = screen.getByRole("button", { name: "Ver erro" });
    expect(details).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(details);
    expect(details).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Falha de autenticação");
  });

  it("shows a later successful attempt after the history refreshes", async () => {
    const failed = {
      id: 20, cycle_id: "cycle", status: "failed", status_label: "Erro", collector: "murilo", collector_label: "MURILO",
      trigger: "scheduled", trigger_label: "Agendada", created_at: "2026-09-28T06:00:00Z", started_at: "2026-09-28T06:00:00Z",
      finished_at: "2026-09-28T06:01:00Z", duration_seconds: 60, found: 0, created: 0, updated: 0, resolved: 0,
      error: "Falha inicial", message: "", source: { code: "pje-tjrn", system: "PJe 1º Grau", tribunal: "TJRN" },
    };
    const success = { ...failed, id: 21, status: "success", status_label: "Sucesso", trigger: "rerun", trigger_label: "Reexecução de fonte", created_at: "2026-09-28T10:00:00Z", started_at: "2026-09-28T10:00:00Z", error: "" };
    const history = (runs: typeof failed[]) => ({ period_start: "2026-08-30", period_end: "2026-09-28", days: [{ date: "2026-09-28", runs }] });
    api.mockResolvedValueOnce(history([failed])).mockResolvedValueOnce(history([success, failed]));
    render(<NotificationsProvider><CollectionHistoryPanel /></NotificationsProvider>);

    expect(await screen.findByText("(1 execução)")).toBeVisible();
    fireEvent(window, new Event("collections-updated"));
    expect(await screen.findByText("(2 execuções)")).toBeVisible();
    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]).getByText("Sucesso")).toBeVisible();
    expect(within(rows[0]).getByText("10:00")).toBeVisible();
    expect(within(rows[1]).getByText("Erro")).toBeVisible();
    expect(within(rows[1]).getByText("06:00")).toBeVisible();
  });
});
