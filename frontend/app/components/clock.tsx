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

  if (!now) return <div className="relative size-11 rounded-full border border-line-strong bg-surface-raised max-[760px]:size-[42px]" />;

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
    <div className="flex items-center gap-[11px] rounded-lg border border-line bg-surface px-[11px] py-2">
      <div data-testid="clock-face" className="relative size-11 rounded-full border border-line-strong bg-surface-raised before:absolute before:left-1/2 before:h-full before:w-px before:bg-line-strong before:content-[''] after:absolute after:top-1/2 after:h-px after:w-full after:bg-line-strong after:content-[''] max-[760px]:size-[42px]" aria-hidden="true">
        <i className="absolute z-[2] bottom-1/2 left-[calc(50%-1px)] h-3 w-0.5 origin-bottom rounded-sm bg-text" style={{ transform: `rotate(${hour * 30 + minute / 2}deg)` }} />
        <i className="absolute z-[2] bottom-1/2 left-[calc(50%-1px)] h-[17px] w-0.5 origin-bottom rounded-sm bg-text" style={{ transform: `rotate(${minute * 6}deg)` }} />
        <i className="absolute z-[2] bottom-1/2 left-[calc(50%-1px)] h-[18px] w-px origin-bottom rounded-sm bg-accent" style={{ transform: `rotate(${second * 6}deg)` }} />
        <b className="absolute z-[3] top-[calc(50%-2px)] left-[calc(50%-2px)] size-[5px] rounded-full bg-accent" />
      </div>
      <div className="flex flex-col gap-px max-[760px]:hidden">
        <strong className="text-[19px] leading-[1.1] tabular-nums">
          {String(hour).padStart(2, "0")}:{String(minute).padStart(2, "0")}
        </strong>
        <small className="text-[10px] font-bold tracking-[.08em] text-muted uppercase">Fortaleza</small>
      </div>
    </div>
  );
}
