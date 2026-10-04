import type { CollectionRun, Expediente } from "../lib/types";
import { at, dayOffset, localDay, type DemoState } from "./seed";

const eventDay = (value: string) => localDay(new Date(value));
const paramsPage = (params: URLSearchParams) => Math.max(1, Number(params.get("page")) || 1);
const stamp = (value: string | null) => value ? new Date(value).getTime() : 0;
function groupBy<T>(items: T[], key: (item: T) => string) {
  const grouped = new Map<string, T[]>();
  items.forEach((item) => { const group = key(item); grouped.set(group, [...(grouped.get(group) ?? []), item]); });
  return grouped;
}

export function filteredExpedientes(state: DemoState, params: URLSearchParams) {
  const q = (params.get("q") ?? "").toLocaleLowerCase("pt-BR");
  const now = Date.now();
  const weekday = new Date(`${state.seedDay}T12:00:00-03:00`).getUTCDay();
  const nextMonday = 8 - (weekday || 7);
  const nextWeek = new Date(`${dayOffset(state.seedDay, nextMonday + 7)}T00:00:00-03:00`).getTime();
  const filtered = state.expedientes.filter((item) => {
    if (q && ![item.processo.numero, item.processo.partes_texto, item.processo.assunto].some((part) => part.toLocaleLowerCase("pt-BR").includes(q))) return false;
    if (params.get("source") && item.source?.code !== params.get("source")) return false;
    if (params.get("pending_type") && item.tipo_pendencia !== params.get("pending_type")) return false;
    if (params.get("read") === "unread" && !item.unread) return false;
    if (params.get("read") === "read" && item.unread) return false;
    if (params.get("event_kind") && item.latest_event?.kind !== params.get("event_kind")) return false;
    const day = eventDay(item.latest_event?.created_at ?? item.capturado_em);
    if (params.get("date_from") && day < params.get("date_from")!) return false;
    if (params.get("date_to") && day > params.get("date_to")!) return false;
    const deadline = params.get("deadline");
    const due = stamp(item.prazo_fatal);
    if (deadline === "urgent" && !(item.ativo && due && due <= now + 72 * 3600_000)) return false;
    if (deadline === "overdue" && !(item.ativo && due && due < now)) return false;
    if (deadline === "future" && !(item.ativo && due > now + 72 * 3600_000)) return false;
    if (deadline === "next_week" && !(item.ativo && due >= now && due < nextWeek)) return false;
    if (deadline === "calculating" && !(item.ativo && item.status_prazo_fatal === "em_calculo")) return false;
    if (deadline === "none" && !(item.ativo && item.status_prazo_fatal === "sem_prazo")) return false;
    if (deadline === "resolved" && item.ativo) return false;
    return true;
  });
  const ordering = params.get("ordering") ?? "recent";
  filtered.sort((a, b) => ordering === "process" ? a.processo.numero.localeCompare(b.processo.numero)
    : ordering === "deadline" ? (stamp(a.prazo_fatal) || Infinity) - (stamp(b.prazo_fatal) || Infinity)
    : ordering === "expedition" ? stamp(b.data_expedicao) - stamp(a.data_expedicao)
    : stamp(b.latest_event?.created_at ?? b.capturado_em) - stamp(a.latest_event?.created_at ?? a.capturado_em));
  return filtered;
}

export function filteredPublications(state: DemoState, params: URLSearchParams) {
  const q = (params.get("q") ?? "").toLocaleLowerCase("pt-BR");
  return state.publications.filter((item) => {
    const collectedDay = eventDay(item.collected_at);
    if (params.get("collected_from") && collectedDay < params.get("collected_from")!) return false;
    if (params.get("collected_to") && collectedDay > params.get("collected_to")!) return false;
    if (params.get("date_from") && item.data_disponibilizacao < params.get("date_from")!) return false;
    if (params.get("date_to") && item.data_disponibilizacao > params.get("date_to")!) return false;
    if (params.get("tribunal") && item.tribunal !== params.get("tribunal")) return false;
    if (params.get("read") === "unread" && !item.unread) return false;
    if (q && ![item.processo.numero, item.texto, ...item.recipients.map((person) => person.name)].some((part) => part.toLocaleLowerCase("pt-BR").includes(q))) return false;
    return true;
  }).sort((a, b) => stamp(b.collected_at) - stamp(a.collected_at));
}

