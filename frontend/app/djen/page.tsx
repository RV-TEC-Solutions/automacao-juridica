"use client";

import { MagnifyingGlass, Newspaper } from "@phosphor-icons/react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AppShell } from "../components/app-shell";
import { DjenDrawer } from "../components/djen-drawer";
import { DjenList } from "../components/djen-list";
import { EmptyState, LoadingRows, PageTitle, Panel, Pagination } from "../components/ui";
import { api } from "../lib/api";
import type { DjenCommunication, DjenCommunicationPage } from "../lib/types";

export default function DjenPage() {
  const [data, setData] = useState<DjenCommunicationPage | null>(null);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<DjenCommunication | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try { setData(await api<DjenCommunicationPage>(`djen/communications/?page=${page}&q=${encodeURIComponent(submitted)}`)); setError(""); }
    catch (exception) { setError(exception instanceof Error ? exception.message : "Não foi possível carregar as publicações."); }
  }, [page, submitted]);
  useEffect(() => { queueMicrotask(() => { void load(); }); }, [load]);
  const search = (event: FormEvent) => { event.preventDefault(); setPage(1); setSubmitted(query.trim()); };
  const updateRead = useCallback((updated: DjenCommunication) => {
    setSelected(updated); setData((current) => current ? { ...current, results: current.results.map((item) => item.id === updated.id ? updated : item) } : current);
  }, []);
  return <AppShell>
    <PageTitle title="Publicações DJEN" description="Comunicações do Diário de Justiça Eletrônico Nacional localizadas pela OAB configurada." />
    <form onSubmit={search} className="mb-6 flex max-w-3xl gap-2" role="search">
      <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Processo, parte, advogado ou trecho da publicação" aria-label="Pesquisar publicações DJEN" />
      <Button type="submit"><MagnifyingGlass />Pesquisar</Button>
    </form>
    <div className="mb-4 flex items-center justify-between text-sm text-muted-foreground"><span>{data ? `${data.count} publicação${data.count === 1 ? "" : "ões"}` : "Carregando publicações…"}</span>{submitted && <Button variant="ghost" size="sm" onClick={() => { setQuery(""); setSubmitted(""); setPage(1); }}>Limpar busca</Button>}</div>
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
