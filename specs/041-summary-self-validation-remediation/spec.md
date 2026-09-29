# Agent Specification: Summary Self-Validation & Remediation

**Feature Branch**: `041-summary-self-validation-remediation`
**Created**: 2026-08-18
**Status**: Draft
**Change Type**: modify-existing (extends `ava-summary-validate` + `ava-summary-remediation`)

> **Language note**: This spec is a planning document written in **English**.
> The agent body implementation (Category 2 in tasks) MUST be written in
> **Brazilian Portuguese** per Constitution Article V.
> The agent frontmatter (`name`, `version`, `description`, `allowed-tools`) uses
> mixed language: English keys, Portuguese content.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID (primary)** | `ava-summary-validate` (existing — MINOR version bump) |
| **Agent ID (secondary)** | `ava-summary-remediation` (existing — MINOR version bump) |
| **Version** | `ava-summary-validate` → `1.5.0` · `ava-summary-remediation` → `1.6.0` |
| **Phase** | `F8 — Summary (cross-cutting)` |
| **Module** | `summary` (`src/modules/ava-fabric-agents/summary/`) |
| **Role** | After HTML is produced by `build_summary_comprehensive.py`, automatically run a deep item-by-item audit of every section/card/table/Mermaid diagram (F1–F8), distinguish legitimate-empty from generation-failure, verify artefact presence against the manifest, apply auto-corrections, and regenerate the HTML until zero CRITICAL/HIGH findings or the retry cap is reached. |
| **Skill** | `ava-summary-validate` _(internal quality gate — no new SKILL.md)_ · `ava-summary-remediation` _(existing SKILL.md, unchanged routing)_ |
| **Dispatch** | `ava-summary-validate` → internal-only, auto-triggered by `ava-summary` and `ava-summary-remediation` · `ava-summary-remediation` → user-facing via existing SKILL.md |

> **Change Type rationale (`modify-existing`)**: Both agents already exist in
> `src/modules/ava-fabric-agents/summary/agents/`. This feature extends their
> behaviour rather than creating new files. The `module.yaml` entry already
> exists — Category 4 (registrar **novos** agentes no `module.yaml`) tasks are **N/A**.
> Updating the module-level `version` field (`1.4.1 → 1.5.0`) is **not** Category 4;
> it is a metadata/config change that goes to **Category 3**, because the module
> manifest version must reflect the behaviour shipped by the agents it declares.
> `ava-summary-validate` has no SKILL.md (internal) — Category 1.5 is **N/A**.
> `ava-summary-remediation` SKILL.md routing is unchanged — Category 1.5 is **N/A**.
> Version bumps: both are MINOR (new behaviour, output contract extended, no breaking change).

---

## 2. Agent Frontmatter

### 2.1 `ava-summary-validate` (updated)

```yaml
---
name: "ava-summary-validate"
version: "1.5.0"
description: |
  Non-regression quality gate do Summary HTML. Após o HTML ser gerado por
  build_summary_comprehensive.py, executa auditoria item a item de cada
  seção/card/tabela/chip de artefato (fases F1–F8): detecta itens vazios
  por falha (vs. vazio legítimo), artefatos ausentes do manifesto, configurações
  divergentes do build validator e diagramas Mermaid inválidos (via
  mermaid_playwright_gate.py). Emite validation-report.{md,json} com severidade
  CRITICAL/HIGH/MEDIUM/LOW e causa raiz (agente/fase/arquivo).
  Ativa com: "validate summary", "audit summary", "check summary integrity",
  "summary validator", "summary-validate", "validar summary".
allowed-tools: Read, Bash, Glob, Grep, Write
---
```

### 2.2 `ava-summary-remediation` (updated)

```yaml
---
name: "ava-summary-remediation"
version: "1.6.0"
description: |
  Agente de reparo pós-pipeline do Summary executivo. Audita HTML gerado
  (ou artefatos incompletos em outputs/), aplica correções automáticas
  (regenerar artefato faltante chamando agente responsável, corrigir path/nome
  de manifesto, re-sanitizar Mermaid), reconstrói via build_summary_comprehensive.py
  e repete a validação via ava-summary-validate até zero findings CRITICAL/HIGH
  ou atingir MAX_REMEDIATION_ATTEMPTS (configurável). Emite remediation-report.json
  consolidado com exit code 0/1 compatível com CI.
  Ativa com: "corrigir o summary", "remediar o summary", "@ava-summary-remediation",
  "consertar visualização do summary".
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---
```

