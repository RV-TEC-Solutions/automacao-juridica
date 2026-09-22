"use client";

import { ArrowSquareOut, Check, SpinnerGap, Tray } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "../components/app-shell";
import { BezelCard, Feedback, LoadingRows, PageTitle } from "../components/ui";
import { api, formatDateTime } from "../lib/api";
import type { Notice, NoticePage } from "../lib/types";

export default function NoticesPage() {
  const [data, setData] = useState<NoticePage | null>(null);
  const [onlyUnread, setOnlyUnread] = useState(false);
  const [error, setError] = useState("");
  const [reading, setReading] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await api<NoticePage>(`notices/${onlyUnread ? "?read=unread" : ""}`));
      setError("");
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Não foi possível carregar os avisos.");
    }
  }, [onlyUnread]);

  useEffect(() => { queueMicrotask(() => { void load(); }); }, [load]);

  const markRead = async (notice: Notice) => {
    if (!notice.unread) return;
    setReading(notice.id);
    try {
      const updated = await api<Notice>(`notices/${notice.id}/read/`, { method: "POST" });
      setData((current) => current ? { ...current, results: current.results.map((item) => item.id === updated.id ? updated : item) } : current);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Não foi possível atualizar o aviso.");
    } finally {
      setReading(null);
    }
  };

  return (
    <AppShell>
      <PageTitle eyebrow="Central de comunicações" title="Avisos do PJe" description="Comunicados recebidos nas fontes conectadas e confirmados com segurança no PJe." />

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <p className="m-0 text-sm font-medium text-quiet">{data ? `${data.count} comunicado${data.count === 1 ? "" : "s"} no histórico` : "Carregando histórico…"}</p>
        <button
          className={`cursor-pointer rounded-lg border px-3 py-2 text-xs font-extrabold transition-colors ${onlyUnread ? "border-brand bg-brand text-brand-fg" : "border-rule bg-panel text-ink-soft hover:bg-panel-muted"}`}
          aria-pressed={onlyUnread}
          onClick={() => setOnlyUnread((value) => !value)}
        >
          Somente não lidos
        </button>
      </div>

      {error && <Feedback action={<button className="button-secondary cursor-pointer px-3 py-1.5 text-xs font-bold" onClick={load}>Tentar novamente</button>}>{error}</Feedback>}
      {!data && !error && <LoadingRows />}

      <div className="space-y-4">
        {data?.results.map((notice) => (
          <BezelCard key={notice.id} innerClassName="p-5 sm:p-6">
            <article aria-label={notice.title}>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    {notice.unread && <span className="rounded-full bg-caution-soft px-2 py-0.5 text-[10px] font-extrabold tracking-wide text-caution">NÃO LIDO</span>}
                    <span className="text-xs font-semibold text-quiet">Publicado {formatDateTime(notice.published_at, { dateStyle: "medium", timeStyle: undefined })}</span>
                  </div>
                  <h2 className="m-0 text-base font-extrabold tracking-tight text-ink sm:text-lg">{notice.title}</h2>
                  {(notice.included_by || notice.included_at) && <p className="mb-0 mt-1.5 text-xs text-quiet">Incluído por {notice.included_by || "autor não informado"}{notice.included_at ? ` em ${formatDateTime(notice.included_at)}` : ""}</p>}
                </div>
                <button
                  className="button-secondary shrink-0 cursor-pointer px-3 py-2 text-xs font-bold disabled:cursor-wait"
                  disabled={!notice.unread || reading === notice.id}
                  onClick={() => markRead(notice)}
                >
                  {reading === notice.id ? <SpinnerGap className="animate-spin" size={15} /> : <Check size={15} weight="bold" />}
                  {notice.unread ? "Marcar como lido" : "Lido"}
                </button>
              </div>

              <div className="notice-content mt-5 border-t border-rule pt-4 text-sm leading-7 text-ink-soft" dangerouslySetInnerHTML={{ __html: notice.content_html }} />
              <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-rule pt-3">
                <span className="mr-1 text-[10px] font-extrabold tracking-[.12em] text-quiet uppercase">Origens</span>
                {notice.sources.map((source) => <span key={source.code} className="rounded-md border border-rule bg-panel-muted px-2 py-1 text-[10px] font-bold text-ink-soft">{source.system}</span>)}
                {notice.links.length > 0 && <span className="ml-auto flex items-center gap-1 text-xs font-bold text-quiet"><ArrowSquareOut size={13} /> Links preservados no comunicado</span>}
              </div>
            </article>
          </BezelCard>
        ))}
        {data?.results.length === 0 && <BezelCard innerClassName="grid place-items-center gap-3 p-12 text-center"><Tray size={28} className="text-quiet" weight="duotone" /><div><strong className="block text-sm text-ink">Nenhum aviso encontrado</strong><span className="text-xs text-quiet">Os próximos comunicados recebidos no PJe aparecerão aqui.</span></div></BezelCard>}
      </div>
    </AppShell>
  );
}
