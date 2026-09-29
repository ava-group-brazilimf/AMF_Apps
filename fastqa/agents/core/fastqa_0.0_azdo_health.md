---
name: "fastqa_0.0_azdo_health"
description: "Diagnóstico e validação da integração Azure DevOps"

tools:
  - memory
---

# Template: Diagnóstico — Azure DevOps Health Check

## 🎯 Objetivo

> **⚠️ ATENÇÃO:** Este agente é invocado automaticamente pela extensão FastQA quando o comando `@fastqa:azdo_health` é executado. A extensão TypeScript gerencia o estado da jornada e renderiza os botões ▶️ — este arquivo serve apenas como documentação e referência de configuração.

Verificar se a integração Azure DevOps está corretamente configurada antes de qualquer operação dependente.

---

## 📋 O que o diagnóstico verifica

A extensão executa automaticamente o script `check-health.command.ts`, que valida:

| Check | O que testa |
|---|---|
| ✅/❌ `fastqa/.env` existe | Arquivo de configuração presente |
| ✅/❌ `AZURE_DEVOPS_ORG_URL` | Var definida e não é placeholder |
| ✅/❌ `AZURE_DEVOPS_PAT` | PAT definido e não é placeholder |
| ✅/❌ `AZURE_DEVOPS_DEFAULT_PROJECT` | Projeto configurado |
| ✅/❌ Conectividade REST | `GET /_apis/projects?api-version=7.1` com auth |
| ✅/❌ Projeto existe | Projeto configurado existe na organização |
| ✅/❌ MCP wrapper existe | `fastqa/scripts/mcp-azdo-wrapper.js` presente |
| ✅/❌ mcp.json usa wrapper | Não usa `${env:...}` legado |

---

## 🔄 Fluxo gerenciado pela extensão

```
@fastqa:azdo_health
       │
       ▼
  Executa check-health.command.ts
       │
  ┌────┴────┐
  │ Exit 0  │ ─── Verifica MCP Server ativo
  └─────────┘         │
                 ┌────┴────┐
                 │ MCP OK  │ ─── ✅ Avança journey_state + ▶️ próximo step
                 └─────────┘
                 │
                 ┌────┴────────┐
                 │ MCP parado  │ ─── Orienta iniciar MCP + 🔁 revalidar
                 └─────────────┘
  │
  ┌────┴────┐
  │ Exit 1  │ ─── ❓ QuickPick: "Vai usar Azure DevOps?"
  └─────────┘         │
                 ┌────┴────┐
                 │   SIM   │ ─── Guia de configuração inline + 🔁 botão
                 └─────────┘
                 │
                 ┌────┴────┐
                 │   NÃO   │ ─── Lista arquivos em manual_test/US/
                 └─────────┘     ▶️ load_pbi com modo local
```

---

## ⚙️ Referência de Configuração

### `fastqa/.env`

```dotenv
# URL da organização Azure DevOps
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/sua-organizacao

# Personal Access Token (PAT)
# Escopos mínimos: Work Items (R&W) + Test Management (R&W)
AZURE_DEVOPS_PAT=seu-pat-aqui

# Nome exato do projeto (case-sensitive)
AZURE_DEVOPS_DEFAULT_PROJECT=NomeDoProjeto

# Versão da API (não alterar)
AZURE_DEVOPS_API_VERSION=7.1
```

### `.vscode/mcp.json`

```json
"azureDevOps": {
  "command": "node",
  "args": ["fastqa/scripts/mcp-azdo-wrapper.js"]
}
```

> O wrapper `mcp-azdo-wrapper.js` carrega as credenciais diretamente do `fastqa/.env`, garantindo que o MCP e os scripts TypeScript usem a **mesma fonte** de credenciais. Não é necessário configurar variáveis de ambiente no SO.

### Iniciar servidor MCP

`Ctrl+Shift+P` → `MCP: List Servers` → `azureDevOps` → **Start Server**

