# Agent Implementation Plan: QA Local Execution Pipeline, Observability & Test Pyramid

**Spec**: `specs/002-qa-local-pipeline/spec.md`
**Tech Stack**: See `src/shared/data/reference-architecture.yaml` (v1.0.0) — do not hardcode versions.

---

## Summary

| Field | Value |
|---|---|
| **Change Type** | `new-agent` + `modify-existing` (5 components) |
| **Phase** | `F5 — QA` (orchestrated by `ava-qa-orchestrator`) |
| **Module** | `qa-agents` |
| **Primary Requirement** | Formalizar o pipeline de execução local de QA com pré-condições validadas, suítes orquestradas, métricas observáveis e visualização em pirâmide de testes no relatório HTML consolidado. |
| **Technical Approach** | Criar `ava-qa-local-runner` como wrapper formal de `qa_test_runner.py`; completar `qa_preflight.py` com checagens de artefatos; migrar o bridge agent para o caminho canônico `outputs/tobe/qa/fastqa/`; adicionar visualização da pirâmide ao HTML summary. |
| **Implementation Status** | 2/12 componentes existem com gaps; 10/12 requerem criação ou modificação. Veja `research.md`. |

---

## Constitution Check

- [x] **Article I** — Sem versões hardcoded. `backend_version` e `node_version` lidos de `project-config.yaml`. `ntp_server` lido de `quality_gates.ntp_server`. ✅
- [x] **Article II** — `ava-qa-local-runner` segue o padrão `^ava-[a-z0-9-]+$`. Frontmatter incluirá apenas `name`, `version`, `description`, `allowed-tools`. ✅
- [x] **Article III** — F5 é orquestrado por `ava-qa-orchestrator`. `ava-qa-local-runner` é disparado via trigger `LR`. `ava-summary` é invocado após F5 pelo master-orchestrator. ✅
- [x] **Article IV** — `ava-qa-local-runner` requer nova entrada em `src/modules/ava-fabric-agents/qa-agents/module.yaml`. Todos os demais são modify-existing (entradas já existem). ✅
- [x] **Article V** — Corpo do agente `ava-qa-local-runner` em pt-BR. Scripts Python mantêm docstrings em inglês (convenção existente no projeto). ✅
- [x] **Article VI** — BDD scenarios: 6 cenários (S1–S6) cobrindo nominal, falha de pré-condição, guardrail do bridge, pirâmide, retry e CI. ✅
- [x] **Article VII** — Sem impacto no F1 security pipeline. A validação de artefatos adicionada ao preflight não acessa dados sensíveis. ✅
- [x] **Article VIII** — `trace_id` propagado via `shared-context.md`. Observability events adicionados a contract e frontend generators com NTP timestamp. ✅
- [x] **Article IX** — N/A — agentes são arquivos `.md` de instrução LLM; scripts Python são utilitários. Clean Architecture aplica-se ao código gerado, não aos agentes. ✅
- [x] **Article X** — Bumps determinados: `ava-qa-bridge-fastqa-tobe` MAJOR (1.2.0→2.0.0), `ava-qa-orchestrator` MINOR (1.6.0→1.7.0), `ava-qa-contract-test-generator` MINOR (1.1.0→1.2.0), `ava-qa-frontend-test-generator` MINOR (1.1.0→1.2.0), `ava-qa-local-runner` NEW (1.0.0). ✅
- [x] **Article XI** — `ava-qa-local-runner`: user-facing → SKILL.md obrigatório. `qa_preflight.py` e `qa_test_runner.py`: utilitários internos → sem SKILL.md. ✅

### Quality Gate Check

