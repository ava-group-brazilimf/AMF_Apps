# Agent Development Tasks: ava-asis-documentation — Batch Protocol + Completude Assertion

**Plan**: `specs/029-screen-flow-batch-protocol/plan.md`
**Agent ID**: `ava-asis-documentation` | **Phase**: `F1` | **Module**: `asis-diagnostic`

**Change Type**: `modify-existing` — agent v2.x → v3.0.0 (MAJOR bump). No new agent file created; `module.yaml` already registered.

> Complete categories sequentially. Mark [P] for tasks parallelizable within a category.

---

## Category 1 — Agent Frontmatter & Contract Definition

Must complete before any other category. All tasks update the existing file `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md`.

- [X] **1.1** Locate existing `src/modules/ava-fabric-agents/asis-diagnostic/agents/documentation-asis.md`
- [X] **1.2** Update YAML frontmatter (Article II):
  - `version: "3.0.0"` — MAJOR bump (execution model change)
  - `description: |` — append: "NOVO em v3.0: Screen Flow Mapper usa protocolo de geração em lotes por bounded context com assertion de completude para evitar truncamento."
  - `allowed-tools: Read, Write, Edit, Bash` — Bash is required for script invocation (verify it is already present)
  - Do NOT add phase, module, inputs, outputs, or dependencies to frontmatter
- [ ] **1.3** Update `## Output Contract` YAML block to include new artifacts:
  - `screen_flow_bc_artifacts: "projects/{project_name}/outputs/asis/docs/screen-flow-*.mmd"`
  - `completeness_assertion: "projects/{project_name}/outputs/asis/docs/screen-flow-completeness.json"`
  - Paths use lowercase `{project_name}` and correct phase folder (`outputs/asis/docs/`)
- [X] **1.3** Update `## Output Contract` YAML block to include new artifacts:
  - `screen_flow_bc_artifacts: "projects/{project_name}/outputs/asis/docs/screen-flow-*.mmd"`
  - `completeness_assertion: "projects/{project_name}/outputs/asis/docs/screen-flow-completeness.json"`
  - Paths use lowercase `{project_name}` and correct phase folder (`outputs/asis/docs/`)
- [X] **1.4** Verify dispatch mode unchanged (user-facing via existing `.github/skills/ava-asis-documentation/SKILL.md`)

---

## Category 2 — Agent Behavior & Instructions

Depends on Category 1. All tasks edit `documentation-asis.md` in the FT (Screen Flow Mapper) section.

- [X] **2.1** Write REGRA ABSOLUTA in FT section: script invocation is MANDATORY
  - Add explicit instruction: "FT DEVE invocar `Bash: python src/shared/tools/gen_screen_flow.py ...` — geração inline de mermaid é PROIBIDA"
  - Add guard: if mermaid content is generated inline without tool invocation → log `[FT-INLINE-GENERATION-DETECTED]` and mark sub-skill FAILED
- [X] **2.2** Write Batch Protocol activation condition
  - Rule: `DADO form_count > 80` → aplicar protocolo de iteração por BC
  - Rule: `DADO form_count <= 80` → geração single-pass com assertion aplicada igualmente
  - Reference: use `form-registry.json` como lista canônica; fallback glob `.dfm`/`.pas` apenas se registry ausente
- [X] **2.3** Write per-bounded-context generation protocol
  - Step: Ler `form-registry.json` → agrupar por `bounded_context` (ou inferir de `unit_path`/`directory`)
  - Step: Invocar `gen_screen_flow.py` com `--project {project_name} --input {form_registry_path} --output {output_dir}`; o tool já gera `screen-flow-{bc_slug}.mmd`
  - Step: O tool já valida cada `.mmd` com `validate_diagram.py`
  - Step: Registrar intermediários gerados