> **Auto-start:** Após o setup (`/start` ou `/update`), a setting `chat.mcp.autostart` é habilitada automaticamente no workspace. Na primeira inicialização, o VS Code exibirá um **diálogo de Trust** — clique em "Allow" para que os servidores MCP iniciem automaticamente a partir da próxima sessão.

---

## 🔧 Troubleshooting

### MCP server parado (health check passa mas MCP não responde)

**Sintoma:** O health check REST passa (8/8 checks OK), mas ao tentar usar ferramentas MCP (ex.: `list_projects`, `get_work_item`) elas não estão disponíveis ou retornam erro de conexão.

**Causa:** O VS Code não inicia automaticamente servidores MCP definidos em `.vscode/mcp.json`. O servidor precisa ser iniciado manualmente pelo menos uma vez por sessão.

**Solução:**
1. `Ctrl+Shift+P` → `MCP: List Servers`
2. Localize `azureDevOps` → clique em **Start Server**
3. Execute `@fastqa:azdo_health` novamente para revalidar

### MCP reporta "conectado" mas retorna 401 (Authentication Failed)

**Sintoma:** O servidor MCP aparece como ativo no VS Code, o health check REST passa, mas ao usar ferramentas MCP (ex.: `get_work_item`) retorna `401 — Failed to authenticate`.

**Causa:** O MCP estava usando `${env:...}` (variáveis do SO) enquanto o health check usava `fastqa/.env`. Quando as credenciais divergem, o health check passa mas o MCP falha.

**Solução:**
1. Execute `@fastqa_ /update` para migrar para o wrapper `mcp-azdo-wrapper.js`
2. Verifique que `fastqa/.env` tem o PAT correto e não expirado
3. Reinicie o servidor MCP: `Ctrl+Shift+P` → `MCP: List Servers` → `azureDevOps` → **Restart**
4. Execute `@fastqa:azdo_health` para revalidar

### PAT expirado

**Sintoma:** Checks 1-4 passam, Check 5 (REST) falha com `401 (PAT inválido ou expirado)`.

**Solução:**
1. Acesse `https://dev.azure.com/{org}/_usersSettings/tokens`
2. Crie um novo PAT com escopos: Work Items (R&W), Test Management (R&W)
3. Atualize `AZURE_DEVOPS_PAT` em `fastqa/.env`
4. Reinicie o servidor MCP

### Conflito process.env vs .env (401 com PAT válido no .env)

**Sintoma:** O PAT no `fastqa/.env` está correto e válido, mas o Check 5 retorna `401`. O diagnóstico pode exibir: `⚠️ CONFLITO: AZURE_DEVOPS_PAT do .env difere do process.env`.

**Causa:** O terminal do VS Code herda variáveis de ambiente do SO. Se `AZURE_DEVOPS_PAT` está definida no SO (stale/diferente), versões anteriores do health check usavam o valor do SO em vez do `.env`.

**Solução:**
1. Execute `@fastqa_ /update` para atualizar o health check (`.env` agora tem precedência)
2. Se o problema persistir, remova a variável `AZURE_DEVOPS_PAT` do SO:
   - Windows: `setx AZURE_DEVOPS_PAT ""` + reiniciar VS Code
   - Linux/Mac: remover do `~/.bashrc` ou `~/.zshrc`
3. Reinicie o VS Code para limpar vars herdadas


# Template: Diagnóstico — Azure DevOps Health Check

## 🎯 Objetivo
Verificar se a integração com o Azure DevOps está corretamente configurada **antes** de executar qualquer comando que dependa desta integração (`load_pbi`, `azdo_create_test_case`, etc.).

Quando há qualquer problema, este agente bifurca o fluxo com base na intenção do usuário: guia a configuração se o Azure DevOps será usado, ou redireciona para documentação local caso contrário.

---

## 🔄 Fluxo de Execução

