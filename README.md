# RYV Expedientes

## Manual do usuário

Consulte o [Manual do usuário](docs/manual-do-usuario/MANUAL_DO_USUARIO.md),
com instruções passo a passo, índice e capturas com destaques vermelhos,
ou baixe a [versão em PDF](docs/manual-do-usuario/RYV-Expedientes-Manual-do-Usuario.pdf).
As capturas utilizam dados fictícios de demonstração.

## Guia técnico

Aplicação para acompanhar expedientes do PJe e publicações do Diário de Justiça
Eletrônico Nacional (DJEN). Este guia explica como implantar em outro notebook
sem as dependências previamente instaladas.

## Ambiente validado e arquitetura

Inventário conferido em **08/10/2026**. A coleta **#47, TJRN 1º grau**, terminou
com sucesso: 38 expedientes encontrados, 2 criados e 4 atualizados. A quantidade
depende da conta e dos dados do tribunal. Esse teste confirma o fluxo A3 no
TJRN 1º grau; outros modelos de token e fontes precisam de validação própria.

Use **Ubuntu 24.04 LTS amd64/x86_64**, instalado diretamente no notebook.
O host de referência informa **Ubuntu 24.04.5 LTS**. Windows, macOS, WSL, ARM
ou USB redirecionado por uma VM não foram validados neste procedimento.
Se a máquina não tem Linux, instale Ubuntu 24.04 pelo
[instalador oficial](https://releases.ubuntu.com/24.04/) antes dos comandos.
É necessário usuário com `sudo`, Bash, internet, acesso ao código e aos
instaladores, token A3 conectado e PIN/TOTP válidos da conta do tribunal.

Para um notebook ainda sem sistema, obtenha a ISO Desktop amd64 na página
oficial, grave-a em pendrive com a ferramenta de criação de disco de inicialização
de outro computador, inicie pelo pendrive e siga “Instalar Ubuntu”. Crie o usuário
administrador, conecte Ethernet/Wi-Fi, reinicie e abra o Terminal. A instalação
do sistema é a etapa anterior ao APT; não há comando da aplicação que substitua
o instalador do sistema operacional.

```text
Token A3 na USB do notebook
  → kernel Linux / controlador USB
  → libusb + driver CCID (libccid.so), carregado pelo pcscd do host
  → socket /run/pcscd/pcscd.comm compartilhado com backend e worker
  → SafeSign (PKCS#11) → PJeOffice → Chromium, dentro do worker
  → API Django → PostgreSQL
  → frontend Next.js, porta 3002 → navegadores da rede do escritório
```

O `pcscd` é o serviço específico do token que roda fora do Docker. CCID é uma
biblioteca carregada por ele, não um aplicativo com janela. Docker/containerd
são outros serviços locais. No modo já testado, Node.js executa o frontend no
host. Python da aplicação, Java, PJeOffice, SafeSign e o navegador da coleta
ficam dentro dos containers; não precisam ser instalados no desktop.

O token testado é **Giesecke & Devrient StarSign CUT**, USB **1059:0017**.
O cadastro CCID associa esse ID a `Giesecke & Devrient GmbH StarSign Crypto USB Token`.
A biblioteca do leitor é:

```text
/usr/lib/pcsc/drivers/ifd-ccid.bundle/Contents/Linux/libccid.so
```

A associação foi confirmada pelo USB e pelo cadastro `/etc/libccid_Info.plist`;
não foi possível consultar a memória do daemon como administrador.
O suporte genérico USB vem no kernel Ubuntu: não existe um instalador separado
“USB para A3”. Outro modelo pode ser detectado pelo CCID e ainda exigir outro
driver PKCS#11 para acessar seu certificado.

### Versões exatas no notebook de referência

| Componente | Versão/pacote instalado | Função |
| --- | --- | --- |
| Kernel | `7.0.0-38-generic` | USB e hardware |
| Metapacote HWE | `linux-image-generic-hwe-24.04=7.0.0-38.38~24.04.4` | Kernel observado |
| Driver CCID | `libccid=1.5.5-1` | Comunicação com leitor/token |
| Serviço PC/SC | `pcscd=2.0.3-1build1` | Acesso ao dispositivo |
| Cliente PC/SC | `libpcsclite1=2.0.3-1build1` | Biblioteca de comunicação |
| Biblioteca USB | `libusb-1.0-0=2:1.0.27-1` | USB em espaço de usuário |
| Diagnóstico PC/SC | `pcsc-tools=1.7.1-1` | `pcsc_scan` |
| Diagnóstico USB | `usbutils=1:017-3build1` | `lsusb` |
| Docker Engine/CLI | `docker.io=29.1.3-0ubuntu3~24.04.2` | Engine/CLI `29.1.3` |
| Compose | `docker-compose-v2=2.40.3+ds1-0ubuntu1~24.04.1` | `docker compose` |
| containerd | `containerd=2.2.1-0ubuntu1~24.04.3` | Runtime |
| runc | `runc=1.3.4-0ubuntu1~24.04.1` | Runtime OCI |
| Node.js local | `22.23.3` | Frontend no modo testado |
| npm local | `10.9.9` | Instalação do frontend |

Essas versões foram medidas, não estimadas. O kernel registra a referência,
mas não significa que apenas essa revisão funcione em outro hardware.
Preserve os prefixos Debian/Ubuntu, como `2:`, nos comandos APT.
Este guia usa os pacotes Ubuntu `docker.io`/`docker-compose-v2`, como o host
original; não os misture com `docker-ce`/`docker-compose-plugin` de outro repositório.
Se uma versão desaparecer do APT, use o pacote arquivado da mesma versão ou
valide outra combinação; não troque silenciosamente pela versão mais recente.

### Dependências e serviços nos containers

| Componente | Versão observada |
| --- | --- |
| Base Ubuntu | `ubuntu:24.04`, digest `sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55` |
| Python | `3.12.3`; pacote `python3.12=3.12.3-1ubuntu0.17` |
| Django | `5.2.18`, fixado no Dockerfile |
| Playwright / Chromium | `1.63.0` / Chrome for Testing `153.0.8010.12`, revisão `1243` |
| PJeOffice Pro | `2.5.16u`, Linux x64 |
| Java usado pelo assinador | Zulu `8.72.0.17`, OpenJDK `1.8.0_382-b05`, incluído no ZIP |
| Java adicional do APT | `default-jre=2:1.21-75+exp1`; o launcher usa o Java do ZIP |
| SafeSign | `safesignidentityclient=4.7.0.0-AET.000`, Ubuntu 24.04 x86_64 |
| Biblioteca SafeSign | `/usr/lib/libaetpkss.so.3.9.34.1`, alias `/usr/lib/libaetpkss.so.3` |
| PC/SC instalado | `pcscd` e `libpcsclite1`, ambos `2.0.3-1build1` |
| CCID / USB | `libccid=1.5.5-1` / `libusb-1.0-0=2:1.0.27-1` |
| Xvfb | `2:21.1.12-1ubuntu1.8`, tela virtual `:99` |
| D-Bus | `dbus-x11=1.14.10-4ubuntu4.1` |
| AT-SPI | `at-spi2-core=2.52.0-1build1` |
| Python AT-SPI | `python3-pyatspi=2.46.1-1`, executado por `/usr/bin/python3` |
| Ponte Java ATK | `libatk-wrapper-java` e `libatk-wrapper-java-jni`, ambos `0.40.0-3build2` |
| OpenSC | `0.25.0~rc1-1ubuntu0.2`, fornece `pkcs11-tool` |
| PostgreSQL | imagem `postgres:18.6`, servidor `18.6`, pacote `18.6-1.pgdg13+2` |
| Frontend do projeto | Next.js `16.3.2`, React/React DOM `19.2.8`, conforme lockfile |

O Compose contém `postgres` (banco), `backend` (API), `worker` (fila/agendamento)
e `frontend` (opcional no modo local). Só o worker inicia PJeOffice, com
`PJE_OFFICE_ENABLED=true`. O driver SafeSign é instalado na imagem Ubuntu
compatível e usa o leitor do `pcscd` no host pelo socket compartilhado.
A tela Xvfb, D-Bus, Java ATK e AT-SPI permitem localizar a janela e preencher PIN.
**As janelas do navegador e PJeOffice não aparecem no desktop.**
PJeOffice atende internamente em 8800/8801, sem publicação na rede.
Não é necessário `--privileged`, nem montar todo `/dev/bus/usb`.

As tabelas registram o ambiente testado, mas as tags Docker e os intervalos de
`requirements.txt` não congelam tudo. O Dockerfile fixa Django e o ZIP/checksum
PJeOffice; pacotes APT e outras dependências Python podem mudar em builds futuros.
Para preservar o conteúdo interno exatamente, use a exportação de imagens
explicada ao final do passo a passo.

## 1. Instalar dependências no notebook vazio

```bash
cat /etc/os-release
uname -r
dpkg --print-architecture
sudo apt-get update
sudo apt-get install -y software-properties-common ca-certificates curl git xz-utils openssl nano
sudo add-apt-repository -y universe
sudo apt-get update
```

A arquitetura deve ser `amd64`. Instale as versões do host validado:

```bash
sudo apt-get install -y \
  libccid=1.5.5-1 \
  pcscd=2.0.3-1build1 \
  libpcsclite1=2.0.3-1build1 \
  libusb-1.0-0=2:1.0.27-1 \
  pcsc-tools=1.7.1-1 \
  usbutils=1:017-3build1 \
  docker.io=29.1.3-0ubuntu3~24.04.2 \
  docker-compose-v2=2.40.3+ds1-0ubuntu1~24.04.1 \
  containerd=2.2.1-0ubuntu1~24.04.3 \
  runc=1.3.4-0ubuntu1~24.04.1
```

Confira a disponibilidade se o APT não encontrar algum pacote:

```bash
apt-cache policy libccid pcscd libpcsclite1 libusb-1.0-0 docker.io docker-compose-v2 containerd runc
```

Opcionalmente, para a mesma revisão HWE, se disponível no APT:

```bash
sudo apt-get install -y linux-image-generic-hwe-24.04=7.0.0-38.38~24.04.4
sudo reboot
```

Depois do reboot, confira `uname -r`. Faça os comandos de implantação no novo
notebook, não no original com coletas ou outros trabalhos em andamento.
Inicie Docker e PC/SC. O socket deve existir antes de criar os containers:

```bash
sudo systemctl enable --now docker
sudo systemctl enable --now pcscd.socket
sudo systemctl start pcscd.service
sudo usermod -aG docker "$USER"
```

Saia da sessão Linux e entre novamente para aplicar o grupo Docker. Esse grupo
permite administrar o host via Docker; dê acesso apenas a usuários responsáveis.
Depois:

```bash
docker version
docker compose version
systemctl status docker pcscd.socket pcscd.service --no-pager
test -S /run/pcscd/pcscd.comm
ls -l /run/pcscd/pcscd.comm
```

O PC/SC usa ativação por socket e `--auto-exit`; o daemon pode parar sem clientes
e iniciar na próxima consulta. Mantenha `pcscd.socket` ativo. Se recriar o socket
no host, recrie os containers consumidores: o bind mount pode apontar ao arquivo
anterior.

## 2. Conectar e validar o token no host

Conecte o token diretamente na USB e execute:

```bash
lsusb
pcsc_scan -c -t 1
dpkg-query -W libccid pcscd libpcsclite1 libusb-1.0-0
grep -n 'StarSign' /etc/libccid_Info.plist
ls -l /usr/lib/pcsc/drivers/ifd-ccid.bundle/Contents/Linux/libccid.so
```

Para o modelo de referência, espere `1059:0017`, StarSign e
`Card state: Card inserted`. `pcsc_scan` não envia PIN. Se falhar aqui, resolva
USB/CCID/PC/SC antes do Docker. Instalar PJeOffice no desktop não corrige essa etapa.

## 3. Obter o código com as alterações Docker

Se as alterações já estiverem publicadas no repositório ao qual você tem acesso:

```bash
git clone https://github.com/RV-TEC-Solutions/automacao-juridica.git
cd automacao-juridica
git status --short
test -f backend-automacao/docker/pjeoffice-pro
```

O repositório pode exigir autenticação. **Este guia não envia alterações locais
para o GitHub.** Um clone antigo pode não conter a instalação do PJeOffice.
Para transportar os arquivos atuais, execute na raiz do projeto original:

```bash
tar \
  --exclude=.git --exclude=.agents --exclude=.codex --exclude=.aws \
  --exclude='.env*' --exclude=.venv --exclude=node_modules --exclude=.next \
  --exclude=brasloger --exclude=backups --exclude='*.sqlite3' \
  --exclude=backend-automacao/respostas_expedientes \
  -czf /tmp/automacao-juridica-codigo.tar.gz .
cp .env.example /tmp/automacao-juridica.env.example
```

Transfira os dois arquivos para `~/Downloads/` do destino por pendrive ou outro
meio autorizado. No destino:

```bash
mkdir -p ~/automacao-juridica
tar -xzf ~/Downloads/automacao-juridica-codigo.tar.gz -C ~/automacao-juridica
cp ~/Downloads/automacao-juridica.env.example ~/automacao-juridica/.env.example
cd ~/automacao-juridica
```

O arquivo inclui `docker/vendor` se presente, mas exclui banco, capturas e `.env`.
Não copie credenciais de outra pessoa. Um hash Git não representa mudanças
não commitadas. Os próximos comandos assumem a raiz do projeto.

## 4. Preparar os instaladores do assinador e driver

```bash
mkdir -p backend-automacao/docker/vendor
curl --fail --location --retry 3 \
  https://pje-office.pje.jus.br/pro/pjeoffice-pro-v2.5.16u-linux_x64.zip \
  -o backend-automacao/docker/vendor/pjeoffice.zip
printf '%s\n' '6087391759c7cba11fb5ef815fe8be91713b46a8607c12eb664a9d9a6882c4c7  backend-automacao/docker/vendor/pjeoffice.zip' | sha256sum -c -
```

Obtenha **SafeSign IC Standard Linux 4.7.0.0-AET.000, Ubuntu 24.04 x86_64** junto
ao fornecedor do token/certificado ou transfira o instalador autorizado usado
na máquina original. Não foi confirmado um URL público do fabricante para esse
arquivo. Coloque o `.deb` em Downloads:

```bash
cp "$HOME/Downloads/SafeSign IC Standard Linux 4.7.0.0-AET.000 ub2404 x86_64.deb" \
  backend-automacao/docker/vendor/safesign.deb
printf '%s\n' 'e8b4011bcd2d819beb709a0676e40181b1fce0dbdc123eb931b2b0a1feedd9a7  backend-automacao/docker/vendor/safesign.deb' | sha256sum -c -
dpkg-deb -f backend-automacao/docker/vendor/safesign.deb Package Version Architecture
```

Espere `safesignidentityclient`, `4.7.0.0-AET.000`, `amd64`. Se os checksums
não coincidirem, não assuma que é o mesmo artefato. Se os instaladores vieram
na cópia do projeto, basta verificá-los, sem repetir os downloads/cópias.
Eles ficam fora do Git. Não instale o `.deb` no host: o Dockerfile o instala
no container. A imagem Debian antiga não atendia à ABI desse SafeSign Ubuntu.

## 5. Configurar banco, credenciais, relógio e IP

```bash
test -f .env || cp .env.example .env
chmod 600 .env
openssl rand -hex 32
nano .env
```

Use a senha gerada para o banco. Não sobrescreva um `.env` já configurado.
Configure também OAB e origem da aplicação:

```dotenv
POSTGRES_DB=pje_automacao
POSTGRES_USER=pje_automacao
POSTGRES_PASSWORD=SUBSTITUA_PELA_SENHA_GERADA
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
DJEN_OAB_NUMBER=5691
DJEN_OAB_STATE=RN
ALLOWED_HOSTS=*
CORS_ALLOW_ALL_ORIGINS=True
CSRF_TRUSTED_ORIGINS=http://localhost:3002,http://127.0.0.1:3002,http://192.168.10.77:3002
```

`192.168.10.77` é o notebook original, não um IP obrigatório. Descubra o IP do
novo servidor pela interface Ethernet/Wi-Fi:

```bash
ip -4 addr show
ip -4 route
```

Use o IP da interface conectada ao escritório, não os endereços das bridges
Docker `172.*`. Substitua o IP no `CSRF_TRUSTED_ORIGINS`. Reserve esse endereço
por DHCP no roteador; cada servidor deve ter seu próprio IP.

Crie o arquivo externo de credenciais:

```bash
install -d -m 700 "$HOME/.config/pje-automacao"
touch "$HOME/.config/pje-automacao/.env"
chmod 600 "$HOME/.config/pje-automacao/.env"
nano "$HOME/.config/pje-automacao/.env"
```

```dotenv
PJE_CERT_PIN=PIN_REAL_DO_TOKEN
PJE_TOTP_SECRET=SEGREDO_BASE32_DO_AUTENTICADOR
```

TOTP é o segredo de configuração do autenticador, não o código temporário de
seis dígitos. Compose monta essa pasta somente para leitura. Para o modo Docker
atual, configure **também** `PJE_CERT_PIN` e `PJE_TOTP_SECRET` com os mesmos valores
no `.env` principal, editando-o com `nano .env`. Foi assim que o teste funcionou:
os dois valores estavam preenchidos no ambiente do container e no arquivo externo.
O Compose declara essas variáveis mesmo quando vazias, e `load_dotenv` não
substitui variáveis existentes vazias; portanto, somente o arquivo externo não
basta nesta configuração. Não publique segredos em Git, logs ou linha de comando.

Confira a presença dos valores no ambiente, sem mostrar seu conteúdo, depois de
subir o backend na etapa 6:

```bash
docker compose exec backend python -c 'import os; print({k: bool(os.environ.get(k)) for k in ("PJE_CERT_PIN", "PJE_TOTP_SECRET")})'
```

Ambos devem indicar `True`. Alterar o `.env` requer recriar os containers
consumidores, não apenas reiniciar o processo.

```bash
sudo timedatectl set-timezone America/Fortaleza
sudo timedatectl set-ntp true
timedatectl status
```

Confirme sincronização do relógio; TOTP depende dela. Se outro serviço NTP
administra o relógio, verifique a sincronização nele. O agendador da aplicação
usa `America/Fortaleza`, mesmo se comandos no container exibirem UTC.

## 6. Construir e iniciar banco/backend

```bash
docker compose config --quiet
docker compose build backend worker
docker compose up -d postgres
docker compose up -d backend
docker compose logs --tail 80 backend
curl --retry 30 --retry-delay 2 --retry-connrefused --fail --silent --show-error \
  http://127.0.0.1:8007/api/auth/csrf/ -o /dev/null
docker compose exec backend python manage.py configurar_app --if-empty
```

Digite usuário, nome e senha do painel. A senha do painel é diferente do PIN A3.
O `curl` espera a API ficar disponível; se terminar com erro, confira os logs
antes de criar a conta ou prosseguir.
O entrypoint aplica migrations automaticamente. Não execute `makemigrations`
para contornar avisos sem revisão. Não inicie `run-local.sh` junto deste modo.
Deixe o worker agendador parado durante a configuração; se já o iniciou:

```bash
docker compose stop worker
```

Para transportar a base existente, use backup/restauração ao final. A migração
SQLite é uma alternativa que exige banco de destino vazio, descrita adiante.

## 7. Autorizar o SSO e executar uma coleta isolada

Crie um worker temporário com os mesmos volumes/imagem, mas sem processar a fila:

```bash
docker compose run -d --no-deps --name pje-worker-setup worker sleep infinity
docker logs --tail 30 pje-worker-setup
docker exec pje-worker-setup pcsc_scan -c -t 1
docker exec pje-worker-setup pkcs11-tool --module /usr/lib/libaetpkss.so.3 --list-slots
```

Espere `Card inserted` e slot SafeSign com token inicializado. Listar slots
não envia PIN. A primeira autorização do PJeOffice fica na tela virtual.
O comando abaixo observa e autoriza **somente o SSO oficial**
`https://sso.cloud.pje.jus.br/auth/realms/pje`, escolhendo “Sempre”. A permissão
é persistida em `pjeoffice_worker_data`; não desativa a solicitação de PIN.
Grave e inicie o observador antes da coleta:

```bash
docker exec -i pje-worker-setup sh -c 'cat > /tmp/autorizar-sso.py' <<'PY'
import os
import time
for item in open('/proc/1/environ', 'rb').read().split(b'\0'):
    if item.startswith(b'DBUS_SESSION_BUS_ADDRESS='):
        os.environ['DBUS_SESSION_BUS_ADDRESS'] = item.split(b'=', 1)[1].decode()
import pyatspi

def walk(node):
    yield node
    for child in node:
        yield from walk(child)

deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    for app in pyatspi.Registry.getDesktop(0):
        if 'pjeoffice' not in (app.name or '').lower():
            continue
        for window in app:
            if window.name != 'Autorização de site':
                continue
            nodes = list(walk(window))
            expected = 'Endereço: https://sso.cloud.pje.jus.br/auth/realms/pje'
            if not any(node.name == expected for node in nodes):
                raise SystemExit('Origem diferente do SSO esperado; nenhuma autorização concedida.')
            buttons = [node for node in nodes if node.getRole() == pyatspi.ROLE_PUSH_BUTTON
                       and node.name == 'Sempre']
            if len(buttons) != 1 or not buttons[0].queryAction().doAction(0):
                raise SystemExit('Não foi possível confirmar a autorização.')
            print('SSO oficial autorizado.', flush=True)
            raise SystemExit(0)
    time.sleep(0.5)
print('Nenhuma autorização nova encontrada; confira o resultado da coleta.', flush=True)
PY
docker exec -d pje-worker-setup sh -c '/usr/bin/python3 /tmp/autorizar-sso.py > /tmp/autorizacao-sso.log 2>&1'
```

Execute TJRN 1º grau como `RERUN`, para não disparar a cadeia inteira de tribunais.
O teste usa PIN/TOTP configurados e grava expedientes no banco:

```bash
docker exec -i pje-worker-setup python manage.py shell <<'PY'
import os
for item in open('/proc/1/environ', 'rb').read().split(b'\0'):
    if item.startswith(b'DBUS_SESSION_BUS_ADDRESS='):
        os.environ['DBUS_SESSION_BUS_ADDRESS'] = item.split(b'=', 1)[1].decode()
from automation.models import AutomationRun, AutomationSource
from automation.queue import enqueue_run
from automation.services.pjeoffice.physical_token import validar_token_fisico
from automation.services.pje.runner import executar_coleta
validar_token_fisico()
source = AutomationSource.objects.get(code='pje-tjrn')
run = enqueue_run(source, AutomationRun.Trigger.RERUN)
print('Coleta de teste:', run.pk, flush=True)
executar_coleta(run)
run.refresh_from_db()
print('Resultado:', run.status, 'Encontrados:', run.expedientes_encontrados,
      'Criados:', run.expedientes_criados, 'Atualizados:', run.expedientes_atualizados)
if run.status != AutomationRun.Status.SUCCESS:
    raise SystemExit(run.mensagem_erro or 'Coleta não terminou com sucesso.')
PY
docker exec pje-worker-setup cat /tmp/autorizacao-sso.log
```

Espere `Resultado: success`, após PIN automático, TOTP e captura das abas.
Se houver erro de PIN incorreto, confira a credencial antes de repetir; o token
pode bloquear após tentativas inválidas. Não é esperado ver janelas no desktop.
Depois do sucesso, encerre o temporário e ligue o worker normal:

```bash
docker stop pje-worker-setup
docker rm pje-worker-setup
docker compose up -d worker
docker compose logs --tail 40 worker
```

Não execute os dois workers simultaneamente no mesmo banco/token. O normal
agenda a coleta diária, por padrão às **06:00**, e processa a fila. Ao iniciar
após o horário pode agendar recuperação do dia e percorrer as fontes habilitadas.
O DJEN usa OAB/UF configuradas, consulta sete dias e independe do token físico.

## 8. Iniciar o frontend no modo já testado

O frontend de referência roda no host com Node `22.23.3` e npm `10.9.9`.
Instale essa distribuição oficial:

```bash
mkdir -p /tmp/node-pje-install
cd /tmp/node-pje-install
curl --fail --location https://nodejs.org/dist/v22.23.3/node-v22.23.3-linux-x64.tar.xz -o node-v22.23.3-linux-x64.tar.xz
curl --fail --location https://nodejs.org/dist/v22.23.3/SHASUMS256.txt -o SHASUMS256.txt
grep ' node-v22.23.3-linux-x64.tar.xz$' SHASUMS256.txt | sha256sum -c -
sudo tar -xJf node-v22.23.3-linux-x64.tar.xz -C /opt
export PATH="/opt/node-v22.23.3-linux-x64/bin:$PATH"
sudo env PATH="/opt/node-v22.23.3-linux-x64/bin:$PATH" npm install --global npm@10.9.9
printf '%s\n' 'export PATH="/opt/node-v22.23.3-linux-x64/bin:$PATH"' >> "$HOME/.profile"
node --version
npm --version
cd "$HOME/automacao-juridica"
npm --prefix frontend ci
```

Se clonou em outra pasta, ajuste o `cd`. Use `npm ci` para respeitar o lockfile.
Edite `frontend/next.config.ts`, colocando o IP do novo notebook em
`allowedDevOrigins`, por exemplo:

```typescript
allowedDevOrigins: ["192.168.10.77"],
```

Use apenas IP/hostname, sem protocolo/porta. Reinicie o Next.js após alterações.
Inicie num terminal que permanecerá aberto:

```bash
BACKEND_URL=http://127.0.0.1:8007 npm --prefix frontend run dev -- --hostname 0.0.0.0 --port 3002
```

### Alternativa: frontend também no Docker

Para dispensar Node local, pare o frontend local com `Ctrl+C` no seu terminal:

```bash
docker compose build frontend
docker compose up -d frontend
docker compose logs --tail 40 frontend
```

O Dockerfile usa `node:20-alpine`, `next build --webpack`, servidor standalone
em `0.0.0.0:3002` e backend interno `http://backend:8007`. Esse modo não usa HMR.
**A coleta #47 não validou o frontend Docker.** A tag não fixa a revisão exata
de Node/Alpine: valide build, login e API antes de adotá-lo. Node `22.23.3`/npm
`10.9.9` acima pertencem ao frontend local, não a essa imagem.

## 9. Acessar pelo IP na rede do escritório

Substitua o IP pelos dados da etapa 5:

```bash
ss -ltnp '( sport = :3002 )'
curl --noproxy '*' -I http://127.0.0.1:3002/
curl --noproxy '*' -I http://192.168.10.77:3002/
```

De outro computador, abra **http://IP_DO_NOTEBOOK:3002** e use a conta criada.
O token permanece no servidor do worker, não no computador cliente.
Os clientes precisam de navegador e acesso à LAN, sem drivers A3 ou Docker.
Se o host usa UFW e o frontend local está bloqueado:

```bash
sudo ufw status
sudo ufw allow from 192.168.10.0/24 to any port 3002 proto tcp
```

Ajuste a sub-rede. Não ative/redefina firewall às cegas durante acesso remoto.
Confira isolamento de Wi-Fi/rede de visitantes e regras entre VLANs.
Portas Docker publicadas podem contornar UFW; controle-as também no firewall/
roteador conforme a [documentação Docker](https://docs.docker.com/engine/install/ubuntu/#firewall-limitations).

| Porta | Acesso/uso |
| --- | --- |
| `3002/tcp` | Frontend na LAN |
| `8007/tcp` | API; Compose publica em todas as interfaces, mas clientes usam o proxy `/api` do frontend |
| `5433/tcp` | Banco somente em `127.0.0.1`; porta interna PostgreSQL `5432` |
| `8800/8801` | PJeOffice somente dentro do worker |

O guia é para HTTP na LAN. Não encaminhe essas portas para a internet.
Se o IP mudar, atualize `CSRF_TRUSTED_ORIGINS` no `.env` e recrie o backend.
No modo desenvolvimento atualize também `allowedDevOrigins` e reinicie Next.js:

```bash
docker compose up -d --force-recreate --no-deps backend
```

## 10. Operação e diagnóstico

Banco, backend e worker usam `restart: unless-stopped`; Docker inicia no boot.
O frontend local precisa ser iniciado novamente após reboot; o frontend Docker
segue a política de reinicialização. Mantenha notebook ligado, rede e token
conectados. Ajuste suspensão/tampa nas configurações de energia do Ubuntu.

```bash
docker compose ps
docker compose logs --since 15m --tail 200 backend worker
docker compose exec worker pcsc_scan -c -t 1
docker compose exec worker pkcs11-tool --module /usr/lib/libaetpkss.so.3 --list-slots
docker compose exec worker sh -c 'tail -n 40 /tmp/pjeoffice-startup.log'
journalctl -u pcscd --since '30 minutes ago' --no-pager
docker compose exec worker python manage.py test automation.tests.PJeOfficeTests --noinput
```

| Falha | Verificação/ação |
| --- | --- |
| Token ausente / `No reader found` | USB, `lsusb`, CCID e `pcsc_scan` no host primeiro |
| Protocolo PC/SC cliente `4:5`, servidor `4:4` | Use combinação PC/SC `2.0.3-1build1`; imagem anterior Debian Trixie/PCSC 2.3 falhou com esse host |
| Detectado no host, ausente no container | Confira montagem/socket; recrie consumidores se o socket foi recriado |
| PJeOffice ausente no AT-SPI | Java, startup log, Java ATK e sessão D-Bus |
| Janela PIN ausente no primeiro uso | Autorização SSO da etapa 7; o volume pode ter sido apagado |
| PIN/TOTP não configurados | Arquivo externo, montagem e precedência das variáveis; não imprima segredos |
| TOTP recusado | Segredo Base32 e sincronização do relógio |
| WebSocket `/_next/hmr` inválido | `allowedDevOrigins` para IP atual e reinício do Next local |
| Login/POST com 403 | Autenticação/CSRF; acessar outro IP não compartilha necessariamente sessão de localhost |
| Porta 3002 ocupada | `ss`; execute somente um frontend nessa porta |

Após recriar o socket PC/SC, fora de uma coleta em andamento:

```bash
docker compose stop worker backend
sudo systemctl restart pcscd.socket
sudo systemctl start pcscd.service
docker compose up -d --force-recreate --no-deps backend worker
```

`docker compose down` preserva volumes. **`docker compose down -v` apaga banco
e configuração do assinador.** `postgres_data` guarda dados,
`pjeoffice_worker_data` guarda configurações/autorizações e
`backend-automacao/respostas_expedientes` recebe capturas/diagnósticos que podem
conter dados processuais. A remoção do volume PJeOffice exige nova autorização.

## Preservar exatamente as imagens validadas

Para evitar mudanças em APT/Python num build futuro, exporte as imagens do
notebook original e os inventários:

```bash
mkdir -p backups/implantacao
docker image inspect automacao-juridica-backend:latest automacao-juridica-worker:latest postgres:18.6 \
  --format '{{json .RepoTags}} {{.Id}}' > backups/implantacao/imagens.txt
docker save -o backups/implantacao/imagens-docker.tar \
  automacao-juridica-backend:latest automacao-juridica-worker:latest postgres:18.6
sha256sum backups/implantacao/imagens-docker.tar > backups/implantacao/imagens-docker.sha256
docker compose exec -T worker pip freeze > backups/implantacao/python-worker.txt
docker compose exec -T worker dpkg-query -W > backups/implantacao/pacotes-worker.txt
dpkg-query -W > backups/implantacao/pacotes-host.txt
```

IDs observados no teste (não são URLs de um registry público):

```text
backend:  sha256:7b8dea623fac8e434c6da7a2d2744d58ebd8d5728d7d046d0c11415ef1a46023
worker:   sha256:8d85c65d3df4c6a1e26c32bd1139df48e8459453b9647df6ce3d2453c71a3ab0
postgres: sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722
```

Transfira as imagens e o código/Compose correspondente. No novo host, com os
arquivos nos mesmos caminhos relativos à raiz do projeto:

```bash
sha256sum -c backups/implantacao/imagens-docker.sha256
docker load -i backups/implantacao/imagens-docker.tar
docker image inspect automacao-juridica-backend:latest automacao-juridica-worker:latest postgres:18.6 \
  --format '{{json .RepoTags}} {{.Id}}'
docker compose up -d --no-build postgres backend
```

Esse caminho substitui o build da etapa 6. Na etapa 7 use
`docker compose run --no-build -d --no-deps --name pje-worker-setup worker sleep infinity`
e inicie o worker definitivo com `docker compose up -d --no-build worker`.
As imagens não contêm banco ou credenciais externas; repita configuração,
autorização e teste no destino. Frontend local continua com Node fixo e `npm ci`.

Para arquivar também os pacotes principais do host enquanto disponíveis no APT:

```bash
mkdir -p backups/implantacao/debs
cd backups/implantacao/debs
apt-get download \
  libccid=1.5.5-1 pcscd=2.0.3-1build1 libpcsclite1=2.0.3-1build1 \
  libusb-1.0-0=2:1.0.27-1 pcsc-tools=1.7.1-1 usbutils=1:017-3build1 \
  docker.io=29.1.3-0ubuntu3~24.04.2 docker-compose-v2=2.40.3+ds1-0ubuntu1~24.04.1 \
  containerd=2.2.1-0ubuntu1~24.04.3 runc=1.3.4-0ubuntu1~24.04.1
sha256sum ./*.deb > SHA256SUMS
```

No destino, nessa pasta, execute `sha256sum -c SHA256SUMS` e
`sudo apt-get install -y ./*.deb`. Isso arquiva pacotes principais, não todo o
sistema/dependências transitivas. APT ainda resolve dependências compatíveis;
não é um kit offline completo.

## Migração alternativa de SQLite e modo local antigo

Para uma base SQLite anterior, prepare PostgreSQL **vazio**, com API/worker e
frontend parados. Não execute configuração inicial nem entrypoint Docker de
backend/worker antes da importação. O script local suporta esse fluxo:

```bash
sudo apt-get install -y python3-venv
python3 -m venv .venv
.venv/bin/pip install -r backend-automacao/requirements.txt 'Django==5.2.18'
docker compose up -d postgres
./run-local.sh import-sqlite
```

O script preserva SQLite e cria backups. Falhas deixam a marca
`.postgres-import-incomplete`; revise antes de repetir, sem apagar banco/backups
para contornar o erro. Depois use os serviços Docker e valide conta/dados.
Não execute `setup` numa base importada. O modo antigo `./run-local.sh` executa
API/worker no host e exige PJeOffice/AT-SPI locais; é diferente do modo deste guia.

## Referências

- [CCID no Ubuntu Noble](https://packages.ubuntu.com/noble/libccid).
- [PC/SC no Ubuntu Noble](https://packages.ubuntu.com/noble/pcscd).
- [Driver CCID e suporte USB](https://ccid.apdu.fr/).
- [Guia oficial PJeOffice Pro](https://pjeoffice.trf3.jus.br/pjeoffice-pro/docs/userguide.html).
- [Distribuição Node.js 22.23.3](https://nodejs.org/dist/v22.23.3/).
- [Next.js allowedDevOrigins](https://nextjs.org/docs/app/api-reference/config/next-config-js/allowedDevOrigins).
- [Detalhes da imagem do projeto](backend-automacao/docker/README.md).

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

## Backup e restauração do PostgreSQL

Pare backend e worker (`docker compose stop backend worker`) antes da restauração. Crie um backup manual em formato
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
docker compose exec backend python manage.py test automation expedientes --noinput
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Os testes Django usam um banco de teste PostgreSQL separado.