---

## 3. Output Contract

### 3.1 `ava-summary-validate` outputs (extended)

```yaml
outputs:
  validation_report_md:    "projects/{project_name}/outputs/summary/validation-report.md"
  validation_report_json:  "projects/{project_name}/outputs/summary/validation-report.json"
  # new in v1.5.0 — detailed per-item findings consumed by ava-summary-remediation
  deep_audit_json:         "projects/{project_name}/outputs/summary/deep-audit-report.json"
```

> **`deep-audit-report.json` schema** (new artifact):
> ```json
> {
>   "schema_version": "1.0",
>   "generated_at": "<ISO-8601>",
>   "project": "<project_name>",
>   "html_path": "<absolute path to audited HTML>",
>   "summary": {
>     "critical": 0, "high": 0, "medium": 0, "low": 0,
>     "promotable": true
>   },
>   "findings": [
>     {
>       "id": "DA-001",
>       "severity": "CRITICAL|HIGH|MEDIUM|LOW",
>       "phase": "F1|F2|...|F8",
>       "section": "<human-readable section name>",
>       "agent_responsible": "<ava-agent-id>",
>       "artifact_path": "<relative path or null>",
>       "finding_type": "empty_by_failure|missing_artifact|divergent_config|mermaid_error|placeholder_unresolved|table_no_rows|list_no_items",
>       "detail": "<what was observed>",
>       "root_cause": "<why this happened>",
>       "auto_correctable": true,
>       "suggested_fix": "<action to take>"
>     }
>   ]
> }
> ```

### 3.2 `ava-summary-remediation` outputs (extended)

```yaml
outputs:
  remediation_report_json:      "projects/{project_name}/outputs/summary/remediation-report.json"
  mermaid_validation_report_md: "projects/{project_name}/outputs/summary/mermaid-validation-report.md"
  mermaid_validation_report_json: "projects/{project_name}/outputs/summary/mermaid-validation-report.json"
  # HTML rebuilt by build_summary_comprehensive.py (path unchanged):
  summary_html:                 "projects/{project_name}/outputs/summary/AVA-FABRIC-SUMMARY-{PROJECT_NAME}-{DATE}.html"
```

> **`remediation-report.json` schema** (extended in v1.6.0):
> ```json
> {
>   "schema_version": "2.0",
>   "project": "<project_name>",
>   "attempts": 1,
>   "max_attempts": 3,
>   "final_status": "CLEAN|PARTIAL|BLOCKED",
>   "exit_code": 0,
>   "forced": false,
>   "deep_audit_summary": { "critical": 0, "high": 0, "medium": 0, "low": 0 },
>   "corrections_applied": [],
>   "unresolved_findings": [],
>   "mermaid_gate": { "diagrams_checked": 0, "diagrams_fixed": 0, "diagrams_failed": 0 }
> }
> ```
> `"forced": true` is set only when `remediate_summary.py --force-promote` is invoked
> on a BLOCKED result. Default value is `false` (field always present in schema v2.0).

---

## 4. Detailed Feature Behaviour

### 4.1 Deep Audit — What Constitutes a "Finding"

The deep audit (`ava-summary-validate` v1.5.0) extends the existing 101-rule catalog
(C1–C11) with a new category **C12 — Deep Item Audit** covering:

