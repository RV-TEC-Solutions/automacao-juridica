"use client";

import { CaretDown, Clock, WarningCircle } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Fragment, useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, formatDateTime } from "../lib/api";
import type { CollectionHistory, CollectionRun } from "../lib/types";
import { EmptyState, HistoryDayHeader, LoadingRows } from "./ui";
import { useNotifications } from "./notifications";

const statusVariant: Record<CollectionRun["status"], "outline" | "warning" | "success" | "destructive"> = {
  pending: "outline", running: "warning", success: "success", failed: "destructive",
  cancelled: "warning", disabled: "outline", skipped: "outline",
};

function formatDuration(seconds: number | null) {
  if (seconds === null) return "Em andamento";
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes ? `${minutes} min ${remainder}s` : `${remainder}s`;
}

function RunRows({ run, expanded, onToggle }: { run: CollectionRun; expanded: boolean; onToggle: () => void }) {
  const errorId = `collection-run-error-${run.id}`;
  return <Fragment>
    <TableRow>
      <TableCell><Badge variant={statusVariant[run.status]}>{run.status_label}</Badge></TableCell>
      <TableCell><strong className="block text-xs">{run.source?.system ?? "Fonte indisponível"}</strong><span className="text-xs text-muted-foreground">{run.source?.tribunal ?? "—"}</span></TableCell>
      <TableCell>{run.trigger_label}</TableCell>
      <TableCell>{formatDateTime(run.started_at ?? run.created_at, { timeStyle: "short" })}</TableCell>
      <TableCell>{formatDuration(run.duration_seconds)}</TableCell>
      <TableCell><span>{run.found} encontrados</span><span className="mx-2 text-border">·</span><span className="text-success">+{run.created}</span><span className="mx-2 text-border">·</span><span>{run.updated} alt.</span><span className="mx-2 text-border">·</span><span>{run.resolved} res.</span></TableCell>
      <TableCell className="text-right">{run.error ? <Button variant="outline" size="sm" className="text-destructive" aria-expanded={expanded} aria-controls={errorId} onClick={onToggle}>Ver erro<CaretDown className={expanded ? "rotate-180" : ""} /></Button> : "—"}</TableCell>
    </TableRow>
    {run.error && expanded && <TableRow id={errorId} className="bg-destructive/10"><TableCell colSpan={7}><div role="alert" className="flex gap-2 whitespace-pre-wrap text-xs leading-6 text-destructive"><WarningCircle size={16} weight="fill" className="mt-2 shrink-0" />{run.error}</div></TableCell></TableRow>}
  </Fragment>;
}

export function CollectionHistoryPanel() {
  const [data, setData] = useState<CollectionHistory | null>(null);
  const { notify } = useNotifications();
  const [error, setError] = useState("");
  const [expandedRun, setExpandedRun] = useState<number | null>(null);
  const load = useCallback(async () => {
    try { setData(await api<CollectionHistory>("automation/history/")); setError(""); }
    catch (exception) { const message = exception instanceof Error ? exception.message : "Falha ao carregar o relatório de coletas."; setError(message); notify({ message }); }
  }, [notify]);

  useEffect(() => { queueMicrotask(() => { void load(); }); }, [load]);
  if (!data && !error) return <LoadingRows />;

  return <div className="space-y-8">

    {data?.days.map((day) => <section key={day.date} aria-labelledby={`collection-day-${day.date}`}>
      <HistoryDayHeader date={day.date} label={`${day.runs.length} fonte${day.runs.length === 1 ? "" : "s"}`} icon={<Clock size={18} aria-hidden="true" />} id={`collection-day-${day.date}`} />
      <div className="overflow-hidden rounded-lg border bg-card"><Table className="min-w-5xl" aria-labelledby={`collection-day-${day.date}`}><TableHeader className="bg-muted/50"><TableRow><TableHead>Status</TableHead><TableHead>Fonte</TableHead><TableHead>Acionamento</TableHead><TableHead>Início</TableHead><TableHead>Duração</TableHead><TableHead>Resultados</TableHead><TableHead className="text-right">Detalhes</TableHead></TableRow></TableHeader><TableBody>{day.runs.map((run) => <RunRows key={run.id} run={run} expanded={expandedRun === run.id} onToggle={() => setExpandedRun((current) => current === run.id ? null : run.id)} />)}</TableBody></Table></div>
    </section>)}
    {data && data.days.length === 0 && <EmptyState icon={<Clock size={26} weight="duotone" />} title="Nenhuma coleta encontrada" description="A consulta diária pode não ter coletas para os filtros atuais." />}
  </div>;
}
