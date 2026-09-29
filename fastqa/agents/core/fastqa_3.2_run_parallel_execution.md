---
name: "fastqa_3.2_run_parallel_execution"
description: "Executor paralelo de cenários Gherkin via múltiplos servidores Playwright MCP com captura de evidências POR STEP (Screenshot ou Vídeo)"

tools:
  - playwright mcp (múltiplos servidores)
  - memory
  - sequential-thinking
---

# 🚀 Executor Paralelo com Playwright MCP

## 📋 Objetivo
Execute **manualmente** múltiplos cenários de teste **em browsers separados**, usando servidores Playwright MCP diferentes para cada cenário. Cada cenário é executado interpretando a linguagem natural (Gherkin) e traduzindo para ações no browser em tempo real.

O usuário pode escolher entre dois formatos de evidência (aplicado a **todos** os cenários):
- **📷 Screenshot** — Captura de imagem estática por step (padrão)
- **🎥 Vídeo** — Gravação contínua com capítulos por step (requer `--caps=devtools`)

**⚠️ ATENÇÃO:** Este prompt é para **EXECUÇÃO MANUAL** via Playwright MCP, **NÃO** para criar scripts automatizados. Os cenários são executados via linguagem natural.

---

## ⚙️ Pré-requisitos

### 1. Servidor MCP Base (`.vscode/mcp.json`)

O template inclui apenas o servidor `playwright-web` (para execução individual). Os servidores paralelos (`playwright-parallel-1`, `playwright-parallel-2`, etc.) são **criados automaticamente** pelo agente no **Passo 0.5** conforme a quantidade de cenários informada pelo usuário.

```json
{
  "servers": {
    "playwright-web": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--output-dir", "fastqa/manual_test/evidence",
        "--viewport-size=1366,768",
        "--extension",
        "--caps=devtools"
      ],
      "env": {
        "PLAYWRIGHT_MCP_EXTENSION_TOKEN": "<EXTENSION_TOKEN>"
      }
    }
  }
}
```

**ℹ️ Sobre os servidores paralelos criados dinamicamente:**
- Cada servidor paralelo recebe `--isolated` para executar em browser separado
- Cada servidor com `--output-dir` diferente para sua pasta de evidências
- **TODOS** os servidores com `--caps=devtools`
- O token `PLAYWRIGHT_MCP_EXTENSION_TOKEN` é copiado do `playwright-web`

> **ℹ️ `--caps=devtools`** habilita as ferramentas `browser_start_video`, `browser_stop_video` e `browser_video_chapter`, necessárias para o modo de evidência em **Vídeo**. Pode ser mantido mesmo quando o modo Screenshot for selecionado — não causa nenhum impacto.

### 2. Estrutura de Diretórios
As pastas de evidências serão criadas **AUTOMATICAMENTE** no Passo 1 do Fluxo de Execução.

---

## 🎯 Fluxo de Execução

> **⚠️ REGRA CRÍTICA DE EVIDÊNCIAS:**
> - **Modo 📷 Screenshot:** Cada step Gherkin executado **DEVE** gerar **obrigatoriamente** um screenshot salvo na pasta `fastqa/manual_test/evidence/TS-{NNN}/`.
> - **Modo 🎥 Vídeo:** A gravação de vídeo contínua com capítulos por step **substitui** screenshots individuais. Cada step gera um `browser_video_chapter` no vídeo.
>
> Se a pasta NÃO existir, **CRIE-A** antes de iniciar qualquer step.

### Passo 0 — Preparação

1. Solicitar ao usuário a identificação dos **cenários** a executar (ex: "TC-15, TC-16, TC-17" ou "todos de test_cases/") e **AGUARDAR** resposta
2. Carregar cenários Gherkin de `fastqa/manual_test/test_cases/`
3. Solicitar **URL** da aplicação e **AGUARDAR** resposta
4. Solicitar o **formato de evidência** e **AGUARDAR** resposta:

