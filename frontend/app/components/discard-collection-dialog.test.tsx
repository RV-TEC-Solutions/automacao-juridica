import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DiscardCollectionDialog } from "./discard-collection-dialog";

describe("DiscardCollectionDialog", () => {
  it("focuses cancel and only confirms after the explicit destructive action", () => {
    const onClose = vi.fn();
    const onConfirm = vi.fn();
    render(<DiscardCollectionDialog open busy={false} onClose={onClose} onConfirm={onConfirm} />);

    expect(screen.getByRole("alertdialog")).toHaveTextContent("Os expedientes novos serão excluídos");
    expect(screen.getByRole("alertdialog")).toHaveTextContent("A pipeline e o histórico de orquestração do dia também serão limpos");
    expect(screen.getByRole("button", { name: "Cancelar" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onClose).toHaveBeenCalledOnce();
    expect(onConfirm).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Descartar coleta" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