### 1️⃣ Executar o script de diagnóstico

```bash
# Rodar a partir da raiz do workspace (onde a pasta fastqa/ está)
npx tsx fastqa/scripts/azure-devops/commands/check-health.command.ts
```

> Execute o script acima no terminal e aguarde a tabela de resultado.

---

### 2️⃣ Interpretar o resultado

#### ✅ TODOS OS CHECKS PASSARAM

```
✅ INTEGRAÇÃO OK — Azure DevOps configurado corretamente.
```

**Ação OBRIGATÓRIA — Verificar MCP Server:**

Após o health check REST passar, é **obrigatório** verificar se o MCP server `azureDevOps` está ativo no VS Code. O health check valida apenas a conectividade REST direta — o MCP server pode estar parado mesmo com credenciais corretas.

1. **Tente chamar uma ferramenta MCP** (ex.: `list_projects` ou `get_project`) para testar se o servidor está respondendo.

2. **Se a ferramenta MCP estiver disponível e responder com sucesso:**
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ✅ Azure DevOps — Conexão validada!

     • Organização: {AZURE_DEVOPS_ORG_URL}
     • Projeto:     {AZURE_DEVOPS_DEFAULT_PROJECT}
     • MCP Server:  azureDevOps ✅ ativo e respondendo

   📍 Próximo: @fastqa:load_pbi
      "Carregar PBI do Azure DevOps"
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

3. **Se a ferramenta MCP NÃO estiver disponível** (servidor parado):
   ```
   ✅ Health check REST: OK
   ⚠️ MCP Server azureDevOps: NÃO ESTÁ ATIVO

   O servidor MCP precisa ser iniciado manualmente:
     1. Ctrl+Shift+P → "MCP: List Servers"
     2. Localize "azureDevOps" → clique em "Start Server"
     3. Execute @fastqa:azdo_health novamente para revalidar
   ```
   **NÃO** avançar a jornada neste caso. Aguardar o usuário iniciar o MCP e revalidar.

4. **Se a ferramenta MCP retornar erro 401 (Authentication Failed):**
   ```
   ✅ Health check REST: OK
   ❌ MCP Server: 401 — Authentication Failed

   O PAT pode ter expirado após o health check ou o MCP está usando credenciais antigas.
   Solução:
     1. Verifique fastqa/.env — o PAT está correto e não expirado?
     2. Reinicie o MCP: Ctrl+Shift+P → "MCP: List Servers" → azureDevOps → Restart
     3. Execute @fastqa:azdo_health novamente
   ```
   **NÃO** avançar a jornada neste caso.

---

#### ❌ UM OU MAIS CHECKS FALHARAM

Antes de exibir o guia de correção, **perguntar ao usuário**:

```
❌ Detectei problemas na integração com o Azure DevOps.

Você vai usar o **Azure DevOps** para carregar o PBI desta jornada?

  1️⃣  Sim — quero configurar/corrigir e usar o Azure DevOps
  2️⃣  Não — vou usar documentação local (fastqa/manual_test/US/)
```

**AGUARDAR** a resposta do usuário antes de prosseguir.

---

### 3️⃣A — Resposta: SIM (usar Azure DevOps)

Exibir o passo-a-passo de configuração, focando apenas nos checks que falharam:

#### 📋 Guia de Configuração

**Passo 1 — Criar o arquivo `.env`**

Se `fastqa/.env` não existe:
```bash
# Na pasta fastqa/ do seu projeto
cp fastqa/.env.example fastqa/.env
```
> Abra `fastqa/.env` e preencha os valores abaixo.

**Passo 2 — Configurar as variáveis obrigatórias**

