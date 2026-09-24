import type { Expediente } from "../lib/types";

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

export function EventBadges({ item, showSource = false }: { item: Expediente; showSource?: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {item.unread && <Badge tone="unread">Não lido</Badge>}
      <Badge tone={item.latest_event?.kind ?? "neutral"}>
        {item.latest_event?.kind_label ?? (item.ativo ? "Ativo" : "Resolvido")}
      </Badge>
      {item.tipo_pendencia_label && (
        <Badge tone="neutral">{item.tipo_pendencia_label.replace("Pendente de ", "")}</Badge>
      )}
      {showSource && item.source && <Badge tone="neutral"><span className="whitespace-nowrap">{item.source.system} · {item.source.tribunal}</span></Badge>}
    </div>
  );
}
