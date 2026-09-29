import type { Expediente } from "../lib/types";

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
  return <span data-source={source.code} className="inline-flex w-max items-center gap-2 rounded-full border border-border bg-background px-2 py-2 text-xs font-medium text-foreground"><span aria-hidden="true" className="size-2 rounded-full bg-muted-foreground" /><span className="whitespace-nowrap">{source.system} · {source.tribunal}</span></span>;
}

export function EventBadges({ item }: { item: Expediente }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
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
