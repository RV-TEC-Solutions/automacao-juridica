"use client";

import { Popover } from "@base-ui/react/popover";
import { CaretDown, MagnifyingGlass, X } from "@phosphor-icons/react";
import { type ReactNode, useId, useState } from "react";
import { Button } from "./button";
import { Input } from "./input";
import { Label } from "./label";

export type MultiSelectOption = { value: string; label: string };
const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");

export function MultiSelect({ name, label, options, initialSelection = [], onDirty, placeholder, searchLabel, emptyMessage, feedback }: {
  name: string; label: string; options: MultiSelectOption[]; initialSelection?: string[];
  onDirty: () => void; placeholder: string; searchLabel: string; emptyMessage: string; feedback?: ReactNode;
}) {
  const id = useId();
  const [selected, setSelected] = useState(() => new Set(initialSelection));
  const [search, setSearch] = useState("");
  const visible = options.filter((option) => normalize(option.label).includes(normalize(search.trim())));
  const change = (values: Set<string>) => { setSelected(values); onDirty(); };
  const toggle = (value: string) => { const next = new Set(selected); if (next.has(value)) next.delete(value); else next.add(value); change(next); };

  return <div className="min-w-0 space-y-2">
    <Label id={`${id}-label`} htmlFor={id} className="text-xs uppercase tracking-wide">{label}</Label>
    {[...selected].map((value) => <input key={value} type="hidden" name={name} value={value} />)}
    <Popover.Root onOpenChange={() => setSearch("")}>
      <Popover.Trigger id={id} aria-labelledby={`${id}-label ${id}-value`} render={<Button type="button" variant="outline" className="w-full justify-between font-normal" />}>
        <span id={`${id}-value`} className="truncate">{selected.size ? `${selected.size} selecionado${selected.size === 1 ? "" : "s"}` : placeholder}</span>
        <CaretDown aria-hidden="true" className="text-muted-foreground" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner sideOffset={6} align="start" className="z-50">
          <Popover.Popup aria-labelledby={`${id}-label`} className="w-[max(var(--anchor-width),20rem)] max-w-[calc(100vw-2rem)] overflow-hidden rounded-lg border bg-popover text-popover-foreground shadow-lg outline-none">
            <div className="relative border-b p-3">
              <MagnifyingGlass aria-hidden="true" className="absolute left-6 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input aria-label={searchLabel} placeholder={searchLabel} value={search} onChange={(event) => setSearch(event.target.value)} onInput={(event) => event.stopPropagation()} onKeyDown={(event) => {
                if (event.key === "Enter") event.preventDefault();
                if (event.key === "ArrowDown") { event.preventDefault(); event.currentTarget.closest('[role="dialog"]')?.querySelector<HTMLInputElement>('input[type="checkbox"]')?.focus(); }
              }} className="pl-9" />
            </div>
            <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
              <Button type="button" variant="ghost" size="sm" disabled={!visible.length || visible.every((option) => selected.has(option.value))} onClick={() => change(new Set([...selected, ...visible.map((option) => option.value)]))}>{search.trim() ? "Selecionar resultados" : "Selecionar todos"}</Button>
              <Button type="button" variant="ghost" size="sm" disabled={!selected.size} onClick={() => change(new Set())}>Limpar {label.toLocaleLowerCase("pt-BR")}</Button>
            </div>
            {feedback}
            <div className="max-h-60 overflow-y-auto overscroll-contain p-2" role="group" aria-label={`Opções de ${label.toLocaleLowerCase("pt-BR")}`}>
              {visible.map((option) => <label key={option.value} className={`flex min-h-11 cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors hover:bg-muted focus-within:ring-2 focus-within:ring-inset focus-within:ring-ring ${selected.has(option.value) ? "bg-accent text-accent-foreground" : ""}`}>
                <input type="checkbox" checked={selected.has(option.value)} onChange={() => toggle(option.value)} className="size-4 shrink-0 accent-primary" />
                <span className="min-w-0 break-words">{option.label}</span>
              </label>)}
              {!visible.length && !feedback && <p className="px-3 py-5 text-sm text-muted-foreground" role="status">{search.trim() ? "Nenhum resultado para essa busca." : emptyMessage}</p>}
            </div>
            <p className="border-t px-4 py-3 text-xs text-muted-foreground" aria-live="polite">{selected.size} selecionado{selected.size === 1 ? "" : "s"} · Sem seleção, inclui todos.</p>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
    {selected.size > 0 && <div className="flex max-h-28 flex-wrap gap-1.5 overflow-y-auto" aria-label={`${label} selecionados`}>
      {[...selected].map((value) => {
        const text = options.find((option) => option.value === value)?.label ?? `${label === "Clientes" ? "Cliente" : "Fonte"} #${value}`;
        return <button key={value} type="button" aria-label={`Remover ${text}`} onClick={() => toggle(value)} className="inline-flex max-w-full items-center gap-1.5 rounded-md border bg-muted px-2 py-1 text-xs text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <span className="truncate">{text}</span><X aria-hidden="true" className="size-3 shrink-0" />
        </button>;
      })}
    </div>}
  </div>;
}
