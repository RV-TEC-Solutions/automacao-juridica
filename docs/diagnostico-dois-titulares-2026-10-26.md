# Diagnóstico e proposta: Murilo e Cristiano

> Atualização posterior: por orientação explícita do responsável, a origem
> atual das credenciais é o `.env` da raiz, com permissão `600`. As referências
> abaixo ao arquivo externo descrevem a investigação e a proposta anteriores
> a essa decisão. Consulte `coleta-dois-titulares.md` para a configuração atual.

Inspeção realizada em 26/10/2026 no código, na configuração local e nos contêineres ativos. Escopo: levantamento e proposta arquitetural. Não foram alteradas credenciais ou configurações operacionais, enviados PINs, iniciados logins nos tribunais ou executadas coletas reais.

## Resultado principal

O suporte básico já existe no commit `e3fee78` (`feat(coletas): adiciona execução sequencial por titular`). A solução mais enxuta é completar essa implementação e validar a operação, mantendo um único worker e um PJeOffice gerenciado, com perfil próprio por titular. Não é necessário duplicar o sistema, as fontes ou os expedientes.

**A situação atual é: os dois tokens são reconhecidos pelo worker, mas somente Murilo está habilitado e possui credenciais configuradas.** A identificação dos dois titulares no frontend ainda está incompleta.

## Evidências do computador e da operação

Consultas USB e PKCS#11 realizadas sem `--login` e sem fornecer PIN:

| Titular | Dispositivo USB | Rótulo retornado pelo módulo | Série do token | Biblioteca no worker |
| --- | --- | --- | --- | --- |
| Murilo | `1059:0017`, StarSign CUT | `AC CERTMAIS - MURILO MARIZ` | `2108950019F94896` | `/usr/lib/libaetpkss.so.3` |
| Cristiano | `0529:0620`, Aladdin Token JC / SafeNet eToken | `AC CERTMAIS - CRISTIANO LUIZ` | `027ef6e7` | `/usr/lib/libeToken.so` |

O módulo SafeSign reconheceu o token de Murilo e não reconheceu o de Cristiano. O módulo SafeNet reconheceu o de Cristiano e não apresentou outro token inicializado. Essa separação atende à verificação conservadora implementada em `verify_token`.

No host, `/usr/lib/libeToken.so` não foi encontrado no caminho padrão consultado. **Isso não impede o fluxo Docker:** a biblioteca existe no worker e conseguiu ler o token de Cristiano pelo socket PC/SC compartilhado. Não há necessidade demonstrada de instalar outro driver no host para esse fluxo.

Outras constatações:

- Backend, worker, frontend e PostgreSQL estavam em execução; não havia coleta pendente ou em andamento na consulta.
- O processo principal do worker estava com `PJE_OFFICE_MANAGED=true` e `PJE_COLLECTORS=murilo`; a API também estava configurada apenas para `murilo`.
- O Java do assinador estava ativo. Isso não comprova disponibilidade de todas as etapas de autenticação.
- O worker possuía as credenciais legadas de Murilo e não possuía `PJE_CRISTIANO_CERT_PIN` ou `PJE_CRISTIANO_TOTP_SECRET` no ambiente configurado. O arquivo externo consultado também não continha essas chaves.
- As migrações `automation.0017_automationrun_collector` e `expedientes.0009_expediente_collection_accounts` já estavam aplicadas.
- Os arquivos `collectors.py`, `identity.py` e `runner.py` no worker tinham os mesmos hashes dos arquivos locais. Não foi feita uma comparação integral das imagens com a árvore local.
- O `.env` do projeto tinha permissão `600`; `~/.config/pje-automacao/.env` tinha permissão `664`, divergindo do `600` exigido em `BOAS_PRATICAS.md`.

Reconhecimento do dispositivo e leitura do rótulo/série não comprovam validade do certificado, acerto do PIN, vínculo do autenticador ou acesso de Cristiano a cada tribunal. Esses pontos continuam pendentes de homologação.

## O que já foi implementado

