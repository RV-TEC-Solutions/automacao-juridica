import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ProcessList } from "./process-list";

const processNumber = "0800000-00.2026.8.20.0001";

function renderList() {
  const onSelect = vi.fn();
  render(<ProcessList rows={[{
    id: 1, number: processNumber, badges: null, title: "Intimação", detail: "Parte A",
    dateLabel: "Prazo fatal", date: "13/10/2026", unread: false, onSelect,
  }]} />);
  return { onSelect, button: screen.getByRole("button", { name: "Copiar número do processo" }) };
}

describe("ProcessList copy button", () => {
  const execCommand = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("navigator", Object.create(navigator, { clipboard: { value: undefined, configurable: true } }));
    execCommand.mockReset().mockReturnValue(true);
    Object.defineProperty(document, "execCommand", { value: execCommand, configurable: true });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    Reflect.deleteProperty(document, "execCommand");
  });

  it("confirms success only after the clipboard write succeeds", async () => {
    let finishCopy!: () => void;
    const writeText = vi.fn(() => new Promise<void>((resolve) => { finishCopy = resolve; }));
    Object.defineProperty(navigator, "clipboard", { value: { writeText } });
    const { button, onSelect } = renderList();

    fireEvent.click(button);
    expect(writeText).toHaveBeenCalledWith(processNumber);
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    expect(onSelect).not.toHaveBeenCalled();
    await act(async () => finishCopy());
    expect(screen.getByRole("status")).toHaveTextContent("Número do processo copiado.");
    expect(execCommand).not.toHaveBeenCalled();
  });

  it("copies over HTTP when the modern clipboard API is unavailable and restores focus", async () => {
    const { button, onSelect } = renderList();
    button.focus();
    execCommand.mockImplementation(() => {
      const textarea = document.activeElement as HTMLTextAreaElement;
      expect(textarea.tagName).toBe("TEXTAREA");
      expect(textarea.value).toBe(processNumber);
      expect(textarea.selectionStart).toBe(0);
      expect(textarea.selectionEnd).toBe(processNumber.length);
      return true;
    });

    fireEvent.click(button);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Número do processo copiado."));
    expect(execCommand).toHaveBeenCalledWith("copy");
    expect(button).toHaveFocus();
    expect(document.querySelector("textarea")).toBeNull();
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("uses the fallback when the browser denies clipboard access", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("Permission denied"));
    Object.defineProperty(navigator, "clipboard", { value: { writeText } });
    fireEvent.click(renderList().button);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Número do processo copiado."));
    expect(execCommand).toHaveBeenCalledWith("copy");
  });

  it.each(["returns false", "throws"])("shows a recovery message when fallback %s", async (failure) => {
    execCommand.mockImplementation(() => {
      if (failure === "throws") throw new Error("Copy unavailable");
      return false;
    });
    const { button } = renderList();
    button.focus();
    fireEvent.click(button);
    expect(await screen.findByRole("alert")).toHaveTextContent("Selecione o número do processo e copie manualmente.");
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    expect(document.querySelector("textarea")).toBeNull();
    expect(button).toHaveFocus();
  });

  it.each(["Enter", " "])("allows the copy button's native %s action without opening the expediente", (key) => {
    const { button, onSelect } = renderList();
    expect(fireEvent.keyDown(button, { key })).toBe(true);
    expect(onSelect).not.toHaveBeenCalled();
    const row = button.closest('[role="button"]')!;
    expect(fireEvent.keyDown(row, { key })).toBe(false);
    expect(onSelect).toHaveBeenCalledOnce();
  });
});
