"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../providers";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (!loading && user) router.replace("/"); }, [loading, user, router]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await login(String(form.get("username")), String(form.get("password")));
      router.replace("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível entrar.");
    } finally {
      setBusy(false);
    }
  };

  return <main className="grid min-h-screen place-items-center bg-bg p-8 before:fixed before:inset-0 before:pointer-events-none before:bg-[radial-gradient(circle_at_50%_15%,rgba(150,85,63,.17),transparent_38%)] max-[760px]:p-[18px]">
    <section className="relative z-[1] w-full max-w-[410px] rounded-[9px] border border-line bg-surface p-[30px] shadow-[0_24px_70px_var(--panel-shadow)] max-[760px]:p-6">
      <div className="mb-[42px] flex items-center gap-2.5"><span className="grid size-[34px] place-items-center rounded-[7px] bg-sidebar text-[11px] font-extrabold text-white">PE</span><strong className="text-[15px]">Painel de Expedientes</strong></div>
      <div><h1 className="mb-2 text-[27px]">Boas-vindas</h1><p className="mb-[27px] text-[13px] leading-[1.5] text-muted">Acesse sua área de trabalho para acompanhar expedientes e prazos.</p></div>
      <form className="grid gap-[15px]" onSubmit={submit}>
        <label className="flex flex-col gap-[7px] text-[11px] font-[650] text-text-soft">Usuário<input className="min-h-[41px] rounded-[5px] border border-line bg-surface-raised px-[11px] py-2.5 text-[13px] text-text outline-0 focus:border-accent focus:shadow-[0_0_0_2px_var(--color-accent-soft)]" name="username" autoComplete="username" required autoFocus placeholder="Digite seu usuário" /></label>
        <label className="flex flex-col gap-[7px] text-[11px] font-[650] text-text-soft">Senha<input className="min-h-[41px] rounded-[5px] border border-line bg-surface-raised px-[11px] py-2.5 text-[13px] text-text outline-0 focus:border-accent focus:shadow-[0_0_0_2px_var(--color-accent-soft)]" name="password" type="password" autoComplete="current-password" required placeholder="Digite sua senha" /></label>
        {error && <div className="rounded-[5px] border border-red/[.2] bg-red-soft px-2.5 py-[9px] text-[11px] text-red">{error}</div>}
        <button className="mt-[3px] min-h-[38px] cursor-pointer rounded-[5px] border border-primary-bg bg-primary-bg px-[15px] py-[9px] font-bold text-primary-text hover:bg-primary-hover disabled:cursor-default disabled:opacity-[.55]" disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button>
      </form>
      <small className="mt-6 block text-center text-[10px] text-muted">Ambiente local · seus dados permanecem nesta máquina</small>
    </section>
  </main>;
}
