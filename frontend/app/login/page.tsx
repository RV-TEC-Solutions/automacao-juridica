"use client";

import { ArrowRight, CheckCircle, LockKey, ShieldCheck, User } from "@phosphor-icons/react";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
    <main className="grid min-h-screen place-items-center bg-muted p-4 sm:p-6">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-xl border border-border bg-card shadow-xl md:grid-cols-2">
        {/* Left architectural luxury panel */}
        <section className="relative hidden flex-col justify-between overflow-hidden border-r border-white/10 bg-zinc-900 p-10 text-white md:flex">
          
          <div className="relative z-10">
            <div className="mb-10 inline-block">
              <Image
                src="/brand/logo-dark@2x.png"
                alt="Barros, Mariz & Rebouças Advogados"
                width={159}
                height={64}
                className="h-12 w-auto object-contain"
              />
            </div>

            <h1 className="max-w-xs text-3xl font-bold leading-tight tracking-tight text-zinc-100">
              Excelência jurídica. Precisão operacional.
            </h1>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-zinc-400">
              Monitoramento automatizado de expedientes, controle rigoroso de prazos fatais e auditoria contínua do PJe.
            </p>

            <div className="mt-8 space-y-4">
              <div className="flex items-center gap-2 text-xs text-zinc-300">
                <CheckCircle size={16} className="text-emerald-400 shrink-0" weight="fill" />
                <span>Coleta direta nos tribunais via PJeOffice</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-zinc-300">
                <CheckCircle size={16} className="text-emerald-400 shrink-0" weight="fill" />
                <span>Classificação e triagem de intimações e ciências</span>
              </div>
            </div>
          </div>

          <div className="relative z-10 flex items-center gap-4 border-t border-white/10 pt-6 text-xs text-zinc-400">
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
              <h2 className="text-2xl font-extrabold tracking-tight text-foreground">
                Acesso ao sistema
              </h2>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                Autentique-se com sua conta operacional para acompanhar os expedientes e coletas.
              </p>
            </div>

            <form className="mt-8 grid gap-4" onSubmit={submit}>
              <div>
                <Label className="mb-2 block text-xs" htmlFor="login-username">
                  Usuário
                </Label>
                <div className="relative">
                  <User size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="login-username"
                    className="pl-10"
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
                <Label className="mb-2 block text-xs" htmlFor="login-password">
                  Senha
                </Label>
                <div className="relative">
                  <LockKey size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="login-password"
                    className="pl-10"
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
                <Alert variant="destructive">
                  <span className="size-2 rounded-full bg-destructive shrink-0" />
                  {error}
                </Alert>
              )}

              <Button
                type="submit"
                className="mt-2 w-full"
                disabled={busy}
              >
                <LockKey size={16} weight="bold" />
                {busy ? "Entrando no sistema…" : "Entrar"}
                <ArrowRight size={16} />
              </Button>
            </form>
          </div>

          <div className="mt-10 border-t border-border pt-4 text-center">
            <small className="text-xs font-medium text-muted-foreground">
              Barros, Mariz & Rebouças Advogados · RYVTEC Soluções e Consultoria
            </small>
          </div>
        </section>
      </div>
    </main>
  );
}
