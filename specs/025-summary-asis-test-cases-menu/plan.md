# Agent Implementation Plan: Summary — Add Test Cases AS-IS Menu

**Spec**: `specs/025-summary-asis-test-cases-menu/spec.md`
**Tech Stack**: See `src/shared/data/reference-architecture.yaml` (v1.0.0) — do not hardcode versions.

---

## Summary

| Field | Value |
|---|---|
| **Agents affected** | `ava-summary`, `ava-summary-validate`, `ava-summary-remediation` |
| **Phase** | F8 (Summary) |
| **Module** | `summary` |
| **Primary Requirement** | Display formal AS-IS test cases from `asis/qa/test-cases.md` in a new "Test Cases" sidebar item inside F1 — Diagnóstico AS-IS |
| **Technical Approach** | Add `build_test_cases()` parser, inject `D.testCases[]` into the HTML data object, add nav item + section `s-f1-tc` to the template, add C11.37 validator rule, and add Remediation Regra J |

---

## Constitution Check

- [X] **Article I** — No technology versions hardcoded; Python parsing uses regex only
- [X] **Article II** — No new agent frontmatter; all three modified agents already comply with `^ava-[a-z0-9-]+$`
- [X] **Article III** — No pipeline phase sequence change; Summary still runs after every phase
- [X] **Article IV** — No new agents → `module.yaml` unchanged
- [X] **Article V** — Agent body text in Brazilian Portuguese; JS function names/variables follow existing English convention
- [X] **Article VI** — 4 BDD scenarios in spec section 4 (nominal, absent artifact, validator warn, remediation)
- [X] **Article VII** — No security sub-pipeline impact
- [X] **Article VIII** — `trace_id` propagation unaffected; no new trace point needed
- [X] **Article IX** — N/A: all modified files are Python utility scripts or LLM `.md` prompt files
- [X] **Article X** — MINOR bump for `ava-summary` (new D.* field + new section → `1.8.0`); PATCH for `ava-summary-validate` and `ava-summary-remediation` (new optional rule → `1.4.1`)
- [X] **Article XI** — All three agents already have SKILL.md wrappers; no split change needed

### Quality Gate Check

- [X] No `[NEEDS CLARIFICATION]` markers remain in spec
- [X] Source path follows `projects/{project_name}/outputs/asis/qa/test-cases.md`
- [X] Downstream `ava-summary-validate` confirmed to exist

---

## Phase 0 — Research

### Resolved Questions

| Question | Answer | Evidence |
|---|---|---|
| Who produces `test-cases.md`? | `ava-asis-bridge-fastqa` Step 17b consolidates `fastqa/manual_test/test_cases/**/PBI-*.md` | `bridge-fastqa-asis.md` Step 17b |
| Markdown structure of `test-cases.md`? | H2 `## CT-NNN — <title>`, bold inline metadata, `### Pré-condições`, `### Passos` table, `### Pós-condições` | `projects/Meu-ERP_w_AST/outputs/asis/qa/test-cases.md` |
| Where is `D.*` data injected in the builder? | Lines ~8160–8205 in `build_summary_comprehensive.py` — `data_injection` f-string at `filetree_ph` anchor | `build_summary_comprehensive.py:8160` |
| Where is the `build_test_map()` call site? | Line ~7627: `test_map, test_gaps = build_test_map(asis_dir)` | `build_summary_comprehensive.py:7627` |
| How to add a CHECKS entry in `validate_summary.py`? | Add `_c11_37()` function after `_c11_36` (line ~1761); add `Check("C11.37", ...)` after C11.36 in `CHECKS` list (line ~2659) | `validate_summary.py:1761,2659` |
| How to add a Rule in `remediate_summary.py`? | After Rule I (~line 267), follow `write_if_absent()` + `synthesized.append()` pattern | `remediate_summary.py:267` |
| Where is the new nav item inserted? | After `s-f1-qa` item, before `s-f1-db` | `summary-template.html:776–779` |
| Where is the new section `<div>` inserted? | After closing `</div>` of `s-f1-qa`, before `<!-- F1: Banco de Dados -->` | `summary-template.html:~1333` |

---

## Phase 1 — Design & Contracts

### Data Model

**New `D.testCases` field** (Array):