export function page<T>(items: T[], params: URLSearchParams, defaultSize: number, maxSize = defaultSize) {
  const current = paramsPage(params);
  const size = Math.min(maxSize, Math.max(1, Number(params.get("page_size")) || defaultSize));
  const start = (current - 1) * size;
  return { count: items.length, next: start + size < items.length ? current + 1 : null, previous: current > 1 ? current - 1 : null, results: items.slice(start, start + size) };
}

export function pipeline(state: DemoState) {
  const { collection, sources } = state;
  const steps = sources.map((source) => {
    const index = collection.codes.indexOf(source.code);
    const run = state.runs.find((item) => item.cycle_id === collection.cycleId && item.source?.code === source.code);
    const status = !source.enabled ? "disabled" : index < 0 ? "pending" : collection.active && index === collection.current ? "running" : run?.status === "success" ? "success" : "pending";
    return { code: source.code, group: source.group, label: `${source.system} · ${source.tribunal}`, status, run_id: run?.id ?? null, error: "", message: run?.message ?? "" };
  });
  const cycleRuns = state.runs.filter((run) => run.cycle_id === collection.cycleId);
  const completed = steps.filter((step) => step.status === "success").length;
  const finished = !collection.active && cycleRuns.length > 0;
  return { cycle_id: collection.cycleId, status: collection.active ? "running" : finished ? "success" : "idle",
    active: collection.active, completed, total: steps.filter((step) => step.status !== "disabled").length,
    started_at: cycleRuns.at(-1)?.started_at ?? null, finished_at: finished ? cycleRuns[0]?.finished_at ?? null : null,
    current_step: collection.active ? collection.codes[collection.current] : null, steps };
}

export function dashboard(state: DemoState) {
  const today = state.seedDay;
  const todayEvents = state.expedientes.filter((item) => eventDay(item.latest_event?.created_at ?? item.capturado_em) === today);
  const countKind = (items: Expediente[], kind: string) => items.filter((item) => item.latest_event?.kind === kind).length;
  const urgent = filteredExpedientes(state, new URLSearchParams("deadline=urgent")).length;
  const nextWeek = filteredExpedientes(state, new URLSearchParams("deadline=next_week")).length;
  const latestRun = [...state.runs].sort((a, b) => stamp(b.created_at) - stamp(a.created_at))[0] ?? null;
  return { display_name: state.user.display_name,
    today: { new: countKind(todayEvents, "new"), updated: countKind(todayEvents, "updated"), resolved: countKind(todayEvents, "resolved"),
      discardable: 0, unread: state.expedientes.filter((item) => item.unread).length, urgent, next_week: nextWeek,
      calculating: state.expedientes.filter((item) => item.ativo && item.status_prazo_fatal === "em_calculo").length },
    since_last_visit: { since: state.lastVisit, new: countKind(todayEvents, "new"), updated: countKind(todayEvents, "updated"), resolved: countKind(todayEvents, "resolved") },
    latest_run: latestRun ? runSimple(latestRun) : null, collection_pipeline: pipeline(state),
    recent: filteredExpedientes(state, new URLSearchParams()).slice(0, 8),
    notices: { unread: state.notices.filter((item) => item.unread).length, recent: state.notices.slice(0, 4) } };
}

function runSimple(run: CollectionRun) {
  return { id: run.id, cycle_id: run.cycle_id, status: run.status, trigger: run.trigger, started_at: run.started_at,
    finished_at: run.finished_at, found: run.found, created: run.created, updated: run.updated, resolved: run.resolved,
    error: run.error, message: run.message, source: run.source?.code ?? null };
}

