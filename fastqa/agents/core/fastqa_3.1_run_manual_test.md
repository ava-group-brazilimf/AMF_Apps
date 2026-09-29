---
name: "fastqa_3.1_run_manual_test"
description: "Executor de cenários Gherkin via Playwright MCP com captura de evidências POR STEP (Screenshot ou Vídeo)"

tools:
  - playwright (mcp)
  - memory
  - sequential-thinking
---

# 🚀 Executor de Teste Manual com Playwright MCP

## 📋 Objetivo
Execute **manualmente** um cenário de teste utilizando o Playwright MCP. O teste é executado interpretando a linguagem natural (Gherkin) e traduzindo para ações no browser em tempo real.

O usuário pode escolher entre dois formatos de evidência:
- **📷 Screenshot** — Captura de imagem estática por step (padrão)
- **🎥 Vídeo** — Gravação contínua com capítulos por step (requer `--caps=devtools`)

**⚠️ ATENÇÃO:** Este prompt é para **EXECUÇÃO MANUAL** via Playwright MCP, **NÃO** para criar scripts automatizados. Os cenários são executados via linguagem natural.

---

## ⚙️ Pré-requisitos

### 1. Servidor MCP (`.vscode/mcp.json`)
```json
{
  "servers": {
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--viewport-size=1366,768",
        "--caps=devtools"
      ]
    }
  }
}
```

> **ℹ️ `--caps=devtools`** habilita as ferramentas `browser_start_video`, `browser_stop_video` e `browser_video_chapter`, necessárias para o modo de evidência em **Vídeo**. Pode ser mantido mesmo quando o modo Screenshot for selecionado — não causa nenhum impacto.

### 2. Estrutura de Diretórios
A pasta de evidências será criada **AUTOMATICAMENTE** no passo 1 do Fluxo de Execução.

---

## 🎯 Fluxo de Execução

> **⚠️ REGRA CRÍTICA DE EVIDÊNCIAS:**
> - **Modo 📷 Screenshot:** Cada step Gherkin executado **DEVE** gerar **obrigatoriamente** um screenshot salvo na pasta `fastqa/manual_test/evidence/TC-{ID}/`.
> - **Modo 🎥 Vídeo:** A gravação de vídeo contínua com capítulos por step **substitui** screenshots individuais. Cada step gera um `browser_video_chapter` no vídeo.
>
> Se a pasta NÃO existir, **CRIE-A** antes de iniciar qualquer step.

### Passo 0 — Preparação

1. Solicitar ao usuário a identificação do **Test Case** (ex: TC-15) e **AGUARDAR** resposta
2. Carregar cenário Gherkin de `fastqa/manual_test/test_cases/`
3. Solicitar **URL** da aplicação e **AGUARDAR** resposta
4. Solicitar o **formato de evidência** e **AGUARDAR** resposta:

```markdown
📸 **Selecione o formato de captura de evidências:**

1. 🎥 **Vídeo** — Gravação contínua com capítulos por step (arquivo .webm)
   - Captura toda a interação visual, ideal para toasts e animações
   - Requer `--caps=devtools` no servidor MCP

2. 📷 **Screenshot** — Captura de imagem por step (arquivos .png)
   - Uma imagem por step Gherkin (padrão atual)
   - Recomendado usar `browser_snapshot` complementar para registrar textos visíveis
```

> **❌ NÃO PROSSEGUIR SEM A RESPOSTA DO USUÁRIO.**
> A escolha define o `MODO DE EVIDÊNCIA` utilizado em todos os passos seguintes.

### Passo 1 — Criar Pasta de Evidências (OBRIGATÓRIO)

**ANTES de qualquer navegação no browser**, crie a pasta de evidências:

```
fastqa/manual_test/evidence/TC-{ID}/
```

Exemplo: se o Test Case é TC-15, criar `fastqa/manual_test/evidence/TC-15/`.

**Comando para criar a pasta (usar run_in_terminal):**
```bash
mkdir -p fastqa/manual_test/evidence/TC-{ID}
```
ou no PowerShell:
```powershell
New-Item -ItemType Directory -Path "fastqa/manual_test/evidence/TC-{ID}" -Force
```

> **❌ NÃO PROSSEGUIR SEM CRIAR A PASTA.**
> **❌ NÃO SALVAR evidências na raiz do projeto.**
> **❌ NÃO SALVAR evidências em outra pasta que não seja `fastqa/manual_test/evidence/TC-{ID}/`.**

### Passo 2 — Navegar até a URL

1. Utilizar `browser_navigate` para acessar a URL informada
2. **IMEDIATAMENTE** após a navegação, capturar a primeira evidência conforme o modo selecionado:

#### 📷 Modo Screenshot

