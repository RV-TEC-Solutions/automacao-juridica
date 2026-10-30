import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type { ReactNode } from "react";

const { replace, paths } = vi.hoisted(() => ({ replace: vi.fn(), paths: [] as string[] }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }), useSearchParams: () => new URLSearchParams("tab=publicacoes&attorney=murilo&page=2") }));
vi.mock("../providers", () => ({ useAuth: () => ({ user: null }) }));
vi.mock("../components/notifications", () => ({ useNotifications: () => ({ notify: vi.fn() }) }));
vi.mock("../hooks/use-live-list", () => ({ useLiveList: (path: string) => { paths.push(path); return { data: null, loading: true, error: "", reload: vi.fn(), setData: vi.fn() }; } }));
vi.mock("../components/app-shell", () => ({ AppShell: ({ children }: { children: ReactNode }) => <div>{children}</div> }));
vi.mock("../components/pdf-export-button", () => ({ PdfExportButton: ({ path }: { path: string }) => <span data-testid="pdf" data-path={path} /> }));
import { HistoricoClient } from "./view";

it("preserves the attorney in history requests and exports and resets pagination when changed", () => {
  render(<HistoricoClient />);
  expect(paths.some((path) => path.startsWith("djen/history/") && path.includes("attorney=murilo"))).toBe(true);
  expect(screen.getByTestId("pdf")).toHaveAttribute("data-path", expect.stringContaining("attorney=murilo"));
  fireEvent.change(screen.getByLabelText("Por advogado"), { target: { value: "cristiano" } });
  const url = new URL(replace.mock.lastCall![0], "http://localhost");
  expect(url.searchParams.get("attorney")).toBe("cristiano");
  expect(url.searchParams.has("page")).toBe(false);
});