export function collectionHistory(state: DemoState) {
  const grouped = groupBy([...state.runs].sort((a, b) => stamp(b.created_at) - stamp(a.created_at)), (run) => eventDay(run.created_at));
  return { period_start: dayOffset(state.seedDay, -29), period_end: state.seedDay,
    days: Array.from(grouped, ([date, runs]) => ({ date, runs })).sort((a, b) => b.date.localeCompare(a.date)) };
}

export function expedienteHistory(state: DemoState, params: URLSearchParams) {
  const from = params.get("date_from") ?? dayOffset(state.seedDay, -29);
  const to = params.get("date_to") ?? state.seedDay;
  const events = state.expedientes.filter((item) => item.latest_event?.kind === "new" && eventDay(item.latest_event.created_at) >= from && eventDay(item.latest_event.created_at) <= to)
    .sort((a, b) => stamp(b.latest_event?.created_at ?? null) - stamp(a.latest_event?.created_at ?? null));
  const current = paramsPage(params);
  const subset = events.slice((current - 1) * 50, current * 50);
  const grouped = groupBy(subset, (item) => eventDay(item.latest_event!.created_at));
  return { period_start: from, period_end: to, count: events.length, page: current, page_size: 50,
    days: Array.from(grouped, ([date, items]) => ({ date, new_count: events.filter((item) => eventDay(item.latest_event!.created_at) === date).length,
      items: items.map((expediente) => ({ event: expediente.latest_event, expediente })) })) };
}

export function djenHistory(state: DemoState, params: URLSearchParams) {
  const all = filteredPublications(state, params);
  const current = paramsPage(params);
  const subset = all.slice((current - 1) * 50, current * 50);
  const grouped = groupBy(subset, (item) => eventDay(item.collected_at));
  return { count: all.length, page: current, page_size: 50, days: Array.from(grouped, ([date, items]) => ({ date, items })) };
}

export function statistics(state: DemoState, period: number) {
  const start = dayOffset(state.seedDay, -(period - 1));
  const previousStart = dayOffset(state.seedDay, -(period * 2 - 1));
  const current = state.expedientes.filter((item) => eventDay(item.latest_event?.created_at ?? item.capturado_em) >= start);
  const previous = state.expedientes.filter((item) => { const day = eventDay(item.latest_event?.created_at ?? item.capturado_em); return day >= previousStart && day < start; });
  const byKind = (items: Expediente[], kind: string) => items.filter((item) => item.latest_event?.kind === kind).length;
  const timeline = Array.from({ length: period }, (_, i) => dayOffset(state.seedDay, i - period + 1)).flatMap((day) =>
    (["new", "updated", "resolved"] as const).map((kind) => ({ day, kind, total: current.filter((item) => eventDay(item.latest_event!.created_at) === day && item.latest_event?.kind === kind).length })));
  const active = state.expedientes.filter((item) => item.ativo);
  const countBy = (key: "tipo_pendencia" | "status_prazo_fatal") => Array.from(groupBy(active, (item) => String(item[key])), ([value, items]) => ({ [key]: value, total: items.length }));
  const completedRuns = state.runs.filter((run) => run.status === "success");
  const seconds = completedRuns.reduce((total, run) => total + 360 + run.found * 75, 0);
  return { period, time_saved: { total_seconds: seconds, today_seconds: completedRuns.filter((run) => eventDay(run.created_at) === state.seedDay).reduce((total, run) => total + 360 + run.found * 75, 0),
      source_days: completedRuns.length, items: completedRuns.reduce((total, run) => total + run.created, 0), tabs: completedRuns.length * 2 },
    totals: { current: current.length, previous: previous.length, change_percent: previous.length ? Math.round((current.length - previous.length) / previous.length * 100) : null,
      new: byKind(current, "new"), updated: byKind(current, "updated"), resolved: byKind(current, "resolved") },
    timeline, pending_distribution: countBy("tipo_pendencia"), deadline_distribution: countBy("status_prazo_fatal") };
}

