import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export function Panel({ children, className, innerClassName, onClick, selected, ariaLabel }: { children: ReactNode; className?: string; innerClassName?: string; onClick?: () => void; selected?: boolean; ariaLabel?: string }) {
  const styles = cn("rounded-lg border bg-card text-card-foreground shadow-sm", selected && "ring-2 ring-ring", className);
  if (onClick) return <button type="button" className={cn(styles, "w-full text-left")} onClick={onClick} aria-pressed={selected} aria-label={ariaLabel}><div className={innerClassName}>{children}</div></button>;
  return <section className={styles}><div className={innerClassName}>{children}</div></section>;
}

const tones = { blue: "bg-muted text-foreground", green: "bg-success-soft text-success", amber: "bg-warning-soft text-warning", rose: "bg-destructive/10 text-destructive", cyan: "bg-muted text-foreground", slate: "bg-muted text-muted-foreground" };

export function MetricCard({ label, value, note, icon, tone = "blue", children, className, innerClassName, onClick, selected }: { label: string; value: string | number; note: string; icon: ReactNode; tone?: keyof typeof tones; children?: ReactNode; className?: string; innerClassName?: string; onClick?: () => void; selected?: boolean }) {
  return <Panel className={cn("group transition-colors hover:bg-muted/40", className)} innerClassName={cn("flex min-h-36 flex-col p-4", innerClassName)} onClick={onClick} selected={selected} ariaLabel={label ? `Filtrar expedientes: ${label}` : undefined}>{children ?? <><div className="flex items-start justify-between gap-2"><span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</span><span className={cn("grid size-10 place-items-center rounded-md", tones[tone])}>{icon}</span></div><div className="mt-auto pt-4"><strong className="block truncate font-mono text-2xl font-semibold tabular-nums">{value}</strong><small className="mt-2 block text-xs text-muted-foreground">{note}</small></div></>}</Panel>;
}

export function PageTitle({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return <header className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>{description && <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{description}</p>}</div>{actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}</header>;
}

export function LoadingRows() { return <Panel innerClassName="space-y-2 p-4">{[1, 2, 3].map((row) => <Skeleton className="h-20 w-full" key={row} />)}</Panel>; }

export function EmptyState({ icon, title, description }: { icon: ReactNode; title: string; description: string }) {
  return <div className="px-6 py-16 text-center"><div className="mx-auto mb-4 grid size-12 place-items-center rounded-2xl border border-border bg-muted text-muted-foreground">{icon}</div><h3 className="mb-2 text-base font-extrabold text-foreground">{title}</h3><p className="mx-auto mb-0 max-w-sm text-xs text-muted-foreground sm:text-sm">{description}</p></div>;
}

export function HistoryDayHeader({ date, label, icon, id }: { date: string; label: string; icon: ReactNode; id: string }) {
  const formatted = new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Fortaleza", day: "numeric", month: "long", year: "numeric" }).format(new Date(`${date}T12:00:00-03:00`));
  return <header className="mb-4 flex items-center gap-4"><span className="grid size-10 shrink-0 place-items-center rounded-lg border border-border bg-muted text-muted-foreground">{icon}</span><h2 id={id} className="text-sm font-extrabold tracking-tight text-foreground sm:text-base">{formatted} <span className="font-medium text-muted-foreground">({label})</span></h2></header>;
}

export function Pagination({ page, pages, onPageChange, label = "Paginação" }: { page: number; pages: number; onPageChange: (page: number) => void; label?: string }) {
  if (pages <= 1) return null;
  return <nav className="mt-6 flex items-center justify-center gap-4 text-xs text-muted-foreground" aria-label={label}>
    <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>← Anterior</Button>
    <span>Página <strong className="font-mono text-foreground">{page}</strong> de <span className="font-mono">{pages}</span></span>
    <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>Próxima →</Button>
  </nav>;
}
