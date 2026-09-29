# Agent Specification: Summary Item Correlation

**Feature Branch**: `042-summary-item-correlation`
**Created**: 2026-08-19
**Status**: Draft
**Change Type**: modify-existing (extends `ava-summary-validate` — next MINOR after v1.5.0)

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation MUST be written in **Brazilian Portuguese** per
> Constitution Article V. Frontmatter fields use mixed language: English keys,
> Portuguese content.

> **Incremental extension**: This spec extends 041-summary-self-validation-remediation,
> which is already in production. All prior clarifications from spec 041 are inherited
> as resolved constraints — they are not re-opened here. This spec addresses only
> the concrete-correlation gap discovered during real production runs
> (nopcommerce-02-cli-ava: 45 empty tables, 3 empty lists, all reporting
> "unidentified section" / "ava-summary" as section/agent_responsible).

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID (primary)** | `ava-summary-validate` (existing — MINOR version bump) |
| **Agent ID (secondary)** | `ava-summary-remediation` (existing — MINOR version bump) |
| **Version** | `ava-summary-validate` → `1.6.0` · `ava-summary-remediation` → `1.7.0` |
| **Data artifact version** | `artifact-map.yaml` → `1.1.0` (MINOR — new top-level section added) |
| **Phase** | `F8 — Summary (cross-cutting)` |
| **Module** | `summary` (`src/modules/ava-fabric-agents/summary/`) |
| **Role** | Extend the existing Deep Item Audit (C12.6/C12.7) so that every empty table or list finding carries concrete, verified identification: which HTML element ID, which `D.*` field, which origin artifact, and which agent produced (or failed to produce) the data — enabling accurate root-cause triage without manual inspection of the HTML source. |
| **Skill** | `ava-summary-validate` _(internal-only, no SKILL.md — unchanged)_ · `ava-summary-remediation` _(existing SKILL.md, routing unchanged)_ |
| **Dispatch** | Unchanged from spec 041: `ava-summary-validate` auto-triggered by `ava-summary` and `ava-summary-remediation`; `ava-summary-remediation` user-facing via existing SKILL.md |
| **New agents** | **NONE** — this extension does not create any new agent files |

> **Change Type rationale (`modify-existing`)**: All affected files already exist:
> `validate_summary.py` (extending `_c12da_6`, `_c12da_7`, adding post-processing
> deduplication), `artifact-map.yaml` (new top-level section `html_element_correlation`),
> and agent `.md` files (version bump + documentation of new finding types).
> The `module.yaml` `version` field bump (`1.5.0 → 1.6.0`) is a **Category 3** metadata
> change, not a Category 4 new-agent registration.
> Version bumps are MINOR: new observable behaviour (new finding_types in output, new
> fields in `deep-audit-report.json`, new correlation logic), no breaking schema changes.

---

## 2. Agent Frontmatter

### 2.1 `ava-summary-validate` (updated to 1.6.0)

```yaml
---
name: "ava-summary-validate"
version: "1.6.0"
description: |
  Non-regression quality gate do Summary HTML. Após o HTML ser gerado por
  build_summary_comprehensive.py, executa auditoria item a item de cada
  seção/card/tabela/chip de artefato (fases F1–F8): detecta itens vazios
  por falha (vs. vazio legítimo), artefatos ausentes do manifesto, configurações
  divergentes do build validator e diagramas Mermaid inválidos (via
  mermaid_playwright_gate.py). Emite validation-report.{md,json} com severidade
  CRITICAL/HIGH/MEDIUM/LOW e causa raiz (agente/fase/arquivo).
  A partir da v1.6.0, C12.6/C12.7 identificam CONCRETAMENTE qual elemento HTML
  (por id), qual campo D.*, qual artefato de origem e qual agente são responsáveis,
  classificando a causa raiz como missing_artifact, parser_gap ou render_gap.
  Ativa com: "validate summary", "audit summary", "check summary integrity",
  "summary validator", "summary-validate", "validar summary".
allowed-tools: Read, Bash, Glob, Grep, Write
---
```

### 2.2 `ava-summary-remediation` (updated to 1.7.0)

```yaml
---
name: "ava-summary-remediation"
version: "1.7.0"
description: |
  Agente de reparo pós-pipeline do Summary executivo. Audita HTML gerado
  (ou artefatos incompletos em outputs/), aplica correções automáticas
  (regenerar artefato faltante chamando agente responsável, corrigir path/nome
  de manifesto, re-sanitizar Mermaid), reconstrói via build_summary_comprehensive.py
  e repete a validação via ava-summary-validate até zero findings CRITICAL/HIGH
  ou atingir MAX_REMEDIATION_ATTEMPTS (configurável). A partir da v1.7.0, a
  estratégia de correção reconhece parser_gap e render_gap: nenhum dispatch de
  agente upstream é feito para esses tipos; build_summary_comprehensive.py é
  re-executado e seu stdout+stderr são capturados para rastrear qual
  parser/função JS falhou.
  Emite remediation-report.json consolidado com exit code 0/1 compatível com CI.
  Ativa com: "corrigir o summary", "remediar o summary", "@ava-summary-remediation",
  "consertar visualização do summary".
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---
```

---

## 3. Output Contract

### 3.1 `ava-summary-validate` — `deep-audit-report.json` schema (extended in v1.6.0)

The schema version is bumped from `"1.0"` to `"1.1"`. The existing `findings[]` array
is extended with two new fields per finding (only present when the element was identified
via the correlation map; both are `null` for findings from map-unknown elements):

```json
{
  "schema_version": "1.1",
  "generated_at": "<ISO-8601>",
  "project": "<project_name>",
  "html_path": "<absolute path to audited HTML>",
  "summary": {
    "critical": 0, "high": 0, "medium": 0, "low": 0,
    "promotable": true
  },
  "findings": [
    {
      "id": "DA-001",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "phase": "F1|F2|...|F8|MULTIPLE",
      "section": "<human-readable section name — from correlation map when element id is known>",
      "agent_responsible": "<ava-agent-id — from correlation map, never 'ava-summary' when id is known>",
      "artifact_path": "<relative path or null — from correlation map when resolved>",
      "html_element_id": "<value of id= attribute, or null when element has no id>",
      "d_field": "<D.* field name, e.g. 'scenarios' — from correlation map, or null>",
      "render_function": "<JS function name, e.g. 'renderScenarios()' — from correlation map, or null>",
      "finding_type": "empty_by_failure|missing_artifact|divergent_config|mermaid_error|placeholder_unresolved|table_no_rows|list_no_items|parser_gap|render_gap",
      "detail": "<what was observed>",
      "root_cause": "<why this happened>",
      "auto_correctable": false,
      "suggested_fix": "<action to take>"
    }
  ]
}
```