- [x] Nenhum `[NEEDS CLARIFICATION]` na spec
- [x] Todos os outputs seguem `projects/{project_name}/outputs/...` ou `src/shared/...`
- [x] `next_agent` downstream confirmado: `ava-qa-local-runner` → `ava-summary` (via orchestrator)

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Backend test framework | xUnit 2.7 + Moq + FluentAssertions + Testcontainers | `reference-architecture.yaml → tech_stack.backend.testing` |
| Frontend test framework | Jest + Angular Testing Library | `reference-architecture.yaml → tech_stack.frontend.testing.unit` |
| API test framework | Playwright (TypeScript) | `reference-architecture.yaml → tech_stack.frontend.testing.e2e` |
| Contract test framework | PactNet | `ava-qa-contract-test-generator` (existing agent) |
| Container runtime | Docker (padrão) / Podman | Detectado dinamicamente em `qa_preflight.py` e `qa_test_runner.py` |
| Report format | HTML autocontido | Consistente com `ava-summary` (padrão existente) |
| NTP server | `pool.ntp.org` (default) | `project-config.yaml → quality_gates.ntp_server` (configurável) |
| CI target | GitHub Actions / Azure DevOps | Detectado por `ava-qa-local-runner` a partir do `project-config.yaml` |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

```
F2 → ava-summary → F3 → ava-summary
                 → F5 (QA)
                     └─ ava-qa-orchestrator (QS)
                         ├─ Step 1–9: agentes QA existentes (GR→BM→TS→TC→AS→CT→FT→ET+EC+FQ→PT→RS)
                         │            └─ ava-qa-bridge-fastqa-tobe (FQ) → outputs/tobe/qa/fastqa/ ← MAJOR bump
                         ├─ Step 10: ava-qa-local-runner (LR) ◄── NEW
                         │           ├─ qa_preflight.py (pré-condições + artifacts + NTP)
                         │           ├─ qa_test_runner.py (Unit→Integration→Contract→Frontend)
                         │           └─ emite: preflight-report.json, test-results.json,
                         │                     test-pyramid-metrics.json, qa-execution-report.html,
                         │                     qa-ci-pipeline.yml
                         └─ Step 11: quality-strategy.md + qa-master-report.md
                     → ava-summary
                 → F7 → ava-summary
                 → F6 → ava-summary (FINAL)
```

**Standalone**: `@ava-qa-local-runner` invocável diretamente pelo usuário via SKILL.md (trigger `LR`).

**Quality gates nesta fase**:
- `ava-qa-local-runner` bloqueia se `qa_preflight.py` retorna exit 1 (FAIL)
- Container runtime ausente → Integration/DB marcados como `NOT_EXECUTED` (modo `local`)
- Container runtime ausente → FAIL fatal (modo `ci`)

`human_gate_required: true` quando:
- `qa_preflight.py` retorna exit 1 por ferramenta de toolchain ausente (`dotnet`, `node`)
- Todos os retries de uma suite falharem no modo `ci`

---

## 3. Clean Architecture Alignment

```
Domain         → NO  — nenhum código de domínio gerado nesta feature
Application    → NO  — idem
Infrastructure → NO  — idem
Presentation   → NO  — idem
```

> **N/A** — todos os artefatos são arquivos de instrução LLM (`.md`), scripts Python (`.py`),
> templates TypeScript (`.ts`), checklists (`.md`) e configuração CI (`.yml`).
> Clean Architecture aplica-se ao código **gerado** pelos agentes, não aos próprios agentes.

---

## 4. Agent File Structure

