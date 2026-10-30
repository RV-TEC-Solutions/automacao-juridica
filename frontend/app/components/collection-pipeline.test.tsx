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
      code: `step-${index}`, group: groups[index], label: labels[index],
      status: !active && (status === "running" || status === "pending") ? "success" : status,
      run_id: index + 1, error: status === "failed" ? "Falha de autenticação no tribunal" : "", message: "",
    })),
  };
}

const handlers = () => ({
  onRefresh: vi.fn(), onRun: vi.fn(), onCancel: vi.fn(), onDiscard: vi.fn(), onRerun: vi.fn(),
});

describe("CollectionPipeline", () => {
  it.each(["murilo", "cristiano", "all"])("requires an explicit choice and starts only the selected scope: %s", (target) => {
    const value = pipeline(false);
    value.collectors = ["murilo", "cristiano"].map((code) => ({
      code, label: `DR. ${code.toUpperCase()}`, enabled: true,
      pin_configured: true, totp_configured: true, state: "success", last_success_at: null, error: "",
    }));
    const callbacks = handlers();
    render(<CollectionPipeline pipeline={value} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={false} {...callbacks} />);
    const start = screen.getByRole("button", { name: "Executar coleta" });
    expect(start).toBeDisabled();
    fireEvent.click(start);
    expect(callbacks.onRun).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole("combobox", { name: "Coletar para" }), { target: { value: target } });
    expect(start).toBeEnabled();
    fireEvent.click(start);
    expect(callbacks.onRun).toHaveBeenCalledExactlyOnceWith(target === "all" ? undefined : target);
  });

  it("prevents changing the collection target during an active cycle", () => {
    render(<CollectionPipeline pipeline={pipeline()} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={false} {...handlers()} />);
    expect(screen.getByRole("combobox", { name: "Coletar para" })).toBeDisabled();
  });

  it("reruns the selected owner and keeps error descriptions distinct", () => {
    const value = pipeline(false);
    value.steps = ["murilo", "cristiano"].map((collector) => ({
      code: "pje-tjrn", collector, group: `${collector} · TJRN`,
      label: `${collector} · 1º Grau`, status: "failed", run_id: 1,
      error: `Falha de ${collector}`, message: "",
    }));
    const callbacks = handlers();
    render(<CollectionPipeline pipeline={value} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={false} {...callbacks} />);

    const first = screen.getByRole("button", { name: "Reexecutar somente murilo · 1º Grau" });
    const second = screen.getByRole("button", { name: "Reexecutar somente cristiano · 1º Grau" });
    expect(first).toHaveAccessibleDescription("Falha de murilo");
    expect(second).toHaveAccessibleDescription("Falha de cristiano");
    fireEvent.click(second);
    expect(callbacks.onRerun).toHaveBeenCalledWith("pje-tjrn", "cristiano");
  });

  it("announces the running owner when source codes repeat", () => {
    const value = pipeline();
    value.current_step = "pje-tjrn";
    value.current_collector = "cristiano";
    value.steps = ["murilo", "cristiano"].map((collector) => ({
      code: "pje-tjrn", collector, group: `${collector} · TJRN`,
      label: `${collector} · 1º Grau`, status: collector === "murilo" ? "success" : "running",
      run_id: 1, error: "", message: "",
    }));
    render(<CollectionPipeline pipeline={value} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={false} {...handlers()} />);

    expect(screen.getByRole("status")).toHaveTextContent("cristiano · 1º Grau: Em execução.");
  });

  it.each(["pending", "running"] as const)("blocks all reruns when another source is %s outside the PJe cycle", (status) => {
    const value = pipeline(false);
    value.steps.push({ code: "djen", group: "DJEN", label: "Publicações nacionais", status, run_id: 99, error: "", message: "" });
    const callbacks = handlers();
    render(<CollectionPipeline pipeline={value} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={false} {...callbacks} />);
    screen.getAllByRole("button", { name: /Reexecutar somente/ }).forEach((button) => {
      expect(button).toBeDisabled();
      fireEvent.click(button);
    });
    expect(callbacks.onRerun).not.toHaveBeenCalled();
  });

  it("blocks all sources while the start request is in flight", () => {
    render(<CollectionPipeline pipeline={pipeline(false)} refreshing={false} starting={true} cancelling={false} discarding={false} canDiscard={false} {...handlers()} />);
    screen.getAllByRole("button", { name: /Reexecutar somente/ }).forEach((button) => expect(button).toBeDisabled());
  });
  it("renders groups and steps in API order with labelled states", () => {
    render(<CollectionPipeline pipeline={pipeline()} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={false} {...handlers()} />);
    const region = screen.getByTestId("pipeline-scroll-region");
    expect(within(region).getAllByRole("heading", { level: 4 }).map((item) => item.textContent)).toEqual(["TJRN", "Justiça Eleitoral", "TRT21", "TRF5"]);
    expect(within(region).getAllByRole("listitem").map((item) => item.textContent)).toEqual(expect.arrayContaining([
      expect.stringContaining("Concluída"), expect.stringContaining("Em execução"), expect.stringContaining("Aguardando"),
      expect.stringContaining("Falhou"), expect.stringContaining("Interrompida"), expect.stringContaining("Desativada"), expect.stringContaining("Ignorada"),
    ]));
    expect(screen.getByText("Falha de autenticação no tribunal")).toBeVisible();
  });

  it("disables every rerun while the cycle is active and preserves cancel", () => {
    render(<CollectionPipeline pipeline={pipeline()} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={false} {...handlers()} />);
    screen.getAllByRole("button", { name: /Reexecutar somente/ }).forEach((button) => expect(button).toBeDisabled());
    expect(screen.getByRole("button", { name: "Descartar coleta do dia" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Interromper coleta" })).toBeEnabled();
  });

  it("enables valid actions after completion and calls rerun with the source", () => {
    const callbacks = handlers();
    render(<CollectionPipeline pipeline={pipeline(false)} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={true} {...callbacks} />);
    const reruns = screen.getAllByRole("button", { name: /Reexecutar somente/ });
    expect(reruns[0]).toBeEnabled();
    expect(reruns[5]).toBeDisabled();
    fireEvent.click(reruns[0]);
    expect(callbacks.onRerun).toHaveBeenCalledWith("step-0");
    expect(screen.getByRole("link", { name: "Ver relatório de coletas" })).toHaveAttribute("href", "/historico?tab=orquestracao");
    fireEvent.click(screen.getByRole("button", { name: "Descartar coleta do dia" }));
    expect(callbacks.onDiscard).toHaveBeenCalled();
    fireEvent.change(screen.getByRole("combobox", { name: "Coletar para" }), { target: { value: "all" } });
    expect(screen.getByRole("button", { name: "Executar coleta" })).toBeEnabled();
  });

  it("allows a DJEN rerun while the token is unavailable", () => {
    const callbacks = handlers();
    const value = pipeline(false);
    value.steps.push({ code: "djen", group: "DJEN", label: "Publicações nacionais", status: "pending", run_id: null, error: "", message: "" });
    render(<CollectionPipeline pipeline={value} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={false} tokenAvailable={false} {...callbacks} />);

    expect(screen.getByRole("button", { name: "Executar coleta" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Reexecutar somente Publicações nacionais" }));
    expect(callbacks.onRerun).toHaveBeenCalledWith("djen");
  });

  it("shows both DJEN cards and reruns the shared collection", () => {
    const callbacks = handlers();
    const value = pipeline(false);
    value.steps = ["murilo", "cristiano"].map((collector) => ({
      code: "djen", collector, group: "DJEN", label: collector === "murilo" ? "Dr. Murilo Mariz" : "Dr. Cristiano Barros",
      status: "success", run_id: 99, error: "", message: "",
    }));
    render(<CollectionPipeline pipeline={value} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={false} {...callbacks} />);
    expect(screen.getAllByText("Coleta conjunta")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Reexecutar coleta conjunta DJEN (Dr. Cristiano Barros)" }));
    expect(callbacks.onRerun).toHaveBeenCalledWith("djen");
  });

  it("links only failed steps to orchestration without making rerun a nested control", () => {
    const callbacks = handlers();
    render(<CollectionPipeline pipeline={pipeline(false)} refreshing={false} starting={false} cancelling={false} discarding={false} canDiscard={false} {...callbacks} />);
    const link = screen.getByRole("link", { name: "Ver falha de Justiça Eleitoral · TRE-RN · 2º Grau no histórico de coletas" });
    expect(link).toHaveAttribute("href", "/historico?tab=orquestracao&failed_source=step-3");
    expect(screen.getAllByRole("link", { name: /Ver falha de/ })).toHaveLength(1);
    const rerun = screen.getByRole("button", { name: "Reexecutar somente TRE-RN · 2º Grau" });
    expect(link.contains(rerun)).toBe(false);
    fireEvent.click(rerun);
    expect(callbacks.onRerun).toHaveBeenCalledWith("step-3");
  });
});