```dotenv
# URL da organização Azure DevOps
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/sua-organizacao

# Personal Access Token (PAT)
# Como criar: https://learn.microsoft.com/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate
# Escopos mínimos necessários: Work Items (Read & Write), Test Management (Read & Write)
AZURE_DEVOPS_PAT=seu-pat-aqui

# Nome exato do projeto no Azure DevOps (case-sensitive)
AZURE_DEVOPS_DEFAULT_PROJECT=NomeDoProjeto

# Versão da API (não alterar)
AZURE_DEVOPS_API_VERSION=7.1
```

**Passo 3 — Verificar o servidor MCP em `.vscode/mcp.json`**

Confirmar que o bloco `azureDevOps` usa o wrapper (não `${env:...}` legado):

```json
"azureDevOps": {
  "command": "node",
  "args": ["fastqa/scripts/mcp-azdo-wrapper.js"]
}
```

> O wrapper carrega credenciais diretamente do `fastqa/.env`. Se o `mcp.json` ainda usa `${env:...}`, execute `@fastqa_ /update` para migrar automaticamente.

**Passo 4 — Iniciar o servidor MCP no VS Code**

1. Abrir a paleta de comandos: `Ctrl+Shift+P` (Windows/Linux) ou `Cmd+Shift+P` (macOS)
2. Buscar: `MCP: List Servers`
3. Localizar `azureDevOps` e clicar em **Start Server**

**Passo 5 — Revalidar**

```
Após configurar, execute novamente: @fastqa:azdo_health
```

---

### 3️⃣B — Resposta: NÃO (usar documentação local)

Verificar se existe algum arquivo em `fastqa/manual_test/US/`:

```bash
# Listar arquivos existentes em manual_test/US/
```

**Cenário A — Arquivo encontrado (`PBI-{ID}.md` ou `US-{ID}.md`):**

```
✅ Arquivo local encontrado em fastqa/manual_test/US/

Você pode prosseguir sem o Azure DevOps.
Execute @fastqa:load_pbi — ele lerá o arquivo local automaticamente.
```

**Cenário B — Nenhum arquivo encontrado:**

```
📄 Nenhuma documentação local encontrada em fastqa/manual_test/US/

Crie o arquivo do PBI antes de continuar:
  Caminho: fastqa/manual_test/US/PBI-{ID}.md

Use o formato abaixo como referência (baseado em PBI-13.md):
```

Exibir o template de formato:

```markdown
# [Tipo de Item] #[ID]: [Título]

**Estado:** [New | Active | Resolved | Closed]
**Prioridade:** [1-4]
**Iteração:** [NomeProjeto\Sprint N]
**Criado em:** [DD/MM/AAAA]
**Criado por:** [Nome]

---

## 📝 Descrição

### 👤 User Story

Como [persona],
Quero [ação],
Para que [benefício].

### 📋 Descrição Detalhada

[Contexto detalhado do requisito]

---

## ✅ Critérios de Aceite

- [ ] [Critério 1]
- [ ] [Critério 2]
- [ ] [Critério N]

---

## 🔗 Dependências

[Descrever ou "Nenhuma dependência identificada."]

## 📄 Notas Técnicas

[URLs, configurações, restrições técnicas relevantes]
```

```
Após criar o arquivo, execute: @fastqa:load_pbi
```

---

## 🔄 Continuidade da Jornada

Após concluir este comando com sucesso (qualquer caminho — AzDO configurado ou fallback local confirmado):

1. **Leia** `fastqa/scripts/journey_state.json`
2. **Se `active_journey` não é null** (jornada ativa):
   - Marque o step atual como `"completed"` no array `steps`
   - Adicione ao `context` a chave `azdo_health_mode`: `"azure_devops"` ou `"local_docs"`
   - Incremente `current_step_index`
   - Atualize `updated_at` com timestamp atual
   - Grave o arquivo `journey_state.json`
   - Exiba mensagem de continuidade:
     ```
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     🔌 Diagnóstico AzDO — Step {N}/{total} ✅ Concluído!
     📍 Próximo: @fastqa:{próximo_comando}
        "{descrição_do_próximo}"
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ```
