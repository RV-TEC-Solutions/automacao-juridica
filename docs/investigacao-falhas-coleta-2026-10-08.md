# Investigação das falhas de coleta — 08/10/2026

Consulta ao histórico `AutomationRun`, logs do worker e do PJeOffice, HTMLs e screenshot de diagnóstico, código dos conectores e carregamento público das telas de SSO. Horários das execuções em America/Fortaleza (UTC−3). O log Java do PJeOffice usa UTC: 01:47 de 09/10 corresponde a 22:47 de 08/10.

## Varas Federais (`varas-justica-comum`)

- Última falha consultada: execução **66**, 23:04:31–23:04:58. As execuções 58, 64 e 65 também falharam; o mesmo padrão aparece em 04 e 05/10.
- Login concluído. A coleta chega à árvore com seis abas, salva quatro HTMLs na execução 66 e falha ao clicar na quinta. Outras tentativas param na quarta ou sexta aba.
- O log identifica `#_viewRoot:status .rich-mp-container` interceptando o clique. É a camada de carregamento AJAX/RichFaces, não o aviso de expiração do certificado.
- `clicar_apos_dispensar_aviso_certificado()` usa `timeout=1000` e só repete quando consegue fechar o aviso do certificado. Assim, carregamentos AJAX que bloqueiem o clique por mais de um segundo encerram a coleta.
- `esperar_view_expedientes()` aceita timeout de `networkidle` e prossegue após um segundo; não verifica explicitamente o fim do carregamento RichFaces nem se o conteúdo já corresponde à aba selecionada.
- A camada já estava oculta no HTML final de diagnóstico, embora estivesse ativa durante as tentativas de clique: evidência de bloqueio transitório.
- Os HTMLs parciais ficam no disco, mas a execução falha antes de retornar os arquivos ao runner. Os contadores permanecem em zero e esses arquivos não são importados por essa execução.

**Conclusão:** problema de sincronização e prazo curto dos cliques; não é falha de token. Correção indicada: aguardar o término do AJAX, confirmar o conteúdo da aba e permitir tempo de clique compatível com o carregamento, mantendo o tratamento do aviso de certificado.

Evidências: `backend-automacao/respostas_expedientes/varas-justica-comum/20261008_230447/` e `diagnostico/20261008_230458_008893/`. Código: `backend-automacao/automation/services/pje/browser.py`, funções `clicar_apos_dispensar_aviso_certificado`, `esperar_view_expedientes` e `coletar_expedientes`; importação em `runner.py`.

## TRT21 segundo grau (`trt21-2g`)

- Falha **56**, 22:48:53–22:49:40: `entrar_com_pdpj()` não encontrou `.botao-certificado-titulo` visível em 15 segundos.
- A URL já era o SSO, cliente `pje-trt21-2g`. O HTML capturado contém apenas parte do documento, sem elemento `body`. A tentativa de screenshot também excedeu seu prazo.
- A falha ocorreu antes do clique de certificado e do preenchimento de PIN.
- A reexecução **67**, 23:05:13–23:05:27, teve **sucesso**, com mensagem “Nenhum expediente novo encontrado”. As execuções de 04 e 05/10 também tiveram sucesso.

**Conclusão:** evidências consistentes com carregamento incompleto/intermitente da tela de SSO. A última coleta já teve sucesso. Não foi demonstrada quebra permanente do seletor ou falha do token. Correção indicada: detectar carregamento incompleto e registrar falhas de recursos/JavaScript antes de aplicar uma nova tentativa limitada.

Evidência: `backend-automacao/respostas_expedientes/trt21-2g/diagnostico/20261008_224910_768910/page.html`.

## TRE-RN primeiro grau (`tre-rn-1g`)