```
TestCaseEntry {
  id:              string   // "CT-001"
  title:           string   // "Baixa Completa de Conta a Pagar (Happy Path)"
  priority:        string   // "P0"
  type:            string   // "Funcional"
  module:          string   // "Contas a Pagar — Baixa"
  rules:           string   // "BR-0001, BR-0002"
  steps:           number   // count of data rows in ### Passos table
  preconditions:   string   // raw text under ### Pré-condições
  steps_raw:       string   // raw Markdown of the ### Passos table
  postconditions:  string   // raw text under ### Pós-condições
}
```

**Source**: `projects/{project_name}/outputs/asis/qa/test-cases.md` (optional)

### KPI Tiles

| KPI | PT Label | EN Label | Formula |
|---|---|---|---|
| Total | `Total Test Cases` | `Total Test Cases` | `D.testCases.length` |
| P0 | `Casos P0` | `P0 Cases` | `filter priority === 'P0'` |
| Functional | `Funcionais` | `Functional` | `filter type includes 'Funcional'` |
| Negative/Edge | `Negativos / Edge` | `Negative / Edge` | `filter type includes 'Negativo' or 'Edge'` |

### i18n Keys (both `pt` and `en` sections)

| Key | PT | EN |
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

### Validator Rule C11.37

```
ID:       C11.37
Category: Content Completeness
Level:    warn   (optional artifact — test-cases.md only exists when FastQA has run)
Check:    D.testCases non-empty when asis/qa/test-cases.md has ≥1 CT- heading
Fix:      No auto-fix (data-level, builder must re-run)
```

### Remediation Regra J

```
When: asis/qa/test-cases.md absent AND fastqa/manual_test/ does not exist
Action: write synthesized placeholder (SYNTH_TAG header + message)
Do NOT synthesize when: fastqa/manual_test/ exists
  → that means FastQA has been run; Step 17b just hasn't consolidated yet
  → the gap is upstream, not a safe case for synthesis
```

---

## 1. Technical Context

| Dimension | Choice |
|---|---|
| Runtime | Python 3.x (`build_summary_comprehensive.py`, `validate_summary.py`, `remediate_summary.py`) |
| Template | HTML + vanilla JavaScript (`summary-template.html`) |
| CSS | Re-uses existing classes: `.kg`, `.kc`, `.at`, `.sv`, `.sc`, `.sa`, `.sm`, `.sb2` — no new CSS |
| Data contract | `D.testCases[]` in `const D = {}` — serialised via existing `safe_json()` |
| Source artifact | `asis/qa/test-cases.md` — optional; parser returns `[]` when absent |

---

## 2. Phase Placement

No pipeline phase sequence change. Feature only affects what `ava-summary` extracts and renders from existing `asis/` outputs, and the post-generation validator/remediation logic.

Quality gate: Summary Validator (after every phase) — C11.37 as `warn`, non-blocking.

---

## 3. Clean Architecture Alignment

N/A — all modified files are Python utility scripts and LLM `.md` prompt files, not application code.

---

## 4. File Impact Matrix

| File | Change | Version |
|---|---|---|
| `summary-template.html` | Nav item + section body + JS functions + i18n keys | — (not versioned) |
| `build_summary_comprehensive.py` | `build_test_cases()` + call site + `data_injection` line | — (not versioned) |
| `validate_summary.py` | `_c11_37()` function + `Check("C11.37",...)` entry | — (not versioned) |
| `remediate_summary.py` | Rule J block in `phase1_artifact_resolution()` | — (not versioned) |
| `summary-agent.md` | Step 0 read list + D.* schema + Data Source Mapping + HTML Structure | `1.7.0` → `1.8.0` |
| `summary-validate-agent.md` | C11.37 in rule table + description count | `1.4.0` → `1.4.1` |
| `summary-remediation-agent.md` | Regra J description + heuristics table row | `1.4.0` → `1.4.1` |

---

## 5. module.yaml Impact

No new agents created. No `module.yaml` change required.

---

## 6. trace_id Propagation

No new trace_id propagation required. `build_summary_comprehensive.py` already propagates `trace_id` through the HTML `data-trace` attribute. `D.testCases` is a data payload, not a trace point.

---

## 7. Implementation Steps (ordered)

### 7.1 `build_summary_comprehensive.py` — Add `build_test_cases()`

