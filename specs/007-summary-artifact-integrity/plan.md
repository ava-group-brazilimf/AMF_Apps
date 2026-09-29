# Agent Implementation Plan: Summary Artifact Integrity Verification

**Spec**: `specs/007-summary-artifact-integrity/spec.md`
**Tech Stack**: See `src/shared/data/reference-architecture.yaml` (v1.0.0) — do not hardcode versions.

---

## Summary

| Field | Value |
|---|---|
| **Agent ID** | `ava-summary` + `ava-summary-validate` (modify existing) |
| **Phase** | `F8` |
| **Module** | `summary` |
| **PBI** | 2299 (children: 2300, 2301, 2302, 2303) |
| **Primary Requirement** | Add pre-build artifact integrity check that emits `[ARTIFACT-MISSING]`/`[ARTIFACT-EMPTY]` per absent artifact and expands `summary-validate-agent.md` with C11 rules |
| **Technical Approach** | Insert Step 0.5 into `summary-agent.md`; add `_c11_1/2/3` to `validate_summary.py`; bump versions in both agents and module.yaml |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Justify gate failures in Complexity Tracking (section 9).*

### Constitution Gates

- [x] **Article I** — No technology versions hardcoded; artifact-map.yaml path is a config reference, not a literal version
- [x] **Article II** — Frontmatter bumped to `1.1.0` in both agents; only `name`, `version`, `description`, `allowed-tools` fields; no added fields
- [x] **Article II** — Agent names `ava-summary` and `ava-summary-validate` match `^ava-[a-z0-9-]+$`
- [x] **Article III** — F8 placement unchanged; `ava-summary` still invoked after every phase; `ava-summary-validate` still runs post-summary
- [x] **Article IV** — `module.yaml` version bump from `1.0.0` → `1.1.0` (see Plan section 5)
- [x] **Article V** — New Step 0.5 body written in Brazilian Portuguese; C11 rule descriptions use Portuguese
- [x] **Article VI** — BDD scenarios cover nominal (S1), missing (S2), empty (S3), validator detection (S4–S5), and Sophia E2E (S6)
- [x] **Article VII** — No new security surface area; read-only file existence checks only
- [x] **Article VIII** — Step 0.5 row added to MICRO timing table in both FULL and STATUS_ONLY templates
- [x] **Article IX** — N/A: agents are LLM prompt `.md` files, not generated C# code
- [x] **Article X** — MINOR bump (new optional behavior, backward-compatible); no contract change
- [x] **Article XI** — `ava-summary` SKILL.md already exists; no changes needed (routing unchanged)

### Quality Gate Check

- [x] No `[NEEDS CLARIFICATION]` markers remain in spec
- [x] No new output paths; existing paths unchanged
- [x] Downstream `next_agent` unchanged: `ava-summary-validate` after `ava-summary`

---

## 1. Technical Context

| Dimension | Choice | Source |
|---|---|---|
| Runtime | Python 3.11+ (validate_summary.py) | reference-architecture.yaml (tooling scripts) |
| Artifact discovery | `artifact-map.yaml` | `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` |
| Agent prompt language | Brazilian Portuguese | Constitution Article V |
| Timing | NTP via `src/shared/utils/ntp_time.py` | summary-agent.md existing convention |
| HTML validation | `validate_summary.py --project {project_name}` | existing CLI interface, unchanged |
| Version bump | MINOR (1.0.0 → 1.1.0) | Constitution Article X |

**Project overrides**: `projects/{project_name}/context/project-config.yaml`

---

## 2. Phase Placement

```
... -> ava-summary (F8) -> ava-summary-validate (F8.5)
```

This change does **not** alter phase placement. Step 0.5 runs inside the `ava-summary` execution flow,
before the existing `Step 1-2` block.

**Quality gate at this phase**: Summary Validator (`ava-summary-validate`) — C11 rules added here enforced as part of that gate.

Conditions for `human_gate_required: true`: unchanged (not affected by this feature).

---

## 3. Clean Architecture Alignment

```
Domain         -> NO -- agent is an LLM prompt file
Application    -> NO -- agent is an LLM prompt file
Infrastructure -> NO -- agent is an LLM prompt file
Presentation   -> NO -- agent is an LLM prompt file
```

Note: `validate_summary.py` is a standalone Python script. Its changes follow the existing function-per-rule pattern — no layered architecture applies.

Cross-layer coupling: NONE

---

## 4. Agent File Structure

Existing files modified (no new files created):

```
src/modules/ava-fabric-agents/summary/agents/
+-- summary-agent.md          <- INSERT Step 0.5 section + update MICRO tables + bump version
+-- summary-validate-agent.md <- ADD C11 row to Rule Catalog table + bump version

src/modules/ava-fabric-agents/summary/utils/
+-- validate_summary.py       <- ADD _c11_1/_c11_2/_c11_3 functions + Check() registrations

src/modules/ava-fabric-agents/summary/
+-- module.yaml               <- VERSION bump 1.0.0 -> 1.1.0
```

