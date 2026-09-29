"use client";

import { CheckCircle, WarningCircle, X } from "@phosphor-icons/react";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type NotificationTone = "success" | "warning" | "error";
type NotificationInput = { message: string; tone?: NotificationTone };
type Notification = NotificationInput & { id: number };
type NotificationsValue = { notify: (input: NotificationInput) => void };

const NotificationsContext = createContext<NotificationsValue | null>(null);
const MAX_NOTIFICATIONS = 3;
const DISMISS_AFTER = 5_000;

function compactMessage(message: string) {
  const compact = message.replace(/\s+/g, " ").trim();
  return compact.length > 180 ? `${compact.slice(0, 177).trimEnd()}…` : compact;
}

function Toast({ notification, onDismiss }: { notification: Notification; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(notification.id), DISMISS_AFTER);
    return () => window.clearTimeout(timer);
  }, [notification.id, onDismiss]);

  const config = {
    success: { label: "Sucesso", Icon: CheckCircle, className: "border-success/35 bg-success-soft text-success" },
    warning: { label: "Atenção", Icon: WarningCircle, className: "border-warning/35 bg-warning-soft text-warning" },
    error: { label: "Erro", Icon: WarningCircle, className: "border-destructive/35 bg-destructive/10 text-destructive" },
  }[notification.tone ?? "error"];
  const Icon = config.Icon;

  return <div role={notification.tone === "error" ? "alert" : "status"} className={cn("pointer-events-auto flex items-start gap-3 rounded-lg border p-3 shadow-lg", config.className)}>
    <Icon size={20} weight="fill" className="mt-0.5 shrink-0" aria-hidden="true" />
    <div className="min-w-0 flex-1"><p className="text-sm font-semibold">{config.label}</p><p className="mt-0.5 text-sm leading-5 text-current/90">{compactMessage(notification.message)}</p></div>
    <Button type="button" variant="ghost" size="icon" className="size-8 shrink-0" onClick={() => onDismiss(notification.id)} aria-label={`Fechar aviso de ${config.label.toLowerCase()}`}>
      <X size={16} aria-hidden="true" />
    </Button>
  </div>;
}

export function NotificationsProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const dismiss = useCallback((id: number) => setNotifications((current) => current.filter((notification) => notification.id !== id)), []);
  const notify = useCallback(({ message, tone = "error" }: NotificationInput) => {
    const text = compactMessage(message);
    if (!text) return;
    setNotifications((current) => {
      if (current.some((notification) => notification.message === text && notification.tone === tone)) return current;
      return [...current, { id: Date.now() + Math.random(), message: text, tone }].slice(-MAX_NOTIFICATIONS);
    });
  }, []);

  return <NotificationsContext.Provider value={{ notify }}>
    {children}
    <div className="pointer-events-none fixed inset-x-4 top-4 z-50 mx-auto flex w-auto max-w-md flex-col gap-2 sm:left-auto sm:right-6 sm:mx-0" aria-live="polite" aria-atomic="true">
      {notifications.map((notification) => <Toast key={notification.id} notification={notification} onDismiss={dismiss} />)}
    </div>
  </NotificationsContext.Provider>;
}

export function useNotifications() {
  const context = useContext(NotificationsContext);
  if (!context) throw new Error("useNotifications must be used within NotificationsProvider");
  return context;
}
