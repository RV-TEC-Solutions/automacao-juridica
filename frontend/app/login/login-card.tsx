import { Eye, EyeSlash, LockKey, User } from "@phosphor-icons/react";
import Image from "next/image";
import { FormEvent, useState } from "react";
import celeriLogo from "../../public/images/celeri-logo.png";
import styles from "./login.module.css";

function CeleriBrand() {
  return (
    <div className={styles.brand}>
      <Image src={celeriLogo} alt="Céleri" width={216} height={216} priority unoptimized draggable={false} className={styles.brandImage} />
      <span className={styles.brandDescription}>Automação de expedientes</span>
    </div>
  );
}

type LoginFieldProps = {
  kind: "username" | "password";
  visible?: boolean;
  onToggleVisibility?: () => void;
};

function LoginField({ kind, visible = false, onToggleVisibility }: LoginFieldProps) {
  const password = kind === "password";
  const id = password ? "login-password" : "login-username";
  const Icon = password ? LockKey : User;

  return (
    <div className={styles.field}>
      <label htmlFor={id}>{password ? "Senha" : "Usuário"}</label>
      <div className={styles.inputWrap}>
        <Icon size={20} weight="regular" aria-hidden="true" />
        <input
          id={id}
          name={password ? "password" : "username"}
          type={password && !visible ? "password" : "text"}
          autoComplete={password ? "current-password" : "username"}
          placeholder={password ? "Sua senha" : "Seu usuário"}
          required
        />
        {password && (
          <button
            className={styles.visibilityButton}
            type="button"
            onClick={onToggleVisibility}
            aria-label={visible ? "Ocultar senha" : "Mostrar senha"}
            aria-pressed={visible}
          >
            {visible ? <Eye size={20} aria-hidden="true" /> : <EyeSlash size={20} aria-hidden="true" />}
          </button>
        )}
      </div>
    </div>
  );
}

type LoginCardProps = {
  busy: boolean;
  error: string;
  help: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onHelp: () => void;
};

export function LoginCard({ busy, error, help, onSubmit, onHelp }: LoginCardProps) {
  const [passwordVisible, setPasswordVisible] = useState(false);

  return (
    <section className={styles.card} aria-labelledby="login-title">
      <CeleriBrand />
      <div className={styles.operation}>BMR <span aria-hidden="true">·</span> Operação local</div>

      <div className={styles.intro}>
        <h1 id="login-title">Entrar</h1>
        <p>Use sua conta para acessar os expedientes.</p>
      </div>

      <form className={styles.form} onSubmit={onSubmit}>
        <LoginField kind="username" />
        <LoginField
          kind="password"
          visible={passwordVisible}
          onToggleVisibility={() => setPasswordVisible((current) => !current)}
        />
        {error && <p className={styles.error} role="alert">{error}</p>}
        <button className={styles.submitButton} type="submit" disabled={busy}>
          {busy ? "Entrando…" : "Entrar"}
        </button>
      </form>

      <div className={styles.helpArea}>
        <button className={styles.helpButton} type="button" onClick={onHelp} aria-expanded={help}>
          Esqueceu sua senha?
        </button>
        {help && <p className={styles.helpText}>Peça ao administrador do escritório para redefinir sua senha.</p>}
      </div>

      <footer className={styles.footer}>BMR · Céleri Comunicações · © 2026 RYVTEC Soluções e Consultoria. Todos os direitos reservados.</footer>
    </section>
  );
}