> **Backward compatibility**: `schema_version` bump from `"1.0"` to `"1.1"` signals
> to consumers (e.g., `ava-summary-remediation`) that `html_element_id`, `d_field`,
> and `render_function` fields are present. Consumers MUST treat these three fields as
> optional (nullable) to remain compatible with v1.0 reports produced without `--deep`
> or before this feature ships.

### 3.2 `ava-summary-remediation` — `remediation-report.json` (unchanged schema v2.0)

No schema version change for `remediation-report.json`. The new `parser_gap` and
`render_gap` finding types appear in the `unresolved_findings[]` array with
`auto_correctable: false` (same field, already present). The existing `schema_version: "2.0"`
is preserved.

### 3.3 `artifact-map.yaml` (new section `html_element_correlation`)

```yaml
# ─────────────────────────────────────────────────────────────────
# ELEMENT CORRELATION MAP
# Added: spec 042-summary-item-correlation (2026-08-19)
# Audited & corrected: Clarification Q2+Q3 (2026-08-19) — full
#   cross-reference against summary-template.html and validate_summary.py
#   regression guards C11.10/C11.15. See §Clarifications for detail.
# Purpose: Maps HTML element ids (tables/lists with fixed ids in the
#   template) to their D.* field, origin artifact, responsible agent,
#   and JavaScript render function. Consumed exclusively by _c12da_6
#   and _c12da_7 in validate_summary.py to resolve section/agent_responsible
#   and classify the root cause of empty tables/lists.
# Source of truth: summary-template.html (id= attributes + JS functions)
#   NOT summary-agent.md §"Data Source Mapping" (confirmed outdated for
#   2 dead entries and 5 wrong ids — see Clarification Q2).
# Extend this section whenever a new fixed-id table or list is added to the template.
# ─────────────────────────────────────────────────────────────────
html_element_correlation:

  # ── F1 AS-IS ───────────────────────────────────────────────────
  tb-patterns:
    d_field: "patterns"
    section: "F1 — Padrões Identificados"
    phase: "F1"
    agent_responsible: "ava-asis-solution-delphi"
    artifact_path: "project/outputs/asis/pattern-classifications.json"
    render_function: "renderPatterns()"

  tb-risks:
    d_field: "risks"
    section: "F1 — Risk Register"
    phase: "F1"
    agent_responsible: "ava-asis-gaps-risks"
    artifact_path: "project/outputs/asis/risk-register.json"
    render_function: "renderRisks()"

  # REMOVED: tb-cc — element absent from template (C11.10 requires renderComplexityTable()
  # and id="tb-complexity" to be fully removed from Inventory & Metrics section).
  # D.ccTop still populated by build_summary_comprehensive.py for C2.2/C2.10 KPIs;
  # no table renders it. See Clarification Q2.

  tb-rules:                          # was: tb-bizrules — wrong id; template uses getElementById('tb-rules')
    d_field: "bizRules"              # confirmed: renderRulesTable() at template line 6860
    section: "F1 — Regras de Negócio AS-IS"
    phase: "F1"
    agent_responsible: "ava-asis-documentation"
    artifact_path: "project/outputs/asis/docs/business-rules.md"
    render_function: "renderRulesTable()"

  tb-reqs:
    d_field: "funcReqs"
    section: "F1 — Requisitos Funcionais AS-IS"
    phase: "F1"
    agent_responsible: "ava-asis-documentation"
    artifact_path: "project/outputs/asis/docs/business-rules.md"
    render_function: "renderReqsTable()"

  tb-schema:                         # was: schema-tbody — wrong id; template uses getElementById('tb-schema')
    d_field: "dbSchema"              # confirmed: renderDBSchema() at template line 6521
    section: "F1 — Database Schema"
    phase: "F1"
    agent_responsible: "ava-asis-db-analyzer"
    artifact_path: "project/outputs/asis/db/schema-inventory.md"
    render_function: "renderDBSchema()"

  tb-sps:                            # was: sp-tbody — wrong id + wrong function
    d_field: "sps"                   # template uses getElementById('tb-sps') at line 6531
    section: "F1 — Stored Procedures" # renderSPs() does NOT exist; renderDBSchema() handles
    phase: "F1"                      # BOTH D.dbSchema→tb-schema AND D.sps→tb-sps (C11.12 confirms)
    agent_responsible: "ava-asis-db-analyzer"
    artifact_path: "project/outputs/asis/db/stored-procedures-map.md"
    render_function: "renderDBSchema()"

  # ── F2 TO-BE ───────────────────────────────────────────────────
  # REMOVED: tb-tobebc-detail — element absent from template (C11.15 regression guard
  # explicitly checks 'id="tb-tobebc-detail"' in ctx.html and FAILS if found;
  # renderTOBEBCDetail() was fully removed). See Clarification Q2.

  tb-tobebc:                         # was: tobebc-tbody — wrong id; template uses getElementById('tb-tobebc')
    d_field: "tobebc"                # confirmed: renderTOBEBC() at template line 6258
    section: "F2 — Bounded Contexts TO-BE"
    phase: "F2"
    agent_responsible: "ava-tobe-architecture-design"
    artifact_path: "project/outputs/tobe/bounded-context-map.md"
    render_function: "renderTOBEBC()"

  tb-endpoints:                      # was: endpoints-tbody — wrong id + wrong function
    d_field: "apiEndpoints"          # template uses getElementById('tb-endpoints') at line 7277
    section: "F2 — API Endpoints TO-BE" # renderEndpoints() does NOT exist; actual function is
    phase: "F2"                      # renderAPISurface() (template line 7276). See Clarification Q3.
    agent_responsible: "ava-tobe-architecture-design"
    artifact_path: "project/outputs/tobe/api-map.md"
    render_function: "renderAPISurface()"

  # ── F5 QA ──────────────────────────────────────────────────────
  tb-scen:
    d_field: "scenarios"
    section: "F5 — Cenários & Casos"
    phase: "F5"
    agent_responsible: "ava-qa-bridge-fastqa-tobe"
    artifact_path: "project/outputs/qa/scenario-generator/scenario-register.json"
    render_function: "renderScenarios()"

  tb-defects:
    d_field: "defects"
    section: "F5 — Defeitos Identificados"
    phase: "F5"
    agent_responsible: "ava-qa-defect-identifier"
    artifact_path: "project/outputs/qa/defect-identifier-report.md"
    render_function: "renderDefects()"
```

