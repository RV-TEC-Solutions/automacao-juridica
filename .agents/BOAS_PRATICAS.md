# Guia de Boas Práticas — Painel de Expedientes & Automação Jurídica

Este documento reúne os padrões de engenharia, arquitetura, segurança e design para o desenvolvimento contínuo da plataforma **Painel de Expedientes** (PJe/TJRN) da RYV-TEC.

---

## 1. 🛡️ Segurança & Gestão de Credenciais (Regra de Ouro)

1. **Credenciais Fora do Repositório**:
   - `PJE_CERT_PIN` e `PJE_TOTP_SECRET` residem obrigatoriamente no arquivo local `~/.config/pje-automacao/.env`.
   - Permissões estritas: `chmod 600 ~/.config/pje-automacao/.env`.
   - **É terminantemente proibido**:
     - Hardcodear senhas, tokens ou certificados em qualquer arquivo do projeto;
     - Retornar PINs ou segredos em endpoints da API;
     - Registrar credenciais em logs do sistema ou em mensagens de erro.
2. **Autenticação de Usuários**:
   - Autenticação via sessões Django protegidas por CSRF (`/api/auth/csrf/`, `/api/auth/login/`).
   - Senhas criptografadas com PBKDF2/Argon2.

---

## 2. 🎨 Padrões de Frontend (Next.js 16, Tailwind v4, Padrão Brasloger)

A interface deve seguir a mesma sofisticação executiva e minimalismo corporativo do projeto **Brasloger** (estética Linear, Vercel e Flexport):

1. **Zero Aspecto Amador (*Anti-Slop*)**:
   - Elementos com bordas sutis (`rule`), fundos monocromáticos (`zinc-950`/`zinc-900` no tema escuro e `zinc-50`/`white` no tema claro).
   - Tipografia de precisão: `Plus Jakarta Sans` para textos gerais e `JetBrains Mono` com `tabular-nums` para números de processo CNJ, identificadores e prazos.
2. **Hierarquia Visual para Prazos e Expedientes**:
   - **Prazos Fatais Críticos** (< 24h ou vencidos): Badges de alto contraste em carmim/rubi (`danger`).
   - **Prazos em Alerta** (24h a 72h): Badges âmbar translúcidos (`caution`).
   - **Expedientes Resolvidos**: Verde esmeralda refinado (`positive`).
   - **Pendente de Ciência**: Azul institucional suave (`brand` / `info`).
3. **Ergonomia e Densidade**:
   - Acompanhamento em lista e tabela de alta densidade sem poluição visual.
   - Detalhamento de teor via gaveta lateral fluida (`ExpedienteDrawer`), mantendo o advogado no fluxo da lista.
   - Tratamento obrigatório de estados: Skeleton Loaders durante loading, Empty States elegantes e tratamento amigável de erro.
4. **Validação Obrigatória de Frontend**:
   ```bash
   npm --prefix frontend run lint
   npm --prefix frontend run test      # Vitest
   npm --prefix frontend run build     # Build de produção Next.js
   npm --prefix frontend run test:e2e  # Playwright E2E
   ```

---

## 3. ⚙️ Padrões de Backend (Django 5/6, Django REST Framework)

1. **Transações Atômicas**:
   - Toda rotina de persistência de lotes de expedientes coletados deve ser envelopada em `transaction.atomic()`, garantindo que falhas de rede ou timeout não deixem o banco em estado inconsistente.
2. **Idempotência de Ingestão**:
   - O par `(source, identificador_pje)` possui restrição única (`unique_expediente_per_source`).
   - Se o expediente já existe, atualize apenas campos mutáveis e registre o diff no `ExpedienteEvent`.
3. **Auditoria de Eventos (`ExpedienteEvent`)**:
   - Toda alteração de estado (`new`, `updated`, `resolved`) gera um evento vinculado à execução (`AutomationRun`).
   - O campo `changes` deve conter apenas as chaves modificadas (ex: `{"prazo_fatal": {"old": null, "new": "2026-10-01T23:59:59"}}`).
4. **Prevenção de N+1 Queries**:
   - Sempre utilize `select_related("processo", "source")` e `prefetch_related("events")` nas consultas do DRF.
5. **Precisão de Fuso Horário**:
   - Fuso horário oficial: `America/Fortaleza`.
   - Prazos fatais processuais devem considerar rigorosamente as regras do CPC e feriados locais quando aplicável.
6. **Validação Obrigatória de Backend**:
   ```bash
   .venv/bin/python backend-automacao/manage.py test automation expedientes
   ```

---

## 4. 🤖 Agentes Especializados Configurados (`.agents/`)

| Agente | Arquivo | Responsabilidade |
| :--- | :--- | :--- |
| **Frontend Dev** | [`front-dev.md`](file:///home/rafael/RYV_TEC/automacao-juridica/.agents/front-dev.md) / [`frontend-dev.md`](file:///home/rafael/RYV_TEC/automacao-juridica/.agents/frontend-dev.md) | Interface Next.js 16, padrão visual Brasloger, componentes executivos, drawer de expediente, dashboards analíticos, Vitest e testes E2E Playwright. |
| **Backend Dev** | [`backend-dev.md`](file:///home/rafael/RYV_TEC/automacao-juridica/.agents/backend-dev.md) | APIs DRF, modelos `Processo`/`Expediente`/`ExpedienteEvent`, motor de scraping PJe (Playwright + AT-SPI), filas assíncronas e testes de persistência. |
| **DevOps Agent** | [`devops-agent.md`](file:///home/rafael/RYV_TEC/automacao-juridica/.agents/devops-agent.md) | Orquestração local (`run-local.sh`), ambiente gráfico Linux/AT-SPI, daemon PJeOffice, instalação de navegadores e esteiras de CI/CD. |

---

## 5. 🚀 Rotina de Execução Local

```bash
# Instalação inicial (uma única vez)
python3 -m venv .venv
.venv/bin/pip install -r backend-automacao/requirements.txt
.venv/bin/playwright install chromium
npm --prefix frontend install
./run-local.sh setup

# Execução no dia a dia
./run-local.sh
```

A aplicação subirá simultaneamente:
- **Frontend Next.js**: `http://localhost:3002`
- **API Django**: `http://127.0.0.1:8007`
- **Worker de Coleta**: Ativo em background (coleta agendada diária às 06:00).