| Sub-rule ID | Finding Type | Description |
|---|---|---|
| C12.1 | `empty_by_failure` | Card/KPI tile renders value `0`, `"N/E"`, `""`, or `"—"` when the source artifact has data. Distinguish from `empty_legitimate` (phase not yet executed — detected by `D.agentStatus[phase].done == false`). |
| C12.2 | `placeholder_unresolved` | Any `{{X}}`, `[NEEDS CLARIFICATION]`, or `AG-NN` token visible in rendered HTML outside `<script>` blocks. **Scope**: template/config-origin placeholders only. Does **not** include `[INCOMPLETE]` or `[ARTIFACT-MISSING]` — those are exclusively covered by C11.39 and C11.40 respectively, avoiding double-reporting. |
| C12.3 | `missing_artifact` | File referenced in `artifact-map.yaml` (or any agent's Output Contract section) is absent from `projects/{project_name}/outputs/` or has zero bytes. |
| C12.4 | `divergent_config` | Artifact name, relative path, or schema version declared in an agent's Output Contract differs from what `build_summary_comprehensive.py` expects at parse time (detected by cross-referencing `artifact-map.yaml` vs. actual filesystem paths). |
| C12.5 | `mermaid_error` | Diagram included in the Summary fails Playwright syntax/render check (delegated to `mermaid_playwright_gate.py` — no reimplementation). |
| C12.6 | `table_no_rows` | `<table>` element whose `<tbody>` is present but contains zero `<tr>` elements, when `D.agentStatus[phase].done == true`. **Structural distinction from C11.41**: C11.41 targets tables with no `<tbody>` element at all (structurally incomplete template output); C12.6 targets tables that have a `<tbody>` but no data rows (content failure in a completed phase). They test different HTML patterns and require no deduplication. |
| C12.7 | `list_no_items` | `<ul>` / `<ol>` with zero `<li>` when content is expected based on phase completion status. |

> **C12 scope invariant — deduplication rule** (decided 2026-08-18):
> C12 rules MUST NOT overlap with C11.39–C11.41 when `--deep` is active. Specifically:
> - **C12.2** covers only `{{X}}`, `[NEEDS CLARIFICATION]`, `AG-NN` — never `[INCOMPLETE]` (→ C11.39) or `[ARTIFACT-MISSING]` (→ C11.40).
> - **C12.6** covers tables with a `<tbody>` present but empty — never tables missing `<tbody>` entirely (→ C11.41).
> This guarantees that `validation-report.json` in `--deep` mode contains no functional duplicates between the C11.x and C12.x rule sets, and that the remediation loop's `deep-audit-report.json` (which contains only C12.x findings) is the single source of truth for automated correction without double-counting.

#### Legitimate-Empty vs. Failure-Empty Distinction (C12.1)

The deep auditor applies the following decision logic before raising C12.1:

```
IF D.agentStatus[phase].done == false
  → classify as empty_legitimate (INFO, not a finding)
ELSE IF source_artifact exists AND source_artifact.size > 100 bytes
  → classify as empty_by_failure (CRITICAL or HIGH)
ELSE IF source_artifact does not exist
  → raise C12.3 (missing_artifact) — do NOT raise C12.1 simultaneously
ELSE
  → classify as empty_legitimate (INFO)
```

### 4.2 Severity Mapping

| Severity | Condition |
|---|---|
| **CRITICAL** | Missing artifact that blocks a client-facing phase; unresolved `{{X}}` placeholder in the HTML title, project name, or KPI section; Mermaid diagram that was explicitly requested in the migration report fails to render. |
| **HIGH** | KPI tile value is `0` or `N/E` when the backing artifact has non-empty data; table with zero rows in a completed phase; missing artifact for a non-blocking but contractually required output. |
| **MEDIUM** | Divergent file name or path between `artifact-map.yaml` and actual filesystem; Mermaid diagram in a secondary section fails to render; list with zero items in a completed phase. |
| **LOW** | Schema version mismatch (artifact valid but older schema); INFO-level placeholder visible only in secondary tooltips. |

### 4.3 Mermaid Integration (no reimplementation)

The deep audit calls `mermaid_playwright_gate.py` (already implemented in spec 040)
as a **sub-step**, passing the HTML path. Results are consumed from the returned
`MermaidGateResult` object. Every diagram reported as `status: failed` by the gate
is registered as a C12.5 finding with severity mapping from the gate's own severity
field. The deep auditor does **not** re-implement Playwright logic.

### 4.4 Auto-Correction Strategy (Remediation Loop)

`ava-summary-remediation` v1.6.0 adds a structured correction loop after the deep audit:

```
LOOP (attempt = 1 .. MAX_REMEDIATION_ATTEMPTS):
  1. Run deep audit → consume deep-audit-report.json
  2. IF no CRITICAL or HIGH findings:
       IF no MEDIUM or LOW findings → BREAK (status = CLEAN)
       ELSE → BREAK (status = PARTIAL)   ← applies at ANY iteration, not only at max
  3. For each auto_correctable finding:
     a. missing_artifact   → invoke responsible agent (from finding.agent_responsible)
                             using its trigger code from module.yaml
                             DISPATCH FAILURE HANDLING (two paths):
                             - Transient failure (timeout / non-zero exit code):
                               log dispatch_error in remediation-report.json,
                               consume attempt, continue loop normally.
                             - Structural failure (agent_id not resolvable in module.yaml,
                               or agent permanently unavailable):
                               set finding.auto_correctable = false,
                               record dispatch_error with reason in unresolved_findings,
                               do NOT consume this attempt for that finding,
                               continue loop with remaining findings.
     b. divergent_config   → patch artifact-map.yaml entry or output path
     c. mermaid_error      → delegate fix to mermaid_playwright_gate.py auto-fix
                             (GR-001..GR-012 guardrails already implemented in spec 040)
     d. placeholder_unresolved → re-run build_summary_comprehensive.py
                             (builder resolves placeholders from project-config.yaml)
     e. empty_by_failure   → re-run build_summary_comprehensive.py after correcting
                             the source artifact parse path
  4. Re-run build_summary_comprehensive.py
  5. Re-run validate_summary.py → append iteration results to remediation-report.json
ENDLOOP

IF remaining CRITICAL/HIGH > 0 after MAX_REMEDIATION_ATTEMPTS:
  → status = BLOCKED, exit code 1
  → List unresolved findings with manual remediation guidance
  → For findings with dispatch_error (structural): include reason and agent_id
    in suggested_fix so the operator knows to fix module.yaml registration
```

> **Invariant**: `ava-summary-remediation` never synthesises HTML content directly.
> All HTML reconstruction goes through `build_summary_comprehensive.py`.
> All Mermaid fixes go through `mermaid_playwright_gate.py`.
>
> **Dispatch failure invariant**: A structural dispatch failure (agent not resolvable)
> MUST NOT silently consume retry attempts. It is recorded immediately as a
> non-auto-correctable finding so that `MAX_REMEDIATION_ATTEMPTS` budget is spent
> only on findings that have a chance of being resolved automatically.
>
> **Force-promote override**: When `remediate_summary.py` is invoked with `--force-promote`,
> the HTML IS delivered even when `final_status` is `BLOCKED`. The flag:
> - Sets `remediation-report.json."forced": true`
> - Keeps exit code `1` (CI can detect and react, but does not physically block the file)
> - Emits a `[WARN] FORCED PROMOTION — unresolved CRITICAL/HIGH findings remain` header
>   in the report, listing each unresolved finding
> - Is intended for human-authorised overrides only (e.g., demo cutover, known acceptable debt)
> - MUST be implemented as a new task (Category 3) in `/speckit.tasks`

### 4.5 Auto-Trigger Integration

The self-validation loop fires automatically in two paths:

| Trigger path | Where hooked | What happens |
|---|---|---|
| `/ava-summary` executed | End of `summary-agent.md` execution sequence | After `build_summary_comprehensive.py` succeeds, agent invokes `validate_summary.py --deep --project {project_name}`. If findings exist, agent invokes `remediate_summary.py` (remediation script). |
| `/ava-summary-remediation` executed | Already in remediation flow | Remediation loop is the primary flow; no additional hook needed. |

The parameter `--deep` added to `validate_summary.py` activates C12 rules in addition
to C1–C11. Without `--deep`, existing behaviour is unchanged (backward-compatible).

### 4.6 Consolidated Report Format (CI-Compatible)

The final report emitted by `remediation-report.json` follows the same exit-code
convention as `validate_summary.py`:

- **Exit 0** → `final_status: CLEAN` — all CRITICAL/HIGH resolved or no findings.
- **Exit 1** → `final_status: BLOCKED` — at least one unresolved CRITICAL/HIGH finding.
  - HTML is NOT automatically delivered in this state.
  - To override: invoke `remediate_summary.py --force-promote`; sets `"forced": true`
    in the report and emits a mandatory warning header. Exit code remains `1`.
- **Exit 0 + warnings** → `final_status: PARTIAL` — only MEDIUM/LOW remain after the
  loop breaks. **PARTIAL applies at ANY loop iteration** where no CRITICAL/HIGH findings
  remain: the loop does NOT continue iterating solely to attempt MEDIUM/LOW corrections.
  MEDIUM/LOW findings are reported as residual noise; they do not block promotion.

The CI pipeline reads exit code; the human reads `remediation-report.json`.

> **`--force-promote` field in `remediation-report.json`**:
> ```json
> { "forced": false }   // default — absent or false when not invoked with --force-promote
> { "forced": true  }   // set when --force-promote overrides a BLOCKED state
> ```

### 4.7 MAX_REMEDIATION_ATTEMPTS Configuration

The retry cap is resolved at runtime (Configuration-Driven, Article I):

1. `project-config.yaml` → `summary.max_remediation_attempts` (project override)
2. `reference-architecture.yaml` → `summary.max_remediation_attempts` (canonical default: `3`)
3. Hard fallback: `3`

---

## 5. User Scenarios (Given-When-Then)

> **Language convention**: Story descriptions may be written in Brazilian Portuguese.
> Acceptance scenarios MUST be in English for BDD traceability with F5 QA agents.

### Scenario 1 — Nominal Path: Clean Summary (Priority: P1)

**Story**: Como o master-orchestrator, quero que a validação profunda rode automaticamente
após `/ava-summary` e confirme que o HTML está íntegro, sem exigir nenhum passo manual extra.

**Why this priority**: This is the primary happy path — zero manual intervention required.

**Acceptance Scenarios**:

1. **Given** a project where all phases (F1–F7) completed successfully and all
   contracted artifacts exist in `outputs/`, **When** `/ava-summary` is executed,
   **Then** `build_summary_comprehensive.py` runs, followed automatically by
   `validate_summary.py --deep`, and `deep-audit-report.json` is written with
   `summary.promotable: true`.
2. **Given** the above, **When** the deep audit completes with zero CRITICAL/HIGH
   findings, **Then** `ava-summary` reports success, `remediation-report.json` is
   NOT written (no remediation loop needed), and exit code is 0.
3. **Given** the above, **Then** `D.agentStatus` in the HTML correctly reflects all
   phases as done, and no `{{X}}` or `AG-NN` tokens appear in the rendered output.

---

### Scenario 2 — Remediation Loop: CRITICAL Finding Auto-Corrected (Priority: P1)

**Story**: Como o agente de remediação, quero detectar artefatos ausentes e corrigi-los
automaticamente sem intervenção do usuário, regenerando o HTML ao final.

**Why this priority**: Core value proposition — automatic self-healing.

**Acceptance Scenarios**:

1. **Given** a Summary HTML with one KPI tile showing `0` where `risk-register.md`
   exists and has 15 entries, **When** `ava-summary-remediation` runs, **Then**
   the deep audit produces a finding `C12.1` with severity `HIGH`, `auto_correctable: true`,
   and `suggested_fix` naming the correct parse path fix.
2. **Given** the above, **When** the remediation loop applies the fix and rebuilds
   the HTML, **Then** the KPI tile displays `15` and the finding no longer appears
   in the second-iteration deep audit.
3. **Given** `missing_artifact` finding for `security-map.md` (agent: `ava-asis-security-orchestrator`),
   **When** auto-correction runs, **Then** the responsible agent trigger is dispatched,
   the artifact is regenerated, and the next rebuild includes it.
4. **Given** a `mermaid_error` finding for `diag-c4ctx`, **When** auto-correction runs,
   **Then** `mermaid_playwright_gate.py` is called with the diagram source, fixes are
   applied per GR-001..GR-012, and the corrected diagram is reflected in the rebuilt HTML.

---

### Scenario 3 — Legitimate Empty: Phase Not Yet Executed (Priority: P2)

**Story**: Como o validador, quero distinguir "vazio por regra de negócio legítima"
(fase não executada) de "vazio por falha de geração", para não gerar falsos positivos.

**Why this priority**: Prevents noise that would erode team trust in the gate.

**Acceptance Scenarios**:

1. **Given** a project where only F1 was executed (`D.agentStatus.f2.done == false`),
   **When** the deep audit runs, **Then** all F2-origin sections that are empty are
   classified as `empty_legitimate` (INFO level), and zero CRITICAL/HIGH findings
   are raised for those sections.
2. **Given** the above, **Then** `deep-audit-report.json.summary.promotable` is `true`
   (partial pipeline run is not a promotion blocker).

---

### Scenario 4 — Retry Cap Reached: BLOCKED Status (Priority: P1)

**Story**: Como o usuário, quero ser informado claramente quando a remediação automática
não conseguiu resolver todos os problemas, com causa raiz e orientação de correção manual.

**Why this priority**: Safety gate — must never silently pass a broken summary.

**Acceptance Scenarios**:

1. **Given** a missing artifact that cannot be regenerated (responsible agent fails or
   is not available), **When** the remediation loop reaches `MAX_REMEDIATION_ATTEMPTS`
   with the finding still open, **Then** `remediation-report.json.final_status` is
   `BLOCKED`, exit code is `1`, and `unresolved_findings` lists the finding with
   `suggested_fix` containing manual remediation guidance.
2. **Given** the above, **Then** the HTML is NOT automatically delivered. The user must
   explicitly invoke `remediate_summary.py --force-promote` to override the BLOCKED state;
   when they do, `remediation-report.json."forced"` is `true`, exit code remains `1`,
   and a `[WARN] FORCED PROMOTION` header lists all unresolved findings.
3. **Given** MEDIUM/LOW-only findings remain after any loop iteration (including the
   first), **When** the loop breaks because no CRITICAL/HIGH findings are present,
   **Then** `final_status` is `PARTIAL`, exit code is `0`, the summary IS promotable,
   and the loop does NOT continue iterating to attempt further MEDIUM/LOW corrections.

---

### Scenario 5 — Edge Case: Mermaid Diagram Failure Reported in Consolidated Report (Priority: P2)

**Story**: Como o QA lead, quero que falhas de Mermaid apareçam no mesmo relatório
consolidado, citando a skill Playwright como fonte da checagem.

**Why this priority**: Unified report — no separate Mermaid-only channel needed.

**Acceptance Scenarios**:

1. **Given** the HTML contains a Mermaid diagram with invalid syntax, **When** the
   deep audit runs, **Then** `mermaid_playwright_gate.py` is invoked as a sub-step
   and its result is reflected as a C12.5 finding in `deep-audit-report.json`, with
   `finding_type: mermaid_error` and `agent_responsible: mermaid_playwright_gate`.
2. **Given** the above, **Then** the finding detail includes the diagram element ID
   and the specific syntax error reported by the Playwright gate.
3. **Given** the Playwright gate successfully fixes the diagram, **Then** the C12.5
   finding is absent from the second-iteration deep audit.

---

## 6. Quality Gate Requirements

- [x] Agent IDs follow `ava-{phase}-{role}` pattern — both are existing, registered agents (Article II)
- [x] Frontmatter contains only `name`, `version`, `description`, `allowed-tools` (Article II)
- [ ] `module.yaml` `version` field updated from `1.4.1` → `1.5.0` (Article IV — no new entry, only version bump)
- [x] All output paths use lowercase `{project_name}` and correct phase folder `outputs/summary/` (Article II)
- [x] BDD scenarios cover nominal (S1), remediation (S2), edge case (S3, S5), and gate paths (S4) (Article VI)
- [x] Security sub-pipeline impact: none — this agent reads security outputs but does not modify the security pipeline (Article VII)
- [x] No technology versions hardcoded — `MAX_REMEDIATION_ATTEMPTS` resolved from config (Article I)
- [x] Skill/Agent split: both agents retain existing split — `ava-summary-validate` internal-only, `ava-summary-remediation` user-facing via existing SKILL.md (Article XI)
- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] `--deep` flag is backward-compatible — existing `validate_summary.py` callers without `--deep` are unaffected

