"use client";

import { ArrowRight, CalendarDots, Copy, Check, FolderSimple } from "@phosphor-icons/react";
import { useState } from "react";
import { formatDateTime } from "../lib/api";
import type { Expediente } from "../lib/types";
import { EventBadges } from "./badge";
import { Panel } from "./ui";

export function ExpedienteList({
  items,
  onSelect,
}: {
  items: Expediente[];
  onSelect: (item: Expediente) => void;
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
      <div className="px-6 py-16 text-center">
        <div className="mx-auto mb-4 grid size-12 place-items-center rounded-2xl bg-muted border border-border text-muted-foreground">
          <FolderSimple size={26} weight="duotone" />
        </div>
        <h3 className="mb-2 text-base font-extrabold text-foreground">
          Nenhum expediente por aqui
        </h3>
        <p className="mb-0 max-w-sm mx-auto text-xs sm:text-sm text-muted-foreground">
          Quando a coleta no PJe identificar novas intimações ou alterações, elas aparecerão nesta lista.
        </p>
      </div>
    );
  }

  return (
    <Panel innerClassName="overflow-hidden">
      <div className="divide-y divide-border">
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
            className={`group relative grid w-full cursor-pointer grid-cols-1 gap-4 border-0 bg-transparent px-4 py-4 text-left transition-all duration-150 hover:bg-muted sm:flex sm:items-center sm:gap-6 sm:px-6 ${
              item.unread
                ? "before:absolute before:inset-y-4 before:left-0 before:w-2 before:rounded-r-full before:bg-success"
                : ""
            }`}
            onClick={() => onSelect(item)}
          >
            {/* Main process information */}
            <div className="min-w-0 pr-2 sm:flex-1">
              <EventBadges item={item} />
              <div className="mt-2 flex items-center gap-2">
                <strong className="block truncate font-mono text-sm font-extrabold tracking-tight text-foreground sm:text-sm">
                  {item.processo.numero}
                </strong>
                <button
                  type="button"
                  title="Copiar número do processo"
                  aria-label="Copiar número do processo"
                  onClick={(e) => copyProcessNumber(e, item)}
                  className="grid size-6 place-items-center rounded-md text-muted-foreground opacity-0 transition-all hover:bg-muted hover:text-foreground group-hover:opacity-100"
                >
                  {copiedId === item.id ? (
                    <Check size={13} weight="bold" className="text-success" />
                  ) : (
                    <Copy size={13} />
                  )}
                </button>
              </div>
              <span className="mt-2 block truncate text-xs sm:text-sm font-semibold text-foreground">
                {item.processo.assunto || item.tipo_documento || "Sem assunto informado"}
              </span>
              <small className="mt-2 block truncate text-xs text-muted-foreground">
                {item.processo.partes_texto || item.destinatario}
              </small>
            </div>

            {/* Deadline information */}
            <div className="flex min-w-0 items-start gap-2 border-t border-dashed border-border pt-4 sm:w-56 sm:shrink-0 sm:border-0 sm:pt-0">
              <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-muted border border-border text-muted-foreground">
                <CalendarDots size={15} weight="duotone" />
              </div>
              <div>
                <span className="block text-xs font-extrabold tracking-wide text-muted-foreground uppercase">
                  Prazo fatal
                </span>
                <strong className="mt-2 block font-mono text-xs font-bold text-foreground">
                  {formatDateTime(item.prazo_fatal)}
                </strong>
              </div>
            </div>

            {/* Trailing chevron */}
            <div className="hidden size-8 shrink-0 place-items-center rounded-lg border border-transparent text-muted-foreground transition-all group-hover:border-border group-hover:bg-card group-hover:text-foreground group-hover:translate-x-2 sm:grid">
              <ArrowRight size={17} weight="bold" />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
