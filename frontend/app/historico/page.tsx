import { Suspense } from "react";

import { HistoricoClient } from "./view";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <HistoricoClient />
    </Suspense>
  );
}
