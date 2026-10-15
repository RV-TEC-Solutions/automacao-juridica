"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

// Keep visible lists fresh, including collections started in another browser.
export function useLiveList<T>(path: string, enabled = true, intervalMs = 10_000) {
  const [snapshot, setSnapshot] = useState<{ path: string; data: T | null }>({ path, data: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const request = useRef<AbortController | null>(null);

  const reload = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError("");
    try {
      const data = await api<T>(path, { signal: controller.signal });
      if (!controller.signal.aborted) {
        setSnapshot({ path, data });
        setError("");
      }
    } catch (exception) {
      if (!controller.signal.aborted) {
        setError(exception instanceof Error ? exception.message : "Não foi possível atualizar a lista.");
      }
    } finally {
      if (request.current === controller) request.current = null;
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    if (!enabled) return;
    let disposed = false;
    queueMicrotask(() => { if (!disposed) void reload(); });
    const refresh = () => {
      if (document.visibilityState === "visible" && !request.current) void reload();
    };
    // Avoid cancelling slow requests on every polling tick.
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible" && !request.current) void reload();
    }, intervalMs);
    const onVisible = refresh;
    window.addEventListener("focus", refresh);
    window.addEventListener("collections-updated", onVisible);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      disposed = true;
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
      window.removeEventListener("collections-updated", onVisible);
      document.removeEventListener("visibilitychange", onVisible);
      request.current?.abort();
      request.current = null;
    };
  }, [enabled, intervalMs, reload]);

  const setData = useCallback((update: T | null | ((current: T | null) => T | null)) => {
    setSnapshot((current) => ({ path, data: typeof update === "function"
      ? (update as (current: T | null) => T | null)(current.path === path ? current.data : null) : update }));
  }, [path]);
  const data = snapshot.path === path ? snapshot.data : null;
  return { data, setData, loading: enabled && (loading || (!data && !error)), error, reload };
}
