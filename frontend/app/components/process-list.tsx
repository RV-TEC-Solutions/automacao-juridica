"use client";

import { ArrowRight, CalendarDots, Check, Copy } from "@phosphor-icons/react";
import { useState, type ReactNode } from "react";
import { Panel } from "./ui";

type ProcessRow = {
  id: number;
  number: string;
  badges: ReactNode;
  title: string;
  detail: string;
  dateLabel: string;
  date: string;
  unread: boolean;
  onSelect: () => void;
};

export function ProcessList({ rows }: { rows: ProcessRow[] }) {
  const [copiedId, setCopiedId] = useState<number | null>(null);
  return <Panel innerClassName="overflow-hidden">
    <div className="divide-y divide-border">
      {rows.map((row) => <div key={row.id} role="button" tabIndex={0}
        onClick={row.onSelect}
        onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); row.onSelect(); } }}
        className={`group relative grid w-full cursor-pointer grid-cols-1 gap-4 border-0 bg-transparent px-4 py-4 text-left transition-all duration-150 hover:bg-muted sm:flex sm:items-center sm:gap-6 sm:px-6 ${row.unread ? "before:absolute before:inset-y-4 before:left-0 before:w-2 before:rounded-r-full before:bg-success" : ""}`}>
        <div className="min-w-0 pr-2 sm:flex-1">
          {row.badges}
          <div className="mt-2 flex items-center gap-2">
            <strong className="block truncate font-mono text-sm font-extrabold tracking-tight text-foreground">{row.number}</strong>
            <button type="button" title="Copiar número do processo" aria-label="Copiar número do processo"
              onClick={(event) => { event.stopPropagation(); if (navigator.clipboard) { void navigator.clipboard.writeText(row.number); setCopiedId(row.id); setTimeout(() => setCopiedId(null), 1800); } }}
              className="grid size-6 place-items-center rounded-md text-muted-foreground opacity-0 transition-all hover:bg-muted hover:text-foreground group-hover:opacity-100 focus-visible:opacity-100">
              {copiedId === row.id ? <Check size={13} weight="bold" className="text-success" /> : <Copy size={13} />}
            </button>
          </div>
          <span className="mt-2 block truncate text-xs font-semibold text-foreground sm:text-sm">{row.title}</span>
          <small className="mt-2 block truncate text-xs text-muted-foreground">{row.detail}</small>
        </div>
        <div className="flex min-w-0 items-start gap-2 border-t border-dashed border-border pt-4 sm:w-56 sm:shrink-0 sm:border-0 sm:pt-0">
          <div className="grid size-8 shrink-0 place-items-center rounded-lg border border-border bg-muted text-muted-foreground"><CalendarDots size={15} weight="duotone" /></div>
          <div>
            <span className="block text-xs font-extrabold uppercase tracking-wide text-muted-foreground">{row.dateLabel}</span>
            <strong className="mt-2 block font-mono text-xs font-bold text-foreground">{row.date}</strong>
          </div>
        </div>
        <div className="hidden size-8 shrink-0 place-items-center rounded-lg border border-transparent text-muted-foreground transition-all group-hover:translate-x-2 group-hover:border-border group-hover:bg-card group-hover:text-foreground sm:grid"><ArrowRight size={17} weight="bold" /></div>
      </div>)}
    </div>
  </Panel>;
}
