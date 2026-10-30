"use client";

import { CaretDown, FunnelSimple, MagnifyingGlass, X } from "@phosphor-icons/react";
import { type FormEvent, type ReactNode, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MultiSelect } from "@/components/ui/multi-select";
import { getCollectionSourceOptions } from "../lib/collection-sites";
import { Select } from "@/components/ui/select";
import { AppShell } from "../components/app-shell";
import { AttorneySelect } from "../components/attorney-select";
import { ClientFilter } from "../components/client-filter";
import { ExpedienteDrawer } from "../components/expediente-drawer";
import { ExpedienteList } from "../components/expediente-list";
import { PdfExportButton } from "../components/pdf-export-button";
import { ListLoading, LoadingRows, PageTitle, Pagination } from "../components/ui";
import { useLiveList } from "../hooks/use-live-list";
import type { Expediente } from "../lib/types";

type PageData = { count: number; next: string | null; previous: string | null; results: Expediente[] };

function FilterField({ label, children }: { label: string; children: ReactNode }) {
  return <div className="space-y-2"><Label className="text-xs uppercase tracking-wide">{label}</Label>{children}</div>;
}

export function ExpedientesClient() {
  const search = useSearchParams();
  const router = useRouter();
  const [selected, setSelected] = useState<Expediente | null>(null);
  const [filtersDirty, setFiltersDirty] = useState(false);
  const [resetVersion, setResetVersion] = useState(0);
  const query = search.toString();

  const { data, reload: load, loading, error } = useLiveList<PageData>("expedientes/?" + query);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const params = new URLSearchParams();
    for (const [key, value] of new FormData(event.currentTarget).entries()) if (value) params.append(key, String(value));
    setFiltersDirty(false);
    if (params.toString() === query) void load();
    router.replace(`/expedientes?${params}`);
  };

  const page = Math.max(1, Number(search.get("page") ?? 1) || 1);
  const pages = Math.max(1, Math.ceil((data?.count ?? 0) / 25));
  const go = (nextPage: number) => { const params = new URLSearchParams(search); params.set("page", String(nextPage)); router.replace(`/expedientes?${params}`); };
  const clear = () => { setFiltersDirty(false); setResetVersion((value) => value + 1); if (!query) void load(); router.replace("/expedientes"); };
  const exportParams = new URLSearchParams(search);
  exportParams.delete("page");
  exportParams.delete("page_size");

  return <AppShell>
    <PageTitle title="Expedientes" description="Pesquise, filtre e audite intimações e expedientes capturados nas instâncias conectadas do PJe." />

    <form key={`${query}:${resetVersion}`} className="mb-6 overflow-hidden rounded-lg border bg-card shadow-sm" onSubmit={submit} onInput={(event) => {
      setFiltersDirty(true);
      const form = event.currentTarget;
      const first = form.elements.namedItem("deadline_from") as HTMLInputElement;
      const last = form.elements.namedItem("deadline_to") as HTMLInputElement;
      last.setCustomValidity(first.value && last.value && first.value > last.value ? "A data final do prazo deve ser igual ou posterior à data inicial." : "");
    }}>
      <div className="flex flex-col gap-4 border-b bg-muted/50 p-4 sm:flex-row">
        <div className="relative flex-1"><MagnifyingGlass size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" /><Input name="q" defaultValue={search.get("q") ?? ""} placeholder="Número do processo, partes ou assunto" aria-label="Buscar expedientes" className="pl-10" /></div>
        <Button type="submit"><MagnifyingGlass />Buscar</Button>
      </div>

      <details className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between px-6 py-4 text-sm font-semibold hover:bg-muted/50">
          <span className="flex items-center gap-2"><FunnelSimple size={18} />Filtros avançados{query && <span className="rounded-full bg-muted px-2 py-2 text-xs">ativos</span>}</span>
          <CaretDown className="transition-transform group-open:rotate-180" />
        </summary>
        <div className="grid gap-4 border-t p-6 sm:grid-cols-2 lg:grid-cols-4">
          <div className="sm:col-span-2"><MultiSelect name="source" label="Fontes" options={getCollectionSourceOptions()} initialSelection={search.getAll("source")} onDirty={() => setFiltersDirty(true)} placeholder="Todas as fontes" searchLabel="Buscar fonte ou tribunal" emptyMessage="Nenhuma fonte disponível." /></div>
          <div className="sm:col-span-2"><ClientFilter initialSelection={search.getAll("client")} onDirty={() => setFiltersDirty(true)} /></div>
          <FilterField label="Por advogado"><AttorneySelect defaultValue={search.get("attorney") ?? ""} onChange={() => setFiltersDirty(true)} /></FilterField>
          <FilterField label="Pendência"><Select name="pending_type" defaultValue={search.get("pending_type") ?? ""} aria-label="Pendência"><option value="">Todas as pendências</option><option value="ciencia">Ciência</option><option value="resposta">Resposta</option><option value="nao_identificada">Não identificada</option></Select></FilterField>
          <FilterField label="Prazo"><Select name="deadline" defaultValue={search.get("deadline") ?? ""} aria-label="Prazo"><option value="">Todos os prazos</option><option value="urgent">Urgentes</option><option value="overdue">Vencidos</option><option value="future">Futuros</option><option value="next_week">Até o fim da próxima semana</option><option value="calculating">Em cálculo</option><option value="none">Sem prazo</option><option value="resolved">Resolvidos</option></Select></FilterField>
          <FilterField label="Situação de leitura"><Select name="read" defaultValue={search.get("read") ?? ""} aria-label="Leitura"><option value="">Lidos e não lidos</option><option value="unread">Não lidos</option><option value="read">Lidos</option></Select></FilterField>
          <FilterField label="Coleta a partir de"><Input name="date_from" type="date" defaultValue={search.get("date_from") ?? ""} aria-label="Coleta a partir de" /></FilterField>
          <FilterField label="Coleta até"><Input name="date_to" type="date" defaultValue={search.get("date_to") ?? ""} aria-label="Coleta até" /></FilterField>
          <FilterField label="Data inicial do prazo"><Input name="deadline_from" type="date" defaultValue={search.get("deadline_from") ?? ""} aria-label="Data inicial do prazo" /></FilterField>
          <FilterField label="Data final do prazo"><Input name="deadline_to" type="date" defaultValue={search.get("deadline_to") ?? ""} aria-label="Data final do prazo" /></FilterField>
          <FilterField label="Ordenação"><Select name="ordering" defaultValue={search.get("ordering") ?? "recent"} aria-label="Ordenação"><option value="recent">Mais recentes</option><option value="deadline">Prazo fatal mais próximo</option><option value="expedition">Expedição recente</option><option value="process">Número do processo</option></Select></FilterField>
          <div className="flex items-end"><Button type="button" variant="outline" className="w-full" onClick={clear}>Limpar filtros</Button></div>
        </div>
      </details>
    </form>


    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground"><PdfExportButton path={`expedientes/export.pdf/?${exportParams}`} count={data?.count} disabled={filtersDirty} label="Exportar expedientes em PDF" analytical /><div className="flex flex-wrap items-center gap-2"><span>{data ? `${data.count} expediente${data.count === 1 ? "" : "s"} encontrado${data.count === 1 ? "" : "s"}` : "Carregando consulta operacional…"}</span>{query && <Button variant="ghost" size="sm" onClick={clear}><X />Limpar filtros</Button>}</div></div>
    <ListLoading loading={loading} error={error} />
    {data ? <ExpedienteList items={data.results} onSelect={setSelected} /> : !error && <LoadingRows />}
    <Pagination page={page} pages={pages} onPageChange={go} />
    <ExpedienteDrawer item={selected} onClose={() => setSelected(null)} onRead={() => { if (selected) setSelected({ ...selected, unread: false }); void load(); }} />
  </AppShell>;
}