> **Extension rule**: When a new fixed-id table or list is added to the Summary HTML
> template, a corresponding entry MUST be added to `html_element_correlation` before
> the feature ships. Elements without fixed ids (dynamically generated rows, anonymous
> lists) are NOT covered by this map — C12.6/C12.7 fall back to the existing heading
> heuristic for those.

---

## 4. Detailed Feature Behaviour

### 4.1 Extended Decision Logic for `_c12da_6` (table_no_rows) and `_c12da_7` (list_no_items)

The two functions are refactored to apply the following per-element logic BEFORE emitting a finding.
All existing detection logic (tbody-present/empty for C12.6, empty ul/ol for C12.7) is preserved —
only what happens AFTER detection changes.

```
# For each empty table <tbody> (C12.6) or empty list <ul>/<ol> (C12.7):

STEP 1 — Resolve element id
  id = re.search(r'id="([^"]+)"', element_html)
  IF id is None:
    → use existing heading-heuristic for section/agent_responsible (fallback)
    → emit table_no_rows / list_no_items finding (unchanged behaviour)
    → CONTINUE to next element

STEP 2 — Look up id in html_element_correlation map
  corr = html_element_correlation.get(id)
  IF corr is None:
    → use existing heading-heuristic fallback (gap in inventory, not a bug)
    → emit table_no_rows / list_no_items finding with note: "element id not in correlation map"
    → CONTINUE to next element

STEP 3 — Gate: phase not yet executed                    ← NEW (Clarification Q1, 2026-08-19; corrected Q1-R2, 2026-08-19)
  IF NOT _is_phase_done(ctx, corr["phase"]):
    → element is legitimately empty; phase has not been executed yet
    → NO finding is emitted (same pattern as C12.1 in spec 041 §4.1:
       "empty_legitimate (INFO, not a finding)"; severity="INFO" is NOT
       a valid enum value in §3.1 and does not appear in findings[])
    → Any observability signal (e.g. debug log) goes to stderr/log only,
       never to deep-audit-report.json
    → CONTINUE to next element
  # _is_phase_done() checks D.agentStatus for ≥1 agent with the phase prefix
  # having status 'done' — same implementation used by C12.1 and C12.3.
  # This gate closes the inherited bug (spec 041 C12.6/C12.7 did not call
  # _is_phase_done(); the refactor in 042 is the correct moment to fix it).

STEP 4 — Resolve origin artifact on disk                 ← was STEP 3
  artifact_full_path = ctx.project_dir / corr["artifact_path"]
  IF NOT artifact_full_path.exists() OR artifact_full_path.stat().st_size == 0:
    → classify as missing_artifact
    → CHECK deduplication (§4.4): if artifact_path already flagged by C12.3, SUPPRESS this finding
    → ELSE emit missing_artifact finding with:
        section           = corr["section"]
        agent_responsible = corr["agent_responsible"]
        artifact_path     = corr["artifact_path"]
        html_element_id   = id
        d_field           = corr["d_field"]
        render_function   = corr["render_function"]
        finding_type      = "missing_artifact"      # ← replaces table_no_rows / list_no_items
        auto_correctable  = True                    # existing C12.3 correction strategy applies
    → CONTINUE to next element

STEP 5 — Check D.* field in the HTML data block          ← was STEP 4
  raw_slice = _extract_json_slice(ctx.html, corr["d_field"])
  d_field_has_data = raw_slice is not None and len(raw_slice.strip()) > 4
                     # len > 4 excludes '[]', '{}', '""', 'null'

  IF NOT d_field_has_data:
    → classify as parser_gap (§4.3)
    → emit parser_gap finding with:
        section           = corr["section"]
        agent_responsible = corr["agent_responsible"]
        artifact_path     = corr["artifact_path"]
        html_element_id   = id
        d_field           = corr["d_field"]
        render_function   = corr["render_function"]
        finding_type      = "parser_gap"
        severity          = "HIGH"
        auto_correctable  = False
        suggested_fix     = (
          f"Artifact '{corr['artifact_path']}' exists but D.{corr['d_field']} "
          f"is empty/null in the HTML. "
          f"Re-run build_summary_comprehensive.py and inspect its captured "
          f"output to find the parser responsible for D.{corr['d_field']} — it "
          f"either did not run, did not find the expected pattern, or was not "
          f"called in the data-injection function."
        )
    → CONTINUE to next element

STEP 6 — D.* field has data but element still empty → render_gap  ← was STEP 5
  → classify as render_gap (§4.3)
  → emit render_gap finding with:
        section           = corr["section"]
        agent_responsible = corr["agent_responsible"]
        artifact_path     = corr["artifact_path"]
        html_element_id   = id
        d_field           = corr["d_field"]
        render_function   = corr["render_function"]
        finding_type      = "render_gap"
        severity          = "MEDIUM"
        auto_correctable  = False
        suggested_fix     = (
          f"D.{corr['d_field']} has data in the HTML but #{id} renders empty. "
          f"Inspect JS function {corr['render_function']}: it may read a wrong "
          f"key from D.*, be absent from init(), or fail silently on a TypeError."
        )
```

> **Invariant — section/agent_responsible accuracy**: When an element's `id` IS in the
> correlation map, the emitted finding MUST use `corr["section"]` and
> `corr["agent_responsible"]` — never the heading-heuristic result and never the
> generic `"ava-summary"` / `"unidentified section"`. The heading heuristic fallback
> is reserved exclusively for elements not covered by the map (inventory gap).

### 4.2 Deduplication Rule Extension (extending §4.1 of spec 041)

The existing deduplication invariant (spec 041 §4.1) is extended:

> A finding whose `artifact_path` is already present in a `missing_artifact` finding
> emitted by C12.3 MUST NOT be re-emitted by C12.6 or C12.7 as a separate
> `missing_artifact` finding. Exactly ONE finding per artifact path must appear in
> `deep-audit-report.json`.

**Implementation**: After all DEEP_CHECKS run and before `_write_deep_audit_json`
serialises the output, a post-processing deduplication pass removes any `missing_artifact`
findings from C12.6/C12.7 whose `artifact_path` matches an existing C12.3 `missing_artifact`
finding. The C12.3 finding is the one that survives (it carries the canonical artifact-level
context; C12.6/C12.7 add element-level context that is not needed when the root cause is
already identified as a missing artifact).

The full deduplication matrix now reads:

| Condition | Surviving finding_type | Suppressed finding_type |
|---|---|---|
| `<tbody>` absent (no tbody element at all) | C11.41 only | — (C12.6 never fires; mutually exclusive) |
| `<tbody>` present, zero `<tr>` | C12.6 fires → further classified below | — |
| `<ul>`/`<ol>` zero `<li>` | C12.7 fires → further classified below | — |
| Artifact for element missing → also caught by C12.3 | C12.3 `missing_artifact` | C12.6/C12.7 `missing_artifact` (suppressed) |
| Artifact for element missing → NOT caught by C12.3 | C12.6/C12.7 `missing_artifact` | — |
| Artifact exists, D.* field empty | C12.6/C12.7 `parser_gap` | — |
| Artifact exists, D.* field has data, element empty | C12.6/C12.7 `render_gap` | — |
| `[INCOMPLETE]` token | C11.39 only | C12.2 never covers this (mutually exclusive) |
| `[ARTIFACT-MISSING]` token | C11.40 only | C12.2 never covers this (mutually exclusive) |

### 4.3 New Finding Types

This feature extends the `finding_type` enum (§3.1 of spec 041) with two new values:

#### `parser_gap`

| Attribute | Value |
|---|---|
| **Definition** | Origin artifact exists and has content, but the corresponding `D.*` field in the generated HTML is empty, null, or an empty collection (`[]` / `{}` / `""`) |
| **Root cause** | Bug in `build_summary_comprehensive.py`: the parser responsible for `D.{d_field}` either did not run, failed silently, matched zero patterns in the artifact, or was not invoked in the data-injection function |
| **Severity** | `HIGH` — real data exists in the project but is invisible in the Summary; the executive report is materially incomplete |
| **auto_correctable** | `false` in v1 (same semantics as Clarification Q7 of spec 041: `auto_correctable` is a capability flag, not a dispatch guarantee; no reimplementation of parser logic is expected in this version) |
| **Remediation action** | Re-run `build_summary_comprehensive.py`; attach its captured stdout+stderr excerpt to `suggested_fix`; fall through to MANUAL — a developer must fix the parser |
| **Does NOT dispatch upstream agents** | The artifact already exists; running the upstream agent again would produce the same artifact; the problem is the parser reading it, not the agent producing it |

#### `render_gap`

| Attribute | Value |
|---|---|
| **Definition** | `D.{d_field}` has non-empty data in the generated HTML (confirmed by `_extract_json_slice`), but the DOM element `#{html_element_id}` still renders with zero rows/items |
| **Root cause** | Bug in the JavaScript render function (`{render_function}`) embedded in the Summary template: the function reads a wrong key from `D.*`, is absent from `init()`, or throws a silent TypeError |
| **Severity** | `MEDIUM` — the data is present and recoverable without re-execution of any upstream agent; only the JS rendering layer is broken |
| **auto_correctable** | `false` in v1 (same rationale as `parser_gap`; no reimplementation of JS render functions is expected in this version) |
| **Remediation action** | Re-run `build_summary_comprehensive.py`; include name of `render_function` and `html_element_id` in `suggested_fix`; fall through to MANUAL — a developer must fix the template's render function |
| **Does NOT dispatch upstream agents** | Both the artifact and the D.* data are already correct; the problem is purely in the HTML template's rendering layer |

### 4.4 Severity Mapping Extension (extending §4.2 of spec 041)

The complete severity mapping table for `deep-audit-report.json`, with the two new rows appended:

| Severity | Condition |
|---|---|
| **CRITICAL** | Missing artifact that blocks a client-facing phase; unresolved `{{X}}` placeholder in the HTML title, project name, or KPI section; Mermaid diagram that was explicitly requested fails to render |
| **HIGH** | KPI tile value is `0` or `N/E` when the backing artifact has non-empty data; table with zero rows in a completed phase (`table_no_rows`); missing artifact for a non-blocking but contractually required output; **`parser_gap`** — artifact exists but the D.* field is empty (data silently lost in the build step) |
| **MEDIUM** | Divergent file name or path between `artifact-map.yaml` and actual filesystem; Mermaid diagram in a secondary section fails to render; list with zero items in a completed phase (`list_no_items`); **`render_gap`** — D.* field has data but the JS render function fails to populate the DOM element |
| **LOW** | Schema version mismatch (artifact valid but older schema); INFO-level placeholder visible only in secondary tooltips |

### 4.5 Auto-Correction Strategy Extension (extending §4.4 of spec 041)

The remediation loop in `ava-summary-remediation` v1.7.0 adds two new branches:

```
# Extended correction loop — new branches for parser_gap and render_gap:
  f. parser_gap (new):
       DO NOT dispatch upstream agent.
       Action: re-run build_summary_comprehensive.py for the project, capturing
       its stdout+stderr output.
       The captured output surfaces which parser function produced an empty result for D.{d_field}.
       Record the output excerpt in finding.suggested_fix.
       Set finding.auto_correctable = false (no automated fix strategy in v1).
       → finding moves to unresolved_findings with manual remediation guidance.

  g. render_gap (new):
       DO NOT dispatch upstream agent or rebuild artifact.
       Action: re-run build_summary_comprehensive.py for the project, capturing
       its stdout+stderr output.
       The captured output confirms D.{d_field} is populated; suggested_fix names the
       failing render_function and html_element_id for the developer.
       Set finding.auto_correctable = false (no automated JS patching in v1).
       → finding moves to unresolved_findings with manual remediation guidance.
```

> **Invariant (inherited from spec 041, extended)**: `parser_gap` and `render_gap`
> findings with `auto_correctable: false` MUST NOT consume `MAX_REMEDIATION_ATTEMPTS`
> budget for structural-failure reasons (same invariant as structural dispatch failures
> for `missing_artifact`). If all remaining CRITICAL/HIGH findings are `parser_gap` or
> `render_gap` (both `auto_correctable: false`), the loop MUST break immediately after
> recording them as `unresolved_findings`, rather than exhausting the retry budget on
> findings that have no automatic resolution path.
>
> **Severity gate**: `parser_gap` is HIGH → contributes to the `BLOCKED` gate condition
> (≥1 unresolved HIGH → `final_status: BLOCKED`, exit code 1). `render_gap` is MEDIUM
> → does not block promotion; reported as residual noise under `final_status: PARTIAL`.