**Regra de captura de screenshot:**
- Usar `browser_take_screenshot` do Playwright MCP
- **MOVER ou RENOMEAR** o arquivo gerado para a pasta de evidências com o nome correto
- Se o `browser_take_screenshot` salvar o arquivo em outro local, **copie-o** para a pasta de evidências usando `run_in_terminal`
- **Complementar** com `browser_snapshot` para registrar textos visíveis na tela (títulos, mensagens, labels)

**Nome do arquivo:** `step-00-navegacao-inicial_{HH}h{MM}m{SS}s.png`
**Caminho completo:** `fastqa/manual_test/evidence/TC-{ID}/step-00-navegacao-inicial_{HH}h{MM}m{SS}s.png`

> **ℹ️ TIMESTAMP:** Capturar horário exato no momento da navegação (formato `14h23m07s`) e inserir como sufixo no nome do arquivo. Use `Get-Date -Format 'HHhmmmsss'` (PowerShell) ou `date +%Hh%Mm%Ss` (Bash) para obter o valor.

#### 🎥 Modo Vídeo

1. Obter timestamp: `$ts = Get-Date -Format 'HHhmmss'` → formatar como `HHhMMmSSs`
2. Chamar `browser_start_video` com:
   - `filename`: `TC-{ID}_video_{HH}h{MM}m{SS}s.webm`
3. Chamar `browser_video_chapter` com:
   - `title`: `"Navegação Inicial"`
   - `description`: URL acessada

> **ℹ️** O vídeo será salvo no `--output-dir` configurado no servidor MCP. Não é necessário mover o arquivo manualmente.

### Passo 3 — Executar Steps Gherkin (COM EVIDÊNCIA POR STEP)

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
│     fastqa/manual_test/evidence/TC-{ID}/        │
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
Move-Item -Path "screenshot-gerado.png" -Destination "fastqa/manual_test/evidence/TC-{ID}/step-{NN}-{keyword}-{descricao}_${ts}.png" -Force
```

```bash
# Bash — obter timestamp e mover screenshot para pasta de evidências
ts=$(date +%Hh%Mm%Ss)
mv screenshot-gerado.png fastqa/manual_test/evidence/TC-{ID}/step-{NN}-{keyword}-{descricao}_${ts}.png
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

### Passo 4 — Evidência Final de Resultado

#### 📷 Modo Screenshot

Ao final de TODOS os steps, capturar um screenshot final com timestamp:
- Se **PASSED**: `step-final-resultado-passed_{HH}h{MM}m{SS}s.png`
- Se **FAILED**: `step-final-resultado-failed_{HH}h{MM}m{SS}s.png`

Salvar em: `fastqa/manual_test/evidence/TC-{ID}/`

#### 🎥 Modo Vídeo

Ao final de TODOS os steps:
1. Chamar `browser_video_chapter` com:
   - `title`: `"Resultado Final - PASSED"` ou `"Resultado Final - FAILED"`
   - `description`: Resumo da execução (total de steps, steps passados/falhados)
2. Chamar `browser_stop_video` para finalizar e salvar o arquivo `.webm`

> **ℹ️ O timestamp do screenshot final (ou do início/fim do vídeo) marca a duração total da execução.**

### Passo 5 — Verificar Evidências

**ANTES de gerar o relatório**, verificar as evidências conforme o modo selecionado:

#### 📷 Modo Screenshot

Listar a pasta de evidências para confirmar que TODOS os screenshots foram salvos:

```powershell
Get-ChildItem "fastqa/manual_test/evidence/TC-{ID}/" | Format-Table Name, Length
```

> **Se algum screenshot estiver faltando, CAPTURAR NOVAMENTE antes de prosseguir.**

#### 🎥 Modo Vídeo

Verificar que o arquivo `.webm` foi salvo na pasta de evidências:

```powershell
Get-ChildItem "fastqa/manual_test/evidence/TC-{ID}/" -Filter "*.webm" | Format-Table Name, Length
```

 **Se o arquivo .webm NÃO existir, verificar o `--output-dir` configurado no servidor MCP e copiar para a pasta de evidências.**

**Após verificar o vídeo, PERGUNTAR ao usuário e AGUARDAR resposta:**

```markdown
⚡ **Deseja gerar uma versão acelerada (2x) do vídeo para revisão rápida?**

1. **Sim** — Gerar versão 2x (requer `ffmpeg` instalado)
2. **Não** — Manter apenas o vídeo original
```

> **❌ NÃO PROSSEGUIR SEM A RESPOSTA DO USUÁRIO.**

Se **Sim**, executar:

```powershell
ffmpeg -i "fastqa/manual_test/evidence/TC-{ID}/TC-{ID}_video_{HH}h{MM}m{SS}s.webm" -filter:v "setpts=0.5*PTS" -an "fastqa/manual_test/evidence/TC-{ID}/TC-{ID}_video_{HH}h{MM}m{SS}s_2x.webm"
```