---

## 7. Dependencies

| Dependency | Agent / Script | Reason |
|---|---|---|
| Summary builder | `build_summary_comprehensive.py` | Exclusive HTML producer — all rebuilds go through it |
| Existing validator | `validate_summary.py` (C1–C11) | Deep audit extends this with `--deep` flag; does not replace it |
| Mermaid gate | `mermaid_playwright_gate.py` (spec 040) | Called as sub-step for C12.5; no reimplementation |
| Remediation script | `remediate_summary.py` | Existing repair script extended with deep-audit-driven corrections |
| Artifact manifest | `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` | Source of truth for expected artifacts per phase |
| Project config | `projects/{project_name}/context/project-config.yaml` | Resolves `MAX_REMEDIATION_ATTEMPTS` and project metadata |
| Reference architecture | `src/shared/data/reference-architecture.yaml` | Default value for `summary.max_remediation_attempts` |

---

## 8. Exclusions

- **No new Python test suites** — per scope decision: this spec delivers implementation tasks only, not a separate automated test suite.
- **No manual verification checklist** — the consolidated report (`remediation-report.json`) is the only deliverable for CI and manual inspection.
- **No reimplementation of Playwright/Mermaid validation** — `mermaid_playwright_gate.py` is consumed as-is; GR-001..GR-012 guardrails are not redefined here.
- **No new SKILL.md** — routing for `ava-summary-remediation` is unchanged; `ava-summary-validate` remains internal-only.
- **No upstream agent re-execution beyond auto-correction scope** — the remediation loop may invoke a responsible agent via its trigger code but does not orchestrate full phase re-runs.
- **Agent synthesis of HTML is prohibited** — handled exclusively by `build_summary_comprehensive.py` (existing invariant preserved).