```
# NOVO agente (user-facing)
.github/skills/ava-qa-local-runner/
└── SKILL.md                                          ← routing wrapper (NEW)

src/modules/ava-fabric-agents/qa-agents/agents/
├── local-runner-agent.md                             ← corpo do agente (NEW)
│
# Agentes MODIFICADOS (modify-existing)
├── bridge-fastqa-tobe.md              v1.2.0 → v2.0.0 MAJOR (path migration + Fraud Guard)
├── contract-test-generator-agent.md  v1.1.0 → v1.2.0 MINOR (observability + checklist)
├── frontend-test-generator-agent.md  v1.1.0 → v1.2.0 MINOR (observability + checklist + template)
└── qa-orchestrator-agent.md          v1.6.0 → v1.7.0 MINOR (LR trigger + path corrections)

# Scripts Python (modify-existing)
src/shared/utils/
├── qa_preflight.py                   ADD: artifact checks + NTP + JSON output
└── qa_test_runner.py                 ADD: --retry + test-pyramid-metrics.json

# Summary builder (modify-existing)
src/modules/ava-fabric-agents/summary/utils/
└── build_summary_comprehensive.py   ADD: QA Test Pyramid section

# Novos artefatos compartilhados (NEW)
src/shared/checklists/
├── contract-test-checklist.md        69 critérios
└── frontend-test-checklist.md        69 critérios

src/shared/templates/
└── playwright-api-tobe.template.ts   template Playwright TO-BE
```

**Dispatch mode**: `ava-qa-local-runner` é user-facing (SKILL.md obrigatório) + internamente disparado via `LR`. Scripts Python são utilitários internos sem SKILL.md.

---

## 5. module.yaml Impact

```yaml
# src/modules/ava-fabric-agents/qa-agents/module.yaml
# Diff a aplicar:
name: qa-agents
version: "1.3.0"   # bump de 1.2.0 (nova entrada = MINOR)
date: "2026-07-06"
agents:
  # ... (13 entradas existentes — sem alteração) ...
  - id: ava-qa-local-runner          # [NEW]
    file: agents/local-runner-agent.md
    skill: ava-qa-local-runner
```

O `module.yaml` raiz (`/module.yaml`) **não** precisa de alteração — `qa-agents` já é um módulo registrado.

---

## 6. Observability & Trace Propagation

`trace_id` propagado via `shared-context.md` (padrão existente). Sem alterações em `agent-task.schema.json`.

**Adições desta feature**:

| Componente | Evento emitido | Localização |
|---|---|---|
| `ava-qa-contract-test-generator` | `test_generation_started/completed/failed` | Seção `## Observability` em `contract-test-report.md` |
| `ava-qa-frontend-test-generator` | `test_generation_started/completed/failed` | Seção `## Observability` em `frontend-test-report.md` |
| `qa_preflight.py` | timestamp NTP | Campo `generated_at` + `ntp_fallback` em `preflight-report.json` |
| `qa_test_runner.py` | timestamp NTP | Campos `execution_timestamp` + `ntp_fallback` em ambos os JSONs |

Schema do evento: `data-model.md §4`.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| `agent-task.schema.json` | NO | Sem novos campos de input |
| `agent-result.schema.json` | NO | Sem novos campos no schema JSON do pipeline |
| `test-results.json` | YES | Adicionar `ntp_fallback`, `retry_count` (root) e `suites[].retry_attempts` — extensão não-breaking |
| `test-pyramid-metrics.json` | YES (NEW) | Novo arquivo — ver `data-model.md §1` |
| `preflight-report.json` | YES (FORMALIZED) | Formaliza output do `qa_preflight.py` como JSON estruturado — ver `data-model.md §2` |
| `project-config.yaml` template | YES | Adicionar `quality_gates.ntp_server` e `qa_runner.retry_count` |

---

## 8. Implementation Phases

### Phase 0 — Research ✅ CONCLUÍDO

Ver [research.md](./research.md).

**Resultado**: 2/12 componentes existem com gaps (`qa_preflight.py` sem artifact checks; `qa_test_runner.py` sem retry e pyramid metrics). 10/12 requerem criação ou modificação.

**Breaking change identificado**: `ava-qa-bridge-fastqa-tobe` usa `outputs/qa/fastqa/` em toda a sua extensão — migração para `outputs/tobe/qa/fastqa/` é obrigatória (CA12) e é uma mudança de contrato → MAJOR bump.

---

### Phase 1 — Design ✅ CONCLUÍDO

