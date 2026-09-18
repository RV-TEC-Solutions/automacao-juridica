"use client";

import { Check, Copy, X } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { api, formatDateTime } from "../lib/api";
import type { Expediente } from "../lib/types";
import { Badge, EventBadges } from "./badge";

const labels: Record<string, string> = {
  tipo_pendencia: "Pendência",
  acao_pje: "Ação no PJe",
  caixa: "Caixa",
  destinatario: "Destinatário",
  tipo_documento: "Documento",
  meio_comunicacao: "Meio",
  data_expedicao: "Expedição",
  prazo_texto: "Prazo",
  status_prazo_fatal: "Situação do prazo",
  prazo_fatal: "Prazo fatal",
  ciencia_texto: "Ciência",
  "processo.classe": "Classe",
  "processo.assunto": "Assunto",
  "processo.partes_texto": "Partes",
  "processo.unidade_judiciaria": "Unidade judiciária",
  ativo: "Situação",
};

function show(value: unknown) {
  if (value === null || value === "") return "Não informado";
  if (typeof value === "boolean") return value ? "Ativo" : "Resolvido";
  return String(value);
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[10px] font-extrabold tracking-[.14em] text-quiet uppercase">
        {label}
      </dt>
      <dd className="mt-1 text-xs sm:text-sm font-semibold leading-relaxed text-ink-soft">
        {value}
      </dd>
    </div>
  );
}

