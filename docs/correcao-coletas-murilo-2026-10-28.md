# Autenticação das coletas de Murilo — 28/10/2026

As alterações deste atendimento são condicionadas ao titular `murilo`.
As credenciais, o fluxo de Cristiano e o DJEN não foram alterados.

## Evidências

As execuções 431 e 433–443 de Murilo falharam antes do TOTP, com exceção
do crash na abertura do portal TSE. As capturas dos timeouts permaneceram
na tela inicial do SSO, sem campo de autenticação em duas etapas.

No log do assinador de Murilo, a requisição seguinte provocava o descarte
da anterior, ainda aguardando autenticação. O preenchimento de um diálogo
antigo não conclui a requisição do navegador atual. O processo era mantido
entre fontes e entre ciclos, mesmo depois que o navegador fechava.

O worker anterior também registrou dois encerramentos por falta de memória.
O notebook estava com a swap cheia. Esses registros não permitem atribuir
retrospectivamente cada crash a uma causa única.

## Correções

- O assinador de Murilo é iniciado novamente antes de cada fonte, preservando
  as autorizações de site e a verificação do módulo e da série do token.
  Isso elimina os diálogos pendentes do processo anterior sem reenviar PIN
  na mesma tentativa.
- Somente seu processo Java recebe heap máximo de 256 MiB. O limite total
  do worker continua em 512 MiB, com até 1536 MiB somando RAM e swap.
- Seu Chromium continua com interface gráfica, desativa a aceleração por GPU
  e limita os processos de renderização. Uma tentativa com o shell headless
  recebeu HTTP 403 do TJRN e foi abandonada.
- Antes de esperar o TOTP, seu fluxo aguarda a resposta da requisição ao
  PJeOffice. Ausência de resposta e erro HTTP do assinador são diagnosticados
  como falha da autenticação por certificado. Respostas OPTIONS não confirmam
  a conclusão da assinatura. A confirmação usa o evento `requestfinished`,
  sem tentar reler o corpo HTTP que o Chromium pode descartar ao navegar
  para a tela do TOTP.
- Depois de receber a resposta inteira, encerra o assinador gerenciado de
  Murilo para liberar sua memória durante o TOTP e a coleta. A etapa de
  encerramento também é executada ao sair do navegador em caso de falha.
  Somente o assinador preparado para essa identidade pelo próprio worker
  pode ser encerrado.
- Para Murilo, o TSE abre diretamente
  `https://pje.tse.jus.br/pje/login.seam`, endereço publicado no
  [portal oficial do TSE](https://www.tse.jus.br/servicos-judiciais/processos/pje).
  O portal institucional que sofreu o crash deixa de ser carregado nessa coleta.
- O TRE-RN usa os destinos publicados no portal,
  `https://pje1g-rn.tse.jus.br/pje` e `https://pje.tre-rn.jus.br/pje`,
  evitando as páginas intermediárias que não terminaram de renderizar os
  links no prazo e voltaram a pressionar a memória do worker.

Não foram criados valores fictícios para CAPTCHA nem ignoradas validações do
portal. Os 404 dos parâmetros auxiliares e `TOKEN_CAPTCHA is not defined`
não foram tratados como causas comprovadas da falha do certificado.

## Validação automatizada

Passaram 125 testes dos módulos `automation.tests`,
`automation.test_collectors`, `automation.test_pje_reliability` e
`automation.test_pjeoffice_atspi`, executados com `PJE_COLLECTORS=murilo`.
Os testes de dois titulares usam sua própria configuração explícita.
Os novos casos cobrem a renovação do assinador de Murilo, a reutilização
preservada para Cristiano, a resposta do assinador antes do TOTP, a exclusão
do preflight e a restrição dos ajustes de navegador e TSE ao titular solicitado.

## Primeiro ciclo de verificação real

O ciclo exclusivo de Murilo, execuções 458–469, concluiu seis fontes:
TRE-RN 2º grau (1 expediente), TSE (sem pendências), TRT21 2º grau (sem
pendências), TRF5 2º grau/TRU (33), Turmas Recursais (40) e TRU (33).
O timeout após PIN não reapareceu.

TJRN nos dois graus, Varas e JEF avançaram até a coleta, mas falharam na
segunda aba. TRT21 1º grau chegou aos expedientes e o renderer caiu.
TRE-RN 1º grau parou no portal, antes de solicitar autenticação.
O contador do cgroup registrou cinco encerramentos por falta de memória
durante esse ciclo. A liberação do assinador após a assinatura e o acesso
direto ao TRE-RN 1º grau foram acrescentados após essa verificação.

Na execução isolada 470, o TJRN 2º grau concluiu as duas abas e importou 27
expedientes. O contador do novo worker permaneceu com `oom_kill=0`.

## Resultado final

As últimas execuções das 12 fontes de Murilo concluíram com sucesso. A API
da pipeline foi consultada e confirmou os 12 estados `success`, incluindo a
reexecução isolada do TRE-RN 2º grau. A última conclusão ocorreu às
08h44min47s de 28/10/2026, em America/Fortaleza.

| Fonte | Execução | Expedientes encontrados |
| --- | --- | ---: |
| TJRN 1º grau | 474 | 79 |
| TJRN 2º grau | 475 | 27 |
| TRE-RN 1º grau | 476 | 0 |
| TRE-RN 2º grau | 486 | 1 |
| TSE 3º grau | 478 | 0 |
| TRT21 1º grau | 479 | 1 |
| TRT21 2º grau | 480 | 0 |
| TRF5 2º grau/TRU | 481 | 33 |
| Varas da Justiça Comum | 482 | 113 |
| JEF 5ª Região | 483 | 113 |
| Turmas Recursais | 484 | 40 |
| TRU 5ª Região | 485 | 33 |

O TJRN 1º grau concluiu suas 19 abas; Varas e JEF concluíram suas seis abas.
O TSE abriu e concluiu sem crash. O TRT21 1º grau conseguiu ler seu expediente,
sem introduzir valores fictícios de CAPTCHA.

Na execução 477, o portal institucional do TRE-RN 2º grau ainda consumiu
memória demais antes do login; esse worker registrou dois encerramentos por
falta de memória. Após incluir também o acesso direto desse grau e aplicar a
imagem final, a execução 486 concluiu com identidade de Murilo conferida e
`oom=0`, `oom_kill=0` no novo worker.

Os arquivos de autenticação e identidade da imagem final foram comparados por
SHA-256 com o código local e coincidiram. Os 125 testes passaram novamente
com essa versão. O worker ficou ativo e não restaram execuções pendentes ou
em andamento. Nenhuma coleta de Cristiano ou DJEN foi iniciada durante este
atendimento, e o `.env` não foi alterado. As tentativas anteriores permanecem
registradas no histórico.
