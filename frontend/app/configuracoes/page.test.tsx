import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { api, notify } = vi.hoisted(() => ({ api: vi.fn(), notify: vi.fn() }));
vi.mock("../lib/api", () => ({ api }));
vi.mock("../components/app-shell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("../components/notifications", () => ({ useNotifications: () => ({ notify }) }));
vi.mock("../providers", () => ({ useAuth: () => ({ refresh: vi.fn() }) }));

import SettingsPage from "./page";

describe("switch geral de fontes", () => {
  beforeEach(() => {
    api.mockReset();
    notify.mockReset();
  });

  it("habilita as fontes desabilitadas e depois desabilita todas", async () => {
    api.mockImplementation((path: string, options?: RequestInit) => {
      if (path === "settings/") return Promise.resolve({ display_name: "Teste", theme: "light", collection_time: "08:00", credential_status: {} });
      if (path === "sources/") return Promise.resolve([
        { code: "a", system: "PJe", tribunal: "A", enabled: true },
        { code: "b", system: "PJe", tribunal: "B", enabled: false },
      ]);
      const enabled = JSON.parse(String(options?.body)).enabled as boolean;
      return Promise.resolve({ code: path.split("/")[1], system: "PJe", tribunal: path.includes("/a/") ? "A" : "B", enabled });
    });

    render(<SettingsPage />);
    const all = await screen.findByRole("switch", { name: "Habilitar todas as fontes" });
    expect(all).toHaveAttribute("aria-checked", "false");

    fireEvent.click(all);
    await waitFor(() => expect(all).toHaveAttribute("aria-checked", "true"));
    expect(api).toHaveBeenCalledWith("sources/b/", { method: "PATCH", body: JSON.stringify({ enabled: true }) });
    expect(api).not.toHaveBeenCalledWith("sources/a/", expect.anything());

    fireEvent.click(all);
    await waitFor(() => expect(all).toHaveAttribute("aria-checked", "false"));
    expect(api).toHaveBeenCalledWith("sources/a/", { method: "PATCH", body: JSON.stringify({ enabled: false }) });
    expect(api).toHaveBeenCalledWith("sources/b/", { method: "PATCH", body: JSON.stringify({ enabled: false }) });
  });
});