Insert a new function **after** the `build_test_map()` definition (~line 6741+), following the same docstring and return-list-of-dicts pattern:

```python
def build_test_cases(asis_dir: Path) -> list:
    """Parse asis/qa/test-cases.md into D.testCases[].

    Expects headings: ## CT-NNN — <title>
    Metadata fields: **ID**, **Prioridade**, **Tipo**, **Módulo**, **Regras**
    Subsections: ### Pré-condições, ### Passos (table), ### Pós-condições
    Returns [] when file absent or no CT- headings found.
    """
    tc_path = asis_dir / "qa" / "test-cases.md"
    if not tc_path.exists():
        return []
    text = tc_path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r'\n(?=## CT-)', text)
    results = []
    for block in blocks:
        m_head = re.match(r'^## (CT-\d+)\s*(?:—|-+)\s*(.+)', block)
        if not m_head:
            continue
        entry: dict = {
            "id": m_head.group(1).strip(),
            "title": m_head.group(2).strip(),
            "priority": "", "type": "", "module": "", "rules": "",
            "steps": 0, "preconditions": "", "steps_raw": "", "postconditions": "",
        }
        m_pri  = re.search(r'\*{1,2}Prioridade\*{1,2}\s*:\s*([^|\n*]+)', block)
        m_typ  = re.search(r'\*{1,2}Tipo\*{1,2}\s*:\s*([^|\n*]+)', block)
        m_mod  = re.search(r'\*{1,2}Módulo\*{1,2}\s*:\s*([^\n]+)', block)
        m_rul  = re.search(r'\*{1,2}Regras\*{1,2}\s*:\s*([^\n]+)', block)
        if m_pri: entry["priority"]  = m_pri.group(1).strip()
        if m_typ: entry["type"]      = m_typ.group(1).strip()
        if m_mod: entry["module"]    = m_mod.group(1).strip()
        if m_rul: entry["rules"]     = m_rul.group(1).strip()
        m_pre  = re.search(r'### Pré-condições\s*\n([\s\S]*?)(?=\n###|\Z)', block)
        m_step = re.search(r'### Passos\s*\n([\s\S]*?)(?=\n###|\Z)',        block)
        m_post = re.search(r'### Pós-condições\s*\n([\s\S]*?)(?=\n###|\Z)', block)
        if m_pre:  entry["preconditions"]  = m_pre.group(1).strip()
        if m_step:
            steps_text = m_step.group(1).strip()
            entry["steps_raw"] = steps_text
            data_rows = [l for l in steps_text.splitlines()
                         if l.startswith('|')
                         and not re.match(r'^\|[-:\s|]+$', l)
                         and not re.search(r'Ação|Action|^#', l[:12])]
            entry["steps"] = len(data_rows)
        if m_post: entry["postconditions"] = m_post.group(1).strip()
        results.append(entry)
    return results
```

### 7.2 `build_summary_comprehensive.py` — Call site

After the existing call `test_map, test_gaps = build_test_map(asis_dir)` (~line 7627), add:

```python
    test_cases = build_test_cases(asis_dir)
```

### 7.3 `build_summary_comprehensive.py` — `data_injection` injection

In the `data_injection` f-string block (~line 8175), after:
```python
        f'  testGaps: {safe_json(test_gaps)},\n'
```
add:
```python
        f'  testCases: {safe_json(test_cases)},\n'
```

Also update the build metrics log line to include `testCases={len(test_cases)}`.

### 7.4 `summary-template.html` — Sidebar nav item

After the `s-f1-qa` nav item and before the `s-f1-db` nav item (~line 778), insert:

```html
    <div class="ni" onclick="nav('s-f1-tc',this)">
      <span class="nd" id="nd-f1-tc"></span>
      <span data-i18n="nav-tc">Test Cases</span>
      <span class="nb" id="nb-tc" style="display:none">0</span>
    </div>
```

### 7.5 `summary-template.html` — Section `<div>`

After the closing `</div>` of the `s-f1-qa` section and before the `<!-- F1: Banco de Dados -->` comment (~line 1334), insert:

