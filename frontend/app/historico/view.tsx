"use client";

import { CalendarBlank, FolderSimple, Newspaper } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AppShell } from "../components/app-shell";
import { ExpedienteDrawer } from "../components/expediente-drawer";
import { ExpedienteList } from "../components/expediente-list";
import { DjenList } from "../components/djen-list";
import { DjenDrawer } from "../components/djen-drawer";
import { CollectionHistoryPanel } from "../components/collection-history";
import { PdfExportButton } from "../components/pdf-export-button";
import { EmptyState, HistoryDayHeader, ListLoading, LoadingRows, PageTitle, Pagination } from "../components/ui";
import { useNotifications } from "../components/notifications";
import { useLiveList } from "../hooks/use-live-list";
import { localCollectionDate } from "../lib/export";
import type { DjenCommunication, DjenHistory, Expediente, History } from "../lib/types";
import { getCollectionSite } from "../lib/collection-sites";
import { useAuth } from "../providers";

export function HistoricoClient() {
  const router = useRouter();
  const search = useSearchParams();
  const { user } = useAuth();
  const [selected, setSelected] = useState<Expediente | null>(null);
  const [selectedPublication, setSelectedPublication] = useState<DjenCommunication | null>(null);
  const { notify } = useNotifications();
  const [dateFrom, setDateFrom] = useState(() => search.get("date_from") || localCollectionDate(-29));
  const [dateTo, setDateTo] = useState(() => search.get("date_to") || localCollectionDate());
  const appliedFrom = search.get("date_from") || localCollectionDate(-29);
  const appliedTo = search.get("date_to") || localCollectionDate();
  const tab = search.get("tab") === "orquestracao" ? "orquestracao" : search.get("tab") === "publicacoes" ? "publicacoes" : "expedientes";
  const page = Math.max(1, Number(search.get("page") ?? 1) || 1);
  useEffect(() => {
    const source = search.get("failed_source");
    if (!user || tab !== "orquestracao" || !source) return;
    const site = getCollectionSite(source);
    if (site) notify({
      tone: "warning",
      message: `A coleta de ${site.name}${search.get("collector") === "murilo" ? " de Dr. Murilo" : search.get("collector") === "cristiano" ? " de Dr. Cristiano" : ""} falhou. Você pode consultar os expedientes manualmente, diretamente no site.`,
      link: { href: site.href, label: `Clique aqui para acessar ${site.name}` },
    });
    const params = new URLSearchParams(search);
    params.delete("failed_source");
    params.delete("collector");
    router.replace(`/historico?${params}`, { scroll: false });
  }, [user, tab, search, router, notify]);
  const historyParams = new URLSearchParams({ page: String(page), date_from: appliedFrom, date_to: appliedTo });
  const publicationParams = new URLSearchParams({ page: String(page), collected_from: appliedFrom, collected_to: appliedTo });
  const { data, setData, reload: reloadHistory, loading: historyLoading, error: historyError } = useLiveList<History>(`history/?${historyParams}`, tab === "expedientes");
  const { data: publications, setData: setPublications, reload: reloadPublications, loading: publicationsLoading, error: publicationsError } = useLiveList<DjenHistory>(`djen/history/?${publicationParams}`, tab === "publicacoes");

  const applyDates = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const earliest = localCollectionDate(-29);
    const latest = localCollectionDate();
    if (dateFrom > dateTo || dateFrom < earliest || dateTo > latest) {
      notify({ tone: "warning", message: "Escolha um intervalo válido dentro dos últimos 30 dias." });
      return;
    }
    const params = new URLSearchParams(search);
    params.set("date_from", dateFrom); params.set("date_to", dateTo); params.delete("page");
    if (dateFrom === appliedFrom && dateTo === appliedTo && page === 1) {
      if (tab === "expedientes") void reloadHistory();
      if (tab === "publicacoes") void reloadPublications();
    }
    router.replace(`/historico?${params}`, { scroll: false });
  };

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

  const selectTab = (nextTab: "expedientes" | "publicacoes" | "orquestracao") => {
    const params = new URLSearchParams(search);
    if (nextTab === "expedientes") params.delete("tab");
    else params.set("tab", nextTab);
    params.delete("page");
    const query = params.toString();
    router.replace(`/historico${query ? `?${query}` : ""}`, { scroll: false });
  };

  return <AppShell>
    <PageTitle title="Histórico" description="Consulte expedientes, publicações processuais e coletas dos últimos 30 dias." />
    <Tabs value={tab} onValueChange={(value) => selectTab(value as "expedientes" | "publicacoes" | "orquestracao")}>
      <TabsList aria-label="Tipo de histórico"><TabsTrigger value="expedientes">Expedientes</TabsTrigger><TabsTrigger value="publicacoes">Publicações Processuais</TabsTrigger><TabsTrigger value="orquestracao">Orquestração de coletas</TabsTrigger></TabsList>
      {tab !== "orquestracao" && <form onSubmit={applyDates} className="my-5 flex flex-wrap items-end gap-3 rounded-lg border bg-card p-4">
        <label className="space-y-1 text-xs font-semibold">Coletas de<Input type="date" value={dateFrom} min={localCollectionDate(-29)} max={localCollectionDate()} onChange={(event) => setDateFrom(event.target.value)} required /></label>
        <label className="space-y-1 text-xs font-semibold">Até<Input type="date" value={dateTo} min={localCollectionDate(-29)} max={localCollectionDate()} onChange={(event) => setDateTo(event.target.value)} required /></label>
        <Button type="submit" variant="outline">Aplicar período</Button>
      </form>}
      <TabsContent value="orquestracao"><CollectionHistoryPanel /></TabsContent>
      <TabsContent value="publicacoes">
        <div className="mb-4 flex justify-start"><PdfExportButton path={`djen/communications/export.pdf/?${new URLSearchParams({ scope: "history", collected_from: appliedFrom, collected_to: appliedTo })}`} count={publications?.count} disabled={dateFrom !== appliedFrom || dateTo !== appliedTo} label="Exportar histórico de publicações em PDF" /></div>
        <ListLoading loading={publicationsLoading} error={publicationsError} />
        {!publications && !publicationsError && <LoadingRows />}
        {publications && <div className="space-y-8">
          {publications.days.map((day) => <section key={day.date} aria-labelledby={`publication-day-${day.date}`}>
            <HistoryDayHeader date={day.date} label={`${day.items.length} publicação${day.items.length === 1 ? "" : "ões"}`} icon={<Newspaper size={18} weight="duotone" aria-hidden="true" />} id={`publication-day-${day.date}`} />
            <DjenList items={day.items} onSelect={setSelectedPublication} />
          </section>)}
          {publications.count === 0 && <EmptyState icon={<Newspaper size={26} weight="duotone" />} title="Nenhuma publicação encontrada" description="Não houve publicações processuais coletadas nos últimos 30 dias." />}
          <Pagination page={page} pages={Math.max(1, Math.ceil(publications.count / publications.page_size))} onPageChange={go} label="Paginação do histórico de publicações" />
        </div>}
        <DjenDrawer item={selectedPublication} onClose={() => setSelectedPublication(null)} onRead={(updated) => {
          setSelectedPublication(updated);
          setPublications((current) => current && { ...current, days: current.days.map((day) => ({ ...day, items: day.items.map((item) => item.id === updated.id ? updated : item) })) });
        }} />
      </TabsContent>
      <TabsContent value="expedientes">

    <div className="mb-4 flex justify-start"><PdfExportButton path={`expedientes/export.pdf/?${new URLSearchParams({ scope: "history", date_from: appliedFrom, date_to: appliedTo })}`} count={data?.count} disabled={dateFrom !== appliedFrom || dateTo !== appliedTo} label="Exportar histórico de expedientes em PDF" analytical /></div>

    <ListLoading loading={historyLoading} error={historyError} />
    {!data && !historyError && <LoadingRows />}
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
