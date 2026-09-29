"use client";

import { WarningCircle } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function DiscardCollectionDialog({ open, busy, onClose, onConfirm }: { open: boolean; busy: boolean; onClose: () => void; onConfirm: () => void }) {
  return <Dialog open={open} onOpenChange={(nextOpen) => { if (!nextOpen && !busy) onClose(); }}>
    <DialogContent role="alertdialog" showCloseButton={!busy}>
      <DialogHeader>
        <span className="grid size-10 place-items-center rounded-md bg-destructive/10 text-destructive"><WarningCircle size={20} weight="duotone" aria-hidden="true" /></span>
        <DialogTitle>Descartar a coleta de hoje?</DialogTitle>
        <DialogDescription>Os expedientes novos serão excluídos e as alterações e resoluções de hoje serão desfeitas. A pipeline e o histórico de orquestração do dia também serão limpos.</DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button autoFocus variant="outline" disabled={busy} onClick={onClose}>Cancelar</Button>
        <Button variant="destructive" disabled={busy} onClick={onConfirm}>{busy ? "Descartando…" : "Descartar coleta"}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>;
}
