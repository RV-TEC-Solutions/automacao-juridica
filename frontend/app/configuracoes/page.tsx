"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "../components/app-shell";
import { api } from "../lib/api";
import { useAuth } from "../providers";

type Settings = {
  display_name: string;
  theme: "light" | "dark" | "system";
  collection_time: string;
  timezone: string;
  credential_status: Record<string, boolean | string>;
};

type Source = {
  code: string;
  system: string;
  tribunal: string;
  enabled: boolean;
};

export default function SettingsPage() {
  const { refresh } = useAuth();
  const [data, setData] = useState<Settings | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = () =>
    Promise.all([api<Settings>("settings/"), api<Source[]>("sources/")])
      .then(([settings, items]) => {
        setData(settings);
        setSources(items);
      })
      .catch((exception) => setError(exception.message));

  useEffect(() => {
    queueMicrotask(() => {
      void load();
    });
  }, []);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);

    try {
      const value = await api<Settings>("settings/", {
        method: "PATCH",
        body: JSON.stringify({
          display_name: form.get("display_name"),
          theme: form.get("theme"),
          collection_time: form.get("collection_time"),
        }),
      });
      setData(value);
      await refresh();
      setMessage("Configurações salvas.");
      setError("");
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Falha ao salvar.");
    }
  };

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);

    if (form.get("new_password") !== form.get("confirmation")) {
      setError("A confirmação da nova senha não coincide.");
      return;
    }

    try {
      await api("auth/password/", {
        method: "POST",
        body: JSON.stringify({
          current_password: form.get("current_password"),
          new_password: form.get("new_password"),
        }),
      });
      event.currentTarget.reset();
      setMessage("Senha alterada com sucesso.");
      setError("");
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Falha ao alterar senha.");
    }
  };

  const toggle = async (source: Source) => {
    try {
      const next = await api<Source>(`sources/${source.code}/`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !source.enabled }),
      });
      setSources((values) => values.map((item) => (item.code === next.code ? next : item)));
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Falha ao atualizar fonte.");
    }
  };

  return (
    <AppShell>
      <div className="mx-auto w-[min(1240px,calc(100%-48px))] py-8 pb-[70px] max-[760px]:w-[calc(100%-28px)] max-[760px]:pt-6 max-[760px]:pb-12">
        <header className="mb-[26px] flex items-end justify-between gap-6 max-[760px]:mb-[22px] max-[760px]:items-start">
          <div>
            <h1 className="mb-[7px] text-[clamp(25px,3vw,34px)] leading-[1.15] font-bold max-[760px]:text-[29px]">Configurações</h1>
            <p className="mb-0 text-[14px] text-muted">Ajuste a experiência e verifique se a automação está pronta.</p>
          </div>
        </header>

        {error && <div className="mb-[14px] rounded-[7px] border border-l-[3px] border-line border-l-red bg-surface px-[14px] py-3 text-[12px] text-muted">{error}</div>}
        {message && <div className="mb-[14px] rounded-[7px] border border-l-[3px] border-line border-l-green bg-surface px-[14px] py-3 text-[12px] text-muted">{message}</div>}

        {data && (
          <form onSubmit={save}>
            <section className="grid grid-cols-[250px_1fr] gap-[42px] border-t border-line py-[26px] max-[760px]:grid-cols-1 max-[760px]:gap-[13px] max-[760px]:py-[22px]">
              <div>
                <h2 className="mb-1.5 text-[16px]">Seu perfil</h2>
                <p className="text-[12px] leading-[1.5] text-muted">Informações usadas na saudação e no acesso local.</p>
              </div>
              <div className="grid grid-cols-2 gap-[14px] max-[760px]:grid-cols-1">
                <label className="flex flex-col gap-[7px] text-[11px] font-[650] text-text-soft">
                  Nome de exibição
                  <input className="min-h-9 w-full rounded-[5px] border border-line bg-surface-raised px-2.5 py-2 text-[12px] text-text outline-0 focus:border-accent focus:shadow-[0_0_0_2px_var(--color-accent-soft)]" name="display_name" defaultValue={data.display_name} />
                </label>
                <label className="flex flex-col gap-[7px] text-[11px] font-[650] text-text-soft">
                  Tema
                  <select className="min-h-9 w-full rounded-[5px] border border-line bg-surface-raised px-2.5 py-2 text-[12px] text-text outline-0 focus:border-accent focus:shadow-[0_0_0_2px_var(--color-accent-soft)]" name="theme" defaultValue={data.theme}>
                    <option value="light">Claro</option>
                    <option value="dark">Escuro</option>
                    <option value="system">Seguir o sistema</option>
                  </select>
                </label>
              </div>
            </section>

            <section className="grid grid-cols-[250px_1fr] gap-[42px] border-t border-line py-[26px] max-[760px]:grid-cols-1 max-[760px]:gap-[13px] max-[760px]:py-[22px]">
              <div>
                <h2 className="mb-1.5 text-[16px]">Coleta diária</h2><p className="text-[12px] leading-[1.5] text-muted">Se o horário for perdido, a coleta acontece ao iniciar o worker.</p>
              </div>
              <div className="grid grid-cols-2 gap-[14px] max-[760px]:grid-cols-1"><label className="flex flex-col gap-[7px] text-[11px] font-[650] text-text-soft">
                  Horário
                  <input className="min-h-9 w-full rounded-[5px] border border-line bg-surface-raised px-2.5 py-2 text-[12px] text-text outline-0 focus:border-accent focus:shadow-[0_0_0_2px_var(--color-accent-soft)]" name="collection_time" type="time" defaultValue={data.collection_time} />
                </label>
                <label className="flex flex-col gap-[7px] text-[11px] font-[650] text-text-soft">
                  Fuso horário
                  <input className="min-h-9 w-full rounded-[5px] border border-line bg-surface-raised px-2.5 py-2 text-[12px] text-muted outline-0" value="America/Fortaleza" disabled />
                </label>
              </div>
            </section>
            <div className="mt-[-8px] mb-7 flex justify-end">
              <button className="min-h-[38px] cursor-pointer rounded-[5px] border border-primary-bg bg-primary-bg px-[15px] py-[9px] font-bold text-primary-text hover:bg-primary-hover">Salvar alterações</button>
            </div>
          </form>
        )}

        <section className="grid grid-cols-[250px_1fr] gap-[42px] border-t border-line py-[26px] max-[760px]:grid-cols-1 max-[760px]:gap-[13px] max-[760px]:py-[22px]">
          <div>
            <h2 className="mb-1.5 text-[16px]">Fontes</h2><p className="text-[12px] leading-[1.5] text-muted">Fontes desativadas deixam de ser coletadas, mas o histórico permanece.</p>
          </div>
          <div className="grid gap-2">
            {sources.map((source) => (
              <div className="flex items-center gap-3 rounded-md border border-line bg-surface p-3" key={source.code}>
                <span className="grid size-[34px] place-items-center rounded-md bg-accent-soft text-[13px] font-extrabold text-accent">P</span>
                <div className="flex flex-1 flex-col gap-0.5"><strong className="text-[12px]">{source.system}</strong><small className="text-[10px] text-muted">{source.tribunal} · Expedientes</small>
                </div>
                <button
                  role="switch"
                  aria-label={`Coleta ${source.system} ${source.tribunal}`}
                  aria-checked={source.enabled}
                  className={`h-[21px] w-[38px] cursor-pointer rounded-full border-0 p-[3px] ${source.enabled ? "bg-accent" : "bg-line-strong"}`}
                  onClick={() => toggle(source)}
                >
                  <i className={`block size-[15px] rounded-full transition-transform duration-[180ms] ${source.enabled ? "translate-x-[17px] bg-[#633423]" : "bg-[#ddd]"}`} />
                </button>
              </div>
            ))}
          </div>
        </section>

        {data && (
          <section className="grid grid-cols-[250px_1fr] gap-[42px] border-t border-line py-[26px] max-[760px]:grid-cols-1 max-[760px]:gap-[13px] max-[760px]:py-[22px]">
            <div>
              <h2 className="mb-1.5 text-[16px]">Prontidão do PJe</h2><p className="text-[12px] leading-[1.5] text-muted">Os valores sensíveis nunca são exibidos nem editados aqui.</p>
            </div>
            <div className="grid gap-2">
              <Check ok={Boolean(data.credential_status.credential_file)} label="Arquivo de credenciais" />
              <Check ok={Boolean(data.credential_status.pin)} label="PIN do certificado" />
              <Check ok={Boolean(data.credential_status.totp)} label="Segredo TOTP" />
              <Check ok label="PJeOffice" note="Verificado durante cada coleta" />
              <code className="rounded-[5px] bg-surface-raised p-2.5 text-[11px] text-muted">~/.config/pje-automacao/.env</code>
            </div>
          </section>
        )}

        <form onSubmit={changePassword}>
          <section className="grid grid-cols-[250px_1fr] gap-[42px] border-t border-line py-[26px] max-[760px]:grid-cols-1 max-[760px]:gap-[13px] max-[760px]:py-[22px]">
            <div>
              <h2 className="mb-1.5 text-[16px]">Senha de acesso</h2><p className="text-[12px] leading-[1.5] text-muted">Altere a senha usada somente nesta instalação local.</p>
            </div>
            <div className="grid grid-cols-2 gap-[14px] max-[760px]:grid-cols-1">
              <label className="flex flex-col gap-[7px] text-[11px] font-[650] text-text-soft">
                Senha atual
                <input className="min-h-9 w-full rounded-[5px] border border-line bg-surface-raised px-2.5 py-2 text-[12px] text-text outline-0 focus:border-accent focus:shadow-[0_0_0_2px_var(--color-accent-soft)]" name="current_password" type="password" autoComplete="current-password" required />
              </label>
              <label className="flex flex-col gap-[7px] text-[11px] font-[650] text-text-soft">
                Nova senha
                <input className="min-h-9 w-full rounded-[5px] border border-line bg-surface-raised px-2.5 py-2 text-[12px] text-text outline-0 focus:border-accent focus:shadow-[0_0_0_2px_var(--color-accent-soft)]" name="new_password" type="password" minLength={8} autoComplete="new-password" required />
              </label>
              <label className="flex flex-col gap-[7px] text-[11px] font-[650] text-text-soft">
                Confirmar nova senha
                <input className="min-h-9 w-full rounded-[5px] border border-line bg-surface-raised px-2.5 py-2 text-[12px] text-text outline-0 focus:border-accent focus:shadow-[0_0_0_2px_var(--color-accent-soft)]" name="confirmation" type="password" minLength={8} autoComplete="new-password" required />
              </label>
              <button className="min-h-[38px] cursor-pointer self-end rounded-[5px] border border-primary-bg bg-primary-bg px-[15px] py-[9px] font-bold text-primary-text hover:bg-primary-hover">Alterar senha</button>
            </div>
          </section>
        </form>
      </div>
    </AppShell>
  );
}

function Check({ ok, label, note }: { ok: boolean; label: string; note?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-line bg-surface p-3">
      <span className={`grid size-[23px] place-items-center rounded-full text-[11px] font-extrabold ${ok ? "bg-green-soft text-green" : "bg-yellow-soft text-yellow"}`}>{ok ? "✓" : "!"}</span>
      <div className="flex flex-1 flex-col gap-0.5"><strong className="text-[12px]">{label}</strong><small className="text-[10px] text-muted">{note ?? (ok ? "Configurado" : "Configuração ausente")}</small>
      </div>
    </div>
  );
}
