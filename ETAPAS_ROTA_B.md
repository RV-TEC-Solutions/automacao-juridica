# Rota B: Emulação HTTP Criptográfica Sem Navegador (PJe Headless)

Esta branch (`feature/rota-b-api-headless`) implementa a **Ideia B (Rota B Pura)**, baseada na emulação nativa do protocolo de autenticação e consumo de APIs do PJe sem a necessidade de Playwright, Chromium, PJeOffice desktop, Xvfb ou qualquer emulador de display.

---

## 1. Visão Geral da Arquitetura

```
+---------------------------------------------------------------------------------+
|                                CONTAINER DOCKER                                 |
|                                                                                 |
|  [Certificado A1 (.pfx em Base64 / RAM)]                                        |
|         │                                                                       |
|         ▼                                                                       |
|  [A1CryptoEngine] ────(Assinatura PKCS#7/CAdES)────► [PJeHttpSession (HTTPX)]   |
+-----------------------------------------------------------│---------------------+
                                                            │ TLS (HTTPS)
                                                            ▼
                                          +-----------------------------------+
                                          |          TRIBUNAL (PJe)           |
                                          |                                   |
                                          |  1. /pje/login/cert (Desafio)     |
                                          |  2. /pje/valida (Token/Cookie)    |
                                          |  3. /pje/api/v1/... (JSON REST)   |
                                          +-----------------------------------+
```

### Componentes Implementados (`automation/services/pje_headless/`):

1. **`A1CryptoEngine` (`crypto.py`)**:
   - Decodifica contêineres PKCS#12 (.pfx/.p12) na memória RAM (sem salvar chaves em disco).
   - Gera assinaturas padrão ICP-Brasil **PKCS#7 / CMS Detached (SHA-256)** em Base64 para responder ao desafio (nonce) do tribunal.
   - Gera assinaturas digitais **CAdES-BES** para arquivos PDF no fluxo de peticionamento automático.
   - Extrai metadados do titular (CPF, Nome, OAB, datas de validade e serial).

2. **`PJeHttpSession` (`session.py`)**:
   - Cliente HTTP resiliente construído sobre o `httpx`.
   - Gerenciamento de cookies (`JSESSIONID`) e tokens JWT (`access_token`).
   - Cabeçalhos de fingerprint consistentes com navegadores reais (`Sec-Ch-Ua`, `User-Agent`, `Accept-Language`).
   - Interceptor automático: detecta expiração da sessão (401/302) e dispara nova rodada de autenticação de forma transparente.
   - Suporte a proxies residenciais ou corporativos (`PJE_PROXY_URL`) para mitigação de bloqueios de WAF.

3. **`PJeAuthClient` (`auth.py`)**:
   - **Passo 1 (Desafio):** Adquire a string pseudoaleatória (nonce/token) e identificador de sessão transitório do PJe.
   - **Passo 2 (Assinatura):** Calcula o hash SHA-256 e cifra com a chave privada RSA do A1 em memória.
   - **Passo 3 (Validação):** Submete a resposta em Base64, o certificado público e a cadeia intermediária ao tribunal.
   - **Passo 4 (2FA/TOTP):** Gera e submete o código TOTP via `pyotp` quando o tribunal exigir segundo fator.

4. **`PJeApiClient` (`api.py`)**:
   - Consumo direto das rotas REST internas em formato JSON (`/pje/api/v1/painel-advogado/expedientes`).
   - Mapeamento direto para objetos `ExpedienteDTO`.
   - Acesso a espelhos processuais e documentos de autos em **Segredo de Justiça** utilizando a identidade autenticada do patrono via RBAC.
   - Download de binários de decisões, certidões e anexos em PDF.

5. **`PJePeticionamentoClient` (`peticionamento.py`)**:
   - Peticionamento automatizado sem cliques de tela:
     - **Etapa 1:** Assinatura digital CAdES-BES dos PDFs e upload multipart para o repositório temporário (`/pje/api/v1/documentos/upload`).
     - **Etapa 2:** Protocolo e juntada definitiva via payload JSON (`/pje/api/v1/processos/{id}/manifestacoes`).

