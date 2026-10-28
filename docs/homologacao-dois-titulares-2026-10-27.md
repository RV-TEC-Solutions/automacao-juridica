# Homologação de dois titulares — 27/10/2026

## Configuração utilizada

O operador confirmou que o código gerado com a chave decodificada da
exportação do Google Authenticator coincidiu com o aplicativo. A URI de
exportação, a chave e os códigos não foram enviados à conversa.

Antes do login real, a API e o worker ainda tinham uma montagem anterior
do `.env`. Sem coleta ativa, ambos foram recriados, sem rebuild. A comparação
dos arquivos confirmou que os dois serviços passaram a ler o `.env` atual
da raiz. O arquivo mantém permissão `600`.

## TJRN 1º grau

As execuções foram isoladas (`trigger=rerun`) e sequenciais, sem encadear
outras fontes. O worker não foi reiniciado entre as três execuções.

| Execução | Titular | Resultado | Expedientes encontrados | Criados | Atualizados |
| --- | --- | --- | --- | --- | --- |
| 375 | Cristiano | Sucesso | 117 | 112 | 5 |
| 376 | Murilo | Sucesso | 77 | 0 | 0 |
| 377 | Cristiano | Login validado; falha de captura na aba 2/21 | 0 importados | 0 | 0 |

O nome autenticado foi conferido no cabeçalho do portal antes da coleta em
cada execução. Os registros do worker confirmam Cristiano às 10h10min59s,
Murilo às 10h14min25s e Cristiano novamente às 10h18min35s, no fuso
America/Fortaleza. Assim, a autenticação foi validada nos dois sentidos da
alternância, Cristiano → Murilo → Cristiano.

Nenhuma das três execuções registrou falha de credencial. O resultado atual
supera a pendência de validação TOTP documentada em 26/10. Não foi isolada
retrospectivamente a causa exata das rejeições anteriores.

Na execução 377, depois de confirmar a identidade de Cristiano, o PJe não
concluiu o clique ou a resposta AJAX da segunda aba dentro de 30 segundos.
Uma captura parcial foi salva para diagnóstico, sem importação dos resultados
da tentativa. Houve eventos JavaScript/HTTP associados à página, mas a causa
do timeout não foi isolada. Essa falha não é uma rejeição de TOTP.

As coletas bem-sucedidas anteriores foram preservadas. A conferência dos
vínculos ativos por titular encontrou 117 expedientes de Cristiano e 77 de
Murilo, incluindo cinco compartilhados entre ambos.

## Estados fornecidos ao frontend

O payload de titulares usado pela API foi conferido após as três execuções:

- Dr. Murilo: `success`, última fonte concluída às 10h17min02s.
- Dr. Cristiano: `failed`, por falha na última fonte, mantendo a última coleta
  bem-sucedida às 10h13min14s. Seu estado não é `blocked`.

Os horários acima estão em America/Fortaleza. Não restou coleta pendente
ou em execução ao final da conferência.

## Limites desta homologação

O login real foi homologado somente no TJRN 1º grau. Isso não comprova o
login de Cristiano em todas as demais fontes. O DJEN não foi incluído nos
testes nem recebeu nova configuração.

Não foram executados builds ou suítes pesadas. O worker permaneceu com os
limites existentes de 512 MiB de RAM, 1536 MiB somando RAM e swap e uma CPU;
não foi necessário aumentar esses limites. A máquina estava com a swap
cheia, por isso todas as coletas foram executadas uma de cada vez.
