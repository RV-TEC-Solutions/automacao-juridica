import { Suspense } from "react";
import { ExpedientesClient } from "./view";
export default function Page(){return <Suspense fallback={<div className="grid min-h-screen place-items-center bg-background text-sm font-semibold text-muted-foreground"><span className="flex items-center gap-4 rounded-xl border border-border bg-card px-4 py-4"><i className="size-4 animate-spin rounded-full border-2 border-border border-t-primary"/>Carregando expedientes…</span></div>}><ExpedientesClient/></Suspense>}