```markdown
📸 **Selecione o formato de captura de evidências (aplicado a TODOS os cenários):**

1. 🎥 **Vídeo** — Gravação contínua com capítulos por step (arquivo .webm por cenário)
   - Captura toda a interação visual, ideal para toasts e animações
   - Requer `--caps=devtools` no servidor MCP

2. 📷 **Screenshot** — Captura de imagem por step (arquivos .png)
   - Uma imagem por step Gherkin (padrão atual)
   - Recomendado usar `browser_snapshot` complementar para registrar textos visíveis
```

> **❌ NÃO PROSSEGUIR SEM A RESPOSTA DO USUÁRIO.**
> A escolha define o `MODO DE EVIDÊNCIA` utilizado em todos os cenários e passos seguintes.

5. Solicitar ao usuário a **quantidade de servidores MCP paralelos** a criar e **AGUARDAR** resposta:

```markdown
🔢 **Quantos servidores Playwright MCP paralelos deseja utilizar?**

Cada cenário será executado em um servidor isolado. Informe a quantidade desejada (ex: 3 para executar 3 cenários em paralelo).

> ℹ️ Os servidores serão criados automaticamente no `.vscode/mcp.json`
```

> **❌ NÃO PROSSEGUIR SEM A RESPOSTA DO USUÁRIO.**

### Passo 0.5 — Criar Servidores MCP Paralelos (OBRIGATÓRIO)

> **⚠️ Este passo cria dinamicamente os servidores Playwright MCP necessários para a execução paralela.**

1. **Ler** o arquivo `.vscode/mcp.json`
2. **Obter o token** do servidor `playwright-web` existente (campo `env.PLAYWRIGHT_MCP_EXTENSION_TOKEN`)
3. **Para cada servidor necessário** (de 1 até a quantidade informada pelo usuário), adicionar uma entrada no objeto `servers`:

```json
"playwright-parallel-{N}": {
  "command": "npx",
  "args": [
    "@playwright/mcp@latest",
    "--output-dir",
    "fastqa/manual_test/evidence/TS-{NNN}",
    "--viewport-size=1366,768",
    "--isolated",
    "--extension",
    "--caps=devtools"
  ],
  "env": {
    "PLAYWRIGHT_MCP_EXTENSION_TOKEN": "<TOKEN_COPIADO_DO_PLAYWRIGHT_WEB>"
  }
}
```

**Regras de criação:**
- `{N}` = número sequencial (1, 2, 3...)
- `{NNN}` = número com 3 dígitos (001, 002, 003...)
- **TODOS** os servidores paralelos com `--isolated`
- **TODOS** com `--extension` e `--caps=devtools`
- O `PLAYWRIGHT_MCP_EXTENSION_TOKEN` deve ser copiado do `playwright-web`
- Se o token do `playwright-web` for `<EXTENSION_TOKEN>` (placeholder), manter o mesmo placeholder

4. **Gravar** o arquivo `.vscode/mcp.json` atualizado com indentação de 2 espaços
5. **Remover servidores `playwright-parallel-*` excedentes**, se existirem de execuções anteriores (manter apenas a quantidade informada)
6. **Informar ao usuário** que os servidores foram criados e solicitar que recarregue os MCPs:

```markdown
✅ **{N} servidores Playwright MCP paralelos criados em `.vscode/mcp.json`:**

| Servidor | Output Dir |
|----------|-----------|
| playwright-parallel-1 | evidence/TS-001/ |
| playwright-parallel-2 | evidence/TS-002/ |
| playwright-parallel-3 | evidence/TS-003/ |

⚠️ **Ação necessária:** Recarregue os servidores MCP para ativá-los:
1. `Ctrl+Shift+P` → `MCP: List Servers`
2. Verifique que os servidores `playwright-parallel-*` aparecem na lista
3. Inicie os servidores necessários

**Confirme quando os servidores estiverem ativos.**
```

> **❌ NÃO PROSSEGUIR SEM A CONFIRMAÇÃO DO USUÁRIO.**

