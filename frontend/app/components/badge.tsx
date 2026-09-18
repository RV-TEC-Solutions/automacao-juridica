import type { Expediente } from "../lib/types";

export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: string;
  children: React.ReactNode;
}) {
  const tones: Record<string, string> = {
    new: "border-positive/25 bg-positive-soft text-positive",
    unread: "border-positive/25 bg-positive-soft text-positive",
    updated: "border-brand/25 bg-brand-soft text-brand",
    resolved: "border-rule bg-panel-muted text-quiet",
    warning: "border-caution/25 bg-caution-soft text-caution",
  };
  return <span className={`inline-flex w-max items-center rounded-full border px-2 py-1 text-[10px] font-extrabold tracking-[.04em] ${tones[tone] ?? "border-rule bg-panel-muted text-ink-soft"}`}>{children}</span>;
}

export function EventBadges({ item }: { item: Expediente }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {item.unread && <Badge tone="unread">Não lido</Badge>}
      <Badge tone={item.latest_event?.kind ?? "neutral"}>
        {item.latest_event?.kind_label ?? (item.ativo ? "Ativo" : "Resolvido")}
      </Badge>
      {item.tipo_pendencia_label && (
        <Badge>{item.tipo_pendencia_label.replace("Pendente de ", "")}</Badge>
      )}
    </div>
  );
}
