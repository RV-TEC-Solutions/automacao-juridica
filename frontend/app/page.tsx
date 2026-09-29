"use client";

import Link from "next/link";
import { ArrowRight, Bell, ChartLineUp, CalendarDots, ClockCounterClockwise, Sparkle, WarningCircle } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "./components/app-shell";
import { Clock } from "./components/clock";
import { CollectionPipeline } from "./components/collection-pipeline";
import { DiscardCollectionDialog } from "./components/discard-collection-dialog";
import { ExpedienteDrawer } from "./components/expediente-drawer";
import { ExpedienteList } from "./components/expediente-list";
import { LoadingRows, MetricCard, PageTitle, Pagination } from "./components/ui";
import { useNotifications } from "./components/notifications";
import { api } from "./lib/api";
import type { Dashboard, Expediente, ExpedientePage } from "./lib/types";

function greeting() {
  const hour = Number(
    new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Fortaleza",
      hour: "numeric",
      hour12: false,
    }).format(new Date())
  );
  return hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
}

type MetricKey = "new" | "updated" | "unread" | "urgent" | "next_week" | "calculating";

type TokenStatus = { available: boolean; message: string };

const metricFilters: Record<MetricKey, { title: string; description: string; params: Record<string, string> }> = {
  new: { title: "Expedientes de Hoje", description: "Todos os expedientes descobertos na coleta de hoje.", params: { event_kind: "new" } },
  updated: { title: "Expedientes alterados hoje", description: "Expedientes com prazo ou teor alterado hoje.", params: { event_kind: "updated" } },
  unread: { title: "Expedientes não lidos", description: "Expedientes que ainda aguardam leitura.", params: { read: "unread" } },
  urgent: { title: "Expedientes urgentes", description: "Prazos vencidos ou com vencimento nas próximas 72 horas.", params: { deadline: "urgent" } },
  next_week: { title: "Prazos até próxima semana", description: "Expedientes com prazo fatal até o fim da próxima semana.", params: { deadline: "next_week" } },
  calculating: { title: "Prazos em cálculo", description: "Expedientes cujo prazo ainda está em cálculo interno no PJe.", params: { deadline: "calculating" } },
};