7. Atribuir cada cenário a um servidor MCP e apresentar tabela de atribuição:

```markdown
📋 **Atribuição de cenários aos servidores MCP:**

| # | Cenário | Servidor MCP | Pasta de Evidências |
|---|---------|--------------|---------------------|
| 1 | TC-15 - Login válido | playwright-parallel-1 | evidence/TS-001/ |
| 2 | TC-16 - Login inválido | playwright-parallel-2 | evidence/TS-002/ |
| 3 | TC-17 - Reset senha | playwright-parallel-3 | evidence/TS-003/ |

**Confirma esta atribuição?** (Sim / Ajustar)
```

> **❌ NÃO PROSSEGUIR SEM A CONFIRMAÇÃO DO USUÁRIO.**

### Passo 1 — Criar Pastas de Evidências (OBRIGATÓRIO)

**ANTES de qualquer navegação no browser**, criar **TODAS** as pastas de evidências:

```powershell
# PowerShell — criar todas as pastas de uma vez
"TS-001", "TS-002", "TS-003" | ForEach-Object {
    New-Item -ItemType Directory -Path "fastqa/manual_test/evidence/$_" -Force
}
```

> **❌ NÃO PROSSEGUIR SEM CRIAR TODAS AS PASTAS.**
> **❌ NÃO SALVAR evidências na raiz do projeto.**
> **❌ NÃO SALVAR evidências em outra pasta que não seja `fastqa/manual_test/evidence/TS-{NNN}/`.**

### Passo 2 — Navegar e Iniciar Evidência (POR CENÁRIO)

Para **CADA cenário**, no **servidor MCP atribuído**:

1. Utilizar `browser_navigate` (no servidor MCP correto) para acessar a URL informada
2. **IMEDIATAMENTE** após a navegação, capturar a primeira evidência conforme o modo selecionado:

#### 📷 Modo Screenshot

**Regra de captura de screenshot:**
- Usar `browser_take_screenshot` do servidor MCP atribuído ao cenário
- **MOVER ou RENOMEAR** o arquivo gerado para a pasta de evidências com o nome correto
- Se o `browser_take_screenshot` salvar o arquivo em outro local, **copie-o** para a pasta de evidências usando `run_in_terminal`
- **Complementar** com `browser_snapshot` para registrar textos visíveis na tela (títulos, mensagens, labels)

**Nome do arquivo:** `step-00-navegacao-inicial_{HH}h{MM}m{SS}s.png`
**Caminho completo:** `fastqa/manual_test/evidence/TS-{NNN}/step-00-navegacao-inicial_{HH}h{MM}m{SS}s.png`

> **ℹ️ TIMESTAMP:** Capturar horário exato no momento da navegação (formato `14h23m07s`) e inserir como sufixo no nome do arquivo. Use `Get-Date -Format 'HHhmmmsss'` (PowerShell) ou `date +%Hh%Mm%Ss` (Bash) para obter o valor.

#### 🎥 Modo Vídeo

1. Obter timestamp: `$ts = Get-Date -Format 'HHhmmss'` → formatar como `HHhMMmSSs`
2. Chamar `browser_start_video` (no servidor MCP atribuído) com:
   - `filename`: `TS-{NNN}_video_{HH}h{MM}m{SS}s.webm`
3. Chamar `browser_video_chapter` com:
   - `title`: `"Navegação Inicial"`
   - `description`: URL acessada

> **ℹ️** O vídeo será salvo no `--output-dir` configurado no servidor MCP. Não é necessário mover o arquivo manualmente.

### Passo 3 — Executar Steps Gherkin (POR CENÁRIO, COM EVIDÊNCIA POR STEP)

Para **CADA cenário** (executar um cenário por vez, do início ao fim), no **servidor MCP atribuído**:

Para **CADA step** do cenário Gherkin, executar OBRIGATORIAMENTE o ciclo correspondente ao modo de evidência selecionado:

#### 📷 Modo Screenshot

