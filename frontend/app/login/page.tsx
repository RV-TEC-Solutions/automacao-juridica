"use client";

import { FormEvent, useEffect, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { LoginCard } from "./login-card";
import { useAuth } from "../providers";
import styles from "./login.module.css";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [help, setHelp] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/");
  }, [loading, user, router]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    const form = new FormData(event.currentTarget);

    try {
      await login(String(form.get("username")), String(form.get("password")));
      router.replace("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível entrar. Tente novamente.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className={styles.page}>
      <Image
        src="/images/recepcao-luxuosa-bmr.png"
        alt=""
        fill
        priority
        sizes="100vw"
        className={styles.background}
      />
      <div className={styles.scrim} aria-hidden="true" />
      <LoginCard
        busy={busy}
        error={error}
        help={help}
        onSubmit={submit}
        onHelp={() => setHelp((current) => !current)}
      />
    </main>
  );
}
