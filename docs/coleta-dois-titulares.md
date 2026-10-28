# Coletas de MURILO e CRISTIANO

A sequência completa de fontes PJe é executada primeiro para MURILO e depois
reiniciada na primeira fonte habilitada para CRISTIANO. Ambas as fases pertencem
ao mesmo ciclo. Fontes desativadas continuam sendo puladas; falhas de uma fonte
não impedem a próxima; reexecutar uma fonte executa somente essa fonte e titular.

## Configuração

No `.env` local da raiz, com permissão `600` e ignorado pelo Git, configure:

```dotenv
PJE_COLLECTORS=murilo,cristiano
PJE_CERT_PIN=
PJE_TOTP_SECRET=
PJE_CRISTIANO_CERT_PIN=
PJE_CRISTIANO_TOTP_SECRET=
```

Preencha os valores somente nesse arquivo, sem incluí-los no Git.
As credenciais existentes `PJE_CERT_PIN` e `PJE_TOTP_SECRET` continuam sendo de
MURILO. Opcionalmente use `PJE_MURILO_CERT_PIN` e `PJE_MURILO_TOTP_SECRET`.
CRISTIANO nunca usa o PIN ou o autenticador de MURILO como alternativa.
O resolvedor lê somente esse arquivo, montado como somente leitura na API e no
worker. Credenciais herdadas do ambiente não substituem seus valores.
O caminho interno do arquivo no Docker é configurado por `PJE_CREDENTIALS_FILE`;
isso não cria uma segunda origem de credenciais. O antigo arquivo em
`~/.config/pje-automacao/.env` deixou de ser utilizado pelo projeto.

Depois de editar o `.env`, fora de uma coleta em andamento, execute:

```bash
docker compose up -d --force-recreate --no-deps backend worker
```

Isso garante que os dois serviços leiam o arquivo atualizado mesmo quando o
editor o salva por substituição. Não é necessário rebuild para mudar segredos.

### Importar um QR de exportação do Google Authenticator

O coletor espera uma chave Base32 no campo TOTP. O endereço
`otpauth-migration://offline?data=...` exportado pelo Google Authenticator contém
um payload Base64/Protobuf; ele deve ser convertido uma vez antes de configurar
o `.env`. O utilitário local faz essa conversão sem rede, Django ou novas
dependências:

```bash
cd /home/yurivale/automacao-juridica
.venv/bin/python backend-automacao/importar_totp.py --titular cristiano --salvar
```

Exporte somente o cadastro de Cristiano em um QR. Cole a URI completa ou a
linha `QR-Code:` do zbarimg quando o programa solicitar; a entrada é oculta e
não vai para o histórico do shell. Confira o nome e o emissor apresentados.
Depois informe, também no terminal local, os seis dígitos que aparecem nesse
cadastro do Authenticator.

O programa aceita um único cadastro TOTP com SHA1 e seis dígitos, compatível
com o coletor, que usa período de 30 segundos. Ele confere o código informado
com tolerância de um intervalo de 30 segundos. Se houver divergência, formato
incompatível, múltiplas contas ou alteração simultânea do `.env`, a gravação é
recusada. Sem `--salvar`, apenas os metadados são inspecionados.