```html
<!-- F1: Test Cases AS-IS ───────────────────────────────── -->
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
      <table class="at">
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

### 7.6 `summary-template.html` — i18n keys

Locate the `pt:` and `en:` JS objects and add the 10 new key-value pairs to each.

### 7.7 `summary-template.html` — `renderTCKpis()` JS function

Add after existing `renderTestTables()` function:

```javascript
function renderTCKpis() {
  var tcs = D.testCases || [];
  var total = tcs.length;
  var p0   = tcs.filter(function(t){ return t.priority === 'P0'; }).length;
  var func = tcs.filter(function(t){ return t.type && t.type.indexOf('Funcional') >= 0; }).length;
  var neg  = tcs.filter(function(t){ return t.type && (t.type.indexOf('Negativo') >= 0 || t.type.indexOf('Edge') >= 0); }).length;
  var badge = document.getElementById('nb-tc');
  if (badge) { badge.textContent = total; badge.style.display = total > 0 ? '' : 'none'; }
  var tagEl = document.getElementById('tag-tc');
  if (tagEl) tagEl.textContent = total + ' TCs';
  _setDot('nd-f1-tc', total > 0 ? 'ok' : 'idle');
  var kpiEl = document.getElementById('kpi-tc');
  if (!kpiEl) return;
  kpiEl.innerHTML = [
    { l: T('kpi-tc-total', 'Total'), v: total, cls: '' },
    { l: T('kpi-tc-p0', 'P0'), v: p0, cls: p0 > 0 ? 'r' : '' },
    { l: T('kpi-tc-func', 'Funcionais'), v: func, cls: '' },
    { l: T('kpi-tc-neg', 'Negativos/Edge'), v: neg, cls: '' }
  ].map(function(k){
    return '<div class="kc"><div class="kl">' + k.l + '</div><div class="kv ' + k.cls + '">' + k.v + '</div></div>';
  }).join('');
}
```

### 7.8 `summary-template.html` — `renderTestCases()` JS function

Add after `renderTCKpis()`:

```javascript
function renderTestCases() {
  var tcs = D.testCases || [];
  var wrap = document.getElementById('card-tc-wrap');
  if (wrap) wrap.style.display = tcs.length === 0 ? 'none' : '';
  var tb = document.getElementById('tb-tc-body');
  if (!tb) return;
  if (tcs.length === 0) { tb.innerHTML = ''; return; }
  function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function priBadge(p){
    var cls = p === 'P0' ? 'sc' : p === 'P1' ? 'sa' : p === 'P2' ? 'sm' : 'sb2';
    return '<span class="sv ' + cls + '">' + esc(p) + '</span>';
  }
  tb.innerHTML = tcs.map(function(t){
    return '<tr>' +
      '<td class="mono fw">' + esc(t.id) + '</td>' +
      '<td>' + esc(t.title) + '</td>' +
      '<td>' + esc(t.module) + '</td>' +
      '<td>' + priBadge(t.priority) + '</td>' +
      '<td>' + esc(t.type) + '</td>' +
      '<td class="mono" style="font-size:10px">' + esc(t.rules) + '</td>' +
      '<td style="text-align:center">' + (t.steps || 0) + '</td>' +
      '</tr>';
  }).join('');
}
```

> ⚠️ Implementer: verify whether an `esc()` or `h()` HTML-escape helper already exists in the template. If so, use it instead of defining a new local one inside `renderTestCases()`.

### 7.9 `summary-template.html` — Wire into `renderAll()`

Locate `renderAll()` and add two calls (adjacent to other `render*` calls):

```javascript
renderTCKpis();
renderTestCases();
```

### 7.10 `validate_summary.py` — `_c11_37()` + `Check` entry

After `_c11_36()` (~line 1785), add:

```python
def _c11_37(ctx: Ctx) -> Result:
    """D.testCases non-empty when asis/qa/test-cases.md has real CT- headings.
    Level is warn (not error) because test-cases.md is produced by
    ava-asis-bridge-fastqa and is optional — its absence does not block the summary."""
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

After the `C11.36` entry in `CHECKS` (~line 2659), add:

```python
    Check("C11.37", "Content Completeness", "warn",
          "D.testCases is non-empty when asis/qa/test-cases.md has CT- headings",
          "build_test_cases() in build_summary_comprehensive.py must parse CT- blocks and "
          "inject them as testCases in the D object — verify call site and data_injection f-string.",
          _c11_37),
```

### 7.11 `remediate_summary.py` — Rule J

After the Rule I block (~line 267), add:

