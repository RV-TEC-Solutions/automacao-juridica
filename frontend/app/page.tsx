"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "./components/app-shell";
import { Clock } from "./components/clock";
import { ExpedienteDrawer } from "./components/expediente-drawer";
import { ExpedienteList } from "./components/expediente-list";
import { Icon } from "./components/icons";
import { api, formatDateTime } from "./lib/api";
import type { Dashboard, Expediente } from "./lib/types";

function greeting() {
  const hour = Number(
    new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Fortaleza",
      hour: "numeric",
      hour12: false,
    }).format(new Date()),
  );

  return hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
}

function capitalize(value: string) {
  return value.charAt(0).toLocaleUpperCase("pt-BR") + value.slice(1);
}

export default function Home() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Expediente | null>(null);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api<Dashboard>("dashboard/"));
      setError("");
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Falha ao carregar.");
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      load().then(() => api("dashboard/", { method: "POST" }).catch(() => {}));
    });
  }, [load]);

  const run = async () => {
    setRunning(true);

    try {
      await api("automation/runs/", {
        method: "POST",
        body: JSON.stringify({ source: "pje-tjrn" }),
      });
      await load();
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Não foi possível iniciar.");
    } finally {
      setRunning(false);
    }
  };

  const dateParts = new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Fortaleza",
    weekday: "long",
    day: "2-digit",
    month: "long",
  }).formatToParts(new Date());
  const weekday = dateParts.find((part) => part.type === "weekday")?.value ?? "";
  const day = dateParts.find((part) => part.type === "day")?.value ?? "";
  const month = dateParts.find((part) => part.type === "month")?.value ?? "";
  const date = `${capitalize(weekday)}, ${day} de ${capitalize(month)}`;

  return (
    <AppShell>
      <div className="mx-auto w-[min(1240px,calc(100%-48px))] py-8 pb-[70px] max-[760px]:w-[calc(100%-28px)] max-[760px]:pt-6 max-[760px]:pb-12">
        <header className="mb-[26px] flex items-end justify-between gap-6 max-[760px]:mb-[22px] max-[760px]:items-start">
          <div>
            <h1 className="mb-[7px] text-[clamp(25px,3vw,34px)] leading-[1.15] font-bold max-[760px]:text-[29px]">
              {greeting()}, <span>{data?.display_name.split(" ")[0] ?? ""}.</span>
            </h1>
            <p className="mb-0 text-[14px] text-muted max-[760px]:max-w-[230px]">{date}</p>
          </div>
          <Clock />
        </header>

        {error && (
          <div className="mb-[14px] flex items-center justify-between gap-[18px] rounded-[7px] border border-l-[3px] border-line border-l-red bg-surface px-[14px] py-3">
            <div className="flex flex-col gap-[3px]">
              <strong>Não foi possível atualizar o painel</strong>
              <span className="text-[12px] text-muted">{error}</span>
            </div>
            <button className="flex min-w-[150px] cursor-pointer items-center justify-center gap-1.5 whitespace-nowrap rounded-md border border-line bg-surface-raised px-[9px] py-[7px] text-[12px] font-[650] text-text transition-[background-color,border-color,color,opacity] duration-[160ms] hover:border-line-strong hover:bg-surface-hover" onClick={load}>Tentar novamente</button>
          </div>
        )}

        {data?.latest_run?.status === "failed" && (
          <div className="mb-[14px] flex items-center justify-between gap-[18px] rounded-[7px] border border-l-[3px] border-line border-l-yellow bg-surface px-[14px] py-3">
            <div className="flex flex-col gap-[3px]">
              <strong>A última coleta encontrou um problema</strong>
              <span className="text-[12px] text-muted">{data.latest_run.error || "Consulte os detalhes e tente novamente."}</span>
              <small className="text-[12px] text-muted">{formatDateTime(data.latest_run.finished_at)}</small>
            </div>
            <button className="flex min-w-[150px] cursor-pointer items-center justify-center gap-1.5 whitespace-nowrap rounded-md border border-line bg-surface-raised px-[9px] py-[7px] text-[12px] font-[650] text-text transition-[background-color,border-color,color,opacity] duration-[160ms] hover:border-line-strong hover:bg-surface-hover" onClick={run}>Tentar novamente</button>
          </div>
        )}

        <div className="mb-6 flex min-h-12 items-center gap-2.5 rounded-[7px] border border-line bg-surface px-[14px] max-[760px]:flex-wrap max-[760px]:px-3 max-[760px]:py-2.5">
          <div className={`size-[7px] rounded-full bg-muted ${data?.latest_run?.status === "success" ? "bg-green" : data?.latest_run?.status === "failed" ? "bg-red" : ["pending", "running"].includes(data?.latest_run?.status ?? "") ? "bg-yellow shadow-[0_0_0_4px_var(--color-yellow-soft)]" : ""}`} />
          <span className="flex-1 text-[13px] text-muted max-[760px]:min-w-3/4">
            {data?.latest_run ? (
              <>
                Última coleta em <strong className="text-text-soft">{formatDateTime(data.latest_run.finished_at ?? data.latest_run.started_at)}</strong> ·{" "}
                {data.latest_run.status === "success"
                  ? "concluída"
                  : data.latest_run.status === "running"
                    ? "em andamento"
                    : data.latest_run.status === "pending"
                      ? "aguardando"
                      : "com erro"}
              </>
            ) : (
              "Nenhuma coleta executada"
            )}
          </span>
          <button
            className="flex cursor-pointer items-center gap-1.5 rounded-md border border-line bg-surface-raised px-[9px] py-[7px] text-[12px] font-[650] text-text transition-[background-color,border-color,color,opacity] duration-[160ms] hover:border-line-strong hover:bg-surface-hover disabled:cursor-default disabled:opacity-40"
            onClick={run}
            disabled={running || ["pending", "running"].includes(data?.latest_run?.status ?? "")}
          >
            <Icon name="sync" size={17} />
            {running ? "Solicitando…" : "Executar agora"}
          </button>
        </div>

        <section>
          <div className="mb-3 flex items-end justify-between gap-4">
            <div>
              <h2 className="mb-0 text-[21px] font-[650]">Dados gerais</h2>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-2.5 max-[1100px]:grid-cols-2 max-[760px]:gap-2">
            {[
              { label: "Novos", value: data?.today.new ?? 0, tone: "teal", note: "expedientes descobertos" },
              { label: "Alterados", value: data?.today.updated ?? 0, tone: "blue", note: "mudanças relevantes" },
              { label: "Não lidos", value: data?.today.unread ?? 0, tone: "ink", note: "aguardando sua leitura" },
              { label: "Urgentes", value: data?.today.urgent ?? 0, tone: "amber", note: "vencidos ou até 72h" },
            ].map((card) => (
              <article className={`relative flex min-h-28 flex-col rounded-[7px] border border-line bg-surface p-4 text-text before:absolute before:top-4 before:right-4 before:size-[7px] before:rounded-full before:bg-muted before:content-[''] max-[760px]:min-h-[103px] max-[760px]:p-[13px] ${card.tone === "teal" ? "before:bg-green" : card.tone === "blue" ? "before:bg-blue" : card.tone === "ink" ? "before:bg-accent" : "before:bg-yellow"}`} key={card.label}>
                <span className="text-[12px] font-[650] text-text-soft">{card.label}</span>
                <strong className="mt-auto mb-px text-[34px] leading-none font-[650] tabular-nums max-[760px]:text-[30px]">{card.value.toString().padStart(2, "0")}</strong>
                <small className="text-[11px] text-muted">{card.note}</small>
              </article>
            ))}
          </div>
          {(data?.today.calculating ?? 0) > 0 && (
            <p className="mt-2.5 mb-0 text-[12px] text-yellow">◷ {data?.today.calculating} prazo(s) ainda estão em cálculo no PJe.</p>
          )}
        </section>

        {data && (
          <section className="mt-5 mb-[26px] rounded-[7px] border border-line bg-surface-raised px-[17px] py-[15px]">
            <h2 className="mb-2 text-[16px]">Desde sua última visita</h2>
            <p className="mb-[3px] text-[14px] text-text-soft">
              <strong className="text-text">
                {data.since_last_visit.new} novo{data.since_last_visit.new === 1 ? "" : "s"}
              </strong>
              , <strong>{data.since_last_visit.updated} alterado{data.since_last_visit.updated === 1 ? "" : "s"}</strong> e{" "}
              {data.since_last_visit.resolved} resolvido{data.since_last_visit.resolved === 1 ? "" : "s"}.
            </p>
            <small className="text-[11px] text-muted">
              {data.since_last_visit.since
                ? `Desde ${formatDateTime(data.since_last_visit.since)}`
                : "Este é o seu primeiro resumo."}
            </small>
          </section>
        )}

        <section>
          <div className="mb-3 flex items-end justify-between gap-4">
            <div>
              <h2 className="mb-0 text-[21px] font-[650]">Hoje</h2>
            </div>
            <Link href="/expedientes" className="text-[13px] font-semibold text-text-soft no-underline hover:text-accent">
              Ver todos <span>→</span>
            </Link>
          </div>
          {data ? (
            <ExpedienteList items={data.recent} onSelect={setSelected} />
          ) : (
            <div className="grid gap-px">
              <i className="h-[91px] animate-[shimmer_1.5s_infinite] bg-[linear-gradient(90deg,var(--surface),var(--surface-raised),var(--surface))] bg-[length:200%]" />
              <i className="h-[91px] animate-[shimmer_1.5s_infinite] bg-[linear-gradient(90deg,var(--surface),var(--surface-raised),var(--surface))] bg-[length:200%]" />
              <i className="h-[91px] animate-[shimmer_1.5s_infinite] bg-[linear-gradient(90deg,var(--surface),var(--surface-raised),var(--surface))] bg-[length:200%]" />
            </div>
          )}
        </section>
      </div>
      <ExpedienteDrawer
        item={selected}
        onClose={() => setSelected(null)}
        onRead={() => {
          if (selected) setSelected({ ...selected, unread: false });
          load();
        }}
      />
    </AppShell>
  );
}
