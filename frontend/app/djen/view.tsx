"use client";

import { ArrowClockwise, CaretDown, FunnelSimple, MagnifyingGlass, Newspaper } from "@phosphor-icons/react";
import { type FormEvent, type ReactNode, useCallback, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MultiSelect } from "@/components/ui/multi-select";
import { Select } from "@/components/ui/select";
import { AppShell } from "../components/app-shell";
import { DjenDrawer } from "../components/djen-drawer";
import { DjenList } from "../components/djen-list";
import { PdfExportButton } from "../components/pdf-export-button";
import { EmptyState, LoadingRows, PageTitle, Pagination } from "../components/ui";
import { useLiveList } from "../hooks/use-live-list";
import { localCollectionDate } from "../lib/export";
import type { DjenCommunication, DjenCommunicationPage } from "../lib/types";

const UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split(" ");

type FilterOptions = { clientes: { id: number; nome: string }[]; tribunais: string[]; tipos_comunicacao: string[] };
function Field({ label, children }: { label: string; children: ReactNode }) {
  return <div className="space-y-2"><Label className="text-xs uppercase tracking-wide">{label}</Label>{children}</div>;
}

export function DjenClient() {
  const search = useSearchParams();
  const router = useRouter();
  const [today] = useState(localCollectionDate);
  const [dirty, setDirty] = useState(false);
  const [reset, setReset] = useState(0);
  const [selected, setSelected] = useState<DjenCommunication | null>(null);
  const query = search.toString();
  const applied = new URLSearchParams(search);
  if (!applied.has("collected_from")) applied.set("collected_from", today);
  if (!applied.has("collected_to")) applied.set("collected_to", today);
  const { data, setData, loading, error, reload } = useLiveList<DjenCommunicationPage>(`djen/communications/?${applied}`);
  const { data: options, loading: optionsLoading, error: optionsError, reload: reloadOptions } = useLiveList<FilterOptions>("djen/filters/");
  const page = Math.max(1, Number(search.get("page") ?? 1) || 1);
  const go = (next: number) => { const params = new URLSearchParams(applied); params.set("page", String(next)); router.replace(`/djen?${params}`); };
  const clear = () => { setDirty(false); setReset((value) => value + 1); router.replace("/djen?collected_from=&collected_to="); };
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const params = new URLSearchParams();
    for (const [key, value] of new FormData(event.currentTarget)) {
      if (value || key === "collected_from" || key === "collected_to") params.append(key, String(value));
    }
    setDirty(false);
    if (params.toString() === applied.toString()) void reload();
    router.replace(`/djen?${params}`);
  };
  const exportParams = new URLSearchParams(applied);
  exportParams.delete("page");
  const updateRead = useCallback((updated: DjenCommunication) => {
    setSelected(updated);
    // A leitura pode retirar o item de um filtro de não lidas.
    setData((current) => current ? { ...current, results: current.results.map((item) => item.id === updated.id ? updated : item) } : current);
    void reload();
  }, [setData, reload]);

  return <AppShell>
    <PageTitle title="Publicações DJEN" description="Comunicações do Diário de Justiça Eletrônico Nacional localizadas pela OAB configurada." actions={<Button variant="outline" disabled={loading} onClick={() => void reload()}><ArrowClockwise aria-hidden="true" className={loading ? "motion-safe:animate-spin" : ""} />{loading ? "Atualizando…" : "Atualizar"}</Button>} />
    <form key={`${query}:${reset}`} onSubmit={submit} role="search" className="mb-6 overflow-hidden rounded-lg border bg-card shadow-sm" onInput={(event) => {
      setDirty(true);
      for (const [from, to] of [["collected_from", "collected_to"], ["date_from", "date_to"]]) {
        const first = event.currentTarget.elements.namedItem(from) as HTMLInputElement;
        const last = event.currentTarget.elements.namedItem(to) as HTMLInputElement;
        last.setCustomValidity(first.value && last.value && first.value > last.value ? "A data final deve ser igual ou posterior à inicial." : "");
      }
    }}>
      <div className="flex flex-col gap-4 border-b bg-muted/50 p-4 sm:flex-row">
        <div className="relative flex-1"><MagnifyingGlass size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" /><Input name="q" defaultValue={search.get("q") ?? ""} placeholder="Processo, parte, advogado ou trecho da publicação" aria-label="Pesquisar publicações DJEN" className="pl-10" /></div>
        <Button type="submit"><MagnifyingGlass />Buscar</Button>
      </div>
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between px-6 py-4 text-sm font-semibold hover:bg-muted/50">
          <span className="flex items-center gap-2"><FunnelSimple size={18} />Filtros avançados{query && <span className="rounded-full bg-muted px-2 py-2 text-xs">ativos</span>}</span>
          <CaretDown className="transition-transform group-open:rotate-180" />
        </summary>
        <div className="grid gap-4 border-t p-6 sm:grid-cols-2 lg:grid-cols-4">
          {optionsError && <div role="alert" className="flex flex-wrap items-center gap-3 text-sm sm:col-span-2 lg:col-span-4"><span>Não foi possível atualizar as opções dos filtros.</span><Button type="button" variant="outline" size="sm" onClick={() => void reloadOptions()}>Tentar novamente</Button></div>}
          {optionsLoading && !options && <p role="status" className="text-sm text-muted-foreground sm:col-span-2 lg:col-span-4">Carregando filtros…</p>}
          <div className="sm:col-span-2"><MultiSelect name="tribunal" label="Tribunais" options={(options?.tribunais ?? []).map((value) => ({ value, label: value }))} initialSelection={search.getAll("tribunal")} onDirty={() => setDirty(true)} placeholder="Todos os tribunais" searchLabel="Buscar tribunal" emptyMessage="Nenhum tribunal coletado até o momento." /></div>
          <div className="sm:col-span-2"><MultiSelect name="client" label="Clientes" options={(options?.clientes ?? []).map((client) => ({ value: String(client.id), label: client.nome }))} initialSelection={search.getAll("client")} onDirty={() => setDirty(true)} placeholder="Todos os clientes" searchLabel="Buscar cliente pelo nome" emptyMessage="Nenhum destinatário coletado até o momento." /></div>
          <p className="text-xs text-muted-foreground sm:col-span-2 lg:col-span-4">No DJEN, o filtro de clientes considera os destinatários informados na publicação. Ao selecionar vários, inclui publicações de qualquer um deles.</p>
          <div className="sm:col-span-2"><MultiSelect name="uf" label="Unidade federativa (UF)" options={UFS.map((value) => ({ value, label: value }))} initialSelection={search.getAll("uf")} onDirty={() => setDirty(true)} placeholder="Todas as UFs" searchLabel="Buscar UF" emptyMessage="Nenhuma UF encontrada." /></div>
          <p className="text-xs text-muted-foreground sm:col-span-2">Filtra pela UF do tribunal ou pela origem do processo. Tribunais regionais com vários estados exigem origem identificável; publicações sem UF identificável ficam fora desse filtro.</p>
          <Field label="Tipo de comunicação"><Select name="tipo_comunicacao" defaultValue={search.get("tipo_comunicacao") ?? ""} aria-label="Tipo de comunicação"><option value="">Todos os tipos</option>{[...new Set([...(options?.tipos_comunicacao ?? []), ...(search.get("tipo_comunicacao") ? [search.get("tipo_comunicacao")!] : [])])].map((kind) => <option key={kind}>{kind}</option>)}</Select></Field>
          <Field label="Situação de leitura"><Select name="read" defaultValue={search.get("read") ?? ""} aria-label="Situação de leitura"><option value="">Lidas e não lidas</option><option value="unread">Não lidas</option><option value="read">Lidas</option></Select></Field>
          <Field label="Coleta a partir de"><Input name="collected_from" type="date" defaultValue={applied.get("collected_from") ?? ""} aria-label="Coleta a partir de" /></Field>
          <Field label="Coleta até"><Input name="collected_to" type="date" defaultValue={applied.get("collected_to") ?? ""} aria-label="Coleta até" /></Field>
          <Field label="Disponibilização a partir de"><Input name="date_from" type="date" defaultValue={search.get("date_from") ?? ""} aria-label="Disponibilização a partir de" /></Field>
          <Field label="Disponibilização até"><Input name="date_to" type="date" defaultValue={search.get("date_to") ?? ""} aria-label="Disponibilização até" /></Field>
          <Field label="Ordenação"><Select name="ordering" defaultValue={search.get("ordering") ?? "recent"} aria-label="Ordenação"><option value="recent">Coleta mais recente</option><option value="publication">Disponibilização mais recente</option><option value="oldest">Disponibilização mais antiga</option><option value="process">Número do processo</option></Select></Field>
          <div className="flex items-end"><Button type="button" variant="outline" className="w-full" onClick={clear}>Limpar filtros</Button></div>
        </div>
      </details>
    </form>
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground"><PdfExportButton path={`djen/communications/export.pdf/?${exportParams}`} count={data?.count} disabled={dirty || loading || !data} label="Exportar publicações em PDF" /><span>{data ? `${data.count} ${data.count === 1 ? "publicação" : "publicações"}` : "Carregando publicações…"}</span></div>
    {loading && <div role="status" className="mb-4 overflow-hidden rounded-lg border border-primary/20 bg-primary/5">
      <div className="flex items-center gap-3 p-4">
        <ArrowClockwise size={22} aria-hidden="true" className="shrink-0 text-primary motion-safe:animate-spin" />
        <div><p className="text-sm font-semibold">{data ? "Atualizando publicações DJEN…" : "Carregando publicações DJEN…"}</p><p className="mt-1 text-xs text-muted-foreground">{data ? "A lista atual permanece disponível enquanto buscamos as atualizações." : "Buscando publicações para o período selecionado. Aguarde a conclusão da consulta."}</p></div>
      </div>
      <div role="progressbar" aria-label="Carregamento de publicações DJEN" className="h-1 bg-primary/10"><div className="h-full w-full bg-primary/60 motion-safe:animate-pulse" /></div>
    </div>}
    {error && <div role="alert" className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm"><span className="text-destructive">{error}</span><Button variant="outline" size="sm" disabled={loading} onClick={() => void reload()}>Tentar novamente</Button></div>}
    <section aria-label="Publicações DJEN" aria-busy={loading}>
    {!data && !error && <LoadingRows />}
    {data && <DjenList items={data.results} onSelect={setSelected} />}
    {data?.results.length === 0 && <EmptyState icon={<Newspaper size={26} weight="duotone" />} title="Nenhuma publicação encontrada" description="Nenhuma comunicação corresponde aos filtros atuais." />}
    {data && <Pagination page={page} pages={Math.max(1, Math.ceil(data.count / 20))} onPageChange={go} label="Paginação de publicações DJEN" />}
    </section>
    <DjenDrawer item={selected} onClose={() => setSelected(null)} onRead={updateRead} />
  </AppShell>;
}
