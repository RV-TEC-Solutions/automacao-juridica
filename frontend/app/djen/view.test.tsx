import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

const { replace, reload, state } = vi.hoisted(() => ({ replace: vi.fn(), reload: vi.fn(), state: { query: "", loading: false, error: "", hasData: true } }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }), useSearchParams: () => new URLSearchParams(state.query) }));
vi.mock("../hooks/use-live-list", () => ({ useLiveList: (path: string) => ({
  data: path === "djen/filters/" ? { clientes: [{ id: 1, nome: "CAIXA" }, { id: 2, nome: "Outro" }], tribunais: ["TJRN", "TRF5"], tipos_comunicacao: ["Intimação"] } : state.hasData ? { count: 40, results: [] } : null,
  reload, setData: vi.fn(), loading: state.loading, error: state.error,
}) }));
vi.mock("../components/app-shell", () => ({ AppShell: ({ children }: { children: ReactNode }) => <div>{children}</div> }));
vi.mock("../components/djen-drawer", () => ({ DjenDrawer: () => null }));
vi.mock("../components/djen-list", () => ({ DjenList: () => null }));
vi.mock("../components/pdf-export-button", () => ({ PdfExportButton: ({ path, disabled }: { path: string; disabled: boolean }) => <button data-path={path} disabled={disabled}>PDF</button> }));
import { DjenClient } from "./view";

afterEach(cleanup);
beforeEach(() => { replace.mockReset(); reload.mockReset(); state.loading = false; state.error = ""; state.hasData = true; state.query = "uf=SP&uf=DF&client=1&client=2&tribunal=TJRN&tribunal=TRF5&read=unread&page=2&collected_from=&collected_to="; });

it("preserves multiple filters in pagination and PDF and resets page on submission", () => {
  const { container } = render(<DjenClient />);
  fireEvent.click(screen.getByText("Filtros avançados", { exact: false }));
  const path = screen.getByRole("button", { name: "PDF" }).getAttribute("data-path")!;
  const exported = new URL(path, "http://localhost");
  expect(exported.searchParams.getAll("client")).toEqual(["1", "2"]);
  expect(exported.searchParams.getAll("tribunal")).toEqual(["TJRN", "TRF5"]);
  expect(exported.searchParams.getAll("uf")).toEqual(["SP", "DF"]);
  expect(exported.searchParams.has("page")).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: /Anterior/ }));
  expect(new URL(replace.mock.lastCall![0], "http://localhost").searchParams.getAll("client")).toEqual(["1", "2"]);
  fireEvent.submit(container.querySelector("form")!);
  const submitted = new URL(replace.mock.lastCall![0], "http://localhost");
  expect(submitted.searchParams.getAll("client")).toEqual(["1", "2"]);
  expect(submitted.searchParams.getAll("uf")).toEqual(["SP", "DF"]);
  expect(submitted.searchParams.has("page")).toBe(false);
});

it("marks changes dirty, validates dates and clears every filter", () => {
  render(<DjenClient />);
  fireEvent.click(screen.getByText("Filtros avançados", { exact: false }));
  fireEvent.input(screen.getByRole("textbox", { name: "Pesquisar publicações DJEN" }), { target: { value: "nova busca" } });
  expect(screen.getByRole("button", { name: "PDF" })).toBeDisabled();
  const first = screen.getByLabelText("Coleta a partir de");
  const last = screen.getByLabelText("Coleta até");
  fireEvent.input(first, { target: { value: "2026-10-03" } });
  fireEvent.input(last, { target: { value: "2026-10-01" } });
  expect(last).toBeInvalid();
  fireEvent.input(last, { target: { value: "2026-10-04" } });
  expect(last).toBeValid();
  fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }));
  expect(replace).toHaveBeenLastCalledWith("/djen?collected_from=&collected_to=");
});

it("shows initial loading and an indeterminate progress bar until publications arrive", () => {
  state.loading = true;
  state.hasData = false;
  const { rerender } = render(<DjenClient />);
  expect(screen.getByText("Carregando publicações DJEN…")).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).not.toHaveAttribute("aria-valuenow");
  expect(screen.getByRole("region", { name: "Publicações DJEN" })).toHaveAttribute("aria-busy", "true");
  expect(screen.getByRole("button", { name: "Atualizando…" })).toBeDisabled();
  expect(screen.queryByText("Nenhuma publicação encontrada")).not.toBeInTheDocument();
  state.loading = false;
  state.hasData = true;
  rerender(<DjenClient />);
  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Publicações DJEN" })).toHaveAttribute("aria-busy", "false");
  fireEvent.click(screen.getByRole("button", { name: "Atualizar" }));
  expect(reload).toHaveBeenCalledOnce();
});

it("shows refresh feedback with existing results and allows retry after failure", () => {
  state.loading = true;
  const { rerender } = render(<DjenClient />);
  expect(screen.getByText("Atualizando publicações DJEN…")).toBeInTheDocument();
  expect(screen.getByText("40 publicações")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "PDF" })).toBeDisabled();
  state.loading = false;
  state.error = "Falha ao consultar publicações.";
  rerender(<DjenClient />);
  expect(screen.getAllByRole("alert").some((alert) => alert.textContent?.includes(state.error))).toBe(true);
  fireEvent.click(screen.getAllByRole("button", { name: "Tentar novamente" }).at(-1)!);
  expect(reload).toHaveBeenCalledOnce();
});
