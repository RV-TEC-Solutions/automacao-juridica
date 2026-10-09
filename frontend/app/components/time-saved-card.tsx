import { ClockCounterClockwise } from "@phosphor-icons/react";
import type { TimeSaved } from "../lib/types";

function formatDuration(seconds: number) {
  const minutes = Math.round(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `${minutes} min`;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

export function TimeSavedCard({ value }: { value?: TimeSaved }) {
  return (
    <section className="mb-6 rounded-lg border bg-card text-card-foreground shadow-sm" aria-label="Tempo economizado estimado">
      <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
        <div className="flex min-w-0 items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-md bg-success-soft text-success">
            <ClockCounterClockwise size={20} weight="duotone" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Tempo economizado · estimativa</h3>
            <strong className="mt-2 block font-mono text-2xl font-semibold tabular-nums sm:text-3xl">{formatDuration(value?.total_seconds ?? 0)}</strong>
            <p className="mt-2 text-xs text-muted-foreground">Acumulado desde a primeira coleta concluída · até 4 h por dia</p>
          </div>
        </div>
        <div className="border-t pt-3 sm:min-w-40 sm:border-l sm:border-t-0 sm:pl-6 sm:pt-0">
          <span className="block text-xs font-semibold text-muted-foreground">Hoje</span>
          <strong className="mt-1 block font-mono text-xl font-semibold tabular-nums">{formatDuration(value?.today_seconds ?? 0)}</strong>
          <span className="mt-1 block text-xs text-muted-foreground">{value?.source_days ?? 0} consultas por fonte e dia no histórico</span>
        </div>
      </div>
      <details className="border-t px-4 py-3 text-xs text-muted-foreground">
        <summary className="w-fit cursor-pointer font-semibold text-foreground focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">Como calculamos</summary>
        <p className="mt-3 max-w-3xl leading-5">Simulamos uma pessoa consultando cada fonte com calma: acessar e autenticar, verificar avisos, abrir as caixas, conferir os registros e organizar o resultado. Descontamos uma breve conferência da coleta automática.</p>
        <ul className="mt-2 list-disc space-y-1 pl-4 leading-5">
          <li>PJe direto (TJRN): 6 min por fonte/dia + 45 s por aba + 1 min 15 s por expediente.</li>
          <li>PJe via portal (TRE-RN, TSE e TRF5): 8 min por fonte/dia + 45 s por aba + 1 min 15 s por expediente.</li>
          <li>TRT21: 6 min por fonte/dia + 2 min por expediente, incluindo a abertura dos detalhes.</li>
          <li>DJEN: 12 min por coleta/dia para sete datas + 1 min 30 s por publicação nova.</li>
        </ul>
        <p className="mt-2 max-w-3xl leading-5">Contamos apenas coletas concluídas e não descartadas. Reexecuções no mesmo dia não repetem o tempo fixo; no PJe usamos o maior volume encontrado e no DJEN só publicações novas. O total de cada dia é limitado a 4 h, mesmo quando a soma das fontes e registros ultrapassa esse valor. O acumulado cobre todo o histórico, independentemente do período selecionado acima. É uma estimativa de trabalho operacional, não uma medição cronometrada.</p>
      </details>
    </section>
  );
}
