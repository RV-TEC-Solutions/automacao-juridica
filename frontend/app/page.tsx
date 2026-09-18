"use client";

import Link from "next/link";
import { ArrowRight, Bell, ChartLineUp, ClockCounterClockwise, Play, Sparkle, WarningCircle } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "./components/app-shell";
import { Clock } from "./components/clock";
import { ExpedienteDrawer } from "./components/expediente-drawer";
import { ExpedienteList } from "./components/expediente-list";
import { BezelCard, Feedback, LoadingRows, MetricCard, PageTitle } from "./components/ui";
import { api, formatDateTime } from "./lib/api";
import type { Dashboard, Expediente } from "./lib/types";

function greeting() { const hour = Number(new Intl.DateTimeFormat("en-US", { timeZone: "America/Fortaleza", hour: "numeric", hour12: false }).format(new Date())); return hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite"; }

export default function Home() {
  const [data, setData] = useState<Dashboard | null>(null); const [error, setError] = useState(""); const [selected, setSelected] = useState<Expediente | null>(null); const [running, setRunning] = useState(false);
  const load = useCallback(async () => { try { setData(await api<Dashboard>("dashboard/")); setError(""); } catch (exception) { setError(exception instanceof Error ? exception.message : "Falha ao carregar."); } }, []);
  useEffect(() => { queueMicrotask(() => { load().then(() => api("dashboard/", { method: "POST" }).catch(() => {})); }); }, [load]);
  const run = async () => { setRunning(true); try { await api("automation/runs/", { method: "POST", body: JSON.stringify({ source: "pje-tjrn" }) }); await load(); } catch (exception) { setError(exception instanceof Error ? exception.message : "Não foi possível iniciar."); } finally { setRunning(false); } };
  const runStatus = data?.latest_run?.status;
  const statusCopy = !data?.latest_run ? "Nenhuma coleta executada" : runStatus === "success" ? "Coleta concluída" : runStatus === "failed" ? "Coleta requer atenção" : runStatus === "running" ? "Coleta em andamento" : "Coleta aguardando";
  const statusTone = runStatus === "success" ? "bg-positive" : runStatus === "failed" ? "bg-danger" : ["pending", "running"].includes(runStatus ?? "") ? "bg-caution animate-pulse" : "bg-quiet";
  const date = new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Fortaleza", weekday: "long", day: "2-digit", month: "long" }).format(new Date());
  return <AppShell><PageTitle eyebrow="Painel operacional" title={`${greeting()}, ${data?.display_name.split(" ")[0] ?? ""}.`} description={date.charAt(0).toUpperCase() + date.slice(1)} actions={<Clock />} />
    {error && <Feedback action={<button className="button-secondary cursor-pointer px-3 text-xs" onClick={load}>Tentar novamente</button>}>{error}</Feedback>}
    {data?.latest_run?.status === "failed" && <Feedback tone="warning" action={<button className="button-secondary cursor-pointer px-3 text-xs" onClick={run}>Tentar novamente</button>}>{data.latest_run.error || "A última coleta encontrou um problema."}</Feedback>}
    <BezelCard className="mb-5" innerClassName="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"><div className="flex items-center gap-3"><span className={`size-2.5 rounded-full ${statusTone}`} /><div><strong className="block text-sm font-extrabold text-ink">{statusCopy}</strong><small className="mt-0.5 block text-xs text-quiet">{data?.latest_run ? `Última atualização ${formatDateTime(data.latest_run.finished_at ?? data.latest_run.started_at)}` : "Inicie uma coleta para atualizar os expedientes."}</small></div></div><button className="button-primary cursor-pointer px-4 text-sm" onClick={run} disabled={running || ["pending", "running"].includes(runStatus ?? "")}><Play size={16} weight="fill" />{running ? "Solicitando…" : "Executar coleta"}</button></BezelCard>
    <section className="mb-7"><div className="mb-3 flex items-center justify-between"><div><h2 className="mb-1 text-base font-extrabold text-ink">Visão executiva</h2><p className="mb-0 text-xs text-quiet">Indicadores do ciclo de coleta atual.</p></div><ChartLineUp size={20} className="text-brand" /></div><div className="grid grid-cols-2 gap-3 lg:grid-cols-4"><MetricCard label="Novos" value={data?.today.new ?? 0} note="expedientes descobertos" icon={<Sparkle size={18} weight="duotone" />} tone="blue" /><MetricCard label="Alterados" value={data?.today.updated ?? 0} note="mudanças relevantes" icon={<ClockCounterClockwise size={18} weight="duotone" />} tone="cyan" /><MetricCard label="Não lidos" value={data?.today.unread ?? 0} note="aguardando leitura" icon={<Bell size={18} weight="duotone" />} tone="slate" /><MetricCard label="Urgentes" value={data?.today.urgent ?? 0} note="vencidos ou até 72h" icon={<WarningCircle size={18} weight="duotone" />} tone="amber" /></div>{(data?.today.calculating ?? 0) > 0 && <p className="mt-3 text-xs font-semibold text-caution">{data?.today.calculating} prazo(s) ainda estão em cálculo no PJe.</p>}</section>
    {data && <BezelCard className="mb-7" innerClassName="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"><div><span className="text-[10px] font-extrabold tracking-[.12em] text-brand uppercase">Atividade desde a última visita</span><p className="mt-1 mb-0 text-sm text-ink-soft"><strong className="text-ink">{data.since_last_visit.new} novo{data.since_last_visit.new === 1 ? "" : "s"}</strong>, <strong className="text-ink">{data.since_last_visit.updated} alterado{data.since_last_visit.updated === 1 ? "" : "s"}</strong> e <strong className="text-ink">{data.since_last_visit.resolved} resolvido{data.since_last_visit.resolved === 1 ? "" : "s"}</strong>.</p></div><small className="text-xs text-quiet">{data.since_last_visit.since ? `Desde ${formatDateTime(data.since_last_visit.since)}` : "Primeiro resumo"}</small></BezelCard>}
    <section><div className="mb-3 flex items-end justify-between gap-4"><div><h2 className="mb-1 text-base font-extrabold text-ink">Expedientes recentes</h2><p className="mb-0 text-xs text-quiet">Acompanhe as últimas alterações identificadas.</p></div><Link href="/expedientes" className="inline-flex items-center gap-1 text-xs font-extrabold text-brand no-underline hover:text-brand-strong">Ver consulta <ArrowRight size={15} /></Link></div>{data ? <ExpedienteList items={data.recent} onSelect={setSelected} /> : <LoadingRows />}</section>
    <ExpedienteDrawer item={selected} onClose={() => setSelected(null)} onRead={() => { if (selected) setSelected({ ...selected, unread: false }); load(); }} />
  </AppShell>;
}