```
┌─────────────────────────────────────────────────┐
│  CICLO POR STEP (repetir para CADA step):       │
│                                                 │
│  1. Ler o step Gherkin                          │
│  2. Traduzir para ação Playwright               │
│  3. Executar no browser (click, fill, assert..) │
│  4. ⚠️ CAPTURAR SCREENSHOT DO STEP ⚠️           │
│  5. Capturar browser_snapshot (texto visível)   │
│  6. Garantir que screenshot está na pasta:       │
│     fastqa/manual_test/evidence/TS-{NNN}/       │
│  7. Registrar resultado (✅ ou ❌)              │
│                                                 │
│  ❌ NÃO AVANÇAR PARA O PRÓXIMO STEP SEM        │
│     TER FEITO O SCREENSHOT DO STEP ATUAL        │
└─────────────────────────────────────────────────┘
```

> **💡 Dica para evidências mais detalhadas:**
> - Quebre steps compostos em sub-steps (ex: "preenche formulário e clica" → um screenshot ao preencher + outro ao clicar)
> - Use `browser_snapshot` junto com cada screenshot para registrar textos visíveis na tela (mensagens, toasts, alertas, labels)
> - Quando detectar elementos transientes (toasts, notificações), adicione observações descritivas no relatório de execução sobre o conteúdo exibido

**Nomenclatura OBRIGATÓRIA dos screenshots:**

| Step # | Keyword | Arquivo |
|--------|---------|---------|
| 1 | Given | `step-01-given-{descricao-curta}_{HH}h{MM}m{SS}s.png` |
| 2 | When | `step-02-when-{descricao-curta}_{HH}h{MM}m{SS}s.png` |
| 3 | And | `step-03-and-{descricao-curta}_{HH}h{MM}m{SS}s.png` |
| 4 | Then | `step-04-then-{descricao-curta}_{HH}h{MM}m{SS}s.png` |
| ... | ... | `step-{NN}-{keyword}-{descricao-curta}_{HH}h{MM}m{SS}s.png` |

**Regras de nomenclatura:**
- `{NN}` = número sequencial com 2 dígitos (01, 02, 03...)
- `{keyword}` = given, when, then, and, but (lowercase)
- `{descricao-curta}` = resumo do step em 3-5 palavras, sem acentos, separado por hífen
- `{HH}h{MM}m{SS}s` = timestamp do momento da captura (ex: `14h23m07s`)
  - PowerShell: `Get-Date -Format 'HHhmmss'` → formatar como `14h23m07s`
  - Bash/Linux: `date +%Hh%Mm%Ss`
- Exemplos reais:
  - `step-01-given-usuario-na-pagina-login_14h23m07s.png`
  - `step-02-when-preenche-email-valido_14h23m15s.png`
  - `step-03-and-preenche-senha-valida_14h23m22s.png`
  - `step-04-when-clica-botao-entrar_14h23m30s.png`
  - `step-05-then-redireciona-para-dashboard_14h23m38s.png`

**⚠️ Garantia de salvamento na pasta correta:**

Após cada `browser_take_screenshot`, verificar onde o arquivo foi salvo.
Se o Playwright MCP salvou em outro diretório (ex: raiz do projeto), **MOVER** o arquivo com o timestamp correto:

```powershell
# PowerShell — obter timestamp e mover screenshot para pasta de evidências
$ts = Get-Date -Format 'HHhmmss'
# Formatar como HHhMMmSSs (ex: 14h23m07s)
$ts = $ts -replace '(\d{2})h(\d{2})(\d{2})', '$1h$2m$3s'
Move-Item -Path "screenshot-gerado.png" -Destination "fastqa/manual_test/evidence/TS-{NNN}/step-{NN}-{keyword}-{descricao}_${ts}.png" -Force
```

```bash
# Bash — obter timestamp e mover screenshot para pasta de evidências
ts=$(date +%Hh%Mm%Ss)
mv screenshot-gerado.png fastqa/manual_test/evidence/TS-{NNN}/step-{NN}-{keyword}-{descricao}_${ts}.png
```