- Falha **52**, 22:46:58–22:47:36: o helper AT-SPI terminou após 30 segundos com “Janela do PIN ausente: []”.
- A captura permaneceu na tela de login SSO, cliente `pje-trern-1g`, com tema `pje-v2`. O botão `#kc-pje-office` existe e continua chamando `autenticar(...)`.
- **Não há requisição ao PJeOffice no intervalo dessa execução.** O assinador registrou autenticações bem-sucedidas às 22:46:43–46, antes dela, e 22:47:47–49, durante a execução seguinte do TRE-RN segundo grau (**53**, sucesso, dois expedientes).
- Portanto, a mensagem do helper não comprova PIN incorreto nem defeito do token: o fluxo falhou antes de chegar ao assinador. O código chama o helper logo após o clique, sem confirmar a chamada local ao PJeOffice ou registrar erros JavaScript da página.
- O script público `pje-v2/js/pjeOffice.js` respondeu HTTP 200 e usa a integração conhecida: imagem HTTP para `localhost:8800/pjeOffice/requisicao/`, tarefa `sso.autenticador`, envio posterior do formulário. O script do tema PDPJ consultado apresentou o mesmo conteúdo.
- Em consulta pública via Chromium no worker, as telas de TRE-RN 1G e TRT21 2G carregaram com `autenticar` disponível, script HTTP 200 e sem erros JavaScript observados. Em uma tentativa posterior, com navegador visível, a abertura do SSO do TRE-RN excedeu 20 segundos antes de `domcontentloaded`; não foi possível chegar ao teste do botão nessa tentativa.
- Os testes públicos não usaram o certificado nem executaram coleta. No teste previsto do botão, chamadas ao PJeOffice seriam interceptadas; o timeout ocorreu antes do clique.
- As execuções **5** (04/10) e **21** (05/10) de TRE-RN 1G tiveram sucesso. Na tentativa anterior de 08/10 às 21h, **ambos** os graus do TRE-RN falharam com PJeOffice ausente no AT-SPI (43 e 44); isso é diferente da falha 52.

**Conclusão:** a falha recente é anterior ao uso do token. Há evidência de instabilidade de carregamento do SSO, mas não há console/rede da execução 52 para provar o motivo exato pelo qual o clique não gerou requisição. A aparência do login mudou, porém os dados disponíveis não demonstram que essa mudança quebrou a integração. Não é possível afirmar retrospectivamente se houve falha no script, bloqueio no navegador ou outro problema da página.

Correção indicada: registrar `pageerror`, falhas de recursos e resultado da chamada local sem expor cookies, desafios ou tokens; confirmar disponibilidade de `autenticar` e a comunicação com o assinador antes de esperar o PIN. Diferenciar falha da página de ausência da janela/PIN, evitando o diagnóstico enganoso atual.

Evidência: `backend-automacao/respostas_expedientes/tre-rn-1g/diagnostico/20261008_224735_896755/`. Código: `browser.py`, funções `clicar_certificado`, `autenticar_pje` e `abrir_pje`.

## Escopo

Investigação concluída com os registros disponíveis. Nenhum código funcional foi alterado, nenhum serviço foi reiniciado e nenhuma nova coleta ou autenticação com certificado foi iniciada.

## Correções posteriores solicitadas pelo usuário

- Cliques toleram até dez segundos de bloqueio transitório e aguardam a camada RichFaces antes de começar. A coleta aguarda a resposta POST da aba pelo identificador enviado no formulário, recebe o corpo completo e verifica o fim do carregamento antes de salvar o HTML.
- O SSO deve apresentar o botão e os scripts necessários. Há uma única recarga de recuperação, exclusivamente antes de chamar o assinador. Nenhuma autenticação com certificado é repetida automaticamente.
- O helper de PIN só começa depois de o navegador iniciar a requisição local de autenticação. As mensagens distinguem preparação da tela, comunicação com o PJeOffice, preenchimento do PIN e apresentação do campo de autenticação em duas etapas.
- Falhas de coleta informam a aba e a quantidade de capturas parciais não importadas. O histórico recebe a etapa e os erros de navegador observados; o worker registra fonte, duração, URL sem parâmetros, tipo de erro e caminhos de evidências.
- Cada falha com captura HTML também gera `diagnostico.json`. Os eventos de JavaScript, console, recursos interrompidos e HTTP de erro ficam limitados aos últimos vinte registros, com parâmetros de URL e segredos configurados removidos do resumo e das mensagens.
- Validação: 113 testes de backend aprovados na imagem Docker com PostgreSQL; Chromium com duas abas simuladas validou máscara inicial de 1,5 segundo e renderizações de 1,8 segundo, confirmando o conteúdo correto das duas abas. Não houve autenticação real nos tribunais nessa validação.
