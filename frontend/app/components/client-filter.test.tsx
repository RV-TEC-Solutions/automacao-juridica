import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { api } = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../lib/api", () => ({ api }));
import { ClientFilter } from "./client-filter";

const clients = [{ id: 1, nome: "Caixa Econômica Federal" }, { id: 2, nome: "Outro cliente" }];
afterEach(cleanup);
beforeEach(() => { api.mockReset().mockResolvedValue(clients); });

describe("ClientFilter", () => {
  it("keeps selections on search and refresh and submits repeated parameters", async () => {
    const dirty = vi.fn();
    const { container } = render(<form><ClientFilter initialSelection={["1"]} onDirty={dirty} /></form>);
    fireEvent.click(screen.getByRole("button", { name: /Clientes/ }));
    expect(await screen.findByRole("checkbox", { name: "Caixa Econômica Federal" })).toBeChecked();
    fireEvent.input(screen.getByRole("textbox"), { target: { value: "outro" } });
    expect(dirty).not.toHaveBeenCalled();
    expect(screen.queryByRole("checkbox", { name: "Caixa Econômica Federal" })).toBeNull();
    fireEvent.click(screen.getByRole("checkbox", { name: "Outro cliente" }));
    expect(new FormData(container.querySelector("form")!).getAll("client")).toEqual(["1", "2"]);
    api.mockResolvedValue([...clients, { id: 3, nome: "Novo cliente" }]);
    window.dispatchEvent(new Event("collections-updated"));
    await waitFor(() => expect(api).toHaveBeenCalledTimes(2));
    fireEvent.input(screen.getByRole("textbox"), { target: { value: "" } });
    expect(await screen.findByRole("checkbox", { name: "Novo cliente" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Outro cliente" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Caixa Econômica Federal" })).toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "Limpar clientes" }));
    expect(new FormData(container.querySelector("form")!).getAll("client")).toEqual([]);
  });

  it("matches without accents and reports no results", async () => {
    render(<ClientFilter initialSelection={[]} onDirty={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Clientes Todos os clientes" }));
    await screen.findByRole("checkbox", { name: "Outro cliente" });
    fireEvent.input(screen.getByRole("textbox"), { target: { value: "ECONOMICA" } });
    expect(screen.getByRole("checkbox", { name: "Caixa Econômica Federal" })).toBeVisible();
    expect(screen.queryByRole("checkbox", { name: "Outro cliente" })).toBeNull();
    fireEvent.input(screen.getByRole("textbox"), { target: { value: "inexistente" } });
    expect(screen.getByText("Nenhum resultado para essa busca.")).toBeVisible();
  });

  it("shows loading, retries errors, and handles an empty catalog", async () => {
    api.mockRejectedValueOnce(new Error("failed")).mockResolvedValueOnce([]);
    render(<ClientFilter initialSelection={[]} onDirty={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Clientes Todos os clientes" }));
    expect(screen.getByText("Carregando clientes…")).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível atualizar os clientes.");
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Nenhum cliente coletado até o momento.")).toBeVisible();
  });
});
