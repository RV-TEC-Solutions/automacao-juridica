"use client";

import { ArrowRight, CalendarDots, FolderSimple } from "@phosphor-icons/react";
import { formatDateTime } from "../lib/api";
import type { Expediente } from "../lib/types";
import { EventBadges } from "./badge";
import { BezelCard } from "./ui";

export function ExpedienteList({ items, onSelect }: { items: Expediente[]; onSelect: (item: Expediente) => void }) {
  if (!items.length) return <BezelCard innerClassName="px-6 py-14 text-center"><FolderSimple size={30} className="mx-auto mb-3 text-quiet" /><h3 className="mb-2 text-base font-extrabold text-ink">Nenhum expediente por aqui</h3><p className="mb-0 text-sm text-quiet">Quando a coleta encontrar algo, os itens aparecerão nesta lista.</p></BezelCard>;

  return <BezelCard innerClassName="overflow-hidden">
    <div className="divide-y divide-rule">
      {items.map((item) => <button key={item.id} className={`group relative grid w-full cursor-pointer grid-cols-1 gap-4 border-0 bg-transparent px-4 py-4 text-left transition-colors hover:bg-panel-hover sm:grid-cols-[minmax(0,1fr)_190px_auto] sm:items-center sm:px-5 ${item.unread ? "before:absolute before:inset-y-4 before:left-0 before:w-1 before:rounded-r-full before:bg-brand" : ""}`} onClick={() => onSelect(item)}>
        <div className="min-w-0"><EventBadges item={item} /><strong className="mt-2 block truncate font-[family-name:var(--font-mono)] text-sm font-extrabold text-ink sm:text-base">{item.processo.numero}</strong><span className="mt-1 block truncate text-sm font-semibold text-ink-soft">{item.processo.assunto || item.tipo_documento || "Sem assunto informado"}</span><small className="mt-1 block truncate text-xs text-quiet">{item.processo.partes_texto || item.destinatario}</small></div>
        <div className="flex min-w-0 items-center gap-2 border-t border-dashed border-rule pt-3 sm:block sm:border-0 sm:pt-0"><CalendarDots size={17} className="shrink-0 text-brand sm:mb-1" /><div><span className="block text-[10px] font-extrabold tracking-[.1em] text-quiet uppercase">Prazo fatal</span><strong className="mt-1 block font-[family-name:var(--font-mono)] text-xs font-bold text-ink-soft">{formatDateTime(item.prazo_fatal)}</strong><small className="mt-1 block truncate text-[11px] text-quiet">{item.source ? `${item.source.system} · ${item.source.tribunal}` : "Fonte não informada"}</small></div></div>
        <ArrowRight size={19} className="absolute right-4 bottom-4 text-quiet transition-transform group-hover:translate-x-1 group-hover:text-brand sm:static" />
      </button>)}
    </div>
  </BezelCard>;
}
