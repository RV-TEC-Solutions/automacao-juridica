"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "../providers";
import { Icon } from "./icons";

const links = [
  ["/", "Início", "home"],
  ["/expedientes", "Expedientes", "file"],
  ["/estatisticas", "Estatísticas", "chart"],
  ["/configuracoes", "Configurações", "settings"],
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-2.5 text-muted">
        <div className="size-5 animate-spin rounded-full border-2 border-line border-t-accent" />
        <span>Preparando seu painel…</span>
      </div>
    );
  }

  const initials = user.display_name.charAt(0).toUpperCase();

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-[236px] flex-col border-r border-r-black/[.18] bg-sidebar px-3 pt-[18px] pb-[14px] text-white max-[760px]:hidden">
        <Link href="/" className="flex items-center gap-2.5 px-2 pt-0.5 pb-[22px] no-underline">
          <span className="grid size-[34px] shrink-0 place-items-center rounded-[7px] bg-[#f5d3c4] text-[12px] font-extrabold tracking-[-.02em] text-[#713d2d] shadow-[inset_0_0_0_1px_rgba(83,41,26,.12)]">PE</span>
          <span className="flex flex-col gap-px">
            <strong className="text-[16px] leading-[1.1]">Painel</strong>
            <small className="text-[12px] text-white/[.68]">Expedientes</small>
          </span>
        </Link>
        <span className="px-2.5 py-2 text-[11px] font-bold tracking-[.09em] text-white/[.58] uppercase">Workspace</span>
        <nav className="flex flex-col gap-[3px]">
          {links.map(([href, label, icon]) => (
            <Link key={href} href={href} className={`relative flex min-h-10 items-center gap-[11px] rounded-md px-[11px] font-[550] text-white/[.78] no-underline transition-[background-color,border-color,color,opacity] duration-[160ms] hover:bg-black/[.09] hover:text-white ${pathname === href ? "bg-sidebar-active text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,.08)] before:absolute before:left-0 before:h-5 before:w-[3px] before:rounded-r before:bg-[#ffe4d8] before:content-['']" : ""}`}>
              <Icon name={icon} />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
        <div className="mt-auto grid grid-cols-[32px_1fr_auto] items-center gap-[9px] border-t border-white/[.18] px-1.5 pt-[14px] pb-0.5">
          <div className="grid size-8 place-items-center rounded-full bg-[#f3cab8] text-[13px] font-extrabold text-[#6e3928]">{initials}</div>
          <div className="flex min-w-0 flex-col">
            <strong className="overflow-hidden text-[13px] text-ellipsis whitespace-nowrap">{user.display_name}</strong>
            <small className="text-[11px] text-white/[.58]">{user.username}</small>
          </div>
          <button
            className="grid cursor-pointer place-items-center rounded-md border-0 bg-transparent p-[7px] text-inherit transition-[background-color,border-color,color,opacity] duration-[160ms] hover:bg-white/10"
            aria-label="Sair"
            onClick={async () => {
              await logout();
              router.replace("/login");
            }}
          >
            <Icon name="logout" />
          </button>
        </div>
      </aside>

      <main className="min-h-screen ml-[236px] max-[760px]:ml-0">
        <div className="min-h-[calc(100vh-58px)] max-[760px]:min-h-screen">{children}</div>
      </main>

      <nav className="fixed right-0 bottom-0 left-0 z-50 hidden h-[62px] grid-cols-4 border-t border-line bg-topbar-solid backdrop-blur-[12px] max-[760px]:grid">
        {links.map(([href, label, icon]) => (
          <Link key={href} href={href} className={`flex flex-col items-center justify-center gap-[3px] text-[10px] text-muted no-underline ${pathname === href ? "text-accent" : ""}`}>
            <Icon name={icon} />
            <span>{label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