```python
    # Rule J — Test Cases AS-IS (ava-asis-bridge-fastqa Step 17b)
    # Only synthesize a placeholder when test-cases.md is absent AND there is no
    # evidence that FastQA has been run (fastqa/manual_test/ absent).
    # When fastqa/manual_test/ exists but Step 17b hasn't run yet,
    # the gap is upstream — do not fabricate synthetic test cases.
    tc_path_j = qa_dir / "test-cases.md"
    if not tc_path_j.exists():
        has_fastqa_manual = (BASE_DIR / "fastqa" / "manual_test").exists()
        if not has_fastqa_manual:
            if write_if_absent(
                tc_path_j,
                SYNTH_TAG.replace("{agent}", "ava-asis-bridge-fastqa")
                + "# Test Cases AS-IS\n\n"
                  "> No test cases available. "
                  "Run @ava-asis-bridge-fastqa (Step 17b) to consolidate "
                  "test cases from fastqa/manual_test/test_cases/.\n",
            ):
                synthesized.append(str(tc_path_j))
                log.append("✅ Rule J: synthesized placeholder test-cases.md")
```

### 7.12 `summary-agent.md` — Documentation

1. Add to **Step 0 F1 read list** (after `test-gaps.md`):
   ```
   Read: asis/qa/test-cases.md  (CT-NNN blocks — produced by ava-asis-bridge-fastqa Step 17b; optional)
   ```
2. Add row to **D.* Field Schemas** table:
   ```
   | `D.testCases` | `renderTestCases()` | `{id, title, priority, type, module, rules, steps, preconditions, steps_raw, postconditions}` |
   ```
3. Add row to **Data Source Mapping** table:
   ```
   | `testCases` | `asis/qa/test-cases.md` | `## CT-\d+` headings → extract metadata fields + step count |
   ```
4. Add under F1 in **Output HTML Structure**:
   ```
   └─ Test Cases               ← qa/test-cases.md (CT-NNN blocks: id, title, priority, type, module, rules, steps)
   ```
5. Bump version frontmatter: `1.7.0` → `1.8.0`

### 7.13 `summary-validate-agent.md` — Documentation

1. Add C11.37 row to the C11 rule table:
   ```
   | C11.37 | `warn` | `D.testCases` non-empty when `asis/qa/test-cases.md` has ≥1 `CT-` heading | não |
   ```
2. Increment rule count in description frontmatter by 1.
3. Bump version: `1.4.0` → `1.4.1`

### 7.14 `summary-remediation-agent.md` — Documentation

1. Add **Regra J** paragraph in Fase 1 section (after Regra I).
2. Add C11.37 row to the heuristics table in Fase 5:
   ```
   | **Test Cases AS-IS não pode ficar vazio com dado real disponível** | O menu "Test Cases" (F1-AS-IS) NUNCA deve exibir `D.testCases` vazio quando `asis/qa/test-cases.md` possui entradas `CT-` válidas. | `build_test_cases()` (`build_summary_comprehensive.py`); guardado por `C11.37` |
   ```
3. Bump version: `1.4.0` → `1.4.1`

---

## 8. Regression Safety

All changes are purely additive:
- New HTML section and nav item do not touch existing ones
- `build_test_cases()` is a standalone function; `build_test_map()` is unchanged
- `D.testCases` is a new field; existing fields in `data_injection` are untouched
- C11.37 is `warn`; no existing `error` check is modified
- Rule J in `remediate_summary.py` is additive; Rules A–I are unchanged
- `C11.34` (Test Gaps AS-IS) is not affected — it reads `test-gaps.md`, not `test-cases.md`

---

## 9. Complexity Tracking

| Risk | Severity | Mitigation |
|---|---|---|
| `test-cases.md` format varies across projects | Medium | Forgiving regex; missing fields default to `""` without raising |
| Large `D.testCases` payload for projects with many CTs | Low | Only string fields; `safe_json()` handles it like `testGaps` |
| `esc()` / `h()` helper name collision in JS | Low | Implementer must grep template before adding a new `esc()` local |
| `renderAll()` exact location in template | Low | Implementer uses grep to locate call site |
| `steps_raw` field contains raw Markdown that may include backticks | Low | `safe_json()` handles escaping; field is informational only |

---

## 10. Quickstart Reference

See [quickstart.md](quickstart.md) for validation commands after implementation.
