Parte 2: Especificação Técnica da Rota B (Emulação HTTP Criptográfica Sem Navegador)

A Rota B baseia-se na emulação nativa do protocolo de autenticação do PJe. Em vez de orquestrar instâncias do Playwright e emuladores de display para interagir com o software de desktop PJeOffice, seu microsserviço assume o papel do cliente HTTP e do motor criptográfico, executando o ciclo de vida completo de autenticação e consumo de APIs internas em containers Docker.
1. Visão Geral da Arquitetura

+---------------------------------------------------------------------------------+
|                                CONTAINER DOCKER                                 |
|                                                                                 |
|  [Certificado A1 (.pfx)]                                                        |
|         │                                                                       |
|         ▼                                                                       |
|  [Motor Criptográfico] ──(Assinatura PKCS#7)──► [HTTP Client (HTTPX/Async)]     |
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

A solução é composta por:

    Cofre de Chaves em Memória: Módulo que decodifica o arquivo PKCS#12 (.pfx) do advogado com a respectiva senha e mantém o par de chaves e o certificado X.509 disponíveis em memória segura durante o ciclo da requisição.

    Motor de Assinatura CAdES/PKCS#7: Camada criptográfica construída sobre bibliotecas de padrão ICP-Brasil (como cryptography ou asn1crypto em Python, ou Bouncy Castle em Java/Go) que gera a estrutura SignedData exigida pelo tribunal.

    Cliente de Sessão HTTP: Instância com persistência de cookies (jar de cookies), cabeçalhos de fingerprint padronizados e controle de renovação automática de tokens.

2. O Ciclo de Autenticação Passo a Passo

O PJe utiliza o padrão Challenge-Response para autenticação baseada em certificados. O navegador tradicional delega isso ao PJeOffice local; na Rota B, o fluxo é inteiramente sintetizado via chamadas de rede.
Passo 1: Aquisição do Desafio (Challenge)

O backend executa uma requisição GET ou POST para o endpoint de pré-login do tribunal (que varia conforme a versão do PJe, ex.: /pje/login.seam, /pje/autenticacao/login ou rota do Keycloak institucional).

    Resposta do Tribunal: Um payload JSON ou parâmetro HTML contendo uma string pseudoaleatória (nonce/token) e, frequentemente, um identificador transitório de sessão (UUID).

    Finalidade: O servidor registra esse texto temporariamente em cache e aguarda que o usuário prove a posse da chave privada correspondente àquela identidade.

Passo 2: Construção da Assinatura Digital Headless

De posse do texto do desafio, o backend aciona o motor criptográfico localmente:

    O texto do desafio é convertido em bytes (codificação UTF-8 ou ISO-8859-1, conforme exigência do tribunal específico).

    Calcula-se o resumo criptográfico dos dados utilizando a função hash SHA-256 (padrão ICP-Brasil v5+).

    A chave privada RSA do certificado A1 cifra o resumo criptográfico, gerando a assinatura.

    Encapsula-se o resultado na estrutura padrão PKCS#7 / CMS (Cryptographic Message Syntax - RFC 5652) no formato Attached ou Detached (o PJeOffice tradicionalmente utiliza Detached SignedData, onde o conteúdo original não é duplicado dentro do envelope).

    O envelope binário DER é convertido para uma representação em Base64.

Passo 3: Submissão da Resposta e Emissão da Sessão

O cliente HTTP envia um POST para o endpoint de validação do PJe contendo:

    O payload Base64 da assinatura gerada.

    O certificado público do advogado (extraído do A1) e a cadeia de certificados intermediários da Autoridade Certificadora (AC).

    O identificador de desafio (nonce/session-id).

Processamento no Tribunal:

    O servidor do PJe valida a cadeia do certificado digital contra a Autoridade Certificadora Raiz da ICP-Brasil.

    Confere se a assinatura confere com o texto do desafio que ele próprio emitiu segundos antes.

    Valida a situação cadastral do CPF/OAB na base de usuários do tribunal.

    Havendo conformidade, o servidor emite nos cabeçalhos de resposta:

        O cookie de sessão Java: Set-Cookie: JSESSIONID=...; Path=/pje; Secure; HttpOnly.

        Em versões modernizadas (PJe 2.x com arquitetura PDPJ): o cabeçalho com o token JWT de autorização (access_token).

3. Consumo das APIs Internas e Acesso a Processos Sigilosos

Uma vez estabelecida a sessão, o sistema não precisa processar código HTML ou lidar com elementos de tela. O front-end moderno do PJe (baseado em Angular) consome serviços REST internos que estão plenamente acessíveis para a sua sessão autenticada.
Como Funciona o Acesso a Autos com Segredo de Justiça

Nos sistemas de consulta pública, processos em segredo de justiça são bloqueados ou omitidos. Na Rota B:

    A sessão HTTP carrega o identificador e a assinatura do advogado formalmente constituído nos autos.

    Quando seu backend faz uma chamada para a rota de detalhes do processo (ex.: GET /pje/api/v1/processos/{idProcesso} ou endpoint de timeline processual), o controle de acesso baseado em regras (RBAC) do PJe identifica que o titular da sessão é patrono habilitado.

    O sistema retorna a integridade do espelho processual: partes, decisões, certidões e links para download dos binários em PDF de todos os anexos sigilosos.

Coleta Contínua de Intimações (Painel do Advogado)

Em vez de navegar pelas abas visuais do portal:

    O backend realiza requisições periódicas para as rotas que alimentam o "Painel do Advogado" (ex.: endpoints de comunicações não lidas, pendências de ciência e prazos abertos).

    A resposta é estruturada diretamente em JSON, contendo: identificador da intimação, data de disponibilização, prazo fatal em dias, número único CNJ e teor da certidão de publicação.

    Isso permite ingerir centenas de intimações em milissegundos, salvando-as diretamente no banco de dados da aplicação.

4. Ciclo de Peticionamento Automático

O peticionamento automatizado dispensa a simulação de formulários web complexos e é executado em duas etapas HTTP:
Etapa 1: Assinatura e Upload de Documentos

    A petição e os documentos probatórios são compilados em formato PDF (em conformidade com o padrão PDF/A e as resoluções de tamanho de arquivo do tribunal).

    O motor criptográfico assina cada PDF digitalmente no padrão CAdES-BES com carimbo de tempo, utilizando a chave privada A1.

    O cliente HTTP envia os arquivos via requisição multipart/form-data para o endpoint de repositório temporário do PJe (ex.: /pje/api/v1/documentos/upload), capturando os identificadores (hash ou UUID) de cada arquivo armazenado.

Etapa 2: Protocolo da Manifestação Processual

O backend submete uma requisição POST com payload JSON para o endpoint de juntada do processo:
JSON

{
  "idProcesso": 1284750,
  "tipoManifestacao": "CONTESTACAO",
  "documentoPrincipal": {
    "idUpload": "a7b3c9-...",
    "descricao": "Contestação com Pedido de Efeito Suspensivo",
    "tipoDocumento": 38
  },
  "anexos": [
    {
      "idUpload": "f4e2d1-...",
      "descricao": "Procuração Ad Judicia",
      "tipoDocumento": 12
    }
  ],
  "segredoJustica": false
}

    O PJe realiza a juntada definitiva aos autos, gera o comprovante de protocolo com número de recibo e carimbo do servidor, e devolve o status 200 OK acompanhado dos metadados da juntada.

5. Diretrizes de Engenharia e Infraestrutura

Para garantir estabilidade em ambiente Docker e mitigar bloqueios de infraestrutura:

    Ciclo de Vida das Chaves em Memória: Nunca extraia certificados A1 em disco dentro do container sem criptografia. Carregue o arquivo .pfx a partir de variáveis de ambiente codificadas em Base64 ou cofres de segredos, instanciando as chaves exclusivamente na memória RAM da aplicação.

    Gerenciamento de Timeouts e Sessões: A sessão JSESSIONID do PJe expira tipicamente entre 15 e 30 minutos de inatividade. O cliente HTTP deve implementar um interceptador (middleware) que detecta respostas 401 Unauthorized ou redirecionamentos para telas de login, disparando automaticamente uma nova rodada de autenticação Challenge-Response e repetindo a requisição original de forma transparente.

    Evasão de Bloqueios de WAF: Portais de tribunais com proteções perimetrais (Cloudflare, Imperva, F5) bloqueiam requisições oriundas de faixas de IP pertencentes a provedores de nuvem pública. O tráfego de saída dos containers deve ser obrigatoriamente roteado por meio de um pool de proxies residenciais ou empresariais fixos baseados no Brasil, mantendo consistência de cabeçalhos HTTP (User-Agent moderno, cabeçalhos Sec-Ch-Ua e negociação TLS idêntica a navegadores reais).