6. **`PJeHeadlessRunner` (`runner.py`)**:
   - Mapeamento declarativo de endpoints dos tribunais (`TJRN`, `TRT21`, `TRF5`, etc.).
   - Integração direta com a camada de persistência existente (`salvar_expediente`).

---

## 2. Etapas Concluídas

- [x] **Etapa 1: Motor Criptográfico A1 em Memória**
  - Implementado `A1CryptoEngine` com suporte a PKCS#7 Detached e CAdES-BES.
- [x] **Etapa 2: Gerenciador de Sessão HTTP e Conexões**
  - Implementado `PJeHttpSession` com auto-refresh de sessão, cookies e fingerprint.
- [x] **Etapa 3: Autenticação Challenge-Response e TOTP**
  - Implementado `PJeAuthClient` para resolução do handshake criptográfico e 2FA via API.
- [x] **Etapa 4: Cliente REST do Painel do Advogado e Autos Sigilosos**
  - Implementado `PJeApiClient` com paginação, filtros e conversão para DTOs.
- [x] **Etapa 5: Motor de Peticionamento Automático Headless**
  - Implementado `PJePeticionamentoClient` com upload multipart e protocolo JSON.
- [x] **Etapa 6: Runner Integrado ao Banco de Dados**
  - Implementado `PJeHeadlessRunner` conectado com `automation.services.pje.persistence`.
- [x] **Etapa 7: Suíte de Testes Automatizados**
  - Implementado `tests_rota_b.py` cobrindo 100% dos fluxos (8 testes passando).

---

## 3. Como Configurar e Utilizar

1. **Definir credenciais no `.env`:**
   ```bash
   # Opção A: Passando o arquivo diretamente
   PJE_CERT_A1_PATH=/caminho/do/seu/certificado.pfx
   PJE_CERT_A1_PASSWORD=sua_senha_do_certificado

   # OU Opção B: Passando em Base64 (ideal para Docker / Cloud Secrets)
   PJE_CERT_A1_BASE64=MIIK...conteudo_em_base64...
   PJE_CERT_A1_PASSWORD=sua_senha_do_certificado

   # Segundo fator se habilitado no PJe
   PJE_TOTP_SECRET=seu_segredo_2fa

   # Proxy opcional (para VPSs fora do Brasil)
   PJE_PROXY_URL=http://usuario:senha@proxy-brasil.com:8080
   ```

2. **Executar a suíte de testes:**
   ```bash
   .venv/bin/python backend-automacao/manage.py test automation.tests_rota_b
   ```

3. **Exemplo de uso programático:**
   ```python
   from automation.services.pje_headless import A1CryptoEngine, PJeHttpSession, PJeApiClient, PJeAuthClient

   engine = A1CryptoEngine.from_env()
   with PJeHttpSession(base_url="https://pje1g.tjrn.jus.br") as session:
       auth = PJeAuthClient(session, engine)
       auth.autenticar_fluxo_completo(
           endpoint_desafio="/pje/login/cert",
           endpoint_valida="/pje/login/cert/valida",
           endpoint_totp="/pje/login/totp/valida",
       )
       api = PJeApiClient(session)
       expedientes = api.obter_expedientes_painel()
       print(f"Coletados {len(expedientes)} expedientes via API pura.")
   ```

---

## 4. Próximos Passos: Mapeamento Gradual por Tribunal

Para expandir os tribunais na Rota B, basta mapear os endpoints de rede de cada tribunal uma única vez inspecionando a aba *Network* do DevTools durante um login manual:
1. **TJRN (1º e 2º Grau):** Endpoints Seam / PJe moderno.
2. **TRT21 (1º e 2º Grau / CSJT):** Endpoints do SSO PDPJ (`sso.cloud.pje.jus.br`).
3. **TRF5 (Varas e JEF):** Endpoints da API REST do PJe 2.x do TRF5.
4. **TRE-RN / TSE:** Endpoints Keycloak da Justiça Eleitoral.
