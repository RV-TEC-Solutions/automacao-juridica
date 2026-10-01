# Painel de Expedientes

Aplicação local para acompanhar expedientes coletados do PJe/TJRN.

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
