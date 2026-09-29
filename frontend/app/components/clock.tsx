"use client";

import { Clock as ClockIcon } from "@phosphor-icons/react";
import { useEffect, useState } from "react";

export function Clock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    const update = () => setNow(new Date());
    update();
    const timer = window.setInterval(update, 60_000);
    return () => window.clearInterval(timer);
  }, []);
  const time = now ? new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Fortaleza", hour: "2-digit", minute: "2-digit" }).format(now) : "--:--";
  return <div data-testid="clock-face" className="flex h-12 items-center gap-2 rounded-md border bg-card px-4 shadow-sm"><ClockIcon size={20} className="text-muted-foreground" aria-hidden="true" /><div><strong className="block font-mono text-sm font-semibold tabular-nums">{time}</strong><span className="block text-xs text-muted-foreground">Fortaleza</span></div></div>;
}
