---
name: "executar_testes_manuais_com_mcp"
description: "Executor de cenários Gherkin via Playwright MCP com captura automática de evidências em vídeo"

tools:
  ['vscode', 'execute', 'read', 'edit', 'search', 'web', 'pylance-mcp-server/*', 'memory/*', 'sequential-thinking/*', 'agent', 'playwright/*','ms-python.python/getPythonEnvironmentInfo', 'ms-python.python/getPythonExecutableCommand', 'ms-python.python/installPythonPackage', 'ms-python.python/configurePythonEnvironment', 'todo']
---

# 🚀 Prompt de Execução de Teste Manual de API com Playwright MCP 

## 📋 Objetivo

Execute **via Playwright MCP** testes de API utilizando a interface do Swagger UI. O teste será executado interpretando a linguagem natural (Gherkin) e traduzindo para ações automatizadas no browser em tempo real.

**⚠️ REGRA OBRIGATÓRIA - SEMPRE TESTES DE API:**
- **SEMPRE** usar Playwright MCP para abrir e executar testes no Swagger UI
- **NUNCA** executar manualmente sem MCP
- **OBRIGATÓRIO** habilitar servidor MCP antes de iniciar

**🌐 IMPORTANTE - TESTES DE API:** Para testes de API, a execução é **SEMPRE via interface do Swagger UI**, utilizando Playwright MCP para automação de interações.

---

## ⚙️ Pré-requisitos de Configuração

### 1. Configurar Servidor MCP (`.vscode/mcp.json`)

**⚠️ REGRA OBRIGATÓRIA:** Configure um servidor Playwright MCP dedicado para testes de API:

```json
{
  "servers": {
    "playwright-api": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--viewport-size=1366,768"
      ]
    }
  }
}
```

**Servidores MCP Recomendados:**
- **Servidor principal:** `playwright-api` (dedicado para testes de API)
- **OBRIGATÓRIO** habilitar servidor antes da execução

**Notas Importantes:**
- Para testes de API, evidências devem ir em `manual_test/evidence/api/TS-API-[ID]-[método]-[recurso]/`
- Para teste único, **NÃO** é necessário usar a flag `--isolated`
- **SEMPRE** verificar se servidor MCP está ativo antes de iniciar

### 2. Estrutura de Diretórios

**⚠️ CONFORMIDADE OBRIGATÓRIA:**
```
fastqa-code/
└── manual_test/
    └── evidence/
        └── api/
            └── TS-API-[ID]-[método]-[recurso]/  # TS-API-001-GET-Activities
                ├── 01-request.png
                ├── 02-response.png
                └── curl-command.txt
```

**Exemplos de nomenclatura correta:**
- `manual_test/evidence/api/TS-API-001-GET-Activities/`
- `manual_test/evidence/api/TS-API-002-POST-Books/`
- `manual_test/evidence/api/TS-API-003-PUT-Users/`
- `manual_test/evidence/api/TS-API-004-DELETE-Activities/`
- **PADRÃO:** `TS-API-[ID]-[método]-[recurso]/` (seguir numeração sequencial)

---

## 🎯 Prompt de Execução

**Cole este prompt no chat:**