No new files. SKILL.md at `.github/skills/ava-summary/SKILL.md` is unchanged.

**Dispatch mode**: user-facing (existing SKILL.md; routing unchanged).

---

## 5. module.yaml Impact

Version bump only in `src/modules/ava-fabric-agents/summary/module.yaml`:

```yaml
# Change:
version: "1.0.0"
# To:
version: "1.1.0"
```

No new agent entries. Existing entries (`ava-summary`, `ava-summary-validate`) unchanged.
The **top-level** `module.yaml` at repo root is NOT updated (no new module).

---

## 6. Observability & Trace Propagation

N/A — these are LLM prompt files. `trace_id` flows through `shared-context.md` as before.

New emit lines (`[ARTIFACT-MISSING]`, `[ARTIFACT-EMPTY]`, `[ARTIFACT-CHECK]`) are stdout-only and do not mutate trace context.

---

## 7. Schema Changes

| Schema | Change Required | Description |
|---|---|---|
| agent-task.schema.json | NO | Inputs unchanged |
| agent-result.schema.json | NO | Outputs unchanged; no new artifact paths |

---

## 8. Implementation Phases

### Phase 0 — summary-agent.md: Add Step 0.5 Block

Insert the following section into `summary-agent.md` immediately **before** `## Execution Steps`:

````markdown
## Step 0.5 — Verificação de Integridade de Artefatos (Pré-Build)

> ⛔ **OBRIGATÓRIO** — Executar ANTES de qualquer geração HTML.
> SE `TIMING_MODE == FULL`: capturar `NTP_STEP05 = Bash: python src/shared/utils/ntp_time.py`
> antes de iniciar; registrar `NTP_STEP05_END` após conclusão.

**Objetivo**: Confirmar existência e tamanho > 0 de cada artefato listado em
`src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` antes de iniciar a geração HTML.

**Algoritmo**:
```
1. Ler artifact-map.yaml → lista de entradas (agent_id → primary_output / outputs_map paths)
2. Para cada path em cada entrada:
   a. Resolver caminho real: substituir prefixo "project/outputs/" por "projects/{project_name}/outputs/"
   b. Verificar existência do arquivo no disco
   c. SE não existe → emitir:
        [ARTIFACT-MISSING: {section_name}] — arquivo ausente: {relative_path}
      → adicionar {section_name} a sections_omitted
   d. SE existe E tamanho == 0 → emitir:
        [ARTIFACT-EMPTY: {section_name}] — arquivo vazio (0 bytes): {relative_path}
      → adicionar {section_name} a sections_omitted
   e. SE existe E tamanho > 0 → contabilizar como OK (sem emissão por artefato OK)
3. Emitir linha de resumo:
   [ARTIFACT-CHECK] Resultado: {ok}/{total} OK | {missing} ausentes | {empty} vazios
     Seções omitidas: [{section_name_1}, {section_name_2}, ...]
4. SE sections_omitted está vazio → emitir:
   [ARTIFACT-CHECK] OK — {total} artefatos verificados, 0 ausentes
```

**Comportamento de omissão**: Para cada seção em `sections_omitted`, ao executar o Step 3,
NÃO passar os dados dessa seção ao `build_summary_comprehensive.py`.
Injetar como único conteúdo do slot da seção:
`<!-- OMITTED: artifact missing or empty — {relative_path} -->`

**Regra**: `[ARTIFACT-MISSING]` e `[ARTIFACT-EMPTY]` são emitidos APENAS em stdout —
NUNCA no HTML final. O HTML final NÃO deve conter esses marcadores literais.
````

### Phase 1 — summary-agent.md: Update MICRO Timing Tables

Add `Step 0.5 — Verificação de Integridade` row **before** the Step 1 row in both table variants:

**FULL template** — add after NTP_START row:
```
│ Step 0.5 — Verificação de Integridade│ Descoberta │ ✅/❌/⏳ │ YYYY-MM-DDTHH:MM:SS-03:00 │ YYYY-MM-DDTHH:MM:SS-03:00 │ X hora(s), Y minuto(s) e Z segundo(s)│
```

**STATUS_ONLY template** — add before Step 1 row:
```
│ Step 0.5 — Verificação de Integridade│ ✅/❌/⏳ │
```

Also bump frontmatter: `version: 1.0.0` → `version: 1.1.0` and `date:` → `2026-07-08`.

### Phase 2 — summary-validate-agent.md: Add C11 to Rule Catalog

Add C11 row to the **Rule Catalog** table after C9:

```markdown
| **C11 Artifact Integrity** | C11.1–C11.3 | Detects unresolved `[INCOMPLETE]`/`[ARTIFACT-MISSING]` placeholders and tables with zero data rows in generated HTML |
```

