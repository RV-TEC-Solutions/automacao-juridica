import { NextRequest } from "next/server";
import { advanceCollection, collectionHistory, dashboard, djenHistory, expedienteHistory, filteredExpedientes, filteredPublications, page, startCollection, statistics } from "../../demo/data";
import { demoPdf } from "../../demo/pdf";
import { localDay, type DemoState } from "../../demo/seed";
import { withState } from "../../demo/store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Context = { params: Promise<{ path: string[] }> };
const json = (value: unknown, status = 200) => Response.json(value, { status, headers: { "Cache-Control": "no-store" } });
const error = (message: string, status = 400) => json({ detail: message }, status);

function pdfResponse(title: string, rows: string[], filename: string) {
  const bytes = demoPdf(title, rows);
  return new Response(new Uint8Array(bytes), { headers: { "Content-Type": "application/pdf", "Content-Disposition": `attachment; filename="${filename}"`, "Cache-Control": "no-store" } });
}

function settings(state: DemoState) {
  return { ...state.user, timezone: "America/Fortaleza",
    credential_status: { credential_file: false, pin: false, totp: false, pjeoffice: "Ambiente de demonstração" } };
}

function exportItems(state: DemoState, params: URLSearchParams) {
  if (params.get("scope") === "history") {
    const historyParams = new URLSearchParams(params);
    historyParams.set("event_kind", "new");
    return filteredExpedientes(state, historyParams);
  }
  if (params.get("scope") !== "overview") return filteredExpedientes(state, params);
  const metric = params.get("metric");
  const mapped = new URLSearchParams();
  if (metric === "new" || metric === "updated") { mapped.set("event_kind", metric); mapped.set("date_from", state.seedDay); mapped.set("date_to", state.seedDay); }
  else if (metric === "unread") mapped.set("read", "unread");
  else if (["urgent", "next_week", "calculating"].includes(metric ?? "")) mapped.set("deadline", metric!);
  return filteredExpedientes(state, mapped);
}

