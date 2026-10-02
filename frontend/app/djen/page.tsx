"use client";

import { MagnifyingGlass, Newspaper } from "@phosphor-icons/react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AppShell } from "../components/app-shell";
import { DjenDrawer } from "../components/djen-drawer";
import { DjenList } from "../components/djen-list";
import { PdfExportButton } from "../components/pdf-export-button";
import { EmptyState, LoadingRows, PageTitle, Panel, Pagination } from "../components/ui";
import { api } from "../lib/api";
import { localCollectionDate } from "../lib/export";
import type { DjenCommunication, DjenCommunicationPage } from "../lib/types";

export default function DjenPage() {
  const [data, setData] = useState<DjenCommunicationPage | null>(null);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [dateFrom, setDateFrom] = useState(() => localCollectionDate());
  const [dateTo, setDateTo] = useState(() => localCollectionDate());
  const [appliedFrom, setAppliedFrom] = useState(() => localCollectionDate());
  const [appliedTo, setAppliedTo] = useState(() => localCollectionDate());
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<DjenCommunication | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), q: submitted, collected_from: appliedFrom, collected_to: appliedTo });
      setData(await api<DjenCommunicationPage>(`djen/communications/?${params}`)); setError("");
    }
    catch (exception) { setError(exception instanceof Error ? exception.message : "Não foi possível carregar as publicações."); }
  }, [page, submitted, appliedFrom, appliedTo]);
  useEffect(() => { queueMicrotask(() => { void load(); }); }, [load]);
  const search = (event: FormEvent) => {
    event.preventDefault();
    if (dateFrom > dateTo) { setError("A data inicial não pode ser posterior à data final."); return; }
    setData(null); setPage(1); setSubmitted(query.trim()); setAppliedFrom(dateFrom); setAppliedTo(dateTo);
  };
  const exportParams = new URLSearchParams({ q: submitted, collected_from: appliedFrom, collected_to: appliedTo });
  const updateRead = useCallback((updated: DjenCommunication) => {
    setSelected(updated); setData((current) => current ? { ...current, results: current.results.map((item) => item.id === updated.id ? updated : item) } : current);
  }, []);
  return <AppShell>
    <PageTitle title="Publicações DJEN" description="Comunicações do Diário de Justiça Eletrônico Nacional localizadas pela OAB configurada." />
    <form onSubmit={search} className="mb-6 grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_auto_auto_auto]" role="search">
      <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Processo, parte, advogado ou trecho da publicação" aria-label="Pesquisar publicações DJEN" />
      <label className="flex items-center gap-2 text-xs font-semibold">Coleta de <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} aria-label="Coleta de" required /></label>
      <label className="flex items-center gap-2 text-xs font-semibold">Até <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} aria-label="Coleta até" required /></label>
      <Button type="submit"><MagnifyingGlass />Pesquisar</Button>
    </form>
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground"><PdfExportButton path={`djen/communications/export.pdf/?${exportParams}`} count={data?.count} disabled={dateFrom !== appliedFrom || dateTo !== appliedTo || query.trim() !== submitted} label="Exportar publicações em PDF" /><div className="flex flex-wrap items-center gap-2"><span>{data ? `${data.count} publicação${data.count === 1 ? "" : "ões"}` : "Carregando publicações…"}</span>{submitted && <Button variant="ghost" size="sm" onClick={() => { setData(null); setQuery(""); setSubmitted(""); setPage(1); }}>Limpar busca</Button>}</div></div>
    {error && <Panel innerClassName="p-6 text-sm font-semibold text-destructive">{error}</Panel>}
    {!data && !error && <LoadingRows />}
    <div>
      {data && <DjenList items={data.results} onSelect={setSelected} />}
      {data?.results.length === 0 && <EmptyState icon={<Newspaper size={26} weight="duotone" />} title="Nenhuma publicação encontrada" description="A consulta diária pode não ter comunicações para os filtros atuais." />}
    </div>
    {data && <Pagination page={page} pages={Math.ceil(data.count / 20)} onPageChange={setPage} label="Paginação de publicações DJEN" />}
    <DjenDrawer item={selected} onClose={() => setSelected(null)} onRead={updateRead} />
  </AppShell>;
}
