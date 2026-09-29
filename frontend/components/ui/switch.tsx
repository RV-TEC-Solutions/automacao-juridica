"use client";

import { Switch as SwitchPrimitive } from "@base-ui/react/switch";
import { cn } from "@/lib/utils";

function Switch({ className, ...props }: SwitchPrimitive.Root.Props) {
  return <SwitchPrimitive.Root data-slot="switch" className={cn("group inline-flex h-6 w-12 items-center rounded-full bg-input outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring data-checked:bg-primary disabled:cursor-not-allowed disabled:opacity-50", className)} {...props}><SwitchPrimitive.Thumb className="block size-4 translate-x-2 rounded-full bg-card shadow-sm transition-transform group-data-checked:translate-x-6" /></SwitchPrimitive.Root>;
}

export { Switch };
