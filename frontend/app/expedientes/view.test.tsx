import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

const { replace, reload, state } = vi.hoisted(() => ({ replace: vi.fn(), reload: vi.fn(), state: { query: "" } }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }), useSearchParams: () => new URLSearchParams(state.query) }));
vi.mock("../hooks/use-live-list", () => ({ useLiveList: (path: string) => ({
  data: path === "expedientes/clientes/" ? [{ id: 1, nome: "CAIXA" }, { id: 2, nome: "Outro" }] : { count: 30, results: [] },
  reload, loading: false, error: "",
}) }));
vi.mock("../components/app-shell", () => ({ AppShell: ({ children }: { children: ReactNode }) => <div>{children}</div> }));
vi.mock("../components/expediente-drawer", () => ({ ExpedienteDrawer: () => null }));
vi.mock("../components/expediente-list", () => ({ ExpedienteList: () => null }));
vi.mock("../components/pdf-export-button", () => ({ PdfExportButton: ({ path, disabled }: { path: string; disabled: boolean }) => <button data-path={path} disabled={disabled}>PDF</button> }));
import { ExpedientesClient } from "./view";

afterEach(cleanup);
beforeEach(() => { replace.mockReset(); reload.mockReset(); state.query = "client=1&client=2&source=pje-tjrn&page=2"; });

it("preserves clients for pagination and PDF and resets the page on submit", () => {
  const { container } = render(<ExpedientesClient />);
  fireEvent.click(screen.getByText("Filtros avançados", { exact: false }));
  expect(screen.getByRole("button", { name: "PDF" })).toHaveAttribute("data-path", "expedientes/export.pdf/?client=1&client=2&source=pje-tjrn");
  fireEvent.click(screen.getByRole("button", { name: /Anterior/ }));
  const paged = new URL(replace.mock.lastCall![0], "http://localhost");
  expect(paged.searchParams.getAll("client")).toEqual(["1", "2"]);
  expect(paged.searchParams.get("page")).toBe("1");
  fireEvent.submit(container.querySelector("form")!);
  const submitted = new URL(replace.mock.lastCall![0], "http://localhost");
  expect(submitted.searchParams.getAll("client")).toEqual(["1", "2"]);
  expect(submitted.searchParams.has("page")).toBe(false);
});

it("applies the attorney filter and includes it in the submitted query", () => {
  const { container } = render(<ExpedientesClient />);
  fireEvent.click(screen.getByText("Filtros avançados", { exact: false }));
  fireEvent.change(screen.getByLabelText("Por advogado"), { target: { value: "cristiano" } });
  expect(screen.getByRole("button", { name: "PDF" })).toBeDisabled();
  fireEvent.submit(container.querySelector("form")!);
  expect(new URL(replace.mock.lastCall![0], "http://localhost").searchParams.get("attorney")).toBe("cristiano");
});

it("clears unapplied selections when the current URL has no filters", () => {
  state.query = "";
  render(<ExpedientesClient />);
  fireEvent.click(screen.getByText("Filtros avançados"));
  fireEvent.click(screen.getByRole("button", { name: "Clientes Todos os clientes" }));
  fireEvent.click(screen.getByRole("checkbox", { name: "CAIXA" }));
  expect(screen.getByRole("button", { name: "PDF" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }));
  fireEvent.click(screen.getByText("Filtros avançados"));
  fireEvent.click(screen.getByRole("button", { name: "Clientes Todos os clientes" }));
  expect(screen.getByRole("checkbox", { name: "CAIXA" })).not.toBeChecked();
  expect(screen.getByRole("button", { name: "PDF" })).toBeEnabled();
});


it("offers all 13 sources and keeps selections while searching", async () => {
  state.query = "";
  const { container } = render(<ExpedientesClient />);
  fireEvent.click(screen.getByText("Filtros avançados"));
  fireEvent.click(screen.getByRole("button", { name: "Fontes Todas as fontes" }));
  expect(await screen.findAllByRole("checkbox")).toHaveLength(13);
  fireEvent.click(screen.getByRole("checkbox", { name: "TJRN · 1º Grau" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Buscar fonte ou tribunal" }), { target: { value: "TRF5" } });
  expect(screen.getAllByRole("checkbox")).toHaveLength(5);
  fireEvent.click(screen.getByRole("button", { name: "Selecionar resultados" }));
  expect(new FormData(container.querySelector("form")!).getAll("source")).toHaveLength(6);
  fireEvent.click(screen.getByRole("button", { name: "Limpar fontes" }));
  expect(new FormData(container.querySelector("form")!).getAll("source")).toEqual([]);
});
