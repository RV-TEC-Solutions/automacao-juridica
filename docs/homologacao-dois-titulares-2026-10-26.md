# Implantação e homologação — 26/10/2026

> Atualização de 27/10/2026: a execução 375 de Cristiano no TJRN 1º grau
> concluiu com sucesso, identidade conferida e 117 expedientes encontrados.
> A pendência TOTP descrita abaixo registra o estado de 26/10; ela não
> representa o resultado desse novo teste. Ver a
> [homologação de 27/10](homologacao-dois-titulares-2026-10-27.md).

## Estado atual

A configuração e o frontend para dois titulares foram implantados. Backend,
frontend, PostgreSQL e worker estão em execução. O DJEN permanece com a
configuração anterior; nenhuma consulta para uma nova OAB foi adicionada.

A autenticação completa de Cristiano e a alternância completa entre os dois
titulares **ainda dependem de esclarecer a rejeição na etapa TOTP**. O segredo
não foi comprovadamente identificado como a causa. Por orientação
posterior do responsável, a origem das credenciais foi migrada para o `.env`
da raiz do projeto.

## Credenciais

- Origem única atual: `.env` da raiz do projeto, com permissão `600` e ignorado
  pelo Git. Os valores foram preservados na mudança de origem.
- O arquivo é montado somente para leitura na API e no worker; não é incluído
  nas imagens nem encaminhado ao frontend. O arquivo externo antigo deixou
  de conter as credenciais PJe e não é mais montado nos serviços.
- `PJE_COLLECTORS=murilo,cristiano` continua habilitado.
- Após editar o `.env`, recriar API e worker fora de uma coleta em andamento:
  `docker compose up -d --force-recreate --no-deps backend worker`.
  Isso garante a nova montagem mesmo com salvamento por substituição de
  arquivo. Não é necessário rebuild para corrigir credenciais.
- As credenciais de Cristiano nunca usam os valores de Murilo como alternativa.

Na validação da migração para a raiz, os hashes dos arquivos montados na API
e no worker corresponderam ao `.env` do projeto, ambos com montagem somente
para leitura. Nenhum PIN/TOTP ficou declarado no ambiente de criação dos
contêineres. O arquivo anterior ficou sem chaves PJe.

Os 172 testes de backend passaram novamente com essa configuração; build,
lint, os dois testes unitários pertinentes e os dois cenários E2E de
configurações/titulares também passaram. Os serviços foram recriados e as
credenciais dos dois titulares puderam ser lidas da raiz. Não foi feita
nova tentativa de autenticação de Cristiano, pois seu segredo não foi
alterado nesta migração.

## Verificações antes de autenticar

Ambos os tokens foram reconhecidos pelo módulo e pela série esperados, sem
login PKCS#11 ou envio de PIN nessa pré-verificação. Os dois conjuntos de
credenciais estavam preenchidos; os segredos TOTP tinham formato válido. O
relógio do notebook estava sincronizado por NTP.

Formato válido de um segredo TOTP não comprova associação à conta correta.

## Execuções reais, somente TJRN 1º grau

| Execução | Titular | Resultado | Evidência |
| --- | --- | --- | --- |
| 358 | Cristiano | Falha de credencial | O fluxo chegou ao TOTP e o portal exibiu `Código inválido`. `credential_failure=true`; nenhum expediente foi importado por essa execução. |
| 359 | Murilo | Sucesso após trocar o token | Identidade conferida no cabeçalho autenticado; 78 expedientes encontrados. Concluída às 18h23, no fuso America/Fortaleza. |
| 360 | Cristiano | Nova falha na validação TOTP | Uma única nova tentativa, solicitada pelo operador, usando o `.env` raiz atual. O fluxo voltou a registrar `Código inválido`; nenhum expediente foi importado. |

As execuções usaram `trigger=rerun`, sem encadear outras fontes. As execuções
358 e 359 ocorreram antes da migração da origem para o `.env` raiz; a execução
360 ocorreu depois, por solicitação expressa do operador. A causa da rejeição
TOTP continua sem confirmação.

O mesmo fluxo e relógio funcionaram para Murilo. A pendência foi apresentada
ao operador para conferir e, se necessário, corrigir `PJE_CRISTIANO_TOTP_SECRET` no `.env`
raiz, usando o segredo de configuração da conta correta, não o código
temporário de seis dígitos.

Na revisão da evidência salva da execução 358, a captura de tela e o HTML
confirmaram a mensagem visível `Código inválido`, no elemento
`input-error-otp-code`. A etapa registrada foi posterior ao retorno da função
que gera o OTP, preenche o campo e aciona Validar. Não foram gravados o OTP
nem o corpo da requisição enviada. Portanto, a evidência confirma a falha de
validação apresentada pelo portal e a conclusão dessas operações no navegador,
mas não identifica isoladamente a causa nem os dígitos recebidos pelo servidor.

## Interface e tratamento de falhas

- Dashboard e configurações mostram Dr. Murilo e Dr. Cristiano separadamente.
- A API real de configurações e o dashboard responderam HTTP 200 com ambos
  os titulares. Murilo aparece com a última fonte concluída; Cristiano,
  com credencial suspensa e sem fonte concluída.
- O histórico mostra o titular da execução e a navegação para falhas preserva
  a identificação do advogado.
- Rejeição explícita de PIN, PIN bloqueado, TOTP rejeitado, ausência de
  credenciais ou divergência de identidade suspendem as próximas fontes
  daquele titular no ciclo. Erros de fonte continuam permitindo a próxima.
- O envio do PIN pelo helper tem no máximo uma confirmação por invocação.
  Nenhum PIN foi invalidado deliberadamente para testar o token; a rejeição
  é coberta por testes simulados.

## Validação de software

- Build de produção do frontend concluído.
- 172 testes de backend passaram dentro da imagem Docker atualizada, em banco
  PostgreSQL temporário exclusivo, removido ao final.
- Lint do frontend e 47 testes unitários passaram.
- Os 16 cenários E2E desktop/mobile foram validados: 14 passaram na execução
  inicial; os dois de fluxo principal passaram após corrigir seus dados
  simulados de coleta ainda não iniciada e do endpoint de clientes.
- A migração `0018_automationrun_credential_failure` foi aplicada.

## Memória

Builds e testes foram executados em sequência. O frontend foi compilado com
512 MiB de RAM, 1536 MiB somando RAM e swap, uma CPU e heap Node de 640 MiB.
Os testes de navegador usaram a imagem de produção e apenas um worker.

O worker de coleta ficou permanentemente limitado no Compose a 512 MiB de RAM,
1536 MiB somando RAM e swap e uma CPU. Os limites efetivos foram conferidos
no contêiner. Na conferência da implantação inicial havia aproximadamente
881 MiB de memória disponível no notebook e nenhuma coleta ativa.

## Próxima etapa

Depois de conferir a configuração e a geração/envio do TOTP de Cristiano,
reexecutar somente o TJRN 1º
grau para esse titular, confirmar sua identidade e a persistência, e finalizar
a alternância entre os dois. As demais fontes não foram homologadas com login
real de Cristiano nesta etapa.
