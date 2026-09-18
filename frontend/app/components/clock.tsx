"use client";

import { useEffect, useState } from "react";

export function Clock() {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    const first = setTimeout(() => setNow(new Date()), 0);
    const timer = setInterval(() => setNow(new Date()), 1000);

    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, []);

  if (!now) return <div className="relative size-10 rounded-xl border border-rule bg-panel-muted" />;

  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Fortaleza",
    hour: "numeric",
    minute: "numeric",
    second: "numeric",
    hour12: false,
  }).formatToParts(now);
  const value = (type: string) => Number(parts.find((part) => part.type === type)?.value ?? 0);
  const hour = value("hour");
  const minute = value("minute");
  const second = value("second");

  return (
    <div className="flex items-center gap-3 rounded-xl border border-rule bg-panel px-3 py-2 shadow-sm">
      <div data-testid="clock-face" className="relative size-10 rounded-full border border-rule bg-panel-muted before:absolute before:left-1/2 before:h-full before:w-px before:bg-rule before:content-[''] after:absolute after:top-1/2 after:h-px after:w-full after:bg-rule after:content-['']" aria-hidden="true">
        <i className="absolute z-[2] bottom-1/2 left-[calc(50%-1px)] h-3 w-0.5 origin-bottom rounded-sm bg-ink" style={{ transform: `rotate(${hour * 30 + minute / 2}deg)` }} />
        <i className="absolute z-[2] bottom-1/2 left-[calc(50%-1px)] h-[15px] w-0.5 origin-bottom rounded-sm bg-ink" style={{ transform: `rotate(${minute * 6}deg)` }} />
        <i className="absolute z-[2] bottom-1/2 left-[calc(50%-1px)] h-[16px] w-px origin-bottom rounded-sm bg-brand" style={{ transform: `rotate(${second * 6}deg)` }} />
        <b className="absolute z-[3] top-[calc(50%-2px)] left-[calc(50%-2px)] size-[5px] rounded-full bg-brand" />
      </div>
      <div className="flex flex-col gap-px max-sm:hidden">
        <strong className="font-[family-name:var(--font-mono)] text-base leading-[1.1] font-bold tabular-nums text-ink">
          {String(hour).padStart(2, "0")}:{String(minute).padStart(2, "0")}
        </strong>
        <small className="text-[10px] font-extrabold tracking-[.1em] text-quiet uppercase">Fortaleza</small>
      </div>
    </div>
  );
}