#### 🎥 Modo Vídeo

```
┌─────────────────────────────────────────────────┐
│  CICLO POR STEP (repetir para CADA step):       │
│                                                 │
│  1. Ler o step Gherkin                          │
│  2. browser_video_chapter com:                  │
│     - title: "Step {NN} - {keyword} {descricao}"│
│     - description: texto completo do step       │
│  3. Traduzir para ação Playwright               │
│  4. Executar no browser (click, fill, assert..) │
│  5. Registrar resultado (✅ ou ❌)              │
│                                                 │
│  ❌ NÃO AVANÇAR PARA O PRÓXIMO STEP SEM        │
│     TER REGISTRADO O CHAPTER NO VÍDEO           │
└─────────────────────────────────────────────────┘
```

**Nomenclatura dos capítulos de vídeo:**

| Step # | Keyword | Título do Chapter |
|--------|---------|-------------------|
| 1 | Given | `Step 01 - Given {descricao-curta}` |
| 2 | When | `Step 02 - When {descricao-curta}` |
| 3 | And | `Step 03 - And {descricao-curta}` |
| 4 | Then | `Step 04 - Then {descricao-curta}` |

> **ℹ️** O vídeo captura automaticamente toda a interação visual, incluindo elementos transientes como toasts, notificações e animações.

### Passo 4 — Evidência Final de Resultado (POR CENÁRIO)

Ao finalizar **TODOS os steps** de um cenário, capturar a evidência final:

#### 📷 Modo Screenshot

Capturar um screenshot final com timestamp:
- Se **PASSED**: `step-final-resultado-passed_{HH}h{MM}m{SS}s.png`
- Se **FAILED**: `step-final-resultado-failed_{HH}h{MM}m{SS}s.png`

Salvar em: `fastqa/manual_test/evidence/TS-{NNN}/`

#### 🎥 Modo Vídeo

1. Chamar `browser_video_chapter` com:
   - `title`: `"Resultado Final - PASSED"` ou `"Resultado Final - FAILED"`
   - `description`: Resumo da execução (total de steps, steps passados/falhados)
2. Chamar `browser_stop_video` para finalizar e salvar o arquivo `.webm`

> **ℹ️ O timestamp do screenshot final (ou do início/fim do vídeo) marca a duração total da execução do cenário.**

**Após concluir o cenário, avançar para o próximo cenário da lista (Passo 2 → 3 → 4) até todos serem executados.**

### Passo 5 — Verificar Evidências (TODOS OS CENÁRIOS)

**ANTES de gerar o relatório**, verificar as evidências de **TODOS** os cenários:

#### 📷 Modo Screenshot

Listar as pastas de evidências para confirmar que TODOS os screenshots foram salvos:

```powershell
"TS-001", "TS-002", "TS-003" | ForEach-Object {
    Write-Host "`n=== $_ ===" -ForegroundColor Cyan
    Get-ChildItem "fastqa/manual_test/evidence/$_/" | Format-Table Name, Length
}
```

> **Se algum screenshot estiver faltando, CAPTURAR NOVAMENTE antes de prosseguir.**

#### 🎥 Modo Vídeo

Verificar que os arquivos `.webm` foram salvos nas pastas de evidências:

```powershell
"TS-001", "TS-002", "TS-003" | ForEach-Object {
    Write-Host "`n=== $_ ===" -ForegroundColor Cyan
    Get-ChildItem "fastqa/manual_test/evidence/$_/" -Filter "*.webm" | Format-Table Name, Length
}
```

> **Se algum arquivo .webm NÃO existir, verificar o `--output-dir` configurado no servidor MCP correspondente e copiar para a pasta de evidências.**

**Após verificar os vídeos, PERGUNTAR ao usuário e AGUARDAR resposta:**

```markdown
⚡ **Deseja gerar versões aceleradas (2x) dos vídeos para revisão rápida?**