| Área | Arquivos principais | Comportamento existente |
| --- | --- | --- |
| Cadastro dos titulares | `backend-automacao/automation/collectors.py` | Código, nome, série e módulo por titular; variáveis próprias; fallback legado somente para Murilo. |
| Habilitação e ordem | `backend-automacao/config/settings.py`, `.env.example`, `docker-compose.yml` | `PJE_COLLECTORS`, com padrão `murilo`; variáveis de Cristiano encaminhadas ao worker. |
| Fila e execução | `automation/queue.py`, `automation/services/pje/runner.py` | Percorre as 12 fontes PJe habilitadas para Murilo e depois reinicia a sequência para Cristiano, no mesmo ciclo. Reexecução fica restrita à fonte e ao titular. |
| Seleção do token | `automation/services/pjeoffice/identity.py`, `backend-automacao/docker/pjeoffice-pro`, `backend-automacao/entrypoint.sh` | Confere módulo/série antes do PIN e troca o processo do assinador usando diretórios separados por titular. |
| Navegador e PIN/TOTP | `automation/services/pje/browser.py`, `automation/services/pjeoffice/atspi.py` | Novo contexto de navegador por fonte; fluxo existente recebe temporariamente as credenciais do titular corrente. |
| Persistência | `automation/models.py`, `expedientes/models.py`, `automation/services/pje/persistence.py` e migrações acima | `AutomationRun.collector` registra a identidade; `Expediente.collection_accounts` controla presença em cada caixa. |
| API e pipeline | `automation/views.py`, `automation/pipeline.py` | Execuções e histórico incluem titular; etapas da pipeline incluem titular e identificam quem está executando. |
| Frontend | `frontend/app/page.tsx`, `frontend/app/components/collection-pipeline.tsx`, `frontend/app/lib/types.ts` | A pipeline diferencia etapas por titular e envia o titular correto ao reexecutar. |
| Drivers e documentação | `backend-automacao/Dockerfile`, `backend-automacao/docker/README.md`, `docs/coleta-dois-titulares.md` | Inclusão do SafeNet e orientação inicial para dois titulares. |

Os caminhos abreviados `automation/` e `expedientes/` nesta tabela ficam em `backend-automacao/`.

## Arquitetura recomendada

Manter **fonte** e **titular** como dimensões separadas. TJRN 1º grau continua uma única fonte; passa a ter uma execução por titular no ciclo. Com as 12 fontes atuais habilitadas, são 24 etapas PJe. O DJEN continua uma consulta independente, com cobertura definida por OAB.

O worker deve continuar sequencial. Ao iniciar uma identidade, resolve suas credenciais, verifica seu token, prepara o perfil isolado do PJeOffice e abre uma sessão nova do navegador por fonte. Ao trocar de titular, encerra o assinador anterior antes de iniciar o seguinte. Esse mecanismo já existe e se ajusta ao uso dos dois tokens neste notebook.

O uso temporário de `os.environ` é aceitável para esse único worker sequencial. Não permite paralelizar titulares ou executar um segundo worker com segurança: há ambiente global, um assinador e uma porta local compartilhados. Documentar e garantir uma única instância; não executar o worker de `run-local.sh` simultaneamente com o worker Docker. Se for necessário reforçar isso em código, usar um bloqueio global de execução, sem introduzir outra fila ou serviço.

Preservar a unicidade de expediente por `(source, identificador_pje)`. Um expediente compartilhado permanece um único registro, conhecido por ambas as caixas. A coleta de Cristiano não pode arquivar um expediente exclusivo de Murilo; um compartilhado só deixa de estar ativo quando estiver ausente de todas as caixas que o conheciam. O código e os testes existentes já contemplam essas regras.

Há uma hipótese a validar: os campos mutáveis do mesmo identificador devem representar o mesmo expediente nas duas caixas. Hoje a última coleta sobrescreve campos como `caixa`, `acao_pje` e prazo. Se a homologação mostrar diferenças relevantes por advogado, será necessário persistir essas observações por titular. Não recomendo criar essa estrutura adicional sem confirmar a necessidade.

## Complementos antes da ativação confiável

### 1. Credenciais e configuração

O mínimo funcional oferecido pelo código atual é acrescentar no `.env` local:

```dotenv
PJE_COLLECTORS=murilo,cristiano
PJE_CRISTIANO_CERT_PIN=
PJE_CRISTIANO_TOTP_SECRET=
```

Os campos vazios acima são apenas um modelo; devem receber os valores verdadeiros em edição local. As chaves legadas `PJE_CERT_PIN` e `PJE_TOTP_SECRET` continuam pertencendo a Murilo. A chave usada pelo código é **`PJE_TOTP_SECRET`**, não `TOTP_SECRET`. O valor TOTP é o segredo de cadastramento do autenticador, não o código temporário de seis dígitos.

