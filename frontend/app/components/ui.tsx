import type { ReactNode } from "react";
import { CheckCircle, Info, WarningCircle } from "@phosphor-icons/react";

export function BezelCard({
  children,
  className = "",
  innerClassName = "",
  onClick,
  selected = false,
  ariaLabel,
}: {
  children: ReactNode;
  className?: string;
  innerClassName?: string;
  onClick?: () => void;
  selected?: boolean;
  ariaLabel?: string;
}) {
  const classes = `bezel-card ${onClick ? "cursor-pointer text-left" : ""} ${selected ? "outline-2 outline-offset-2 outline-black" : ""} ${className}`;
  const content = <div className={`bezel-inner ${innerClassName}`}>{children}</div>;

  if (onClick) {
    return (
      <button type="button" className={classes} onClick={onClick} aria-pressed={selected} aria-label={ariaLabel}>
        {content}
      </button>
    );
  }

  return (
    <section className={classes}>{content}</section>
  );
}

const tones = {
  blue: "border-zinc-300 dark:border-zinc-700 bg-panel-muted text-ink",
  green: "border-positive/30 bg-positive-soft text-positive",
  amber: "border-caution/30 bg-caution-soft text-caution",
  rose: "border-danger/30 bg-danger-soft text-danger",
  cyan: "border-info/30 bg-info-soft text-info",
  slate: "border-rule bg-panel-muted text-ink-soft",
};

export function MetricCard({
  label,
  value,
  note,
  icon,
  tone = "blue",
  children,
  className = "",
  innerClassName = "",
  onClick,
  selected,
}: {
  label: string;
  value: string | number;
  note: string;
  icon: ReactNode;
  tone?: keyof typeof tones;
  children?: ReactNode;
  className?: string;
  innerClassName?: string;
  onClick?: () => void;
  selected?: boolean;
}) {
  return (
    <BezelCard
      className={`group transition-all duration-200 hover:-translate-y-0.5 ${className}`}
      innerClassName={`flex min-h-[148px] flex-col p-4 sm:p-5 ${innerClassName}`}
      onClick={onClick}
      selected={selected}
      ariaLabel={label ? `Filtrar expedientes: ${label}` : undefined}
    >
      {children ?? (
        <>
          <div className="flex items-start justify-between gap-3">
            <span className="text-[10px] font-extrabold tracking-[.14em] text-quiet uppercase">
              {label}
            </span>
            <span className={`grid size-9 place-items-center rounded-xl border shadow-xs transition-transform group-hover:scale-105 ${tones[tone]}`}>
              {icon}
            </span>
          </div>
          <div className="mt-auto pt-4">
            <strong
              className="block truncate font-[family-name:var(--font-mono)] text-2xl font-extrabold tracking-[-.05em] tabular-nums text-ink sm:text-[28px]"
              title={String(value)}
            >
              {value}
            </strong>
            <small className="mt-1 block text-xs font-medium text-quiet leading-tight">
              {note}
            </small>
          </div>
        </>
      )}
    </BezelCard>
  );
}

export function PageTitle({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        {eyebrow && (
          <p className="mb-1.5 text-[10px] font-extrabold tracking-[.18em] text-quiet uppercase">
            {eyebrow}
          </p>
        )}
        <h1 className="mb-1 text-[clamp(1.75rem,2.8vw,2.35rem)] font-extrabold tracking-tight leading-tight text-ink">
          {title}
        </h1>
        {description && (
          <p className="mb-0 max-w-2xl text-xs sm:text-sm leading-relaxed text-quiet">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2.5">{actions}</div>}
    </header>
  );
}

export function Feedback({
  children,
  tone = "danger",
  action,
}: {
  children: ReactNode;
  tone?: "danger" | "success" | "warning" | "info";
  action?: ReactNode;
}) {
  const styles = {
    success: {
      wrap: "border-positive/25 bg-positive-soft text-positive",
      Icon: CheckCircle,
    },
    warning: {
      wrap: "border-caution/25 bg-caution-soft text-caution",
      Icon: WarningCircle,
    },
    danger: {
      wrap: "border-danger/25 bg-danger-soft text-danger",
      Icon: WarningCircle,
    },
    info: {
      wrap: "border-info/25 bg-info-soft text-info",
      Icon: Info,
    },
  }[tone];

  const IconComponent = styles.Icon;

  return (
    <div
      className={`mb-5 flex items-center justify-between gap-4 rounded-xl border p-4 text-xs sm:text-sm font-semibold shadow-xs ${styles.wrap}`}
      role="alert"
    >
      <div className="flex items-center gap-2.5">
        <IconComponent size={19} weight="duotone" className="shrink-0" />
        <span>{children}</span>
      </div>
      {action}
    </div>
  );
}

export function LoadingRows() {
  return (
    <div className="bezel-card">
      <div className="bezel-inner divide-y divide-rule overflow-hidden">
        {[1, 2, 3].map((row) => (
          <div
            className="h-24 animate-pulse bg-[linear-gradient(90deg,var(--panel),var(--panel-muted),var(--panel))] bg-[length:200%]"
            key={row}
          />
        ))}
      </div>
    </div>
  );
}