> **Calling-context and annotation requirement** _(Clarifications Q1+Q2, 2026-08-19 rodada 3)_:
> In the current repository state (spec 041 N1-N6 patches uncommitted), `phase8_deep_audit_triage()`
> is invoked directly from `main()`. This is by design — `parser_gap` and `render_gap` are
> non-dispatchable by spec invariant, so they fit correctly in a standalone triage phase rather
> than inside an agent-dispatch loop. When `run_remediation_loop` is implemented
> (`cat3-remediation-loop-041`), the call site moves from `main()` to the loop; the function
> itself is preserved as the non-dispatchable branch handler. See §7 Dependencies for the
> full future-dependency declaration.
>
> **Required docstring annotation**: Task 3.1 in `/speckit.tasks` MUST require the following
> NOTE paragraph inside `phase8_deep_audit_triage()`'s docstring:
> *"NOTE: Called directly from `main()` until `run_remediation_loop` (spec 041,
> `cat3-remediation-loop-041`) is implemented. At that point, this function becomes the
> non-dispatchable branch handler inside the loop — do NOT delete or replace; update the
> call site from `main()` to `run_remediation_loop`."*

---

## 5. User Scenarios (Given-When-Then)

> **Language convention**: Story descriptions in Brazilian Portuguese.
> Acceptance scenarios in English for BDD traceability.

### Scenario 1 — Nominal Path: Known-id Empty Table Reports Real Agent (Priority: P1)

**Story**: Como engenheiro de qualidade, quero que ao rodar `--deep` sobre um projeto real
com tabelas vazias (ex.: nopcommerce-02-cli-ava), o `deep-audit-report.json` apresente o
agente e a seção REAIS — nunca mais "unidentified section" / "ava-summary" — para qualquer
elemento cujo `id` esteja no mapa de correlação.

**Why this priority**: This is the primary acceptance criterion — the production regression
that motivated this feature.

**Acceptance Scenarios**:

1. **Given** a Summary HTML where `id="tb-scen"` exists with an empty `<tbody>`,
   **When** `validate_summary.py --deep` runs,
   **Then** the C12.6 finding for `tb-scen` reports:
   `section: "F5 — Cenários & Casos"`,
   `agent_responsible: "ava-qa-bridge-fastqa-tobe"`,
   `html_element_id: "tb-scen"`,
   `d_field: "scenarios"`,
   `render_function: "renderScenarios()"`.

2. **Given** the same HTML, **Then** `section` is NEVER `"unidentified section"` and
   `agent_responsible` is NEVER `"ava-summary"` for any element whose `id` appears in
   `html_element_correlation`.

3. **Given** a table with no `id` attribute (dynamically generated, no fixed id),
   **When** C12.6 fires for it, **Then** the heading-heuristic fallback is used and
   the finding note includes `"element id not in correlation map"` — no crash, no
   silent omission.

---

### Scenario 2 — Root-Cause Classification: parser_gap vs render_gap (Priority: P1)

**Story**: Como desenvolvedor responsável pelo build do Summary, quero que o relatório de
auditoria me diga se o problema está no parser Python ou na função JS de renderização —
sem precisar ler o HTML manualmente.

**Why this priority**: The two failure modes have completely different repair workflows;
conflating them forces manual investigation on every finding.

**Acceptance Scenarios**:

1. **Given** a project where `scenario-register.json` exists and has 12 scenario entries,
   but `D.scenarios` in the HTML is `[]` (empty array),
   **When** C12.6 audits `id="tb-scen"`,
   **Then** the finding is classified as `parser_gap` with `severity: HIGH` and
   `suggested_fix` names the parser responsible for `D.scenarios`.

2. **Given** a project where `scenario-register.json` exists, `D.scenarios` in the HTML
   has 12 entries, but `id="tb-scen"` renders with zero `<tr>` rows,
   **When** C12.6 audits `id="tb-scen"`,
   **Then** the finding is classified as `render_gap` with `severity: MEDIUM` and
   `suggested_fix` names `renderScenarios()` as the failing render function.

3. **Given** a `parser_gap` finding, **When** `ava-summary-remediation` processes it,
   **Then** `build_summary_comprehensive.py` is re-run, its stdout+stderr output is
   captured, and the finding moves to `unresolved_findings` with `auto_correctable: false`
   and the output excerpt in `suggested_fix`. No upstream agent is dispatched.

4. **Given** a `render_gap` finding, **When** `ava-summary-remediation` processes it,
   **Then** the loop records the finding as unresolvable-automatically, attaches the
   `render_function` name and `html_element_id` to `suggested_fix`, and does NOT dispatch
   any agent or rebuild any artifact.

---

### Scenario 3 — Deduplication: missing_artifact not Double-Reported (Priority: P1)

**Story**: Como usuário do pipeline, quero que o mesmo problema raiz apareça exatamente
uma vez no relatório — não como `missing_artifact` (C12.3) E como `table_no_rows` (C12.6).

**Why this priority**: Double-reporting inflates severity counts and misleads automated
triage tools.

**Acceptance Scenarios**:

1. **Given** `scenario-register.json` is absent from disk AND `id="tb-scen"` has an
   empty tbody, **When** the deep audit runs, **Then** exactly ONE finding is emitted
   for `scenario-register.json` — either from C12.3 or from C12.6, never both.
   The surviving finding uses `finding_type: "missing_artifact"` (not `table_no_rows`).

2. **Given** the above, **Then** `deep-audit-report.json.findings` contains no two entries
   with identical `artifact_path` and `finding_type: "missing_artifact"`.

3. **Given** `risk-register.json` is absent AND is already flagged by C12.3,
   **When** C12.6 processes `id="tb-risks"`,
   **Then** the C12.6 `missing_artifact` finding for the same path is suppressed in
   the post-processing deduplication pass.

---

### Scenario 4 — Map Coverage: Unknown ID Falls Back Gracefully (Priority: P2)

**Story**: Como mantenedor do template, quero que tables ou listas com ids não mapeados
(gaps de inventário) sejam reportadas com um fallback razoável — não com um crash ou
uma supressão silenciosa.

**Why this priority**: Template evolves; new ids will be added before the map is updated.

**Acceptance Scenarios**:

1. **Given** the HTML contains `id="tb-new-feature"` which is NOT in `html_element_correlation`,
   **When** C12.6 fires for it, **Then** the finding uses the heading-heuristic for
   `section`, sets `agent_responsible: "ava-summary"` (existing fallback),
   `finding_type: "table_no_rows"`, `html_element_id: "tb-new-feature"`,
   `d_field: null`, `render_function: null`, and includes a note:
   `"element id not in correlation map — update artifact-map.yaml html_element_correlation"`.

2. **Given** the above, **Then** no exception is raised, the audit continues processing
   remaining elements, and `deep-audit-report.json` is still written.

---

### Scenario 5 — Phase Gate: Unexecuted Phase Produces No Finding (Priority: P1)