function newRun(state: DemoState, sourceCode: string, status: CollectionRun["status"], cycleId: string): CollectionRun {
  const source = state.sources.find((item) => item.code === sourceCode)!;
  const now = at(state.seedDay, 9, Math.min(59, state.runs.length % 59));
  return { id: Math.max(0, ...state.runs.map((item) => item.id)) + 1, cycle_id: cycleId, status,
    status_label: status === "running" ? "Executando" : "Sucesso", trigger: "manual", trigger_label: "Manual",
    created_at: now, started_at: now, finished_at: status === "success" ? now : null, duration_seconds: status === "success" ? 90 : null,
    found: 0, created: 0, updated: 0, resolved: 0, error: "", message: status === "success" ? "Coleta fictícia concluída." : "Coleta fictícia em andamento.",
    source: { code: source.code, system: source.system, tribunal: source.tribunal } };
}

export function startCollection(state: DemoState, requestedSource?: string, rerun = false) {
  if (state.collection.active) throw new Error("Já existe uma coleta em andamento.");
  const enabled = state.sources.filter((source) => source.enabled).map((source) => source.code);
  const codes = rerun && requestedSource ? enabled.filter((code) => code === requestedSource) : enabled;
  if (!codes.length) throw new Error("Habilite uma fonte antes de iniciar a coleta.");
  const cycleId = `demo-ciclo-${Date.now()}`;
  state.collection = { active: true, current: 0, codes, cycleId };
  const run = newRun(state, codes[0], "running", cycleId);
  state.runs.unshift(run);
  return runSimple(run);
}

function completeCurrent(state: DemoState) {
  const { collection } = state;
  const source = collection.codes[collection.current];
  const run = state.runs.find((item) => item.cycle_id === collection.cycleId && item.source?.code === source && item.status === "running");
  if (!run) return;
  run.status = "success"; run.status_label = "Sucesso"; run.finished_at = at(state.seedDay, 9, Math.min(59, state.runs.length % 59));
  run.duration_seconds = 90; run.found = source === "djen" ? 3 : 8 + collection.current % 4;
  run.created = source === "djen" ? 3 : 2; run.updated = source === "djen" ? 0 : 1; run.resolved = 0;
  run.message = "Coleta fictícia concluída.";
  if (source === "djen") {
    const first = state.publications[0];
    const id = Math.max(...state.publications.map((item) => item.id)) + 1;
    state.publications.unshift({ ...first, id, link_inteiro_teor: `/demo/inteiro-teor/${id}`,
      numero_comunicacao: first.numero_comunicacao + 100, collected_at: at(state.seedDay, 9, 40), read_at: null, unread: true });
  } else {
    const template = state.expedientes.find((item) => item.source?.code === source) ?? state.expedientes[0];
    const id = Math.max(...state.expedientes.map((item) => item.id)) + 1;
    const date = at(state.seedDay, 9, Math.min(59, state.runs.length % 59));
    state.expedientes.unshift({ ...template, id, identificador_pje: String(80000000 + id), capturado_em: date, atualizado_em: date,
      unread: true, latest_event: { id, kind: "new", kind_label: "Novo", changes: {}, created_at: date, read_at: null },
      processo: { ...template.processo, id, numero: `${String(9000000 + id)}-00.${state.seedDay.slice(0, 4)}.${source === "pje-tjrn" || source === "pje2g-tjrn" ? "8.20" : source.startsWith("tre") ? "6.20" : source === "tse-3g" ? "6.00" : source.startsWith("trt") ? "5.21" : "4.05"}.${String(9000 + id % 100).padStart(4, "0")}` } });
  }
}

export function advanceCollection(state: DemoState, finish = false) {
  if (!state.collection.active) throw new Error("Nenhuma coleta em andamento.");
  do {
    completeCurrent(state);
    state.collection.current++;
    if (state.collection.current >= state.collection.codes.length) { state.collection.active = false; break; }
    state.runs.unshift(newRun(state, state.collection.codes[state.collection.current], "running", state.collection.cycleId!));
  } while (finish);
  return pipeline(state);
}