- [x] [data-model.md](./data-model.md) — schemas dos novos JSONs e eventos de observabilidade
- [x] [contracts/output-contracts.md](./contracts/output-contracts.md) — contratos de saída para todos os agentes afetados
- [x] [quickstart.md](./quickstart.md) — 10 cenários de validação end-to-end

---

### Phase 2 — Implementation Tasks

> Organizadas por categoria. Dependências indicadas onde aplicável.

---

#### Categoria 1 — Scripts Python (base do pipeline)

**Task 1.1 — `qa_preflight.py`: artifact existence checks (CA01)**

Adicionar três novas funções `check_openapi_specs()`, `check_contract_files()` e `check_angular_components()` ao script existente. Cada função usa `glob()` para verificar a existência dos artefatos correspondentes nos caminhos canônicos e retorna um dict `{id, status, detail}` seguindo o padrão das funções existentes.

Adicionar também escrita de `preflight-report.json` em `projects/{project_name}/outputs/qa/` (atualmente o script só imprime para stdout).

Detalhes de implementação: ver `data-model.md §2` para o schema do JSON de saída.

---

**Task 1.2 — `qa_test_runner.py`: retry support (CA05)**

Adicionar argumento `--retry N` ao `argparse`. Envolver cada chamada de suite em `run_with_retry()`:

```python
def run_with_retry(run_fn, *args, max_retries: int = 0, **kwargs) -> list:
    last_results = []
    attempt = 0
    for attempt in range(max_retries + 1):
        last_results = run_fn(*args, **kwargs)
        if not any(r["status"] == "FAIL" for r in last_results):
            break
        if attempt < max_retries:
            print(f"⚠️ Retry {attempt + 1}/{max_retries}")
    for r in last_results:
        r["retry_attempts"] = attempt
    return last_results
```

Ler `qa_runner.retry_count` de `project-config.yaml` como fallback quando `--retry` não for especificado. Adicionar `retry_count` (root) e `suites[].retry_attempts` ao JSON de saída.

---

**Task 1.3 — `qa_test_runner.py`: pyramid metrics output (CA06, CA19)**

Adicionar função `write_pyramid_metrics()` chamada após `write_results()` em `main()`. A função agrega os resultados das suítes em três camadas (Unit / Integration+Contract / E2E+Frontend) e escreve `test-pyramid-metrics.json`. Detalhes do schema: ver `data-model.md §1`.

> **Nota de mapeamento de camadas**: Suítes do tipo `contract` são classificadas na camada **Integration** da pirâmide, pois testam contratos de interface entre componentes integrados (não são testes unitários nem E2E).

---

**Task 1.4 — NTP timestamp (CA15)**

Adicionar função `get_ntp_timestamp(ntp_server: str) -> tuple[str, bool]` em ambos os scripts (ou como import de `ntp_guard.py` se criado). Retorna `(iso_timestamp, ntp_fallback)`. Timeout: 2 segundos. Fallback para `datetime.now(timezone.utc)` com `ntp_fallback=True`. Dependência soft: `ntplib` (guarded com try/except).

---

#### Categoria 2 — Novo agente `ava-qa-local-runner`

**Task 2.1 — Criar `local-runner-agent.md`**

**Caminho**: `src/modules/ava-fabric-agents/qa-agents/agents/local-runner-agent.md`

**Frontmatter** (exato):
```yaml
---
name: "ava-qa-local-runner"
version: "1.0.0"
description: |
  Orquestra a execução local do pipeline de QA nas camadas Unit, Integration,
  Contract e Frontend. Valida pré-condições via qa_preflight.py, executa suítes
  em sequência via qa_test_runner.py, coleta métricas e gera o relatório HTML
  consolidado com a QA Test Pyramid. Produz também o pipeline CI com etapas
  independentes por camada.
  Ativa com: "executar testes locais", "qa local pipeline", "run qa pipeline",
  "qa test runner", "executar suítes de teste", "LR".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---
```

