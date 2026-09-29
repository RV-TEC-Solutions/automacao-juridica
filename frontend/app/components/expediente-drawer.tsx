"use client";

import { Check, Copy } from "@phosphor-icons/react";
import { type ReactNode, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
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

function Field({ label, value }: { label: string; value: ReactNode }) {
  return <div><dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</dt><dd className="mt-2 text-sm font-medium leading-6 text-foreground">{value}</dd></div>;
}

function DetailSection({ title, children }: { title: string; children: ReactNode }) {
  return <section className="rounded-lg border bg-card p-6"><h3 className="mb-4 text-xs font-semibold uppercase tracking-wide">{title}</h3>{children}</section>;
}

export function ExpedienteDrawer({ item, onClose, onRead }: { item: Expediente | null; onClose: () => void; onRead: () => void }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!item?.unread) return;
    api(`expedientes/${item.id}/read/`, { method: "POST" }).then(onRead).catch(() => {});
  }, [item, onRead]);

  if (!item) return null;
  const event = item.latest_event;

  const copyProcess = () => {
    if (!navigator.clipboard) return;
    void navigator.clipboard.writeText(item.processo.numero);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return <Sheet open onOpenChange={(open) => { if (!open) onClose(); }}>
    <SheetContent className="max-w-2xl overflow-y-auto bg-background">
      <SheetHeader className="sticky top-0 z-10 bg-background/95 pr-16 backdrop-blur">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Detalhe do expediente</span>
        <div className="flex items-center gap-2">
          <SheetTitle className="truncate font-mono">{item.processo.numero}</SheetTitle>
          <Button variant="outline" size="icon-sm" onClick={copyProcess} aria-label="Copiar processo" title="Copiar processo">
            {copied ? <Check className="text-success" weight="bold" /> : <Copy />}
          </Button>
        </div>
      </SheetHeader>

      <div className="space-y-4 p-6">
        <section className="rounded-lg border bg-card p-6">
          <EventBadges item={item} />
          <span className="mt-4 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">{item.tipo_documento || "Expediente"}</span>
          <strong className="mt-2 block text-xl font-semibold leading-6">{item.processo.assunto || "Assunto não informado"}</strong>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.processo.partes_texto || "Partes não informadas"}</p>
        </section>

        <DetailSection title="Prazo e ação processual">
          <dl className="grid gap-4 sm:grid-cols-2">
            <Field label="Prazo fatal" value={formatDateTime(item.prazo_fatal)} />
            <Field label="Prazo original" value={item.prazo_texto || "—"} />
            <Field label="Situação do prazo" value={<Badge tone={item.status_prazo_fatal === "em_calculo" ? "warning" : "neutral"}>{item.status_prazo_fatal_label}</Badge>} />
            <Field label="Ação disponível" value={item.acao_pje_label || "Nenhuma"} />
          </dl>
          <p className="mt-4 border-t pt-4 text-xs leading-6 text-muted-foreground">As ações processuais são informativas e devem ser executadas diretamente na respectiva plataforma do PJe.</p>
        </DetailSection>

        <DetailSection title="Dados do processo">
          <dl className="grid gap-4 sm:grid-cols-2">
            <Field label="Classe" value={item.processo.classe || "—"} />
            <Field label="Unidade judiciária" value={item.processo.unidade_judiciaria || "—"} />
            <Field label="Destinatário" value={item.destinatario || "—"} />
            <Field label="Expedido em" value={formatDateTime(item.data_expedicao)} />
            <Field label="Meio de comunicação" value={item.meio_comunicacao || "—"} />
            <Field label="Tribunal de origem" value={item.source ? `${item.source.system} · ${item.source.tribunal}` : "—"} />
          </dl>
        </DetailSection>

        {event && Object.keys(event.changes).length > 0 && <DetailSection title="Última alteração identificada">
          <p className="mb-4 font-mono text-xs text-muted-foreground">{formatDateTime(event.created_at)}</p>
          <div className="space-y-2">{Object.entries(event.changes).map(([key, values]) => <div key={key} className="grid gap-2 rounded-md border bg-muted/50 p-4 sm:grid-cols-2"><strong className="text-xs font-semibold">{labels[key] ?? key}</strong><span className="flex flex-wrap items-center gap-2 text-xs"><del className="rounded-md bg-destructive/10 px-2 py-2 text-destructive no-underline">{show(values.before)}</del><b className="text-muted-foreground">→</b><ins className="rounded-md bg-success-soft px-2 py-2 text-success no-underline">{show(values.after)}</ins></span></div>)}</div>
        </DetailSection>}

        {item.ciencia_texto && <DetailSection title="Registro de ciência"><p className="text-sm leading-6 text-muted-foreground">{item.ciencia_texto}</p></DetailSection>}
      </div>
    </SheetContent>
  </Sheet>;
}
