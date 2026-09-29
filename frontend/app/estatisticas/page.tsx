"use client";

import { ChartBar, CheckCircle, ClockCounterClockwise, Sparkle } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { AppShell } from "../components/app-shell";
import { Panel, MetricCard, PageTitle } from "../components/ui";
import { useNotifications } from "../components/notifications";
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

type TimelineDay = {
  day: string;
  new: number;
  updated: number;
  resolved: number;
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

function groupTimeline(rows: Stats["timeline"]): TimelineDay[] {
  const days = new Map<string, TimelineDay>();

  rows.forEach((row) => {
    const day = days.get(row.day) ?? { day: row.day, new: 0, updated: 0, resolved: 0 };
    if (row.kind === "new" || row.kind === "updated" || row.kind === "resolved") day[row.kind] += row.total;
    days.set(row.day, day);
  });

  return Array.from(days.values()).sort((first, second) => first.day.localeCompare(second.day));
}

function formatChartDay(day: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Fortaleza", day: "2-digit", month: "2-digit", year: "numeric",
  }).format(new Date(`${day}T12:00:00-03:00`));
}

export default function StatisticsPage() {
  const [period, setPeriod] = useState(7);
  const [data, setData] = useState<Stats | null>(null);
  const { notify } = useNotifications();

  useEffect(() => {
    api<Stats>(`statistics/?period=${period}`)
      .then((value) => {
        setData(value);
      })
      .catch((exception) => notify({ message: exception instanceof Error ? exception.message : "Não foi possível carregar as estatísticas." }));
  }, [period, notify]);

  const timeline = groupTimeline(data?.timeline ?? []);
  const maxDailyTotal = Math.max(1, ...timeline.map((day) => day.new + day.updated + day.resolved));

  return (
    <AppShell>
      <PageTitle
        title="Estatísticas"
        description="Acompanhe o volume histórico de entradas, alterações de prazos e resoluções de expedientes."
        actions={
          <div className="flex rounded-xl border border-border bg-muted/80 p-2 shadow-xs">
            <Button
              variant={period === 7 ? "default" : "ghost"}
              size="sm"
              onClick={() => setPeriod(7)}
            >
              7 dias
            </Button>
            <Button
              variant={period === 30 ? "default" : "ghost"}
              size="sm"
              onClick={() => setPeriod(30)}
            >
              30 dias
            </Button>
          </div>
        }
      />

      {data && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
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

          <Panel className="mb-6" innerClassName="p-6 sm:p-6">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-border/60 pb-4">
              <div>
                <h2 className="mb-2 text-sm sm:text-base font-extrabold tracking-tight text-foreground">
                  Entradas e movimentações
                </h2>
                <p className="mb-0 text-xs text-muted-foreground font-medium">
                  Cada coluna representa um dia e sua altura mostra o total de eventos registrados.
                </p>
              </div>

              <div className="flex items-center gap-4 text-xs font-extrabold tracking-wider text-muted-foreground uppercase">
                <span className="flex items-center gap-2">
                  <i className="size-2 rounded-sm bg-success" />
                  Chegadas
                </span>
                <span className="flex items-center gap-2">
                  <i className="size-2 rounded-sm bg-primary" />
                  Alterados
                </span>
                <span className="flex items-center gap-2">
                  <i className="size-2 rounded-sm bg-muted-foreground" />
                  Resolvidos
                </span>
              </div>
            </div>

            {timeline.length ? (
              <>
                <div className="flex h-60 items-end gap-2 border-b border-border px-2 pt-4">
                  {timeline.map((day, index) => {
                    const total = day.new + day.updated + day.resolved;
                    const labelInterval = Math.max(1, Math.ceil(timeline.length / 6));
                    const showLabel = index === 0 || index === timeline.length - 1 || index % labelInterval === 0;
                    const description = `${formatChartDay(day.day)}: ${day.new} chegadas, ${day.updated} alterações e ${day.resolved} resoluções.`;

                    return (
                      <div key={day.day} className="group flex min-w-0 flex-1 flex-col justify-end self-stretch" title={description}>
                        <div className="flex flex-1 items-end justify-center">
                          {total > 0 && (
                            <div className="flex w-full max-w-8 flex-col overflow-hidden rounded-t-sm transition-opacity group-hover:opacity-80" style={{ height: `${Math.max(8, (total / maxDailyTotal) * 100)}%` }}>
                              {day.new > 0 && <div className="bg-success" style={{ height: `${(day.new / total) * 100}%` }} />}
                              {day.updated > 0 && <div className="bg-primary" style={{ height: `${(day.updated / total) * 100}%` }} />}
                              {day.resolved > 0 && <div className="bg-muted-foreground/60" style={{ height: `${(day.resolved / total) * 100}%` }} />}
                            </div>
                          )}
                        </div>
                        <span className="mt-2 h-4 truncate text-center text-xs font-medium text-muted-foreground">{showLabel ? formatChartDay(day.day).slice(0, 5) : ""}</span>
                      </div>
                    );
                  })}
                </div>
                <p className="mb-0 mt-4 text-xs font-medium text-muted-foreground">
                  Chegadas são expedientes identificados pela primeira vez. Movimentações são alterações e resoluções de expedientes já conhecidos.
                </p>
              </>
            ) : (
              <div className="rounded-xl border border-dashed border-border px-6 py-12 text-center text-xs sm:text-sm text-muted-foreground">
                Nenhuma movimentação registrada neste período.
              </div>
            )}
          </Panel>

          <div className="grid gap-6 lg:grid-cols-2">
            <Distribution
              title="Pendências Ativas"
              rows={data.pending_distribution.map((row) => ({
                label: labels[row.tipo_pendencia] ?? row.tipo_pendencia,
                total: row.total,
              }))}
              barColor="bg-primary"
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
    <Panel innerClassName="p-6 sm:p-6">
      <h2 className="mb-6 text-xs font-extrabold tracking-tight text-foreground uppercase">
        {title}
      </h2>
      {rows.length ? (
        <div className="space-y-4">
          {rows.map((row) => (
            <div key={row.label}>
              <div className="mb-2 flex justify-between text-xs">
                <span className="font-semibold text-foreground">{row.label}</span>
                <strong className="font-mono tabular-nums text-foreground">
                  {row.total}
                </strong>
              </div>
              <div className="block h-2 overflow-hidden rounded-full bg-muted border border-border/50">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${barColor}`}
                  style={{ width: `${(row.total / total) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mb-0 text-xs sm:text-sm text-muted-foreground font-medium">Nenhum expediente ativo.</p>
      )}
    </Panel>
  );
}