1. **Sim** — Gerar versão 2x de TODOS os vídeos (requer `ffmpeg` instalado)
2. **Não** — Manter apenas os vídeos originais
```

> **❌ NÃO PROSSEGUIR SEM A RESPOSTA DO USUÁRIO.**

Se **Sim**, executar para cada cenário:

```powershell
# Gerar versão 2x de todos os vídeos
Get-ChildItem "fastqa/manual_test/evidence/TS-*/" -Filter "*.webm" | Where-Object { $_.Name -notlike "*_2x*" } | ForEach-Object {
    $output = $_.FullName -replace '\.webm$', '_2x.webm'
    ffmpeg -i $_.FullName -filter:v "setpts=0.5*PTS" -an $output
}
```

> **ℹ️** Os arquivos originais são preservados. As versões aceleradas são salvas com sufixo `_2x`. Requer `ffmpeg` instalado (`winget install FFmpeg` ou `choco install ffmpeg`).

---

## 📋 Requisitos de Execução

1. **Assertividade:** Siga EXATAMENTE todos os passos de cada cenário
2. **Validações:** Valide TODAS as condições esperadas (URLs, mensagens, elementos)
3. **Formato de evidência:** Respeitar o modo selecionado pelo usuário (📷 Screenshot ou 🎥 Vídeo) — mesmo modo para TODOS os cenários
4. **Evidências por step:**
   - **📷 Screenshot:** Capture screenshot + `browser_snapshot` para **CADA** step Gherkin
   - **🎥 Vídeo:** Registre um `browser_video_chapter` para **CADA** step Gherkin
5. **Pasta obrigatória:** `fastqa/manual_test/evidence/TS-{NNN}/` — **NUNCA** salvar em outro local
6. **Timeouts:** Use `{ timeout: 30000 }` para ações lentas
7. **Nomenclatura:**
   - **📷 Screenshot:** `step-{NN}-{keyword}-{descricao-curta}_{HH}h{MM}m{SS}s.png`
   - **🎥 Vídeo:** `TS-{NNN}_video_{HH}h{MM}m{SS}s.webm`

---

## 📊 Relatório de Execução

Após a execução de **TODOS** os cenários, gerar o relatório conforme o modo de evidência selecionado:

### 📷 Relatório Consolidado — Modo Screenshot

```markdown
# 📋 RELATÓRIO DE EXECUÇÃO PARALELA

## Resumo
- **Data**: [data/hora]
- **URL**: [url]
- **Formato de Evidência**: 📷 Screenshot
- **Total de cenários**: [N]
- **Aprovados**: [n] ✅
- **Reprovados**: [n] ❌
- **Tempo total**: [tempo]

## Resultados por Cenário
| TS-ID | Cenário | Servidor MCP | Status | Steps | Screenshots | Tempo |
|-------|---------|-------------|--------|-------|-------------|-------|
| TS-001 | [nome] | playwright-parallel-1  | ✅ | 5/5 | 7 | 30s |
| TS-002 | [nome] | playwright-parallel-2 | ❌ | 3/5 | 5 | 45s |
| TS-003 | [nome] | playwright-parallel-3 | ✅ | 4/4 | 6 | 25s |

---

## Detalhamento — TS-001: [nome do cenário]

### Steps Executados
| # | Step | Status | Evidência | Observações |
|---|------|--------|-----------|-------------|
| 1 | Given ... | ✅ | step-01-given-descricao_14h23m07s.png | [textos visíveis] |
| 2 | When ... | ✅ | step-02-when-descricao_14h23m15s.png | |
| 3 | Then ... | ✅ | step-03-then-descricao_14h23m30s.png | Toast: "Sucesso" |

### Arquivos de Evidência
- step-00-navegacao-inicial_14h23m00s.png
- step-01-given-descricao_14h23m07s.png
- ...
- step-final-resultado-passed_14h24m05s.png

---

## Detalhamento — TS-002: [nome do cenário]
[... mesmo formato ...]

## Observações Gerais
- [observações descritivas sobre elementos transientes, mensagens detectadas via browser_snapshot]
```

### 🎥 Relatório Consolidado — Modo Vídeo

```markdown
# 📋 RELATÓRIO DE EXECUÇÃO PARALELA

