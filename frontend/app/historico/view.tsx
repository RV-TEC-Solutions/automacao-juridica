"use client";

import { CalendarBlank, FolderSimple } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AppShell } from "../components/app-shell";
import { ExpedienteDrawer } from "../components/expediente-drawer";
import { ExpedienteList } from "../components/expediente-list";
import { CollectionHistoryPanel } from "../components/collection-history";
import { EmptyState, HistoryDayHeader, LoadingRows, PageTitle, Pagination } from "../components/ui";
import { useNotifications } from "../components/notifications";
import { api } from "../lib/api";
import type { Expediente, History } from "../lib/types";

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
      return <section key={day.date} aria-labelledby={`history-day-${day.date}`}>
        <HistoryDayHeader date={day.date} label={`${day.new_count} expediente${day.new_count === 1 ? "" : "s"}`} icon={<CalendarBlank size={18} weight="duotone" aria-hidden="true" />} id={`history-day-${day.date}`} />
        <ExpedienteList items={day.items.map(({ event, expediente }) => ({ ...expediente, latest_event: event }))} onSelect={setSelected} />
      </section>;
    })}
    {data.count === 0 && <EmptyState icon={<FolderSimple size={26} weight="duotone" />} title="Nenhum expediente encontrado" description="A consulta diária pode não ter expedientes para os filtros atuais." />}
    <Pagination page={page} pages={pages} onPageChange={go} label="Paginação do histórico" />
    </div>}
    <ExpedienteDrawer item={selected} onClose={() => setSelected(null)} onRead={markRead} />
    </TabsContent>
    </Tabs>
  </AppShell>;
}
