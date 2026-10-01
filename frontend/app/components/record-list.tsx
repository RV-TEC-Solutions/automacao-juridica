import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function RecordList({ children, className }: { children: ReactNode; className?: string }) {
  return <ul className={cn("overflow-hidden rounded-lg border border-border bg-card divide-y divide-border", className)}>{children}</ul>;
}
