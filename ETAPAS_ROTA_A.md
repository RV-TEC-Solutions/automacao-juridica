# Rota A: Emulação do PJeOffice via Mock Server Local e Certificado A1

Esta branch (`feature/rota-a-mock-pjeoffice`) implementa a **Ideia A (Rota Híbrida)**, projetada para **destravar imediatamente a automação no Docker** eliminando os pontos de falha do Token físico A3 e do PJeOffice Java desktop, sem necessidade de reescrever de imediato todo o código de extração e navegação do Playwright.

---

## 1. Visão Geral da Arquitetura

```
+---------------------------------------------------------------------------------------+
|                                    CONTAINER DOCKER                                   |
|                                                                                       |
|   [Certificado A1 (.pfx)]                                                             |
|           │                                                                           |
|           ▼ (Em memória RAM)                                                          |
|   [A1CryptoEngine (Python)]                                                           |
|           │                                                                           |
|           ▼                                                                           |
|   [PJeOfficeMockServer (127.0.0.1:8800)] ◄───(HTTP/CORS)───► [Chromium (Playwright)]  |
+-----------------------------------------------------------------------│---------------+
                                                                        │ HTTPS
                                                                        ▼
                                                                  [TRIBUNAL (PJe)]
```

### O que foi eliminado:
- ❌ **Token físico USB A3** e o daemon `pcscd` compartilhado via socket.
- ❌ **Aplicação desktop Java (PJeOffice Pro)** com interface gráfica Swing.
- ❌ **Automação de acessibilidade AT-SPI2** (`python3-pyatspi`) e busca de janelas com digitação de PIN.
- ❌ **Falhas de foco de janela** e timeout de renderização de telas virtuais no Xvfb.

### O que assumiu o controle:
-  **`A1CryptoEngine` (`automation/services/pjeoffice/crypto.py`)**: Carrega a chave privada e a cadeia de certificados do A1 diretamente na memória RAM (sem salvar em disco). Realiza a assinatura digital PKCS#7 Detached (SHA-256) em menos de 5ms.
-  **`PJeOfficeMockServer` (`automation/services/pjeoffice/mock_server.py`)**: Servidor HTTP em Python escutando na porta padrão 8800 com suporte a CORS e Private Network Access. Quando o PJe no navegador solicita a assinatura de um desafio (nonce), o mock assina instantaneamente na memória e devolve a resposta no protocolo esperado pelo tribunal.
-  **`browser.py` e `physical_token.py` atualizados**: Detectam a presença do A1, iniciam o mock automaticamente, dispensam o preenchimento de PIN e permitem rodar o Playwright em modo `headless=True` real.

---

## 2. Etapas de Implementação

###  Etapa 1: Motor Criptográfico A1 em Memória
- [x] Criação de `A1CryptoEngine` com suporte ao padrão ICP-Brasil (PKCS#12 / .pfx).
- [x] Extração segura de metadados: CPF, Nome do Advogado, OAB, número serial e validade do certificado.
- [x] Geração de assinatura digital PKCS#7 / CMS Detached com SHA-256 em Base64.
- [x] Carregamento flexível: via variável Base64 (`PJE_CERT_A1_BASE64`) ou arquivo local (`PJE_CERT_A1_PATH`).

###  Etapa 2: Servidor Mock do PJeOffice (Porta 8800)
- [x] Implementação de `PJeOfficeMockServer` escutando em `127.0.0.1:8800`.
- [x] Tratamento de preflight `OPTIONS` com headers `Access-Control-Allow-Private-Network: true` e `Access-Control-Allow-Origin: *`.
- [x] Rotas de status e liveness (`/pjeOffice/`, `/pjeOffice/versao`, `/health`).
- [x] Rota de assinatura (`POST /pjeOffice/`) com envelope de resposta contendo assinatura, certificado e cadeia.
- [x] Suporte a execução em thread de background ou processo autônomo via CLI.

###  Etapa 3: Integração com o Fluxo do Navegador
- [x] Atualização de `browser.py`: `autenticar_pje()` verifica se o modo A1 está ativo e ignora o robô AT-SPI, pois a assinatura é resolvida instantaneamente pelo mock.
- [x] Concessão de permissões de rede privada (`local-network-access`) para o Chromium se comunicar com a porta 8800.
- [x] Atualização de `physical_token.py` para validar o certificado A1 sem tentar invocar `pcsc_scan`.
- [x] Suporte a `PJE_BROWSER_HEADLESS=true`.

###  Etapa 4: Ambiente e Containers Docker
- [x] Adição da biblioteca `cryptography` ao `requirements.txt`.
- [x] Atualização do `entrypoint.sh` para iniciar o `PJeOfficeMockServer` quando as variáveis do A1 estiverem presentes.
- [x] Atualização do `.env.example` com os parâmetros do A1.

###  Etapa 5: Validação e Testes Automatizados
- [x] Testes unitários do motor criptográfico (`TestA1CryptoEngine`).
- [x] Testes de requisição HTTP e CORS do mock server (`TestPJeOfficeMockServer`).
- [x] Testes de validação de token físico unificado (`TestValidarTokenFisicoA1`).

---

## 3. Como Configurar e Utilizar

1. **Obtenha o certificado e-CPF A1 do advogado** (arquivo `.pfx` ou `.p12`).
2. **Defina as variáveis no seu `.env`** (ou `~/.config/pje-automacao/.env`):
   ```bash
   # Opção A: Passando o arquivo diretamente
   PJE_CERT_A1_PATH=/caminho/do/seu/certificado.pfx
   PJE_CERT_A1_PASSWORD=sua_senha_do_certificado

   # OU Opção B: Passando em Base64 (ideal para Docker / Cloud Secrets)
   # Gerar com: cat certificado.pfx | base64 -w 0
   PJE_CERT_A1_BASE64=MIIK...conteudo_em_base64...
   PJE_CERT_A1_PASSWORD=sua_senha_do_certificado

   # Configurações do modo
   PJE_AUTH_MODE=a1
   PJE_BROWSER_HEADLESS=true
   PJE_TOTP_SECRET=seu_segredo_2fa
   ```

3. **Executar os testes:**
   ```bash
   .venv/bin/python backend-automacao/manage.py test automation.tests_rota_a
   ```

4. **Executar a automação:**
   ```bash
   ./run-local.sh
   # ou no docker:
   docker compose up -d --build
   ```
