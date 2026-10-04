# Céleri — ambiente de demonstração

Esta branch usa somente o frontend Next.js. As telas, coletas, publicações e PDFs usam dados fictícios. Não é necessário iniciar Django, PostgreSQL, worker ou conectar token físico. O frontend não consulta serviços externos.

## Iniciar

```bash
npm --prefix frontend install
npm --prefix frontend run dev -- --port 3002
```

Abra `http://localhost:3002`. A entrada é automática como **Operador Demo**.

## Gravar uma coleta

Na visão geral, clique em **Executar coleta**. Use **Próxima fonte** para avançar uma etapa ou **Concluir coleta** para terminar o ciclo. Painel, listas, histórico, estatísticas e PDFs passam a refletir os resultados simulados.

## Reiniciar para outra tomada

```bash
npm --prefix frontend run demo:reset
```

Atualize a página. O comando apaga apenas `frontend/.demo-state.json`, que é ignorado pelo Git. O arquivo é recriado com datas relativas ao dia local de Fortaleza. Mudanças de leitura, tema, fontes e coletas são descartadas.

## Verificar

```bash
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

O teste de navegador inicia o servidor local na porta 3002. Os dados do SQLite histórico não são carregados pela aplicação de demonstração.