---

## 9. Assumptions

- `artifact-map.yaml` (`src/modules/ava-fabric-agents/summary/data/`) is the canonical manifest listing all expected output artifacts per phase and their responsible agent ID. **Confirmed gap (audited 2026-08-18)**: current v1.0.1 covers `f1_asis`, `f2_tobe`, `f3_stack`, `f5_qa`, `f6_deliverables`, `f7_devops` — missing `f3_prototype` (F3 Prototype, added in Constitution v1.4.0) and `f8_summary` (cross-cutting Summary phase). Adding these two phase entries with their contracted artifacts is **mandatory scope** of this feature (Category 3 task). The deep auditor (C12.3) depends on a complete manifest to correctly classify `missing_artifact` findings.
- `D.agentStatus` in the Summary HTML data block is the authoritative signal for "has this phase executed?" — the deep auditor trusts it for legitimate-empty classification.
- `mermaid_playwright_gate.py` is callable as a Python module (`from mermaid_playwright_gate import run_playwright_mermaid_gate`) from within `validate_summary.py --deep`. No additional inter-process protocol is introduced.
- Responsible-agent trigger codes are already registered in their respective `module.yaml` files; the remediation loop uses those codes to dispatch agents without hardcoding invocation commands.
- The `--deep` flag added to `validate_summary.py` is backward-compatible: existing CI pipelines calling `validate_summary.py --project X` (without `--deep`) continue to execute C1–C11 only, with exit code semantics unchanged.

