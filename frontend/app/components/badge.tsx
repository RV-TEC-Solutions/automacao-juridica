import type { Expediente } from "../lib/types";

export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: string;
  children: React.ReactNode;
}) {
  const tones: Record<string, string> = {
    new: "border-green/[.22] bg-green-soft text-green",
    unread: "border-green/[.22] bg-green-soft text-green",
    updated: "border-blue/[.24] bg-blue-soft text-blue",
    resolved: "text-muted",
    warning: "border-yellow/[.24] bg-yellow-soft text-yellow",
  };
  return <span className={`inline-flex w-max rounded border border-line bg-surface-raised px-1.5 py-0.5 text-[10px] font-[650] tracking-[.02em] text-text-soft ${tones[tone] ?? ""}`}>{children}</span>;
}

export function EventBadges({ item }: { item: Expediente }) {
  return (
    <div className="mb-0.5 flex flex-wrap gap-[5px]">
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
