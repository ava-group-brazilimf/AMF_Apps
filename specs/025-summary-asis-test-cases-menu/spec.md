# Spec: Summary — Add Test Cases AS-IS Menu to F1 Sidebar

**Feature Branch**: `025-summary-asis-test-cases-menu`
**Created**: 2026-07-20
**Status**: Draft
**Change Type**: `modify-existing`
**Spec Number**: `025`

> **Language note**: This spec is a planning document written in **English**.
> Implementation changes in agent `.md` files and HTML templates MUST keep Brazilian Portuguese per Constitution Article V.

---

## 1. Overview

The `ava-summary` agent generates an interactive HTML report consolidating all pipeline phases. The F1 — Diagnóstico AS-IS group in the left sidebar currently includes sections for Architecture, Business Modules, Documentation, Business Rules, Screen Flow, Inventory & Metrics, Security Review, Test Baseline, Database, Events/Pub-Sub, and Gap List.

This feature adds a new **Test Cases** menu item to the F1 group. The section displays the formal test cases stored in `projects/{project_name}/outputs/asis/qa/test-cases.md` — the artifact produced by `ava-asis-bridge-fastqa` (Step 17b) and consumed in the FastQA pipeline. The section header in the HTML is `Test Cases AS-IS`.

### Source Artifact

| Field | Value |
|---|---|
| **Source file** | `projects/{project_name}/outputs/asis/qa/test-cases.md` |
| **Producer agent** | `ava-asis-bridge-fastqa` (Step 17b — consolidated test cases from `fastqa/manual_test/test_cases/`) |
| **Format** | Markdown with H2/H3 headings per test case; table of `# | Ação | Resultado Esperado` steps; frontmatter metadata fields `ID`, `Prioridade`, `Tipo`, `Módulo`, `Regras` |

### Example artefact structure (from `test-cases.md`)

```markdown
## CT-001 — Baixa Completa de Conta a Pagar (Happy Path)

**ID**: CT-001
**Prioridade**: P0 | **Tipo**: Funcional
**Módulo**: Contas a Pagar — Baixa
**Regras**: BR-0001, BR-0002

### Pré-condições
...

### Passos
| # | Ação | Resultado Esperado |
|---|---|---|
| 1 | ... | ... |
```

---

## 2. Affected Components

| Component | Change Type | Description |
|---|---|---|
| `summary-template.html` | Modify | Add nav item `s-f1-tc` + section `<div id="s-f1-tc">` |
| `build_summary_comprehensive.py` | Modify | Add `build_test_cases()` parser; inject `D.testCases` into HTML data; update Step 0 Read list |
| `summary-agent.md` | Modify | Add `test-cases.md` to Step 0 F1 read list; add `D.testCases` to D.* Field Schemas; update Output HTML Structure |
| `summary-validate-agent.md` | Modify | Add C11.37 rule: `D.testCases` non-empty when `asis/qa/test-cases.md` exists |
| `validate_summary.py` | Modify | Implement C11.37 check |
| `summary-remediation-agent.md` | Modify | Add Regra J in Fase 1: synthesize empty placeholder when `test-cases.md` absent; add C11.37 to heuristics table |
| `remediate_summary.py` | Modify | Implement Regra J |

---

## 3. Detailed Changes

### 3.1 `summary-template.html` — Sidebar Nav Item

Insert after the existing `s-f1-qa` nav item (Test Baseline) and before `s-f1-db`:

```html
<div class="ni" onclick="nav('s-f1-tc',this)">
  <span class="nd" id="nd-f1-tc"></span>
  <span data-i18n="nav-tc">Test Cases</span>
  <span class="nb" id="nb-tc" style="display:none">0</span>
</div>
```

The `nb-tc` badge displays the total count of test cases parsed from `test-cases.md`.

### 3.2 `summary-template.html` — Section Body

Insert after `</div><!-- /s-f1-qa -->` and before `<!-- F1: Banco de Dados -->`:

