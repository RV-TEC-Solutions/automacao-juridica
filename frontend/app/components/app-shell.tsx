"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, ChartBar, ClockCounterClockwise, FileText, GearSix, House, Moon, SignOut, SpinnerGap, Sun } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../providers";
import { api } from "../lib/api";
import type { NoticePage } from "../lib/types";

const links = [
  ["/", "Visão geral", House],
  ["/expedientes", "Expedientes", FileText],
  ["/historico", "Histórico", ClockCounterClockwise],
  ["/avisos", "Avisos", Bell],
  ["/estatisticas", "Estatísticas", ChartBar],
  ["/configuracoes", "Configurações", GearSix],
] as const;

export function Brand({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <Link href="/" className="group flex shrink-0 items-center gap-2 no-underline" title="Barros, Mariz & Rebouças Advogados">
        <div className="flex items-center">
          <img
            src="/brand/logo-mark-light@2x.png"
            alt="BMR Advogados"
            className="theme-light-only h-9 w-auto object-contain transition-transform group-hover:scale-105"
          />
          <img
            src="/brand/logo-mark-dark@2x.png"
            alt="BMR Advogados"
            className="theme-dark-only h-9 w-auto object-contain transition-transform group-hover:scale-105"
          />
        </div>
      </Link>
    );
  }

  return (
    <Link href="/" className="group flex shrink-0 items-center gap-3.5 no-underline" title="Barros, Mariz & Rebouças Advogados">
      <div className="flex items-center">
        <img
          src="/brand/logo-light@2x.png"
          alt="Barros, Mariz & Rebouças Advogados"
          className="theme-light-only h-9 w-auto object-contain transition-transform group-hover:scale-[1.02]"
        />
        <img
          src="/brand/logo-dark@2x.png"
          alt="Barros, Mariz & Rebouças Advogados"
          className="theme-dark-only h-9 w-auto object-contain transition-transform group-hover:scale-[1.02]"
        />
      </div>
      <div className="hidden min-[540px]:flex flex-col border-l border-rule pl-3 py-0.5">
        <strong className="text-[11px] font-extrabold tracking-tight text-ink leading-none">Automação PJe</strong>
        <span className="mt-1 flex items-center gap-1.5 text-[10px] font-semibold text-quiet">
          <span className="size-1.5 rounded-full bg-positive animate-pulse" />
          Operação Local
        </span>
      </div>
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout, setTheme } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [switchingTheme, setSwitchingTheme] = useState(false);
  const [unreadNotices, setUnreadNotices] = useState(0);

  const loadUnreadNotices = useCallback(async () => {
    try {
      const notices = await api<NoticePage>("notices/?read=unread");
      setUnreadNotices(notices.count);
    } catch {
      // A falha ao buscar a contagem não deve impedir a navegação do usuário.
    }
  }, []);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    queueMicrotask(() => { void loadUnreadNotices(); });
    window.addEventListener("notices:changed", loadUnreadNotices);
    return () => window.removeEventListener("notices:changed", loadUnreadNotices);
  }, [user, loadUnreadNotices]);

  if (loading || !user) {
    return (
      <div className="grid min-h-screen place-items-center bg-app text-quiet">
        <div className="flex items-center gap-3 rounded-2xl border border-rule bg-panel px-5 py-4 text-sm font-semibold shadow-sm">
          <SpinnerGap size={20} className="animate-spin text-ink-soft" />
          Preparando o painel operacional…
        </div>
      </div>
    );
  }

  const initials = user.display_name.charAt(0).toUpperCase();

  return (
    <div className="min-h-screen bg-app text-ink">
      <span role="status" aria-atomic="true" className="sr-only">{unreadNotices === 0 ? "Nenhum aviso não lido" : unreadNotices === 1 ? "1 aviso não lido" : `${unreadNotices} avisos não lidos`}</span>
      <header className="sticky top-0 z-40 border-b border-rule bg-[var(--shell)] backdrop-blur-xl">
        <div className="mx-auto flex h-[72px] max-w-[1600px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <Brand />

          <nav className="hidden items-center rounded-xl border border-rule bg-panel-muted/80 p-1 shadow-sm lg:flex" aria-label="Navegação principal">
            {links.map(([href, label, Icon]) => {
              const active = pathname === href;
              const isNotices = href === "/avisos";
              const unreadLabel = unreadNotices === 1 ? "1 aviso não lido" : `${unreadNotices} avisos não lidos`;
              return (
                <Link
                  key={href}
                  href={href}
                  aria-label={isNotices && unreadNotices > 0 ? `${label}, ${unreadLabel}` : label}
                  className={`relative flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-bold no-underline transition-all ${
                    active
                      ? "bg-brand text-brand-fg shadow-sm"
                      : "text-quiet hover:bg-panel hover:text-ink"
                  }`}
                >
                  <Icon size={16} weight={active || (isNotices && unreadNotices > 0) ? "fill" : "regular"} className={isNotices && unreadNotices > 0 ? "notice-bell text-caution" : undefined} />
                  {label}
                  {isNotices && unreadNotices > 0 && (
                    <span aria-hidden="true" className="absolute -bottom-2 -right-2 grid size-6 place-items-center rounded-full border border-caution/25 bg-caution-soft text-[11px] font-extrabold leading-none text-caution shadow-sm">
                      {unreadNotices}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-2.5">
            <Link
              href="/configuracoes"
              className="hidden items-center gap-2.5 rounded-xl border border-rule bg-panel px-3 py-2 text-xs font-bold text-ink-soft no-underline shadow-sm transition-colors hover:border-zinc-400 sm:flex"
            >
              <span className="grid size-6 place-items-center rounded-full bg-panel-muted border border-rule text-[10px] font-extrabold text-ink">
                {initials}
              </span>
              <span className="max-w-32 truncate">{user.display_name}</span>
            </Link>

            <button
              className="grid size-10 cursor-pointer place-items-center rounded-xl border border-rule bg-panel text-quiet shadow-sm transition-all hover:bg-panel-muted hover:text-ink disabled:opacity-50"
              aria-label={document.documentElement.dataset.theme === "dark" ? "Mudar para tema claro" : "Mudar para tema escuro"}
              title={document.documentElement.dataset.theme === "dark" ? "Mudar para tema claro" : "Mudar para tema escuro"}
              disabled={switchingTheme}
              onClick={async () => {
                const current = document.documentElement.dataset.theme;
                setSwitchingTheme(true);
                try {
                  await setTheme(current === "dark" ? "light" : "dark");
                } finally {
                  setSwitchingTheme(false);
                }
              }}
            >
              {document.documentElement.dataset.theme === "dark" ? (
                <Sun size={18} weight="duotone" />
              ) : (
                <Moon size={18} weight="duotone" />
              )}
            </button>

            <button
              className="grid size-10 cursor-pointer place-items-center rounded-xl border border-rule bg-panel text-quiet shadow-sm transition-all hover:bg-panel-muted hover:text-danger"
              aria-label="Sair"
              title="Sair"
              onClick={async () => {
                await logout();
                router.replace("/login");
              }}
            >
              <SignOut size={18} />
            </button>
          </div>
        </div>

        <nav className="flex gap-1.5 overflow-x-auto border-t border-rule px-4 py-2 lg:hidden" aria-label="Navegação principal móvel">
          {links.map(([href, label, Icon]) => {
            const active = pathname === href;
            const isNotices = href === "/avisos";
            const unreadLabel = unreadNotices === 1 ? "1 aviso não lido" : `${unreadNotices} avisos não lidos`;
            return (
              <Link
                key={href}
                href={href}
                aria-label={isNotices && unreadNotices > 0 ? `${label}, ${unreadLabel}` : label}
                className={`relative flex shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-bold no-underline transition-colors ${
                  active ? "bg-brand text-brand-fg" : "bg-panel-muted/80 text-quiet"
                }`}
              >
                <Icon size={15} weight={active || (isNotices && unreadNotices > 0) ? "fill" : "regular"} className={isNotices && unreadNotices > 0 ? "notice-bell text-caution" : undefined} />
                {label}
                {isNotices && unreadNotices > 0 && (
                  <span aria-hidden="true" className="absolute -bottom-2 -right-2 grid size-6 place-items-center rounded-full border border-caution/25 bg-caution-soft text-[11px] font-extrabold leading-none text-caution shadow-sm">
                    {unreadNotices}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </header>

      <main className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>

      <footer className="mt-12 border-t border-rule px-4 py-7 text-center text-xs text-quiet">
        <div className="flex flex-col sm:flex-row items-center justify-center gap-2">
          <span className="font-bold tracking-wider text-ink-soft uppercase">Barros, Mariz & Rebouças Advogados</span>
          <span className="hidden sm:inline text-quiet/60">•</span>
          <span>Automação de Expedientes PJe</span>
          <span className="hidden sm:inline text-quiet/60">•</span>
          <span className="text-[11px]">Operação local e segura</span>
        </div>
      </footer>
    </div>
  );
}
