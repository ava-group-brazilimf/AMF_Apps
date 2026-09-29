# Agent Specification: Mermaid Playwright Auto-Fix Quality Gate

**Feature Branch**: `040-mermaid-playwright-autofix`
**Created**: 2026-08-17
**Status**: Draft
**Change Type**: modify-existing

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `ava-summary` / `ava-summary-remediation` |
| **Version** | `ava-summary`: 2.1.0 → **2.2.0** (MINOR — new gate step, no contract change) · `ava-summary-remediation`: 1.x.x → **MINOR bump** |
| **Phase** | `F8 — Summary (cross-cutting)` |
| **Module** | `summary` (`src/modules/ava-fabric-agents/summary/`) |
| **Role** | Both agents gain an embedded **Playwright Mermaid Validation & Auto-Fix Gate**: load the generated Summary HTML in Chromium headless, capture render failures, attempt auto-correction from guardrail rules, and emit a structured report before finalising the file. |
| **Skill** | `ava-summary` · `ava-summary-remediation` (both already user-facing with SKILL.md) |
| **Dispatch** | `ava-summary`: invoked by master-orchestrator after every phase · `ava-summary-remediation`: user-facing standalone repair |

## Clarifications

### Session 2026-08-17

- Q: Qual é o caminho real de `mermaid-guardrails.md` e como deve ser resolvido o `guardrails_path` em `mermaid_playwright_gate.py`? → A: Arquivo confirmado em `src/modules/ava-fabric-agents/shared/mermaid-guardrails.md` (v1.6.0, não é dependência bloqueante). `guardrails_path` tem default computado internamente via `Path(__file__)` e ambos os callers expõem a flag opcional `--mermaid-guardrails-path <path>` para override sem editar código.
- Q: É necessário adicionar flag de opt-out explícito (`--skip-mermaid-gate`)? Se sim, qual `overall_status` e impacto no spec? → A: Sim. Flag `--skip-mermaid-gate` adicionada a ambos os callers. `overall_status: "DISABLED"` (distinto de `"SKIPPED"` que sinaliza ausência do Chromium). Documentado como RF9 com Scenario 6 (4 acceptance criteria) no spec.

---

> **Change Type is `modify-existing`**:
> - Primary implementation targets two Python scripts: `build_summary_comprehensive.py` and `remediate_summary.py` (plus a new shared module `mermaid_playwright_gate.py`).
> - Agent `.md` files receive MINOR instruction additions for the new gate step.
> - `module.yaml` entry already exists — no new agent registration required.
> - SKILL.md files already exist — no routing changes required.
> - Version bumps: MINOR (new optional gate step added to both agents; no input/output contract breaking change).

---

## 2. Agent Frontmatter (delta — additions only)

Both agents' existing frontmatter is unchanged except `version` bump and a new activation phrase referencing the gate. The gate step itself is **internal** — no new SKILL.md is introduced.

For `ava-summary`:
```yaml
---
name: "ava-summary"
version: "2.2.0"   # MINOR bump: +playwright-mermaid-gate
description: |
  Consolida todos os relatórios gerados pelos workflows AS-IS e TO-BE da AVA Fabric
  e produz um relatório HTML interativo padronizado com design Avanade. Executa
  quality gate Playwright (headless Chromium) para validação e correção automática
  de sintaxe Mermaid v11.14.0 antes de finalizar o Summary.
  Ativa com: "gerar summary", "consolidar relatórios", "generate summary report",
  "relatório html", "summary ava".
allowed-tools: Read, Write, Edit, Bash
---
```

For `ava-summary-remediation`:
```yaml
---
name: "ava-summary-remediation"
version: "2.x.0"   # MINOR bump: +playwright-mermaid-gate
description: |
  Agente de reparo pós-pipeline do Summary executivo. Audita um HTML já gerado,
  resolve artefatos incompletos, executa quality gate Playwright para validação e
  correção automática de sintaxe Mermaid v11.14.0, reconstrói e revalida o Summary.
  Nunca sobrescreve artefatos fora de outputs/summary/.
  Ativa com: "corrigir o summary", "remediar o summary", "consertar visualização do summary".
allowed-tools: Read, Write, Edit, Bash
---
```

