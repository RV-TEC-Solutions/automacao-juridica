"use client";

import { ArrowLeft, ArrowRight, MagnifyingGlass, Newspaper } from "@phosphor-icons/react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AppShell } from "../components/app-shell";
import { DjenDrawer } from "../components/djen-drawer";
import { LoadingRows, PageTitle, Panel } from "../components/ui";
import { api } from "../lib/api";
import type { DjenCommunication, DjenCommunicationPage } from "../lib/types";

const date = (value: string) => new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));

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
    <div className="space-y-3">
      {data?.results.map((item) => <button key={item.id} type="button" onClick={() => setSelected(item)} className="block w-full rounded-xl border bg-card p-5 text-left transition-colors hover:bg-muted/45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0"><div className="mb-2 flex flex-wrap items-center gap-2"><span className="rounded-md border bg-muted px-2 py-1 text-xs font-extrabold">{item.tribunal}</span>{item.unread && <span className="rounded-full bg-warning-soft px-2 py-1 text-xs font-extrabold text-warning">NOVA</span>}<span className="text-xs font-semibold text-muted-foreground">{date(item.data_disponibilizacao)}</span></div><h2 className="truncate font-mono text-sm font-extrabold sm:text-base">{item.processo.numero}</h2><p className="mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">{item.texto || item.tipo_comunicacao}</p></div><div className="shrink-0 text-left sm:text-right"><strong className="block text-sm">{item.tipo_comunicacao || "Comunicação"}</strong><span className="mt-1 block max-w-64 truncate text-xs text-muted-foreground">{item.orgao}</span></div></div>
      </button>)}
      {data?.results.length === 0 && <Panel innerClassName="grid place-items-center gap-3 p-10 text-center"><Newspaper size={32} className="text-muted-foreground" /><strong>Nenhuma publicação encontrada</strong><span className="text-sm text-muted-foreground">A consulta diária pode não ter comunicações para os filtros atuais.</span></Panel>}
    </div>
    {data && (data.previous || data.next) && <div className="mt-6 flex justify-end gap-2"><Button variant="outline" disabled={!data.previous} onClick={() => setPage((value) => value - 1)}><ArrowLeft />Anterior</Button><Button variant="outline" disabled={!data.next} onClick={() => setPage((value) => value + 1)}>Próxima<ArrowRight /></Button></div>}
    <DjenDrawer item={selected} onClose={() => setSelected(null)} onRead={updateRead} />
  </AppShell>;
}
