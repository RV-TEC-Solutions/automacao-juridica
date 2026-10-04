import { notFound } from "next/navigation";

export default async function InteiroTeorPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const number = Number(id);
  if (!Number.isInteger(number) || number < 1 || number > 999) notFound();
  return <main className="mx-auto max-w-3xl p-8 text-foreground">
    <div className="mb-8 border-b pb-6">
      <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Ambiente de demonstração</p>
      <h1 className="mt-4 text-2xl font-bold">Inteiro teor fictício</h1>
      <p className="mt-2 text-sm text-muted-foreground">Comunicação demonstrativa #{number}. Este documento não possui validade jurídica.</p>
    </div>
    <article className="space-y-5 rounded-xl border bg-card p-8 text-sm leading-7">
      <p><strong>Destinatário:</strong> Parte destinatária {String(number).padStart(2, "0")}</p>
      <p>Fica registrada, para fins exclusivamente ilustrativos, a disponibilização desta comunicação no painel de demonstração.</p>
      <p>O prazo exibido é fictício. Nenhuma ação processual é realizada por esta página.</p>
    </article>
  </main>;
}