**Story**: Como CI engineer, quero que elementos de fases ainda não executadas (ex.: F5-QA
em um projeto que só rodou F1+F2) sejam silenciosamente ignorados pelo auditor — sem nenhum
finding emitido — em vez de serem classificados como `missing_artifact`/`parser_gap`
(CRITICAL/HIGH) e bloquearem a promoção de fases já concluídas.
(Corrected: Clarification Q1-R2, 2026-08-19 — see §Clarifications.)

**Why this priority**: Without STEP 3 gate, any pipeline run that has not completed all
phases would receive spurious CRITICAL/HIGH findings for legitimately empty elements,
contradicting the invariant established in spec 041 §4.1 C12.1.
(Added: Clarification Q1, 2026-08-19.)

**Acceptance Scenarios**:

1. **Given** a project where F5 (QA) has NOT been executed (`D.agentStatus` has no F5 agent
   with status `"done"`), AND `id="tb-scen"` has an empty `<tbody>`,
   **When** `validate_summary.py --deep` runs,
   **Then** NO finding is emitted for `tb-scen` — `findings[]` in `deep-audit-report.json`
   contains zero entries with `html_element_id: "tb-scen"`. The element is silently skipped
   (same semantics as C12.1 "empty_legitimate (INFO, not a finding)" in spec 041 §4.1).

2. **Given** the above, **Then** `deep-audit-report.json.summary.promotable` is NOT
   set to `false` on account of `tb-scen`, and neither the CRITICAL nor HIGH nor LOW counter
   in `summary{}` is incremented for this element.

3. **Given** a project where F5 HAS been executed AND `id="tb-scen"` is still empty,
   **When** `validate_summary.py --deep` runs,
   **Then** `_is_phase_done(ctx, "F5")` returns `True`, the STEP 3 gate does not fire,
   and STEP 4 (artifact resolution) proceeds normally, potentially classifying the element
   as `missing_artifact`, `parser_gap`, or `render_gap`.

---

### Scenario 6 — Remediation Loop: parser_gap Does Not Exhaust Retry Budget (Priority: P1)

**Story**: Como CI engineer, quero que findings irremediáveis automaticamente (parser_gap)
não desperdicem as tentativas de remediação que poderiam corrigir outros findings
auto_correctable.

**Why this priority**: Retry budget is finite; structural failures must not crowd out
fixable issues.

**Acceptance Scenarios**:

1. **Given** the deep audit emits one `parser_gap` (HIGH, `auto_correctable: false`)
   and one `missing_artifact` (CRITICAL, `auto_correctable: true`),
   **When** the remediation loop runs,
   **Then** the `missing_artifact` correction is attempted (agent dispatched), the
   `parser_gap` is immediately moved to `unresolved_findings` without consuming an
   attempt, and `MAX_REMEDIATION_ATTEMPTS` is preserved for the `missing_artifact`.

2. **Given** all remaining findings are `parser_gap` or `render_gap` after the first
   remediation attempt, **When** the loop evaluates them, **Then** the loop breaks
   immediately (no further attempts consumed), `final_status` is `BLOCKED` (≥1 unresolved
   HIGH from `parser_gap`), and `unresolved_findings` lists each with `auto_correctable: false`.

---

## 6. Quality Gate Requirements

- [x] Agent IDs follow `ava-{phase}-{role}` pattern — both are existing, registered agents (Article II)
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [ ] `module.yaml` `version` field updated from `1.5.0` → `1.6.0` (Article IV — metadata bump, Category 3 task)
- [x] All output paths use lowercase `{project_name}` and correct phase folder `outputs/summary/` (Article II)
- [x] BDD scenarios cover nominal (S1), root-cause classification (S2), deduplication (S3), fallback (S4), phase-not-done gate (S5), and retry-budget gate (S6) paths (Article VI)
- [x] Security sub-pipeline impact: none — this extension reads security outputs for correlation but does not modify the security pipeline (Article VII)
- [x] No technology versions hardcoded — correlation map is data-driven from `artifact-map.yaml`, no hardcoded IDs in Python (Article I)
- [x] Skill/Agent split: unchanged from spec 041 — `ava-summary-validate` internal-only, `ava-summary-remediation` user-facing via existing SKILL.md (Article XI)
- [x] No new SKILL.md — routing unchanged (Article XI)
- [x] `--deep` flag backward-compatibility preserved — existing callers without `--deep` execute C1–C11 only; C12.6/C12.7 new logic runs only within `--deep` mode (Article I / spec 041 §4.5)
- [x] `auto_correctable: false` for both `parser_gap` and `render_gap` in v1 — inheriting Clarification Q7 semantics from spec 041 (capability flag, not dispatch guarantee)
- [x] Deduplication invariant declared: same artifact_path never produces both a C12.3 AND a C12.6/C12.7 `missing_artifact` finding
- [x] No `[NEEDS CLARIFICATION]` markers remain

---

## 7. Dependencies

| Dependency | Agent / Script | Reason |
|---|---|---|
| Summary builder | `build_summary_comprehensive.py` | Re-invoked for `parser_gap`/`render_gap` triage, with stdout+stderr captured via `run_script()`; exclusive HTML producer (existing invariant) |
| Deep Item Audit v1.5.0 | `validate_summary.py` (spec 041, C12.6/C12.7) | Extended in-place; the existing `_c12da_6`/`_c12da_7` functions are refactored, not replaced |
| Artifact manifest | `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` | Extended with new `html_element_correlation` section (v1.0.1 → v1.1.0) |
| Data Source Mapping | `summary-agent.md` §§ "D.* Field Schemas" / "Data Source Mapping" | Source of truth for populating `html_element_correlation` — existing documentation consumed, not re-created |
| JSON slice extractor | `_extract_json_slice()` in `validate_summary.py` | Reused to check `D.{d_field}` presence without new parsing infrastructure |
| Deduplication post-pass | `_write_deep_audit_json()` in `validate_summary.py` | Extended with artifact_path deduplication logic between C12.3 and C12.6/C12.7 findings |
| Remediation loop | `remediate_summary.py` | Extended with `parser_gap`/`render_gap` branches (cases `f` and `g` in §4.5) |
| Project config | `projects/{project_name}/context/project-config.yaml` | Resolves artifact base paths at runtime |
| Spec 041 patches N1-N6 _(future dependency)_ | `remediate_summary.py` — `run_remediation_loop`, `_dispatch_correction`, `_IMPLEMENTED_DISPATCH_STRATEGIES` | **NOT committed in current branch** (grep confirmed zero matches). Feature 042 proceeds independently via `phase8_deep_audit_triage()`. When N1-N6 are committed, this function becomes the non-dispatchable branch handler inside `run_remediation_loop` — call site moves from `main()` to the loop; function itself is preserved. Consolidation tracked as `cat3-remediation-loop-041` (plan.md §13). _(Clarification Q1, 2026-08-19 rodada 3.)_ |

