# Agent Implementation Plan: Isolamento de Janela por Agente + Context Engineering

**Spec**: `specs/033-agent-isolation-context-engineering/spec.md`
**Tech Stack**: See `src/shared/data/reference-architecture.yaml` (v1.0.0) — do not hardcode versions.
**Runtime facts**: `docs/copilot-cli-runtime-facts.md` (M0, medido — não estimado)

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | — (nenhum agente novo; muda a invocação dos 102 despacháveis) |
| **Phase** | `F1` como padrão de referência; wrappers gerados para F1–F8 |
| **Module** | `asis-diagnostic` (validação) + `src/shared/tools` (infraestrutura) |
| **Primary Requirement** | Cada agente invocado pelo orquestrador de fase roda em janela de contexto própria, sem mudar o modo de execução via CLI |
| **Technical Approach** | `AGENTS.md` como fonte única de guardrails (carregado nativamente + injetado nos wrappers) · 102 `.agent.md` gerados do `agent_registry` · orquestrador troca N dispatches in-prompt por **uma** chamada ao `agent_runner.py`, que faz spawn de `copilot -p --agent` por nó · context pack determinístico em disco · hook `preToolUse` como enforcement |

---

## Constitution Check

*GATE: passou antes da Phase 0. Re-checar após a Phase 1. Falhas justificadas na seção 9.*

### Constitution Gates

| Artigo | Gate | Status |
|---|---|---|
| **I** | Nenhuma versão de tecnologia hardcoded | ✅ `AGENTS.md` é language-agnostic por construção e guardado por `validate_language_agnostic.py`; o wire model vem do env BYOK, não do prompt |
| **II** | Frontmatter das specs canônicas contém só `name`, `version`, `description`, `allowed-tools` | ⚠️ **Ver §9** — as specs canônicas ficam intactas; os `.agent.md` são artefatos gerados sob o schema do CLI, que **descarta** `version`/`allowed-tools` |
| **II** | `name` casa `^ava-[a-z0-9-]+$` | ✅ herdado do `agent_registry`; teste afirma nos 102 wrappers |
| **III** | Colocação de fase válida; `ava-summary` após toda fase | ✅ o runner é **intra-fase**; a sequência F1→ava-summary→F2 não é tocada |
| **IV** | Diff do `module.yaml` de módulo preparado | ✅ **N/A** — nenhum agente novo, nenhuma entrada nova |
| **V** | Corpo do agente em pt-BR | ✅ `AGENTS.md`, corpos de wrapper, docstrings e mensagens em pt-BR |
| **VI** | Cenários BDD (nominal + edge + gate) | ✅ 11 cenários na seção 4 da spec |
| **VII** | Impacto no sub-pipeline de segurança avaliado | ✅ os 8 agentes de `agents/security/` ganham wrapper como os demais; `ava-asis-security-orchestrator` continua no DAG e não é contornado |
| **VIII** | Propagação de `trace_id` documentada | ✅ ver seção 6 — `project-config.yaml` → envelope → pack → artefato, sem mutação |
| **IX** | Ordenação de camadas Clean Architecture | ✅ **N/A** — os agentes são arquivos de prompt LLM; ver seção 3 |
| **X** | Tipo de bump determinado | ✅ `orchestrator-asis.md` **MAJOR** (o contrato de dispatch muda); os demais agentes **sem bump** (não são editados) |
| **XI** | Split Skill/Agent declarado | ✅ os 75 `SKILL.md` continuam sendo a entrada humana; os `.agent.md` são a entrada do runner. Ver seção 4 |

### Quality Gate Check

- [x] Nenhum marcador `[NEEDS CLARIFICATION]` na spec
- [x] Todas as saídas seguem `projects/{project_name}/outputs/[phase]/…` (o pack fica em
      `projects/{project_name}/outputs/.context/`, dentro da convenção)
