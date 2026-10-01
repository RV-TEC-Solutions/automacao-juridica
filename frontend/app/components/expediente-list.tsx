import { FolderSimple } from "@phosphor-icons/react";
import { formatDateTime } from "../lib/api";
import type { Expediente } from "../lib/types";
import { EventBadges } from "./badge";
import { ProcessList } from "./process-list";
import { EmptyState } from "./ui";

export function ExpedienteList({ items, onSelect }: { items: Expediente[]; onSelect: (item: Expediente) => void }) {
  if (!items.length) return <EmptyState icon={<FolderSimple size={26} weight="duotone" />} title="Nenhum expediente por aqui" description="Quando a coleta no PJe identificar novas intimações ou alterações, elas aparecerão nesta lista." />;
  return <ProcessList rows={items.map((item) => ({
    id: item.id,
    number: item.processo.numero,
    badges: <EventBadges item={item} />,
    title: item.processo.assunto || item.tipo_documento || "Sem assunto informado",
    detail: item.processo.partes_texto || item.destinatario,
    dateLabel: "Prazo fatal",
    date: formatDateTime(item.prazo_fatal),
    unread: item.unread,
    onSelect: () => onSelect(item),
  }))} />;
}
