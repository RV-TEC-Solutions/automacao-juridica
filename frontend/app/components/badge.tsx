import { Info } from "@phosphor-icons/react";
import type { Expediente } from "../lib/types";

const unidentifiedPendingHelp = "O PJe não forneceu informações suficientes para distinguir se este expediente aguarda ciência ou resposta.";

const sourceBadgeClasses: Record<string, string> = {
  "pje-tjrn": "source-badge-tjrn-1g", "pje2g-tjrn": "source-badge-tjrn-2g",
  "tre-rn-1g": "source-badge-tre-rn-1g", "tre-rn-2g": "source-badge-tre-rn-2g",
  "tse-3g": "source-badge-tse-3g",
  trt21: "source-badge-trt21-1g", "trt21-2g": "source-badge-trt21-2g",
  "trf5-2g-tru": "source-badge-trf5-tru", "varas-justica-comum": "source-badge-trf5-varas",
  "jef-5-regiao": "source-badge-trf5-jef", "trs-5-regiao": "source-badge-trf5-trs",
  "tru-5-regiao": "source-badge-trf5-tru-alt",
};

export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: string;
  children: React.ReactNode;
}) {
  const tones: Record<string, string> = {
    new: "border-success/30 bg-success-soft text-success font-bold",
    unread: "border-success/35 bg-success-soft text-success font-extrabold",
    updated: "border-zinc-300 dark:border-zinc-700 bg-muted text-foreground font-bold",
    resolved: "border-border bg-muted/80 text-muted-foreground font-medium",
    warning: "border-warning/30 bg-warning-soft text-warning font-bold",
    danger: "border-destructive/30 bg-destructive/10 text-destructive font-bold",
  };

  return (
    <span
      className={`inline-flex w-max items-center gap-2 rounded-full border px-2 py-2 text-xs leading-none ${
        tones[tone] ?? "border-border bg-muted text-foreground font-medium"
      }`}
    >
      {tone === "unread" && <span className="size-2 rounded-full bg-success" />}
      {children}
    </span>
  );
}

export function SourceBadge({ source }: { source: NonNullable<Expediente["source"]> }) {
  const sourceClass = sourceBadgeClasses[source.code] ?? "source-badge-default";
  return <span data-source={source.code} className={`source-badge ${sourceClass}`}><span aria-hidden="true" className="source-badge-dot" /><span className="whitespace-nowrap">{source.system} · {source.tribunal}</span></span>;
}

export function EventBadges({ item }: { item: Expediente }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {item.unread && <Badge tone="unread">Não lido</Badge>}
      <Badge tone={item.latest_event?.kind ?? "neutral"}>
        {item.latest_event?.kind_label ?? (item.ativo ? "Ativo" : "Resolvido")}
      </Badge>
      {item.tipo_pendencia_label && (
        <span className="inline-flex items-center gap-1">
          <Badge tone="neutral">{item.tipo_pendencia === "nao_identificada" ? "Tipo de pendência: não identificada" : item.tipo_pendencia_label.replace("Pendente de ", "")}</Badge>
          {item.tipo_pendencia === "nao_identificada" &&
            <span tabIndex={0} role="img" aria-label={unidentifiedPendingHelp} title={unidentifiedPendingHelp} className="cursor-help text-muted-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"><Info size={14} weight="bold" aria-hidden="true" /></span>
          }
        </span>
      )}
      {item.source && <SourceBadge source={item.source} />}
    </div>
  );
}
