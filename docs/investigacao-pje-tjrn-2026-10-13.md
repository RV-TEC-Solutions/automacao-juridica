# Falhas de autenticação PJe TJRN — 13/10/2026

## Evidência e causa

Os logs fornecidos para `pje-tjrn` e `pje2g-tjrn` mostram a mesma exceção: `Locator.wait_for` rejeitou `text=CERTIFICADO DIGITAL` porque encontrou 12 elementos. Entre eles está o controle de autenticação `<input type="button" id="kc-pje-office" value="CERTIFICADO DIGITAL">`, além de links e textos informativos.

Os dois perfis estavam sem `certificate_button_selector`. O fluxo compartilhado de `autenticar_pje` e `clicar_certificado` usava `get_by_text("CERTIFICADO DIGITAL", exact=True)`. O log mostra que essa seleção não foi única na página observada. A preparação falhou antes do clique e, nessa tentativa, antes de iniciar a chamada ao PJeOffice, preencher o PIN ou validar o TOTP.

Os erros 404 e recursos interrompidos de `consulta-processual-link` e `custom-login-info` são evidências adicionais. Não demonstram a causa da violação de unicidade nem permitem concluir que impedirão a autenticação após corrigir o seletor. Seu impacto posterior permanece sem validação.

## Correção

Os dois perfis TJRN em `backend-automacao/automation/services/pje/sources.py` agora declaram `certificate_button_selector="#kc-pje-office"`, seguindo o ID presente nos logs. O fluxo existente usa essa configuração tanto na preparação quanto no clique, mantendo a verificação de unicidade.

## Validação

- Os 13 testes de `automation.test_pje_reliability` passaram. O novo teste cobre preparação e clique dos dois graus pelo mesmo seletor.
- Chromium local com HTML simulado reproduziu 12 correspondências para `text=CERTIFICADO DIGITAL`. A preparação e o clique com `#kc-pje-office` funcionaram para ambos os perfis, com um clique por perfil.
- Nenhuma autenticação real ou coleta nos tribunais foi executada. A validação completa depende de uma nova execução no ambiente com certificado, PJeOffice e TOTP.

As alterações anteriores existentes no workspace foram preservadas.