**Corpo do agente** — 7 seções obrigatórias (em pt-BR):

| Seção | Conteúdo |
|---|---|
| `## Papel & Persona` | Engenheiro de plataforma QA, garante execução orquestrada e observável |
| `## Input Contract` | `project-config.yaml` (required); `test-results.json` e `.sln` (optional) |
| `## Output Contract` | 5 artefatos (ver `contracts/output-contracts.md §Contract 1`) |
| `## Pre-condition Gate` | Bloqueia se `qa_preflight.py` exit != 0; `PREFLIGHT_SKIPPED` se script ausente |
| `## Execution Steps` | 7 passos: ler config → preflight → test runner → ler resultados → HTML report → CI YAML → emit signal |
| `## Completion Checklist Gate` | 6 critérios: preflight-report.json ✓, test-results.json ✓, test-pyramid-metrics.json ✓, HTML ✓, CI YAML ✓, trace_id propagado ✓ |
| `## Guardrails` | Não executar suítes se preflight FAIL; não gerar outputs sintéticos; CI YAML nunca com caminhos hardcoded |

---

**Task 2.2 — Criar SKILL.md**

**Caminho**: `.github/skills/ava-qa-local-runner/SKILL.md`

Seguir o padrão das SKILL.md existentes no projeto (ex.: `ava-qa-bridge-fastqa-tobe`):
1. Resolve `project_name` de `projects/*/context/project-config.yaml` (excluir `_template`)
2. Lê `projects/{project_name}/context/agent-task-config.yaml` e `shared-context.md`
3. Passa `language` lido de `project-config.yaml`
4. Delega ao agente `src/modules/ava-fabric-agents/qa-agents/agents/local-runner-agent.md`

---

#### Categoria 3 — Bridge FastQA: migração de caminho (MAJOR)

**Task 3.1 — `bridge-fastqa-tobe.md` v1.2.0 → v2.0.0**

**Caminho**: `src/modules/ava-fabric-agents/qa-agents/agents/bridge-fastqa-tobe.md`

Aplicar as seguintes substituições (usando replace_string_in_file para cada ocorrência, preservando contexto):

| Substituição | Ocorrências confirmadas |
|---|---|
| `version: "1.2.0"` → `version: "2.0.0"` | Frontmatter (linha ~3) |
| `outputs/qa/fastqa/` → `outputs/tobe/qa/fastqa/` | Linhas 24, 170–172, 969, 1094–1096, 1116, 1129 |
| String de confirmação do spec-read → incluir `v2.0.0` | Linha do `"✅ SPEC LIDO: ..."` |
| Guardrail da Execution Invariant | Adicionar linha do Fraud Guard |

**Fraud Guard a adicionar** na seção `## ⛔ Execution Invariant`:
```
❌ Emitir conteúdo não fundamentado em artefatos lidos explicitamente (FRAUD GUARD)
   → Cada Write() DEVE ser precedido por pelo menos um Read() do artefato fonte
   → Se nenhum Read() executado antes de Write() → ABORT: "FRAUD_GUARD: synthetic output detected"
```

---

#### Categoria 4 — module.yaml

**Task 4.1 — Registrar `ava-qa-local-runner`**

Em `src/modules/ava-fabric-agents/qa-agents/module.yaml`:
- Bump `version: "1.2.0"` → `"1.3.0"`, atualizar `date`
- Adicionar entrada `ava-qa-local-runner` ao final da lista `agents`

---

#### Categoria 5 — Modificações em agentes existentes

**Task 5.1 — `qa-orchestrator-agent.md` v1.6.0 → v1.7.0**

Modificações em `src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md`:

