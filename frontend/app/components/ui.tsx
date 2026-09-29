import type { ReactNode } from "react";
import { CheckCircle, Info, WarningCircle } from "@phosphor-icons/react";
import { Alert } from "@/components/ui/alert";
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

export function Feedback({ children, tone = "danger", action }: { children: ReactNode; tone?: "danger" | "success" | "warning" | "info"; action?: ReactNode }) {
  const config = { success: ["success", CheckCircle], warning: ["warning", WarningCircle], danger: ["destructive", WarningCircle], info: ["default", Info] }[tone] as ["success" | "warning" | "destructive" | "default", typeof Info];
  const Icon = config[1];
  return <Alert variant={config[0]} className="mb-4"><Icon size={18} className="shrink-0" /><div className="min-w-0 flex-1 text-sm font-medium">{children}</div>{action}</Alert>;
}

export function LoadingRows() { return <Panel innerClassName="space-y-2 p-4">{[1, 2, 3].map((row) => <Skeleton className="h-20 w-full" key={row} />)}</Panel>; }

export function Pagination({ page, pages, onPageChange, label = "Paginação" }: { page: number; pages: number; onPageChange: (page: number) => void; label?: string }) {
  if (pages <= 1) return null;
  return <nav className="mt-6 flex items-center justify-center gap-4 text-xs text-muted-foreground" aria-label={label}>
    <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>← Anterior</Button>
    <span>Página <strong className="font-mono text-foreground">{page}</strong> de <span className="font-mono">{pages}</span></span>
    <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>Próxima →</Button>
  </nav>;
}
