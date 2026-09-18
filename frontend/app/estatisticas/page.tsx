"use client";

import { ChartBar, CheckCircle, ClockCounterClockwise, Sparkle } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { AppShell } from "../components/app-shell";
import { BezelCard, Feedback, MetricCard, PageTitle } from "../components/ui";
import { api } from "../lib/api";

type Stats = {
  period: number;
  totals: {
    current: number;
    previous: number;
    change_percent: number | null;
    new?: number;
    updated?: number;
    resolved?: number;
  };
  timeline: { day: string; kind: string; total: number }[];
  pending_distribution: { tipo_pendencia: string; total: number }[];
  deadline_distribution: { status_prazo_fatal: string; total: number }[];
};

const labels: Record<string, string> = {
  new: "Novos",
  updated: "Alterados",
  resolved: "Resolvidos",
  ciencia: "Ciência",
  resposta: "Resposta",
  nao_identificada: "Outros",
  calculado: "Calculado",
  em_calculo: "Em cálculo",
  sem_prazo: "Sem prazo",
};

export default function StatisticsPage() {
  const [period, setPeriod] = useState(7);
  const [data, setData] = useState<Stats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Stats>(`statistics/?period=${period}`)
      .then((value) => {
        setData(value);
        setError("");
      })
      .catch((exception) => setError(exception.message));
  }, [period]);

  const max = Math.max(1, ...(data?.timeline.map((row) => row.total) ?? [1]));

  return (
    <AppShell>
      <PageTitle
        eyebrow="Inteligência operacional"
        title="Estatísticas"
        description="Acompanhe o volume histórico de entradas, alterações de prazos e resoluções de expedientes."
        actions={
          <div className="flex rounded-xl border border-rule bg-panel-muted/80 p-1 shadow-xs">
            <button
              className={`cursor-pointer rounded-lg px-3.5 py-1.5 text-xs font-extrabold transition-all ${
                period === 7
                  ? "bg-brand text-brand-fg shadow-xs"
                  : "text-quiet hover:text-ink"
              }`}
              onClick={() => setPeriod(7)}
            >
              7 dias
            </button>
            <button
              className={`cursor-pointer rounded-lg px-3.5 py-1.5 text-xs font-extrabold transition-all ${
                period === 30
                  ? "bg-brand text-brand-fg shadow-xs"
                  : "text-quiet hover:text-ink"
              }`}
              onClick={() => setPeriod(30)}
            >
              30 dias
            </button>
          </div>
        }
      />

      {error && <Feedback>{error}</Feedback>}

      {data && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MetricCard
              label="Atividade Total"
              value={data.totals.current}
              note={
                data.totals.change_percent === null
                  ? "sem base anterior"
                  : `${data.totals.change_percent >= 0 ? "↑" : "↓"} ${Math.abs(
                      data.totals.change_percent
                    )}% ante ciclo anterior`
              }
              icon={<ChartBar size={18} weight="duotone" />}
              tone="slate"
            />
            <MetricCard
              label="Novos"
              value={data.totals.new ?? 0}
              note="expedientes descobertos"
              icon={<Sparkle size={18} weight="duotone" />}
              tone="green"
            />
            <MetricCard
              label="Alterados"
              value={data.totals.updated ?? 0}
              note="mudanças relevantes de prazo"
              icon={<ClockCounterClockwise size={18} weight="duotone" />}
              tone="amber"
            />
            <MetricCard
              label="Resolvidos"
              value={data.totals.resolved ?? 0}
              note="cumpridos / baixados"
              icon={<CheckCircle size={18} weight="duotone" />}
              tone="blue"
            />
          </div>

          <BezelCard className="mb-6" innerClassName="p-5 sm:p-6">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-rule/60 pb-4">
              <div>
                <h2 className="mb-1 text-sm sm:text-base font-extrabold tracking-tight text-ink">
                  Movimentações e Chegadas
                </h2>
                <p className="mb-0 text-xs text-quiet font-medium">
                  Volume de eventos processuais registrados nos últimos {period} dias.
                </p>
              </div>

              <div className="flex items-center gap-4 text-[10px] font-extrabold tracking-wider text-quiet uppercase">
                <span className="flex items-center gap-1.5">
                  <i className="size-2 rounded-sm bg-positive" />
                  Novos
                </span>
                <span className="flex items-center gap-1.5">
                  <i className="size-2 rounded-sm bg-brand" />
                  Alterados
                </span>
                <span className="flex items-center gap-1.5">
                  <i className="size-2 rounded-sm bg-quiet" />
                  Resolvidos
                </span>
              </div>
            </div>

            {data.timeline.length ? (
              <div className="flex h-[240px] items-end gap-1.5 border-b border-rule px-2 pt-4">
                {data.timeline.map((row, index) => (
                  <div
                    key={`${row.day}-${row.kind}-${index}`}
                    className={`min-w-1.5 flex-1 rounded-t-sm transition-all hover:opacity-80 ${
                      row.kind === "updated"
                        ? "bg-brand"
                        : row.kind === "resolved"
                        ? "bg-quiet/60"
                        : "bg-positive"
                    }`}
                    style={{ height: `${Math.max(8, (row.total / max) * 100)}%` }}
                    title={`${row.day}: ${row.total} ${labels[row.kind] ?? row.kind}`}
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-rule px-6 py-12 text-center text-xs sm:text-sm text-quiet">
                Nenhuma movimentação registrada neste período.
              </div>
            )}
          </BezelCard>

          <div className="grid gap-5 lg:grid-cols-2">
            <Distribution
              title="Pendências Ativas"
              rows={data.pending_distribution.map((row) => ({
                label: labels[row.tipo_pendencia] ?? row.tipo_pendencia,
                total: row.total,
              }))}
              barColor="bg-brand"
            />
            <Distribution
              title="Situação dos Prazos"
              rows={data.deadline_distribution.map((row) => ({
                label: labels[row.status_prazo_fatal] ?? row.status_prazo_fatal,
                total: row.total,
              }))}
              barColor="bg-zinc-600 dark:bg-zinc-400"
            />
          </div>
        </>
      )}
    </AppShell>
  );
}

function Distribution({
  title,
  rows,
  barColor,
}: {
  title: string;
  rows: { label: string; total: number }[];
  barColor: string;
}) {
  const total = rows.reduce((sum, row) => sum + row.total, 0) || 1;

  return (
    <BezelCard innerClassName="p-5 sm:p-6">
      <h2 className="mb-5 text-xs font-extrabold tracking-tight text-ink uppercase">
        {title}
      </h2>
      {rows.length ? (
        <div className="space-y-4">
          {rows.map((row) => (
            <div key={row.label}>
              <div className="mb-1.5 flex justify-between text-xs">
                <span className="font-semibold text-ink-soft">{row.label}</span>
                <strong className="font-[family-name:var(--font-mono)] tabular-nums text-ink">
                  {row.total}
                </strong>
              </div>
              <div className="block h-2 overflow-hidden rounded-full bg-panel-muted border border-rule/50">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${barColor}`}
                  style={{ width: `${(row.total / total) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mb-0 text-xs sm:text-sm text-quiet font-medium">Nenhum expediente ativo.</p>
      )}
    </BezelCard>
  );
}
