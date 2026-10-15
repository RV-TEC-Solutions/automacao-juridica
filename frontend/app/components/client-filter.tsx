"use client";

import { Button } from "@/components/ui/button";
import { MultiSelect } from "@/components/ui/multi-select";
import { useLiveList } from "../hooks/use-live-list";

export type Cliente = { id: number; nome: string };

export function ClientFilter({ initialSelection, onDirty }: {
  initialSelection: string[]; onDirty: () => void;
}) {
  const { data, loading, error, reload } = useLiveList<Cliente[]>("expedientes/clientes/");
  return <MultiSelect name="client" label="Clientes" initialSelection={initialSelection} onDirty={onDirty}
    options={(data ?? []).map((client) => ({ value: String(client.id), label: client.nome }))}
    placeholder="Todos os clientes" searchLabel="Buscar cliente pelo nome" emptyMessage="Nenhum cliente coletado até o momento."
    feedback={error ? <div role="alert" className="space-y-2 px-4 py-3 text-sm">
      <p>Não foi possível atualizar os clientes.</p>
      <Button type="button" variant="outline" size="sm" onClick={() => void reload()}>Tentar novamente</Button>
    </div> : loading && !data ? <p role="status" className="px-4 py-3 text-sm text-muted-foreground">Carregando clientes…</p> : undefined} />;
}
