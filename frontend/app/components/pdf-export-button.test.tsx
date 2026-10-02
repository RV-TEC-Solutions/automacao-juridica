import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { downloadPdf } = vi.hoisted(() => ({ downloadPdf: vi.fn() }));
vi.mock("../lib/export", () => ({ downloadPdf }));

import { PdfExportButton } from "./pdf-export-button";
import { NotificationsProvider } from "./notifications";

describe("PdfExportButton", () => {
  beforeEach(() => { downloadPdf.mockReset().mockResolvedValue(undefined); });

  it("explains the selected overview filter before downloading", async () => {
    render(<NotificationsProvider><PdfExportButton path="expedientes/export.pdf/?scope=overview&metric=urgent"
      label="Exportar expedientes em PDF" summary="Urgentes · inclui coletas anteriores" count={12} /></NotificationsProvider>);
    const trigger = screen.getByRole("button", { name: "Exportar expedientes em PDF" });
    expect(trigger).toHaveTextContent("");
    expect(trigger.querySelector("svg")).not.toBeNull();
    fireEvent.click(trigger);
    expect(screen.getByText("Urgentes · inclui coletas anteriores")).toBeVisible();
    expect(screen.getByText(/12 registros serão incluídos/)).toBeVisible();
    expect(downloadPdf).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Baixar PDF" }));
    await waitFor(() => expect(downloadPdf).toHaveBeenCalledWith("expedientes/export.pdf/?scope=overview&metric=urgent"));
  });

  it("does not download an empty result", () => {
    render(<NotificationsProvider><PdfExportButton path="djen/communications/export.pdf/" count={0} /></NotificationsProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Exportar PDF" }));
    expect(downloadPdf).not.toHaveBeenCalled();
    expect(screen.getByText("Não há registros para exportar com os filtros atuais.")).toBeVisible();
  });

  it("offers the analytical expedition report without changing publication exports", async () => {
    const { container } = render(<NotificationsProvider><PdfExportButton path="expedientes/export.pdf/?scope=list" label="Exportar expedientes em PDF" analytical /></NotificationsProvider>);
    fireEvent.click(within(container).getByRole("button", { name: "Exportar expedientes em PDF" }));
    fireEvent.click(screen.getByRole("button", { name: "Analítico" }));
    await waitFor(() => expect(downloadPdf).toHaveBeenCalledWith("expedientes/export.pdf/?scope=list&mode=analitico"));
  });
});