---

## 3. Output Contract

New artifacts produced by the gate step (appended to each agent's existing Output Contract):

```yaml
outputs:
  # existing artifacts unchanged
  mermaid_validation_report_json: "projects/{project_name}/outputs/summary/mermaid-validation-report.json"
  mermaid_validation_report_md:   "projects/{project_name}/outputs/summary/mermaid-validation-report.md"
```

> **Append decision**: `mermaid-validation-report.json` is a NEW file (not merged into the existing `summary-data.json`) to keep gate results independently parseable by CI tools, `validate_summary.py`, and downstream quality dashboards. The existing `remediation-report.md/.json` written by `remediate_summary.py` will be extended with a new `mermaid_gate` section rather than replaced.

---

## 4. New Shared Module: `mermaid_playwright_gate.py`

A single Python module is introduced under `src/modules/ava-fabric-agents/summary/utils/` and imported by both `build_summary_comprehensive.py` and `remediate_summary.py`. This avoids duplication and ensures a single correction ruleset.

### 4.1 Responsibilities

| Responsibility | Details |
|---|---|
| **Load & render** | Open the target Summary HTML in Playwright (Chromium headless). Wait for `window.mermaid` to be defined AND for all `.mermaid` elements to finish processing (success: `<svg>` child present; failure: raw code text remains). |
| **Capture console errors** | Subscribe to `page.on("console")` and `page.on("pageerror")` before navigation. Filter messages matching known Mermaid v11.14.0 failure patterns. |
| **Correlate failures** | Map each failed `.mermaid` DOM element to its source — `diagram_id` (HTML `id` attribute or sequential index), `section_name` (nearest `<h2>`/`<h3>` heading), and optionally the originating `.mmd` file path (resolved via the `data-src` attribute if present, otherwise inline). |
| **Report generation** | Emit `mermaid-validation-report.json` per schema defined in Section 5. |
| **Auto-correction** | Apply guardrail-driven fixes (Section 6) to the raw Mermaid source. Write corrected source back into the HTML and trigger a re-render cycle via Playwright. |
| **Retry loop** | Repeat probe → fix → re-render up to `max_attempts` (default: 3, CLI-configurable). On exhaustion, inject the `%% [INCOMPLETE - needs review]` placeholder and mark the diagram `FAIL_UNRESOLVED`. |
| **Diff & audit trail** | For every applied correction, record `before` / `after` snippets and a `timestamp` (ISO 8601) in the report. |

### 4.2 Module API (conceptual, implementation-language-agnostic)

```
run_playwright_mermaid_gate(
    html_path: Path,
    guardrails_path: Path,  # default computed from Path(__file__) → src/modules/ava-fabric-agents/shared/mermaid-guardrails.md
    max_attempts: int = 3,
    timeout_ms: int = 15_000
) -> MermaidGateResult
```

> **`guardrails_path` resolution (Clarification 2026-08-17)**: The module resolves the default path internally via `Path(__file__).resolve()` anchored to `src/modules/ava-fabric-agents/shared/mermaid-guardrails.md`. The parameter exists for testability and CI override — callers do not need to supply it unless overriding. Both `build_summary_comprehensive.py` and `remediate_summary.py` expose an optional CLI flag `--mermaid-guardrails-path <path>` that, when provided, overrides the computed default PATH VALUE — though, per Section 12, this currently has NO EFFECT on correction behavior, since the ruleset is hardcoded in Python (`_apply_gr001`–`_apply_gr012`) rather than parsed from this file at runtime.

`MermaidGateResult` carries:
- `overall_status`: `"PASS"` | `"PASS_WITH_FIXES"` | `"FAIL"` | `"SKIPPED"` (Chromium unavailable — Scenario 4) | `"DISABLED"` (explicit user opt-out via `--skip-mermaid-gate` — Scenario 6/RF9)
- `diagrams`: list of `DiagramResult` (see Section 5)
- `total_fixed`: int
- `total_unresolved`: int
- `report_path`: Path to written JSON report

---

## 5. Report Schema (`mermaid-validation-report.json`)

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-08-17T19:00:00Z",
  "html_source": "projects/{project_name}/outputs/summary/AVA-FABRIC-SUMMARY-*.html",
  "mermaid_version_under_test": "11.14.0",
  "overall_status": "PASS | PASS_WITH_FIXES | FAIL | SKIPPED | DISABLED",
  "total_diagrams": 12,
  "total_valid": 10,
  "total_fixed": 1,
  "total_unresolved": 1,
  "diagrams": [
    {
      "diagram_id": "c4-context-01",
      "section": "AS-IS Architecture",
      "diagram_type": "C4Context",
      "source_file": "outputs/asis/diagrams/c4-context.mmd",
      "status": "PASS | FIXED | FAIL_UNRESOLVED",
      "error_type": "SyntaxError | ParseError | RenderFailure | null",
      "error_message": "Syntax error in text · mermaid version 11.14.0",
      "error_line": 7,
      "code_snippet": "graph LR\n  A-->B",
      "guardrail_rule_violated": "GR-001: Use `flowchart` not `graph`",
      "fix_applied": "Replaced `graph LR` with `flowchart LR`",
      "fix_attempts": 1,
      "diff": {
        "before": "graph LR\n  A-->B",
        "after": "flowchart LR\n  A-->B",
        "timestamp": "2026-08-17T19:00:01Z"
      }
    }
  ]
}
```

---

## 6. Auto-Correction Ruleset (mapped from `mermaid-guardrails.md`)

The correction routine applies rules in priority order. Each rule is tagged with a guardrail ID for traceability in the report.

| Rule ID | Trigger | Correction Applied |
|---|---|---|
| GR-001 | Keyword `graph` (not followed by `TD`/`LR`/`BT`/`RL`) | Replace with `flowchart` |
| GR-002 | Keyword `graph TD` / `graph LR` etc. | Replace with `flowchart TD` / `flowchart LR` etc. |
| GR-003 | Label spanning multiple lines without `<br/>` in quotes | Join lines; insert `<br/>` between parts; wrap in `"..."` |
| GR-004 | `subgraph` block missing closing `end` | Append `end` before the next `subgraph` or end of diagram |
| GR-005 | Node ID containing prohibited chars (`~`, `→`, `—`, NBSP, ZWS, backtick, `;`, emoji) | Strip or replace with `_` |
| GR-006 | Node ID containing curly quotes (`"`, `"`, `'`, `'`) | Replace with straight `"` or `'` |
| GR-007 | Node referenced in an edge before it is declared | Insert a declaration line before the first edge referencing that node |
| GR-008 | More than 2 levels of nested `subgraph` | Flatten third-level subgraph into second level |
| GR-009 | C4 diagram using `graph`/`flowchart` keywords instead of C4 macros | Reclassify as `flowchart`; flag for manual review with `%% [NEEDS REVIEW - was C4 style]` |
| GR-010 | `sequenceDiagram` participant names containing prohibited chars | Sanitise to alphanumeric+underscore, update all references |
| GR-011 | Arrow type `-->` used in `stateDiagram-v2` context | Replace with `-->` (already valid) or `[*] -->` if transition from initial state |
| GR-012 | Diagram source is empty or whitespace only | Replace with placeholder `flowchart LR\n  A[No diagram data]\n%% [INCOMPLETE - needs review]` |