- [X] **2.4** Write Completeness Assertion block (post-geração OBRIGATÓRIA)
  - Step: Contar `N_nodes` em `screen-flow.mmd` invocando `Bash: python src/shared/tools/count_mermaid_nodes.py --input <screen-flow.mmd> --output <tmp_nodes.json>` (script já existente ou a ser criado; o agente NÃO conta manualmente)
  - Step: Contar `N_registry` em `form-registry.json` (entradas `form_id`; fallback glob → contagem de arquivos `.dfm`/`.pas`)
  - Step: Calcular `coverage_pct = (N_nodes / N_registry) * 100`
  - Step: Invocar `Bash: python src/shared/tools/write_assertion.py --project {project_name} --status <PASS|FAIL> --coverage <pct> --nodes <N> --registry <R> [--missing <forms>]` para gravar `screen-flow-completeness.json`
  - Step: Se `coverage_pct >= 80` → `status: "PASS"`
  - Step: Se `coverage_pct < 80` → `status: "FAIL"` + `missing_forms` array
- [X] **2.5** Write Retry Logic (max 3 tentativas)
  - Step: Se assertion FAIL → incrementar `retry_count`; re-executar geração para BCs com forms faltantes
  - Step: Após re-geração, re-executar assertion
  - Step: Se `retry_count == 3` E assertion ainda FAIL → `AgentResult.success = false`, `risk.level = "high"`, `human_gate_required = true`
- [X] **2.6** Write Script Fallback
  - Step: Se `gen_screen_flow.py` não existir no caminho esperado → logar `[FT-SCRIPT-MISSING]`
  - Step: Fallback: iteração manual por BC via subprocesso com Python inline (mínimo de argumentos)
  - Step: Ainda assim aplicar assertion de completude
- [X] **2.7** Update Pre-Completion Validation Checklist in `documentation-asis.md`
  - Add: "`screen-flow-completeness.json` verificado com `status: "PASS"` OBRIGATÓRIO antes de reportar `completed`"
  - Add: "Per-BC intermediários `screen-flow-*.mmd` presentes no diretório de saída (para debugging)"
  - Add: "Nenhum comentário `%% [UNREGISTERED]` permanece no mermaid final (mantido da v2.x)"
- [X] **2.8** Update Output Verification section
  - Add: verificar existência de `screen-flow-completeness.json` — ausente = FALHA
  - Add: verificar JSON schema mínimo: campos `status`, `coverage_pct`, `N_nodes`, `N_registry`

---

## Category 3 — Shared Schema Updates

Skip — plan Section 7 and spec Section 6 confirm **no schema changes** (`agent-task.schema.json` and `agent-result.schema.json` unchanged). `screen-flow-completeness.json` is a lightweight artifact file, not a schema field.

- [X] **3.1** N/A — no changes to shared schemas

---

## Category 4 — Module Registration

N/A — `modify-existing`. Agent `ava-asis-documentation` is already registered in `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml`.

- [X] **4.1** N/A — no new module registration needed

---

## Category 5 — Quality Gate Checklists

- [X] **5.1** Update F1 consistency gate checklist (`readiness-gate-checklist.md` or equivalent):
  - Add item: "`screen-flow-completeness.json` existe e `status == \"PASS\"`"
  - Add item: "Per-BC intermediários `screen-flow-*.mmd` estão presentes em `outputs/asis/docs/`""
- [X] **5.2** Add assertion status validation to Summary Validator (55 rules) — reference existing rule list and note that a new rule should validate `screen-flow-completeness.json`:
  - Rule: "Screen Flow Completeness: `coverage_pct >= 80` OR `human_gate_required == true`""
- [X] **5.3** [P] Update `docs/qa-orchestrator-io-map.md` if assertion JSON is referenced as QA input

---

## Category 6 — Acceptance Validation & QA Integration

Depends on Category 2.

- [X] **6.1** Confirm spec Section 4 Scenario 1 (Nominal P1 — 665-form ERP) coverage:
  - Acceptance: `screen-flow.mmd` contains ≥80% of forms, `screen-flow-completeness.json` has `status: "PASS"`, intermediários `screen-flow-*.mmd` existem
- [X] **6.2** Confirm spec Section 4 Scenario 2 (Edge P2 — LLM skips script) coverage:
  - Acceptance: `[FT-INLINE-GENERATION-DETECTED]` log presente quando script não invocado; sub-skill FAILED
- [X] **6.3** Confirm spec Section 4 Scenario 3 (Gate P1 — assertion FAIL) coverage:
  - Acceptance: após 3 retries ainda FAIL → `AgentResult.success = false`, `risk.level = "high"`, `human_gate_required = true`
