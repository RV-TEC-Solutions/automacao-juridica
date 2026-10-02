# Painel de Expedientes

Aplicação local para acompanhar expedientes coletados do PJe e publicações do
Diário de Justiça Eletrônico Nacional (DJEN).

## Instalação inicial

Requer Python 3.12+, Node.js 20+, Docker Compose, PJeOffice e uma sessão gráfica Linux com AT-SPI.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend-automacao/requirements.txt
.venv/bin/playwright install chromium
npm --prefix frontend install
cp .env.example .env
# Edite POSTGRES_PASSWORD no .env antes de iniciar o banco.
docker compose up -d postgres
```

O PostgreSQL escuta apenas em `127.0.0.1:5433` por padrão. O volume
`postgres_data` preserva os dados entre reinicializações. Inicie o contêiner
manualmente antes de iniciar a aplicação.

Para uma instalação nova, sem SQLite a importar:

```bash
./run-local.sh setup
```

Configure `PJE_CERT_PIN` e `PJE_TOTP_SECRET` em
`~/.config/pje-automacao/.env`. Esse arquivo permanece fora do repositório
e os valores nunca são devolvidos pela API.

A consulta pública do DJEN usa por padrão a OAB `5691/RN`. Para outra
inscrição, configure `DJEN_OAB_NUMBER` e `DJEN_OAB_STATE` no `.env`. O DJEN
consulta as publicações do Diário dos últimos sete dias, incluindo o dia
atual, e é agendado diariamente no horário configurado, independentemente
das fontes PJe e do token físico. Reexecuções manuais usam a mesma janela.

## Migrar o SQLite existente

Pare a API, o worker e o frontend. O PostgreSQL de destino precisa estar
completamente vazio: não execute `setup` nem `run-local.sh` antes da
importação. Com o contêiner iniciado e o `.env` configurado, execute:

```bash
./run-local.sh import-sqlite
```

O comando cria um backup consistente em `backups/`, aplica as migrations,
transfere os dados e confere as contagens. Ele preserva o
`backend-automacao/db.sqlite3` original. Se falhar, a aplicação fica
bloqueada pela marca `.postgres-import-incomplete`. Inspecione o erro e
recrie **somente o volume deste projeto**, após confirmar seu nome com
`docker compose config --volumes`, antes de repetir a importação. Não
apague o backup ou a marca sem concluir a recuperação.

Após a importação, confirme o login e as telas de expedientes, avisos e
histórico. Execute uma coleta controlada e verifique o resultado antes de
retomar o uso normal. Não execute `setup` em uma base importada; ele é
reservado à instalação inicial.

## Executar

```bash
docker compose up -d postgres
./run-local.sh
```

O script verifica a conexão, aplica migrations pendentes e sobe a API Django
em `127.0.0.1:8007`, o worker/agendador e o frontend em
`http://localhost:3002`. A coleta diária usa `America/Fortaleza`, por
padrão às 06:00.

Para executar API e frontend em contêineres, use `docker compose up -d --build`.
Esse modo usa o mesmo PostgreSQL configurado no `.env`. A coleta agendada
continua disponível pelo `./run-local.sh`.

### Teste isolado com coleta PJe

Esta pilha usa banco próprio e instala Chromium e PJeOffice no contêiner do
worker. O PJeOffice instalado no notebook não é usado. Para autenticar no PJe,
o worker lê `PJE_CERT_PIN` e `PJE_TOTP_SECRET` de
`~/.config/pje-automacao/.env` e acessa o token pelo serviço PC/SC do host,
compartilhado em `/run/pcscd`. O token precisa estar conectado e o serviço
PC/SC ativo no computador.
Para o token StarSign CUT S, esta configuração também monta, somente para
leitura, o driver PKCS#11 `/usr/lib/libaetpkss.so.3.9.34.1` instalado no host.
A biblioteca cliente PC/SC do host também é montada em
`/opt/token-libs/libpcsclite.so.1` para manter a mesma versão do protocolo.
A versão de `libstdc++` exigida pelo driver é montada em
`/opt/token-libs/libstdc++.so.6`.
As demais fontes podem ser desativadas na interface para testar apenas o
PJe 1º Grau.

```bash
docker compose -f docker-compose.isolated.yml up -d --build
docker compose -f docker-compose.isolated.yml ps
```

Acesse `http://localhost:3003` com usuário `admin` e senha `admin`. A API fica
em `127.0.0.1:8008`. O projeto Compose `bmr-isolado` tem rede e volume de banco
próprios; o banco `bmr-postgres-1` continua separado. O worker processa as
coletas acionadas na interface e registra `Executando coleta #...` em
`docker compose -f docker-compose.isolated.yml logs -f worker`. O agendamento
diário fica desligado nesta pilha de testes.

Se a coleta parar antes do PIN, confira o token no worker:

```bash
docker compose -f docker-compose.isolated.yml exec worker pcsc_scan -c -t 1
docker compose -f docker-compose.isolated.yml exec worker pkcs11-tool --module /usr/lib/libaetpkss.so.3.9.34.1 -L
```

`Card inserted` confirma apenas a presença do cartão. Se o segundo comando
mostrar `token not recognized`, o driver ainda não consegue ler o certificado;
retire e recoloque o token antes de tentar outra coleta.

Para parar os serviços, preservando os dados de teste:

```bash
docker compose -f docker-compose.isolated.yml down
```

## Backup e restauração do PostgreSQL

Pare a aplicação antes da restauração. Crie um backup manual em formato
customizado, fora do Git:

```bash
mkdir -p backups
chmod 700 backups
umask 077
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backups/postgres.dump
```

Para restaurar esse backup sobre o banco configurado no `.env`, com o
contêiner ativo e a aplicação parada:

```bash
docker compose exec -T postgres sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/postgres.dump
```

A restauração substitui os dados do banco de destino. Depois de novas
gravações no PostgreSQL, use seus backups para recuperação; o SQLite
preservado representa apenas o estado anterior à migração.

## Validação

```bash
.venv/bin/python backend-automacao/manage.py test automation expedientes
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Os testes Django usam um banco de teste PostgreSQL separado.