async function handle(request: NextRequest, context: Context) {
  const path = (await context.params).path.join("/");
  const params = request.nextUrl.searchParams;
  const method = request.method;
  let body: Record<string, unknown> = {};
  if (method !== "GET") body = await request.json().catch(() => ({}));
  try {
    return await withState(async (state) => {
      if (path === "auth/me" && method === "GET") return { value: json(state.user) };
      if (path === "settings") {
        if (method === "PATCH") {
          if (typeof body.display_name === "string" && body.display_name.trim()) state.user.display_name = body.display_name.trim();
          if (["light", "dark", "system"].includes(String(body.theme))) state.user.theme = body.theme as DemoState["user"]["theme"];
          if (typeof body.collection_time === "string" && /^([01]\d|2[0-3]):[0-5]\d$/.test(body.collection_time)) state.user.collection_time = body.collection_time;
        }
        return { value: json(settings(state)), write: method === "PATCH" };
      }
      if (path === "sources" && method === "GET") return { value: json(state.sources.map((source) => ({ code: source.code, system: source.system, tribunal: source.tribunal, enabled: source.enabled }))) };
      const sourceMatch = path.match(/^sources\/([^/]+)$/);
      if (sourceMatch && method === "PATCH") {
        const source = state.sources.find((item) => item.code === sourceMatch[1]);
        if (!source) return { value: error("Fonte não encontrada.", 404) };
        if (typeof body.enabled === "boolean") source.enabled = body.enabled;
        return { value: json({ code: source.code, system: source.system, tribunal: source.tribunal, enabled: source.enabled }), write: true };
      }
      if (path === "automation/token-status" && method === "GET") return { value: json({ available: true, message: "Coleta simulada disponível sem token físico." }) };
      if (path === "dashboard") {
        if (method === "POST") { state.lastVisit = new Date().toISOString(); return { value: json({ visited_at: state.lastVisit }), write: true }; }
        return { value: json(dashboard(state)) };
      }
      if (path === "automation/history" && method === "GET") return { value: json(collectionHistory(state)) };
      if (path === "automation/runs") {
        if (method === "POST") return { value: json(startCollection(state, String(body.source ?? "pje-tjrn"), body.rerun === true), 202), write: true };
        return { value: json(state.runs.slice(0, 20)) };
      }
      if (path === "demo/advance" && method === "POST") return { value: json(advanceCollection(state, body.finish === true)), write: true };
      if (path === "expedientes" && method === "GET") return { value: json(page(filteredExpedientes(state, params), params, 25, 50)) };
      const expedienteRead = path.match(/^expedientes\/(\d+)\/read$/);
      if (expedienteRead && method === "POST") {
        const item = state.expedientes.find((row) => row.id === Number(expedienteRead[1]));
        if (!item) return { value: error("Expediente não encontrado.", 404) };
        item.unread = false;
        if (item.latest_event) item.latest_event.read_at = new Date().toISOString();
        return { value: json({ read_at: item.latest_event?.read_at ?? null, events_marked: 1 }), write: true };
      }
      if (path === "history" && method === "GET") return { value: json(expedienteHistory(state, params)) };
      if (path === "statistics" && method === "GET") {
        const period = Number(params.get("period") ?? 7);
        return { value: [7, 30].includes(period) ? json(statistics(state, period)) : error("Período deve ser 7 ou 30 dias.") };
      }
      if (path === "notices" && method === "GET") return { value: json(page(state.notices.filter((item) => params.get("read") !== "unread" || item.unread), params, 25)) };
      const noticeMatch = path.match(/^notices\/(\d+)(?:\/(read))?$/);
      if (noticeMatch) {
        const notice = state.notices.find((item) => item.id === Number(noticeMatch[1]));
        if (!notice) return { value: error("Aviso não encontrado.", 404) };
        if (noticeMatch[2] === "read" && method === "POST") { notice.unread = false; notice.read_at = new Date().toISOString(); return { value: json(notice), write: true }; }
        if (!noticeMatch[2] && method === "GET") return { value: json(notice) };
      }
      if (path === "djen/communications" && method === "GET") return { value: json(page(filteredPublications(state, params), params, 20)) };
      if (path === "djen/history" && method === "GET") return { value: json(djenHistory(state, params)) };
      const publicationMatch = path.match(/^djen\/communications\/(\d+)(?:\/(read))?$/);
      if (publicationMatch) {
        const item = state.publications.find((row) => row.id === Number(publicationMatch[1]));
        if (!item) return { value: error("Publicação não encontrada.", 404) };
        if (publicationMatch[2] === "read" && method === "POST") { item.unread = false; item.read_at = new Date().toISOString(); return { value: json(item), write: true }; }
        if (!publicationMatch[2] && method === "GET") return { value: json(item) };
      }
      if (path === "expedientes/export.pdf" && method === "GET") {
        const items = exportItems(state, params);
        if (!items.length) return { value: error("Nenhum expediente encontrado para exportação.", 404) };
        const rows = items.flatMap((item) => params.get("mode") === "analitico"
          ? [`${item.processo.numero} | ${item.tipo_documento} | ${item.source?.tribunal ?? ""}`,
            `  ${item.processo.assunto} | ${item.tipo_pendencia_label} | ${item.prazo_texto}`]
          : [`${item.processo.numero} | ${item.tipo_documento} | ${item.source?.tribunal ?? ""} | ${item.processo.assunto}`]);
        return { value: pdfResponse("Relatório de expedientes", rows, `expedientes-demo-${localDay()}.pdf`) };
      }
      if (path === "djen/communications/export.pdf" && method === "GET") {
        const filtered = params.get("scope") === "overview" ? new URLSearchParams({ collected_from: state.seedDay, collected_to: state.seedDay }) : params;
        const items = filteredPublications(state, filtered);
        if (!items.length) return { value: error("Nenhuma publicação encontrada para exportação.", 404) };
        const rows = items.map((item) => `${item.processo.numero} | ${item.tribunal} | ${item.tipo_comunicacao} | ${item.data_disponibilizacao}`);
        return { value: pdfResponse("Publicações processuais", rows, `publicacoes-demo-${localDay()}.pdf`) };
      }
      return { value: error("Rota não disponível no ambiente de demonstração.", 404) };
    });
  } catch (cause) {
    return error(cause instanceof Error ? cause.message : "Falha no cenário de demonstração.", 409);
  }
}

export async function GET(request: NextRequest, context: Context) { return handle(request, context); }
export async function POST(request: NextRequest, context: Context) { return handle(request, context); }
export async function PATCH(request: NextRequest, context: Context) { return handle(request, context); }