- [x] `next_agent` downstream confirmado — o encadeamento entre fases não muda

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Runtime de execução | GitHub Copilot CLI **≥ 1.0.77** | `docs/copilot-cli-runtime-facts.md` |
| Janela de contexto | **128.000** tokens | M0 § 1 — 75 ocorrências de `tokenLimit`, todas 128000 |
| Overhead estático (runner) | **10.938** tokens | facts § 10 — re-medido com os 102 wrappers e `--excluded-tools=skill,task` |
| Orçamento útil por processo | **~109.062** | 128.000 − 10.938 − ~8.000 de reserva |
| Provider | BYOK Anthropic → Azure AI Foundry, wire model `claude-sonnet-4-6` | `copilot-cli-headroom.bat` L44–83 |
| Modelo pinado por nó | `claude-sonnet-4` (nunca `auto`) | M0 § P-5.1 — sem pin, cai em `gpt-5.4` e 404 |
| Rota | **direta**; via proxy só após o shim de `/v1/models/{id}` | M0 § 7 |
| Ferramentas do agente | `view`, `create`, `edit`, `glob`, `grep`, `powershell` | M0 § 5 — nomes reais das tools |
| Tools excluídas no processo isolado | `skill`, `task` | facts § 10.2 — `task` carrega o catálogo dos 102 agentes (−12.394) |
| Linguagem do código novo | Python 3, stdlib primeiro, imports pesados defensivos | convenção do repo |
| Shell alvo | PowerShell (Windows) — `taskkill /T /F` | M0; R10 |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`
(novo campo `execution_backend: inprompt | process`, default `inprompt`).

---

## 2. Phase Placement

Sequência do pipeline preservada — esta mudança é **intra-fase**, não altera a ordem:

```
F1 -> ava-summary -> F2 -> ava-summary -> F3 -> ava-summary
                                       -> F5 -> ava-summary
                                       -> F7 -> ava-summary
                                       -> F6 -> ava-summary (FINAL)
```

O que muda **dentro** da F1:

```
ANTES                                   DEPOIS
ava-asis-orchestrator (193.848 chars)   ava-asis-orchestrator (~15 KB)
  └ DISPATCH @a  (in-prompt)              └ powershell: agent_runner.py --phase F1
  └ DISPATCH @b  (in-prompt)                   ├ copilot -p --agent a   ← janela própria
  └ DISPATCH @c  (in-prompt)                   ├ copilot -p --agent b   ← janela própria
  = 761K acumulados numa janela de 128K        └ copilot -p --agent c   ← janela própria
```

**Quality gate nesta fase**: `security_gate` (F1) — inalterado. O `ava-asis-security-orchestrator`
continua sendo um nó do DAG.

Condições para `human_gate_required: true` — inalteradas. Acrescenta-se apenas:
- `config_error` num nó (404 de modelo) → **aborta a fase**, não retenta (é BYOK mal configurado).
- `context_overflow` detectado (`session.compaction_start` ou `session.truncation`) → sinaliza no
  relatório mesmo que o nó tenha "passado", porque é a assinatura exata da ISSUE-002.

---

## 3. Clean Architecture Alignment

```
Domain         -> NO
Application    -> NO
Infrastructure -> NO
Presentation   -> NO
```

**N/A** — os agentes são arquivos de prompt LLM (`.md`), não código gerado. A Clean Architecture
aplica-se aos artefatos de código produzidos na F3 (codegen), fora do escopo desta spec.
As ferramentas Python novas (`generate_agent_wrappers.py`, `context_pack.py`,
`pretooluse_guard.py`) são utilitários de esteira e seguem a convenção existente de
`src/shared/tools/` — stdlib primeiro, imports pesados defensivos, degradar nunca quebrar.

Cross-layer coupling: **NONE**.

---

## 4. Agent File Structure

Split de três camadas — **nenhuma delas é fonte duplicada de conteúdo de domínio**:

```
AGENTS.md                                    <- guardrails gerais, language-agnostic (FONTE ÚNICA)

.github/skills/ava-{phase}-{role}/
└── SKILL.md                                 <- entrada HUMANA (75, inalterados)

.github/agents/ava-{phase}-{role}.agent.md   <- entrada do RUNNER (102, GERADOS)
                                                frontmatter + AGENTS-CORE injetado + ponteiro

src/modules/ava-fabric-agents/{module}/agents/
└── {role}.md                                <- FONTE ÚNICA do conteúdo de domínio (inalterada)
```

**Frontmatter do `.agent.md`** (schema do Copilot CLI, verificado no M0):

```yaml
---
name: ava-asis-inventory
description: <do agent_registry, pt-BR>
tools: ["view", "create", "edit", "glob", "grep", "powershell"]
model: claude-sonnet-4
target: github-copilot
user-invocable: true
metadata: {version: "1.6.1", phase: "F1", module: "asis-diagnostic"}
---
```

Campos aceitos pelo CLI: `description` (obrigatório), `name`, `tools`, `model`, `target`,
`disable-model-invocation`, `user-invocable`, `mcp-servers`, `metadata`.
Campos **descartados** com warning: `version`, `allowed-tools`.

**Mapa de tools** (`TOOL_NAME_MAP`, hoje em `agent_runner.py:81` sem uso — move para o gerador):

| Frontmatter da spec | Tool real do CLI |
|---|---|
| `Read` | `view` |
| `Write` | `create` |
| `Edit` | `edit` |
| `Glob` | `glob` |
| `Grep` | `grep` |
| `Bash` | **`powershell`** |
| `WebFetch` / `WebSearch` | `web_fetch` / `web_search` |

**Dispatch mode**: híbrido — `user-invocable: true` (picker `/agent` e `--agent`) **e**
model-invocable (delegação nativa). A produção usa o runner.

**Shared resources**: `AGENTS.md` · `agent_registry.py` · `artifact_gate.ARTIFACT_CONTRACTS` ·
`context_budget.AGENT_ARTIFACT_SLICE` · `headroom_context.build_agent_context()` ·
`shared/batch-write-protocol.md` · **novo** `shared/context-pack-protocol.md`.

---

## 5. module.yaml Impact

**Nenhum.** Não há agente novo. Os 102 já estão registrados nos `module.yaml` de módulo, e o
`agent_registry.py` deriva o catálogo do disco — os wrappers são artefatos gerados, não agentes.

Arquivos de dados que mudam, sem serem `module.yaml`:

```
src/shared/data/pipeline-dag/F1.yaml        # 3 nós (wave2) -> DAG F1 completo
projects/{p}/context/project-config.yaml    # + execution_backend: inprompt | process
```

---

## 6. Observability & Trace Propagation

Esta spec **usa** o pipeline de observabilidade, então a seção não é N/A.

```
project-config.yaml.trace_id
  └→ agent_runner.build_envelope()      "Vars: … trace_id={trace_id} …"
      └→ context-pack.md (cabeçalho)
          └→ artefato produzido pelo agente