export function ExpedienteDrawer({
  item,
  onClose,
  onRead,
}: {
  item: Expediente | null;
  onClose: () => void;
  onRead: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!item) return;
    closeRef.current?.focus();
    if (item.unread) {
      api(`expedientes/${item.id}/read/`, { method: "POST" })
        .then(onRead)
        .catch(() => {});
    }
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    addEventListener("keydown", escape);
    return () => removeEventListener("keydown", escape);
  }, [item, onClose, onRead]);

  if (!item) return null;

  const copyProcess = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(item.processo.numero);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const event = item.latest_event;

  return (
    <div
      className="fixed inset-0 z-[60] flex justify-end bg-black/40 backdrop-blur-sm transition-opacity"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside
        className="h-full w-full max-w-[680px] overflow-y-auto border-l border-rule bg-app shadow-[-16px_0_48px_var(--shadow)] flex flex-col"
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        <header className="sticky top-0 z-10 flex items-start justify-between border-b border-rule bg-[var(--shell)] px-6 py-5 backdrop-blur-xl">
          <div className="min-w-0 pr-3">
            <p className="mb-1 text-[10px] font-extrabold tracking-[.16em] text-quiet uppercase">
              Detalhe do Expediente
            </p>
            <div className="flex items-center gap-2">
              <h2
                id="drawer-title"
                className="mb-0 truncate font-[family-name:var(--font-mono)] text-lg font-extrabold text-ink"
              >
                {item.processo.numero}
              </h2>
              <button
                type="button"
                onClick={copyProcess}
                title="Copiar processo"
                aria-label="Copiar processo"
                className="grid size-7 place-items-center rounded-lg border border-rule bg-panel text-quiet transition-colors hover:bg-panel-muted hover:text-ink"
              >
                {copied ? (
                  <Check size={14} weight="bold" className="text-positive" />
                ) : (
                  <Copy size={14} />
                )}
              </button>
            </div>
          </div>

          <button
            ref={closeRef}
            className="grid size-10 shrink-0 cursor-pointer place-items-center rounded-xl border border-rule bg-panel text-quiet shadow-xs transition-colors hover:bg-panel-muted hover:text-ink"
            onClick={onClose}
            aria-label="Fechar"
            title="Fechar"
          >
            <X size={18} weight="bold" />
          </button>
        </header>

        <div className="flex-1 space-y-4 p-6">
          {/* Main summary card */}
          <section className="bezel-card">
            <div className="bezel-inner p-5 sm:p-6">
              <EventBadges item={item} />
              <span className="mt-3.5 block text-[10px] font-extrabold tracking-[.14em] text-quiet uppercase">
                {item.tipo_documento || "Expediente"}
              </span>
              <strong className="mt-1.5 block text-lg sm:text-xl font-extrabold leading-snug text-ink">
                {item.processo.assunto || "Assunto não informado"}
              </strong>
              <p className="mt-2.5 mb-0 text-xs sm:text-sm leading-relaxed text-quiet">
                {item.processo.partes_texto || "Partes não informadas"}
              </p>
            </div>
          </section>

          {/* Prazo e providência */}
          <section className="bezel-card">
            <div className="bezel-inner p-5 sm:p-6">
              <h3 className="mb-4 text-xs font-extrabold tracking-tight text-ink uppercase">
                Prazo e Ação Processual
              </h3>
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Prazo fatal" value={formatDateTime(item.prazo_fatal)} />
                <Field label="Prazo original" value={item.prazo_texto || "—"} />
                <Field
                  label="Situação do prazo"
                  value={
                    <Badge tone={item.status_prazo_fatal === "em_calculo" ? "warning" : "neutral"}>
                      {item.status_prazo_fatal_label}
                    </Badge>
                  }
                />
                <Field label="Ação disponível" value={item.acao_pje_label || "Nenhuma"} />
              </dl>
              <div className="mt-4 pt-3 border-t border-rule/60">
                <p className="mb-0 text-[11px] text-quiet leading-relaxed">
                  As ações processuais são informativas e devem ser executadas diretamente na respectiva plataforma do PJe.
                </p>
              </div>
            </div>
          </section>

          {/* Processo details */}
          <section className="bezel-card">
            <div className="bezel-inner p-5 sm:p-6">
              <h3 className="mb-4 text-xs font-extrabold tracking-tight text-ink uppercase">
                Dados do Processo
              </h3>
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Classe" value={item.processo.classe || "—"} />
                <Field label="Unidade Judiciária" value={item.processo.unidade_judiciaria || "—"} />
                <Field label="Destinatário" value={item.destinatario || "—"} />
                <Field label="Expedido em" value={formatDateTime(item.data_expedicao)} />
                <Field label="Meio de Comunicação" value={item.meio_comunicacao || "—"} />
                <Field
                  label="Tribunal de Origem"
                  value={item.source ? `${item.source.system} · ${item.source.tribunal}` : "—"}
                />
              </dl>
            </div>
          </section>

          {/* Alterações detectadas */}
          {event && Object.keys(event.changes).length > 0 && (
            <section className="bezel-card">
              <div className="bezel-inner p-5 sm:p-6">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="mb-0 text-xs font-extrabold tracking-tight text-ink uppercase">
                    Última Alteração Identificada
                  </h3>
                  <small className="font-mono text-[11px] text-quiet">
                    {formatDateTime(event.created_at)}
                  </small>
                </div>
                <div className="space-y-3">
                  {Object.entries(event.changes).map(([key, values]) => (
                    <div
                      key={key}
                      className="grid gap-1.5 rounded-xl border border-rule bg-panel-muted/50 p-3 sm:grid-cols-[120px_1fr] sm:items-center"
                    >
                      <strong className="text-xs font-bold text-ink-soft">
                        {labels[key] ?? key}
                      </strong>
                      <span className="flex flex-wrap items-center gap-2 text-xs">
                        <del className="rounded-md border border-danger/30 bg-danger-soft px-2 py-0.5 text-danger no-underline font-medium">
                          {show(values.before)}
                        </del>
                        <b className="text-quiet">→</b>
                        <ins className="rounded-md border border-positive/30 bg-positive-soft px-2 py-0.5 text-positive no-underline font-semibold">
                          {show(values.after)}
                        </ins>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Ciência */}
          {item.ciencia_texto && (
            <section className="bezel-card">
              <div className="bezel-inner p-5 sm:p-6">
                <h3 className="mb-2 text-xs font-extrabold tracking-tight text-ink uppercase">
                  Registro de Ciência
                </h3>
                <p className="mb-0 text-xs sm:text-sm leading-relaxed text-quiet">
                  {item.ciencia_texto}
                </p>
              </div>
            </section>
          )}
        </div>
      </aside>
    </div>
  );
}