1. Bump `version: 1.6.0` → `version: 1.7.0`, `date: "2026-07-06"`
2. Agent Team QA — adicionar linha: `| ava-qa-local-runner | Execução Local | Após RS (trigger LR) |`
3. Triggers / Menu — adicionar: `| LR | **Local Runner** — executa pipeline QA local completo |`
4. Output Contract — mudar 3 caminhos FastQA de `outputs/qa/fastqa/` → `outputs/tobe/qa/fastqa/`; adicionar 4 novos outputs do `LR`
5. Step 11b — substituir chamada direta ao `qa_test_runner.py` por dispatch ao `ava-qa-local-runner`
6. FQ COMPLETION GATE (step 9c) — atualizar todas as ocorrências de `outputs/qa/fastqa/` → `outputs/tobe/qa/fastqa/`
7. Instrução de dispatch ao bridge (step 9) — atualizar caminho mencionado no texto

---

**Task 5.2 — `contract-test-generator-agent.md` v1.1.0 → v1.2.0**

Adicionar ao final do arquivo (após a última seção existente):
- Seção `## Observabilidade` com eventos obrigatórios e referência ao schema
- Seção `## NTP Timestamp Guardrail` com regras de fallback
- Seção `## Checklist de Validação` referenciando `src/shared/checklists/contract-test-checklist.md`
- Bump `version: 1.1.0` → `version: 1.2.0`, `date: "2026-07-06"`

---

**Task 5.3 — `frontend-test-generator-agent.md` v1.1.0 → v1.2.0**

Mesmo padrão da Task 5.2, adicionando também:
- Input opcional: `src/shared/templates/playwright-api-tobe.template.ts`
- Seção `## Checklist de Validação` referenciando `src/shared/checklists/frontend-test-checklist.md`
- Bump `version: 1.1.0` → `version: 1.2.0`, `date: "2026-07-06"`

---

#### Categoria 6 — Novos artefatos compartilhados

**Task 6.1 — `contract-test-checklist.md` (CA08)**

Criar `src/shared/checklists/contract-test-checklist.md` com **exatamente 69 itens**:
- Grupo 1: Configuração PactNet Consumer (15 itens)
- Grupo 2: Configuração PactNet Provider (15 itens)
- Grupo 3: Identificação de Consumer-Provider Pairs (10 itens)
- Grupo 4: Execução e Publicação de Contratos (10 itens)
- Grupo 5: Observabilidade e NTP (9 itens)
- Grupo 6: Integração CI (10 itens)

**Validação**: `grep -c "^- \[" src/shared/checklists/contract-test-checklist.md` deve retornar `69`.

---

**Task 6.2 — `frontend-test-checklist.md` (CA09)**

Criar `src/shared/checklists/frontend-test-checklist.md` com **exatamente 69 itens**:
- Grupo 1: Isolamento de Componentes (15 itens)
- Grupo 2: Testes de Services e NgRx Stores (15 itens)
- Grupo 3: Query Patterns — Angular Testing Library (12 itens)
- Grupo 4: Configuração Jest (8 itens)
- Grupo 5: Observabilidade e NTP (9 itens)
- Grupo 6: Integração CI (10 itens)

**Validação**: `grep -c "^- \[" src/shared/checklists/frontend-test-checklist.md` deve retornar `69`.

---

**Task 6.3 — `playwright-api-tobe.template.ts` (CA10)**

Criar `src/shared/templates/playwright-api-tobe.template.ts` com:
- `playwright.config.ts` pattern: `baseURL` de `process.env.API_BASE_URL` (obrigatório — nunca hardcoded)
- Fixture `base-api-test.ts`: estende `test` com Authorization header de `process.env.API_TOKEN`
- Exemplo `health.spec.ts`: GET 200, POST 201, autenticação Bearer, 401 sem token, 404 not found
- Todos os valores de exemplo marcados com `// TODO: replace with project-specific values`
- **Validação**: `npx tsc --noEmit --target ES2020 --moduleResolution node playwright-api-tobe.template.ts` deve retornar exit 0

---

#### Categoria 7 — HTML Summary: QA Test Pyramid