---

## 8. Exclusions

- **No new Python HTML parsing library** — all element-id extraction uses the existing regex patterns already present in `validate_summary.py`; `BeautifulSoup` or equivalent is explicitly forbidden (spec 041 architecture constraint).
- **No new correlation framework** — `html_element_correlation` is a plain YAML dict consumed by the existing `_load_artifact_map()` loader; no new config-parsing infrastructure.
- **No reimplementation of parser logic** — `parser_gap` and `render_gap` report the problem and name the responsible function; they do not attempt to fix or re-implement `build_summary_comprehensive.py` parsers or JS render functions.
- **No new SKILL.md** — routing for `ava-summary-remediation` is unchanged; `ava-summary-validate` remains internal-only.
- **No automated JS patching** — `render_gap` correction in v1 is MANUAL; no automated template modification.
- **No automated Python parser patching** — `parser_gap` correction in v1 is MANUAL.
- **No new agents** — this entire feature is implemented by modifying three existing files (`validate_summary.py`, `artifact-map.yaml`, `remediate_summary.py`) and bumping version fields in agent `.md` files.
- **No changes to C12.1–C12.5** — existing checks are untouched by this extension.
- **No changes to C1–C11** — existing non-deep checks are untouched.
- **No suíte de testes automatizados em Python** — per scope decision inherited from spec 041: validation via manual protocol, same convention as spec 041 task 5.1.

---

## 9. Assumptions

1. **`html_element_correlation` section is the extension mechanism**: The YAML key under
   `html_element_correlation` is the exact `id=` attribute value from the HTML template.
   The data in `summary-agent.md §§ "D.* Field Schemas"` and `"Data Source Mapping"` is the
   authoritative source for populating this section — no new discovery work is required beyond
   what is already documented.

2. **Minimum initial inventory covers all active ids referenced in the template**:
   The `html_element_correlation` section ships with **10** verified entries covering
   `tb-patterns`, `tb-risks`, `tb-rules`, `tb-reqs`, `tb-schema`, `tb-sps`,
   `tb-tobebc`, `tb-endpoints`, `tb-scen`, `tb-defects`.
   Dead entries `tb-cc` (element removed per C11.10) and `tb-tobebc-detail`
   (element removed per C11.15) are explicitly excluded. Additional ids from the
   template can be added as `html_element_correlation` entries in future patches
   without a MINOR bump (pure data extension).
   **Source of truth for this section**: `summary-template.html` `id=` attributes
   and JS function names — NOT `summary-agent.md §"Data Source Mapping"` which was
   found to be outdated for 7 of the original 12 entries. (Clarification Q2+Q3.)

3. **`_extract_json_slice(ctx.html, d_field)` is reliable for presence check**:
   This function already exists in `validate_summary.py` and is used by multiple
   existing checks (C12.1 and others). Its contract (returns `None` on miss, raw slice
   string on hit) is trusted for the `parser_gap` vs `render_gap` branch decision.
   A slice of length ≤ 4 characters is treated as effectively empty (`[]`, `{}`,
   `""`, `null`).

4. **Artifact path resolution is project-relative**: Paths in `html_element_correlation`
   follow the same `project/outputs/...` prefix convention as the rest of `artifact-map.yaml`.
   `_c12da_6`/`_c12da_7` resolve them against `ctx.project_dir` (already available in
   `Ctx`), exactly as `_c12da_3` does for C12.3 artifact checks.

5. **Post-processing deduplication pass does not change finding IDs**: Existing findings
   from C12.3 keep their original `id` (`DA-NNN`). Suppressed C12.6/C12.7 `missing_artifact`
   findings are simply omitted from the final JSON — they do not appear with a
   `"suppressed": true` flag, to keep the schema clean.

6. **`parser_gap` severity is HIGH, not CRITICAL**: The data is present in the project;
   only the build step failed to include it. CRITICAL is reserved for blocking
   client-facing artifacts or title-level placeholder failures. A `parser_gap` is
   a reproducible failure with a clear, named repair action — HIGH is appropriate.

7. **`render_gap` is not a regression in C12.6/C12.7 detection**: The original
   C12.6/C12.7 already fired for these elements. The new logic only changes the
   `finding_type`, `section`, `agent_responsible`, and `suggested_fix` — the element
   was already being detected.

---

## 10. Success Criteria

| Criterion | Measure |
|---|---|
| Real section/agent identification | Running `--deep` over nopcommerce-02-cli-ava (or any project with tables/lists whose ids are in `html_element_correlation`), `deep-audit-report.json` contains zero findings with `section: "unidentified section"` or `agent_responsible: "ava-summary"` for those elements |
| Root-cause triage accuracy | Every empty element in the map results in exactly ONE outcome: ① NO finding emitted (when phase not yet executed — `_is_phase_done()` returns `False`, same as C12.1 empty_legitimate semantics in spec 041); or ② exactly one of `missing_artifact`, `parser_gap`, or `render_gap` finding — never `table_no_rows` or `list_no_items` when the id is in the map |
| Deduplication enforced | No `artifact_path` appears in two separate `missing_artifact` findings simultaneously in `deep-audit-report.json` |
| Fallback does not crash | Elements with ids absent from `html_element_correlation` produce a `table_no_rows`/`list_no_items` finding with `html_element_id` set and a note about the inventory gap — no exception, no suppression |
| `parser_gap`/`render_gap` in enum | `finding_type` values `parser_gap` and `render_gap` appear in the schema documentation (§3.1) and in the Severity Mapping table (§4.4) with their own entries |
| Retry budget preserved | `parser_gap`/`render_gap` findings with `auto_correctable: false` do not consume `MAX_REMEDIATION_ATTEMPTS`; the loop breaks immediately when only these finding types remain |
| Backward compatibility | Existing calls to `validate_summary.py --project X` (no `--deep`) produce identical output to v1.5.0; `deep-audit-report.json` schema v1.1 is backward-compatible with v1.0 consumers treating `html_element_id`/`d_field`/`render_function` as optional nullable fields |
| `render_gap` does not block promotion | A project with only `render_gap` findings (MEDIUM) yields `final_status: PARTIAL`, exit code 0, and the summary IS promotable |

---

## Clarifications

### Session 2026-08-19