> **ℹ️** O arquivo original é preservado. A versão acelerada é salva com sufixo `_2x`. Requer `ffmpeg` instalado (`winget install FFmpeg` ou `choco install ffmpeg`).

---

## 📋 Requisitos de Execução

1. **Assertividade:** Siga EXATAMENTE todos os passos do cenário
2. **Validações:** Valide TODAS as condições esperadas (URLs, mensagens, elementos)
3. **Formato de evidência:** Respeitar o modo selecionado pelo usuário (📷 Screenshot ou 🎥 Vídeo)
4. **Evidências por step:**
   - **📷 Screenshot:** Capture screenshot + `browser_snapshot` para **CADA** step Gherkin
   - **🎥 Vídeo:** Registre um `browser_video_chapter` para **CADA** step Gherkin
5. **Pasta obrigatória:** `fastqa/manual_test/evidence/TC-{ID}/` — **NUNCA** salvar em outro local
6. **Timeouts:** Use `{ timeout: 30000 }` para ações lentas
7. **Nomenclatura:**
   - **📷 Screenshot:** `step-{NN}-{keyword}-{descricao-curta}_{HH}h{MM}m{SS}s.png`
   - **🎥 Vídeo:** `TC-{ID}_video_{HH}h{MM}m{SS}s.webm`

---

## 📊 Relatório de Execução

Após a execução, gerar o relatório conforme o modo de evidência selecionado:

### 📷 Relatório — Modo Screenshot

```markdown
# 📋 RELATÓRIO DE EXECUÇÃO MANUAL - TC-{ID}

## Cenário: [nome do cenário]
- **Data**: [data/hora]
- **URL**: [url]
- **Test Case ID**: TC-{ID}
- **Formato de Evidência**: 📷 Screenshot
- **Resultado**: ✅ PASSED | ❌ FAILED
- **Total de Steps**: [N]
- **Screenshots Capturados**: [N]

## Steps Executados
| # | Step | Status | Evidência | Observações |
|---|------|--------|-----------|-------------|
| 1 | Given ... | ✅ | step-01-given-descricao_14h23m07s.png | [textos visíveis, toasts detectados] |
| 2 | When ... | ✅ | step-02-when-descricao_14h23m15s.png | |
| 3 | And ... | ✅ | step-03-and-descricao_14h23m22s.png | |
| 4 | Then ... | ✅ | step-04-then-descricao_14h23m30s.png | Toast exibido: "Salvo com sucesso" |

## Pasta de Evidências
`fastqa/manual_test/evidence/TC-{ID}/`

## Arquivos de Evidência
- step-00-navegacao-inicial_14h23m00s.png
- step-01-given-descricao_14h23m07s.png
- step-02-when-descricao_14h23m15s.png
- step-03-and-descricao_14h23m22s.png
- step-04-then-descricao_14h23m30s.png
- step-final-resultado-passed_14h24m05s.png

## Observações
- [observações descritivas sobre elementos transientes, mensagens detectadas via browser_snapshot]
```

### 🎥 Relatório — Modo Vídeo

```markdown
# 📋 RELATÓRIO DE EXECUÇÃO MANUAL - TC-{ID}

## Cenário: [nome do cenário]
- **Data**: [data/hora]
- **URL**: [url]
- **Test Case ID**: TC-{ID}
- **Formato de Evidência**: 🎥 Vídeo
- **Resultado**: ✅ PASSED | ❌ FAILED
- **Total de Steps**: [N]
- **Capítulos no Vídeo**: [N]

## Steps Executados (Capítulos do Vídeo)
| # | Step | Status | Capítulo |
|---|------|--------|----------|
| 1 | Given ... | ✅ | Step 01 - Given descricao |
| 2 | When ... | ✅ | Step 02 - When descricao |
| 3 | And ... | ✅ | Step 03 - And descricao |
| 4 | Then ... | ✅ | Step 04 - Then descricao |

## Pasta de Evidências
`fastqa/manual_test/evidence/TC-{ID}/`

## Arquivo de Vídeo
- TC-{ID}_video_{HH}h{MM}m{SS}s.webm

## Observações
- [observações]
```

---

## 💾 Saída
Salvar evidências em: `fastqa/manual_test/evidence/TC-{ID}/`

> **⚠️ REGRA INVIOLÁVEL:** Todas as evidências **DEVEM** estar dentro de `fastqa/manual_test/evidence/TC-{ID}/` ao final da execução. Nenhum arquivo de evidência pode ficar na raiz do projeto ou em qualquer outra pasta.

---

## 🔗 Integração com Azure DevOps (Pós-Execução)

Após finalizar a execução do teste manual, **SEMPRE PERGUNTAR** ao usuário:

```markdown
🔄 **Deseja enviar o resultado desta execução para o Azure DevOps?**

O comando @fastqa:azdo_upload_test_execution permite:
- ✅ Criar Test Run (Test Point) automaticamente
- ✅ Anexar todas as evidências capturadas ao Test Result
- ✅ Atualizar status do Test Case (Passed/Failed)
- ✅ Vincular execução ao Test Plan / Suite / Test Case
- ✅ Criar bug automaticamente se o teste falhou

**Opções:**
1. **Sim** - Enviar resultado agora
2. **Não** - Apenas salvar evidências localmente
3. **Ver parâmetros** - Mostrar como executar manualmente depois
```

### Se usuário escolher "Sim":

1. **Solicitar informações necessárias e AGUARDAR:**
   - **Test Plan ID** (número do plano de testes)
   - **Test Suite ID** (número da suite)
   - **Test Case ID** (número do test case no Azure DevOps — pode ser diferente do TC-{ID} local)
   - **Resultado** (Passed | Failed | Blocked | NotApplicable)
   - **[Opcional]** Comentário sobre a execução

2. **Executar script TypeScript (OBRIGATÓRIO):**
   ```bash
   npx tsx fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts \
     --test-plan-id {valor} \
     --test-suite-id {valor} \
     --test-case-id {valor} \
     --evidence-path "fastqa/manual_test/evidence/TC-{ID}" \
     --result {Passed|Failed} \
     --comment "Execução manual via Playwright MCP - [data]" \
     --auto-bug {true se Failed, false se Passed}
   ```

   > **⚠️ OBRIGATÓRIO:** Usar **SEMPRE** o script TypeScript `upload-test-execution.command.ts`.
   > Este script cria um **Test Run (Test Point)** completo no Azure DevOps, NÃO apenas um attachment.
   > ❌ NÃO usar `upload-evidence.command.ts` para esta finalidade (ele apenas anexa ao Work Item).

3. **O script realiza automaticamente:**
   - Obtém Test Point (vinculação Plan → Suite → TC)
   - Cria Test Run no Azure DevOps
   - Obtém Test Result do Run
   - Faz upload de TODAS as evidências da pasta como attachments do Test Result
   - Atualiza o outcome (Passed/Failed/etc.)
   - Finaliza o Test Run com status Completed
   - [Se --auto-bug + Failed] Cria Bug automaticamente vinculado

4. **Exibir confirmação:**
   ```markdown
   ✅ Execução enviada para Azure DevOps!

   - **Test Run ID:** #[ID]
   - **Test Result ID:** #[ID]
   - **Outcome:** [Passed/Failed]
   - **Evidências anexadas:** [quantidade] arquivos
   - **Bug criado:** #[ID] (se Failed + auto-bug)

   🔗 Ver Test Run: [URL]
   ```

### Se usuário escolher "Ver parâmetros":

Mostrar exemplo de como executar depois:
```bash
npx tsx fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts \
  --test-plan-id 29 \
  --test-suite-id 38 \
  --test-case-id 15 \
  --evidence-path "fastqa/manual_test/evidence/TC-15" \
  --result Passed \
  --comment "Execução manual via Playwright MCP"
```

### Se usuário escolher "Não":

```markdown
✅ Evidências salvas localmente em: fastqa/manual_test/evidence/TC-{ID}/

💡 **Dica:** Você pode enviar para o Azure DevOps depois usando:
npx tsx fastqa/scripts/azure-devops/commands/upload-test-execution.command.ts
```

---

## 🎯 Workflow Completo (Com Azure DevOps)

```
1. Preparação: identificar TC, carregar Gherkin, obter URL
   ↓
2. Selecionar formato de evidência (📷 Screenshot ou 🎥 Vídeo)
   ↓
3. Criar pasta fastqa/manual_test/evidence/TC-{ID}/
   ↓
4. Executar teste manual (@fastqa:run_manual_test)
   ↓
5. Capturar evidência POR STEP:
   - 📷 Screenshot: browser_take_screenshot + browser_snapshot
   - 🎥 Vídeo: browser_video_chapter por step
   ↓
6. Verificar que TODAS as evidências estão na pasta
   ↓
7. Gerar relatório de execução
   ↓
8. Perguntar sobre upload Azure DevOps
   ↓
9. Se Sim: npx tsx upload-test-execution.command.ts
   ↓
10. Test Run criado + Evidências no Test Result + Status atualizado
```

---

## 🔄 Continuidade da Jornada

Após concluir este comando, siga as regras de continuidade:

1. **Leia** `fastqa/scripts/journey_state.json`
2. **Se `active_journey` não é null** (jornada ativa):
   - Marque o step atual como `"completed"` no array `steps`
   - Adicione artefatos produzidos ao `artifacts_produced` (ex: `manual_test/evidence/TC-{ID}/`)
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