---

## Success Criteria

| Criterion | Measure |
|---|---|
| Auto-trigger on `/ava-summary` | Running `/ava-summary` always produces `deep-audit-report.json` — zero extra commands required from the user |
| Finding completeness | Every empty card, missing artifact, and divergent config in a test project is captured in `deep-audit-report.json` with correct `phase`, `agent_responsible`, and `severity` |
| Legitimate-empty precision | Zero false-positive CRITICAL/HIGH findings raised for phases not yet executed (validated by running against a single-phase project) |
| Mermaid integration | All Mermaid errors detected by `mermaid_playwright_gate.py` appear as C12.5 findings in the consolidated report — no separate Mermaid-only report channel required |
| Auto-correction efficacy | At least `missing_artifact`, `divergent_config`, `mermaid_error`, and `placeholder_unresolved` finding types are auto-corrected in the remediation loop without manual intervention |
| Retry cap enforced | Reaching `MAX_REMEDIATION_ATTEMPTS` with unresolved CRITICAL/HIGH yields exit code 1 and `final_status: BLOCKED` |
| CI compatibility | `remediation-report.json` exit code 0/1 integrates with existing CI gates without pipeline changes |
| Backward compatibility | Existing calls to `validate_summary.py --project X` (no `--deep`) pass all 101 existing rules unchanged |