function localDate() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Fortaleza", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return `${values.year}-${values.month}-${values.day}`;
}
export default function Home() {
  const { notify } = useNotifications();
  const [tokenStatus, setTokenStatus] = useState<TokenStatus | null>(null);
  const tokenStatusRef = useRef<TokenStatus | null>(null);
  const [data, setData] = useState<Dashboard | null>(null);

  const [selected, setSelected] = useState<Expediente | null>(null);
  const [running, setRunning] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  const [discardDialogOpen, setDiscardDialogOpen] = useState(false);
  const [discardTrigger, setDiscardTrigger] = useState<HTMLButtonElement | null>(null);

  const [activeMetric, setActiveMetric] = useState<MetricKey>("new");
  const [listPage, setListPage] = useState(1);
  const [expedientes, setExpedientes] = useState<ExpedientePage | null>(null);


  const load = useCallback(async () => {
    try {
      setData(await api<Dashboard>("dashboard/"));
    } catch (exception) {
      notify({ message: exception instanceof Error ? exception.message : "Falha ao carregar." });
    }
  }, [notify]);

  const updateTokenStatus = useCallback((status: TokenStatus) => {
    const wasUnavailable = tokenStatusRef.current?.available === false;
    tokenStatusRef.current = status;
    setTokenStatus(status);
    if (!status.available && !wasUnavailable) notify({ tone: "warning", message: status.message || "Token não conectado." });
  }, [notify]);

  const loadTokenStatus = useCallback(async () => {
    try { updateTokenStatus(await api<TokenStatus>("automation/token-status/")); }
    catch { updateTokenStatus({ available: false, message: "Não foi possível verificar o token físico." }); }
  }, [updateTokenStatus]);

  const loadExpedientes = useCallback(async () => {
    const filter = metricFilters[activeMetric];
    const params = new URLSearchParams({ ...filter.params, page: String(listPage), page_size: "50", ordering: "recent" });
    if (activeMetric === "new" || activeMetric === "updated") {
      const today = localDate();
      params.set("date_from", today);
      params.set("date_to", today);
    }
    try {
      setExpedientes(await api<ExpedientePage>(`expedientes/?${params}`));
    } catch (exception) {
      notify({ message: exception instanceof Error ? exception.message : "Falha ao carregar expedientes." });
    }
  }, [activeMetric, listPage, notify]);

  useEffect(() => {
    queueMicrotask(() => { void loadExpedientes(); });
  }, [loadExpedientes]);

  const selectMetric = (metric: MetricKey) => {
    setActiveMetric(metric);
    setListPage(1);
  };

  useEffect(() => {
    queueMicrotask(() => {
      load().then(() => api("dashboard/", { method: "POST" }).catch(() => {}));
    });
  }, [load]);

  useEffect(() => {
    queueMicrotask(() => { void loadTokenStatus(); });
    const interval = window.setInterval(() => { void loadTokenStatus(); }, 10_000);
    return () => window.clearInterval(interval);
  }, [loadTokenStatus]);

  const run = async (source = "pje-tjrn", rerun = false) => {
    if (!tokenStatus?.available) {
      await loadTokenStatus();
      return;
    }
    setRunning(true);
    try {
      await api("automation/runs/", {
        method: "POST",
        body: JSON.stringify({ source, ...(rerun ? { rerun: true } : {}) }),
      });
      await load();
    } catch (exception) {
      notify({ message: exception instanceof Error ? exception.message : "Não foi possível iniciar." });
    } finally {
      setRunning(false);
    }
  };

  const cancel = async () => {
    const runId = data?.latest_run?.id;
    if (!runId) return;

    setCancelling(true);
    try {
      await api(`automation/runs/${runId}/cancel/`, { method: "POST" });
      await load();
    } catch (exception) {
      notify({ message: exception instanceof Error ? exception.message : "Não foi possível interromper a coleta." });
    } finally {
      setCancelling(false);
    }
  };

  const closeDiscardDialog = () => {
    setDiscardDialogOpen(false);
    window.requestAnimationFrame(() => discardTrigger?.focus());
  };

  const discardToday = async () => {
    let discarded = false;
    setDiscarding(true);
    try {
      const result = await api<{ deleted_expedientes: number; reverted_updates: number; reactivated_expedientes: number }>("automation/collections/today/discard/", { method: "POST" });
      notify({ tone: "success", message: `Coleta descartada: ${result.deleted_expedientes} expedientes excluídos, ${result.reverted_updates} alterações revertidas e ${result.reactivated_expedientes} reativados.` });
      setDiscardDialogOpen(false);
      discarded = true;
      await Promise.all([load(), loadExpedientes()]);
    } catch (exception) {
      notify({ message: exception instanceof Error ? exception.message : "Não foi possível descartar a coleta do dia." });
    } finally {
      setDiscarding(false);
      if (discarded) window.requestAnimationFrame(() => discardTrigger?.focus());
    }
  };

  const pipeline = data?.collection_pipeline;
  const runStatus = data?.latest_run?.status;
  const collectionInProgress = pipeline?.active ?? ["pending", "running"].includes(runStatus ?? "");
  const collectionRunning = pipeline
    ? pipeline.steps.some((step) => step.status === "running")
    : runStatus === "running";
  const canDiscard = Boolean(
    data
    && !collectionRunning
    && !running
    && !discarding
    && data.today.discardable > 0
  );

  useEffect(() => {
    if (!collectionInProgress) return;

    const interval = window.setInterval(() => {
      void load();
    }, 1_500);

    return () => window.clearInterval(interval);
  }, [collectionInProgress, load]);

  const date = new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Fortaleza",
    weekday: "long",
    day: "2-digit",
    month: "long",
  }).format(new Date());

  const formattedDate = date.charAt(0).toUpperCase() + date.slice(1);

  return (
    <AppShell>
      <PageTitle
        title={`${greeting()}, ${data?.display_name.split(" ")[0] ?? ""}.`}
        description={formattedDate}
        actions={<Clock />}
      />

      <div className="mb-8 grid min-w-0 gap-x-6 gap-y-4 xl:grid-cols-2">
        <section className="contents">
          <div className="order-2 flex items-center justify-between xl:order-none xl:col-start-1 xl:row-start-1">
            <div>
              <h2 className="mb-2 text-2xl font-extrabold tracking-tight leading-tight text-foreground sm:text-3xl">Visão executiva</h2>
              <p className="mb-0 text-xs font-medium text-muted-foreground">Indicadores consolidados do ciclo de monitoramento atual.</p>
            </div>
            <div className="grid size-8 place-items-center rounded-xl border border-border bg-card text-muted-foreground"><ChartLineUp size={18} weight="duotone" /></div>
          </div>
          <div className="order-3 grid min-w-0 grid-cols-2 gap-4 lg:grid-cols-3 xl:order-none xl:col-start-1 xl:row-start-2">
            <MetricCard label="Novos" value={data?.today.new ?? 0} note="expedientes descobertos" icon={<Sparkle size={18} weight="duotone" />} tone="green" onClick={() => selectMetric("new")} selected={activeMetric === "new"} />
            <MetricCard label="Alterados" value={data?.today.updated ?? 0} note="mudanças de prazo/teor" icon={<ClockCounterClockwise size={18} weight="duotone" />} tone="blue" onClick={() => selectMetric("updated")} selected={activeMetric === "updated"} />
            <MetricCard label="Não lidos" value={data?.today.unread ?? 0} note="aguardando leitura" icon={<Bell size={18} weight="duotone" />} tone="slate" onClick={() => selectMetric("unread")} selected={activeMetric === "unread"} />
            <MetricCard label="Urgentes" value={data?.today.urgent ?? 0} note="vencidos ou até 72h" icon={<WarningCircle size={18} weight="duotone" />} tone="rose" onClick={() => selectMetric("urgent")} selected={activeMetric === "urgent"} />
            <MetricCard label="Até próxima semana" value={data?.today.next_week ?? 0} note="prazos fatais a vencer" icon={<CalendarDots size={18} weight="duotone" />} tone="amber" onClick={() => selectMetric("next_week")} selected={activeMetric === "next_week"} />
            <MetricCard label="Prazos em cálculo" value={data?.today.calculating ?? 0} note="prazos ainda em cálculo" icon={<WarningCircle size={18} weight="duotone" />} tone="slate" onClick={() => selectMetric("calculating")} selected={activeMetric === "calculating"} />
          </div>
        </section>
        {pipeline && (
          <div className="order-1 min-w-0 xl:order-none xl:col-start-2 xl:row-start-2">
            <CollectionPipeline pipeline={pipeline} refreshing={refreshing} starting={running} cancelling={cancelling}
              discarding={discarding} canDiscard={canDiscard}
              onRefresh={() => { setRefreshing(true); void load().finally(() => setRefreshing(false)); }}
              tokenAvailable={tokenStatus?.available}
              onRun={() => { void run(); }} onCancel={() => { void cancel(); }} onDiscard={(trigger) => { setDiscardTrigger(trigger); setDiscardDialogOpen(true); }} onRerun={(source) => { void run(source, true); }} />
          </div>
        )}
      </div>

      {/* Recent expedientes */}
      <section>
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="mb-2 text-2xl font-extrabold tracking-tight leading-tight text-foreground sm:text-3xl">
              {metricFilters[activeMetric].title}{activeMetric === "new" ? " (" + formattedDate + ")" : ""}
            </h2>
            <p className="mb-0 text-xs text-muted-foreground font-medium">
              {metricFilters[activeMetric].description}
            </p>
          </div>
          <Link
            href="/expedientes"
            className="group inline-flex items-center gap-2 text-xs font-extrabold text-foreground no-underline hover:text-foreground transition-colors"
          >
            Ver consulta completa
            <ArrowRight size={14} weight="bold" className="transition-transform group-hover:translate-x-2" />
          </Link>
        </div>

        {expedientes ? <ExpedienteList items={expedientes.results} onSelect={setSelected} /> : <LoadingRows />}

        {expedientes && <Pagination page={listPage} pages={Math.ceil(expedientes.count / 50)} onPageChange={setListPage} label="Paginação de expedientes" />}
      </section>

      <ExpedienteDrawer
        item={selected}
        onClose={() => setSelected(null)}
        onRead={() => {
          if (selected) setSelected({ ...selected, unread: false });
          load();
          loadExpedientes();
        }}
      />
      <DiscardCollectionDialog open={discardDialogOpen} busy={discarding} onClose={closeDiscardDialog} onConfirm={() => { void discardToday(); }} />
    </AppShell>
  );
}
