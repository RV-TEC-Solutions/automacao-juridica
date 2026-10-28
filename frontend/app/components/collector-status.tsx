import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "../lib/api";
import type { CollectorStatus } from "../lib/types";

const states: Record<CollectorStatus["state"], string> = {
  disabled: "Desabilitado", unconfigured: "Credenciais incompletas", idle: "Aguardando primeira coleta",
  pending: "Na fila", running: "Coletando", blocked: "Credencial suspensa neste ciclo",
  failed: "Falha na última fonte", success: "Última fonte concluída", cancelled: "Coleta interrompida",
};

export function CollectorStatusList({ collectors, detailed = false }: { collectors: CollectorStatus[]; detailed?: boolean }) {
  return <div aria-label="Titulares de coleta" className="grid min-w-0 gap-3 sm:grid-cols-2">
    {collectors.map((collector) => <div key={collector.code} className="min-w-0 rounded-lg border border-border px-3 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong className="text-sm text-foreground">{collector.label}</strong>
        <Badge variant={collector.state === "blocked" || collector.state === "failed" ? "destructive" : collector.state === "running" || collector.state === "unconfigured" ? "warning" : "outline"}>{states[collector.state]}</Badge>
      </div>
      {detailed && <p className="mb-0 mt-2 text-xs text-muted-foreground">
        PIN: {collector.pin_configured ? "configurado" : "ausente"} · TOTP: {collector.totp_configured ? "configurado" : "ausente"}.
        {" "}Token e identidade conferidos durante a autenticação.
      </p>}
      <p className="mb-0 mt-2 text-xs text-muted-foreground">{collector.last_success_at ? `Última fonte concluída: ${formatDateTime(collector.last_success_at)}` : "Nenhuma fonte concluída para este titular."}</p>
      {collector.error && <p className="mb-0 mt-2 wrap-anywhere text-xs text-destructive">{collector.error}</p>}
      {collector.state === "blocked" && <p className="mb-0 mt-2 text-xs text-muted-foreground">Confira a credencial antes de reexecutar. As próximas fontes deste titular foram suspensas no ciclo.</p>}
    </div>)}
  </div>;
}