## Resumo
- **Data**: [data/hora]
- **URL**: [url]
- **Formato de Evidência**: 🎥 Vídeo
- **Total de cenários**: [N]
- **Aprovados**: [n] ✅
- **Reprovados**: [n] ❌
- **Tempo total**: [tempo]

## Resultados por Cenário
| TS-ID | Cenário | Servidor MCP | Status | Steps | Capítulos | Vídeo |
|-------|---------|-------------|--------|-------|-----------|-------|
| TS-001 | [nome] | playwright-parallel-1  | ✅ | 5/5 | 7 | TS-001_video_14h23m00s.webm |
| TS-002 | [nome] | playwright-parallel-2 | ❌ | 3/5 | 5 | TS-002_video_14h23m02s.webm |
| TS-003 | [nome] | playwright-parallel-3 | ✅ | 4/4 | 6 | TS-003_video_14h23m04s.webm |

---

## Detalhamento — TS-001: [nome do cenário]

### Steps Executados (Capítulos do Vídeo)
| # | Step | Status | Capítulo |
|---|------|--------|----------|
| 1 | Given ... | ✅ | Step 01 - Given descricao |
| 2 | When ... | ✅ | Step 02 - When descricao |
| 3 | Then ... | ✅ | Step 03 - Then descricao |

### Arquivo de Vídeo
- TS-001_video_14h23m00s.webm

---

## Detalhamento — TS-002: [nome do cenário]
[... mesmo formato ...]

## Observações Gerais
- [observações]
```

---

## 💾 Saída
Salvar evidências por cenário em: `fastqa/manual_test/evidence/TS-{NNN}/`

> **⚠️ REGRA INVIOLÁVEL:** Todas as evidências **DEVEM** estar dentro de `fastqa/manual_test/evidence/TS-{NNN}/` ao final da execução. Nenhum arquivo de evidência pode ficar na raiz do projeto ou em qualquer outra pasta.

---

## 🔗 Integração com Azure DevOps (Pós-Execução)

Após finalizar a execução de **TODOS** os cenários, **SEMPRE PERGUNTAR** ao usuário:

```markdown
🔄 **Deseja enviar os resultados desta execução para o Azure DevOps?**

O comando @fastqa:azdo_upload_test_execution permite:
- ✅ Criar Test Run (Test Point) automaticamente
- ✅ Anexar todas as evidências capturadas ao Test Result
- ✅ Atualizar status do Test Case (Passed/Failed)
- ✅ Vincular execução ao Test Plan / Suite / Test Case
- ✅ Criar bug automaticamente se o teste falhou

