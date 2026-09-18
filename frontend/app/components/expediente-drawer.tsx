"use client";

import { X } from "@phosphor-icons/react";
import { useEffect, useRef } from "react";
import { api, formatDateTime } from "../lib/api";
import type { Expediente } from "../lib/types";
import { Badge, EventBadges } from "./badge";

const labels: Record<string, string> = { tipo_pendencia: "Pendência", acao_pje: "Ação no PJe", caixa: "Caixa", destinatario: "Destinatário", tipo_documento: "Documento", meio_comunicacao: "Meio", data_expedicao: "Expedição", prazo_texto: "Prazo", status_prazo_fatal: "Situação do prazo", prazo_fatal: "Prazo fatal", ciencia_texto: "Ciência", "processo.classe": "Classe", "processo.assunto": "Assunto", "processo.partes_texto": "Partes", "processo.unidade_judiciaria": "Unidade judiciária", ativo: "Situação" };
function show(value: unknown) { if (value === null || value === "") return "Não informado"; if (typeof value === "boolean") return value ? "Ativo" : "Resolvido"; return String(value); }
function Field({ label, value }: { label: string; value: React.ReactNode }) { return <div><dt className="text-[10px] font-extrabold tracking-[.11em] text-quiet uppercase">{label}</dt><dd className="mt-1.5 text-sm font-semibold leading-5 text-ink-soft">{value}</dd></div>; }

export function ExpedienteDrawer({ item, onClose, onRead }: { item: Expediente | null; onClose: () => void; onRead: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!item) return;
    closeRef.current?.focus();
    if (item.unread) api(`expedientes/${item.id}/read/`, { method: "POST" }).then(onRead).catch(() => {});
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    addEventListener("keydown", escape); return () => removeEventListener("keydown", escape);
  }, [item, onClose, onRead]);
  if (!item) return null;
  const event = item.latest_event;
  return <div className="fixed inset-0 z-[60] flex justify-end bg-slate-950/35 p-0 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside className="h-full w-full max-w-[680px] overflow-y-auto border-l border-rule bg-app shadow-[-16px_0_48px_var(--shadow)]" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <header className="sticky top-0 z-10 flex items-start justify-between border-b border-rule bg-[var(--shell)] px-5 py-5 backdrop-blur-xl sm:px-7"><div className="min-w-0"><p className="mb-2 text-[10px] font-extrabold tracking-[.12em] text-brand uppercase">Detalhe do expediente</p><h2 id="drawer-title" className="mb-0 truncate font-[family-name:var(--font-mono)] text-lg font-extrabold text-ink">{item.processo.numero}</h2></div><button ref={closeRef} className="grid size-10 shrink-0 cursor-pointer place-items-center rounded-xl border border-rule bg-panel text-quiet hover:bg-panel-muted hover:text-ink" onClick={onClose} aria-label="Fechar"><X size={19} /></button></header>
      <div className="space-y-4 p-5 sm:p-7"><section className="bezel-card"><div className="bezel-inner p-5"><EventBadges item={item} /><span className="mt-4 block text-[10px] font-extrabold tracking-[.12em] text-brand uppercase">{item.tipo_documento || "Expediente"}</span><strong className="mt-2 block text-xl font-extrabold leading-7 text-ink">{item.processo.assunto || "Assunto não informado"}</strong><p className="mt-3 mb-0 text-sm leading-6 text-quiet">{item.processo.partes_texto || "Partes não informadas"}</p></div></section>
      <section className="bezel-card"><div className="bezel-inner p-5"><h3 className="mb-5 text-sm font-extrabold text-ink">Prazo e ação</h3><dl className="grid grid-cols-1 gap-5 sm:grid-cols-2"><Field label="Prazo fatal" value={formatDateTime(item.prazo_fatal)} /><Field label="Prazo original" value={item.prazo_texto || "—"} /><Field label="Situação" value={<Badge tone={item.status_prazo_fatal === "em_calculo" ? "warning" : "neutral"}>{item.status_prazo_fatal_label}</Badge>} /><Field label="Ação disponível" value={item.acao_pje_label || "Nenhuma"} /></dl><p className="mt-5 mb-0 text-xs leading-5 text-quiet">A ação é apenas informativa e deve ser realizada diretamente no PJe.</p></div></section>
      <section className="bezel-card"><div className="bezel-inner p-5"><h3 className="mb-5 text-sm font-extrabold text-ink">Processo</h3><dl className="grid gap-5"><Field label="Classe" value={item.processo.classe || "—"} /><Field label="Unidade" value={item.processo.unidade_judiciaria || "—"} /><Field label="Destinatário" value={item.destinatario || "—"} /><Field label="Expedido em" value={formatDateTime(item.data_expedicao)} /><Field label="Meio" value={item.meio_comunicacao || "—"} /></dl></div></section>
      {event && Object.keys(event.changes).length > 0 && <section className="bezel-card"><div className="bezel-inner p-5"><h3 className="mb-5 text-sm font-extrabold text-ink">Última alteração <small className="ml-2 font-normal text-quiet">{formatDateTime(event.created_at)}</small></h3><div className="space-y-4">{Object.entries(event.changes).map(([key, values]) => <div key={key} className="grid gap-2 sm:grid-cols-[130px_1fr]"><strong className="text-xs text-ink-soft">{labels[key] ?? key}</strong><span className="flex flex-wrap items-center gap-2 text-xs"><del className="rounded-lg bg-danger-soft px-2 py-1 text-danger no-underline">{show(values.before)}</del><b className="text-quiet">→</b><ins className="rounded-lg bg-positive-soft px-2 py-1 text-positive no-underline">{show(values.after)}</ins></span></div>)}</div></div></section>}
      {item.ciencia_texto && <section className="bezel-card"><div className="bezel-inner p-5"><h3 className="mb-3 text-sm font-extrabold text-ink">Ciência</h3><p className="mb-0 text-sm leading-6 text-quiet">{item.ciencia_texto}</p></div></section>}</div>
    </aside>
  </div>;
}
