"use client";

import { CheckCircle, Clock, FloppyDisk, Key, ShieldCheck, UserCircle } from "@phosphor-icons/react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { AppShell } from "../components/app-shell";
import { RecordList } from "../components/record-list";
import { Panel, PageTitle } from "../components/ui";
import { useNotifications } from "../components/notifications";
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
  const { notify } = useNotifications();
  const [data, setData] = useState<Settings | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [updatingSources, setUpdatingSources] = useState(false);

  const load = useCallback(() =>
    Promise.all([api<Settings>("settings/"), api<Source[]>("sources/")])
      .then(([settings, items]) => {
        setData(settings);
        setSources(items);
      })
      .catch((exception) => notify({ message: exception instanceof Error ? exception.message : "Não foi possível carregar as configurações." })), [notify]);

  useEffect(() => {
    queueMicrotask(() => {
      void load();
    });
  }, [load]);

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
      notify({ tone: "success", message: "Configurações salvas." });
    } catch (exception) {
      notify({ message: exception instanceof Error ? exception.message : "Falha ao salvar." });
    }
  };

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (form.get("new_password") !== form.get("confirmation")) {
      notify({ message: "A confirmação da nova senha não coincide." });
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
      notify({ tone: "success", message: "Senha de acesso alterada." });
    } catch (exception) {
      notify({ message: exception instanceof Error ? exception.message : "Falha ao alterar senha." });
    }
  };

  const updateSources = async (items: Source[], enabled: boolean) => {
    const changed = items.filter((source) => source.enabled !== enabled);
    if (!changed.length) return;
    setUpdatingSources(true);
    try {
      const results = await Promise.allSettled(changed.map((source) => api<Source>(`sources/${source.code}/`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      })));
      const updated = new Map<string, Source>();
      results.forEach((result, index) => {
        if (result.status === "fulfilled") updated.set(changed[index].code, result.value);
      });
      setSources((current) => current.map((source) => updated.get(source.code) ?? source));
      const failed = results.filter((result) => result.status === "rejected").length;
      if (failed) notify({ message: `${failed} fonte${failed === 1 ? " não pôde" : "s não puderam"} ser atualizada${failed === 1 ? "" : "s"}.` });
    } finally {
      setUpdatingSources(false);
    }
  };

  return (
    <AppShell>
      <PageTitle
        title="Configurações"
        description="Ajuste suas preferências operacionais, credenciais do PJe e rotinas automáticas da banca."
      />

      {data && (
        <form onSubmit={save} className="grid gap-6 lg:grid-cols-2">
          {/* Perfil */}
          <Panel innerClassName="p-6">
            <div className="mb-6 flex items-center gap-4">
              <span className="grid size-10 place-items-center rounded-xl border border-border bg-muted text-foreground">
                <UserCircle size={22} weight="duotone" />
              </span>
              <div>
                <h2 className="mb-2 text-sm font-extrabold text-foreground">Seu perfil</h2>
                <p className="mb-0 text-xs text-muted-foreground font-medium">
                  Informações de identificação no painel.
                </p>
              </div>
            </div>

            <Label className="block text-xs">
              Nome de exibição
              <Input className="mt-2" name="display_name" defaultValue={data.display_name} />
            </Label>

            <Label className="mt-4 block text-xs">
              Tema visual
              <Select className="mt-2" name="theme" defaultValue={data.theme}>
                <option value="light">Claro (Executive Gray)</option>
                <option value="dark">Escuro (Obsidian Graphite)</option>
                <option value="system">Seguir o sistema operacional</option>
              </Select>
            </Label>
          </Panel>

          {/* Coleta diária */}
          <Panel innerClassName="p-6">
            <div className="mb-6 flex items-center gap-4">
              <span className="grid size-10 place-items-center rounded-xl border border-border bg-muted text-foreground">
                <Clock size={22} weight="duotone" />
              </span>
              <div>
                <h2 className="mb-2 text-sm font-extrabold text-foreground">Rotina de coleta</h2>
                <p className="mb-0 text-xs text-muted-foreground font-medium">
                  Agendamento automático de consultas aos tribunais.
                </p>
              </div>
            </div>

            <Label className="block text-xs">
              Horário diário
              <Input
                className="mt-2"
                name="collection_time"
                type="time"
                defaultValue={data.collection_time}
              />
            </Label>

            <Label className="mt-4 block text-xs">
              Fuso horário de referência
              <Input className="mt-2" value="America/Fortaleza (GMT-3)" disabled />
            </Label>
          </Panel>

          <div className="flex justify-end lg:col-span-2">
            <Button type="submit">
              <FloppyDisk size={16} weight="bold" />
              Salvar alterações
            </Button>
          </div>
        </form>
      )}

      {/* Fontes conectadas e Prontidão */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel innerClassName="p-6">
          <div className="mb-6 flex items-center gap-4">
            <span className="grid size-10 place-items-center rounded-xl border border-border bg-muted text-foreground">
              <ShieldCheck size={22} weight="duotone" />
            </span>
            <div>
              <h2 className="mb-2 text-sm font-extrabold text-foreground">Fontes conectadas</h2>
              <p className="mb-0 text-xs text-muted-foreground font-medium">
                Desativar uma fonte interrompe coletas mas preserva o histórico.
              </p>
            </div>
          </div>

          <RecordList>
            <li className="flex min-h-16 items-center gap-4 bg-muted/50 px-4 py-3">
              <div className="min-w-0 flex-1">
                <strong className="block text-xs font-bold text-foreground sm:text-sm">Todas as fontes</strong>
                <small className="text-xs text-muted-foreground">Habilitar ou desabilitar a coleta em todas as fontes</small>
              </div>
              <Switch aria-label="Habilitar todas as fontes" checked={sources.length > 0 && sources.every((source) => source.enabled)} disabled={!sources.length || updatingSources} onCheckedChange={(checked) => { void updateSources(sources, checked); }} />
            </li>
            {sources.map((source) => (
              <li
                className="flex min-h-16 items-center gap-4 px-4 py-3"
                key={source.code}
              >
                <span className="grid size-10 shrink-0 place-items-center rounded-lg border border-border bg-card text-xs font-extrabold text-foreground font-mono">
                  PJe
                </span>
                <div className="min-w-0 flex-1">
                  <strong className="block truncate text-xs sm:text-sm font-bold text-foreground">
                    {source.system} · {source.tribunal}
                  </strong>
                  <small className="text-xs text-muted-foreground font-medium">
                    Monitoramento de expedientes e intimações
                  </small>
                </div>
                <Switch
                  aria-label={`Coleta ${source.system} ${source.tribunal}`}
                  checked={source.enabled}
                  disabled={updatingSources}
                  onCheckedChange={(checked) => { void updateSources([source], checked); }}
                />
              </li>
            ))}
          </RecordList>
        </Panel>

        {data && (
          <Panel innerClassName="p-6">
            <div className="mb-6 flex items-center gap-4">
              <span className="grid size-10 place-items-center rounded-xl border border-border bg-muted text-success">
                <CheckCircle size={22} weight="duotone" />
              </span>
              <div>
                <h2 className="mb-2 text-sm font-extrabold text-foreground">Prontidão operacional</h2>
                <p className="mb-0 text-xs text-muted-foreground font-medium">
                  Status dos certificados e chaves de segurança locais.
                </p>
              </div>
            </div>

            <RecordList>
              <Check ok={Boolean(data.credential_status.credential_file)} label="Arquivo de credenciais" />
              <Check ok={Boolean(data.credential_status.pin)} label="PIN do certificado digital A1/A3" />
              <Check ok={Boolean(data.credential_status.totp)} label="Segredo TOTP de dois fatores" />
              <Check ok label="PJeOffice Integrado" note="Verificado e autenticado a cada coleta" />
            </RecordList>
            <code className="mt-2 block rounded-xl border border-border bg-muted/60 p-2 text-xs font-mono text-muted-foreground">
              ~/.config/pje-automacao/.env
            </code>
          </Panel>
        )}
      </div>

      {/* Alteração de senha */}
      <form onSubmit={changePassword} className="mt-6">
        <Panel innerClassName="p-6">
          <div className="mb-6 flex items-center gap-4">
            <span className="grid size-10 place-items-center rounded-xl border border-border bg-muted text-warning">
              <Key size={22} weight="duotone" />
            </span>
            <div>
              <h2 className="mb-2 text-sm font-extrabold text-foreground">Segurança e senha de acesso</h2>
              <p className="mb-0 text-xs text-muted-foreground font-medium">
                Altere a chave de acesso utilizada exclusivamente nesta máquina.
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            <Label className="text-xs">
              Senha atual
              <Input
                className="mt-2"
                name="current_password"
                type="password"
                autoComplete="current-password"
                required
              />
            </Label>
            <Label className="text-xs">
              Nova senha
              <Input
                className="mt-2"
                name="new_password"
                type="password"
                minLength={8}
                autoComplete="new-password"
                required
              />
            </Label>
            <Label className="text-xs">
              Confirmar nova senha
              <Input
                className="mt-2"
                name="confirmation"
                type="password"
                minLength={8}
                autoComplete="new-password"
                required
              />
            </Label>
            <div className="flex items-end">
              <Button type="submit" variant="outline" className="w-full">
                Alterar senha
              </Button>
            </div>
          </div>
        </Panel>
      </form>
    </AppShell>
  );
}

function Check({ ok, label, note }: { ok: boolean; label: string; note?: string }) {
  return (
    <li className="flex min-h-16 items-center gap-4 px-4 py-3">
      <span
        className={`grid size-6 place-items-center rounded-full text-xs font-bold ${
          ok ? "bg-success-soft text-success border border-success/30" : "bg-warning-soft text-warning border border-warning/30"
        }`}
      >
        {ok ? "✓" : "!"}
      </span>
      <div>
        <strong className="block text-xs text-foreground font-bold">{label}</strong>
        <small className="text-xs text-muted-foreground font-medium">
          {note ?? (ok ? "Configurado e operacional" : "Configuração ausente")}
        </small>
      </div>
    </li>
  );
}
