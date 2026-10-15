import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useLiveList } from "./use-live-list";

const { api } = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../lib/api", () => ({ api }));

afterEach(() => { vi.useRealTimers(); api.mockReset(); });

describe("useLiveList", () => {
  it("keeps existing rows while loading newly collected records", async () => {
    api.mockResolvedValueOnce(["old"]);
    const { result } = renderHook(() => useLiveList<string[]>("items/"));
    await waitFor(() => expect(result.current.data).toEqual(["old"]));
    let finish!: (rows: string[]) => void;
    api.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    act(() => { window.dispatchEvent(new Event("collections-updated")); });
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toEqual(["old"]);
    await act(async () => { finish(["old", "new"]); });
    expect(result.current.data).toEqual(["old", "new"]);
    expect(result.current.loading).toBe(false);
  });

  it("ignores a stale response after changing filters", async () => {
    let finish!: (rows: string[]) => void;
    api.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const { result, rerender } = renderHook(({ path }) => useLiveList<string[]>(path), { initialProps: { path: "old/" } });
    await waitFor(() => expect(api).toHaveBeenCalledTimes(1));
    const signal = api.mock.calls[0][1].signal;
    api.mockResolvedValueOnce(["filtered"]);
    rerender({ path: "new/" });
    await waitFor(() => expect(result.current.data).toEqual(["filtered"]));
    expect(signal.aborted).toBe(true);
    await act(async () => { finish(["stale"]); });
    expect(result.current.data).toEqual(["filtered"]);
  });

  it("polls automatically and stops when the tab is inactive", async () => {
    vi.useFakeTimers();
    api.mockResolvedValue(["row"]);
    const { rerender } = renderHook(({ enabled }) => useLiveList("items/", enabled), { initialProps: { enabled: true } });
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    expect(api).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(api).toHaveBeenCalledTimes(2);
    rerender({ enabled: false });
    await act(async () => { await vi.advanceTimersByTimeAsync(20_000); });
    expect(api).toHaveBeenCalledTimes(2);
  });

  it("retains rows on failure and recovers on refresh", async () => {
    api.mockResolvedValueOnce(["row"]);
    const { result } = renderHook(() => useLiveList<string[]>("items/"));
    await waitFor(() => expect(result.current.data).toEqual(["row"]));
    api.mockRejectedValueOnce(new Error("Falha de conexão"));
    await act(async () => { await result.current.reload(); });
    expect(result.current.data).toEqual(["row"]);
    expect(result.current.error).toBe("Falha de conexão");
    expect(result.current.loading).toBe(false);
    api.mockResolvedValueOnce(["updated"]);
    await act(async () => { await result.current.reload(); });
    expect(result.current.error).toBe("");
    expect(result.current.data).toEqual(["updated"]);
  });
});