---

## Clarifications

### Session 2026-08-18

- Q: O item `module.yaml version bump` no Quality Gate (Seção 6) deveria ser task explícita ou removido dado que Seção 1 diz "Category 4 N/A"? → A: **Opção A** — o bump `module.yaml version: 1.4.1 → 1.5.0` é trabalho real e entra como task de **Categoria 3** (config/metadata). "Category 4 N/A" cobre apenas registrar *novos* agentes; atualizar o campo `version` do módulo não é Category 4. A Seção 1 foi atualizada para esclarecer essa distinção. O gate `[ ]` permanece como indicador de trabalho pendente até a task ser executada.
- Q: Quando o dispatch do agente responsável falha (passo 3a do loop), o que acontece na mesma tentativa? → A: **Opção C** — dois caminhos distintos: (1) falha *transiente* (timeout / exit ≠ 0) consome a tentativa e o loop continua; (2) falha *estrutural* (agente não resolvível no `module.yaml`) marca o finding como `auto_correctable: false`, registra `dispatch_error` em `unresolved_findings`, e **não** consome a tentativa para esse finding. A Seção 4.4 foi atualizada com o pseudocódigo detalhado e um invariante explícito.
- Q: O "override explícito do usuário" para status BLOCKED já existe ou precisa ser desenhado nesta feature? → A: **Opção B** — implementar nesta feature o flag `--force-promote` em `remediate_summary.py`. Quando presente: HTML é entregue; `remediation-report.json."forced"` = `true`; exit code permanece `1`; emite `[WARN] FORCED PROMOTION` com lista de findings não resolvidos. Seções 3.2, 4.4, 4.6 e Cenário 4 (acc. scenario 2) foram atualizados. Vira task explícita de Categoria 3.
- Q: `final_status: PARTIAL` aplica-se somente após esgotar `MAX_REMEDIATION_ATTEMPTS` ou em qualquer iteração onde não restam CRITICAL/HIGH? → A: **Opção A** — PARTIAL aplica-se **em qualquer iteração**. O loop quebra (BREAK) imediatamente quando não há mais CRITICAL/HIGH, independentemente do número de tentativas consumidas. O loop não continua iterando apenas para tentar corrigir MEDIUM/LOW. Seção 4.4 (pseudocódigo do BREAK), 4.6 e Cenário 4 (acc. scenario 3) foram atualizados.
- Q: Atualizar `artifact-map.yaml` para cobrir 100% dos artefatos F1–F7 é escopo garantido ou task condicional? → A: **Opção A** — task **obrigatória** de Categoria 3. Auditoria confirmou: v1.0.1 cobre 6 fases mas está ausente `f3_prototype` (adicionado no Constitution v1.4.0) e `f8_summary`. A Seção 9 (Assumption 1) foi atualizada com o gap confirmado, os artefatos faltantes identificados, e a obrigatoriedade do escopo declarada explicitamente.

