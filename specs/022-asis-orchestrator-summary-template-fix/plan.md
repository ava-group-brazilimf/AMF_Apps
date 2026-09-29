# Agent Implementation Plan: ava-asis-orchestrator — SAS Hook Summary Template Fix

**Spec**: `specs/022-asis-orchestrator-summary-template-fix/spec.md`
**Tech Stack**: N/A — this is an LLM prompt file fix, no code generation

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-asis-orchestrator` |
| **Change Type** | `bugfix` (PATCH) |
| **Phase** | `F1` |
| **Module** | `asis-diagnostic` |
| **Primary Requirement** | The "Hook: AVA Summary" section dispatches `ava-summary \| SAS` without mandating `build_summary_comprehensive.py` or a `success_criteria` block, allowing the summary agent to generate non-compliant HTML inline. |
| **Technical Approach** | Expand the "Hook: AVA Summary" section to explicitly forbid inline HTML generation, add a `success_criteria` block identical to the FP workflow, and add post-dispatch template-signature validation. Bump `2.20.0 → 2.20.1`. |
| **File modified** | `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md` |
| **Files NOT modified** | `summary-agent.md`, `build_summary_comprehensive.py`, `module.yaml`, `SKILL.md` |

---

## Constitution Check

- [x] **Article I** — No technology versions hardcoded. Agent is a prompt file.
- [x] **Article II** — Frontmatter not changed (only body section and version/date fields).
- [x] **Article II** — Agent name `ava-asis-orchestrator` matches `^ava-[a-z0-9-]+$`.
- [x] **Article III** — Phase placement unchanged (F1 orchestrator, SAS hook position preserved).
- [x] **Article IV** — `module.yaml` has no diff — agent already registered, no new agent created.
- [x] **Article V** — Hook section body in Brazilian Portuguese (existing convention maintained).
- [x] **Article VI** — BDD scenarios in spec §5 cover nominal, validation, parity, and SKIP paths.
- [x] **Article VII** — No security pipeline impact; fix is isolated to the summary hook section.
- [x] **Article VIII** — trace_id: N/A — LLM prompt file, not in JSON schema pipeline.
- [x] **Article IX** — Clean Architecture: N/A — agent is an LLM prompt file.
- [x] **Article X** — PATCH bump (`2.20.0 → 2.20.1`). Behaviour fix, no contract change.
- [x] **Article XI** — SKILL.md already exists; no change needed.

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers in spec.
- [x] Template signature `'AVA Fabric Summary Template v1.0'` verified in `build_summary_comprehensive.py:8420`.
- [x] Downstream `next_agent` chain unchanged.

---

## Research Findings

| Question | Decision | Rationale |
|----------|----------|-----------|
| What is the canonical template signature? | `'AVA Fabric Summary Template v1.0'` | Verified in `build_summary_comprehensive.py:8420` |
| Does `summary-agent.md` already call the script? | Yes — Step 3 already mandates it. The bug is the orchestrator not constraining the dispatch. | Out of scope to change `summary-agent.md` |
| Does the FP workflow already have the guard? | Yes — `success_criteria` block already present in the FP workflow section | The SAS hook needs the same guard added |
| Minimal diff? | Expand ~8 lines to ~22 lines in "Hook: AVA Summary" | PATCH-compliant, isolated change |
| Should `summary-agent.md` be modified? | No | Out of spec scope |

---

## 1. Technical Context

Pure LLM prompt file edit. No runtime code, no frameworks, no versioned libraries.

| Dimension | Value |
|---|---|
| Target file type | Markdown (.md) agent prompt |
| Body language | Brazilian Portuguese (per Article V) |
| Script referenced | `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` |
| Template signature | `'AVA Fabric Summary Template v1.0'` |
| Version bump | `2.20.0 → 2.20.1` (PATCH) |

---

## 2. Phase Placement

```
F1 SA pipeline (Phase A→B→C→D)
  └── Final Consistency Gate + Master Report
        └── Hook: AVA Summary  ← FIX HERE
              └── ava-summary | SAS  (enforced: script + success_criteria)
```

Post-dispatch validation flow:
```
[ava-asis-orchestrator] → dispatches → [ava-summary | SAS]
[ava-summary | SAS] completes → [ava-asis-orchestrator] validates template signature
  ✅ → emits "✅ Summary template OK", closes SA run
  ⚠️ → emits "⚠️ SUMMARY TEMPLATE MISMATCH", suggests ava-summary-remediation
  SKIP → orchestrator completes without Summary, no validation
