"use client";

import { CaretDown, Clock, FolderSimple, WarningCircle } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { formatDateTime, api } from "../lib/api";
import type { CollectionHistory, CollectionRun } from "../lib/types";
import { BezelCard, Feedback, LoadingRows } from "./ui";

const statusClass: Record<CollectionRun["status"], string> = {
  pending: "border-rule bg-panel-muted text-quiet",
  running: "border-caution/35 bg-caution-soft text-caution",
  success: "border-positive/30 bg-positive-soft text-positive",
  failed: "border-danger/30 bg-danger-soft text-danger",
  cancelled: "border-caution/30 bg-caution-soft text-caution",
  disabled: "border-rule bg-panel-muted text-quiet",
  skipped: "border-rule bg-panel-muted text-quiet",
};

function formatDay(date: string) {
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Fortaleza", day: "numeric", month: "long", year: "numeric" }).format(new Date(`${date}T12:00:00-03:00`));
}

function formatDuration(seconds: number | null) {
  if (seconds === null) return "Em andamento";
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes ? `${minutes} min ${remainder}s` : `${remainder}s`;
}

function RunRow({ run, expanded, onToggle }: { run: CollectionRun; expanded: boolean; onToggle: () => void }) {
  const errorId = `collection-run-error-${run.id}`;
  return <>
    <tr className="border-b border-rule last:border-0">
      <td className="whitespace-nowrap px-4 py-3"><span className={`inline-flex rounded-full border px-2 py-1 text-[10px] font-extrabold uppercase tracking-wide ${statusClass[run.status]}`}>{run.status_label}</span></td>
      <td className="px-4 py-3"><strong className="block text-xs font-bold text-ink">{run.source?.system ?? "Fonte indisponível"}</strong><span className="text-[11px] font-medium text-quiet">{run.source?.tribunal ?? "—"}</span></td>
      <td className="whitespace-nowrap px-4 py-3 text-xs font-semibold text-ink-soft">{run.trigger_label}</td>
      <td className="whitespace-nowrap px-4 py-3 text-xs font-medium text-quiet">{formatDateTime(run.started_at ?? run.created_at, { timeStyle: "short" })}</td>
      <td className="whitespace-nowrap px-4 py-3 text-xs font-medium text-quiet">{formatDuration(run.duration_seconds)}</td>
      <td className="whitespace-nowrap px-4 py-3 text-[11px] font-semibold text-quiet"><span title="Encontrados">{run.found} encontrados</span><span className="mx-1.5 text-rule">·</span><span className="text-positive" title="Novos">+{run.created}</span><span className="mx-1.5 text-rule">·</span><span title="Alterados">{run.updated} alt.</span><span className="mx-1.5 text-rule">·</span><span title="Resolvidos">{run.resolved} res.</span></td>
      <td className="px-4 py-3 text-right">{run.error ? <button type="button" className="inline-flex items-center gap-1 rounded-lg border border-danger/30 bg-danger-soft px-2 py-1 text-[11px] font-bold text-danger transition-colors hover:border-danger focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-danger" aria-expanded={expanded} aria-controls={errorId} onClick={onToggle}>Ver erro<CaretDown size={12} weight="bold" className={expanded ? "rotate-180" : ""} /></button> : <span className="text-xs text-quiet">—</span>}</td>
    </tr>
    {run.error && expanded && <tr id={errorId} className="border-b border-rule bg-danger-soft/40"><td colSpan={7} className="px-4 py-3"><div role="alert" className="flex gap-2 text-xs leading-relaxed text-danger"><WarningCircle size={16} weight="fill" className="mt-0.5 shrink-0" /><span className="whitespace-pre-wrap">{run.error}</span></div></td></tr>}
  </>;
}

export function CollectionHistoryPanel() {
  const [data, setData] = useState<CollectionHistory | null>(null);
  const [error, setError] = useState("");
  const [expandedRun, setExpandedRun] = useState<number | null>(null);
  const load = useCallback(async () => {
    try { setData(await api<CollectionHistory>("automation/history/")); setError(""); }
    catch (exception) { setError(exception instanceof Error ? exception.message : "Falha ao carregar o relatório de coletas."); }
  }, []);

  useEffect(() => { queueMicrotask(() => { void load(); }); }, [load]);

  if (!data && !error) return <LoadingRows />;
  return <div className="space-y-7">
    {error && <Feedback action={<button className="button-secondary px-3.5 py-1.5 text-xs font-bold" onClick={load}>Tentar novamente</button>}>{error}</Feedback>}
    {data?.days.map((day) => <section key={day.date} aria-labelledby={`collection-day-${day.date}`}>
      <header className="mb-3 flex items-center gap-3"><span className="grid size-9 place-items-center rounded-xl border border-rule bg-panel-muted text-quiet"><Clock size={18} weight="duotone" aria-hidden="true" /></span><h2 id={`collection-day-${day.date}`} className="text-sm font-extrabold tracking-tight text-ink sm:text-base">{formatDay(day.date)} <span className="font-medium text-quiet">({day.runs.length} fonte{day.runs.length === 1 ? "" : "s"})</span></h2></header>
      <BezelCard className="overflow-hidden" innerClassName="overflow-x-auto">
        <table className="min-w-[920px] w-full border-collapse text-left" aria-label={`Execuções de ${formatDay(day.date)}`}>
          <thead className="border-b border-rule bg-panel-muted/60 text-[10px] font-extrabold uppercase tracking-[.12em] text-quiet"><tr><th className="px-4 py-3">Status</th><th className="px-4 py-3">Fonte</th><th className="px-4 py-3">Acionamento</th><th className="px-4 py-3">Início</th><th className="px-4 py-3">Duração</th><th className="px-4 py-3">Resultados</th><th className="px-4 py-3 text-right">Detalhes</th></tr></thead>
          <tbody>{day.runs.map((run) => <RunRow key={run.id} run={run} expanded={expandedRun === run.id} onToggle={() => setExpandedRun((current) => current === run.id ? null : run.id)} />)}</tbody>
        </table>
      </BezelCard>
    </section>)}
    {data && data.days.length === 0 && <BezelCard innerClassName="flex items-center gap-3 px-5 py-4 text-xs font-semibold text-quiet"><FolderSimple size={19} weight="duotone" className="shrink-0" />Nenhuma coleta executada nos últimos 30 dias.</BezelCard>}
  </div>;
}
