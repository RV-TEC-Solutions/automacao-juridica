"use client";

import { CalendarBlank, FolderSimple } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "../components/app-shell";
import { ExpedienteDrawer } from "../components/expediente-drawer";
import { ExpedienteList } from "../components/expediente-list";
import { BezelCard, Feedback, LoadingRows, PageTitle } from "../components/ui";
import { api } from "../lib/api";
import type { Expediente, History } from "../lib/types";

function formatDay(date: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Fortaleza", day: "numeric", month: "long", year: "numeric",
  }).format(new Date(`${date}T12:00:00-03:00`));
}

function itemsForDay(day: History["days"][number]): Expediente[] {
  return day.items.map(({ event, expediente }) => ({ ...expediente, latest_event: event }));
}

export function HistoricoClient() {
  const router = useRouter();
  const search = useSearchParams();
  const [data, setData] = useState<History | null>(null);
  const [selected, setSelected] = useState<Expediente | null>(null);
  const [error, setError] = useState("");
  const page = Math.max(1, Number(search.get("page") ?? 1) || 1);
  const load = useCallback(async () => {
    try { setData(await api<History>("history/?page=" + page)); setError(""); }
    catch (exception) { setError(exception instanceof Error ? exception.message : "Falha ao carregar o histórico."); }
  }, [page]);
  useEffect(() => {
    queueMicrotask(() => { void load(); });
  }, [load]);

  const markRead = () => {
    if (!selected) return;
    const selectedId = selected.id;
    setSelected((item) => item ? { ...item, unread: false } : item);
    setData((current) => current && {
      ...current,
      days: current.days.map((day) => ({
        ...day,
        items: day.items.map((item) => item.expediente.id === selectedId
          ? { ...item, expediente: { ...item.expediente, unread: false } } : item),
      })),
    });
  };

  const pages = Math.max(1, Math.ceil((data?.count ?? 0) / (data?.page_size ?? 50)));
  const go = (nextPage: number) => {
    const params = new URLSearchParams(search);
    params.set("page", String(nextPage));
    router.replace("/historico?" + params);
  };

  return <AppShell>
    <PageTitle eyebrow="Auditoria de coletas" title="Histórico" description="Expedientes inéditos identificados nas coletas dos últimos 30 dias, organizados pela data da coleta em páginas de até 50 itens." />
    {error && <Feedback action={<button className="button-secondary cursor-pointer px-3.5 py-1.5 text-xs font-bold" onClick={load}>Tentar novamente</button>}>{error}</Feedback>}
    {!data && !error && <LoadingRows />}
    {data && <div className="space-y-7">{data.days.map((day) => {
      const items = itemsForDay(day);
      const totalLabel = `${day.new_count} expediente${day.new_count === 1 ? "" : "s"}`;
      return <section key={day.date} aria-labelledby={`history-day-${day.date}`}>
        <header className="mb-3 flex items-center gap-3"><span className="grid size-9 shrink-0 place-items-center rounded-xl border border-rule bg-panel-muted text-quiet"><CalendarBlank size={18} weight="duotone" aria-hidden="true" /></span><h2 id={`history-day-${day.date}`} className="text-sm font-extrabold tracking-tight text-ink sm:text-base">{formatDay(day.date)} <span className="font-medium text-quiet">({totalLabel})</span></h2></header>
        {items.length ? <ExpedienteList items={items} onSelect={setSelected} showSourceBadge /> : <BezelCard innerClassName="flex items-center gap-3 px-5 py-4 text-xs font-semibold text-quiet"><FolderSimple size={19} weight="duotone" className="shrink-0" />Nenhum expediente novo coletado neste dia.</BezelCard>}
      </section>;
    })}
    {data.count === 0 && <BezelCard innerClassName="flex items-center gap-3 px-5 py-4 text-xs font-semibold text-quiet"><FolderSimple size={19} weight="duotone" className="shrink-0" />Nenhum expediente novo coletado nos últimos 30 dias.</BezelCard>}
    {pages > 1 && <nav className="flex items-center justify-center gap-3 text-xs font-medium text-quiet" aria-label="Paginação do histórico">
      <button className="button-secondary cursor-pointer px-3.5 py-2 text-xs font-bold disabled:pointer-events-none disabled:opacity-40" disabled={page <= 1} onClick={() => go(page - 1)}>← Anterior</button>
      <span className="px-2">Página <strong className="font-[family-name:var(--font-mono)] font-bold text-ink">{page}</strong> de <span className="font-[family-name:var(--font-mono)]">{pages}</span></span>
      <button className="button-secondary cursor-pointer px-3.5 py-2 text-xs font-bold disabled:pointer-events-none disabled:opacity-40" disabled={page >= pages} onClick={() => go(page + 1)}>Próxima →</button>
    </nav>}
    </div>}
    <ExpedienteDrawer item={selected} onClose={() => setSelected(null)} onRead={markRead} />
  </AppShell>;
}
