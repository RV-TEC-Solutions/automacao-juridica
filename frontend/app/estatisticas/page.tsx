"use client";

import { useEffect, useState } from "react";

import { AppShell } from "../components/app-shell";
import { api } from "../lib/api";

type Stats = {
  period: number;
  totals: {
    current: number;
    previous: number;
    change_percent: number | null;
    new?: number;
    updated?: number;
    resolved?: number;
  };
  timeline: { day: string; kind: string; total: number }[];
  pending_distribution: { tipo_pendencia: string; total: number }[];
  deadline_distribution: { status_prazo_fatal: string; total: number }[];
};

const kindLabel: Record<string, string> = {
  new: "Novos",
  updated: "Alterados",
  resolved: "Resolvidos",
  ciencia: "Ciência",
  resposta: "Resposta",
  nao_identificada: "Outros",
  calculado: "Calculado",
  em_calculo: "Em cálculo",
  sem_prazo: "Sem prazo",
};

export default function StatisticsPage() {
  const [period, setPeriod] = useState(7);
  const [data, setData] = useState<Stats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Stats>(`statistics/?period=${period}`)
      .then(setData)
      .catch((exception) => setError(exception.message));
  }, [period]);

  const max = Math.max(1, ...(data?.timeline.map((row) => row.total) ?? [1]));

  return (
    <AppShell>
      <div className="mx-auto w-[min(1240px,calc(100%-48px))] py-8 pb-[70px] max-[760px]:w-[calc(100%-28px)] max-[760px]:pt-6 max-[760px]:pb-12">
        <header className="mb-[26px] flex items-end justify-between gap-6 max-[760px]:mb-[22px] max-[760px]:items-start">
          <div>
            <h1 className="mb-[7px] text-[clamp(25px,3vw,34px)] leading-[1.15] font-bold max-[760px]:text-[29px]">Estatísticas</h1>
          </div>
          <div className="flex rounded-md border border-line bg-surface p-[3px]">
            <button className={`cursor-pointer rounded border-0 px-3 py-[7px] text-[12px] ${period === 7 ? "bg-surface-hover text-text" : "bg-transparent text-muted"}`} onClick={() => setPeriod(7)}>
              7 dias
            </button>
            <button className={`cursor-pointer rounded border-0 px-3 py-[7px] text-[12px] ${period === 30 ? "bg-surface-hover text-text" : "bg-transparent text-muted"}`} onClick={() => setPeriod(30)}>
              30 dias
            </button>
          </div>
        </header>

        {error && <div className="mb-[14px] rounded-[7px] border border-l-[3px] border-line border-l-red bg-surface px-[14px] py-3 text-[12px] text-muted">{error}</div>}
        {data && (
          <>
            <div className="mb-3 grid grid-cols-[1.5fr_repeat(3,1fr)] gap-2.5 max-[1100px]:grid-cols-2 max-[760px]:grid-cols-2">
              <article className="flex flex-col rounded-[7px] border border-line bg-surface p-[17px] max-[760px]:col-span-2">
                <span className="text-[11px] font-[650] text-muted">Atividade no período</span>
                <strong className="mt-3 mb-[3px] text-[31px] leading-none font-[650] tabular-nums">{data.totals.current}</strong>
                <small className="text-[11px] text-muted">
                  {data.totals.change_percent === null
                    ? "Sem período anterior para comparar"
                    : `${data.totals.change_percent >= 0 ? "↑" : "↓"} ${Math.abs(data.totals.change_percent)}% ante o período anterior`}
                </small>
              </article>
              <article className="flex flex-col rounded-[7px] border border-line bg-surface p-[17px]"><span className="text-[11px] font-[650] text-muted">Novos</span><strong className="mt-3 mb-[3px] text-[31px] leading-none font-[650] tabular-nums">{data.totals.new ?? 0}</strong><small className="text-[11px] text-muted">expedientes descobertos</small>
              </article>
              <article className="flex flex-col rounded-[7px] border border-line bg-surface p-[17px]"><span className="text-[11px] font-[650] text-muted">Alterados</span><strong className="mt-3 mb-[3px] text-[31px] leading-none font-[650] tabular-nums">{data.totals.updated ?? 0}</strong><small className="text-[11px] text-muted">mudanças relevantes</small>
              </article>
              <article className="flex flex-col rounded-[7px] border border-line bg-surface p-[17px]"><span className="text-[11px] font-[650] text-muted">Resolvidos</span><strong className="mt-3 mb-[3px] text-[31px] leading-none font-[650] tabular-nums">{data.totals.resolved ?? 0}</strong><small className="text-[11px] text-muted">saíram da caixa</small>
              </article>
            </div>

            <section className="mb-3 flex h-[330px] flex-col rounded-[7px] border border-line bg-surface p-[17px]">
              <div className="mb-3 flex items-end justify-between gap-4">
                <div>
                  <h2 className="mb-0 text-[18px] font-[650]">Chegadas e mudanças</h2>
                </div>
                <div className="flex gap-[15px] text-[10px] text-muted">
                  <span className="before:mr-[5px] before:inline-block before:size-[6px] before:rounded-[2px] before:bg-green before:content-['']">Novos</span>
                  <span className="before:mr-[5px] before:inline-block before:size-[6px] before:rounded-[2px] before:bg-blue before:content-['']">Alterados</span>
                </div>
              </div>
              {data.timeline.length ? (
                <div className="flex h-[215px] items-end gap-[5px] border-b border-line px-2.5 pt-2.5">
                  {data.timeline.map((row, index) => (
                    <div
                      className={`min-w-1 max-w-[23px] flex-1 rounded-t-[3px] bg-green ${row.kind === "updated" ? "bg-blue" : row.kind === "resolved" ? "bg-muted" : ""}`}
                      key={`${row.day}-${row.kind}-${index}`}
                      style={{ height: `${Math.max(8, (row.total / max) * 100)}%` }}
                      title={`${row.day}: ${row.total} ${kindLabel[row.kind]}`}
                    />
                  ))}
                </div>
              ) : (
                <div className="rounded-[7px] border border-dashed border-line-strong p-7 text-center text-muted">
                  <h3 className="my-2 text-[15px] text-text">Nenhuma atividade neste período</h3>
                </div>
              )}
            </section>

            <div className="grid grid-cols-2 gap-3 max-[760px]:grid-cols-1">
              <Distribution
                title="Pendências ativas"
                rows={data.pending_distribution.map((row) => ({
                  label: kindLabel[row.tipo_pendencia] ?? row.tipo_pendencia,
                  total: row.total,
                }))}
              />
              <Distribution
                title="Situação dos prazos"
                rows={data.deadline_distribution.map((row) => ({
                  label: kindLabel[row.status_prazo_fatal] ?? row.status_prazo_fatal,
                  total: row.total,
                }))}
              />
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

function Distribution({
  title,
  rows,
}: {
  title: string;
  rows: { label: string; total: number }[];
}) {
  const total = rows.reduce((sum, row) => sum + row.total, 0) || 1;

  return (
    <section className="rounded-[7px] border border-line bg-surface p-[17px]">
      <h2 className="text-[17px]">{title}</h2>
      {rows.length ? (
        rows.map((row) => (
          <div className="mt-[14px]" key={row.label}>
            <div className="mb-1.5 flex justify-between text-[12px] text-text-soft">
              <span>{row.label}</span>
              <strong>{row.total}</strong>
            </div>
            <i className="block h-[5px] overflow-hidden rounded-[3px] bg-surface-raised">
              <b className="block h-full bg-accent" style={{ width: `${(row.total / total) * 100}%` }} />
            </i>
          </div>
        ))
      ) : (
        <p>Nenhum expediente ativo.</p>
      )}
    </section>
  );
}
