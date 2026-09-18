"use client";

import { useEffect, useRef } from "react";

import { api, formatDateTime } from "../lib/api";
import type { Expediente } from "../lib/types";
import { Badge, EventBadges } from "./badge";
import { Icon } from "./icons";

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

  useEffect(() => {
    if (!item) return;

    closeRef.current?.focus();
    document.body.classList.add("drawer-open");
    if (item.unread) {
      api(`expedientes/${item.id}/read/`, { method: "POST" }).then(onRead).catch(() => {});
    }

    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    addEventListener("keydown", escape);

    return () => {
      removeEventListener("keydown", escape);
      document.body.classList.remove("drawer-open");
    };
  }, [item, onClose, onRead]);

  if (!item) return null;
  const event = item.latest_event;

  return (
    <div
      className="fixed inset-0 z-[60] flex justify-end bg-overlay backdrop-blur-sm"
      role="presentation"
      onMouseDown={(mouseEvent) => {
        if (mouseEvent.target === mouseEvent.currentTarget) onClose();
      }}
    >
      <aside className="h-full w-full max-w-[600px] overflow-auto border-l border-line-strong bg-surface shadow-[-18px_0_60px_var(--panel-shadow)]" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        <header className="sticky top-0 z-[2] flex justify-between border-b border-line bg-topbar-solid px-[22px] pt-5 pb-4 backdrop-blur-[12px] max-[760px]:px-[18px]">
          <div>
            <h2 id="drawer-title" className="mb-0 text-[21px]">{item.processo.numero}</h2>
          </div>
          <button ref={closeRef} className="grid cursor-pointer place-items-center rounded-md border-0 bg-transparent p-[7px] text-inherit transition-[background-color,border-color,color,opacity] duration-[160ms] hover:bg-white/10" onClick={onClose} aria-label="Fechar">
            <Icon name="close" />
          </button>
        </header>

        <div className="px-[22px] pt-5 pb-12 max-[760px]:px-[18px]">
          <EventBadges item={item} />
          <section className="border-b border-line py-5">
            <span className="text-[11px] font-bold text-accent uppercase">{item.tipo_documento || "Expediente"}</span>
            <strong className="my-[7px] block text-[20px]">{item.processo.assunto || "Assunto não informado"}</strong>
            <p className="mb-0 leading-[1.55] text-muted">{item.processo.partes_texto || "Partes não informadas"}</p>
          </section>

          <section className="border-b border-line py-5">
            <h3 className="mb-[13px] text-[15px] font-[650]">Prazo e ação</h3>
            <dl className="m-0 grid grid-cols-2 gap-4 max-[760px]:grid-cols-1">
              <div className="flex flex-col gap-1">
                <dt className="text-[10px] font-bold tracking-[.06em] text-muted uppercase">Prazo fatal</dt>
                <dd className="m-0 text-[13px] font-[550] text-text-soft">{formatDateTime(item.prazo_fatal)}</dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-[10px] font-bold tracking-[.06em] text-muted uppercase">Prazo original</dt>
                <dd className="m-0 text-[13px] font-[550] text-text-soft">{item.prazo_texto || "—"}</dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-[10px] font-bold tracking-[.06em] text-muted uppercase">Situação</dt>
                <dd className="m-0 text-[13px] font-[550] text-text-soft">
                  <Badge tone={item.status_prazo_fatal === "em_calculo" ? "warning" : "neutral"}>
                    {item.status_prazo_fatal_label}
                  </Badge>
                </dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-[10px] font-bold tracking-[.06em] text-muted uppercase">Ação disponível</dt>
                <dd className="m-0 text-[13px] font-[550] text-text-soft">{item.acao_pje_label || "Nenhuma"}</dd>
              </div>
            </dl>
            <p className="mt-[14px] mb-0 text-[11px] leading-[1.55] text-muted">A ação é apenas informativa e deve ser realizada diretamente no PJe.</p>
          </section>

          <section className="border-b border-line py-5">
            <h3 className="mb-[13px] text-[15px] font-[650]">Processo</h3>
            <dl className="grid gap-[13px]">
              <div className="flex flex-col gap-1">
                <dt className="text-[10px] font-bold tracking-[.06em] text-muted uppercase">Classe</dt>
                <dd className="m-0 text-[13px] font-[550] text-text-soft">{item.processo.classe || "—"}</dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-[10px] font-bold tracking-[.06em] text-muted uppercase">Unidade</dt>
                <dd className="m-0 text-[13px] font-[550] text-text-soft">{item.processo.unidade_judiciaria || "—"}</dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-[10px] font-bold tracking-[.06em] text-muted uppercase">Destinatário</dt>
                <dd className="m-0 text-[13px] font-[550] text-text-soft">{item.destinatario || "—"}</dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-[10px] font-bold tracking-[.06em] text-muted uppercase">Expedido em</dt>
                <dd className="m-0 text-[13px] font-[550] text-text-soft">{formatDateTime(item.data_expedicao)}</dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-[10px] font-bold tracking-[.06em] text-muted uppercase">Meio</dt>
                <dd className="m-0 text-[13px] font-[550] text-text-soft">{item.meio_comunicacao || "—"}</dd>
              </div>
            </dl>
          </section>

          {event && Object.keys(event.changes).length > 0 && (
            <section className="border-b border-line py-5">
              <h3 className="mb-[13px] text-[15px] font-[650]">
                Última alteração <small className="ml-[7px] text-[10px] font-normal text-muted">{formatDateTime(event.created_at)}</small>
              </h3>
              <div className="grid gap-[13px]">
                {Object.entries(event.changes).map(([key, values]) => (
                  <div key={key} className="grid grid-cols-[125px_1fr] gap-2.5 max-[760px]:grid-cols-1">
                    <strong className="text-[11px]">{labels[key] ?? key}</strong>
                    <span className="flex min-w-0 items-center gap-[7px]">
                      <del className="overflow-wrap-anywhere rounded bg-red-soft px-1.5 py-1 text-[11px] text-red no-underline">{show(values.before)}</del>
                      <b>→</b>
                      <ins className="overflow-wrap-anywhere rounded bg-green-soft px-1.5 py-1 text-[11px] text-green no-underline">{show(values.after)}</ins>
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {item.ciencia_texto && (
            <section className="border-b border-line py-5">
              <h3 className="mb-[13px] text-[15px] font-[650]">Ciência</h3>
              <p className="mb-0 leading-[1.55] text-muted">{item.ciencia_texto}</p>
            </section>
          )}
        </div>
      </aside>
    </div>
  );
}
