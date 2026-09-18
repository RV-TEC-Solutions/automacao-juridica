import type { ReactNode } from "react";

export function BezelCard({ children, className = "", innerClassName = "" }: { children: ReactNode; className?: string; innerClassName?: string }) {
  return <section className={`bezel-card ${className}`}><div className={`bezel-inner ${innerClassName}`}>{children}</div></section>;
}

const tones = {
  blue: "border-brand/25 bg-brand-soft text-brand",
  green: "border-positive/25 bg-positive-soft text-positive",
  amber: "border-caution/25 bg-caution-soft text-caution",
  rose: "border-danger/25 bg-danger-soft text-danger",
  cyan: "border-info/25 bg-info-soft text-info",
  slate: "border-rule bg-panel-muted text-ink-soft",
};

export function MetricCard({ label, value, note, icon, tone = "blue" }: { label: string; value: string | number; note: string; icon: ReactNode; tone?: keyof typeof tones }) {
  return <BezelCard innerClassName="flex min-h-[145px] flex-col p-4 sm:p-5"><div className="flex items-start justify-between gap-3"><span className="text-[10px] font-extrabold tracking-[.12em] text-quiet uppercase">{label}</span><span className={`grid size-9 place-items-center rounded-xl border ${tones[tone]}`}>{icon}</span></div><div className="mt-auto"><strong className="block truncate font-[family-name:var(--font-mono)] text-2xl font-extrabold tracking-[-.06em] text-ink sm:text-[28px]" title={String(value)}>{value}</strong><small className="mt-1 block text-xs font-medium text-quiet">{note}</small></div></BezelCard>;
}

export function PageTitle({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode }) {
  return <header className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div>{eyebrow && <p className="mb-2 text-[10px] font-extrabold tracking-[.14em] text-brand uppercase">{eyebrow}</p>}<h1 className="mb-2 text-[clamp(1.8rem,3vw,2.45rem)] font-extrabold leading-none text-ink">{title}</h1>{description && <p className="mb-0 max-w-2xl text-sm leading-6 text-quiet">{description}</p>}</div>{actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}</header>;
}

export function Feedback({ children, tone = "danger", action }: { children: ReactNode; tone?: "danger" | "success" | "warning"; action?: ReactNode }) {
  const appearance = tone === "success" ? "border-positive/25 bg-positive-soft text-positive" : tone === "warning" ? "border-caution/25 bg-caution-soft text-caution" : "border-danger/25 bg-danger-soft text-danger";
  return <div className={`mb-4 flex items-center justify-between gap-4 rounded-xl border px-4 py-3 text-sm ${appearance}`} role="alert"><span>{children}</span>{action}</div>;
}

export function LoadingRows() { return <div className="bezel-card"><div className="bezel-inner divide-y divide-rule overflow-hidden">{[1, 2, 3].map((row) => <div className="h-24 animate-pulse bg-[linear-gradient(90deg,var(--panel),var(--panel-muted),var(--panel))] bg-[length:200%]" key={row} />)}</div></div>; }
