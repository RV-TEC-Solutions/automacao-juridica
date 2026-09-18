import { Suspense } from "react";
import { ExpedientesClient } from "./view";
export default function Page(){return <Suspense fallback={<div className="grid min-h-screen place-items-center bg-app text-sm font-semibold text-quiet"><span className="flex items-center gap-3 rounded-xl border border-rule bg-panel px-4 py-3"><i className="size-4 animate-spin rounded-full border-2 border-rule border-t-brand"/>Carregando expedientes…</span></div>}><ExpedientesClient/></Suspense>}