**Task 7.1 — `build_summary_comprehensive.py`: seção QA Test Pyramid (CA17, CA18, CA19)**

Adicionar função `build_qa_pyramid_section(project_dir: Path) -> str` em `build_summary_comprehensive.py`:

1. Tenta ler `{project_dir}/outputs/qa/test-pyramid-metrics.json`
2. Se ausente → retorna `<section id="qa-test-pyramid"><p class="no-data">No QA metrics available</p></section>` sem exceção
3. Se presente → gera:
   - Tabela HTML com colunas: Camada | Meta % | Real % | Total | ✅/⚠️
   - CSS triangle pyramid (Unit=base, Integration=middle, E2E=top) usando `clip-path` ou div trick — sem JS externo
   - Indicador ⚠️ quando `|real_pct - target_pct| > 10`
4. A seção é injetada no HTML antes do `</body>`

---

#### Categoria 8 — CI, Documentação e Configuração

**Task 8.1 — `docs/agents-catalog.md`: atualizar referências (CA22)**

- Substituir `outputs/qa/fastqa/` → `outputs/tobe/qa/fastqa/` em todas as ocorrências
- Adicionar `ava-qa-local-runner` na tabela de agentes F5

---

**Task 8.2 — `projects/_template/context/project-config.yaml`: novos campos**

Adicionar:
```yaml
quality_gates:
  ntp_server: "pool.ntp.org"

qa_runner:
  retry_count: 0
```

---

**Task 8.3 — `CHANGELOG.md`: registrar breaking change**

Adicionar entrada com:
- `ava-qa-bridge-fastqa-tobe` MAJOR 2.0.0 — breaking path change
- Ação requerida para projetos que já executaram FQ: mover artefatos de `outputs/qa/fastqa/` → `outputs/tobe/qa/fastqa/`

---

## 9. Complexity Tracking

| Decision | Complexity | Justification |
|---|---|---|
| `ava-qa-bridge-fastqa-tobe` MAJOR bump | Médio | Breaking change em 8+ ocorrências do caminho de saída. Todas as ocorrências mapeadas na Task 3.1 com contagem por linha confirmedada no research. |
| `ava-qa-orchestrator` step 11b refactor | Médio | Substituição de chamada direta ao Python script por dispatch ao novo agente — behavioralmente equivalente, mas afeta 5+ seções do orchestrator (Output Contract, Agent Team, Triggers, step 11b, FQ COMPLETION GATE). |
| NTP integration | Baixo | `ntplib` é biblioteca leve com import guarded. Fallback local garante zero impacto em ambientes offline. |
| Pyramid CSS sem dependências externas | Baixo | CSS triangle technique bem documentada; testável em isolamento antes de injetar no summary builder. |
| `qa_test_runner.py` retry wrapper | Baixo | Loop simples sem mudança no schema de saída existente (campos são adições opcionais). |
| CI YAML multi-plataforma | Médio | Dois templates (GH Actions / AzDo) detectados via `devops_platform` em `project-config.yaml`. Escopo limitado a geração de arquivo YAML. |

---

## 10. Post-Phase 1 Constitution Re-check

- [x] **Article I** — Sem versões hardcoded nos novos artefatos ✅
- [x] **Article II** — `ava-qa-local-runner` frontmatter correto ✅
- [x] **Article III** — Fluxo F1→F2→F3→F5→F7→F6 inalterado; `ava-qa-local-runner` posicionado dentro de F5 ✅
- [x] **Article IV** — `module.yaml` diff definido (Task 4.1) ✅
- [x] **Article X** — `ava-qa-bridge-fastqa-tobe` MAJOR justificado (breaking output path contract) ✅
- [x] **Article XI** — SKILL.md para `ava-qa-local-runner` definido (Task 2.2) ✅
- [x] Sem `[NEEDS CLARIFICATION]` remanescentes ✅

**DECISION: PROCEED** ✅