- Q: §4.1 decision tree never checks `_is_phase_done()` before classifying empty elements — contradicts C12.1 and spec 041 §4.1 for phases not yet executed. Should a gate be added inside the refactor, or deferred as a separate bug? → A: Option A — add explicit STEP 3 gate inside the 042 refactor of `_c12da_6`/`_c12da_7`; both functions confirmed to NOT call `_is_phase_done()` in production (validate_summary.py lines 3258-3371). Function exists at line 2836 and is called by C12.1/C12.3 already. Since 042 is already refactoring these two functions, fixing both the correlation logic AND the legitimate-empty gate in the same changeset avoids re-touching the same code in a future spec.

- Q: Full audit of §3.3 `html_element_correlation` inventory against `summary-template.html` and regression guards C11.10/C11.15. Which approach — remove only the 2 confirmed-dead entries, or audit all 12? → A: Option C (full audit) — cross-reference of all 12 original entries against the actual template `id=` attributes and JS function names revealed 7 problematic entries (2 dead, 5 wrong ids). Findings: `tb-cc` DEAD (C11.10 requires removal of `renderComplexityTable()`/`tb-complexity`; id `tb-cc` never existed in template); `tb-tobebc-detail` DEAD (C11.15 explicitly checks `'id="tb-tobebc-detail"' in ctx.html` and FAILS if found); `tb-bizrules` WRONG ID → `tb-rules` (template line 6860: `getElementById('tb-rules')`); `schema-tbody` WRONG ID → `tb-schema` (template line 3326: `<tbody id="tb-schema">`); `tobebc-tbody` WRONG ID → `tb-tobebc` (template line 3872: `<tbody id="tb-tobebc">`); `endpoints-tbody` WRONG ID → `tb-endpoints` (template line 7277: `getElementById('tb-endpoints')`); `sp-tbody` WRONG ID → `tb-sps` (template line 6531: `getElementById('tb-sps')`). All 7 corrected in §3.3; 5 verified correct entries unchanged. Source of truth revised: `summary-template.html` (not `summary-agent.md §"Data Source Mapping"` which was outdated for 7 entries).

- Q: `sp-tbody` maps to `render_function: "renderSPs()"` but C11.12 checks `renderDBSchema()` for BOTH dbSchema and sps; `renderSPs()` appears to not exist. Confirm before finalizing. → A: Option A — confirmed by template code: `renderSPs()` does NOT exist anywhere in `summary-template.html`. `renderDBSchema()` (template line 6517) handles both `D.dbSchema → getElementById('tb-schema')` (line 6521) and `D.sps → getElementById('tb-sps')` (line 6531) in a single function. C11.12 (`_c11_12`, validate_summary.py line 1229) also confirms this by calling `_extract_js_function(ctx.html, "renderDBSchema")` and checking both `'dbSchema' in body` and `'sps' in body`. Corrected as part of Q2 audit: `sp-tbody` → `tb-sps`, `renderSPs()` → `renderDBSchema()`. Similarly, `endpoints-tbody` had `render_function: "renderEndpoints()"` — `renderEndpoints()` also does not exist; the actual function is `renderAPISurface()` (template line 7276). Both corrected in §3.3.

### Session 2026-08-19 (rodada 2)

- Q: STEP 3 (phase-gate, added by Clarification Q1) emite `severity="INFO"` e `finding_type="empty_legitimate"`, mas o enum de `severity` em §3.1 aceita apenas `CRITICAL|HIGH|MEDIUM|LOW` (sem `INFO`) e a semântica de C12.1 em spec 041 §4.1 define `empty_legitimate` como `"(INFO, not a finding)"` — ou seja, ausência de entrada em `findings[]`, não uma entrada com severidade INFO. Contradição: como corrigir o STEP 3 sem alterar a decisão de fundo (fases não executadas = vazio legítimo, não bloqueante)? → A: Opção A — STEP 3 não emite nenhum finding. Quando `_is_phase_done()` retorna `False`, a função executa apenas `CONTINUE to next element` sem chamar `finding.append()` ou equivalente. Nenhuma entrada é criada em `findings[]`; nenhum campo `severity`, `finding_type` ou `html_element_id` aparece no JSON para este elemento. Observabilidade (se necessária) fica a cargo de `stderr`/log, nunca do schema. Justificativa: (1) é exatamente o padrão já validado e em produção para C12.1 em spec 041 — reutiliza semântica existente sem criar precedente paralelo; (2) evita qualquer extensão de schema (`INFO` não precisa ser adicionado ao enum de `severity`, nem `"info"` ao objeto `summary{}`); (3) Scenario 6 fica consistente: "nenhum finding é emitido para `tb-scen`" em vez de descrever um finding com severity inexistente no schema. Alterações aplicadas: §4.1 STEP 3 reescrito para CONTINUE-sem-finding; Scenario 5 — Phase Gate (título e acceptance scenarios 1 e 2) reescritos para afirmar ausência de finding em `findings[]`.

### Session 2026-08-19 (rodada 3)

- Q: Feature 042 plan.md AD-8 proposes `phase8_deep_audit_triage()` as a new function in `remediate_summary.py`, while spec 041 defines a full dispatch framework (`run_remediation_loop`, `_dispatch_correction`, `_IMPLEMENTED_DISPATCH_STRATEGIES`) confirmed as NOT committed in the current branch (grep zero matches). Should 042 block on 041 patches (Q1-A: PRÉ-REQUISITO), proceed independently with future consolidation (Q1-B: DEPENDÊNCIA FUTURA), or include 041 patches as a Pre-Step and integrate directly into `_dispatch_correction` (Q1-C: IMPLEMENTAR AS DUAS JUNTAS)? → A: Option B (DEPENDÊNCIA FUTURA) — `phase8_deep_audit_triage()` proceeds as designed in AD-8. `parser_gap` and `render_gap` are non-dispatchable by spec invariant; they fit correctly in a standalone triage phase rather than inside an agent-dispatch loop. Consolidation is formally tracked as `cat3-remediation-loop-041` (plan.md §13). §7 Dependencies updated with a FUTURE DEPENDENCY row; §4.5 updated with a calling-context note.

- Q: Should Task 3.1 in `/speckit.tasks` require an inline annotation inside `phase8_deep_audit_triage()` to prevent future implementors of `cat3-remediation-loop-041` from deleting or duplicating the function, and if so, in what form — `# TEMPORARY` inline comment or a docstring NOTE paragraph? → A: Option B (Docstring NOTE) — Task 3.1 must require a NOTE paragraph in the function's docstring. A `# TEMPORARY` comment is incorrect because the function itself is not removed upon consolidation; only the call site moves from `main()` to `run_remediation_loop`. Required NOTE text documented in §4.5 calling-context note.
