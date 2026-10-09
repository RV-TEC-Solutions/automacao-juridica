# Documentação do usuário — RYV Expedientes

- [Manual em Markdown](MANUAL_DO_USUARIO.md)
- [Manual em PDF](RYV-Expedientes-Manual-do-Usuario.pdf)
- [Fonte do conteúdo](conteudo.json)

As capturas estão incorporadas ao PDF. Os arquivos de imagem ficam apenas
no ambiente local e são ignorados pelo Git para reduzir o tamanho do repositório.
Para exibi-las no manual em Markdown, gere-as com o script de captura abaixo.

O manual foi elaborado a partir da interface e das regras implementadas na
codebase em 08/10/2026. Os processos, pessoas, publicações, contagens e mensagens
dos prints são fictícios. As telas são capturas do frontend real com respostas
de API demonstrativas interceptadas no navegador; nenhuma conta real, coleta,
alteração de senha ou descarte de dados é necessário para reproduzi-las.

## Atualizar a documentação

Edite `conteudo.json`, que contém os capítulos, procedimentos, tabelas, legendas
e observações. Não edite diretamente os arquivos gerados. Ao mudar a interface,
atualize também os exemplos e seletores em `scripts/capturar_telas.py`.

Para recapturar, inicie o frontend em um terminal:

```bash
npm --prefix frontend run dev -- --port 3002
```

Em outro terminal, na raiz do projeto:

```bash
.venv/bin/python docs/manual-do-usuario/scripts/capturar_telas.py
.venv/bin/python docs/manual-do-usuario/scripts/gerar_manual.py
```

`MANUAL_BASE_URL` permite informar outra origem do frontend. Use uma origem
permitida pelo servidor de desenvolvimento. A captura requer o pacote Python
Playwright e Google Chrome em `/usr/bin/google-chrome`; adapte o executável no
script se necessário. A geração requer ReportLab e fontes DejaVu Sans nos
caminhos declarados no script. Playwright e ReportLab fazem parte das
dependências Python do projeto.

O script de captura fixa a data demonstrativa em 08/10/2026, usa tema claro,
intercepta todas as chamadas `/api/` e interrompe a execução se encontrar uma
rota não prevista. As molduras e números vermelhos são sobrepostos ao DOM
somente no navegador de captura. Nenhum arquivo da interface é alterado.

## Conferência antes da entrega

Confira as legendas e a correspondência dos números nas imagens. Abra o PDF
para verificar as quebras de página, o índice, as tabelas e a legibilidade.
Quando alterar regras funcionais, confronte o texto com a implementação, em
especial filtros de prazo, leitura automática, datas de coleta, histórico,
exportações e descarte.