- [X] **6.4** [P] Run agent against controlled test project (e.g., `projects/test-determinism/` or a small Delphi sample) to validate:
  - Todos os artefatos do `## Output Contract` são produzidos (incluindo `screen-flow-completeness.json` e `screen-flow-*.mmd`)
  - Arquivos não estão vazios
  - `screen-flow.mmd` é válido Mermaid (syntax check)
- [X] **6.5** [P] Validate `screen-flow-completeness.json` against schema in `data-model.md`:
  - Campos obrigatórios presentes
  - `coverage_pct` calculado corretamente
  - `missing_forms` preenchido quando `status == "FAIL"`
- [X] **6.6** [P] Verify no regression for small projects (≤80 forms):
  - Batch protocol NÃO é acionado
  - Single-pass geração funciona normalmente
  - Assertion ainda é executada e PASS
- [X] **6.7** [P] Map scenarios to F5 QA pipeline inputs:
  - Copiar/referenciar spec Section 4 para `ava-qa-scenario-generator`
  - Verificar formato `FR-NNN` / `BR-NNN` de rastreabilidade (se aplicável)
- [X] **6.8** [P] Validate tool invocation rate (SC-4):
  - Acceptance: Inspecionar logs do agente e confirmar que `gen_screen_flow.py` foi invocado via Bash para 100% dos projetos com >80 forms
  - Acceptance: Se não houver registro de invocação → flag `[FT-INLINE-GENERATION-DETECTED]` e FAIL no teste
  - Nota: A detecção de inline generation é responsabilidade do orquestrador/validator externo, não do auto-guard do agente

---

## Category 7 — Documentation & Catalog Update

Can run parallel with Category 6.

- [X] **7.1** [P] Update `docs/agents-catalog.md`:
  - Atualizar `ava-asis-documentation`: version `3.0.0`, adicionar nota sobre batch protocol + assertion
- [X] **7.2** [P] Add `CHANGELOG.md` entry:
  - Versão: `3.0.0` (MAJOR)
  - Descrição: "FT (Screen Flow Mapper): adicionado protocolo de geração em lotes por bounded context + assertion de completude com retry e human gate"
  - Breaking change: comportamento de geração muda de single-pass para chunked para projetos >80 forms
- [X] **7.3** [P] Update `docs/full-pipeline-guide.md` se a lista de artefatos F1 mudou:
  - Adicionar `screen-flow-completeness.json` e `screen-flow-*.mmd` como artefatos F1
- [X] **7.4** [P] Verify no top-level `module.yaml` changes needed (existing phase)

---

## Dependency Graph

```text
Category 1 (Frontmatter)
    ↓
Category 2 (Behavior/Instructions)
    ↓
Category 5 (Checklists) ← can start during Category 2 late stage
    ↓
Category 6 (Validation) ← depends on Category 2 complete
    ↓
Category 7 (Docs) ← parallel with Category 6
```

**Critical Path**: 1 → 2 → 6 → Done  
**Parallel Opportunities**: Category 5 during Category 2 drafting; Category 7 during Category 6 validation.

---

## Parallel Execution Groups

| Group | Tasks | Parallel? |
|---|---|---|
| **Validation Batch** | 6.4, 6.5, 6.6, 6.7 | ✅ [P] — independent validation tasks |
| **Docs Batch** | 7.1, 7.2, 7.3, 7.4 | ✅ [P] — documentation updates are independent |
| **Checklist Draft** | 5.1, 5.2, 5.3 | ✅ [P] — can be drafted while Category 2 is in progress |

---

## Completion Checklist

- [X] All 7 categories complete (Categories 3 and 4 are N/A — documented above)
- [ ] SKILL.md already exists (user-facing) — no action needed (Article XI)
- [X] `specify self check` — no SpecKit updates pending
- [ ] Agent `.md` frontmatter validated (name pattern, version SemVer, description pt-BR)
- [ ] `module.yaml` unchanged (modify-existing) — verified entry already exists
- [ ] Agent validated against test project — all output artifacts produced including assertion JSON and per-BC intermediates
- [ ] `docs/agents-catalog.md` updated with v3.0.0
- [ ] `CHANGELOG.md` entry committed with MAJOR bump justification
