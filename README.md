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

## Estimativa de tempo economizado

O card da tela de estatísticas simula o trabalho operacional de uma pessoa em ritmo
normal, sem cronometragem real. Para cada fonte e dia, considera abrir o site,
autenticar com certificado/PIN e código quando aplicável, verificar avisos,
percorrer as caixas, conferir campos dos registros e organizar o resultado.
O tempo fixo líquido já desconta cerca de **2 minutos** para conferir a
automação. A leitura jurídica do teor e as providências posteriores não entram
na estimativa.

| Fontes | Passos específicos | Tempo fixo líquido por dia | Por registro |
| --- | --- | ---: | ---: |
| TJRN 1º e 2º grau | Entrar direto no PJe, autenticar, confirmar avisos e abrir as abas de expedientes | 6 min cada | 45 s por aba + 1 min 15 s por expediente encontrado |
| TRE-RN 1º e 2º grau; TSE 3º grau | Navegar pelo portal, selecionar o PJe, autenticar, passar pelos avisos e abrir as abas | 8 min cada | 45 s por aba + 1 min 15 s por expediente encontrado |
| TRT21 1º e 2º grau | Entrar pelo PDPJ, autenticar, conferir avisos, abrir a tabela de expedientes | 6 min cada | 2 min por expediente, incluindo abrir e fechar os detalhes |
| TRF5 2º grau/TRU; Varas da Justiça Comum; JEF 5ª Região; Turmas Recursais; TRU 5ª Região | Navegar pelo portal TRF5, escolher o destino, autenticar, confirmar avisos e abrir as abas | 8 min cada | 45 s por aba + 1 min 15 s por expediente encontrado |
| DJEN | Consultar cada uma das sete datas para a OAB configurada, percorrer páginas e organizar publicações | 12 min por coleta diária | 1 min 30 s por publicação nova |

No PJe, cada expediente encontrado exige conferir processo, destinatário,
documento, tipo de pendência, meio de comunicação e prazo, mesmo quando nada
mudou desde a coleta anterior. No DJEN, o valor variável considera apenas
publicações inéditas, pois a janela de sete dias retorna publicações já
consultadas em dias anteriores. O tempo fixo do DJEN representa cerca de
2 minutos por data, com o desconto de conferência descrito acima.
O número de avisos não é salvo por execução; seu tempo fica dentro da parcela
fixa, que pode subestimar um dia com muitos avisos.

O total soma as estimativas diárias das execuções **concluídas e não descartadas** desde o início
do histórico, com limite de **4 horas por dia** para o conjunto das fontes consultadas.
Esse acumulado não muda com o filtro de 7 ou 30 dias da tela de estatísticas.
Reexecuções da mesma fonte no mesmo dia contam o tempo fixo uma
vez. Para o PJe, conta o maior número de expedientes encontrado naquele dia;
para o DJEN, soma as publicações novas de cada execução. Falhas, execuções em
andamento e descartes não geram tempo economizado. A estimativa pode ser
calibrada após cronometrar uma amostra de consultas manuais por fonte.

Para executar API e frontend em contêineres, use `docker compose up -d --build`.
Esse modo usa o mesmo PostgreSQL configurado no `.env`. A coleta agendada
continua disponível pelo `./run-local.sh`.

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
