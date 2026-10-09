# RYV Expedientes — Manual do usuário

Versão 1.0 · 08/10/2026 · Idioma: português (Brasil)

[Baixar o manual em PDF](RYV-Expedientes-Manual-do-Usuario.pdf)

## Índice

1. [Apresentação e leitura deste manual](#01-apresentacao-e-leitura-deste-manual)
2. [Antes de começar: acesso e preparação](#02-antes-de-comecar-acesso-e-preparacao)
3. [Entrar, mostrar a senha e recuperar o acesso](#03-entrar-mostrar-a-senha-e-recuperar-o-acesso)
4. [Navegação, tema e encerramento da sessão](#04-navegacao-tema-e-encerramento-da-sessao)
5. [Visão geral: indicadores e prioridades](#05-visao-geral-indicadores-e-prioridades)
6. [Coletas: executar, acompanhar e reexecutar](#06-coletas-executar-acompanhar-e-reexecutar)
7. [Coleta independente do DJEN](#07-coleta-independente-do-djen)
8. [Como interpretar os estados das fontes](#08-como-interpretar-os-estados-das-fontes)
9. [Descartar a coleta do dia](#09-descartar-a-coleta-do-dia)
10. [Expedientes: pesquisar e aplicar filtros](#10-expedientes-pesquisar-e-aplicar-filtros)
11. [Filtros de prazo, pendência e leitura](#11-filtros-de-prazo-pendencia-e-leitura)
12. [Detalhe do expediente e leitura local](#12-detalhe-do-expediente-e-leitura-local)
13. [Conferir alterações de um expediente](#13-conferir-alteracoes-de-um-expediente)
14. [Publicações DJEN: pesquisar por coleta](#14-publicacoes-djen-pesquisar-por-coleta)
15. [Detalhe da publicação e inteiro teor](#15-detalhe-da-publicacao-e-inteiro-teor)
16. [Histórico: expedientes dos últimos 30 dias](#16-historico-expedientes-dos-ultimos-30-dias)
17. [Histórico: publicações processuais](#17-historico-publicacoes-processuais)
18. [Histórico: orquestração e diagnóstico de coletas](#18-historico-orquestracao-e-diagnostico-de-coletas)
19. [Avisos do PJe](#19-avisos-do-pje)
20. [Estatísticas e tempo economizado](#20-estatisticas-e-tempo-economizado)
21. [Configurações: perfil, tema e horário diário](#21-configuracoes-perfil-tema-e-horario-diario)
22. [Configurações: fontes e prontidão operacional](#22-configuracoes-fontes-e-prontidao-operacional)
23. [Configurações: alterar a senha de acesso](#23-configuracoes-alterar-a-senha-de-acesso)
24. [Exportar relatórios em PDF](#24-exportar-relatorios-em-pdf)
25. [Roteiro de uso diário](#25-roteiro-de-uso-diario)
26. [Problemas frequentes e como resolver](#26-problemas-frequentes-e-como-resolver)
27. [Glossário e mapa rápido do sistema](#27-glossario-e-mapa-rapido-do-sistema)

<a id="01-apresentacao-e-leitura-deste-manual"></a>

## 01. Apresentação e leitura deste manual

O RYV Expedientes reúne expedientes do PJe, publicações do Diário de Justiça Eletrônico Nacional (DJEN), avisos e resultados das coletas. Este manual orienta a rotina de consulta e acompanhamento do escritório.

1. Use o índice para ir diretamente à área desejada. Cada capítulo apresenta o objetivo da tela, o procedimento e o resultado esperado.
2. Nas capturas, os retângulos vermelhos e os números indicam os controles importantes. A legenda abaixo de cada imagem explica esses números.
3. Os prints mostram a interface da codebase com dados fictícios. Nomes, processos, publicações, contagens, horários e falhas de exemplo não representam uma coleta real.
4. Este manual corresponde à interface disponível em 08/10/2026. A aparência pode variar conforme o tamanho da janela e o tema escolhido.

> **Atenção:** A aplicação auxilia o acompanhamento. A leitura no painel registra organização interna; ciência, resposta e demais atos processuais devem ser realizados na plataforma de origem.

<a id="02-antes-de-comecar-acesso-e-preparacao"></a>

## 02. Antes de começar: acesso e preparação

Peça ao responsável técnico o endereço da aplicação e sua conta de acesso. Na execução local padrão, o endereço é http://localhost:3002.

1. Abra o endereço fornecido em um navegador. Se a página não abrir, solicite ao responsável que verifique se a aplicação está em execução.
2. Tenha seu usuário e sua senha de acesso ao RYV Expedientes. Essa senha é diferente do PIN do certificado digital.
3. Para coletar no PJe, mantenha o token físico conectado e a estrutura de autenticação configurada pelo responsável técnico, incluindo PJeOffice e credenciais locais.
4. Para a rotina automática, o computador e os serviços de coleta precisam permanecer ligados e disponíveis no horário agendado.
5. A coleta do DJEN usa a OAB configurada na instalação, consulta sete datas incluindo o dia atual e independe do token físico. Confirme com o responsável qual OAB está sendo usada.

> **Atenção:** Instalação, criação de conta, configuração de OAB, certificados e recuperação do banco são procedimentos técnicos documentados no README principal. Não existe campo de edição da OAB na interface atual.

<a id="03-entrar-mostrar-a-senha-e-recuperar-o-acesso"></a>

## 03. Entrar, mostrar a senha e recuperar o acesso

A tela de entrada identifica sua conta e abre a Visão geral após a autenticação.

1. Digite o usuário no campo Usuário [1].
2. Digite sua senha no campo Senha [2]. O ícone de olho permite mostrar ou ocultar o que foi digitado.
3. Clique em Entrar [3] e aguarde o carregamento do painel.
4. Se esquecer a senha, clique em Esqueceu sua senha? [4]. A aplicação orienta a pedir ao administrador do escritório a redefinição.
5. Se a entrada falhar, confira o usuário, a senha e a tecla Caps Lock. Persistindo a falha, procure o administrador.

![Tela de Entrar, mostrar a senha e recuperar o acesso com destaques vermelhos numerados](imagens/01-login.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Usuário: identificação da conta.
- **Destaque 2:** Senha: chave de acesso ao painel.
- **Destaque 3:** Entrar: envio dos dados de autenticação.
- **Destaque 4:** Esqueceu sua senha?: instrução para solicitar ajuda ao administrador.

> **Atenção:** A tela não envia e-mail de recuperação nem disponibiliza cadastro de nova conta.

<a id="04-navegacao-tema-e-encerramento-da-sessao"></a>

## 04. Navegação, tema e encerramento da sessão

O menu principal acompanha as telas do sistema. Use-o para alternar entre as sete áreas.

1. No menu [1], escolha Visão geral, Expedientes, Publicações DJEN, Histórico, Avisos, Estatísticas ou Configurações.
2. Clique no botão de lua ou sol [2] para alternar entre os temas claro e escuro. A preferência é salva na conta.
3. Clique no avatar do perfil para abrir Configurações.
4. Ao terminar, clique em Sair [3]. A aplicação encerra a sessão e retorna ao login.
5. Em janelas menores, o menu aparece em uma segunda linha. Deslize a faixa horizontalmente para encontrar os demais itens.

![Tela de Navegação, tema e encerramento da sessão com destaques vermelhos numerados](imagens/18-navegacao.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Menu principal: acesso às áreas do sistema.
- **Destaque 2:** Lua/sol: alteração rápida do tema visual.
- **Destaque 3:** Sair: encerramento da sessão.

<a id="05-visao-geral-indicadores-e-prioridades"></a>

## 05. Visão geral: indicadores e prioridades

A Visão geral combina indicadores, acompanhamento das coletas e listas. Ao clicar em um indicador, a lista de expedientes passa a usar aquele filtro.

1. Comece pelos cartões Urgentes, Não lidos e Prazos em cálculo [2], conforme a rotina de acompanhamento do escritório.
2. Novos mostra os expedientes descobertos hoje. Alterados mostra os que tiveram alterações identificadas hoje.
3. Não lidos reúne expedientes com eventos ainda não lidos. Urgentes inclui prazos vencidos ou com vencimento nas próximas 72 horas.
4. Até próxima semana reúne prazos fatais a vencer até o fim da próxima semana. Prazos em cálculo reúne registros ainda sem cálculo concluído no PJe.
5. Na parte inferior, alterne entre Expedientes e Publicações Processuais. Use Ver consulta completa para abrir a área de consulta correspondente.

![Tela de Visão geral: indicadores e prioridades com destaques vermelhos numerados](imagens/02-visao-geral.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Navegação: escolha a área desejada.
- **Destaque 2:** Indicadores: clique para filtrar a lista.
- **Destaque 3:** Pipeline de coleta: acompanhe as fontes consultadas.

> **Atenção:** Novos e Alterados são recortes de hoje. Os cartões Não lidos, Urgentes, Até próxima semana e Prazos em cálculo representam o estado atual e podem incluir registros coletados em dias anteriores. Os cartões são de expedientes PJe; as publicações DJEN ficam em sua própria aba.

<a id="06-coletas-executar-acompanhar-e-reexecutar"></a>

## 06. Coletas: executar, acompanhar e reexecutar

A Pipeline de coleta mostra as fontes, seus estados e a última sincronização. O ciclo PJe percorre as fontes habilitadas; o DJEN tem sua própria rotina diária.

1. Conecte o token físico e clique no ícone de reprodução Executar coleta [1]. Aguarde o processamento das fontes.
2. Acompanhe a lista [4]. Ela tem rolagem horizontal: mova a faixa para visualizar os grupos à direita, incluindo TRF5 e DJEN.
3. Use Atualizar status da coleta [2] para consultar o progresso. Esse botão atualiza a tela; não inicia outra coleta.
4. Leia o estado de cada fonte, mesmo que o painel informe uma última sincronização. Uma fonte pode falhar enquanto outras concluem.
5. Após o ciclo, clique na seta circular da fonte para Reexecutar somente aquela fonte. Para fontes PJe, o token precisa continuar disponível. A reexecução do DJEN independe dele.
6. Durante um ciclo PJe ativo, o botão de reprodução dá lugar a Interromper coleta. Use-o para solicitar a interrupção; acompanhe a confirmação nos estados e no Histórico.

![Tela de Coletas: executar, acompanhar e reexecutar com destaques vermelhos numerados](imagens/03-coleta.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Executar coleta: início manual do ciclo PJe.
- **Destaque 2:** Atualizar status: nova consulta do andamento.
- **Destaque 3:** Ver relatório de coletas: abre o Histórico de orquestração.
- **Destaque 4:** Fontes e estados: use a rolagem e as setas de reexecução.

> **Atenção:** Executar coleta inicia o ciclo PJe; não deve ser confundido com a coleta independente do DJEN. Interromper uma coleta não desfaz registros já gravados. Para investigar uma falha, consulte Orquestração de coletas no Histórico.

<a id="07-coleta-independente-do-djen"></a>

## 07. Coleta independente do DJEN

O grupo DJEN fica à direita na faixa de fontes da Visão geral. A coleta diária consulta publicações nacionais pela OAB configurada, independentemente do ciclo PJe e do token físico.

1. Na Pipeline, mova a barra horizontal até o grupo DJEN [2].
2. Confira o estado de Publicações DJEN. Quando a rotina terminar e a seta estiver disponível, clique em Reexecutar somente Publicações DJEN [1] para uma nova consulta manual.
3. Aguarde a mudança de estado. Ao concluir, revise Publicações Processuais na Visão geral ou Publicações DJEN no menu.
4. Se não aparecerem resultados, confira o período de coleta e o Histórico de orquestração. Uma consulta bem-sucedida pode não encontrar publicações novas.

![Tela de Coleta independente do DJEN com destaques vermelhos numerados](imagens/20-djen-coleta.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Seta circular da fonte: reexecução manual somente do DJEN.
- **Destaque 2:** Faixa rolada até o fim: grupos TRF5 e DJEN.

> **Atenção:** Executar coleta inicia o ciclo PJe. Para a consulta manual do DJEN, use sua seta própria. A fonte DJEN deve estar habilitada em Configurações. Reexecuções usam a mesma janela dos últimos sete dias de disponibilização.

<a id="08-como-interpretar-os-estados-das-fontes"></a>

## 08. Como interpretar os estados das fontes

Os estados aparecem na Pipeline e no Histórico. A conclusão de uma fonte significa que a execução terminou, mesmo quando nenhum registro novo foi encontrado.


| Estado | Significado e ação do usuário |
| --- | --- |
| Aguardando | Fonte ainda não iniciada ou na fila. Acompanhe o ciclo antes de tentar outra execução. |
| Em execução | Coleta em andamento. Aguarde o resultado; evite iniciar operações repetidas. |
| Concluída | Execução terminou com sucesso. Confira encontrados, novos, alterados e resolvidos no Histórico. |
| Falhou | Execução terminou com erro. Leia a mensagem, verifique o ambiente e reexecute a fonte quando o problema for resolvido. |
| Interrompida | Execução cancelada. Verifique no Histórico o que chegou a ser processado. |
| Desativada | Fonte desabilitada em Configurações. Não participa das coletas enquanto estiver desativada. |
| Ignorada | Fonte não executada naquele ciclo. Não interprete esse estado como confirmação de ausência de expedientes. |

> **Atenção:** A quantidade de fontes concluídas não substitui a conferência individual. Se houver Falhou, Interrompida ou Ignorada, verifique a cobertura da coleta.

<a id="09-descartar-a-coleta-do-dia"></a>

## 09. Descartar a coleta do dia

A lixeira da Pipeline abre uma confirmação para remover os efeitos da coleta do dia. Use esse recurso somente quando realmente precisar invalidar os dados coletados.

1. Na Visão geral, clique na lixeira Descartar coleta do dia. O botão fica disponível quando há dados descartáveis e nenhuma fonte está em execução.
2. Leia a confirmação [1]. O descarte exclui expedientes novos do dia e desfaz alterações e resoluções associadas à coleta.
3. Publicações DJEN vinculadas às execuções descartadas também são excluídas. A Pipeline e o Histórico de orquestração deixam de exibir essas execuções.
4. Clique em Cancelar [2] para manter os dados ou em Descartar coleta [3] para efetivar o descarte.
5. Após a confirmação, confira a notificação e as listas atualizadas. Se necessário, execute uma nova coleta para reconstruir os dados.

![Tela de Descartar a coleta do dia com destaques vermelhos numerados](imagens/04-descarte.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Confirmação: descreve os principais efeitos do descarte.
- **Destaque 2:** Cancelar: fecha a confirmação e preserva os dados.
- **Destaque 3:** Descartar coleta: efetiva a remoção e a reversão.

> **Atenção:** O descarte atua nos dados locais do RYV Expedientes. Ele não desfaz atos realizados nos tribunais. A interface não oferece um botão para desfazer o descarte. A reexecução obtém o estado disponível na fonte naquele momento.

<a id="10-expedientes-pesquisar-e-aplicar-filtros"></a>

## 10. Expedientes: pesquisar e aplicar filtros

A tela Expedientes permite localizar registros por processo, partes ou assunto e combinar filtros de acompanhamento.

1. Digite um número de processo, uma parte ou um assunto no campo de busca [1].
2. Abra Filtros avançados [2]. Escolha os filtros necessários e clique em Buscar para aplicá-los à consulta.
3. Use Fonte, Pendência, Prazo, Situação de leitura, Coleta a partir de, Coleta até e Ordenação. Os filtros são combinados.
4. Confira a quantidade encontrada. Quando houver várias páginas, use os controles de paginação abaixo da lista.
5. Clique em Limpar filtros para voltar à consulta sem restrições. Esse comando também limpa o texto de busca.
6. Clique no registro [4] para abrir os detalhes. Use o ícone de PDF [3] depois de aplicar a pesquisa.

![Tela de Expedientes: pesquisar e aplicar filtros com destaques vermelhos numerados](imagens/05-expedientes.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Busca textual: processo, partes ou assunto.
- **Destaque 2:** Filtros avançados: combinação dos critérios.
- **Destaque 3:** PDF: exportação dos resultados aplicados.
- **Destaque 4:** Registro: acesso ao detalhe do expediente.

> **Atenção:** Os campos de data filtram eventos de coleta, não o vencimento do prazo. Após editar filtros, clique em Buscar: a exportação fica indisponível enquanto as alterações não forem aplicadas. O seletor Fonte atual lista TJRN, TRE-RN, TSE e TRT21; para registros TRF5, use Todas as fontes e a pesquisa por processo.

<a id="11-filtros-de-prazo-pendencia-e-leitura"></a>

## 11. Filtros de prazo, pendência e leitura

Escolha o filtro conforme a pergunta que deseja responder. A tabela abaixo explica a regra aplicada pela versão atual.

1. Exemplo: para revisar pendências urgentes, selecione Prazo = Urgentes e Situação de leitura = Não lidos, depois clique em Buscar.
2. Para achar um registro que desapareceu da lista urgente, limpe os filtros e pesquise pelo processo. Ele pode ter sido lido, ter mudado de prazo ou estar resolvido.

| Filtro | O que retorna |
| --- | --- |
| Urgentes | Expedientes ativos com prazo calculado, vencidos ou a vencer em até 72 horas. |
| Vencidos | Expedientes ativos com prazo calculado anterior ao momento da consulta. |
| Futuros | Expedientes ativos com vencimento além das próximas 72 horas. |
| Até o fim da próxima semana | Expedientes ativos com prazo calculado entre agora e o fim do domingo da próxima semana. |
| Em cálculo | Expedientes ativos cujo prazo ainda está em cálculo na origem. |
| Sem prazo | Expedientes ativos classificados como sem prazo pela fonte. |
| Resolvidos | Expedientes marcados como inativos na base local. |
| Ciência / Resposta | Tipo de pendência informado pelo PJe. |
| Não identificada | A fonte não forneceu dados suficientes para distinguir a pendência. |
| Não lidos / Lidos | Existência ou ausência de eventos ainda não lidos no expediente. |

> **Atenção:** O filtro Futuros exclui os vencimentos nas próximas 72 horas, embora eles ainda não tenham vencido. Sem prazo e Em cálculo são estados diferentes; um traço na data, isoladamente, não permite distingui-los.

<a id="12-detalhe-do-expediente-e-leitura-local"></a>

## 12. Detalhe do expediente e leitura local

Ao selecionar um expediente, abre-se um painel lateral. Ele apresenta o processo, os prazos, a ação indicada pela origem e os dados coletados.

1. Confira o número do processo e use Copiar processo [1] se precisar consultar a plataforma de origem.
2. Em Prazo e ação processual [2], leia o prazo fatal, o prazo original, a situação do cálculo e a ação disponível.
3. Em Dados do processo [3], confira classe, unidade judiciária, destinatário, expedição, meio de comunicação e tribunal.
4. Role o painel para ver Última alteração identificada, quando disponível. Os valores antes e depois ajudam a reconhecer mudanças. O registro de ciência também aparece quando fornecido pela fonte.
5. Feche o painel no botão Fechar, no canto superior. A lista e os indicadores são atualizados após o registro de leitura.

![Tela de Detalhe do expediente e leitura local com destaques vermelhos numerados](imagens/06-detalhe-expediente.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Copiar processo: copia o número para a área de transferência.
- **Destaque 2:** Prazo e ação processual: dados para conferência na origem.
- **Destaque 3:** Dados do processo: identificação e contexto do expediente.

> **Atenção:** Abrir um expediente não lido solicita automaticamente a marcação dos seus eventos como lidos. Não há botão de ciência ou resposta processual neste painel. Tomar ciência e Responder são informações sobre ações disponíveis no PJe, onde devem ser executadas. Uma nova alteração coletada pode tornar o expediente não lido novamente.

<a id="13-conferir-alteracoes-de-um-expediente"></a>

## 13. Conferir alterações de um expediente

Quando há mudança identificada pela coleta, o detalhe do expediente mostra a última alteração disponível com os valores anteriores e atuais.

1. Abra o expediente alterado e role o painel lateral até Última alteração identificada [1].
2. Confira a data do evento e o nome do campo alterado, como Prazo fatal, Destinatário ou Assunto.
3. Compare o valor anterior com o atual, apresentados em comparação, ligados por uma seta. No exemplo fictício, o prazo mudou de 08/10 para 09/10.
4. Confira o registro atual na seção de prazo e consulte a origem antes de adotar providências.

![Tela de Conferir alterações de um expediente com destaques vermelhos numerados](imagens/19-alteracoes.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Última alteração identificada: data, campo e comparação entre os valores.

> **Atenção:** Esta seção aparece quando o último evento traz alterações. Ela não é uma lista de todas as mudanças desde a primeira coleta. Marcar a leitura não confirma uma providência jurídica.

<a id="14-publicacoes-djen-pesquisar-por-coleta"></a>

## 14. Publicações DJEN: pesquisar por coleta

Publicações DJEN reúne comunicações localizadas pela OAB configurada. A tela começa com o período de coleta do dia atual.

1. Digite processo, parte, advogado ou um trecho da publicação na pesquisa [1].
2. Defina Coleta de e Até [2]. A data inicial deve ser igual ou anterior à final.
3. Clique em Pesquisar para aplicar o texto e o intervalo. Confira o total e a lista.
4. Clique na publicação [4] para ler o detalhe. Se houver várias páginas, navegue nos controles abaixo da lista.
5. Use o PDF [3] para baixar os resultados aplicados. Se editar a busca ou o período, clique em Pesquisar antes de exportar.
6. Limpar busca remove o texto pesquisado; o intervalo de coleta selecionado permanece.

![Tela de Publicações DJEN: pesquisar por coleta com destaques vermelhos numerados](imagens/08-djen.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Texto de pesquisa: processo, parte, advogado ou trecho.
- **Destaque 2:** Intervalo de coleta e Pesquisar: aplicação da consulta.
- **Destaque 3:** PDF: download das publicações encontradas.
- **Destaque 4:** Publicação: abertura do detalhe.

> **Atenção:** Data de coleta é quando o RYV Expedientes incorporou o registro. Disponibilização é a data informada pelo DJEN. Uma publicação disponibilizada em 07/10 e coletada em 08/10 aparece na pesquisa por coleta de 08/10. A rotina consulta os últimos sete dias de disponibilização e evita cadastrar novamente publicações já conhecidas.

<a id="15-detalhe-da-publicacao-e-inteiro-teor"></a>

## 15. Detalhe da publicação e inteiro teor

O painel de uma publicação DJEN apresenta sua identificação, as partes, os advogados e o texto disponibilizado pela fonte.

1. Abra uma publicação na lista e confira processo, tribunal, órgão, tipo, classe, data de disponibilização e número da comunicação.
2. Se o link estiver disponível, clique em Abrir inteiro teor [1]. A página de origem abre em outra aba.
3. Em Partes e advogados [2], confira os nomes e a inscrição da OAB associada à comunicação.
4. Leia Texto publicado [3]. Role o painel para ver todo o conteúdo.
5. Use o botão ao lado do número para copiá-lo. Feche o painel no canto superior quando terminar.

![Tela de Detalhe da publicação e inteiro teor com destaques vermelhos numerados](imagens/09-detalhe-djen.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Abrir inteiro teor: acesso externo ao conteúdo de origem.
- **Destaque 2:** Partes e advogados: pessoas relacionadas à comunicação.
- **Destaque 3:** Texto publicado: conteúdo recebido do DJEN.

> **Atenção:** Abrir uma publicação não lida solicita sua marcação como lida no RYV Expedientes. Isso não realiza ciência nem envia manifestação ao tribunal. A tela DJEN não apresenta o mesmo campo Prazo fatal do expediente PJe.

<a id="16-historico-expedientes-dos-ultimos-30-dias"></a>

## 16. Histórico: expedientes dos últimos 30 dias

O Histórico organiza informações por dia. Na aba Expedientes, ele lista os registros descobertos pela primeira vez no período, com os dados atuais do expediente.

1. Abra Histórico no menu e escolha a aba Expedientes [1].
2. Ajuste Coletas de e Até [2] dentro dos últimos 30 dias, incluindo hoje, e clique em Aplicar período.
3. Consulte os grupos por data e selecione o registro [4] para abrir o mesmo painel de detalhes da consulta completa.
4. Use os controles inferiores se houver outras páginas.
5. Use o ícone de PDF [3] para exportar o histórico de expedientes do período aplicado.

![Tela de Histórico: expedientes dos últimos 30 dias com destaques vermelhos numerados](imagens/10-historico.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Abas: expedientes, publicações e orquestração.
- **Destaque 2:** Período: escolha das datas e aplicação.
- **Destaque 3:** PDF: exportação do histórico de expedientes.
- **Destaque 4:** Registro por dia: abertura do detalhe.

> **Atenção:** Esta aba é o histórico de entrada de novos expedientes, não uma lista de todas as alterações diárias. O detalhe mostra a última alteração disponível. Para pesquisar expedientes por eventos de coleta, use a consulta completa; para volumes de alterações e resoluções, veja Estatísticas.

<a id="17-historico-publicacoes-processuais"></a>

## 17. Histórico: publicações processuais

A aba Publicações Processuais do Histórico agrupa as comunicações DJEN pelo dia em que foram coletadas.

1. No Histórico, selecione Publicações Processuais [1].
2. Escolha o período dentro dos últimos 30 dias e clique em Aplicar período.
3. Confira os grupos diários. Clique no registro [3] para abrir identificação, partes, advogados e texto.
4. Use o ícone de PDF [2] para baixar as publicações do período, incluindo registros de outras páginas.

![Tela de Histórico: publicações processuais com destaques vermelhos numerados](imagens/11-historico-djen.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Publicações Processuais: histórico do DJEN.
- **Destaque 2:** PDF: exportação das publicações do período.
- **Destaque 3:** Registro: conteúdo da publicação.

> **Atenção:** Ao trocar de aba, confira as datas aplicadas. Em Expedientes e Publicações, editar as datas exige Aplicar período antes da exportação. Para pesquisar por texto, use a área Publicações DJEN.

<a id="18-historico-orquestracao-e-diagnostico-de-coletas"></a>

## 18. Histórico: orquestração e diagnóstico de coletas

Orquestração de coletas mostra as execuções dos últimos 30 dias e ajuda a verificar cobertura, duração e erros por fonte.

1. No Histórico, clique em Orquestração de coletas [1], ou use Ver relatório de coletas na Pipeline.
2. Leia a tabela [2]: Status, Fonte, Acionamento, Início, Duração, Resultados e Detalhes.
3. Em Resultados, encontrados é o volume localizado; + indica novos registros, alt. indica alterados e res. indica resolvidos. Esses números medem aspectos diferentes.
4. Se aparecer Ver erro, clique para expandir a mensagem [3]. Anote a fonte, o horário e o texto para informar ao responsável.
5. Depois de corrigir a causa da falha, volte à Pipeline e reexecute somente a fonte necessária.

![Tela de Histórico: orquestração e diagnóstico de coletas com destaques vermelhos numerados](imagens/12-orquestracao.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Orquestração: relatório de execuções.
- **Destaque 2:** Tabela: resultado e contexto de cada fonte.
- **Destaque 3:** Erro expandido: mensagem útil para diagnóstico.

> **Atenção:** Esta aba usa seu próprio relatório dos últimos 30 dias; não mostra os campos de período das outras abas. Encontrar registros sem criar novos pode ser normal, pois uma reexecução também encontra registros conhecidos.

<a id="19-avisos-do-pje"></a>

## 19. Avisos do PJe

Avisos reúne comunicados recebidos nas fontes conectadas. A contagem no menu indica quantos ainda estão não lidos localmente.

1. Abra Avisos no menu. Use Somente não lidos [1] para alternar entre todos os comunicados e os pendentes de leitura.
2. Leia o título, a publicação, o autor quando informado e o corpo do aviso [2].
3. Confira Origens para saber em quais fontes o comunicado foi encontrado. Os links do texto são preservados quando existentes.
4. Após ler, clique em Marcar como lido [3]. O botão passa a Lido, e a contagem do menu é atualizada.
5. Se estiver usando o filtro de não lidos, uma nova consulta poderá remover da lista os avisos que você já marcou.

![Tela de Avisos do PJe com destaques vermelhos numerados](imagens/13-avisos.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Somente não lidos: filtro de leitura.
- **Destaque 2:** Comunicado: título, conteúdo e origens.
- **Destaque 3:** Marcar como lido: confirmação explícita da leitura local.

> **Atenção:** Ao contrário dos painéis de expedientes e publicações, nesta tela a leitura depende do clique em Marcar como lido. A confirmação de avisos no PJe durante a coleta e a leitura local são registros diferentes.

<a id="20-estatisticas-e-tempo-economizado"></a>

## 20. Estatísticas e tempo economizado

Estatísticas apresenta o volume de eventos dos expedientes, sua evolução diária e a distribuição das pendências e dos prazos ativos.

1. Escolha 7 dias ou 30 dias [1] para alterar o período dos indicadores de atividade e do gráfico.
2. Leia Atividade Total, Novos, Alterados e Resolvidos. A variação compara o período atual com o anterior; sem base anterior aparece quando a comparação não pode ser calculada.
3. Em Entradas e movimentações [3], cada coluna representa um dia. Use as cores da legenda e passe o cursor para consultar os volumes.
4. Role para Pendências Ativas e Situação dos Prazos. Essas distribuições representam o estado dos expedientes ativos.
5. No cartão Tempo economizado [2], abra Como calculamos para conhecer as regras da estimativa.

![Tela de Estatísticas e tempo economizado com destaques vermelhos numerados](imagens/14-estatisticas.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Período: alternância entre 7 e 30 dias.
- **Destaque 2:** Tempo economizado: estimativa operacional acumulada.
- **Destaque 3:** Gráfico: chegadas, alterações e resoluções por dia.

> **Atenção:** Tempo economizado é uma estimativa, não uma cronometragem. Conta coletas concluídas e não descartadas, limita o total a 4 horas por dia e evita repetir o tempo fixo nas reexecuções. O acumulado abrange todo o histórico, mesmo ao alternar 7/30 dias, e não inclui leitura jurídica nem providências posteriores.

<a id="21-configuracoes-perfil-tema-e-horario-diario"></a>

## 21. Configurações: perfil, tema e horário diário

Configurações permite ajustar o nome exibido, o tema e o horário da rotina automática.

1. No campo Nome de exibição [1], informe como deseja aparecer no painel. Isso não altera seu nome de usuário para login.
2. Em Tema visual [2], escolha Claro, Escuro ou Seguir o sistema operacional.
3. Em Horário diário [3], ajuste a hora desejada para a coleta automática. O fuso de referência exibido é America/Fortaleza (GMT-3).
4. Clique em Salvar alterações [4] e aguarde a notificação Configurações salvas.
5. Mantenha o computador, a aplicação e o serviço de coleta disponíveis nesse horário. Para fontes PJe, mantenha o token conectado e a autenticação preparada.

![Tela de Configurações: perfil, tema e horário diário com destaques vermelhos numerados](imagens/15-configuracoes.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Nome de exibição: identificação visual do perfil.
- **Destaque 2:** Tema visual: preferência de aparência.
- **Destaque 3:** Horário diário: agendamento da coleta.
- **Destaque 4:** Salvar alterações: gravação das preferências.

> **Atenção:** As opções do perfil e do horário são salvas por esse botão. As chaves das fontes, na parte inferior, são aplicadas imediatamente. Ajustar o horário não inicia uma coleta naquele instante.

<a id="22-configuracoes-fontes-e-prontidao-operacional"></a>

## 22. Configurações: fontes e prontidão operacional

As fontes conectadas definem quais consultas PJe e DJEN participam das coletas. A prontidão operacional informa se as credenciais locais estão configuradas.

1. Em Fontes conectadas, use a chave de cada fonte [3] para habilitar ou desabilitar sua coleta.
2. Use Todas as fontes [1] para aplicar a mudança em conjunto. Aguarde o processamento; eventuais falhas são exibidas em notificações.
3. Desativar uma fonte preserva seus dados e seu histórico, mas interrompe a participação nas coletas.
4. Em Prontidão operacional [2], confira Arquivo de credenciais, PIN e Segredo TOTP. Se algo estiver ausente, solicite ao responsável técnico a configuração.
5. A lista PJe contempla TJRN 1º/2º grau, TRE-RN 1º/2º grau, TSE 3º grau, TRT21 1º/2º grau e destinos TRF5: 2º grau/TRU, varas federais, JEF, turmas recursais e TRU alternativo.

![Tela de Configurações: fontes e prontidão operacional com destaques vermelhos numerados](imagens/16-fontes.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Todas as fontes: alteração em conjunto.
- **Destaque 2:** Prontidão operacional: configuração das credenciais.
- **Destaque 3:** Chave individual: habilitar ou desabilitar uma fonte.

> **Atenção:** O DJEN também aparece na lista de fontes e pode ser habilitado ou desabilitado. Sua coleta independe do token físico e do ciclo PJe; a OAB é configurada pelo responsável técnico. A indicação PJeOffice Integrado não é uma checagem contínua do dispositivo: a autenticação é verificada a cada coleta. Configuração presente não garante acesso ao tribunal; confirme o resultado na Pipeline e no Histórico.

<a id="23-configuracoes-alterar-a-senha-de-acesso"></a>

## 23. Configurações: alterar a senha de acesso

O formulário Segurança e senha de acesso altera a senha da sua conta no RYV Expedientes.

1. Em Configurações, role até Segurança e senha de acesso.
2. Digite a Senha atual [1].
3. Digite a Nova senha [2] e repita o mesmo valor em Confirmar nova senha [3]. Use pelo menos oito caracteres.
4. Clique em Alterar senha [4] e aguarde a confirmação Senha de acesso alterada.
5. No próximo acesso, use a nova senha. Se não souber a senha atual, solicite uma redefinição ao administrador.

![Tela de Configurações: alterar a senha de acesso com destaques vermelhos numerados](imagens/17-senha.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Senha atual: validação da identidade.
- **Destaque 2:** Nova senha: novo valor de acesso.
- **Destaque 3:** Confirmar nova senha: repetição do novo valor.
- **Destaque 4:** Alterar senha: envio da solicitação.

> **Atenção:** Esse formulário altera apenas a senha do painel. Não altera o PIN do certificado, o segredo TOTP nem a senha de acesso aos tribunais.

<a id="24-exportar-relatorios-em-pdf"></a>

## 24. Exportar relatórios em PDF

O ícone de download gera relatórios a partir da consulta aplicada. Ele está disponível nas listas de expedientes, nas publicações e nas abas de histórico correspondentes.

1. Aplique primeiro a busca, os filtros e o período. Clique no ícone de exportação da lista desejada.
2. Quando houver confirmação [1], confira o resumo e a quantidade. A exportação inclui todos os registros filtrados, inclusive os de outras páginas.
3. Para expedientes, escolha Sintético [3] para um relatório resumido ou Analítico [2] para dados detalhados e alterações abrangidas pelo período.
4. Para publicações, o download pode começar diretamente; na Visão geral, a confirmação apresenta a opção Baixar PDF.
5. Aguarde a geração. Localize o arquivo na pasta de downloads do navegador e confira se o conteúdo corresponde à consulta.
6. Se não houver registros, o sistema informa que não há resultados para exportar. Altere os filtros ou o período e tente novamente.

![Tela de Exportar relatórios em PDF com destaques vermelhos numerados](imagens/07-exportacao.png)

*Captura da interface real com dados fictícios de demonstração.*

- **Destaque 1:** Confirmação: resumo e quantidade incluída.
- **Destaque 2:** Analítico: detalhamento dos expedientes.
- **Destaque 3:** Sintético: versão resumida dos expedientes.

> **Atenção:** Na Visão geral, o PDF de Novos/Alterados usa os eventos de hoje. Nos demais cartões, ele usa o estado atual e apresenta alterações registradas hoje, embora os expedientes possam ter sido coletados antes. O relatório é um retrato dos dados locais no momento da geração.

<a id="25-roteiro-de-uso-diario"></a>

## 25. Roteiro de uso diário

Use este roteiro para uma conferência organizada do que a aplicação encontrou e do que ainda exige atenção.

1. Entre no RYV Expedientes e confira a data e a última sincronização na Visão geral.
2. Verifique cada fonte da Pipeline, inclusive as que ficam à direita na rolagem. Consulte o Histórico para fontes com falha ou interrupção.
3. Revise Urgentes, Não lidos e Prazos em cálculo. Abra os detalhes, confira o processo e consulte o PJe para as providências necessárias.
4. Revise Novos e Alterados. Verifique as mudanças de prazo e de informações antes de distribuir o trabalho.
5. Abra Publicações Processuais na Visão geral ou Publicações DJEN no menu. Leia o texto e use o inteiro teor quando disponível.
6. Leia os Avisos e marque explicitamente os comunicados já conferidos.
7. Se necessário, exporte as consultas em PDF e revise o Histórico de execuções para registrar a cobertura da coleta.
8. Encerre a sessão com Sair.

> **Atenção:** Abrir um registro marca leitura local; mantenha o controle das providências e dos prazos conforme a rotina do escritório. A ausência de registros numa consulta filtrada deve ser conferida com o período, os critérios e o resultado das fontes.

<a id="26-problemas-frequentes-e-como-resolver"></a>

## 26. Problemas frequentes e como resolver

Comece pelo sintoma abaixo. Quando precisar de ajuda, informe a área, a fonte, o horário e a mensagem exibida, sem enviar senha, PIN ou segredo TOTP.


| Situação | Procedimento |
| --- | --- |
| O endereço não abre | Confirme o endereço com o responsável técnico e peça a verificação dos serviços locais. |
| Não consigo entrar | Confira usuário, senha e Caps Lock. Use Esqueceu sua senha? para consultar a orientação de redefinição. |
| Executar coleta está desabilitado | Conecte o token. Se continuar indisponível, peça a verificação do dispositivo, PJeOffice e credenciais. |
| Uma fonte falhou | Abra Histórico > Orquestração > Ver erro. Corrija a causa e reexecute a fonte na Pipeline. |
| A lista está vazia | Confira período e filtros; limpe-os quando possível. Verifique se a fonte concluiu a coleta e está habilitada. |
| Há registros encontrados, mas nenhum novo | Pode ser uma consulta de registros já conhecidos. Confira também alterados e resolvidos no Histórico. |
| Não vejo uma publicação antiga | Em DJEN, mude as datas de coleta e clique em Pesquisar. O Histórico está limitado aos últimos 30 dias. |
| PDF está desabilitado | Aplique os filtros com Buscar, Pesquisar ou Aplicar período antes de exportar. |
| Não há registros para exportar | A consulta retornou zero resultados. Revise os critérios e o período. |
| A coleta automática não ocorreu | Confira o horário, o fuso, as fontes e se os serviços estavam ativos. Para PJe, verifique também o token. |
| O prazo aparece como um traço | Abra o detalhe e confira a situação: Em cálculo e Sem prazo têm significados diferentes. |
| Não consigo descartar | Confira se há fonte em execução ou se já não existem dados descartáveis naquele dia. |
| Nome alterado, mas login não mudou | Nome de exibição não altera o usuário de autenticação. |
| Erro de autenticação ao consultar | Recarregue a página e entre novamente se a sessão tiver expirado. Persistindo, informe a mensagem ao responsável. |

<a id="27-glossario-e-mapa-rapido-do-sistema"></a>

## 27. Glossário e mapa rápido do sistema

Use os termos abaixo para interpretar os registros e localizar a função adequada.

1. Triagem do dia e andamento: Visão geral. Pesquisa detalhada PJe: Expedientes. Texto de publicação: Publicações DJEN.
2. Entradas e execuções recentes: Histórico. Comunicados institucionais: Avisos. Volumes e estimativa: Estatísticas. Preferências, fontes e senha: Configurações.

| Termo | Significado |
| --- | --- |
| Expediente | Registro de comunicação ou pendência coletado no PJe e associado a um processo. |
| Publicação DJEN | Comunicação do Diário localizada pela OAB configurada. |
| Coleta | Consulta automática da fonte e gravação dos resultados na base local. |
| Pipeline | Visão do andamento e do resultado das fontes de coleta. |
| Novo | Registro descoberto pela primeira vez; não significa necessariamente expedição naquele dia. |
| Alterado | Expediente conhecido que recebeu mudança relevante identificada pela coleta. |
| Resolvido | Expediente classificado como inativo localmente; não significa que o processo inteiro foi encerrado. |
| Não lido | Evento ou publicação ainda sem leitura registrada no painel. |
| Prazo fatal | Data e hora de vencimento registradas conforme as informações coletadas da origem. |
| Disponibilização | Data da publicação informada pelo DJEN, diferente da data de coleta. |
| Pendência de ciência/resposta | Classificação da obrigação indicada no PJe; a ação deve ser realizada lá. |
| TOTP | Mecanismo de código temporário de autenticação, configurado pelo responsável técnico. |
