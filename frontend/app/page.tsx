"use client";

import Link from "next/link";
import { ArrowRight, Bell, ChartLineUp, CalendarDots, ClockCounterClockwise, Play, Sparkle, WarningCircle } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "./components/app-shell";
import { Clock } from "./components/clock";
import { ExpedienteDrawer } from "./components/expediente-drawer";
import { ExpedienteList } from "./components/expediente-list";
import { Feedback, LoadingRows, MetricCard, PageTitle } from "./components/ui";
import { api, formatDateTime } from "./lib/api";
import type { Dashboard, Expediente, ExpedientePage } from "./lib/types";

function greeting() {
  const hour = Number(
    new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Fortaleza",
      hour: "numeric",
      hour12: false,
    }).format(new Date())
  );
  return hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
}

type MetricKey = "new" | "updated" | "unread" | "urgent" | "next_week" | "calculating";

const metricFilters: Record<MetricKey, { title: string; description: string; params: Record<string, string> }> = {
  new: { title: "Expedientes de Hoje", description: "Todos os expedientes descobertos na coleta de hoje.", params: { event_kind: "new" } },
  updated: { title: "Expedientes alterados hoje", description: "Expedientes com prazo ou teor alterado hoje.", params: { event_kind: "updated" } },
  unread: { title: "Expedientes não lidos", description: "Expedientes que ainda aguardam leitura.", params: { read: "unread" } },
  urgent: { title: "Expedientes urgentes", description: "Prazos vencidos ou com vencimento nas próximas 72 horas.", params: { deadline: "urgent" } },
  next_week: { title: "Prazos até próxima semana", description: "Expedientes com prazo fatal até o fim da próxima semana.", params: { deadline: "next_week" } },
  calculating: { title: "Prazos em cálculo", description: "Expedientes cujo prazo ainda está em cálculo interno no PJe.", params: { deadline: "calculating" } },
};