Para a configuração definitiva, recomendo uma única origem de segredos em `~/.config/pje-automacao/.env`, com permissão `600`, alinhada a `BOAS_PRATICAS.md`. Hoje README e código mantêm um arranjo transitório com segredos também no `.env` raiz. O Compose declara variáveis vazias, e o `load_dotenv` não as substitui; somente preencher o arquivo externo não resolve a configuração atual.

O ajuste enxuto é centralizar a leitura desse arquivo em um único resolvedor, aproveitando a montagem somente para leitura já existente; resolver chaves por titular e preservar a compatibilidade de Murilo. Remover declarações vazias de segredos que bloqueiem essa leitura e harmonizar README, `.env.example` e `docs/coleta-dois-titulares.md`. Manter `PJE_COLLECTORS` como configuração não secreta compartilhada por API e worker. Não basta mudar apenas o worker, porque a API também valida quais titulares estão habilitados.

O status deve usar o mesmo resolvedor efetivo. Se a API ler o arquivo montado, pode informar apenas presença/configuração; presença física e autenticação precisam de evidência produzida no worker. Nenhum endpoint deve retornar PIN ou segredo. Uma configuração somente com variáveis de ambiente também precisa ser explícita no Compose: o `.env` da raiz, por si só, não injeta todas as chaves nos serviços, conforme a [documentação oficial do Docker](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/).

### 2. Falhas de autenticação e identidade

Em `runner.py`, qualquer falha atualmente permite agendar a próxima fonte. Isso é adequado para indisponibilidade de um tribunal, mas uma rejeição explícita de PIN pode voltar a ser tentada nas fontes seguintes. Antes de operar automaticamente, distinguir falha de fonte de falha da credencial: ao detectar PIN inválido/bloqueado ou identidade incompatível, suspender as próximas tentativas daquele titular no ciclo e prosseguir para o outro, com motivo visível. Não repetir automaticamente um PIN rejeitado.

Adicionar pré-verificação por titular, sem enviar PIN, para detectar credenciais ausentes e token incompatível. O endpoint `token_status` e a verificação genérica em `physical_token.py` hoje confirmam apenas que há algum cartão inserido. Eles não demonstram que os dois titulares estão prontos.

Na homologação, conferir a identidade autenticada nos portais. O código confirma a chegada ao painel, mas não compara explicitamente o usuário autenticado ao titular esperado. Quando houver identificador estável disponível, essa conferência deve anteceder a persistência. A série conferida hoje é a série física do token, não a impressão digital do certificado; se houver vários certificados no mesmo dispositivo, a seleção também precisa ser validada.

### 3. Visibilidade no frontend

| Ponto | Lacuna atual | Complemento proposto |
| --- | --- | --- |
| Resumo no dashboard | Os nomes aparecem nas etapas, mas Cristiano pode ficar fora da área inicialmente visível da rolagem horizontal. | Mostrar acima da pipeline: **“Titulares habilitados: Dr. Murilo e Dr. Cristiano”**, com status individual. Usar “Coletando Dr. Cristiano” apenas durante execução real. |
| Contagem | O texto diz “fontes”, embora a mesma fonte apareça para dois titulares. | Exibir etapas por titular e separar o resultado do DJEN, evitando sugerir 24 fontes distintas. |
| Histórico de coletas | A API envia `collector`/`collector_label`, mas `CollectionHistoryPanel` não os renderiza e `CollectionRun` não os tipa. | Acrescentar a coluna Titular, inclusive no detalhe do erro. Atualizar `frontend/app/lib/types.ts`. |
| Configurações | `settings_view` e `configuracoes/page.tsx` mostram um único conjunto PIN/TOTP e um indicador fixo de PJeOffice. | Mostrar Murilo e Cristiano separadamente: habilitação, credenciais configuradas, token verificado e última coleta bem-sucedida. Usar “não verificado” quando não houver evidência. |
| Expediente e histórico de eventos | O serializer não expõe `collection_accounts`; o evento não informa o titular da execução. | Expor nomes/códigos seguros de origem e mostrar na gaveta “Encontrado nas caixas de Murilo e Cristiano”, distinguindo descoberta histórica de presença atual. Titular da coleta não deve ser confundido com destinatário ou responsável jurídico. |
| Navegação para falhas | O link da pipeline passa apenas `failed_source`, repetido entre titulares. | Acrescentar titular ou `run_id` para identificar a execução correta no histórico. |

