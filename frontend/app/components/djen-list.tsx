"use client";

import { ArrowRight, CalendarDots, Check, Copy } from "@phosphor-icons/react";
import { useState } from "react";
import type { DjenCommunication } from "../lib/types";
import { RecordList } from "./record-list";
import { Panel } from "./ui";

const date = (value: string) => new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));

export function DjenList({ items, onSelect, home = false }: { items: DjenCommunication[]; onSelect: (item: DjenCommunication) => void; home?: boolean }) {
  const [copiedId, setCopiedId] = useState<number | null>(null);
  if (!items.length) return null;

  if (home) return <Panel innerClassName="overflow-hidden">
    <div className="divide-y divide-border">
      {items.map((item) => <div key={item.id} role="button" tabIndex={0}
        onClick={() => onSelect(item)}
        onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(item); } }}
        className={`group relative grid w-full cursor-pointer grid-cols-1 gap-4 border-0 bg-transparent px-4 py-4 text-left transition-all duration-150 hover:bg-muted sm:flex sm:items-center sm:gap-6 sm:px-6 ${item.unread ? "before:absolute before:inset-y-4 before:left-0 before:w-2 before:rounded-r-full before:bg-success" : ""}`}>
        <div className="min-w-0 pr-2 sm:flex-1">
          {item.unread && <span className="inline-flex rounded-full bg-success-soft px-2 py-0.5 text-xs font-bold text-success">Nova</span>}
          <div className="mt-2 flex items-center gap-2">
            <strong className="block truncate font-mono text-sm font-extrabold tracking-tight text-foreground">{item.processo.numero}</strong>
            <button type="button" title="Copiar número do processo" aria-label="Copiar número do processo"
              onClick={(event) => { event.stopPropagation(); if (navigator.clipboard) { void navigator.clipboard.writeText(item.processo.numero); setCopiedId(item.id); setTimeout(() => setCopiedId(null), 1800); } }}
              className="grid size-6 place-items-center rounded-md text-muted-foreground opacity-0 transition-all hover:bg-muted hover:text-foreground group-hover:opacity-100 focus-visible:opacity-100">
              {copiedId === item.id ? <Check size={13} weight="bold" className="text-success" /> : <Copy size={13} />}
            </button>
          </div>
          <span className="mt-2 block truncate text-xs font-semibold text-foreground sm:text-sm">{item.tipo_comunicacao || item.tipo_documento || "Comunicação"}</span>
          <small className="mt-2 block truncate text-xs text-muted-foreground">{item.orgao || item.recipients.map((recipient) => recipient.name).join(", ") || "—"}</small>
        </div>
        <div className="flex min-w-0 items-start gap-2 border-t border-dashed border-border pt-4 sm:w-56 sm:shrink-0 sm:border-0 sm:pt-0">
          <div className="grid size-8 shrink-0 place-items-center rounded-lg border border-border bg-muted text-muted-foreground"><CalendarDots size={15} weight="duotone" /></div>
          <div>
            <span className="block text-xs font-extrabold uppercase tracking-wide text-muted-foreground">Disponibilização · {item.tribunal}</span>
            <strong className="mt-2 block font-mono text-xs font-bold text-foreground">{date(item.data_disponibilizacao)}</strong>
          </div>
        </div>
        <div className="hidden size-8 shrink-0 place-items-center rounded-lg border border-transparent text-muted-foreground transition-all group-hover:translate-x-2 group-hover:border-border group-hover:bg-card group-hover:text-foreground sm:grid"><ArrowRight size={17} weight="bold" /></div>
      </div>)}
    </div>
  </Panel>;

  return <RecordList>
    {items.map((item) => <li key={item.id}>
      <button type="button" onClick={() => onSelect(item)} className="grid w-full min-w-0 gap-2 px-4 py-3 text-left transition-colors hover:bg-muted/45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_auto] sm:items-center sm:gap-5 sm:px-5">
        <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <strong className="min-w-0 truncate font-mono text-sm text-foreground">{item.processo.numero}</strong>
          {item.unread && <span className="shrink-0 rounded-full bg-warning-soft px-2 py-0.5 text-xs font-bold text-warning">Nova</span>}
        </span>
        <span className="min-w-0 text-xs text-muted-foreground sm:text-sm">
          <span className="block truncate font-semibold text-foreground">{item.tipo_comunicacao || "Comunicação"}</span>
          <span className="block truncate">{item.orgao || item.texto || "—"}</span>
        </span>
        <span className="flex items-center gap-2 text-xs text-muted-foreground sm:justify-end">
          <span className="rounded-md border bg-muted px-2 py-1 font-extrabold text-foreground">{item.tribunal}</span>
          <time dateTime={item.data_disponibilizacao}>{date(item.data_disponibilizacao)}</time>
        </span>
      </button>
    </li>)}
  </RecordList>;
}