Add narrative under the table:

> **C11 Artifact Integrity** — Verifica que o HTML gerado não contém marcadores de artefato ausente
> (`[INCOMPLETE]`, `[ARTIFACT-MISSING]`) não resolvidos e não contém tabelas com zero linhas de dados.
> C11.1 e C11.2 são `error` (bloqueiam promoção); C11.3 é `warn`.

Bump version to `1.1.0` in frontmatter.

### Phase 3 — validate_summary.py: Add C11 Functions + Registrations

**New functions** (insert after `_c9_3`, before the `# ════ Runner` comment block):

```python
# — C11: Artifact Integrity —

def _c11_1(ctx: Ctx) -> Result:
    """C11.1 — No [INCOMPLETE] placeholder in HTML body."""
    import re
    matches = re.findall(r'\[INCOMPLETE\]', ctx.html)
    if matches:
        return Result(False, f"found {len(matches)} [INCOMPLETE] occurrence(s) in HTML")
    return Result(True, "zero [INCOMPLETE] placeholders")

def _c11_2(ctx: Ctx) -> Result:
    """C11.2 — No unresolved [ARTIFACT-MISSING] marker in HTML body."""
    import re
    matches = re.findall(r'\[ARTIFACT-MISSING', ctx.html)
    if matches:
        return Result(False, f"found {len(matches)} [ARTIFACT-MISSING] occurrence(s) in HTML")
    return Result(True, "zero [ARTIFACT-MISSING] markers")

def _c11_3(ctx: Ctx) -> Result:
    """C11.3 — No <table> with thead but zero tbody rows (warn)."""
    import re
    tables = re.findall(r'<table[^>]*>.*?</table>', ctx.html, re.DOTALL | re.IGNORECASE)
    empty_tables = []
    for i, t in enumerate(tables):
        has_thead = bool(re.search(r'<thead', t, re.IGNORECASE))
        if not has_thead:
            continue
        tbody_content = re.search(r'<tbody[^>]*>(.*?)</tbody>', t, re.DOTALL | re.IGNORECASE)
        if not tbody_content or not re.search(r'<tr', tbody_content.group(1), re.IGNORECASE):
            empty_tables.append(i + 1)
    if empty_tables:
        return Result(False, f"empty table(s) at index(es): {empty_tables[:5]}")
    return Result(True, f"all {len(tables)} table(s) have data rows (or no thead)")
```

**New Check registrations** (insert in CHECKS list after `C9.3` entry, before the closing `]`):

```python
    # C11 Artifact Integrity
    Check("C11.1", "Artifact Integrity", "error",
          "No [INCOMPLETE] placeholder in HTML",
          "Re-run summary with all artifacts present; ensure build script resolves all placeholders.",
          _c11_1),
    Check("C11.2", "Artifact Integrity", "error",
          "No unresolved [ARTIFACT-MISSING] marker in HTML",
          "Artifact was missing during summary generation — re-run after generating the artifact.",
          _c11_2),
    Check("C11.3", "Artifact Integrity", "warn",
          "No table with thead but zero data rows",
          "Check artifact extraction in build_summary_comprehensive.py for the empty table's section.",
          _c11_3),
```

### Phase 4 — module.yaml Version Bump

```yaml
# src/modules/ava-fabric-agents/summary/module.yaml
# Change:
version: "1.0.0"
# To:
version: "1.1.0"
```

---

## 9. Complexity Tracking

| Gate | Failure Reason | Justification | Mitigating Controls |
|---|---|---|---|
| Article III (timing invariant) | Step 0.5 is a new step that must appear in MICRO table | Step 0.5 is inserted into both FULL and STATUS_ONLY MICRO templates | Tasks explicitly update both table variants |
| Pre-Step conflict | Existing `Pre-Step — Garantir Artefatos Críticos (NOVO)` handles only metrics/risks fallback | Step 0.5 is a distinct integrity gate (no fallback generation); two steps are complementary | Spec Exclusions section and research Q1 clarify the distinction |

---

## 10. Test Strategy

| Test Type | Tool | Target |
|---|---|---|
| Nominal E2E | Manual / Copilot chat | Scenario A in quickstart.md — all artifacts present |
| Missing artifact | Manual | Scenario B in quickstart.md — renamed file triggers `[ARTIFACT-MISSING]` |
| C11.1 detection | `validate_summary.py` | Scenario C in quickstart.md — injected `[INCOMPLETE]` caught, exit 1 |
| C11.2 detection | `validate_summary.py` | Injected `[ARTIFACT-MISSING` literal caught, exit 1 |
| C11.3 detection | `validate_summary.py` | HTML with empty table emits warning (not error) |
| Sophia project | Manual / CI | AC5 from PBI 2299 — exit 0, c11_errors: 0 in validation-report.json |
| Regression | Existing validate_summary.py suite | C1–C9 checks unchanged and still pass |