```
Execute via Playwright MCP o cenário de teste de API documentado utilizando a interface do Swagger UI.

⚠️ REGRA OBRIGATÓRIA: Executar SEMPRE via Playwright MCP, NUNCA manualmente.

REQUISITOS OBRIGATÓRIOS:

1. **Servidor MCP:**
   - **VALIDAR MCP PLAYWRIGHT HABILITADO** (OBRIGATÓRIO)
   - **Servidor recomendado:** `playwright-api` (dedicado para testes de API)
   - Verificar se servidor MCP está ativo (playwright-api, playwright-web, etc.)
   - Se NÃO estiver habilitado: Solicitar habilitação via `Ctrl+Shift+P` → `MCP: Select Servers`
   - **AGUARDAR** confirmação de habilitação do usuário antes de prosseguir

2. **Assertividade nos Passos:**
   - Siga EXATAMENTE todos os passos descritos no cenário de teste
   - Valide TODAS as condições esperadas (status code, headers, response body)
   - Capture screenshots de request preenchido e response completo

4. **Evidências:**
   - Salve screenshots em: `manual_test/evidence/api/TS-API-[ID]-[método]-[recurso]/`
   - **Estrutura obrigatória:** `manual_test/evidence/api/TS-API-[ID]-[método]-[recurso]/` (TS-API-001-GET-Activities, TS-API-002-POST-Books, etc.)
   - Nomeie os arquivos de forma descritiva:
     - `01-request.png` (request preenchido)
     - `02-response.png` (response completo)
     - `curl-command.txt` (comando curl copiado do Swagger)

5. **Tratamento de Timeouts:**
   - Para ações que podem demorar, aumente o timeout para 30000ms
   - Use `{ timeout: 30000 }` nas ações necessárias

6. **Retorno de Resultados:**
   - Execução bem-sucedida: `✅ [método] [recurso] PASS: [descrição da validação]`
   - Em caso de falha: `❌ [método] [recurso] FAIL: [motivo da falha]`
   - Exemplos: `✅ GET Activities PASS`, `❌ POST Books FAIL`

7. **Relatório:**
   - Após a execução, apresente:
     - Método e Recurso (ex: GET Activities, POST Books)
     - Status (PASS/FAIL)
     - Validações realizadas
     - Caminho das evidências
     - Curl command copiado do Swagger

**Nota:** O Playwright MCP gerencia automaticamente o ciclo de vida do browser.
```

---

## 📝 Exemplo de Código Interno (Referência)

### Como o MCP Interpreta o Cenário de API

**Nota:** O código abaixo é apenas um EXEMPLO de como o Playwright MCP traduz a descrição do teste em ações no Swagger UI. Você NÃO precisa escrever este código - apenas forneça as informações do teste.

```typescript
async (page) => {
  try {
    // 1. Navegação para Swagger UI
    await page.goto('https://fakerestapi.azurewebsites.net/index.html');
    
    // 2. Expandir seção do recurso (ex: Activities)
    await page.click('text=Activities');
    
    // 3. Localizar e expandir endpoint específico
    await page.click('text=GET /api/v1/Activities/{id}');
    
    // 4. Clicar em "Try it out"
    await page.click('button:has-text("Try it out")');
    
    // 5. Preencher parâmetros
    await page.fill('input[placeholder="id"]', '1');
    
    // 6. Screenshot do request preenchido
    await page.screenshot({ 
      path: 'manual_test/evidence/api/TS-API-001-GET-Activities/01-request.png',
      fullPage: true 
    });
    
    // 7. Executar request
    await page.click('button:has-text("Execute")');
    
    // 8. Aguardar response
    await page.waitForSelector('.responses-wrapper', { timeout: 30000 });
    
    // 9. Validar status code
    const statusCode = await page.locator('.response-col_status').textContent();
    
    // 10. Screenshot do response completo
    await page.screenshot({ 
      path: 'manual_test/evidence/api/TS-API-001-GET-Activities/02-response.png',
      fullPage: true 
    });
    
    // 11. Copiar curl command (se disponível)
    const curlCommand = await page.locator('.curl-command').textContent();
    
    // 12. Salvar curl command
    await writeFile('manual_test/evidence/api/TS-API-001-GET-Activities/curl-command.txt', curlCommand);
    
    // 13. Retorno de sucesso
    return `✅ GET Activities/1 PASS: Status ${statusCode} - ${curlCommand}`;
    
  } catch (error) {
    // 14. Captura evidência de falha
    await page.screenshot({ 
      path: 'manual_test/evidence/api/TS-API-001-GET-Activities/error.png',
      fullPage: true 
    });
    
    // 15. Retorno de falha
    return `❌ GET Activities/1 FAIL: ${error.message}`;
  }
}
```

---

## ✅ Checklist de Validação

Antes de executar, certifique-se de que:

