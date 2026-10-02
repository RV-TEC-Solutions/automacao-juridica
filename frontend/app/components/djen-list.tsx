import type { DjenCommunication } from "../lib/types";
import { Badge, SourceBadge } from "./badge";
import { ProcessList } from "./process-list";

const date = (value: string) => new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
const sourceCodes: Record<string, string> = { TJRN: "pje-tjrn", "TRE-RN": "tre-rn-1g", TSE: "tse-3g", TRT21: "trt21", TRF5: "trf5-2g-tru" };

export function DjenList({ items, onSelect }: { items: DjenCommunication[]; onSelect: (item: DjenCommunication) => void }) {
  if (!items.length) return null;
  return <ProcessList rows={items.map((item) => ({
    id: item.id,
    number: item.processo.numero,
    badges: <div className="flex flex-wrap items-center gap-2">
      {item.unread && <Badge tone="unread">Não lido</Badge>}
      <SourceBadge source={{ code: sourceCodes[item.tribunal.toUpperCase()] ?? "djen", system: "DJEN", tribunal: item.tribunal }} />
    </div>,
    title: item.tipo_comunicacao || item.tipo_documento || "Comunicação",
    detail: item.orgao || item.recipients.map((recipient) => recipient.name).join(", ") || "—",
    dateLabel: "Disponibilização",
    date: date(item.data_disponibilizacao),
    unread: item.unread,
    onSelect: () => onSelect(item),
  }))} />;
}
