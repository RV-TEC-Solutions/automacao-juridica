import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const { api } = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../lib/api", () => ({
  api,
  formatDateTime: (value: string | null) => value ? "28 set. 2026, 10:00" : "—",
}));

import { CollectionHistoryPanel } from "./collection-history";

describe("CollectionHistoryPanel", () => {
  it("renders grouped runs and expands an error log", async () => {
    api.mockResolvedValueOnce({
      period_start: "2026-08-30", period_end: "2026-09-28",
      days: [{ date: "2026-09-28", runs: [{
        id: 12, cycle_id: "cycle", status: "failed", status_label: "Erro",
        trigger: "rerun", trigger_label: "Reexecução de fonte",
        created_at: "2026-09-28T10:00:00Z", started_at: "2026-09-28T10:00:00Z", finished_at: "2026-09-28T10:01:00Z", duration_seconds: 60,
        found: 3, created: 1, updated: 1, resolved: 0, error: "Falha de autenticação", message: "",
        source: { code: "pje-tjrn", system: "PJe 1º Grau", tribunal: "TJRN" },
      }] }],
    });
    render(<CollectionHistoryPanel />);

    expect(await screen.findByText("PJe 1º Grau")).toBeVisible();
    const details = screen.getByRole("button", { name: "Ver erro" });
    expect(details).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(details);
    expect(details).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Falha de autenticação");
  });
});