```html
<!-- F1: Test Cases ─────────────────────────────────────── -->
<div id="s-f1-tc" class="sec">
  <div class="ph">
    <h1 data-i18n="pg-tc">Test Cases AS-IS</h1>
    <p><span class="mono">asis/qa/test-cases.md</span></p>
    <div class="hl"></div>
  </div>
  <div class="kg" id="kpi-tc"><!-- renderTCKpis() --></div>
  <div class="cd" id="card-tc-wrap">
    <div class="ch">
      <h2 data-i18n="card-tc">Test Cases</h2>
      <span class="ctag bOk" id="tag-tc">0 TCs</span>
    </div>
    <div class="cb" style="padding:0">
      <table class="at" id="tb-tc">
        <thead><tr>
          <th data-i18n="th-tc-id">ID</th>
          <th data-i18n="th-tc-title">Título</th>
          <th data-i18n="th-tc-module">Módulo</th>
          <th data-i18n="th-tc-priority">Prioridade</th>
          <th data-i18n="th-tc-type">Tipo</th>
          <th data-i18n="th-tc-rules">Regras</th>
          <th data-i18n="th-tc-steps">Passos</th>
        </tr></thead>
        <tbody id="tb-tc-body"></tbody>
      </table>
    </div>
  </div>
</div>
```

### 3.3 `summary-template.html` — i18n Keys

Add to the PT/EN i18n dictionary:

| Key | PT value | EN value |
|---|---|---|
| `nav-tc` | `Test Cases` | `Test Cases` |
| `pg-tc` | `Test Cases AS-IS` | `Test Cases AS-IS` |
| `card-tc` | `Test Cases` | `Test Cases` |
| `th-tc-id` | `ID` | `ID` |
| `th-tc-title` | `Título` | `Title` |
| `th-tc-module` | `Módulo` | `Module` |
| `th-tc-priority` | `Prioridade` | `Priority` |
| `th-tc-type` | `Tipo` | `Type` |
| `th-tc-rules` | `Regras` | `Rules` |
| `th-tc-steps` | `Passos` | `Steps` |

### 3.4 `summary-template.html` — `renderTCKpis()` and `renderTestCases()` JavaScript

Add to the JS block two render functions:

**`renderTCKpis()`** — renders KPI tiles for the Test Cases section:
- Total test cases (`D.testCases.length`)
- P0 count (priority filter)
- Functional count (type filter)
- Negative/edge-case count (where `type` contains "Negativo" or "Edge")

**`renderTestCases()`** — renders the `#tb-tc-body` tbody:
- One row per entry in `D.testCases`
- Columns: `id`, `title`, `module`, `priority`, `type`, `rules`, `steps` (numeric count)
- Priority badge: P0 → `.sc` (red), P1 → `.sa` (amber), P2 → `.sm` (yellow), P3+ → `.sb2` (green)

Both functions are called from the central `renderAll()` initializer.

### 3.5 `summary-template.html` — nav-dot wiring

Nav dot `nd-f1-tc` is updated by calling `_setDot('nd-f1-tc', ...)` inside `renderTCKpis()` — green (`.ok`) when `D.testCases.length > 0`, grey (`.idle`) otherwise. No separate `renderNavDots()` call is required.

### 3.6 `build_summary_comprehensive.py` — `build_test_cases()` parser

New function `build_test_cases(asis_dir: Path) -> list`:
- Path: `asis_dir / "qa" / "test-cases.md"`
- If not found: return `[]`
- Parser logic:
  1. Split on `## CT-` headings
  2. For each block extract:
     - `id`: e.g. `CT-001`
     - `title`: text after ` — ` on the heading line
     - `priority`: value after `**Prioridade**:`  (strip `| **Tipo**:...` suffix)
     - `type`: value after `**Tipo**:`
     - `module`: value after `**Módulo**:`
     - `rules`: value after `**Regras**:` (comma-separated list)
     - `steps`: count of `|` table rows under `### Passos`
     - `preconditions`: raw text under `### Pré-condições`
     - `steps_raw`: raw markdown of the `### Passos` table (stored for potential future use)
     - `postconditions`: raw text under `### Pós-condições`
  3. Return list of dicts with those fields
- Return schema: `{id, title, priority, type, module, rules, steps, preconditions, steps_raw, postconditions}`

### 3.7 `build_summary_comprehensive.py` — inject `D.testCases`

In the main `build_html()` / `_build_d_object()` function:
1. Call `test_cases = build_test_cases(asis_dir)` alongside existing `build_test_map()` call
2. Inject as `testCases: {safe_json(test_cases)},` in the `const D = {}` block
3. Update the build log line (Step 4.7 metrics) to include `testCases={len(test_cases)}`

### 3.8 `summary-agent.md` — Step 0 F1 Read List

Add to the **F1 — Diagnóstico AS-IS** read block:

```
Read: asis/qa/test-cases.md  (consolidated test cases — CT-NNN — produced by ava-asis-bridge-fastqa Step 17b)
```

