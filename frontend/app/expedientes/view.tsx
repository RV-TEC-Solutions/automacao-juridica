"use client";

import { CaretDown, FunnelSimple, MagnifyingGlass, X } from "@phosphor-icons/react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "../components/app-shell";
import { ExpedienteDrawer } from "../components/expediente-drawer";
import { ExpedienteList } from "../components/expediente-list";
import { Feedback, LoadingRows, PageTitle } from "../components/ui";
import { api } from "../lib/api";
import type { Expediente } from "../lib/types";

type PageData = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Expediente[];
};

const selectClass =
  "control w-full px-3 py-2 text-xs font-semibold";

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
      <PageTitle
        eyebrow="Consulta operacional"
        title="Expedientes"
        description="Pesquise, filtre e audite intimações e expedientes capturados nas instâncias conectadas do PJe."
      />

      <form className="bezel-card mb-6" onSubmit={submit}>
        <div className="bezel-inner overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-rule bg-panel-muted/60 p-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <MagnifyingGlass
                size={18}
                className="absolute top-1/2 left-3.5 -translate-y-1/2 text-quiet"
              />
              <input
                className="control w-full py-2.5 pr-3 pl-10 text-xs sm:text-sm font-medium"
                name="q"
                defaultValue={search.get("q") ?? ""}
                placeholder="Número do processo, partes ou assunto"
                aria-label="Buscar expedientes"
              />
            </div>
            <button
              type="submit"
              className="button-primary cursor-pointer px-5 py-2.5 text-xs sm:text-sm font-bold shadow-xs shrink-0"
            >
              <MagnifyingGlass size={16} weight="bold" />
              Buscar
            </button>
          </div>

          <details className="group">
            <summary className="flex cursor-pointer list-none items-center justify-between px-5 py-3.5 text-xs font-extrabold text-ink transition-colors hover:bg-panel-muted/50">
              <span className="flex items-center gap-2.5">
                <FunnelSimple size={17} className="text-ink-soft" weight="duotone" />
                <span>Filtros avançados</span>
                {query && (
                  <span className="rounded-full border border-zinc-300 dark:border-zinc-700 bg-panel-muted px-2 py-0.5 text-[10px] font-extrabold text-ink">
                    ativos
                  </span>
                )}
              </span>
              <CaretDown
                size={16}
                weight="bold"
                className="text-quiet transition-transform duration-200 group-open:rotate-180"
              />
            </summary>

            <div className="grid grid-cols-1 gap-3.5 border-t border-rule p-5 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="text-[10px] font-extrabold uppercase tracking-wider text-quiet block mb-1">
                  Fonte
                </label>
                <select
                  className={selectClass}
                  name="source"
                  defaultValue={search.get("source") ?? ""}
                  aria-label="Fonte"
                >
                  <option value="">Todas as fontes</option>
                  <option value="pje-tjrn">PJe 1º Grau · TJRN</option>
                  <option value="pje2g-tjrn">PJe 2º Grau · TJRN</option>
                  <option value="trt21">PJe 1º Grau · TRT21</option>
                  <option value="trt21-2g">PJe 2º Grau · TRT21</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-extrabold uppercase tracking-wider text-quiet block mb-1">
                  Pendência
                </label>
                <select
                  className={selectClass}
                  name="pending_type"
                  defaultValue={search.get("pending_type") ?? ""}
                  aria-label="Pendência"
                >
                  <option value="">Todas as pendências</option>
                  <option value="ciencia">Ciência</option>
                  <option value="resposta">Resposta</option>
                  <option value="nao_identificada">Não identificada</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-extrabold uppercase tracking-wider text-quiet block mb-1">
                  Prazo
                </label>
                <select
                  className={selectClass}
                  name="deadline"
                  defaultValue={search.get("deadline") ?? ""}
                  aria-label="Prazo"
                >
                  <option value="">Todos os prazos</option>
                  <option value="urgent">Urgentes</option>
                  <option value="overdue">Vencidos</option>
                  <option value="future">Futuros</option>
                  <option value="calculating">Em cálculo</option>
                  <option value="none">Sem prazo</option>
                  <option value="resolved">Resolvidos</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-extrabold uppercase tracking-wider text-quiet block mb-1">
                  Situação de Leitura
                </label>
                <select
                  className={selectClass}
                  name="read"
                  defaultValue={search.get("read") ?? ""}
                  aria-label="Leitura"
                >
                  <option value="">Lidos e não lidos</option>
                  <option value="unread">Não lidos</option>
                  <option value="read">Lidos</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-extrabold uppercase tracking-wider text-quiet block mb-1">
                  Eventos a partir de
                </label>
                <input
                  className={selectClass}
                  name="date_from"
                  type="date"
                  defaultValue={search.get("date_from") ?? ""}
                  aria-label="Eventos a partir de"
                />
              </div>

              <div>
                <label className="text-[10px] font-extrabold uppercase tracking-wider text-quiet block mb-1">
                  Eventos até
                </label>
                <input
                  className={selectClass}
                  name="date_to"
                  type="date"
                  defaultValue={search.get("date_to") ?? ""}
                  aria-label="Eventos até"
                />
              </div>

              <div>
                <label className="text-[10px] font-extrabold uppercase tracking-wider text-quiet block mb-1">
                  Ordenação
                </label>
                <select
                  className={selectClass}
                  name="ordering"
                  defaultValue={search.get("ordering") ?? "recent"}
                  aria-label="Ordenação"
                >
                  <option value="recent">Mais recentes</option>
                  <option value="deadline">Prazo fatal mais próximo</option>
                  <option value="expedition">Expedição recente</option>
                  <option value="process">Número do processo</option>
                </select>
              </div>

              <div className="flex items-end">
                <button
                  className="button-secondary cursor-pointer w-full px-4 text-xs font-bold"
                  onClick={() => router.replace("/expedientes")}
                  type="button"
                >
                  Limpar filtros
                </button>
              </div>
            </div>
          </details>
        </div>
      </form>

      {error && (
        <Feedback
          action={
            <button className="button-secondary cursor-pointer px-3.5 py-1.5 text-xs font-bold" onClick={load}>
              Tentar novamente
            </button>
          }
        >
          {error}
        </Feedback>
      )}

      {/* Results header & count */}
      <div className="mb-3.5 flex items-center justify-between text-xs text-quiet font-medium">
        <span>
          {data
            ? `${data.count} expediente${data.count === 1 ? "" : "s"} encontrado${data.count === 1 ? "" : "s"}`
            : "Carregando consulta operacional…"}
        </span>
        {query && (
          <button
            type="button"
            className="cursor-pointer border-0 bg-transparent font-extrabold text-ink hover:underline flex items-center gap-1"
            onClick={() => router.replace("/expedientes")}
          >
            <X size={13} weight="bold" />
            Limpar todos os filtros
          </button>
        )}
      </div>

      {data ? <ExpedienteList items={data.results} onSelect={setSelected} /> : <LoadingRows />}

      {/* Pagination controls */}
      {data && pages > 1 && (
        <nav
          className="mt-6 flex items-center justify-center gap-3 text-xs text-quiet"
          aria-label="Paginação"
        >
          <button
            className="button-secondary cursor-pointer px-3.5 py-2 text-xs font-bold disabled:opacity-40 disabled:pointer-events-none"
            disabled={page <= 1}
            onClick={() => go(page - 1)}
          >
            ← Anterior
          </button>
          <span className="px-2">
            Página <strong className="font-[family-name:var(--font-mono)] text-ink font-bold">{page}</strong> de{" "}
            <span className="font-[family-name:var(--font-mono)]">{pages}</span>
          </span>
          <button
            className="button-secondary cursor-pointer px-3.5 py-2 text-xs font-bold disabled:opacity-40 disabled:pointer-events-none"
            disabled={page >= pages}
            onClick={() => go(page + 1)}
          >
            Próxima →
          </button>
        </nav>
      )}

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
