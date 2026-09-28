import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(cleanup);
import type { CollectionPipeline as Pipeline, PipelineStepStatus } from "../lib/types";
import { CollectionPipeline } from "./collection-pipeline";

const statuses: PipelineStepStatus[] = ["success", "running", "pending", "failed", "cancelled", "disabled", "skipped"];
const groups = ["TJRN", "TJRN", "Justiça Eleitoral", "Justiça Eleitoral", "Justiça Eleitoral", "TRT21", "TRF5"];
const labels = ["1º Grau", "2º Grau", "TRE-RN · 1º Grau", "TRE-RN · 2º Grau", "TSE · 3º Grau", "1º Grau trabalhista", "2º Grau / TRU"];

function pipeline(active = true): Pipeline {
  return {
    cycle_id: "cycle-1", status: active ? "running" : "failed", active,
    completed: 1, total: 6, started_at: "2026-09-27T10:00:00Z",
    finished_at: active ? null : "2026-09-27T10:05:00Z", current_step: active ? "step-1" : null,
    steps: statuses.map((status, index) => ({
      code: `step-${index}`, group: groups[index], label: labels[index], status,
      run_id: index + 1, error: status === "failed" ? "Falha de autenticação no tribunal" : "", message: "",
    })),
  };
}

const handlers = () => ({
  onRefresh: vi.fn(), onRun: vi.fn(), onCancel: vi.fn(), onRerun: vi.fn(),
});

describe("CollectionPipeline", () => {
  it("renders groups and steps in API order with labelled states", () => {
    render(<CollectionPipeline pipeline={pipeline()} refreshing={false} starting={false} cancelling={false} {...handlers()} />);
    const region = screen.getByTestId("pipeline-scroll-region");
    expect(within(region).getAllByRole("heading", { level: 4 }).map((item) => item.textContent)).toEqual(["TJRN", "Justiça Eleitoral", "TRT21", "TRF5"]);
    expect(within(region).getAllByRole("listitem").map((item) => item.textContent)).toEqual(expect.arrayContaining([
      expect.stringContaining("Concluída"), expect.stringContaining("Em execução"), expect.stringContaining("Aguardando"),
      expect.stringContaining("Falhou"), expect.stringContaining("Interrompida"), expect.stringContaining("Desativada"), expect.stringContaining("Ignorada"),
    ]));
    expect(screen.getByText("Falha de autenticação no tribunal")).toBeVisible();
  });

  it("disables every rerun while the cycle is active and preserves cancel", () => {
    render(<CollectionPipeline pipeline={pipeline()} refreshing={false} starting={false} cancelling={false} {...handlers()} />);
    screen.getAllByRole("button", { name: /Reexecutar a partir/ }).forEach((button) => expect(button).toBeDisabled());
    expect(screen.getByRole("button", { name: "Interromper coleta" })).toBeEnabled();
  });

  it("enables valid actions after completion and calls rerun with the source", () => {
    const callbacks = handlers();
    render(<CollectionPipeline pipeline={pipeline(false)} refreshing={false} starting={false} cancelling={false} {...callbacks} />);
    const reruns = screen.getAllByRole("button", { name: /Reexecutar a partir/ });
    expect(reruns[0]).toBeEnabled();
    expect(reruns[5]).toBeDisabled();
    fireEvent.click(reruns[0]);
    expect(callbacks.onRerun).toHaveBeenCalledWith("step-0");
    expect(screen.getByRole("button", { name: "Executar coleta" })).toBeEnabled();
  });
});
