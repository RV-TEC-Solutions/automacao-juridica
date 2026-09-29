import {
  ArrowClockwise, ChartBar, CheckCircle, Clock, MinusCircle, Play, Prohibit, Trash,
  SpinnerGap, Stop, XCircle,
} from "@phosphor-icons/react";
import Link from "next/link";
import { Fragment } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import { formatDateTime } from "../lib/api";
import type { CollectionPipeline as Pipeline, PipelineStep, PipelineStepStatus } from "../lib/types";
import { Panel } from "./ui";

const statusMeta: Record<PipelineStepStatus, { label: string; className: string; Icon: typeof Clock }> = {
  pending: { label: "Aguardando", className: "border-border bg-muted text-muted-foreground", Icon: Clock },
  running: { label: "Em execução", className: "border-warning/35 bg-warning-soft text-warning", Icon: SpinnerGap },
  success: { label: "Concluída", className: "border-success/30 bg-success-soft text-success", Icon: CheckCircle },
  failed: { label: "Falhou", className: "border-destructive/30 bg-destructive/10 text-destructive", Icon: XCircle },
  cancelled: { label: "Interrompida", className: "border-warning/30 bg-warning-soft text-warning", Icon: Stop },
  disabled: { label: "Desativada", className: "border-border bg-muted text-muted-foreground opacity-70", Icon: Prohibit },
  skipped: { label: "Ignorada", className: "border-border bg-muted text-muted-foreground opacity-70", Icon: MinusCircle },
};

function Step({ step, canRerun, onRerun }: { step: PipelineStep; canRerun: boolean; onRerun: (code: string) => void }) {
  const meta = statusMeta[step.status];
  const Icon = meta.Icon;
  const errorId = step.error ? `pipeline-error-${step.code}` : undefined;
  return (
    <li className="group/step">
      <div className={`flex min-h-10 items-center gap-2 rounded-lg border px-2 py-2 ${meta.className}`}>
        <Icon
          size={17}
          weight={step.status === "success" || step.status === "failed" ? "fill" : "duotone"}
          className={`shrink-0 ${step.status === "running" ? "animate-spin motion-reduce:animate-none" : ""}`}
          aria-hidden="true"
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-xs font-bold text-foreground" title={step.label}>{step.label}</span>
          <span className="block text-xs font-semibold uppercase tracking-wide">{meta.label}</span>
        </span>
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          aria-label={`Reexecutar somente ${step.label}`}
          aria-describedby={errorId}
          title={canRerun ? `Reexecutar somente ${step.label}` : "Disponível após o fim da coleta"}
          disabled={!canRerun}
          onClick={() => onRerun(step.code)}
        >
          <ArrowClockwise size={14} weight="bold" />
        </Button>
      </div>
      {step.error && <p id={errorId} className="mt-2 line-clamp-2 px-2 text-xs font-semibold leading-snug text-destructive">{step.error}</p>}
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
  const statusDescription = pipeline.active
    ? current ? `${current.label}: ${statusMeta[current.status].label}.` : "Coleta em andamento."
    : pipeline.finished_at ? "Coleta concluída." : "Nenhuma coleta executada ainda.";
  const announcement = `${pipeline.completed} de ${pipeline.total} fontes concluídas. ${statusDescription}${pipeline.finished_at ? ` Última sincronização: ${formatDateTime(pipeline.finished_at)}.` : ""}`;

  return (
    <Panel className="min-w-0 h-full overflow-hidden" innerClassName="flex min-w-0 flex-col p-4 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1">
            <p className="mb-0 text-xs font-extrabold uppercase tracking-wide text-muted-foreground">Pipeline de coleta</p>
            {pipeline.finished_at && <span className="text-xs font-medium text-muted-foreground">Última sincronização: {formatDateTime(pipeline.finished_at)}</span>}
          </div>
          <h3 className="mb-2 text-base font-extrabold tracking-tight text-foreground">{pipeline.completed} de {pipeline.total} fontes concluídas</h3>
          {pipeline.active && <p className="mb-0 truncate text-xs font-medium text-muted-foreground" title={statusDescription}>{statusDescription}</p>}
        </div>
        <div className="flex shrink-0 gap-2">
          <Link href="/historico?tab=orquestracao" className={buttonVariants({ variant: "outline", size: "icon" })} aria-label="Ver relatório de coletas" title="Ver relatório de coletas">
            <ChartBar size={15} weight="duotone" />
          </Link>
          <Button type="button" variant="outline" size="icon" onClick={onRefresh} disabled={refreshing} aria-label="Atualizar status da coleta" title="Atualizar status da coleta">
            <ArrowClockwise size={15} weight="bold" className={refreshing ? "animate-spin motion-reduce:animate-none" : ""} />
          </Button>
          <Button type="button" variant="outline" size="icon" className="text-destructive" onClick={(event) => onDiscard(event.currentTarget)} disabled={!canDiscard || discarding} aria-label="Descartar coleta do dia" title={canDiscard ? "Descartar coleta do dia" : "Disponível quando houver dados coletados e nenhuma coleta ativa"}>
            <Trash size={15} weight="fill" className={discarding ? "animate-pulse" : ""} />
          </Button>
          {pipeline.active ? (
            <Button type="button" variant="outline" size="icon" className="text-destructive" onClick={onCancel} disabled={cancelling} aria-label="Interromper coleta" title="Interromper coleta">
              <Stop size={15} weight="fill" />
            </Button>
          ) : (
            <Button type="button" size="icon" onClick={onRun} disabled={starting} aria-label="Executar coleta" title="Executar coleta">
              <Play size={14} weight="fill" />
            </Button>
          )}
        </div>
      </div>

      <div className="mt-4 min-w-0 overflow-x-auto overscroll-x-contain pb-2" data-testid="pipeline-scroll-region">
        <div className="flex min-w-max items-start">
          {groups.map((group, index) => (
            <Fragment key={group}>
              {index > 0 && <div className="mt-4 h-px w-6 shrink-0 bg-border" aria-hidden="true" />}
              <section className="w-48 shrink-0 rounded-xl border border-border bg-muted/45 p-2" aria-labelledby={`pipeline-group-${index}`}>
                <h4 id={`pipeline-group-${index}`} className="mb-2 text-xs font-extrabold uppercase tracking-wide text-foreground">{group}</h4>
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
    </Panel>
  );
}
