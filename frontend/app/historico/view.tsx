"use client";

import { CalendarBlank, FolderSimple } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AppShell } from "../components/app-shell";
import { ExpedienteDrawer } from "../components/expediente-drawer";
import { ExpedienteList } from "../components/expediente-list";
import { CollectionHistoryPanel } from "../components/collection-history";
import { Panel, LoadingRows, PageTitle, Pagination } from "../components/ui";
import { useNotifications } from "../components/notifications";
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
  const { notify } = useNotifications();
  const [error, setError] = useState("");
  const tab = search.get("tab") === "orquestracao" ? "orquestracao" : "expedientes";
  const page = Math.max(1, Number(search.get("page") ?? 1) || 1);
  const load = useCallback(async () => {
    try { setData(await api<History>("history/?page=" + page)); setError(""); }
    catch (exception) { const message = exception instanceof Error ? exception.message : "Falha ao carregar o histórico."; setError(message); notify({ message }); }
  }, [page, notify]);
  useEffect(() => {
    if (tab !== "expedientes") return;
    queueMicrotask(() => { void load(); });
  }, [load, tab]);

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

  const selectTab = (nextTab: "expedientes" | "orquestracao") => {
    const params = new URLSearchParams(search);
    if (nextTab === "expedientes") params.delete("tab");
    else params.set("tab", nextTab);
    params.delete("page");
    const query = params.toString();
    router.replace(`/historico${query ? `?${query}` : ""}`, { scroll: false });
  };

  return <AppShell>
    <PageTitle title="Histórico" description="Consulte os expedientes identificados e a orquestração das fontes nos últimos 30 dias." />
    <Tabs value={tab} onValueChange={(value) => selectTab(value as "expedientes" | "orquestracao")}>
      <TabsList aria-label="Tipo de histórico"><TabsTrigger value="expedientes">Expedientes</TabsTrigger><TabsTrigger value="orquestracao">Orquestração de coletas</TabsTrigger></TabsList>
      <TabsContent value="orquestracao"><CollectionHistoryPanel /></TabsContent>
      <TabsContent value="expedientes">

    {!data && !error && <LoadingRows />}
    {data && <div className="space-y-8">{data.days.map((day) => {
      const items = itemsForDay(day);
      const totalLabel = `${day.new_count} expediente${day.new_count === 1 ? "" : "s"}`;
      return <section key={day.date} aria-labelledby={`history-day-${day.date}`}>
        <header className="mb-4 flex items-center gap-4"><span className="grid size-10 shrink-0 place-items-center rounded-xl border border-border bg-muted text-muted-foreground"><CalendarBlank size={18} weight="duotone" aria-hidden="true" /></span><h2 id={`history-day-${day.date}`} className="text-sm font-extrabold tracking-tight text-foreground sm:text-base">{formatDay(day.date)} <span className="font-medium text-muted-foreground">({totalLabel})</span></h2></header>
        {items.length ? <ExpedienteList items={items} onSelect={setSelected} /> : <Panel innerClassName="flex items-center gap-4 px-6 py-4 text-xs font-semibold text-muted-foreground"><FolderSimple size={19} weight="duotone" className="shrink-0" />Nenhum expediente novo coletado neste dia.</Panel>}
      </section>;
    })}
    {data.count === 0 && <Panel innerClassName="flex items-center gap-4 px-6 py-4 text-xs font-semibold text-muted-foreground"><FolderSimple size={19} weight="duotone" className="shrink-0" />Nenhum expediente novo coletado nos últimos 30 dias.</Panel>}
    <Pagination page={page} pages={pages} onPageChange={go} label="Paginação do histórico" />
    </div>}
    <ExpedienteDrawer item={selected} onClose={() => setSelected(null)} onRead={markRead} />
    </TabsContent>
    </Tabs>
  </AppShell>;
}