Corrections that cannot be applied deterministically (i.e., require semantic understanding of the diagram's content) are skipped, and the diagram is marked `FAIL_UNRESOLVED` after `max_attempts` exhausted.

---

## 7. Integration Points

### 7.1 `build_summary_comprehensive.py` (ava-summary gate)

The Playwright gate is inserted as **Phase G** — the final step before writing the output HTML file:

```
Phase 1: Data collection
Phase 2: Template population
Phase 3: Diagram injection (existing sanitize_mmd calls)
Phase 4: Security reconciliation
Phase 5: Content/UI guard verification
Phase 6: HTML assembly
Phase G: [NEW] Playwright Mermaid Validation & Auto-Fix Gate
         → If gate fails unresolved diagrams, write HTML with placeholders + emit WARNING
         → Always write mermaid-validation-report.json
         → Skipped with overall_status "DISABLED" if --skip-mermaid-gate is passed
Phase 7: validate_summary.py pass
```

**New CLI flags added to `build_summary_comprehensive.py` (Clarification 2026-08-17)**:
- `--mermaid-guardrails-path <path>` (optional): override path to `mermaid-guardrails.md`; defaults to `src/modules/ava-fabric-agents/shared/mermaid-guardrails.md` computed from module location.
- `--skip-mermaid-gate` (optional, boolean flag): explicitly disable the Playwright gate regardless of Chromium availability. Produces `mermaid-validation-report.json` with `overall_status: "DISABLED"` (RF9).

### 7.2 `remediate_summary.py` (ava-summary-remediation gate)

The Playwright gate is inserted as **Phase 3.5** — between the existing Mermaid sanitisation pass (Phase 3) and the rebuild step (Phase 6):

```
Phase 0: Audit
Phase 1: Artifact resolution
Phase 2: Diagram synthesis
Phase 3: Mermaid sanitization (existing sanitize_mmd)
Phase 3.5: [NEW] Playwright Mermaid Validation & Auto-Fix Gate
           → Runs on the in-memory HTML before rebuild
           → Merge gate results into remediation-report.json (new `mermaid_gate` section)
           → Skipped with overall_status "DISABLED" if --skip-mermaid-gate is passed
Phase 4: Security reconciliation
Phase 5: Content/UI guard verification
Phase 6: Rebuild (build_summary_comprehensive.py call)
Phase 7: Re-validate (validate_summary.py)
```

**New CLI flags added to `remediate_summary.py` (Clarification 2026-08-17)**:
- `--mermaid-guardrails-path <path>` (optional): same semantics as in `build_summary_comprehensive.py`.
- `--skip-mermaid-gate` (optional, boolean flag): same semantics as in `build_summary_comprehensive.py`.

---

## 8. User Scenarios (Given-When-Then)

> **Language convention**: Story descriptions (`**Story**:`) may be written in
> Brazilian Portuguese. Acceptance scenarios (Given/When/Then) MUST be in English
> for BDD traceability with F5 QA agents.

### Scenario 1 — Nominal Path: Summary with no Mermaid errors (Priority: P1)

**Story**: Como o master-orchestrator, quero que o gate Playwright valide o Summary HTML sem introduzir overhead perceptível quando todos os diagramas já estão corretos.

**Why this priority**: The gate must be a zero-friction no-op for valid Summaries — any performance regression on the happy path is unacceptable.

**Acceptance Scenarios**:

1. **Given** a Summary HTML where all `.mermaid` elements render as `<svg>` within 15 seconds, **When** the Playwright gate runs, **Then** `overall_status` is `"PASS"`, `total_unresolved` is `0`, and the gate exits in under 30 seconds total.
2. **Given** the above, **When** the gate completes, **Then** `mermaid-validation-report.json` is written listing all diagrams with `"status": "PASS"` and no `fix_applied` entries.
3. **Given** a Summary with zero `.mermaid` elements, **When** the gate runs, **Then** it exits immediately with `overall_status: "PASS"` and `total_diagrams: 0`.

---

### Scenario 2 — Auto-Fix Path: Summary with fixable Mermaid errors (Priority: P1)

**Story**: Como o agente de build do Summary, quero que erros sintáticos conhecidos (como `graph TD` em vez de `flowchart TD`) sejam corrigidos automaticamente antes da publicação, eliminando o Bug 2679 — Rastreabilidade.

**Why this priority**: Core value of the feature — prevents silent diagram failures from reaching end users.

**Acceptance Scenarios**:

1. **Given** a Summary HTML containing a `.mermaid` element with `graph LR` syntax (GR-001/GR-002 violation), **When** the Playwright gate runs, **Then** the element is corrected to `flowchart LR`, re-renders as `<svg>`, and `status` is `"FIXED"` in the report.
2. **Given** the above, **Then** `diff.before` contains `graph LR` and `diff.after` contains `flowchart LR` and `diff.timestamp` is a valid ISO 8601 string.
3. **Given** a Summary HTML with 3 fixable diagrams, **When** the gate runs with `max_attempts=3`, **Then** all 3 are fixed in a single pass and `overall_status` is `"PASS_WITH_FIXES"`.
4. **Given** a fix is applied, **When** the gate re-validates via Playwright, **Then** the corrected element renders as `<svg>` before the next pass begins.

---

### Scenario 3 — Exhaustion Path: Unresolvable diagram (Priority: P1)

**Story**: Como o responsável pela revisão do Summary, quero que diagramas irreparáveis sejam explicitamente sinalizados com `[INCOMPLETE - needs review]` em vez de publicados silenciosamente quebrados.

**Why this priority**: Safety gate — a broken diagram published silently is worse than an explicitly flagged placeholder.

**Acceptance Scenarios**:

1. **Given** a `.mermaid` element whose syntax cannot be fixed by any guardrail rule, **When** the gate runs `max_attempts` correction cycles, **Then** the diagram source is replaced with the `%% [INCOMPLETE - needs review]` placeholder and `status` is `"FAIL_UNRESOLVED"`.
2. **Given** the above, **Then** `overall_status` is `"FAIL"` and the agent emits a visible WARNING in its execution log.
3. **Given** a Summary with 2 fixable and 1 unresolvable diagram, **Then** the 2 fixable diagrams are corrected and `total_fixed=2`, `total_unresolved=1`, `overall_status="FAIL"`.

---

### Scenario 4 — Edge Case: Playwright/Chromium unavailable (Priority: P2)

**Story**: Como operador do pipeline, quero que a ausência do Playwright não quebre o build do Summary — apenas emita um aviso e continue.

**Why this priority**: Gate must degrade gracefully — blocking the entire Summary build due to a missing tool would be worse than skipping the gate.

**Acceptance Scenarios**:

1. **Given** Playwright/Chromium is not installed, **When** the gate is invoked, **Then** it emits a `WARNING: playwright-gate skipped (chromium unavailable)` log entry, writes a partial report with `overall_status: "SKIPPED"`, and `build_summary_comprehensive.py` continues to completion.
2. **Given** the above, **Then** no exception propagates to the caller and exit code reflects only the outer build result.

---

### Scenario 5 — `ava-summary-remediation` preserves non-Summary artifacts (Priority: P1)

**Story**: Como o agente de remediação, quero que a nova etapa Playwright não sobrescreva nenhum artefato fora de `outputs/summary/`, mantendo a regra já vigente de isolamento.

**Why this priority**: Constitution-level constraint (RF8) — must never be violated.

**Acceptance Scenarios**:

1. **Given** a remediation run that applies Mermaid corrections, **When** the gate writes corrected diagrams back into the HTML, **Then** no file outside `projects/{project_name}/outputs/summary/` is written or modified.
2. **Given** the above, **Then** source `.mmd` files in `outputs/asis/diagrams/` or `outputs/tobe/docs/` are read-only (no writes).

---

### Scenario 6 — Explicit Opt-Out: `--skip-mermaid-gate` flag (Priority: P2) [RF9]

**Story**: Como desenvolvedor rodando builds locais rápidos ou operador de CI que já valida Mermaid em outra etapa, quero poder desabilitar explicitamente o gate Playwright sem precisar desinstalar o Chromium.

**Why this priority**: Operator ergonomics — distinguishes deliberate disabling from tool absence; keeps audit trails clean.

**Acceptance Scenarios**:

1. **Given** `build_summary_comprehensive.py` is invoked with `--skip-mermaid-gate`, **When** the build runs, **Then** the Playwright gate is not invoked (no browser launched), `mermaid-validation-report.json` is written with `overall_status: "DISABLED"`, and the build completes successfully.
2. **Given** the above, **Then** no `WARNING: playwright-gate skipped` message is emitted — the log must distinguish opt-out from unavailability.
3. **Given** `remediate_summary.py` is invoked with `--skip-mermaid-gate`, **Then** the gate is skipped with `overall_status: "DISABLED"` in the merged `remediation-report.json` `mermaid_gate` section.
4. **Given** `--skip-mermaid-gate` is active and Chromium IS installed, **Then** `overall_status` is `"DISABLED"` (not `"SKIPPED"`) — confirming the distinction is source-driven, not tool-driven.

---

## 9. Quality Gate Requirements

- [x] Agent ID follows `ava-{phase}-{role}` pattern (`^ava-[a-z0-9-]+$`) (Article II) — existing agents, no new ID
- [x] Frontmatter MINOR bump only — no structural change (Article II)
- [x] Module-level `module.yaml` does NOT need a new entry — only version bump (Article IV)
- [x] All output paths use lowercase `{project_name}` and correct phase folder `outputs/summary/` (Article II)
- [x] BDD scenarios cover nominal (S1), fix (S2), gate-exhaustion (S3), edge (S4), isolation (S5), opt-out (S6/RF9) paths (Article VI)
- [x] Security sub-pipeline: no impact — gate is read-only on existing HTML (Article VII)
- [x] No technology versions hardcoded in agent body — Mermaid version resolved from embedded `mermaid.min.js` (Article I)
- [x] Skill/Agent split: both agents already have SKILL.md; new module is internal-only (Article XI)
- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] RF9 (`--skip-mermaid-gate`) defined with `"DISABLED"` `overall_status`; coverage: Scenario 6 (4 acceptance criteria)

