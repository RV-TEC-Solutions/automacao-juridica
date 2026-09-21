"use client";

import { ArrowRight, CheckCircle, LockKey, ShieldCheck, User } from "@phosphor-icons/react";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Brand } from "../components/app-shell";
import { useAuth } from "../providers";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/");
  }, [loading, user, router]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await login(String(form.get("username")), String(form.get("password")));
      router.replace("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Credenciais inválidas ou serviço indisponível.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="grid min-h-screen place-items-center overflow-hidden bg-app p-4 sm:p-6 relative before:fixed before:inset-0 before:bg-[radial-gradient(circle_at_20%_20%,color-mix(in_srgb,var(--quiet)_10%,transparent),transparent_40%),radial-gradient(circle_at_80%_80%,color-mix(in_srgb,var(--brand)_8%,transparent),transparent_40%)]">
      <div className="relative z-10 grid w-full max-w-[1020px] overflow-hidden rounded-[1.75rem] border border-rule bg-panel shadow-[0_24px_80px_var(--shadow)] md:grid-cols-[1fr_1.1fr]">
        {/* Left architectural luxury panel */}
        <section className="relative hidden flex-col justify-between overflow-hidden bg-[#16181c] p-10 text-white md:flex border-r border-white/10">
          <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.06),transparent_60%)]" />
          
          <div className="relative z-10">
            <div className="mb-10 inline-block">
              <img
                src="/brand/logo-dark@2x.png"
                alt="Barros, Mariz & Rebouças Advogados"
                className="h-11 w-auto object-contain"
              />
            </div>

            <h1 className="max-w-xs text-3xl font-extrabold leading-[1.12] text-zinc-100 tracking-tight">
              Excelência jurídica. Precisão operacional.
            </h1>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-zinc-400">
              Monitoramento automatizado de expedientes, controle rigoroso de prazos fatais e auditoria contínua do PJe.
            </p>

            <div className="mt-8 space-y-3">
              <div className="flex items-center gap-2.5 text-xs text-zinc-300">
                <CheckCircle size={16} className="text-emerald-400 shrink-0" weight="fill" />
                <span>Coleta direta nos tribunais via PJeOffice</span>
              </div>
              <div className="flex items-center gap-2.5 text-xs text-zinc-300">
                <CheckCircle size={16} className="text-emerald-400 shrink-0" weight="fill" />
                <span>Classificação e triagem de intimações e ciências</span>
              </div>
            </div>
          </div>

          <div className="relative z-10 flex items-center gap-3 border-t border-white/10 pt-6 text-xs text-zinc-400">
            <ShieldCheck size={20} weight="duotone" className="text-zinc-300 shrink-0" />
            <span>Processamento local · Dados protegidos e restritos ao escritório</span>
          </div>
        </section>

        {/* Right login form panel */}
        <section className="flex flex-col justify-between p-8 sm:p-12">
          <div>
            <div className="flex justify-between items-center">
              <Brand />
            </div>

            <div className="mt-10">
              <h2 className="text-2xl font-extrabold tracking-tight text-ink">
                Acesso ao sistema
              </h2>
              <p className="mt-2 text-xs leading-relaxed text-quiet">
                Autentique-se com sua conta operacional para acompanhar os expedientes e coletas.
              </p>
            </div>

            <form className="mt-7 grid gap-4" onSubmit={submit}>
              <div>
                <label className="text-xs font-bold text-ink-soft block mb-1.5" htmlFor="login-username">
                  Usuário
                </label>
                <div className="relative">
                  <User size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-quiet" />
                  <input
                    id="login-username"
                    className="control w-full py-2.5 pr-3 pl-10 text-sm font-medium"
                    name="username"
                    autoComplete="username"
                    required
                    autoFocus
                    placeholder="Digite seu usuário"
                    aria-label="Usuário"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-ink-soft block mb-1.5" htmlFor="login-password">
                  Senha
                </label>
                <div className="relative">
                  <LockKey size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-quiet" />
                  <input
                    id="login-password"
                    className="control w-full py-2.5 pr-3 pl-10 text-sm font-medium"
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    placeholder="Digite sua senha"
                    aria-label="Senha"
                  />
                </div>
              </div>

              {error && (
                <div className="rounded-xl border border-danger/25 bg-danger-soft px-3.5 py-2.5 text-xs font-semibold text-danger flex items-center gap-2">
                  <span className="size-1.5 rounded-full bg-danger shrink-0" />
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="button-primary mt-2 cursor-pointer w-full py-2.5 text-sm"
                disabled={busy}
              >
                <LockKey size={16} weight="bold" />
                {busy ? "Entrando no sistema…" : "Entrar"}
                <ArrowRight size={16} />
              </button>
            </form>
          </div>

          <div className="mt-10 border-t border-rule pt-4 text-center">
            <small className="text-[11px] font-medium text-quiet">
              Barros, Mariz & Rebouças Advogados · RYVTEC Soluções e Consultoria
            </small>
          </div>
        </section>
      </div>
    </main>
  );
}
