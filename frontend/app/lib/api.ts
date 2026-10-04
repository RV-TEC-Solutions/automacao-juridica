export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/${path.replace(/^\//, "")}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Não foi possível concluir a operação." }));
    throw new Error(payload.detail ?? Object.values(payload)[0] ?? "Não foi possível concluir a operação.");
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export const formatDateTime = (value: string | null, options?: Intl.DateTimeFormatOptions) => value
  ? new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Fortaleza", dateStyle: "short", timeStyle: "short", ...options }).format(new Date(value))
  : "—";