```

**Quality gate at this phase**: summary-validator (after SA + SAS hook)

---

## 3. Clean Architecture Alignment

N/A — this agent is an LLM prompt file. It does not generate code artifacts.

---

## 4. Agent File Structure

**No new files.** Single existing file modified:

```
src/modules/ava-fabric-agents/asis-diagnostic/agents/
└── orchestrator-asis.md    ← PATCH: "Hook: AVA Summary" section + version bump
```

`.github/skills/ava-asis-orchestrator/SKILL.md` — **no change** (routes to same agent file).

---

## 5. module.yaml Impact

**No change.** `ava-asis-orchestrator` is already registered in:
```
src/modules/ava-fabric-agents/asis-diagnostic/module.yaml
```
PATCH bugfix does not require registration changes.

---

## 6. Observability & Trace Propagation

N/A — LLM prompt file; does not use the JSON schema pipeline.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|--------|-----------------|-------------|
| `agent-task.schema.json` | NO | No new inputs |
| `agent-result.schema.json` | NO | No new outputs |

---

## 8. Implementation Phases

### Phase 1 — Expand "Hook: AVA Summary" section

**Target**: `orchestrator-asis.md` — replace the "Hook: AVA Summary" section body.

**Current content** (to replace):
```
## Hook: AVA Summary

Após gerar o AS-IS Master Report (`MR`), acionar automaticamente o Summary Agent:

```
→ ava-summary | trigger: SAS
  (gera summary parcial com todas as seções AS-IS preenchidas)
```

O Summary Agent é opcional — pode ser pulado se o usuário digitar `SKIP`.
```

**New content** (replacement):
```
## Hook: AVA Summary

Após gerar o AS-IS Master Report (`MR`), acionar automaticamente o Summary Agent:

```
→ ava-summary | trigger: SAS
  (gera summary parcial com todas as seções AS-IS preenchidas)
```

**⛔ OBRIGATÓRIO — Execução via script (não geração inline):** Ao despachar `ava-summary | SAS`, o agente summary DEVE:
1. Executar o script `build_summary_comprehensive.py --project {project_name}` (Step 3 de `summary-agent.md`)
2. **NÃO** gerar HTML inline — o template HTML é produzido **exclusivamente** pelo script

**Critérios de Sucesso** (validar após `ava-summary | SAS` retornar):

```yaml
success_criteria:
  - Summary HTML contains "AVA Fabric Summary Template v1.0"
  - Summary HTML size > 150 KB
```

**Validação pós-execução:**
- Verificar se o HTML gerado contém a string `"AVA Fabric Summary Template v1.0"`
- SE sim → emitir: `✅ Summary template OK`
- SE não → emitir: `⚠️ SUMMARY TEMPLATE MISMATCH — invocar @ava-summary-remediation para reconstruir`

O Summary Agent é opcional — pode ser pulado se o usuário digitar `SKIP`.
Ao pular: omitir o despacho de `ava-summary` e toda a validação acima.
```

### Phase 2 — Bump version in frontmatter

Change `version: "2.20.0"` → `version: "2.20.1"` and `date: 2026-07-15` → `date: 2026-07-21`.

### Phase 3 — CHANGELOG entry

Prepend to `CHANGELOG.md`:
```markdown
## [2026-07-21] — F1 Orchestrator: Summary hook agora exige template via script (022-asis-orchestrator-summary-template-fix)

- **ava-asis-orchestrator v2.20.1** (PATCH)
- Problema: ao executar em modo SA, o hook `SAS` despachava `ava-summary` sem
  mandar usar `build_summary_comprehensive.py`, permitindo geração HTML inline
  não-conforme com o template AVA Fabric.
- Fix: seção "Hook: AVA Summary" inclui agora instrução obrigatória de uso do
  script, bloco `success_criteria` (assinatura + tamanho > 150 KB) e validação
  pós-execução com aviso `⚠️ SUMMARY TEMPLATE MISMATCH` quando a assinatura não
  é encontrada. Modo SKIP inalterado.
```

---

## 9. Complexity Tracking

| Item | Decision |
|------|----------|
| Whether to also fix `summary-agent.md` | Out of scope — Step 3 already mandates the script. The bug is the orchestrator not constraining the dispatch. |
| Hard `BLOCKED` gate vs. `⚠️ WARNING` | Warning chosen: Summary step is already optional. A hard block would be a behaviour change beyond PATCH scope. `ava-summary-remediation` covers the repair path. |
| Whether the FP workflow needs this change | No — FP already has a `success_criteria` block with template signature check. |

---

## 10. Test Strategy

| Test | Command | Expected |
|------|---------|----------|
| Script mandate in SAS hook | `grep -n "build_summary_comprehensive.py"` in `orchestrator-asis.md` | ≥2 matches (SAS hook + FP workflow) |
| `success_criteria` in SAS hook | `grep -n "success_criteria"` in `orchestrator-asis.md` | ≥2 matches |
| Template signature referenced in SAS hook | `grep -n "AVA Fabric Summary Template"` in `orchestrator-asis.md` | ≥2 matches |
| MISMATCH warning instruction present | `grep -n "SUMMARY TEMPLATE MISMATCH"` in `orchestrator-asis.md` | ≥1 match |
| SKIP instruction preserved | `grep -n "SKIP"` in Hook section | Present |
| Version bumped | `grep -n "^version:"` in frontmatter | `"2.20.1"` |