Arquivos envolvidos: `automation/views.py`, `automation/pipeline.py`, `expedientes/serializers.py`, `frontend/app/lib/types.ts`, `frontend/app/page.tsx`, `frontend/app/configuracoes/page.tsx`, `frontend/app/components/collection-pipeline.tsx`, `frontend/app/components/collection-history.tsx`, `frontend/app/components/expediente-drawer.tsx` e `frontend/app/historico/view.tsx`.

Distinguir claramente **habilitado**, **credenciais configuradas**, **token detectado** e **coleta concluída**. A presença de Cristiano em `PJE_COLLECTORS` não é evidência de que seus dados foram coletados. A conclusão do ciclo deve considerar a cobertura esperada dos dois titulares; ausência de uma fase precisa aparecer como coleta incompleta.

### 4. Pontos adjacentes

- **DJEN:** `automation/services/djen/client.py` consulta uma única OAB configurada em `DJEN_OAB_NUMBER`/`DJEN_OAB_STATE`. Habilitar o token de Cristiano não amplia essa cobertura. Se a intenção também incluir publicações dele, acrescentar sua OAB em um fluxo próprio de consultas, preservando a deduplicação. A UI deve explicitar a cobertura efetiva do DJEN.
- **Avisos:** `NoticeSource` registra confirmação externa por aviso/fonte, sem titular. A deduplicação do conteúdo pode continuar; se for preciso comprovar confirmação externa por advogado, registrar essa confirmação também por titular. A leitura local compartilhada tem outra finalidade.
- **Métricas:** `automation/time_saved.py` agrupa por dia/fonte e usa o maior volume das execuções. Não distingue trabalho de duas caixas. Revisar a premissa da estimativa se ela precisar considerar ambos, evitando somar expedientes compartilhados como se fossem registros únicos diferentes.
- **Exportações e filtros:** incluir origem por titular nos relatórios/filtros caso se deseje rastreabilidade fora da gaveta. É uma extensão, não pré-requisito para autenticar o segundo token.
- **Execução local:** o caminho de dois titulares exige PJeOffice gerenciado no Docker. O `run-local.sh` não fornece esse gerenciamento. Manter essa limitação documentada ou implementar suporte específico antes de usar o modo local com ambos.

## Sequência de implantação sugerida

1. Completar os complementos de configuração, falhas de credencial e frontend acima, mantendo a identidade de Murilo compatível com o histórico existente.
2. Inserir localmente as credenciais verdadeiras de Cristiano, corrigir a permissão do arquivo externo e validar a associação do autenticador à sua conta nos portais. Conferir sincronização do relógio.
3. Construir as imagens alteradas. Em janela sem coleta ativa, recriar os serviços consumidores. Os drivers e as duas migrações já estão disponíveis neste ambiente; não há necessidade de reinstalar tudo. Alterar o `.env` não modifica os processos ativos.
4. Homologar uma fonte para Cristiano de forma isolada. O endpoint atual permite `source`, `collector=cristiano` e `rerun=true`; a flag é necessária para não encadear todas as fontes. Confirmar identidade, PIN, TOTP, autorizações do site, captura e origem dos dados. Não inserir segredos no corpo desse pedido.
5. Validar a troca Murilo → Cristiano → Murilo e depois as 12 fontes para cada titular, incluindo eventuais diferenças de cadastro/acesso e expedientes compartilhados.
6. Só então liberar o ciclo diário dos dois, com estados individuais e erros visíveis. Em uma reversão, desabilitar Cristiano na configuração e recriar os consumidores em momento ocioso, preservando os dados já coletados e sua origem.

## Validações realizadas e limites

- **16 testes de backend passaram** em `automation.test_collectors`, usando o código local e um banco PostgreSQL temporário de nome exclusivo, removido ao final. Cobrem isolamento, seleção conservadora do token, troca simulada do assinador, sequência de 24 etapas, reexecução e reconciliação de caixas exclusivas/compartilhadas.
- **11 testes de frontend passaram** nos componentes `collection-pipeline` e `collection-history`.
- Não foi executada a suíte completa, build ou E2E, pois a atividade não alterou a aplicação. Os testes existentes não comprovam as lacunas de UI e os mecanismos adicionais propostos neste documento.
- Não houve autenticação real de Cristiano, teste de PIN, validação da validade do certificado nem comprovação de acesso a qualquer tribunal. A confirmação atual é de presença e reconhecimento do token.

Após a implementação, acrescentar testes específicos para status por titular, rejeição de PIN sem novas tentativas nas fontes seguintes, cobertura incompleta do ciclo, identificação do titular no histórico/configurações e troca real de identidade em homologação.