- [ ] **✅ MCP Playwright HABILITADO** (OBRIGATÓRIO - servidor `playwright-api` recomendado)
- [ ] Arquivo `.vscode/mcp.json` está configurado corretamente
- [ ] Diretório de evidências configurado para `manual_test/evidence/api/TS-API-[ID]-[método]-[recurso]/`
- [ ] **Estrutura de pastas conforme instruções FastQA API:** usar `TS-API-[ID]-[método]-[recurso]` (TS-API-001-GET-Activities, TS-API-002-POST-Books, etc.)
- [ ] **SEMPRE usar padrão TS-ID:** Seguir `manual_test/evidence/api/TS-API-[ID]-[método]-[recurso]/`
- [ ] URL do Swagger está acessível e funcional
- [ ] Cenário de teste está documentado (opcional - pode ser gerado pelo agent)
- [ ] Endpoints, parâmetros e validações estão claros e testáveis

---

## 🎯 Exemplo de Uso Prático - API via Swagger UI

### Cenário de Teste (exemplo API)

```gherkin
# Buscar Activity por ID via Swagger UI
@api @get @smoke
Scenario: Buscar activity existente através da interface do Swagger
  Given a interface do Swagger está acessível em "https://fakerestapi.azurewebsites.net/index.html"
  And a seção "Activities" está expandida
  When localizar o endpoint "GET /api/v1/Activities/{id}"
  And clicar em "Try it out"
  And preencher o parâmetro id com valor "1"
  And clicar no botão "Execute"
  Then o status code deve ser 200 (verde)
  And o response body deve conter o campo "id" com valor 1
  And o response body deve conter os campos: title, dueDate, completed
  And o header "Content-Type" deve conter "application/json"
  And capturar screenshot do request preenchido
  And capturar screenshot do response completo
  And copiar o curl command gerado pelo Swagger
```

### Execução Automatizada via Swagger UI com Playwright MCP

**Como funciona:**
1. Você fornece o cenário em linguagem natural (Gherkin) ou apenas as informações do teste
2. O Copilot traduz para ações Playwright MCP
3. Executa usando o servidor MCP configurado
4. O browser abre automaticamente e interage com o Swagger UI
5. Captura evidências automaticamente e retorna o resultado

**Você NÃO precisa escrever código** - apenas descrever o teste ou fornecer:
- URL do Swagger
- Recurso a testar (Activities, Books, Users, etc.)
- Operação HTTP (GET, POST, PUT, DELETE)
- Parâmetros necessários (IDs, body, etc.)

**Exemplo de interação:**
```
USER: Testar GET /api/v1/Activities/1
COPILOT: [Executa via MCP]
  1. Navega para Swagger UI
  2. Expande seção Activities
  3. Localiza GET /api/v1/Activities/{id}
  4. Clica "Try it out"
  5. Preenche id=1
  6. Clica "Execute"
  7. Valida status 200
  8. Captura screenshots
  9. Retorna resultado: ✅ PASS
```

---

## 📊 Formato do Relatório Esperado

**Exemplo de Sucesso (API):**
```
✅ GET Activities/1 PASS: Status 200 OK
- Status Code: 200 OK
- Content-Type: application/json; charset=utf-8
- Response Body validado: id=1, title, dueDate, completed presentes
- Evidências: 
  - manual_test/evidence/api/TS-API-001-GET-Activities/01-request.png
  - manual_test/evidence/api/TS-API-001-GET-Activities/02-response.png
  - manual_test/evidence/api/TS-API-001-GET-Activities/curl-command.txt
- Curl Command:
  curl -X GET "https://fakerestapi.azurewebsites.net/api/v1/Activities/1" -H "accept: application/json"
```

**Exemplo de Falha:**
```
❌ POST Activities FAIL: Status 500 Internal Server Error
- Status Code Esperado: 201, Obtido: 500
- Erro: Internal Server Error
- Evidências: 
  - manual_test/evidence/api/TS-API-002-POST-Activities/error.png
- Motivo: Payload inválido ou servidor indisponível
- Curl Command: Salvo em manual_test/evidence/api/TS-API-002-POST-Activities/curl-command.txt
```

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