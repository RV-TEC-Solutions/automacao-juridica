"use client";

import { CircleNotch, DownloadSimple } from "@phosphor-icons/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { downloadPdf } from "../lib/export";
import { useNotifications } from "./notifications";

export function PdfExportButton({ path, label = "Exportar PDF", summary, count, disabled = false, analytical = false }: {
  path: string; label?: string; summary?: string; count?: number; disabled?: boolean; analytical?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const { notify } = useNotifications();

  const download = async (mode = "sintetico") => {
    setBusy(true);
    try {
      await downloadPdf(analytical ? `${path}${path.includes("?") ? "&" : "?"}mode=${mode}` : path);
      setOpen(false);
    } catch (error) {
      notify({ tone: "warning", message: error instanceof Error ? error.message : "Não foi possível gerar o PDF." });
    } finally {
      setBusy(false);
    }
  };

  return <>
    <Button type="button" variant="outline" size="icon" className="size-11 rounded-xl border-slate-300 bg-white text-slate-900 shadow-sm ring-2 ring-slate-200 transition-shadow hover:bg-slate-50 hover:shadow-md [&_svg]:!size-5"
      disabled={busy || disabled} aria-label={label} aria-busy={busy} title={busy ? "Preparando PDF…" : label} onClick={() => {
      if (count === 0) { notify({ tone: "warning", message: "Não há registros para exportar com os filtros atuais." }); return; }
      if (summary || analytical) setOpen(true); else void download();
    }}>
      {busy ? <CircleNotch weight="bold" className="animate-spin" aria-hidden="true" /> : <DownloadSimple weight="bold" aria-hidden="true" />}
    </Button>
    {(summary || analytical) && <Dialog open={open} onOpenChange={(next) => { if (!busy) setOpen(next); }}>
      <DialogContent showCloseButton={!busy}>
        <DialogHeader>
          <DialogTitle>Confirmar exportação em PDF</DialogTitle>
          <DialogDescription>{summary || "Escolha o nível de detalhe do relatório."}</DialogDescription>
        </DialogHeader>
        <p className="text-sm font-semibold text-foreground">{count ?? "Todos os"} registro{count === 1 ? "" : "s"} serão incluídos, inclusive os de outras páginas.</p>
        <DialogFooter>
          <Button type="button" variant="outline" disabled={busy} onClick={() => setOpen(false)}>Cancelar</Button>
          {analytical && <Button type="button" variant="outline" disabled={busy} onClick={() => { void download("analitico"); }}>Analítico</Button>}
          <Button type="button" disabled={busy} onClick={() => { void download(); }}>{busy ? "Preparando PDF…" : analytical ? "Sintético" : "Baixar PDF"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>}
  </>;
}
