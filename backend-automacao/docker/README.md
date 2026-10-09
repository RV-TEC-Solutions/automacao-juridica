# PJeOffice no worker

A imagem usa Ubuntu 24.04 para compatibilidade com o driver SafeSign e PC/SC
2.0.3 do host. O socket `/run/pcscd/pcscd.comm` continua compartilhado; o serviço
PC/SC do host controla o token USB. Não é necessário modo privilegiado.

Antes do build, coloque os instaladores em `docker/vendor/` (ignorado pelo git):

- `pjeoffice.zip`: PJeOffice Pro 2.5.16u Linux x64, disponível em
  https://pje-office.pje.jus.br/pro/pjeoffice-pro-v2.5.16u-linux_x64.zip
  (SHA-256 validado pelo Dockerfile).
- `safesign.deb`: SafeSign IC Standard Linux 4.7.0.0 para Ubuntu 24.04 x86_64,
  fornecido pelo fabricante do token. Nesta máquina o instalador está em Downloads.

Execute `docker compose build backend worker` e
`docker compose up -d --no-deps backend worker` na raiz do projeto.

Somente o worker inicia o PJeOffice (`PJE_OFFICE_ENABLED=true`). O Java do
distribuidor recebe a ponte Java ATK para a automação do PIN via AT-SPI.
A configuração de dispositivos e autorizações fica no volume
`pjeoffice_worker_data`; o PIN continua sendo recebido por variável de ambiente.
Não publique as portas do PJeOffice: ele atende ao navegador dentro do worker.

No primeiro uso, o PJeOffice solicita autorização do site oficial
`https://sso.cloud.pje.jus.br/auth/realms/pje`. Essa autorização foi configurada
neste ambiente e fica salva no volume. Se o volume for apagado, será necessário
autorizar novamente pela janela do assinador na tela virtual antes do teste de
coleta; a automação do PIN não confirma autorizações de sites.

Validação: `docker compose exec worker pcsc_scan -c -t 1` deve mostrar
`Card state: Card inserted`. Isso confirma presença; a coleta deve também
confirmar a leitura do certificado, autenticação e preenchimento do PIN.