### 3.9 `summary-agent.md` — D.* Field Schemas

Add to the D.* Field Schemas table:

| D.* Field | Template Function | Required Keys |
|---|---|---|
| `D.testCases` | `renderTestCases()` | `{id: string, title: string, priority: string, type: string, module: string, rules: string, steps: int, preconditions: string, steps_raw: string, postconditions: string}` |

### 3.10 `summary-agent.md` — Data Source Mapping

Add to the Data Source Mapping table:

| D.* Field | Source File(s) | Parser Pattern |
|---|---|---|
| `testCases` | `asis/qa/test-cases.md` | `## CT-\d+` headings → extract metadata fields + step count |

### 3.11 `summary-agent.md` — Output HTML Structure

Add under `F1 — Diagnóstico AS-IS`:

```
└─ Test Cases               ← qa/test-cases.md (CT-NNN blocks: id, title, priority, type, module, rules, steps)
```

### 3.12 `summary-validate-agent.md` — C11.37 Rule

Add to the **C11 Content Completeness & UI Cleanup** rule table:

| Rule | Level | Check | Auto-fix |
|---|---|---|---|
| C11.37 | `warn` | `D.testCases` is non-empty when `asis/qa/test-cases.md` exists and has ≥ 1 `## CT-` heading | não |

Rationale: `warn` (not `error`) because `test-cases.md` is optional — it is produced by `ava-asis-bridge-fastqa` only when FastQA has been run. Its absence does not block the summary.

Also update the rule count in the agent `description` frontmatter (increment by 1).

### 3.13 `validate_summary.py` — C11.37 implementation

Add check function:

```python
def _c11_37(ctx: Ctx) -> Result:
    """D.testCases non-empty when asis/qa/test-cases.md has CT- headings."""
    asis_dir = ctx.outputs_dir / "asis"
    tc_path = asis_dir / "qa" / "test-cases.md"
    if not tc_path.exists():
        return Result(True, "test-cases.md absent — C11.37 skipped")
    text = tc_path.read_text(encoding="utf-8", errors="replace")
    has_ct = bool(re.search(r'^## CT-', text, re.MULTILINE))
    if not has_ct:
        return Result(True, "test-cases.md has no CT- headings — C11.37 skipped")
    m = re.search(r'\btestCases\s*:\s*(\[[\s\S]*?\])\s*,\s*\n', ctx.html)
    has_data = bool(m and m.group(1).strip() not in ('[]', ''))
    return Result(
        has_data,
        "D.testCases populated from test-cases.md" if has_data
        else "test-cases.md has CT- entries but D.testCases is empty — "
             "verify build_test_cases() is called and its return value is injected "
             "as testCases in the data_injection f-string"
    )
```

Register in `CHECKS` list with `id="C11.37"`, `level="warn"`.

### 3.14 `summary-remediation-agent.md` — Regra J (Fase 1)

Add **Regra J — Test Cases AS-IS**: The expected artifact is `asis/qa/test-cases.md`, produced by `ava-asis-bridge-fastqa` (Step 17b). This rule only synthesizes a placeholder `# synthesized-by-FS — replace with output from @ava-asis-bridge-fastqa` file when:
- `asis/qa/test-cases.md` is absent **AND**
- `D.testCases` is empty **AND**
- There is no evidence of FastQA having been run (no `fastqa/manual_test/` directory or all test-case files under it are empty)

When the file is merely absent but FastQA has produced manual test cases, the remediation agent does **not** synthesize — it reports the gap as a legitimate upstream deficit (`ava-asis-bridge-fastqa` Step 17b must run).

### 3.15 `summary-remediation-agent.md` — C11.37 in heuristics table

Add to the heuristics table in Fase 5:

| Heurística | Regra | Onde é aplicada |
|---|---|---|
| **Test Cases AS-IS não pode ficar vazio com dado real disponível** | O menu "Test Cases" (F1-AS-IS) NUNCA deve exibir `D.testCases` vazio quando `asis/qa/test-cases.md` possui entradas `CT-` válidas. | `build_test_cases()` (`build_summary_comprehensive.py`); guardado por `C11.37` |

### 3.16 `remediate_summary.py` — Regra J implementation

Add logic in `phase1_artifact_resolution()` (alongside existing rules A–I):

