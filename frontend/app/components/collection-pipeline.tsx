import {
  ArrowClockwise, ChartBar, CheckCircle, Clock, MinusCircle, Play, Prohibit, Trash,
  SpinnerGap, Stop, XCircle,
} from "@phosphor-icons/react";
import Link from "next/link";
import { Fragment } from "react";
import { formatDateTime } from "../lib/api";
import type { CollectionPipeline as Pipeline, PipelineStep, PipelineStepStatus } from "../lib/types";
import { BezelCard } from "./ui";

const statusMeta: Record<PipelineStepStatus, { label: string; className: string; Icon: typeof Clock }> = {
  pending: { label: "Aguardando", className: "border-rule bg-panel-muted text-quiet", Icon: Clock },
  running: { label: "Em execução", className: "border-caution/35 bg-caution-soft text-caution", Icon: SpinnerGap },
  success: { label: "Concluída", className: "border-positive/30 bg-positive-soft text-positive", Icon: CheckCircle },
  failed: { label: "Falhou", className: "border-danger/30 bg-danger-soft text-danger", Icon: XCircle },
  cancelled: { label: "Interrompida", className: "border-caution/30 bg-caution-soft text-caution", Icon: Stop },
  disabled: { label: "Desativada", className: "border-rule bg-panel-muted text-quiet opacity-70", Icon: Prohibit },
  skipped: { label: "Ignorada", className: "border-rule bg-panel-muted text-quiet opacity-70", Icon: MinusCircle },
};

function Step({ step, canRerun, onRerun }: { step: PipelineStep; canRerun: boolean; onRerun: (code: string) => void }) {
  const meta = statusMeta[step.status];
  const Icon = meta.Icon;
  const errorId = step.error ? `pipeline-error-${step.code}` : undefined;
  return (
    <li className="group/step">
      <div className={`flex min-h-10 items-center gap-2 rounded-lg border px-2.5 py-2 ${meta.className}`}>
        <Icon
          size={17}
          weight={step.status === "success" || step.status === "failed" ? "fill" : "duotone"}
          className={`shrink-0 ${step.status === "running" ? "animate-spin motion-reduce:animate-none" : ""}`}
          aria-hidden="true"
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[11px] font-bold text-ink" title={step.label}>{step.label}</span>
          <span className="block text-[9px] font-semibold uppercase tracking-[.08em]">{meta.label}</span>
        </span>
        <button
          type="button"
          className="grid size-7 shrink-0 place-items-center rounded-md border border-rule bg-panel text-quiet transition hover:border-quiet hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink disabled:pointer-events-none disabled:opacity-35"
          aria-label={`Reexecutar somente ${step.label}`}
          aria-describedby={errorId}
          title={canRerun ? `Reexecutar somente ${step.label}` : "Disponível após o fim da coleta"}
          disabled={!canRerun}
          onClick={() => onRerun(step.code)}
        >
          <ArrowClockwise size={14} weight="bold" />
        </button>
      </div>
      {step.error && <p id={errorId} className="mt-1.5 line-clamp-2 px-1 text-[10px] font-semibold leading-snug text-danger">{step.error}</p>}
    </li>
  );
}

export function CollectionPipeline({
  pipeline, refreshing, starting, cancelling, discarding, canDiscard,
  onRefresh, onRun, onCancel, onDiscard, onRerun,
}: {
  pipeline: Pipeline;
  refreshing: boolean;
  starting: boolean;
  cancelling: boolean;
  discarding: boolean;
  canDiscard: boolean;
  onRefresh: () => void;
  onRun: () => void;
  onCancel: () => void;
  onDiscard: (trigger: HTMLButtonElement) => void;
  onRerun: (code: string) => void;
}) {
  const groups = Array.from(new Set(pipeline.steps.map((step) => step.group)));
  const current = pipeline.steps.find((step) => step.code === pipeline.current_step);
  const announcement = pipeline.active
    ? `${pipeline.completed} de ${pipeline.total} fontes concluídas. ${current ? `${current.label}: ${statusMeta[current.status].label}.` : "Coleta em andamento."}`
    : pipeline.finished_at
      ? `${pipeline.completed} de ${pipeline.total} fontes concluídas. Última sincronização ${formatDateTime(pipeline.finished_at)}.`
      : "Nenhuma coleta executada ainda.";

  return (
    <BezelCard className="min-w-0 h-full overflow-hidden" innerClassName="flex min-w-0 flex-col p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="mb-1 text-[10px] font-extrabold uppercase tracking-[.14em] text-quiet">Pipeline de coleta</p>
          <h3 className="mb-1 text-base font-extrabold tracking-tight text-ink">{pipeline.completed} de {pipeline.total} fontes concluídas</h3>
          <p className="mb-0 truncate text-[11px] font-medium text-quiet" title={announcement}>{announcement}</p>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <Link href="/historico?tab=orquestracao" className="button-secondary grid size-9 min-h-0 place-items-center p-0 text-quiet focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink" aria-label="Ver relatório de coletas" title="Ver relatório de coletas">
            <ChartBar size={15} weight="duotone" />
          </Link>
          <button type="button" className="button-secondary size-9 min-h-0 p-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink" onClick={onRefresh} disabled={refreshing} aria-label="Atualizar status da coleta" title="Atualizar status da coleta">
            <ArrowClockwise size={15} weight="bold" className={refreshing ? "animate-spin motion-reduce:animate-none" : ""} />
          </button>
          <button type="button" className="button-secondary size-9 min-h-0 border-danger/30 bg-danger-soft p-0 text-danger focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-danger" onClick={(event) => onDiscard(event.currentTarget)} disabled={!canDiscard || discarding} aria-label="Descartar coleta do dia" title={canDiscard ? "Descartar coleta do dia" : "Disponível quando houver dados coletados e nenhuma coleta ativa"}>
            <Trash size={15} weight="fill" className={discarding ? "animate-pulse" : ""} />
          </button>
          {pipeline.active ? (
            <button type="button" className="button-secondary size-9 min-h-0 border-danger/30 bg-danger-soft p-0 text-danger focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-danger" onClick={onCancel} disabled={cancelling} aria-label="Interromper coleta" title="Interromper coleta">
              <Stop size={15} weight="fill" />
            </button>
          ) : (
            <button type="button" className="button-primary size-9 min-h-0 p-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink" onClick={onRun} disabled={starting} aria-label="Executar coleta" title="Executar coleta">
              <Play size={14} weight="fill" />
            </button>
          )}
        </div>
      </div>

      <div className="mt-4 min-w-0 overflow-x-auto overscroll-x-contain pb-2" data-testid="pipeline-scroll-region">
        <div className="flex min-w-max items-start">
          {groups.map((group, index) => (
            <Fragment key={group}>
              {index > 0 && <div className="mt-[18px] h-px w-5 shrink-0 bg-rule" aria-hidden="true" />}
              <section className="w-40 shrink-0 rounded-xl border border-rule bg-panel-muted/45 p-2.5" aria-labelledby={`pipeline-group-${index}`}>
                <h4 id={`pipeline-group-${index}`} className="mb-2.5 text-[10px] font-extrabold uppercase tracking-[.12em] text-ink-soft">{group}</h4>
                <ol className="space-y-2">
                  {pipeline.steps.filter((step) => step.group === group).map((step) => (
                    <Step key={step.code} step={step} canRerun={!pipeline.active && !starting && step.status !== "disabled"} onRerun={onRerun} />
                  ))}
                </ol>
              </section>
            </Fragment>
          ))}
        </div>
      </div>
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">{announcement}</div>
    </BezelCard>
  );
}
