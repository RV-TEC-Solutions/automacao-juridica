# Painel de Expedientes

Aplicação local para acompanhar expedientes coletados do PJe/TJRN.

## Instalação inicial

Requer Python 3.12+, Node.js 20+, PJeOffice e uma sessão gráfica Linux com AT-SPI.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend-automacao/requirements.txt
.venv/bin/playwright install chromium
npm --prefix frontend install
./run-local.sh setup
```

Configure `PJE_CERT_PIN` e `PJE_TOTP_SECRET` em `~/.config/pje-automacao/.env`.
O arquivo permanece fora do repositório e os valores nunca são devolvidos pela API.

## Executar

```bash
./run-local.sh
```

O comando sobe a API Django em `127.0.0.1:8007`, o worker/agendador e o frontend em
`http://localhost:3002`. A coleta diária usa `America/Fortaleza`, por padrão às 06:00.

## Validação

```bash
.venv/bin/python backend-automacao/manage.py test automation expedientes
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```
