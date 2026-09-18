import { Suspense } from "react";
import { ExpedientesClient } from "./view";
export default function Page(){return <Suspense fallback={<div className="flex min-h-screen items-center justify-center gap-2.5 text-muted"><div className="size-5 animate-spin rounded-full border-2 border-line border-t-accent"/>Carregando expedientes…</div>}><ExpedientesClient/></Suspense>}