O parser aceita `version` ausente/zero e versões 1 e 2 quando os campos seguem
a estrutura suportada, mantendo a validação de um único cadastro. O número
da versão sozinho não comprova compatibilidade; o código do app ainda precisa
coincidir antes de gravar. Enums omitidos/zero usam os defaults
SHA1, seis dígitos e TOTP, como no
[importador do Aegis](https://github.com/beemdevelopment/Aegis/blob/master/app/src/main/java/com/beemdevelopment/aegis/otp/GoogleAuthInfo.java).
Outras versões são recusadas com o valor encontrado na mensagem.

Para diagnosticar somente versão, lote e enums, sem mostrar nomes, chave ou
URI, e sem gravar arquivos:

```bash
.venv/bin/python backend-automacao/importar_totp.py --titular cristiano --diagnostico
```

A leitura usa `urlsplit`, decodificação percentual, Base64 e campos Protobuf.
A regex `[0-9]{6}` é usada somente para validar o código digitado do app.
As regras ficam em `backend-automacao/automation/totp_import.py`.

Após a conferência, somente a chave TOTP do titular escolhido é atualizada,
com permissão `600`. O segredo e a URI não são exibidos, e os demais valores
do `.env` são preservados. Se a chave exportada já coincidir com a configurada,
o utilitário informa essa igualdade sem revelar a chave nem substituir o arquivo.
A ferramenta não recria serviços nem testa login
no TJRN. Recrie API e worker pelo comando anterior fora de uma coleta ativa;
a aceitação pelo portal continua dependendo de homologação.

Formato consultado: [esquema de exportação usado pelo Aegis](https://github.com/beemdevelopment/Aegis/blob/master/app/src/main/proto/google_auth.proto)
e [codificação Protobuf](https://protobuf.dev/programming-guides/encoding/).

O padrão continua sendo `PJE_COLLECTORS=murilo` até a configuração das duas
credenciais. O DJEN continua independente, usando a OAB já configurada;
a consulta à OAB de CRISTIANO depende de configuração específica futura.

Prepare o instalador `docker/vendor/safenet.deb` conforme
[o guia Docker](../backend-automacao/docker/README.md). Nesta máquina há uma
cópia do pacote oficial em
`~/.local/share/safenet-10.9.4723/installer/` e uma cópia preparada no vendor.

Depois de validar as credenciais e fora de uma coleta em andamento:

```bash
docker compose build backend worker frontend
docker compose up -d --no-deps backend worker frontend
```

As migrações preservam as coletas anteriores como sendo de MURILO.
Não há alteração automática dos serviços ativos apenas ao editar o código.

## Coletar somente um titular

Na pipeline, selecione **Coletar para → Dr. Cristiano** e clique em
**Executar coleta**. O sistema percorre as fontes habilitadas de Cristiano
e encerra o ciclo ao terminar. Para repetir Murilo, selecione Dr. Murilo.
Os resultados dos outros titulares permanecem no painel e no histórico.

A seleção **Todos os titulares** inicia um novo ciclo completo na ordem de
`PJE_COLLECTORS`. O botão só é habilitado após uma escolha explícita. O
agendamento diário continua iniciando o ciclo completo automaticamente.

Uma coleta individual refaz todas as fontes habilitadas do titular escolhido.
Para repetir somente uma fonte, use **Reexecutar somente…** nessa etapa,
depois de terminar a coleta em andamento. Uma rejeição de credencial encerra
o ciclo individual; um erro de fonte permite seguir para a próxima fonte do
mesmo titular. O DJEN continua com seu fluxo independente.

Na API `POST /api/automation/runs/`, o corpo `{"collector":"cristiano"}`
inicia uma coleta individual, registrada como `trigger=collector`. Sem
`collector`, o comportamento continua sendo um ciclo completo. Com
`rerun=true`, a execução continua restrita à fonte e ao titular informados.

## Seleção do token

O PJeOffice gerenciado pelo worker recebe um diretório próprio por titular no
volume `pjeoffice_worker_data`, em `.pjeoffice-pro/identities/<titular>`.
Cada configuração permite somente a biblioteca correspondente ao titular.
Ao trocar de titular, o assinador anterior é encerrado e o seguinte é iniciado;
os navegadores já usam um contexto novo por fonte. A sessão do desktop é independente.

Antes de qualquer PIN, o worker verifica a biblioteca e o número de série:

| Titular | Módulo no worker | Série esperada |
| --- | --- | --- |
| MURILO | `/usr/lib/libaetpkss.so.3` | `2108950019F94896` |
| CRISTIANO | `/usr/lib/libeToken.so` | `027ef6e7` |

Se o módulo não reconhecer exclusivamente o token esperado, a coleta falha
antes de abrir o navegador e antes de enviar PIN. Autorizações de sites do
perfil principal são reaproveitadas; autorizações ainda inexistentes precisam
ser confirmadas no PJeOffice, como no fluxo anterior.

## Expedientes compartilhados

Um expediente mantém a chave única por fonte e identificador do PJe. O campo
`collection_accounts` registra em quais caixas ele permanece presente. Uma
coleta de CRISTIANO não arquiva itens exclusivos de MURILO. Um item compartilhado
só é arquivado quando deixa de aparecer em todas as caixas que o conheciam.
Fontes que não reconciliavam ausências continuam sem fazê-lo.

## Validação

Os testes cobrem a sequência das 24 etapas PJe, o uso de credenciais próprias,
o bloqueio de um token inesperado, a continuidade após falhas, a reexecução
isolada e a reconciliação de expedientes exclusivos e compartilhados.
Em 27/10/2026, CRISTIANO autenticou no TJRN 1º grau com identidade conferida
no cabeçalho do portal, e a execução 375 concluiu com 117 expedientes
encontrados (112 criados e 5 atualizados). O código gerado pela chave importada
também foi conferido com o Authenticator pelo operador. Esse resultado não
homologa os logins das demais fontes. O reconhecimento dos certificados,
isoladamente, não comprova login.
Os resultados da alternância e os limites do teste estão no
[relatório de 27/10/2026](homologacao-dois-titulares-2026-10-27.md).

## Falhas de credencial e acompanhamento

Uma rejeição explícita de PIN, PIN bloqueado, TOTP rejeitado, credencial ausente
ou divergência de identidade suspende as fontes restantes daquele titular no
ciclo e permite continuar com o próximo titular. Erros de um site continuam
permitindo tentar a fonte seguinte. Uma reexecução manual inicia outra tentativa
isolada; confira a credencial antes de usá-la.

O dashboard e as configurações mostram ambos os titulares e seus estados.
“Última fonte concluída” significa uma execução bem-sucedida, não a conclusão
de todas as fontes daquele advogado. O histórico inclui a coluna Titular.

## Memória no notebook

O worker está limitado a 512 MiB de RAM e 1536 MiB somando RAM e swap, com
uma CPU. O build Next.js usa um worker e otimizações de memória do Webpack.
Neste notebook, execute builds e testes em sequência, com os serviços da
aplicação parados durante a compilação. O limite do heap Node não equivale
ao limite total de RAM do processo ou do contêiner.

O heap padrão do build Docker do frontend é de 512 MiB. Com a swap cheia,
a compilação foi validada usando 768 MiB de RAM somente para o build
(256 MiB adicionais), sem alterar o limite do worker:

```bash
DOCKER_BUILDKIT=0 docker build --memory=768m --memory-swap=1536m \
  --cpu-period=100000 --cpu-quota=100000 \
  --build-arg 'NODE_OPTIONS=--max-old-space-size=512 --max-semi-space-size=8' \
  -t automacao-juridica-frontend ./frontend
```
