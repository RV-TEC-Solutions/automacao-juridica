"use client";

import { ArrowSquareOut, Check, Copy } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { api } from "../lib/api";
import type { DjenCommunication } from "../lib/types";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-lg border bg-card p-5"><h3 className="mb-4 text-xs font-extrabold uppercase tracking-wide text-muted-foreground">{title}</h3>{children}</section>;
}

export function DjenDrawer({ item, onClose, onRead }: { item: DjenCommunication | null; onClose: () => void; onRead: (item: DjenCommunication) => void }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!item?.unread) return;
    api<DjenCommunication>(`djen/communications/${item.id}/read/`, { method: "POST" }).then(onRead).catch(() => {});
  }, [item, onRead]);
  if (!item) return null;
  const copy = () => {
    if (!navigator.clipboard) return;
    void navigator.clipboard.writeText(item.processo.numero);
    setCopied(true); window.setTimeout(() => setCopied(false), 1500);
  };
  return <Sheet open onOpenChange={(open) => { if (!open) onClose(); }}>
    <SheetContent className="max-w-3xl overflow-y-auto bg-background">
      <SheetHeader className="sticky top-0 z-10 bg-background/95 pr-16 backdrop-blur">
        <span className="text-xs font-extrabold uppercase tracking-wide text-muted-foreground">Publicação DJEN</span>
        <div className="flex items-center gap-2"><SheetTitle className="truncate font-mono">{item.processo.numero}</SheetTitle><Button variant="outline" size="icon-sm" onClick={copy} aria-label="Copiar número do processo">{copied ? <Check className="text-success" /> : <Copy />}</Button></div>
      </SheetHeader>
      <div className="space-y-4 p-6">
        <Section title="Identificação">
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            <div><dt className="text-xs font-semibold text-muted-foreground">Tribunal</dt><dd className="mt-1 font-bold">{item.tribunal}</dd></div>
            <div><dt className="text-xs font-semibold text-muted-foreground">Órgão</dt><dd className="mt-1 font-medium">{item.orgao || "—"}</dd></div>
            <div><dt className="text-xs font-semibold text-muted-foreground">Tipo</dt><dd className="mt-1 font-medium">{item.tipo_comunicacao || "—"}</dd></div>
            <div><dt className="text-xs font-semibold text-muted-foreground">Disponibilização</dt><dd className="mt-1 font-medium">{new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(new Date(`${item.data_disponibilizacao}T00:00:00Z`))}</dd></div>
            <div><dt className="text-xs font-semibold text-muted-foreground">Classe</dt><dd className="mt-1 font-medium">{item.nome_classe || "—"}</dd></div>
            <div><dt className="text-xs font-semibold text-muted-foreground">Comunicação</dt><dd className="mt-1 font-mono">#{item.numero_comunicacao}</dd></div>
          </dl>
          {item.link_inteiro_teor && <a href={item.link_inteiro_teor} target="_blank" rel="noreferrer" className="mt-5 inline-flex min-h-10 items-center gap-2 rounded-md border px-4 text-sm font-bold hover:bg-muted">Abrir inteiro teor <ArrowSquareOut /></a>}
        </Section>
        <Section title="Partes e advogados">
          <div className="grid gap-6 sm:grid-cols-2"><div><h4 className="mb-2 text-xs font-bold text-muted-foreground">Partes</h4><ul className="space-y-2 text-sm">{item.recipients.map((person, index) => <li key={`${person.name}-${index}`}><strong>{person.name}</strong>{person.pole && <span className="ml-2 text-xs text-muted-foreground">{person.pole}</span>}</li>)}</ul></div><div><h4 className="mb-2 text-xs font-bold text-muted-foreground">Representação</h4><ul className="space-y-2 text-sm">{item.attorneys.map((lawyer, index) => <li key={`${lawyer.name}-${index}`}><strong>{lawyer.name}</strong><span className="block text-xs text-muted-foreground">Identificação omitida na demonstração</span></li>)}</ul></div></div>
        </Section>
        <Section title="Texto publicado"><p className="whitespace-pre-wrap text-sm leading-7 text-foreground">{item.texto || "Texto não informado pela fonte."}</p></Section>
      </div>
    </SheetContent>
  </Sheet>;
}
