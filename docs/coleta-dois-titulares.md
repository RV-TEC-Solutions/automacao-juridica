# Coletas de MURILO e CRISTIANO

A sequência completa de fontes PJe é executada primeiro para MURILO e depois
reiniciada na primeira fonte habilitada para CRISTIANO. Ambas as fases pertencem
ao mesmo ciclo. Fontes desativadas continuam sendo puladas; falhas de uma fonte
não impedem a próxima; reexecutar uma fonte executa somente essa fonte e titular.

## Configuração

No `.env` da raiz, configure localmente:

```dotenv
PJE_COLLECTORS=murilo,cristiano
PJE_CRISTIANO_CERT_PIN=
PJE_CRISTIANO_TOTP_SECRET=
```

Preencha os dois valores de CRISTIANO no arquivo local, sem incluí-los no git.
As credenciais existentes `PJE_CERT_PIN` e `PJE_TOTP_SECRET` continuam sendo de
MURILO. Opcionalmente use `PJE_MURILO_CERT_PIN` e `PJE_MURILO_TOTP_SECRET`.
CRISTIANO nunca usa o PIN ou o autenticador de MURILO como alternativa.

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
A autenticação real de CRISTIANO ainda exige suas credenciais e um teste no
ambiente de execução; reconhecimento dos certificados não comprova login.
