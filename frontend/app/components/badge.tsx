import type { Expediente } from "../lib/types";

const sourceBadgeClasses: Record<string, string> = {
  "pje-tjrn": "source-badge-tjrn-1g", "pje2g-tjrn": "source-badge-tjrn-2g",
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
    new: "border-positive/30 bg-positive-soft text-positive font-bold",
    unread: "border-positive/35 bg-positive-soft text-positive font-extrabold",
    updated: "border-zinc-300 dark:border-zinc-700 bg-panel-muted text-ink font-bold",
    resolved: "border-rule bg-panel-muted/80 text-quiet font-medium",
    warning: "border-caution/30 bg-caution-soft text-caution font-bold",
    danger: "border-danger/30 bg-danger-soft text-danger font-bold",
  };

  return (
    <span
      className={`inline-flex w-max items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10.5px] tracking-tight leading-tight ${
        tones[tone] ?? "border-rule bg-panel-muted text-ink-soft font-medium"
      }`}
    >
      {tone === "unread" && <span className="size-1.5 rounded-full bg-positive animate-pulse" />}
      {children}
    </span>
  );
}

export function SourceBadge({ source }: { source: NonNullable<Expediente["source"]> }) {
  const sourceClass = sourceBadgeClasses[source.code] ?? "source-badge-default";
  return <span className={`source-badge ${sourceClass}`}><span aria-hidden="true" className="source-badge-dot" /><span className="whitespace-nowrap">{source.system} · {source.tribunal}</span></span>;
}

export function EventBadges({ item }: { item: Expediente }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {item.unread && <Badge tone="unread">Não lido</Badge>}
      <Badge tone={item.latest_event?.kind ?? "neutral"}>
        {item.latest_event?.kind_label ?? (item.ativo ? "Ativo" : "Resolvido")}
      </Badge>
      {item.tipo_pendencia_label && (
        <Badge tone="neutral">{item.tipo_pendencia_label.replace("Pendente de ", "")}</Badge>
      )}
      {item.source && <SourceBadge source={item.source} />}
    </div>
  );
}