---

## 10. Dependencies

| Dependency | Artifact / Agent | Reason |
|---|---|---|
| Summary HTML | `projects/{project_name}/outputs/summary/AVA-FABRIC-SUMMARY-*.html` | Input to the Playwright gate |
| `mermaid.min.js` (v11.14.0 pinned) | `src/modules/ava-fabric-agents/summary/templates/html/mermaid.min.js` | The exact runtime under test — gate validates against THIS bundle |
| Playwright (Chromium) | `playwright` Python package + `chromium` browser binary | Headless rendering engine |
| `mermaid-guardrails.md` | `src/modules/ava-fabric-agents/shared/mermaid-guardrails.md` | Correction ruleset REFERENCE DOCUMENTATION (human-readable only — not parsed at runtime; see Section 12) (confirmed present, v1.6.0) |
| `sanitize_mmd` | `build_summary_comprehensive.py` (existing) | Called before the Playwright gate as a pre-pass |
| `validate_summary.py` | `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` | Runs AFTER the gate (unchanged) |
| `render_blueprint_compatibility.py` | existing utility | Existing Playwright probe infrastructure — the new gate EXTENDS this, not replaces it |

---

## 11. Exclusions

- Rewriting diagrams from scratch or correcting semantic/content errors — only syntactic corrections are in scope.
- Support for Mermaid versions other than v11.14.0 (pinned) — as per RNF4.
- Modifying any artefacts outside `outputs/summary/` — as per RF8 and Scenario 5.
- Visual regression testing of diagram layout — only render failure (no `<svg>`) is detected.
- Integration with external Mermaid CLI (`mmdc`) — the gate uses the bundled `mermaid.min.js` exclusively.
- Adding new agent IDs or SKILL.md files — this is a modification to two existing agents.

