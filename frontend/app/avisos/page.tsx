"use client";

import { ArrowSquareOut, Check, SpinnerGap, Tray } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { AppShell } from "../components/app-shell";
import { Panel, Feedback, LoadingRows, PageTitle } from "../components/ui";
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
      window.dispatchEvent(new Event("notices:changed"));
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Não foi possível atualizar o aviso.");
    } finally {
      setReading(null);
    }
  };

  return (
    <AppShell>
      <PageTitle title="Avisos do PJe" description="Comunicados recebidos nas fontes conectadas e confirmados com segurança no PJe." />

      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <p className="m-0 text-sm font-medium text-muted-foreground">{data ? `${data.count} comunicado${data.count === 1 ? "" : "s"} no histórico` : "Carregando histórico…"}</p>
        <Button
          variant={onlyUnread ? "default" : "outline"}
          size="sm"
          aria-pressed={onlyUnread}
          onClick={() => setOnlyUnread((value) => !value)}
        >
          Somente não lidos
        </Button>
      </div>

      {error && <Feedback action={<Button variant="outline" size="sm" onClick={load}>Tentar novamente</Button>}>{error}</Feedback>}
      {!data && !error && <LoadingRows />}

      <div className="space-y-4">
        {data?.results.map((notice) => (
          <Panel key={notice.id} innerClassName="p-6">
            <article aria-label={notice.title}>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    {notice.unread && <span className="rounded-full bg-warning-soft px-2 py-2 text-xs font-extrabold tracking-wide text-warning">NÃO LIDO</span>}
                    <span className="text-xs font-semibold text-muted-foreground">Publicado {formatDateTime(notice.published_at, { dateStyle: "short", timeStyle: undefined })}</span>
                  </div>
                  <h2 className="m-0 text-base font-extrabold tracking-tight text-foreground sm:text-lg">{notice.title}</h2>
                  {(notice.included_by || notice.included_at) && <p className="mb-0 mt-2 text-xs text-muted-foreground">Incluído por {notice.included_by || "autor não informado"}{notice.included_at ? ` em ${formatDateTime(notice.included_at)}` : ""}</p>}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!notice.unread || reading === notice.id}
                  onClick={() => markRead(notice)}
                >
                  {reading === notice.id ? <SpinnerGap className="animate-spin" size={15} /> : <Check size={15} weight="bold" />}
                  {notice.unread ? "Marcar como lido" : "Lido"}
                </Button>
              </div>

              <div className="notice-content mt-6 border-t border-border pt-4 text-sm leading-7 text-foreground" dangerouslySetInnerHTML={{ __html: notice.content_html }} />
              <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-border pt-4">
                <span className="mr-2 text-xs font-extrabold tracking-wide text-muted-foreground uppercase">Origens</span>
                {notice.sources.map((source) => <span key={source.code} className="rounded-md border border-border bg-muted px-2 py-2 text-xs font-bold text-foreground">{source.system}</span>)}
                {notice.links.length > 0 && <span className="ml-auto flex items-center gap-2 text-xs font-bold text-muted-foreground"><ArrowSquareOut size={13} /> Links preservados no comunicado</span>}
              </div>
            </article>
          </Panel>
        ))}
        {data?.results.length === 0 && <Panel innerClassName="grid place-items-center gap-4 p-12 text-center"><Tray size={28} className="text-muted-foreground" weight="duotone" /><div><strong className="block text-sm text-foreground">Nenhum aviso encontrado</strong><span className="text-xs text-muted-foreground">Os próximos comunicados recebidos no PJe aparecerão aqui.</span></div></Panel>}
      </div>
    </AppShell>
  );
}
