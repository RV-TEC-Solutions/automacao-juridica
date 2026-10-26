# Ausência de janela do PIN — 26/10/2026

Os erros informados para os dois graus do TJRN indicam que a página iniciou
uma requisição ao assinador, mas o helper não localizou a janela do PIN em
30 segundos. Iniciar uma requisição não comprova que o assinador a recebeu.
O 404 de `custom-login-info` não comprova a causa dessa falha.

## Estado observado no worker

- O Java original, PID 21, estava no estado `Z` (zombie), já encerrado.
- A sessão AT-SPI consultada estava sem aplicações.
- Não havia coleta em execução no banco durante a recuperação.
- Foi iniciado somente o PJeOffice já instalado, com o ambiente da sessão
  original do worker. Não houve rebuild, reinício do worker ou envio do PIN.
- Após a recuperação, o novo Java estava ativo, a porta local 8800 aceitava
  conexões e o AT-SPI expunha a aplicação `PJeOffice Pro - 2.5.16u` e sua janela.

Esse estado explica a indisponibilidade do assinador no momento da inspeção.
Não foi determinada a causa do encerramento do Java, nem demonstrado que já
estava encerrado no instante de cada erro originalmente relatado.

## Ajustes no helper

O helper reconhece o nome do PJeOffice sem fixar uma versão e aceita os papéis
AT-SPI de diálogo, frame e janela, mantendo o título exato `Informe a senha`, a
exigência de campo de senha editável e a rejeição de múltiplas correspondências.
Na ausência do PIN, lista as janelas visíveis do assinador, permitindo identificar
etapas anteriores pendentes. Não confirma autorizações de site nem escolhe
certificados automaticamente.

O modo `--diagnostico` consulta a janela e o campo sem ler seu conteúdo e sem
enviar o PIN. Deve ser executado na mesma sessão D-Bus do assinador; um
`docker compose exec` isolado pode não herdar essa sessão.

Após a recuperação inicial, as imagens de backend, worker e frontend foram
reconstruídas e os contêineres substituídos. As migrações foram aplicadas e a
presença do assinador na porta 8800 e no AT-SPI foi confirmada novamente no
worker atualizado. Os testes dos fluxos alterados também passaram dentro da
nova imagem. Nenhuma autenticação real ou coleta foi executada nessa validação
para confirmar o fluxo completo.