```python
# Regra J — Test Cases AS-IS
tc_path = asis_dir / "qa" / "test-cases.md"
if not tc_path.exists():
    has_fastqa_manual = (project_root / "fastqa" / "manual_test").exists()
    if not has_fastqa_manual:
        tc_path.parent.mkdir(parents=True, exist_ok=True)
        tc_path.write_text(
            "# synthesized-by-FS — replace with output from @ava-asis-bridge-fastqa\n"
            "# No test cases found. Run @ava-asis-bridge-fastqa (Step 17b) to generate.\n",
            encoding="utf-8"
        )
        fixes.append("Regra J: synthesized placeholder test-cases.md")
```

---

## 4. User Scenarios

### Scenario 1 — Test Cases section displayed with data

**Story**: Como revisor do pipeline, quero ver os casos de teste AS-IS no relatório HTML para validar a cobertura funcional sem abrir arquivos individuais.

```gherkin
Given asis/qa/test-cases.md exists with at least 3 CT- headings
When the summary is generated via build_summary_comprehensive.py
Then the sidebar shows "Test Cases" under F1 — Diagnóstico AS-IS
And D.testCases contains one entry per CT- block
And the section displays a table with ID, Title, Module, Priority, Type, Rules, Steps columns
And the badge nb-tc shows the correct total count
And the nav dot nd-f1-tc is green
```

### Scenario 2 — Test Cases section hidden when artifact absent

**Story**: Como revisor, quero que a seção fique oculta ou vazia quando o artefato ainda não foi gerado.

```gherkin
Given asis/qa/test-cases.md does not exist
When the summary is generated
Then D.testCases is an empty array []
And the section renders with an empty table (or card hidden if guard logic added)
And the nav dot nd-f1-tc is grey (idle)
And C11.37 check in the validator emits "skipped" (not a warn)
```

### Scenario 3 — Validator detects empty D.testCases with real data present

**Story**: Como gate de qualidade, quero que o validador avise quando o artefato existe mas o builder não populou D.testCases.

```gherkin
Given asis/qa/test-cases.md has 6 CT- headings
And D.testCases in the generated HTML is []
When validate_summary.py runs
Then C11.37 fires as a "warn"
And the validation report lists the check with remediation pointing to build_test_cases()
```

### Scenario 4 — Remediation synthesizes placeholder only when justified

**Story**: Como remediação automática, quero criar um placeholder apenas quando nenhuma fonte de casos de teste existe no projeto.

```gherkin
Given asis/qa/test-cases.md does not exist
And the fastqa/manual_test/ directory does not exist
When remediate_summary.py runs
Then a placeholder test-cases.md is written with synthesized-by-FS header
And the remediation report logs "Regra J: synthesized placeholder test-cases.md"
```

---

## 5. Success Criteria

- A new "Test Cases" nav item appears in F1 group in the sidebar for any project
- For a project with `asis/qa/test-cases.md`, `D.testCases` is populated and the section table shows all CT- entries
- For a project without `asis/qa/test-cases.md`, no error is thrown; `D.testCases = []`
- `validate_summary.py` C11.37 check correctly fires `warn` when data is present but not rendered, and is silent when the file is absent
- `remediate_summary.py` Regra J synthesizes a placeholder only when truly no upstream test-case data exists
- The HTML is still self-contained (no new CDN dependencies)
- No regression in existing C11.* checks (confirmed by running validate_summary.py on existing project)

---

## 6. Non-Goals

- This feature does **not** add an ability to run or execute test cases from within the summary HTML
- This feature does **not** implement a row-click modal or detail drawer — clicking a test case row does not expand step-by-step details in this version
- This feature does **not** parse test cases from formats other than the `CT-NNN` Markdown pattern produced by `ava-asis-bridge-fastqa`
- This feature does **not** modify the `ava-asis-bridge-fastqa` agent itself
- This feature does **not** add a corresponding F5 QA section (test cases are surfaced in F1 where they are generated, not in F5)

---

## 7. Assumptions

- `test-cases.md` follows the format shown in the reference example: H2 headings `## CT-NNN — <title>`, inline metadata bold fields, `### Passos` table, `### Pré-condições` and `### Pós-condições` subsections
- Absent `test-cases.md` is a valid state and must not cause a build failure
- The `build_summary_comprehensive.py` `safe_json()` helper handles serialisation of the `testCases` array correctly (consistent with how `testMap` and `testGaps` are serialised today)

---

## 8. Open Questions

None — the scope is fully bounded by the referenced source artifact and existing template patterns.
