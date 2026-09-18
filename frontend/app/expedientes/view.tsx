"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AppShell } from "../components/app-shell";
import { ExpedienteDrawer } from "../components/expediente-drawer";
import { ExpedienteList } from "../components/expediente-list";
import { Icon } from "../components/icons";
import { api } from "../lib/api";
import type { Expediente } from "../lib/types";

type PageData = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Expediente[];
};

export function ExpedientesClient() {
  const search = useSearchParams();
  const router = useRouter();
  const [data, setData] = useState<PageData | null>(null);
  const [selected, setSelected] = useState<Expediente | null>(null);
  const [error, setError] = useState("");

  const query = search.toString();
  const load = useCallback(async () => {
    try {
      setData(await api<PageData>(`expedientes/?${query}`));
      setError("");
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Falha ao carregar.");
    }
  }, [query]);

  useEffect(() => {
    queueMicrotask(() => {
      void load();
    });
  }, [load]);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const params = new URLSearchParams();

    for (const [key, value] of form.entries()) {
      if (value) params.set(key, String(value));
    }
    router.replace(`/expedientes?${params}`);
  };

  const page = Number(search.get("page") ?? 1);
  const pages = Math.max(1, Math.ceil((data?.count ?? 0) / 25));
  const go = (nextPage: number) => {
    const params = new URLSearchParams(search);
    params.set("page", String(nextPage));
    router.replace(`/expedientes?${params}`);
  };

  return (
    <AppShell>
      <div className="mx-auto w-[min(1240px,calc(100%-48px))] py-8 pb-[70px] max-[760px]:w-[calc(100%-28px)] max-[760px]:pt-6 max-[760px]:pb-12">
        <header className="mb-[26px] flex items-end justify-between gap-6 max-[760px]:mb-[22px] max-[760px]:items-start">
          <div>
            <h1 className="mb-[7px] text-[clamp(25px,3vw,34px)] leading-[1.15] font-bold max-[760px]:text-[29px]">Expedientes</h1>
          </div>
        </header>

        <form className="mb-4 overflow-hidden rounded-[10px] border border-line bg-surface shadow-[0_2px_8px_var(--panel-shadow)]" onSubmit={submit}>
          <div className="flex items-center justify-between gap-3 border-b border-line bg-surface-raised px-3.5 py-2.5">
            <div className="flex items-baseline gap-2">
              <strong className="text-[15px] font-[650] text-text">Filtros</strong>
            </div>
          </div>
          <div className="grid grid-cols-[minmax(220px,1.7fr)_repeat(4,minmax(125px,1fr))_auto] gap-2.5 p-3.5 max-[1100px]:grid-cols-3 max-[760px]:grid-cols-2 max-[420px]:grid-cols-1">
          <label className="relative min-w-0 max-[1100px]:col-span-2 max-[760px]:col-span-2 max-[420px]:col-span-1">
            <span className="pointer-events-none absolute top-1/2 left-2.5 flex -translate-y-1/2 text-muted">
              <Icon name="search" size={18} />
            </span>
            <input className="w-full min-h-10 rounded-[7px] border border-line bg-surface-raised py-2.5 pr-3 pl-[36px] text-[12px] text-text outline-0 transition-[border-color,box-shadow,background-color] duration-[160ms] placeholder:text-muted hover:border-line-strong focus:border-accent focus:bg-surface focus:shadow-[0_0_0_3px_var(--color-accent-soft)]" name="q" defaultValue={search.get("q") ?? ""} placeholder="Processo, partes ou assunto" aria-label="Buscar expedientes" />
          </label>
          <select className="min-h-10 w-full rounded-[7px] border border-line bg-surface-raised px-3 py-2.5 text-[12px] text-text outline-0 transition-[border-color,box-shadow,background-color] duration-[160ms] hover:border-line-strong focus:border-accent focus:bg-surface focus:shadow-[0_0_0_3px_var(--color-accent-soft)]" name="source" defaultValue={search.get("source") ?? ""} aria-label="Fonte">
            <option value="">Todas as fontes</option>
            <option value="pje-tjrn">PJe 1º Grau · TJRN</option>
            <option value="pje2g-tjrn">PJe 2º Grau · TJRN</option>
          </select>
          <select className="min-h-10 w-full rounded-[7px] border border-line bg-surface-raised px-3 py-2.5 text-[12px] text-text outline-0 transition-[border-color,box-shadow,background-color] duration-[160ms] hover:border-line-strong focus:border-accent focus:bg-surface focus:shadow-[0_0_0_3px_var(--color-accent-soft)]" name="pending_type" defaultValue={search.get("pending_type") ?? ""} aria-label="Pendência">
            <option value="">Todas as pendências</option>
            <option value="ciencia">Ciência</option>
            <option value="resposta">Resposta</option>
            <option value="nao_identificada">Não identificada</option>
          </select>
          <select className="min-h-10 w-full rounded-[7px] border border-line bg-surface-raised px-3 py-2.5 text-[12px] text-text outline-0 transition-[border-color,box-shadow,background-color] duration-[160ms] hover:border-line-strong focus:border-accent focus:bg-surface focus:shadow-[0_0_0_3px_var(--color-accent-soft)]" name="deadline" defaultValue={search.get("deadline") ?? ""} aria-label="Prazo">
            <option value="">Todos os prazos</option>
            <option value="urgent">Urgentes</option>
            <option value="overdue">Vencidos</option>
            <option value="future">Futuros</option>
            <option value="calculating">Em cálculo</option>
            <option value="none">Sem prazo</option>
            <option value="resolved">Resolvidos</option>
          </select>
          <select className="min-h-10 w-full rounded-[7px] border border-line bg-surface-raised px-3 py-2.5 text-[12px] text-text outline-0 transition-[border-color,box-shadow,background-color] duration-[160ms] hover:border-line-strong focus:border-accent focus:bg-surface focus:shadow-[0_0_0_3px_var(--color-accent-soft)]" name="read" defaultValue={search.get("read") ?? ""} aria-label="Leitura">
            <option value="">Lidos e não lidos</option>
            <option value="unread">Não lidos</option>
            <option value="read">Lidos</option>
          </select>
          <input className="min-h-10 w-full rounded-[7px] border border-line bg-surface-raised px-3 py-2.5 text-[12px] text-text outline-0 transition-[border-color,box-shadow,background-color] duration-[160ms] hover:border-line-strong focus:border-accent focus:bg-surface focus:shadow-[0_0_0_3px_var(--color-accent-soft)]" name="date_from" type="date" defaultValue={search.get("date_from") ?? ""} aria-label="Eventos a partir de" />
          <input className="min-h-10 w-full rounded-[7px] border border-line bg-surface-raised px-3 py-2.5 text-[12px] text-text outline-0 transition-[border-color,box-shadow,background-color] duration-[160ms] hover:border-line-strong focus:border-accent focus:bg-surface focus:shadow-[0_0_0_3px_var(--color-accent-soft)]" name="date_to" type="date" defaultValue={search.get("date_to") ?? ""} aria-label="Eventos até" />
          <select className="min-h-10 w-full rounded-[7px] border border-line bg-surface-raised px-3 py-2.5 text-[12px] text-text outline-0 transition-[border-color,box-shadow,background-color] duration-[160ms] hover:border-line-strong focus:border-accent focus:bg-surface focus:shadow-[0_0_0_3px_var(--color-accent-soft)]" name="ordering" defaultValue={search.get("ordering") ?? "recent"} aria-label="Ordenação">
            <option value="recent">Mais recentes</option>
            <option value="deadline">Prazo mais próximo</option>
            <option value="expedition">Expedição recente</option>
            <option value="process">Número do processo</option>
          </select>
          <button className="min-h-10 cursor-pointer rounded-[7px] border border-primary-bg bg-primary-bg px-4 py-2.5 text-[12px] font-bold text-primary-text shadow-[0_1px_2px_var(--panel-shadow)] transition-[background-color,border-color,color,opacity,transform] duration-[160ms] hover:bg-primary-hover hover:-translate-y-px max-[760px]:col-span-2 max-[420px]:col-span-1">Aplicar filtros</button>
          </div>
        </form>

        {query && (
          <button className="mb-3 cursor-pointer border-0 bg-transparent text-[11px] font-[650] text-accent" onClick={() => router.replace("/expedientes")}>
            Limpar todos os filtros ×
          </button>
        )}
        {error && (
          <div className="mb-[14px] flex items-center justify-between gap-[18px] rounded-[7px] border border-l-[3px] border-line border-l-red bg-surface px-[14px] py-3">
            <span className="text-[12px] text-muted">{error}</span>
            <button className="flex min-w-[150px] cursor-pointer items-center justify-center gap-1.5 whitespace-nowrap rounded-md border border-line bg-surface-raised px-[9px] py-[7px] text-[12px] font-[650] text-text hover:border-line-strong hover:bg-surface-hover" onClick={load}>Tentar novamente</button>
          </div>
        )}
        {data ? (
          <ExpedienteList items={data.results} onSelect={setSelected} />
        ) : (
          <div className="grid gap-px">
            <i className="h-[91px] animate-[shimmer_1.5s_infinite] bg-[linear-gradient(90deg,var(--surface),var(--surface-raised),var(--surface))] bg-[length:200%]" />
            <i className="h-[91px] animate-[shimmer_1.5s_infinite] bg-[linear-gradient(90deg,var(--surface),var(--surface-raised),var(--surface))] bg-[length:200%]" />
            <i className="h-[91px] animate-[shimmer_1.5s_infinite] bg-[linear-gradient(90deg,var(--surface),var(--surface-raised),var(--surface))] bg-[length:200%]" />
          </div>
        )}

        {data && pages > 1 && (
          <nav className="mt-[22px] flex items-center justify-center gap-[18px] text-[12px] text-muted" aria-label="Paginação">
            <button className="cursor-pointer rounded-[5px] border border-line bg-surface px-2.5 py-[7px] hover:bg-surface-hover disabled:cursor-default disabled:opacity-35" disabled={page <= 1} onClick={() => go(page - 1)}>
              ← Anterior
            </button>
            <span>
              Página <strong>{page}</strong> de {pages}
            </span>
            <button className="cursor-pointer rounded-[5px] border border-line bg-surface px-2.5 py-[7px] hover:bg-surface-hover disabled:cursor-default disabled:opacity-35" disabled={page >= pages} onClick={() => go(page + 1)}>
              Próxima →
            </button>
          </nav>
        )}
      </div>
      <ExpedienteDrawer
        item={selected}
        onClose={() => setSelected(null)}
        onRead={() => {
          if (selected) setSelected({ ...selected, unread: false });
          load();
        }}
      />
    </AppShell>
  );
}
