import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NotificationsProvider, useNotifications } from "./notifications";

afterEach(() => { cleanup(); vi.useRealTimers(); });

function Trigger({ actionable = false }: { actionable?: boolean }) {
  const { notify } = useNotifications();
  return <button onClick={() => notify({
    tone: "warning", message: "Consulte a fonte manualmente.",
    ...(actionable ? { link: { href: "https://example.test/", label: "Clique aqui para acessar o tribunal" } } : {}),
  })}>Notificar</button>;
}

describe("Notifications", () => {
  it("keeps an actionable toast available and opens its descriptive link in a new tab", () => {
    vi.useFakeTimers();
    render(<NotificationsProvider><Trigger actionable /></NotificationsProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Notificar" }));
    act(() => { vi.advanceTimersByTime(60_000); });
    const link = screen.getByRole("link", { name: /Clique aqui para acessar o tribunal/ });
    expect(link).toHaveAttribute("href", "https://example.test/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    fireEvent.click(screen.getByRole("button", { name: "Fechar aviso de atenção" }));
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("continues dismissing ordinary messages automatically", () => {
    vi.useFakeTimers();
    render(<NotificationsProvider><Trigger /></NotificationsProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Notificar" }));
    expect(screen.getByText("Consulte a fonte manualmente.")).toBeVisible();
    act(() => { vi.advanceTimersByTime(5_000); });
    expect(screen.queryByText("Consulte a fonte manualmente.")).not.toBeInTheDocument();
  });
});
