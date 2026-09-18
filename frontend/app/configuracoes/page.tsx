"use client";

import { CheckCircle, Clock, FloppyDisk, Key, ShieldCheck, UserCircle } from "@phosphor-icons/react";
import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "../components/app-shell";
import { BezelCard, Feedback, PageTitle } from "../components/ui";
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

const fieldClass =
  "control mt-1.5 w-full px-3.5 py-2 text-xs sm:text-sm font-semibold";

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
      setMessage("Configurações salvas com sucesso.");
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
      setMessage("Senha de acesso alterada com sucesso.");
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
      <PageTitle
        eyebrow="Preferências e integração"
        title="Configurações"
        description="Ajuste suas preferências operacionais, credenciais do PJe e rotinas automáticas da banca."
      />

      {error && <Feedback>{error}</Feedback>}
      {message && <Feedback tone="success">{message}</Feedback>}

      {data && (
        <form onSubmit={save} className="grid gap-6 lg:grid-cols-2">
          {/* Perfil */}
          <BezelCard innerClassName="p-6">
            <div className="mb-5 flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl border border-rule bg-panel-muted text-ink">
                <UserCircle size={22} weight="duotone" />
              </span>
              <div>
                <h2 className="mb-0.5 text-sm font-extrabold text-ink">Seu perfil</h2>
                <p className="mb-0 text-xs text-quiet font-medium">
                  Informações de identificação no painel.
                </p>
              </div>
            </div>

            <label className="block text-xs font-bold text-ink-soft">
              Nome de exibição
              <input className={fieldClass} name="display_name" defaultValue={data.display_name} />
            </label>

            <label className="mt-4 block text-xs font-bold text-ink-soft">
              Tema visual
              <select className={fieldClass} name="theme" defaultValue={data.theme}>
                <option value="light">Claro (Executive Gray)</option>
                <option value="dark">Escuro (Obsidian Graphite)</option>
                <option value="system">Seguir o sistema operacional</option>
              </select>
            </label>
          </BezelCard>

          {/* Coleta diária */}
          <BezelCard innerClassName="p-6">
            <div className="mb-5 flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl border border-rule bg-panel-muted text-ink">
                <Clock size={22} weight="duotone" />
              </span>
              <div>
                <h2 className="mb-0.5 text-sm font-extrabold text-ink">Rotina de coleta</h2>
                <p className="mb-0 text-xs text-quiet font-medium">
                  Agendamento automático de consultas aos tribunais.
                </p>
              </div>
            </div>

            <label className="block text-xs font-bold text-ink-soft">
              Horário diário
              <input
                className={fieldClass}
                name="collection_time"
                type="time"
                defaultValue={data.collection_time}
              />
            </label>

            <label className="mt-4 block text-xs font-bold text-ink-soft">
              Fuso horário de referência
              <input className={`${fieldClass} opacity-70 cursor-not-allowed`} value="America/Fortaleza (GMT-3)" disabled />
            </label>
          </BezelCard>

          <div className="flex justify-end lg:col-span-2">
            <button type="submit" className="button-primary cursor-pointer px-5 text-sm font-bold shadow-xs">
              <FloppyDisk size={16} weight="bold" />
              Salvar alterações
            </button>
          </div>
        </form>
      )}

      {/* Fontes conectadas e Prontidão */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <BezelCard innerClassName="p-6">
          <div className="mb-5 flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-xl border border-rule bg-panel-muted text-ink">
              <ShieldCheck size={22} weight="duotone" />
            </span>
            <div>
              <h2 className="mb-0.5 text-sm font-extrabold text-ink">Fontes conectadas</h2>
              <p className="mb-0 text-xs text-quiet font-medium">
                Desativar uma fonte interrompe coletas mas preserva o histórico.
              </p>
            </div>
          </div>

          <div className="space-y-2.5">
            {sources.map((source) => (
              <div
                className="flex items-center gap-3.5 rounded-xl border border-rule bg-panel-muted/50 p-3.5"
                key={source.code}
              >
                <span className="grid size-9 place-items-center rounded-lg border border-rule bg-panel text-xs font-extrabold text-ink font-mono">
                  PJe
                </span>
                <div className="min-w-0 flex-1">
                  <strong className="block truncate text-xs sm:text-sm font-bold text-ink">
                    {source.system} · {source.tribunal}
                  </strong>
                  <small className="text-[11px] text-quiet font-medium">
                    Monitoramento de expedientes e intimações
                  </small>
                </div>
                <button
                  role="switch"
                  aria-label={`Coleta ${source.system} ${source.tribunal}`}
                  aria-checked={source.enabled}
                  className={`relative h-6 w-11 cursor-pointer rounded-full border-0 p-1 transition-colors ${
                    source.enabled ? "bg-brand" : "bg-quiet/40"
                  }`}
                  onClick={() => toggle(source)}
                >
                  <i
                    className={`block size-4 rounded-full bg-white shadow-xs transition-transform ${
                      source.enabled ? "translate-x-5" : ""
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </BezelCard>

        {data && (
          <BezelCard innerClassName="p-6">
            <div className="mb-5 flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl border border-rule bg-panel-muted text-positive">
                <CheckCircle size={22} weight="duotone" />
              </span>
              <div>
                <h2 className="mb-0.5 text-sm font-extrabold text-ink">Prontidão operacional</h2>
                <p className="mb-0 text-xs text-quiet font-medium">
                  Status dos certificados e chaves de segurança locais.
                </p>
              </div>
            </div>

            <div className="space-y-2.5">
              <Check ok={Boolean(data.credential_status.credential_file)} label="Arquivo de credenciais" />
              <Check ok={Boolean(data.credential_status.pin)} label="PIN do certificado digital A1/A3" />
              <Check ok={Boolean(data.credential_status.totp)} label="Segredo TOTP de dois fatores" />
              <Check ok label="PJeOffice Integrado" note="Verificado e autenticado a cada coleta" />
              <code className="mt-2.5 block rounded-xl border border-rule bg-panel-muted/60 p-2.5 text-[11px] font-mono text-quiet">
                ~/.config/pje-automacao/.env
              </code>
            </div>
          </BezelCard>
        )}
      </div>

      {/* Alteração de senha */}
      <form onSubmit={changePassword} className="mt-6">
        <BezelCard innerClassName="p-6">
          <div className="mb-5 flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-xl border border-rule bg-panel-muted text-caution">
              <Key size={22} weight="duotone" />
            </span>
            <div>
              <h2 className="mb-0.5 text-sm font-extrabold text-ink">Segurança e senha de acesso</h2>
              <p className="mb-0 text-xs text-quiet font-medium">
                Altere a chave de acesso utilizada exclusivamente nesta máquina.
              </p>
            </div>
          </div>

          <div className="grid gap-3.5 md:grid-cols-4">
            <label className="text-xs font-bold text-ink-soft">
              Senha atual
              <input
                className={fieldClass}
                name="current_password"
                type="password"
                autoComplete="current-password"
                required
              />
            </label>
            <label className="text-xs font-bold text-ink-soft">
              Nova senha
              <input
                className={fieldClass}
                name="new_password"
                type="password"
                minLength={8}
                autoComplete="new-password"
                required
              />
            </label>
            <label className="text-xs font-bold text-ink-soft">
              Confirmar nova senha
              <input
                className={fieldClass}
                name="confirmation"
                type="password"
                minLength={8}
                autoComplete="new-password"
                required
              />
            </label>
            <div className="flex items-end">
              <button
                type="submit"
                className="button-secondary cursor-pointer w-full px-4 text-xs font-bold h-[2.625rem]"
              >
                Alterar senha
              </button>
            </div>
          </div>
        </BezelCard>
      </form>
    </AppShell>
  );
}

function Check({ ok, label, note }: { ok: boolean; label: string; note?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-rule bg-panel-muted/50 p-3">
      <span
        className={`grid size-6 place-items-center rounded-full text-xs font-bold ${
          ok ? "bg-positive-soft text-positive border border-positive/30" : "bg-caution-soft text-caution border border-caution/30"
        }`}
      >
        {ok ? "✓" : "!"}
      </span>
      <div>
        <strong className="block text-xs text-ink font-bold">{label}</strong>
        <small className="text-[11px] text-quiet font-medium">
          {note ?? (ok ? "Configurado e operacional" : "Configuração ausente")}
        </small>
      </div>
    </div>
  );
}
