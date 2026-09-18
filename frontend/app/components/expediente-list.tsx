"use client";

import { formatDateTime } from "../lib/api";
import type { Expediente } from "../lib/types";
import { EventBadges } from "./badge";

export function ExpedienteList({
  items,
  onSelect,
}: {
  items: Expediente[];
  onSelect: (item: Expediente) => void;
}) {
  if (!items.length) {
    return (
      <div className="rounded-[7px] border border-dashed border-line-strong px-5 py-12 text-center text-muted">
        <span className="text-[29px]">∅</span>
        <h3 className="mt-2 mb-1 text-[15px] text-text">Nenhum expediente por aqui</h3>
        <p className="mb-0 text-[12px]">Quando a coleta encontrar algo, os itens aparecerão nesta lista.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[7px] border border-line bg-surface">
      {items.map((item) => (
        <button
          key={item.id}
          className={`relative grid min-h-[92px] w-full grid-cols-[minmax(0,1fr)_210px] gap-6 border-0 border-b border-line bg-transparent py-[15px] pr-[42px] pl-[17px] text-left text-text transition-[background-color,border-color,color,opacity] duration-[160ms] hover:bg-surface-hover last:border-b-0 max-[760px]:grid-cols-1 max-[760px]:gap-[9px] max-[760px]:py-3.5 max-[760px]:pr-[35px] max-[760px]:pl-3.5 ${item.unread ? "shadow-[inset_3px_0_var(--color-accent)]" : ""}`}
          onClick={() => onSelect(item)}
        >
          <div className="flex min-w-0 flex-col justify-center gap-[3px]">
            <EventBadges item={item} />
            <strong className="text-[17px] font-[650]">{item.processo.numero}</strong>
            <span className="overflow-hidden text-[16px] text-ellipsis whitespace-nowrap text-text-soft">{item.processo.assunto || item.tipo_documento || "Sem assunto informado"}</span>
            <small className="overflow-hidden text-[14px] text-ellipsis whitespace-nowrap text-muted">{item.processo.partes_texto || item.destinatario}</small>
          </div>
          <div className="flex min-w-0 flex-col justify-center gap-[3px] max-[760px]:border-t max-[760px]:border-dashed max-[760px]:border-line max-[760px]:pt-2">
            <span className="overflow-hidden text-[14px] text-ellipsis whitespace-nowrap text-muted">Prazo fatal</span>
            <strong className="text-[16px] font-semibold text-text-soft">{formatDateTime(item.prazo_fatal)}</strong>
            <small className="overflow-hidden text-[14px] text-ellipsis whitespace-nowrap text-muted">
              {item.source ? `${item.source.system} · ${item.source.tribunal}` : "Fonte não informada"}
            </small>
          </div>
          <span className="absolute top-1/2 right-4 -translate-y-1/2 text-[24px] text-muted">→</span>
        </button>
      ))}
    </div>
  );
}
