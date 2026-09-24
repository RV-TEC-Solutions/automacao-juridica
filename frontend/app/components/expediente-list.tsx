"use client";

import { ArrowRight, CalendarDots, Copy, Check, FolderSimple } from "@phosphor-icons/react";
import { useState } from "react";
import { formatDateTime } from "../lib/api";
import type { Expediente } from "../lib/types";
import { EventBadges } from "./badge";
import { BezelCard } from "./ui";

export function ExpedienteList({
  items,
  onSelect,
  showSourceBadge = false,
}: {
  items: Expediente[];
  onSelect: (item: Expediente) => void;
  showSourceBadge?: boolean;
}) {
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const copyProcessNumber = (e: React.MouseEvent, item: Expediente) => {
    e.stopPropagation();
    if (navigator.clipboard) {
      navigator.clipboard.writeText(item.processo.numero);
      setCopiedId(item.id);
      setTimeout(() => setCopiedId(null), 1800);
    }
  };

  if (!items.length) {
    return (
      <BezelCard innerClassName="px-6 py-16 text-center">
        <div className="mx-auto mb-3.5 grid size-12 place-items-center rounded-2xl bg-panel-muted border border-rule text-quiet">
          <FolderSimple size={26} weight="duotone" />
        </div>
        <h3 className="mb-1.5 text-base font-extrabold text-ink">
          Nenhum expediente por aqui
        </h3>
        <p className="mb-0 max-w-sm mx-auto text-xs sm:text-sm text-quiet">
          Quando a coleta no PJe identificar novas intimações ou alterações, elas aparecerão nesta lista.
        </p>
      </BezelCard>
    );
  }

  return (
    <BezelCard innerClassName="overflow-hidden">
      <div className="divide-y divide-rule">
        {items.map((item) => (
          <div
            key={item.id}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(item);
              }
            }}
            className={`group relative grid w-full cursor-pointer grid-cols-1 gap-4 border-0 bg-transparent px-4 py-4 text-left transition-all duration-150 hover:bg-panel-hover sm:grid-cols-[minmax(0,1fr)_210px_auto] sm:items-center sm:px-6 ${
              item.unread
                ? "before:absolute before:inset-y-3 before:left-0 before:w-1.5 before:rounded-r-full before:bg-positive"
                : ""
            }`}
            onClick={() => onSelect(item)}
          >
            {/* Main process information */}
            <div className="min-w-0 pr-2">
              <EventBadges item={item} showSource={showSourceBadge} />
              <div className="mt-2.5 flex items-center gap-2">
                <strong className="block truncate font-[family-name:var(--font-mono)] text-sm font-extrabold tracking-tight text-ink sm:text-[15px]">
                  {item.processo.numero}
                </strong>
                <button
                  type="button"
                  title="Copiar número do processo"
                  aria-label="Copiar número do processo"
                  onClick={(e) => copyProcessNumber(e, item)}
                  className="grid size-6 place-items-center rounded-md text-quiet opacity-0 transition-all hover:bg-panel-muted hover:text-ink group-hover:opacity-100"
                >
                  {copiedId === item.id ? (
                    <Check size={13} weight="bold" className="text-positive" />
                  ) : (
                    <Copy size={13} />
                  )}
                </button>
              </div>
              <span className="mt-1 block truncate text-xs sm:text-sm font-semibold text-ink-soft">
                {item.processo.assunto || item.tipo_documento || "Sem assunto informado"}
              </span>
              <small className="mt-0.5 block truncate text-[11.5px] text-quiet">
                {item.processo.partes_texto || item.destinatario}
              </small>
            </div>

            {/* Deadline information */}
            <div className="flex min-w-0 items-start gap-2.5 border-t border-dashed border-rule pt-3 sm:border-0 sm:pt-0">
              <div className="grid size-7 shrink-0 place-items-center rounded-lg bg-panel-muted border border-rule text-quiet">
                <CalendarDots size={15} weight="duotone" />
              </div>
              <div>
                <span className="block text-[10px] font-extrabold tracking-[.12em] text-quiet uppercase">
                  Prazo fatal
                </span>
                <strong className="mt-0.5 block font-[family-name:var(--font-mono)] text-xs font-bold text-ink-soft">
                  {formatDateTime(item.prazo_fatal)}
                </strong>
                <small className="mt-0.5 block truncate text-[11px] text-quiet font-medium">
                  {item.source ? `${item.source.system} · ${item.source.tribunal}` : "Fonte não informada"}
                </small>
              </div>
            </div>

            {/* Trailing chevron */}
            <div className="hidden sm:grid size-8 place-items-center rounded-lg border border-transparent text-quiet transition-all group-hover:border-rule group-hover:bg-panel group-hover:text-ink group-hover:translate-x-0.5">
              <ArrowRight size={17} weight="bold" />
            </div>
          </div>
        ))}
      </div>
    </BezelCard>
  );
}