---

## 12. Assumptions

- Playwright Python package (`playwright`) and Chromium browser binary are installable in the pipeline environment via `pip install playwright && playwright install chromium`.
- `package.json` under `summary/utils/` already defines a Node.js Playwright script (`probe_browser.js`) — the new gate may reuse or extend this infrastructure rather than introducing a second approach.
- `render_blueprint_compatibility.py` already contains `execute_probe()` which performs a browser-based Mermaid render check. The new `mermaid_playwright_gate.py` builds on top of this — it does NOT reimplement the browser invocation from scratch.
- The `summary-template.html` already embeds `mermaid.min.js` locally via `<script src="mermaid.min.js">` — Playwright will load this file from the local filesystem (no network required).
- `data-src` attributes may or may not be present on `.mermaid` elements. When absent, the diagram source is treated as inline.
- `mermaid-guardrails.md` (`src/modules/ava-fabric-agents/shared/mermaid-guardrails.md`,
  v1.6.0) é a documentação canônica e legível por humanos do ruleset de correção
  (GR-001–GR-012). O motor de auto-correção em `mermaid_playwright_gate.py` implementa essas
  regras como funções Python hardcoded (`_apply_gr001` … `_apply_gr012`), e NÃO faz parsing de
  `mermaid-guardrails.md` em tempo de execução. O parâmetro `guardrails_path` (e a flag CLI
  `--mermaid-guardrails-path`) são mantidos na assinatura da função e no CLI por
  compatibilidade futura e testabilidade, mas atualmente NÃO têm nenhum efeito sobre o
  comportamento do gate. Qualquer alteração no ruleset de correção exige atualizar TANTO
  `mermaid-guardrails.md` (documentação) QUANTO a função `_apply_grXXX` correspondente
  (implementação) — os dois artefatos devem ser mantidos sincronizados manualmente; não há
  detecção automática de divergência entre eles.
