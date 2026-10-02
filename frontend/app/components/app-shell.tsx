"use client";

import { Bell, ChartBar, ClockCounterClockwise, FileText, GearSix, House, Moon, Newspaper, SignOut, SpinnerGap, Sun } from "@phosphor-icons/react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api } from "../lib/api";
import type { NoticePage } from "../lib/types";
import { useAuth } from "../providers";
import celeriLogo from "../../public/images/celeri-logo.png";
import bmrLogoLight from "../../public/brand/logo-light@2x.png";
import bmrLogoDark from "../../public/brand/logo-dark@2x.png";

const links = [
  ["/", "Visão geral", House],
  ["/expedientes", "Expedientes", FileText],
  ["/djen", "Publicações DJEN", Newspaper],
  ["/historico", "Histórico", ClockCounterClockwise],
  ["/avisos", "Avisos", Bell],
  ["/estatisticas", "Estatísticas", ChartBar],
  ["/configuracoes", "Configurações", GearSix],
] as const;

export function Brand({ compact = false }: { compact?: boolean }) {
  return <Link href="/" className="flex items-center gap-4" title={compact ? "Céleri" : "Céleri e Barros, Mariz & Rebouças"}>
    <Image src={celeriLogo} alt="Céleri" width={56} height={56} unoptimized draggable={false} className="h-14 w-14 object-contain dark:brightness-0 dark:invert" priority />
    {!compact && <span className="border-l pl-4">
      <Image src={bmrLogoLight} alt="Barros, Mariz & Rebouças Advogados" width={90} height={36} unoptimized draggable={false} className="h-9 w-auto object-contain dark:hidden" priority />
      <Image src={bmrLogoDark} alt="" width={90} height={36} unoptimized draggable={false} className="hidden h-9 w-auto object-contain dark:block" priority />
    </span>}
  </Link>;
}

function NavLinks({ pathname, unreadNotices, mobile = false }: { pathname: string; unreadNotices: number; mobile?: boolean }) {
  return <nav className={cn("items-center gap-2", mobile ? "flex overflow-x-auto border-t px-4 py-2 xl:hidden" : "hidden xl:flex")} aria-label="Navegação principal">
    {links.map(([href, label, Icon]) => {
      const active = pathname === href;
      const count = href === "/avisos" ? unreadNotices : 0;
      return <Link key={href} href={href} className={cn("flex h-10 items-center gap-2 rounded-md px-4 text-sm font-medium transition-colors", mobile && "shrink-0", active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground")} aria-current={active ? "page" : undefined}>
        <Icon size={18} weight={active ? "fill" : "regular"} />
        <span>{label}</span>
        {count > 0 && <span className={cn("ml-auto grid size-6 place-items-center rounded-full text-xs font-semibold", active ? "bg-primary-foreground text-primary" : "bg-warning-soft text-warning")}>{count}</span>}
      </Link>;
    })}
  </nav>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout, setTheme } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [switchingTheme, setSwitchingTheme] = useState(false);
  const [dark, setDark] = useState(false);
  const [unreadNotices, setUnreadNotices] = useState(0);

  const loadUnreadNotices = useCallback(async () => {
    try { setUnreadNotices((await api<NoticePage>("notices/?read=unread")).count ?? 0); } catch { /* Navigation remains available offline. */ }
  }, []);

  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, user, router]);
  useEffect(() => {
    queueMicrotask(() => setDark(document.documentElement.dataset.theme === "dark"));
    if (!user) return;
    queueMicrotask(() => { void loadUnreadNotices(); });
    window.addEventListener("notices:changed", loadUnreadNotices);
    return () => window.removeEventListener("notices:changed", loadUnreadNotices);
  }, [user, loadUnreadNotices]);

  if (loading || !user) return <div className="grid min-h-screen place-items-center bg-background text-muted-foreground"><div className="flex items-center gap-4 rounded-lg border bg-card px-6 py-4 text-sm font-medium shadow-sm"><SpinnerGap size={20} className="animate-spin" />Preparando o painel operacional…</div></div>;

  const toggleTheme = async () => {
    setSwitchingTheme(true);
    try { await setTheme(dark ? "light" : "dark"); setDark(!dark); } finally { setSwitchingTheme(false); }
  };
  const leave = async () => { await logout(); router.replace("/login"); };
  const initials = user.display_name.charAt(0).toUpperCase();

  return <div className="min-h-screen bg-background text-foreground">
    <span role="status" aria-atomic="true" className="sr-only">{unreadNotices === 0 ? "Nenhum aviso não lido" : `${unreadNotices} aviso${unreadNotices === 1 ? "" : "s"} não lido${unreadNotices === 1 ? "" : "s"}`}</span>

    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-screen-2xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <div className="xl:hidden"><Brand compact /></div>
        <div className="hidden xl:block"><Brand /></div>
        <NavLinks pathname={pathname} unreadNotices={unreadNotices} />
        <div className="flex items-center gap-2">
          <Link href="/configuracoes" className="flex h-10 items-center gap-2 rounded-md border bg-card px-2 hover:bg-muted" title="Perfil e preferências">
            <span className="grid size-8 place-items-center rounded-full bg-muted text-xs font-semibold">{initials}</span>
            <span className="hidden max-w-32 truncate text-sm font-medium 2xl:block">{user.display_name}</span>
          </Link>
          <Button variant="outline" size="icon" disabled={switchingTheme} onClick={toggleTheme} aria-label={dark ? "Mudar para tema claro" : "Mudar para tema escuro"} title={dark ? "Mudar para tema claro" : "Mudar para tema escuro"}>{dark ? <Sun /> : <Moon />}</Button>
          <Button variant="outline" size="icon" onClick={leave} aria-label="Sair" title="Sair"><SignOut /></Button>
        </div>
      </div>
      <NavLinks pathname={pathname} unreadNotices={unreadNotices} mobile />
    </header>

    <main className="mx-auto w-full max-w-screen-2xl px-4 py-8 sm:px-6 lg:px-8">{children}</main>
    <footer className="border-t px-6 py-8 text-center text-xs text-muted-foreground">Barros, Mariz & Rebouças Advogados · Céleri Comunicações · © 2026 RYVTEC Soluções e Consultoria. Todos os direitos reservados.</footer>
  </div>;
}
