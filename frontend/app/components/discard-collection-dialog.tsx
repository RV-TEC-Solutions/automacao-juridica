"use client";

import { WarningCircle } from "@phosphor-icons/react";
import { useEffect, useRef } from "react";

export function DiscardCollectionDialog({
  open, busy, onClose, onConfirm,
}: {
  open: boolean;
  busy: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    cancelRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, onClose, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] grid place-items-center bg-black/40 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
      <section role="alertdialog" aria-modal="true" aria-labelledby="discard-dialog-title" aria-describedby="discard-dialog-description" className="w-full max-w-md rounded-2xl border border-danger/30 bg-app shadow-xl">
        <div className="p-5 sm:p-6">
          <span className="grid size-10 place-items-center rounded-xl border border-danger/30 bg-danger-soft text-danger"><WarningCircle size={21} weight="duotone" aria-hidden="true" /></span>
          <h2 id="discard-dialog-title" className="mb-2 mt-4 text-lg font-extrabold tracking-tight text-ink">Descartar a coleta de hoje?</h2>
          <p id="discard-dialog-description" className="mb-0 text-sm leading-relaxed text-quiet">Os expedientes novos serão excluídos e as alterações e resoluções de hoje serão desfeitas. A pipeline e o histórico de orquestração do dia também serão limpos.</p>
        </div>
        <footer className="flex flex-col-reverse gap-2 border-t border-rule bg-panel-muted/45 p-4 sm:flex-row sm:justify-end">
          <button ref={cancelRef} type="button" className="button-secondary px-4 py-2 text-xs font-bold" disabled={busy} onClick={onClose}>Cancelar</button>
          <button type="button" className="button-secondary border-danger/30 bg-danger-soft px-4 py-2 text-xs font-bold text-danger hover:border-danger hover:bg-danger hover:text-white" disabled={busy} onClick={onConfirm}>{busy ? "Descartando…" : "Descartar coleta"}</button>
        </footer>
      </section>
    </div>
  );
}