**Opções:**
1. **Sim** - Enviar resultados de TODOS os cenários
2. **Não** - Apenas salvar evidências localmente
3. **Ver parâmetros** - Mostrar como executar manualmente depois
```

### Se usuário escolher "Sim":

1. **Solicitar informações necessárias e AGUARDAR:**
   - **Test Plan ID** (número do plano de testes)
   - **Test Suite ID** (número da suite)
   - **Mapeamento TS → TC** (qual Test Case ID do Azure DevOps corresponde a cada cenário)

   ```markdown
   📋 **Mapeamento dos cenários para Test Cases do Azure DevOps:**

   | TS-ID | Cenário | TC ID (Azure DevOps) | Resultado |
   |-------|---------|---------------------|-----------|
   | TS-001 | [nome] | ? | ✅ Passed |
   | TS-002 | [nome] | ? | ❌ Failed |
   | TS-003 | [nome] | ? | ✅ Passed |

   Informe os Test Case IDs do Azure DevOps para cada cenário.
   ```

2. **Executar script TypeScript para CADA cenário (OBRIGATÓRIO):**
   ```bash
   npx tsx fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts \
     --test-plan-id {valor} \
     --test-suite-id {valor} \
     --test-case-id {tc-id-azdo} \
     --evidence-path "fastqa/manual_test/evidence/TS-{NNN}" \
     --result {Passed|Failed} \
     --comment "Execução paralela via Playwright MCP - [data] - Cenário TS-{NNN}" \
     --auto-bug {true se Failed, false se Passed}
   ```

   > **⚠️ OBRIGATÓRIO:** Usar **SEMPRE** o script TypeScript `upload-test-execution.command.ts`.
   > Este script cria um **Test Run (Test Point)** completo no Azure DevOps, NÃO apenas um attachment.
   > ❌ NÃO usar `upload-evidence.command.ts` para esta finalidade (ele apenas anexa ao Work Item).

3. **O script realiza automaticamente (para CADA cenário):**
   - Obtém Test Point (vinculação Plan → Suite → TC)
   - Cria Test Run no Azure DevOps
   - Obtém Test Result do Run
   - Faz upload de TODAS as evidências da pasta como attachments do Test Result
   - Atualiza o outcome (Passed/Failed/etc.)
   - Finaliza o Test Run com status Completed
   - [Se --auto-bug + Failed] Cria Bug automaticamente vinculado

4. **Exibir confirmação consolidada:**
   ```markdown
   ✅ Execuções enviadas para Azure DevOps!

   | TS-ID | TC (AzDO) | Test Run ID | Outcome | Evidências | Bug |
   |-------|-----------|-------------|---------|------------|-----|
   | TS-001 | #15 | #[ID] | ✅ Passed | 7 arquivos | — |
   | TS-002 | #16 | #[ID] | ❌ Failed | 5 arquivos | #[ID] |
   | TS-003 | #17 | #[ID] | ✅ Passed | 6 arquivos | — |
   ```

### Se usuário escolher "Ver parâmetros":

Mostrar exemplo de como executar depois:
```bash
# Executar para cada cenário individualmente:
npx tsx fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts \
  --test-plan-id 29 \
  --test-suite-id 38 \
  --test-case-id 15 \
  --evidence-path "fastqa/manual_test/evidence/TS-001" \
  --result Passed \
  --comment "Execução paralela via Playwright MCP"
```

### Se usuário escolher "Não":

```markdown
✅ Evidências salvas localmente em:
- fastqa/manual_test/evidence/TS-001/
- fastqa/manual_test/evidence/TS-002/
- fastqa/manual_test/evidence/TS-003/

💡 **Dica:** Você pode enviar para o Azure DevOps depois usando:
npx tsx fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts
```

---

## 🎯 Workflow Completo (Com Azure DevOps)

```
1. Preparação: identificar cenários, carregar Gherkin, obter URL
   ↓
2. Selecionar formato de evidência (📷 Screenshot ou 🎥 Vídeo)
   ↓
3. Atribuir cenários aos servidores MCP (tabela de atribuição)
   ↓
4. Criar pastas fastqa/manual_test/evidence/TS-{NNN}/ (todas de uma vez)
   ↓
5. Para CADA cenário (sequencialmente):
   a. Navegar no servidor MCP atribuído
   b. Executar steps com evidência POR STEP:
      - 📷 Screenshot: browser_take_screenshot + browser_snapshot
      - 🎥 Vídeo: browser_video_chapter por step
   c. Capturar evidência final (passed/failed)
   ↓
6. Verificar que TODAS as evidências estão nas pastas
   ↓
7. Gerar relatório consolidado + detalhamento por cenário
   ↓
8. Perguntar sobre upload Azure DevOps
   ↓
9. Se Sim: npx tsx upload-test-execution.command.ts (para cada cenário)
   ↓
10. Test Runs criados + Evidências nos Test Results + Status atualizado
```

---

## 🔄 Continuidade da Jornada

Após concluir este comando, siga as regras de continuidade:

1. **Leia** `fastqa/scripts/journey_state.json`
2. **Se `active_journey` não é null** (jornada ativa):
   - Marque o step atual como `"completed"` no array `steps`
   - Adicione artefatos produzidos ao `artifacts_produced`
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