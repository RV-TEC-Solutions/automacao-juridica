import { Suspense } from "react";
import { DjenClient } from "./view";

export default function DjenPage() {
  return <Suspense fallback={<div className="grid min-h-screen place-items-center text-sm text-muted-foreground">Carregando publicações…</div>}><DjenClient /></Suspense>;
}