function localDate() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Fortaleza", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return `${values.year}-${values.month}-${values.day}`;
}
export default function Home() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Expediente | null>(null);
  const [running, setRunning] = useState(false);
  const [activeMetric, setActiveMetric] = useState<MetricKey>("new");
  const [listPage, setListPage] = useState(1);
  const [expedientes, setExpedientes] = useState<ExpedientePage | null>(null);
  const [listError, setListError] = useState("");

  const load = useCallback(async () => {
    try {
      setData(await api<Dashboard>("dashboard/"));
      setError("");
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Falha ao carregar.");
    }
  }, []);

  const loadExpedientes = useCallback(async () => {
    const filter = metricFilters[activeMetric];
    const params = new URLSearchParams({ ...filter.params, page: String(listPage), page_size: "50", ordering: "recent" });
    if (activeMetric === "new" || activeMetric === "updated") {
      const today = localDate();
      params.set("date_from", today);
      params.set("date_to", today);
    }
    try {
      setExpedientes(await api<ExpedientePage>(`expedientes/?${params}`));
      setListError("");
    } catch (exception) {
      setListError(exception instanceof Error ? exception.message : "Falha ao carregar expedientes.");
    }
  }, [activeMetric, listPage]);

  useEffect(() => {
    queueMicrotask(() => { void loadExpedientes(); });
  }, [loadExpedientes]);

  const selectMetric = (metric: MetricKey) => {
    setActiveMetric(metric);
    setListPage(1);
  };

  useEffect(() => {
    queueMicrotask(() => {
      load().then(() => api("dashboard/", { method: "POST" }).catch(() => {}));
    });
  }, [load]);

  const run = async () => {
    setRunning(true);
    try {
      await api("automation/runs/", {
        method: "POST",
        body: JSON.stringify({ source: "pje-tjrn" }),
      });
      await load();
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Não foi possível iniciar.");
    } finally {
      setRunning(false);
    }
  };

  const runStatus = data?.latest_run?.status;
  const collectionInProgress = ["pending", "running"].includes(runStatus ?? "");

  useEffect(() => {
    if (!collectionInProgress) return;

    const interval = window.setInterval(() => {
      void load();
    }, 10_000);

    return () => window.clearInterval(interval);
  }, [collectionInProgress, load]);
  const statusCopy = !data?.latest_run
    ? "Nenhuma coleta executada"
    : runStatus === "success"
    ? "Coleta concluída com êxito"
    : runStatus === "failed"
    ? "Coleta requer atenção"
    : runStatus === "running"
    ? "Coleta em andamento no PJe"
    : "Coleta aguardando execução";

  const statusTone =
    runStatus === "success"
      ? "bg-positive"
      : runStatus === "failed"
      ? "bg-danger"
      : collectionInProgress
      ? "bg-caution animate-pulse"
      : "bg-quiet";

  const date = new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Fortaleza",
    weekday: "long",
    day: "2-digit",
    month: "long",
  }).format(new Date());

  const formattedDate = date.charAt(0).toUpperCase() + date.slice(1);

  return (
    <AppShell>
      <PageTitle
        title={`${greeting()}, ${data?.display_name.split(" ")[0] ?? ""}.`}
        description={formattedDate}
        actions={<Clock />}
      />

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

      <div className="mb-8 grid gap-6 xl:grid-cols-2 xl:items-start">
        {/* Executive metrics section */}
        <section className="order-2 min-w-0 xl:order-1">
        <div className="mb-3.5 flex items-center justify-between">
          <div>
            <h2 className="mb-0.5 text-2xl font-extrabold tracking-tight leading-tight text-ink sm:text-3xl">
              Visão executiva
            </h2>
            <p className="mb-0 text-xs text-quiet font-medium">
              Indicadores consolidados do ciclo de monitoramento atual.
            </p>
          </div>
          <div className="grid size-8 place-items-center rounded-xl border border-rule bg-panel text-quiet">
            <ChartLineUp size={18} weight="duotone" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          <MetricCard
            label="Novos"
            value={data?.today.new ?? 0}
            note="expedientes descobertos"
            icon={<Sparkle size={18} weight="duotone" />}
            tone="green"
            onClick={() => selectMetric("new")}
            selected={activeMetric === "new"}
          />
          <MetricCard
            label="Alterados"
            value={data?.today.updated ?? 0}
            note="mudanças de prazo/teor"
            icon={<ClockCounterClockwise size={18} weight="duotone" />}
            tone="blue"
            onClick={() => selectMetric("updated")}
            selected={activeMetric === "updated"}
          />
          <MetricCard
            label="Não lidos"
            value={data?.today.unread ?? 0}
            note="aguardando leitura"
            icon={<Bell size={18} weight="duotone" />}
            tone="slate"
            onClick={() => selectMetric("unread")}
            selected={activeMetric === "unread"}
          />
          <MetricCard
            label="Urgentes"
            value={data?.today.urgent ?? 0}
            note="vencidos ou até 72h"
            icon={<WarningCircle size={18} weight="duotone" />}
            tone="rose"
            onClick={() => selectMetric("urgent")}
            selected={activeMetric === "urgent"}
          />
          <MetricCard
            label="Até próxima semana"
            value={data?.today.next_week ?? 0}
            note="prazos fatais a vencer"
            icon={<CalendarDots size={18} weight="duotone" />}
            tone="amber"
            onClick={() => selectMetric("next_week")}
            selected={activeMetric === "next_week"}
          />
          <MetricCard
            label="Prazos em cálculo"
            value={data?.today.calculating ?? 0}
            note="prazos ainda em cálculo"
            icon={<WarningCircle size={18} weight="duotone" />}
            tone="slate"
            onClick={() => selectMetric("calculating")}
            selected={activeMetric === "calculating"}
          />
        </div>
        </section>

        {/* Collection status & trigger panel */}
        <MetricCard
          label=""
          value=""
          note=""
          icon={null}
          className="order-1 h-fit xl:order-2 xl:mt-[68px]"
          innerClassName="gap-3 sm:flex-row sm:items-stretch sm:justify-between"
        >
          <div className="flex items-start gap-3.5">
            <div className="relative mt-1 flex size-3 items-center justify-center">
              {collectionInProgress && (
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-caution opacity-75" />
              )}
              <span className={`size-2.5 rounded-full ${statusTone}`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <strong className="text-sm font-extrabold text-ink">{statusCopy}</strong>
                <span className="rounded-md border border-rule bg-panel-muted px-2 py-0.5 text-[10px] font-bold text-quiet">
                  PJe · TJRN
                </span>
              </div>
              <small className="mt-0.5 block text-xs text-quiet font-medium">
                {data?.latest_run
                  ? data.latest_run.message || `Última sincronização ${formatDateTime(data.latest_run.finished_at ?? data.latest_run.started_at)}`
                  : "Dispare uma coleta sob demanda para atualizar os expedientes da banca."}
              </small>
              {runStatus === "failed" && (
                <div
                  className="mt-3 flex items-center gap-2 rounded-lg border border-caution/25 bg-caution-soft px-3 py-2 text-xs font-semibold text-caution"
                  role="alert"
                >
                  <WarningCircle size={16} weight="duotone" className="shrink-0" />
                  <span>{data?.latest_run?.error || "Coleta interrompida antes da conclusão."}</span>
                </div>
              )}
            </div>
          </div>

          <button
            className="button-primary shrink-0 cursor-pointer whitespace-nowrap px-4.5 py-6 text-xs sm:text-sm font-bold shadow-xs sm:self-stretch"
            onClick={run}
            disabled={running || collectionInProgress}
          >
            <Play size={15} weight="fill" />
            {running ? "Solicitando coleta…" : "Executar coleta"}
          </button>
        </MetricCard>
      </div>

      {/* Recent expedientes */}
      <section>
        <div className="mb-3.5 flex items-end justify-between gap-4">
          <div>
            <h2 className="mb-0.5 text-2xl font-extrabold tracking-tight leading-tight text-ink sm:text-3xl">
              {metricFilters[activeMetric].title}{activeMetric === "new" ? " (" + formattedDate + ")" : ""}
            </h2>
            <p className="mb-0 text-xs text-quiet font-medium">
              {metricFilters[activeMetric].description}
            </p>
          </div>
          <Link
            href="/expedientes"
            className="group inline-flex items-center gap-1.5 text-xs font-extrabold text-ink-soft no-underline hover:text-ink transition-colors"
          >
            Ver consulta completa
            <ArrowRight size={14} weight="bold" className="transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>

        {listError && <Feedback action={<button className="button-secondary cursor-pointer px-3.5 py-1.5 text-xs font-bold" onClick={loadExpedientes}>Tentar novamente</button>}>{listError}</Feedback>}
        {expedientes ? <ExpedienteList items={expedientes.results} onSelect={setSelected} /> : <LoadingRows />}

        {expedientes && expedientes.count > 50 && (
          <nav className="mt-6 flex items-center justify-center gap-3 text-xs text-quiet" aria-label="Paginação de expedientes">
            <button className="button-secondary cursor-pointer px-3.5 py-2 text-xs font-bold disabled:pointer-events-none disabled:opacity-40" disabled={listPage <= 1} onClick={() => setListPage((page) => page - 1)}>← Anterior</button>
            <span>Página <strong className="font-[family-name:var(--font-mono)] text-ink">{listPage}</strong> de {Math.ceil(expedientes.count / 50)}</span>
            <button className="button-secondary cursor-pointer px-3.5 py-2 text-xs font-bold disabled:pointer-events-none disabled:opacity-40" disabled={listPage >= Math.ceil(expedientes.count / 50)} onClick={() => setListPage((page) => page + 1)}>Próxima →</button>
          </nav>
        )}
      </section>

      <ExpedienteDrawer
        item={selected}
        onClose={() => setSelected(null)}
        onRead={() => {
          if (selected) setSelected({ ...selected, unread: false });
          load();
          loadExpedientes();
        }}
      />
    </AppShell>
  );
}
