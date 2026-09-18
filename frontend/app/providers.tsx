"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, ensureCsrf } from "./lib/api";
import type { User } from "./lib/types";

type AuthValue = { user: User | null; loading: boolean; login: (username: string, password: string) => Promise<void>; logout: () => Promise<void>; refresh: () => Promise<void>; setTheme: (theme: User["theme"]) => Promise<void> };
const AuthContext = createContext<AuthValue | null>(null);

function applyTheme(theme: User["theme"]) {
  const resolved = theme === "system"
    ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    : theme;
  document.documentElement.dataset.theme = resolved;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try { const value = await api<User>("auth/me/"); setUser(value); applyTheme(value.theme); }
    catch { setUser(null); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { ensureCsrf().then(refresh).catch(() => setLoading(false)); }, [refresh]);
  const login = async (username: string, password: string) => {
    await ensureCsrf();
    const value = await api<User>("auth/login/", { method: "POST", body: JSON.stringify({ username, password }) });
    setUser(value); applyTheme(value.theme);
  };
  const logout = async () => { await api("auth/logout/", { method: "POST" }); setUser(null); };
  const setTheme = async (theme: User["theme"]) => {
    await api("settings/", { method: "PATCH", body: JSON.stringify({ theme }) });
    setUser((current) => current ? { ...current, theme } : current);
    applyTheme(theme);
  };
  useEffect(() => {
    if (!user || user.theme !== "system") return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const syncTheme = () => applyTheme("system");
    media.addEventListener("change", syncTheme);
    return () => media.removeEventListener("change", syncTheme);
  }, [user]);
  return <AuthContext.Provider value={{ user, loading, login, logout, refresh, setTheme }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
