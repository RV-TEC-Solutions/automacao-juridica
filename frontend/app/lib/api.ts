function cookie(name: string) {
  if (typeof document === "undefined") return "";
  return document.cookie.split("; ").find((item) => item.startsWith(`${name}=`))?.split("=")[1] ?? "";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method?.toUpperCase() ?? "GET";
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers.set("X-CSRFToken", decodeURIComponent(cookie("csrftoken")));
  const response = await fetch(`/api/${path.replace(/^\//, "")}`, { ...init, headers, credentials: "include", cache: "no-store" });
  if (response.status === 401 || response.status === 403) throw new Error("AUTH_REQUIRED");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Não foi possível concluir a operação." }));
    throw new Error(payload.detail ?? Object.values(payload)[0] ?? "Não foi possível concluir a operação.");
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function ensureCsrf() { await api("auth/csrf/"); }
export const formatDateTime = (value: string | null, options?: Intl.DateTimeFormatOptions) => value
  ? new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Fortaleza", dateStyle: "medium", timeStyle: "short", ...options }).format(new Date(value))
  : "—";
