"use client";

import Link from "next/link";
import { ArrowRight, Bell, ChartLineUp, ClockCounterClockwise, Play, Sparkle, WarningCircle } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "./components/app-shell";
import { Clock } from "./components/clock";
import { ExpedienteDrawer } from "./components/expediente-drawer";
import { ExpedienteList } from "./components/expediente-list";
import { BezelCard, Feedback, LoadingRows, MetricCard, PageTitle } from "./components/ui";
import { api, formatDateTime } from "./lib/api";
import type { Dashboard, Expediente } from "./lib/types";

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

export default function Home() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Expediente | null>(null);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api<Dashboard>("dashboard/"));
      setError("");
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Falha ao carregar.");
    }
  }, []);

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
      : ["pending", "running"].includes(runStatus ?? "")
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
        eyebrow="Painel operacional"
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

      {data?.latest_run?.status === "failed" && (
        <Feedback
          tone="warning"
          action={
            <button className="button-secondary cursor-pointer px-3.5 py-1.5 text-xs font-bold" onClick={run}>
              Tentar novamente
            </button>
          }
        >
          {data.latest_run.error || "A última coleta encontrou uma inconsistência no PJe."}
        </Feedback>
      )}

      {/* Collection status & trigger banner */}
      <BezelCard
        className="mb-6"
        innerClassName="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"
      >
        <div className="flex items-center gap-3.5">
          <div className="relative flex size-3 items-center justify-center">
            {["pending", "running"].includes(runStatus ?? "") && (
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
                ? `Última sincronização ${formatDateTime(data.latest_run.finished_at ?? data.latest_run.started_at)}`
                : "Dispare uma coleta sob demanda para atualizar os expedientes da banca."}
            </small>
          </div>
        </div>

        <button
          className="button-primary cursor-pointer px-4.5 py-2 text-xs sm:text-sm font-bold shadow-xs"
          onClick={run}
          disabled={running || ["pending", "running"].includes(runStatus ?? "")}
        >
          <Play size={15} weight="fill" />
          {running ? "Solicitando coleta…" : "Executar coleta"}
        </button>
      </BezelCard>

      {/* Executive metrics section */}
      <section className="mb-8">
        <div className="mb-3.5 flex items-center justify-between">
          <div>
            <h2 className="mb-0.5 text-sm sm:text-base font-extrabold tracking-tight text-ink">
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

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <MetricCard
            label="Novos"
            value={data?.today.new ?? 0}
            note="expedientes descobertos"
            icon={<Sparkle size={18} weight="duotone" />}
            tone="green"
          />
          <MetricCard
            label="Alterados"
            value={data?.today.updated ?? 0}
            note="mudanças de prazo/teor"
            icon={<ClockCounterClockwise size={18} weight="duotone" />}
            tone="blue"
          />
          <MetricCard
            label="Não lidos"
            value={data?.today.unread ?? 0}
            note="aguardando leitura"
            icon={<Bell size={18} weight="duotone" />}
            tone="slate"
          />
          <MetricCard
            label="Urgentes"
            value={data?.today.urgent ?? 0}
            note="vencidos ou até 72h"
            icon={<WarningCircle size={18} weight="duotone" />}
            tone="rose"
          />
        </div>

        {(data?.today.calculating ?? 0) > 0 && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-caution/25 bg-caution-soft px-3.5 py-2 text-xs font-semibold text-caution">
            <WarningCircle size={16} weight="duotone" className="shrink-0" />
            <span>{data?.today.calculating} prazo(s) ainda estão em cálculo interno no PJe.</span>
          </div>
        )}
      </section>

      {/* Activity since last visit banner */}
      {data && (
        <BezelCard
          className="mb-8"
          innerClassName="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"
        >
          <div>
            <span className="text-[10px] font-extrabold tracking-[.14em] text-quiet uppercase">
              Atividade desde a última visita
            </span>
            <p className="mt-1 mb-0 text-xs sm:text-sm text-ink-soft leading-relaxed">
              <strong className="text-ink">{data.since_last_visit.new} novo{data.since_last_visit.new === 1 ? "" : "s"}</strong>,{" "}
              <strong className="text-ink">{data.since_last_visit.updated} alterado{data.since_last_visit.updated === 1 ? "" : "s"}</strong> e{" "}
              <strong className="text-ink">{data.since_last_visit.resolved} resolvido{data.since_last_visit.resolved === 1 ? "" : "s"}</strong>.
            </p>
          </div>
          <small className="text-xs font-mono text-quiet shrink-0">
            {data.since_last_visit.since ? `Desde ${formatDateTime(data.since_last_visit.since)}` : "Primeiro resumo"}
          </small>
        </BezelCard>
      )}

      {/* Recent expedientes */}
      <section>
        <div className="mb-3.5 flex items-end justify-between gap-4">
          <div>
            <h2 className="mb-0.5 text-sm sm:text-base font-extrabold tracking-tight text-ink">
              Expedientes recentes
            </h2>
            <p className="mb-0 text-xs text-quiet font-medium">
              Últimas intimações e movimentações capturadas nas fontes conectadas.
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

        {data ? <ExpedienteList items={data.recent} onSelect={setSelected} /> : <LoadingRows />}
      </section>

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