```

Sem mutação em nenhum salto (Art. VIII).

**A telemetria passa a vir do processo, não de um literal copiado à mão.** `session.shutdown` entrega
de graça exatamente o que `pipeline_observer track` pede hoje via bloco `Bash:` em ~206 lugares:
`modelMetrics.*.usage.inputTokens/outputTokens`, `totalApiDurationMs`, `codeChanges.filesModified`,
`systemTokens`, `toolDefinitionsTokens`.

**Contradição viva a resolver no mesmo commit:** `verify_agent_observability.py` (+ CI
`validate-agent-observability.yml`) **exige** os blocos `track` à mão, enquanto o wrapper e o
envelope mandam o agente **não** executá-los. Sequência segura:

1. `pipeline_observer track` vira **idempotente por `(run_id, agent_id, attempt)`** — a linha do
   runner e a do agente não podem contar duas vezes.
2. O runner emite `track` com tokens e duração **reais** de `session.shutdown`.
3. `verify_agent_observability.py` passa a aceitar a omissão para agente migrado (`E*` vira
   condicional), atualizado **no mesmo commit** — deletar em massa deixaria o CI vermelho e a fase
   cega.

`headroom_tool.py attribute` continua funcionando; as janelas de execução ficam **mais** precisas
porque `start_time` deixa de ser igual a `end_time`.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| `agent-task.schema.json` | **NO** | o runner não usa o pipeline de schema JSON |
| `agent-result.schema.json` | **NO** | idem |
| `pipeline-dag/F{N}.yaml` | **YES (novo formato)** | contrato versionado (`version: 1`); documentado em `contracts/pipeline-dag.schema.md` |
| `.agent.md` frontmatter | **YES (novo contrato)** | schema do Copilot CLI; documentado em `contracts/agent-wrapper.schema.json` |
| `context-pack.md` | **YES (novo contrato)** | documentado em `contracts/context-pack.schema.md` |
| `project-config.yaml` | **MINOR** | campo opcional `execution_backend`; ausência ≡ `inprompt` ≡ comportamento atual |

---

## 8. Implementation Phases

**Phase 0 — Fundação (M1).** `AGENTS.md` na raiz (≤ 8 KB, language-agnostic, delimitadores
`AGENTS-CORE`); `generate_agent_wrappers.py` alimentado pelo `agent_registry`; gerar os 102
wrappers; `validate_language_agnostic.py`; `tests/tools/test_agent_wrappers.py` e
`tests/utils/test_validate_language_agnostic.py` (nesses diretórios de propósito: o CHK-04 do
`validate-agent-observability.yml` já coleta `tests/tools` e `tests/utils`, então o gate vale desde
o M1 sem tocar no CI).

**Phase 1 — Contexto (M2).** `context_pack.py` reusando `headroom_context.build_agent_context()`;
gate de orçamento com degradação para query-only registrada; `shared/context-pack-protocol.md`;
`.github/hooks/ava-guardrails.json` + `hooks/pretooluse_guard.py`.

**Phase 2 — Orquestração (M3).** `F1.yaml` completo; `tests/test_pipeline_dag.py` (equivalência de
**conteúdo** com as três fontes existentes); paralelismo (`max_parallel`); escada de retry;
`execution_backend`; `BENIGN_LOG_PATTERNS` em uso.

**Phase 3 — Encolhimento e correções (M4).** `orchestrator-asis.md` → ~15 KB;
`tests/test_agent_body_size.py`; bugs de `project-config.yaml` (L9 malformada, `quality_gates`
duplicado) e de `run_ast_analysis._ensure_manifest_metrics`; `track` idempotente +
`verify_agent_observability.py` no mesmo commit.

**Phase 4 — Registro (M5).** `docs/plan/*.md` redirecionados para esta spec; `CHANGELOG.md`;
`docs/agents-catalog.md`; `.azure-pipelines/validate-agent-observability.yml` com os paths e testes
novos.

---

## 9. Complexity Tracking

| Gate | Failure Reason | Justification | Mitigating Controls |
|---|---|---|---|
| **Artigo II** — frontmatter só com `name`/`version`/`description`/`allowed-tools` | Os `.github/agents/*.agent.md` usam `tools:`, `model:`, `target:`, `metadata:` e **não** têm `version:` | O schema do Copilot CLI **descarta** `version` e `allowed-tools` (`unknown fields ignored`, verificado no M0) e **enforça** `tools`. Cumprir o Artigo II ao pé da letra produziria wrappers sem restrição de tool e sem versão — exatamente o oposto da intenção do Artigo. **Posição:** o Artigo II governa as specs canônicas em `src/modules/.../agents/*.md`, que ficam **inalteradas**; os wrappers são artefatos **gerados** governados pelo schema do CLI | Nenhuma spec canônica é editada · a versão é preservada em `metadata.version`, derivada do frontmatter canônico (que continua sendo a autoridade, Art. II) · `test_agent_wrappers.py` afirma o schema · o gerador é a única forma de produzir wrapper (`--check` reprova drift no CI) · **proposta de emenda**: o Artigo II ganha a frase de escopo *"aplica-se às specs canônicas de agente; wrappers gerados seguem o schema da superfície de execução"* — a ser levada em `/speckit.constitution` numa mudança separada |
| **Artigo X** — bump de versão | `orchestrator-asis.md` recebe **MAJOR** e perde ~92% do corpo | O contrato de dispatch muda de in-prompt para invocação de processo — é breaking por definição | `CHANGELOG.md` com nota de migração · `execution_backend: inprompt` (default) preserva o caminho atual bit a bit · rollback = parar de invocar o runner |
| **Risco R1** — quarta fonte de verdade | `F1.yaml` duplica `slice` e `outputs` que já existem em `AGENT_ARTIFACT_SLICE` e `ARTIFACT_CONTRACTS` | O DAG precisa ser legível por runner **e** por CI; embutir Python nas specs não é opção | `tests/test_pipeline_dag.py` compara **conteúdo**, não presença · `validate_dag()` já falha na carga · CI coleta o teste |

---

## 10. Test Strategy

| Test Type | Tool | Target |
|---|---|---|
| Formato dos wrappers | `pytest tests/tools/test_agent_wrappers.py` | 102/102: `name` casa o padrão, `tools` presente e mapeado, `version`/`allowed-tools` **ausentes**, corpo < 30.000 chars, bloco `AGENTS-CORE` byte-idêntico a `AGENTS.md` |
| Drift do gerador | `generate_agent_wrappers.py --check` (CI) | exit 1 se algum wrapper divergir do que o `agent_registry` produziria |
| Anti-divergência do DAG | `pytest tests/test_pipeline_dag.py` | `dag.nodes ≡ ARTIFACT_CONTRACTS ≡ agent_registry.catalog()`; `dag[n].slice ≡ AGENT_ARTIFACT_SLICE[n]`; aciclicidade |
| Cap de corpo | `pytest tests/test_agent_body_size.py` | hard ≤ 30.000 chars nos wrappers |
| Language-agnostic | `validate_language_agnostic.py --report` → `--strict` | 0 violações em `AGENTS.md` + `.github/agents/` |
| Determinismo do pack | `pytest` + `Compare-Object` | dois builds consecutivos → bytes idênticos |
| Orçamento | `pytest` | fatia acima do budget → pack degradado, decisão registrada, tamanho abaixo do limite |
| Enforcement (CA07) | sonda manual + `events.jsonl` | `view` em `ast-raw/` negado; `hook.start`/`hook.end` presentes |
| Isolamento (CA01) | run F1 real + `events.jsonl` | `systemTokens ≈ 13.449`; **zero** `compaction_start`/`truncation` |
| Nominal BDD (CA02) | run F1 real em `MeuERP-002` | `F1_OUTPUT_CONTRACT` 12/12; 19/19 artefatos |
| Edge/gate BDD (CA09, CA10, CA11) | `pytest` com `events.jsonl` sintético | 404 → `config_error` sem retry · `exit 0` sem artefato → `failed` · `inprompt` → runner recusa |
| Regressão | `pytest tests/tools tests/utils -q` + `verify_agent_observability.py` | suíte existente verde; cobertura de agentes igual antes/depois |
| Modo de execução | `git diff --exit-code` | `copilot-cli-headroom.bat` e `copilot-cli-v1.bat` sem diff |
