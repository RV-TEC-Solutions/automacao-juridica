"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ChartBar, FileText, GearSix, House, Moon, SignOut, SpinnerGap, Sun } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { useAuth } from "../providers";

const links = [
  ["/", "Visão geral", House],
  ["/expedientes", "Expedientes", FileText],
  ["/estatisticas", "Estatísticas", ChartBar],
  ["/configuracoes", "Configurações", GearSix],
] as const;

export function Brand({ compact = false }: { compact?: boolean }) {
  return <Link href="/" className="flex shrink-0 items-center gap-3 no-underline"><span className="grid size-10 place-items-center rounded-xl bg-brand font-[family-name:var(--font-mono)] text-xs font-extrabold tracking-[-.08em] text-white shadow-sm shadow-brand/30">AE</span>{!compact && <span className="hidden min-[420px]:flex flex-col"><strong className="text-[13px] leading-4 text-ink">Automação</strong><small className="text-[11px] font-semibold text-quiet">de Expedientes</small></span>}</Link>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout, setTheme } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [switchingTheme, setSwitchingTheme] = useState(false);

  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, user, router]);

  if (loading || !user) return <div className="grid min-h-screen place-items-center bg-app text-quiet"><div className="flex items-center gap-3 rounded-xl border border-rule bg-panel px-4 py-3 text-sm font-semibold shadow-sm"><SpinnerGap size={18} className="animate-spin text-brand" />Preparando o painel…</div></div>;

  const initials = user.display_name.charAt(0).toUpperCase();
  return <div className="min-h-screen bg-app text-ink">
    <header className="sticky top-0 z-40 border-b border-rule bg-[var(--shell)] backdrop-blur-xl">
      <div className="mx-auto flex h-[68px] max-w-[1600px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Brand />
        <nav className="hidden items-center rounded-xl border border-rule bg-panel-muted p-1 shadow-sm lg:flex" aria-label="Navegação principal">
          {links.map(([href, label, Icon]) => { const active = pathname === href; return <Link key={href} href={href} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold no-underline transition-colors ${active ? "bg-brand text-white shadow-sm" : "text-quiet hover:bg-panel hover:text-ink"}`}><Icon size={16} weight={active ? "fill" : "regular"} />{label}</Link>; })}
        </nav>
        <div className="flex items-center gap-2"><Link href="/configuracoes" className="hidden items-center gap-2 rounded-xl border border-rule bg-panel px-2.5 py-2 text-xs font-bold text-ink-soft no-underline shadow-sm sm:flex"><span className="grid size-5 place-items-center rounded-full bg-brand-soft text-[10px] font-extrabold text-brand">{initials}</span><span className="max-w-28 truncate">{user.display_name}</span></Link><button className="grid size-10 cursor-pointer place-items-center rounded-xl border border-rule bg-panel text-quiet shadow-sm transition-colors hover:bg-panel-muted hover:text-brand disabled:opacity-50" aria-label={document.documentElement.dataset.theme === "dark" ? "Mudar para tema claro" : "Mudar para tema escuro"} title={document.documentElement.dataset.theme === "dark" ? "Mudar para tema claro" : "Mudar para tema escuro"} disabled={switchingTheme} onClick={async () => { const current = document.documentElement.dataset.theme; setSwitchingTheme(true); try { await setTheme(current === "dark" ? "light" : "dark"); } finally { setSwitchingTheme(false); } }}>{document.documentElement.dataset.theme === "dark" ? <Sun size={18} weight="duotone" /> : <Moon size={18} weight="duotone" />}</button><button className="grid size-10 cursor-pointer place-items-center rounded-xl border border-rule bg-panel text-quiet shadow-sm transition-colors hover:bg-panel-muted hover:text-danger" aria-label="Sair" title="Sair" onClick={async () => { await logout(); router.replace("/login"); }}><SignOut size={18} /></button></div>
      </div>
      <nav className="flex gap-1 overflow-x-auto border-t border-rule px-4 py-2 lg:hidden" aria-label="Navegação principal móvel">
        {links.map(([href, label, Icon]) => { const active = pathname === href; return <Link key={href} href={href} className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold no-underline ${active ? "bg-brand text-white" : "bg-panel-muted text-quiet"}`}><Icon size={15} weight={active ? "fill" : "regular"} />{label}</Link>; })}
      </nav>
    </header>
    <main className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
    <footer className="mt-8 border-t border-rule px-4 py-5 text-center text-xs text-quiet"><span className="font-bold text-ink-soft">AUTOMAÇÃO DE EXPEDIENTES</span><span className="mx-2">•</span>Dados processados localmente</footer>
  </div>;
}