- The gate degrades gracefully when Playwright/Chromium is unavailable (Scenario 4), ensuring backward compatibility with environments that have not yet installed the tool.
- `max_attempts` defaults to 3 and is overridable via a CLI flag `--mermaid-gate-max-attempts N` on both `build_summary_comprehensive.py` and `remediate_summary.py`.
- **[Clarification 2026-08-17]** Both callers expose `--skip-mermaid-gate` (boolean, disables gate entirely; `overall_status: "DISABLED"` — distinct from `"SKIPPED"` which signals Chromium unavailability) and `--mermaid-guardrails-path <path>` (optional override for the guardrails file; default resolved internally from `Path(__file__)`). These flags are documented as RF9 and Scenario 6.

---

## 13. Success Criteria

| Criterion | Measure |
|---|---|
| **Zero silent failures** | A Summary HTML that previously displayed raw Mermaid code instead of diagrams now always contains either a rendered `<svg>` or an explicit `%% [INCOMPLETE - needs review]` placeholder — never silent broken code |
| **Auto-fix rate** | At least the guardrail rules GR-001/GR-002 (`graph` → `flowchart`) are corrected automatically in 100% of cases where they are the sole cause of render failure |
| **Report completeness** | `mermaid-validation-report.json` is produced on every gate run and lists every `.mermaid` element with its status (`PASS`/`FIXED`/`FAIL_UNRESOLVED`) |
| **Audit traceability** | Every correction applied includes `before`, `after`, and `timestamp` in the report — enabling full diff-based audit |
| **No regression on valid Summaries** | Gate adds no more than 30 seconds to the total pipeline duration when all diagrams are already valid |
| **Graceful degradation** | When Playwright/Chromium is unavailable, the Summary build completes successfully with a warning — no exception propagates and no artefact is left incomplete |
| **Isolation preserved** | Zero writes outside `projects/{project_name}/outputs/summary/` during any gate run, validated by file-system inspection |
| **Max-attempt enforcement** | Gate never exceeds `max_attempts` correction cycles per diagram regardless of error type |