### Session 2026-08-18 (rodada 2)

- Q: Como tratar a sobreposição entre C11.39-41 (legados, renumerados pelo `/speckit.plan`) e C12.2/C12.6 (novos) quando `--deep` está ativo — Suprimir legados (A), manter com `duplicate_of` (B) ou restringir escopos para torná-los mutuamente exclusivos (C)? → A: **Opção C** — restrição de escopo sem supressão e sem mudança de schema. C12.2 regex reduzido a `{{X}}`, `[NEEDS CLARIFICATION]` e `AG-NN` apenas (`[INCOMPLETE]` → exclusivo de C11.39; `[ARTIFACT-MISSING]` → exclusivo de C11.40). C12.6 restrito a tabelas onde `<tbody>` existe mas tem zero `<tr>` (C11.41 cobre tabelas sem `<tbody>` algum — escopos HTML mutuamente exclusivos). Seção 4.1 (tabela C12 + invariante de deduplicação) e plan.md (§4.2, §4.3, §11) foram atualizados.

### Session 2026-08-19

- Q7 (rodada 3, 2026-08-19): Escopo de dispatch automático em v1 — O Success Criteria "Auto-correction efficacy" afirma que `missing_artifact`, `divergent_config`, `mermaid_error` e `placeholder_unresolved` são "auto-corrected in the remediation loop without manual intervention". Na prática, após os patches N1–N6, apenas `mermaid_error` possui estratégia real implementada em `_dispatch_correction()` via `_IMPLEMENTED_DISPATCH_STRATEGIES` em `remediate_summary.py`. Os outros 3 tipos (`missing_artifact`, `divergent_config`, `placeholder_unresolved`) possuem `auto_correctable: true` no schema de `deep-audit-report.json`, mas sempre caem em `[MANUAL]` no dispatch atual por ausência de implementação — não por falha de agente ou erro de execução. Esta limitação é intencional (decisão de escopo da v1 para evitar dispatch desonesto, documentada no patch N4). → A: **Opção A** — formalizar como clarificação sem alterar o Success Criteria original. O texto do SC permanece como contrato aspiracional da feature completa (o que ela deve entregar em iterações futuras), e `auto_correctable: true` nos 3 tipos sem estratégia real mantém o contrato de dados aberto para extensão: o flag sinaliza "este tipo é elegível para auto-correção quando uma estratégia de dispatch for implementada", não "este tipo será auto-corrigido nesta versão". Nenhuma mudança de código, schema ou comportamento já testado é necessária — a divergência é inteiramente resolvida por esta documentação explícita.
