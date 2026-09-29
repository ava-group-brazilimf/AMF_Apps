# Architecture Blueprint Mermaid Compatibility

Before publishing a Summary, the compatibility gate reads the existing AS-IS
and TO-BE `architecture-blueprint.mmd` artifacts, loads the exact local Mermaid
bundle used by `summary-template.html`, probes `mermaid.version`, tests C4 with
`mermaid.render()`, validates source hashes, and writes the JSON/Markdown
compatibility reports. A failed or incomplete probe blocks client-facing HTML.

The public report uses camelCase fields and `rootCause` values. Inspect
`outputs/summary/compatibility/blueprint-compatibility-report.json` first.

`C4Container` support is not inferred from bundle text. It is supported only
when the loaded runtime exposes a compatible version and the C4 capability
fixture renders successfully. Plugin-required, disabled, unsupported-keyword,
malformed, initialization, and version cases are classified separately.

## Follow-up fora do escopo

`renderTCKpis` / `_setDot` permanece um defeito JavaScript independente. Não é
alterado pela compatibilidade Mermaid/C4; deve ser tratado em uma issue própria.

O harness de layout C4 identifica o primeiro gatilho do `c4-component.mmd` como
`Rel(acl, bankapi, "Calls", "REST HTTPS")` quando as declarações completas e as
relações anteriores estão presentes. O grafo possui aliases resolvidos; portanto
o finding é `RENDERING_FAILURE` no estágio `C4_LAYOUT_RENDER`, não erro de parse
ou integridade de aliases. Segmentação só pode ser aprovada se cada segmento
renderizar e todos os relacionamentos forem preservados.

A matriz mínima Component→Component/System_Ext/Container_Ext/Person_Ext/System
renderiza com Mermaid 11.14.0. Portanto, a combinação isolada de tipos não
confirma um defeito universal do renderer; o problema depende da composição,
densidade ou layout do diagrama completo. O relatório da matriz fica em
`outputs/summary/compatibility/c4-layout-compatibility-matrix.json`.

Para `c4-component.mmd`, a segmentação explícita usa três segmentos: duas
partições de relações estáveis e um segmento focado no par `acl → bankapi` com
as declarações concretas necessárias. Todos os 10 relacionamentos são
preservados e cada segmento deve retornar `VALID_MERMAID` antes de
`publicationAllowed` ser elevado a `true`. O relatório fica em
`outputs/summary/compatibility/c4-component-segmentation-diagnostic.json`.

For `Syntax error in text` / `mermaid version 11.14.0`, check `rendererVersion`,
`rendererSource`, `detectedDialect`, `c4SupportedByRenderer`, `exactErrorMessage`,
`stage`, and the six `hashes` checkpoints. Missing artifact is an upstream
boundary condition; this feature does not generate or discover artifacts.

# Summary Validator Agent — Operation Guide

**Agent ID**: `ava-summary-validate`
**Phase**: 8.5 of 8 (post-`ava-summary`)
**Script**: [`src/modules/ava-fabric-agents/summary/utils/validate_summary.py`](../src/modules/ava-fabric-agents/summary/utils/validate_summary.py)
**Definition**: [`src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`](../src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md)

---

## 1. What it is

A **non-regression quality gate** that runs automatically at the end of every
`ava-summary` build. It audits the freshly generated `AVA-FABRIC-SUMMARY-*.html`
against 101 deterministic rules derived from historical fixes (extensible to 102–103 via planned **C13 Screen Flow Completeness**), then either:

- **Passes** (exit 0) — the HTML is safe to hand to the client.
- **Auto-repairs** safe regressions in-place and re-validates.
- **Fails** (exit 1) with a precise report when a data-level regression
  can't be auto-fixed.

Without this agent, any edit to the template or builder can silently re-break
issues that were expensive to fix the first time — empty KPIs, broken Mermaid,
language drift, orphan nav items, duplicate Mermaid bundle injection, etc.

---

## 2. When it runs

```
┌────────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  ava-summary   │ ──▶ │ HTML written │ ──▶ │  ava-summary-       │
│ (build script) │     │  to disk     │     │  validate           │
└────────────────┘     └──────────────┘     └─────────┬───────────┘
                                                       │
                               ┌───────────────────────┼─────────────┐
                               │                       │             │
                          fix applied ?            all pass          error
                               │                       │             │
                               ▼                       ▼             ▼
                       re-validate loop            exit 0        exit 1
                       (max 2 passes)           ✅ promotable  ❌ hold
```

Triggered automatically from `build_summary_complete.py`; also runnable
standalone via CLI.

---

## 3. How it works (architecture)

### 3.1 Inputs

```yaml
inputs:
  project_name: string # e.g. "Meu-ERP"
  auto_fix: bool # default True in the builder path
```

The validator auto-discovers:

- The newest `AVA-FABRIC-SUMMARY-*.html` in `projects/{name}/outputs/summary/` (by mtime)
- `projects/{name}/context/project-config.yaml` (for `language` flag)
- `projects/{name}/context/shared-context.md` (for ✅ phase markers)
- All source documents under `outputs/asis/` + `outputs/tobe/`

### 3.2 Pipeline

1. **Load** — read HTML + context files once.
2. **Parse** — extract `D.*` fields (kpis, ccTop, bizRules, fileTree, etc.)
   via a safe balanced-delimiter scanner (no `eval` / no JS execution).
3. **Audit** — run all 48 rules; each returns `(ok, detail)`.
4. **Auto-fix** (if enabled) — for each failed rule that has a registered
   fix function, apply it and persist the patched HTML.
5. **Re-validate** — up to `max_fix_passes` (default 2) to handle
   interdependent fixes.
6. **Report** — write both human-readable Markdown and machine-readable JSON
   to `projects/{name}/outputs/summary/validation-report.{md,json}`.
7. **Gate** — exit 0 if all errors pass, exit 1 otherwise.

### 3.3 Output artifacts

| File                     | Audience        | Role                                                                      |
| ------------------------ | --------------- | ------------------------------------------------------------------------- |
| `validation-report.md`   | Humans          | Grouped by severity → errors first, warnings, then full list per category |
| `validation-report.json` | CI / dashboards | Per-check status, applied fixes, summary counts, metadata                 |

---

## 4. The rule catalog (101 rules in 11 categories + 1 planned)

> Note: C10, C11, C12 are documented in the agent definition; `validate_summary.py` currently
> implements C1–C9 fully and C10–C12 incrementally. C13 is planned for `ava-asis-documentation` v3.0.0.

### C1 — Template Integrity (5 rules)

| ID   | Level | Check                                                               |
| ---- | ----- | ------------------------------------------------------------------- |
| C1.1 | error | Signature `AVA Fabric Summary Template v1.0` present                |
| C1.2 | error | Mermaid.js inlined (HTML ≥ 1 MB) · **auto-fix** removes duplicates  |
| C1.3 | error | Zero unresolved `{{X}}` placeholders · **auto-fix** sweeps          |
| C1.4 | info  | HTML size ≥ 200 KB (sanity)                                         |
| C1.5 | warn  | Main `<script>` parses cleanly (uses `node --check` when available) |

### C2 — Dashboard Data Population (9 rules)

| ID   | Level | Check                                                     |
| ---- | ----- | --------------------------------------------------------- |
| C2.1 | error | `D.kpis` ≥ 6 items                                        |
| C2.2 | error | `D.ccTop` populated when source available                 |
| C2.3 | error | `D.bizRules` populated when source available              |
| C2.4 | error | `D.funcReqs` populated when source available              |
| C2.5 | error | `D.testMap` or `D.testGaps` populated                     |
| C2.6 | error | `D.screenMermaid` populated when source has mermaid block |
| C2.7 | error | `D.screenForms` populated when source has form table      |
| C2.8 | warn  | `D.apiEndpoints` populated when openapi specs present     |
| C2.9 | error | `D.arts` contains `ava-asis-solution-delphi` artifacts    |

### C3 — Static Diagram Rendering (6 rules)

| ID   | Level | Check                                                              |
| ---- | ----- | ------------------------------------------------------------------ |
| C3.1 | error | `D.staticDiagrams` non-empty                                       |
| C3.2 | error | Every `.mmd` in `asis/diagrams/` represented in staticDiagrams     |
| C3.3 | error | Diagrams sanitized (no emoji / `→` / `—`) · **auto-fix** sanitizes |
| C3.4 | error | `renderMermaidSafely()` function defined                           |
| C3.5 | error | `renderStaticDiagrams()` called in `init()`                        |
| C3.6 | warn  | Obsolete `_patchNegRects` polling removed · **auto-fix** strips    |

### C4 — Sidebar Structure (5 rules)

| ID   | Level | Check                                                       |
| ---- | ----- | ----------------------------------------------------------- |
| C4.1 | error | 6 phase groups with `data-phase-id`                         |
| C4.2 | error | Removed nav items: Diagramas C4 / Overall / BPMN / Sequence |
| C4.3 | error | Removed nav item `s-f2-code` (Código Gerado)                |
| C4.4 | warn  | Topbar Artefatos item removed                               |
| C4.5 | error | `PHASE_FOLDER_MAP.f3f4 === 'prototype'`                     |

### C5 — Deliverables Submenu (7 rules)

| ID   | Level | Check                                                    |
| ---- | ----- | -------------------------------------------------------- |
| C5.1 | error | `DELIV_CATEGORIES` has 8 semantic categories             |
| C5.2 | error | Each category has `pt` + `en` labels                     |
| C5.3 | error | `classifyDeliverable` + `build` + `init` functions exist |
| C5.4 | error | `setLang()` re-renders the submenu                       |
| C5.5 | error | `initDeliverableSubmenus` is idempotent                  |
| C5.6 | info  | `DelivState.expanded` tracked                            |
| C5.7 | warn  | Categories collapsible via `.dv-cat-body.open`           |

### C6 — File Tree Coverage (6 rules)

| ID   | Level | Check                                                   |
| ---- | ----- | ------------------------------------------------------- |
| C6.1 | error | `fileTree` has `asis` key                               |
| C6.2 | error | `asis.files` non-empty when folder exists               |
| C6.3 | error | `prototype` key populated when `tobe/prototype/` exists |
| C6.4 | error | No `.cs`/`.ts`/`.tsx`/`.jsx` files in fileTree          |
| C6.5 | warn  | No `/tests/` or `/config/` paths in fileTree            |
| C6.6 | error | `summary/` has no `.html` files (no self-reference)     |

### C7 — Phase Tracking (4 rules)

| ID   | Level | Check                                                                                                                     |
| ---- | ----- | ------------------------------------------------------------------------------------------------------------------------- |
| C7.1 | error | `D.agentStatus` is a non-empty dict                                                                                       |
| C7.2 | error | Every ✅ phase in shared-context has a matching done agent                                                                |
| C7.3 | warn  | At least 8 agents done (F1 baseline)                                                                                      |
| C7.4 | warn  | `ava-coder-dotnet` IS referenced (valid during code-generation phase; suppress if `D.agentStatus` shows Stack phase done) |

### C8 — Language Consistency (3 rules)

| ID   | Level | Check                                                   |
| ---- | ----- | ------------------------------------------------------- |
| C8.1 | warn  | If `language:en`, no PT content drift in embedded files |
| C8.2 | error | `project-config.yaml` exists (dual-file invariant)      |
| C8.3 | error | i18n dict has `nav-deliverables` + `dv-empty` (pt+en)   |

### C9 — HTML Deliverable Viewer (3 rules)

| ID   | Level | Check                                                |
| ---- | ----- | ---------------------------------------------------- |
| C9.1 | error | `renderDeliverableContent` has html branch           |
| C9.2 | error | `iframe` uses `srcdoc` + `sandbox`                   |
| C9.3 | error | `.mmd` branch uses `textContent` (preserves `<br/>`) |

### C12 — Artifact Integrity (new, 1 rule)

| ID  | Level | Check                                                                                                        |
| --- | ----- | ------------------------------------------------------------------------------------------------------------ |
| C12 | error | Zero unresolved `[INCOMPLETE]`, `[ARTIFACT-MISSING]` placeholders; zero .mmd tables with 0 data rows renamed |

### C13 — Screen Flow Completeness (planned, extensible to 3 rules)

| ID    | Level | Check                                                                         |
| ----- | ----- | ----------------------------------------------------------------------------- |
| C13.1 | error | `screen-flow-completeness.json` exists when `form-registry.available` is true |
| C13.2 | error | `coverage_pct >= 80`                                                          |
| C13.3 | warn  | `retry_count <= 2` (3rd retry requires human review)                          |

> Not yet implemented in `validate_summary.py`; tracked as known debt.

### Severity semantics

- **`error`** — regression of a historical fix → blocks promotion, exit 1.
- **`warn`** — drift or optional-data signal → does not block.
- **`info`** — observational metric → never blocks.

---

## 5. Auto-fix (closed-loop remediation)

The validator can repair a subset of regressions automatically. Fixes are
**deterministic, idempotent, and scoped to the HTML file only** — they never
touch source `.md`/`.json` files, the template, or the builder.

### Fixable today

| Rule                                | What the fix does                                                              | Why it's safe                                                            |
| ----------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| **C1.2** Duplicate Mermaid          | Strip the second `<script>` block containing the Mermaid bundle                | Only runs when > 1 `__esbuild_esm_mermaid` marker found; keeps the first |
| **C1.3** Placeholder leftovers      | Replace `{{X_JSON}}` with `{}`, other `{{X}}` with `""`                        | Same sweep the builder does; pure string substitution                    |
| **C3.3** Diagram sanitization       | Remove emojis, replace `→` → `to`, `—` → `-` inside the `staticDiagrams` block | Scoped to the block; mirrors build-side `_sanitize_mermaid()`            |
| **C3.6** Dead code `_patchNegRects` | Remove the function definition + its `setTimeout` calls                        | No runtime dependency                                                    |

### Not fixable (require builder rerun or source edit)

- **C2.x** — Missing KPIs/CC/rules/reqs/tests → the validator cannot invent data.
  Fix is in `build_summary_complete.py` or the source files under `asis/`/`tobe/`.
- **C6.1–C6.3** — Missing fileTree keys → scanner didn't run or source folder
  is empty.
- **C7.x** — Missing agent entries in `ARTIFACT_MAP` → update `build_summary_complete.py`.
- **C8.2** — Missing `project-config.yaml` → copy from `agent-task-config.yaml`.

### Fix loop

```
pass = 0
while pass < max_fix_passes and errors_remain:
    for rule in failed_checks:
        if rule.fix is registered:
            html = rule.fix(ctx)
            persist(html)
    re-run all checks
    pass += 1
```

`max_fix_passes = 2` handles interdependent fixes (e.g., a fix that exposes
another check it unblocked).

### Audit trail

Every applied fix is recorded in both output files:

```markdown
## 🔧 Auto-fixes applied (2)

- **C1.3** auto-repaired in-place. Also update the builder so this doesn't regress again next run.
- **C3.3** auto-repaired in-place. Also update the builder so this doesn't regress again next run.
```

```json
{
  "applied_fixes": ["C1.3", "C3.3"],
  ...
}
```

Every notice includes the reminder: **auto-fix is a safety net, not a
substitute for fixing the root cause in the builder**.

---

## 6. Usage

### 6.1 Automatic (default path)

The builder invokes the validator at the end of `build_summary_html()`:

```python
# build_summary_complete.py (final step)
from validate_summary import run_all as _run_validate
rc = _run_validate(project_name, auto_fix=True)
if rc != 0:
    sys.exit(rc)
```

Just run the usual build and the validator runs automatically:

```bash
PYTHONIOENCODING=utf-8 python src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py --project Meu-ERP
```

Expected tail:

```
✅ SUCESSO!
[Validation] Executando non-regression gate (auto-fix habilitado)…
   📋 Validation: 48 passed · 0 warnings · 0 errors
   ✅ All error-level checks passed
```

### 6.2 CLI standalone

Re-run validation without rebuilding the HTML:

```bash
# Full gate with auto-fix (default)
python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project Meu-ERP --fix

# Validate only (report without mutating)
python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project Meu-ERP --no-fix
```

### 6.3 Programmatic

```python
from validate_summary import run_all

rc = run_all("Meu-ERP", auto_fix=True, max_fix_passes=2)
# rc == 0 → HTML is promotable
# rc == 1 → errors remain after fix attempts; check validation-report.md
```

---

## 7. Reading the report

Example `validation-report.md`:

```markdown
# Summary Validation Report — Meu-ERP · 2026-04-17 07:20 ...

- **HTML**: `AVA-FABRIC-SUMMARY-Meu-ERP-2026-04-17.html`
- **Size**: 3,767,449 bytes

| Level       | Count |
| ----------- | ----- |
| ✅ Passed   | 48    |
| ⚠️ Warnings | 0     |
| ❌ Errors   | 0     |

## Full check list

### Template Integrity (5/5)

- ✅ C1.1 — Signature 'AVA Fabric Summary Template v1.0' present — `signature occurrences: 2`
- ✅ C1.2 — Mermaid.js inlined (HTML ≥ 1 MB) — `html=3,767,449 bytes, mermaid markers present`
- ✅ C1.3 — Zero unresolved {{X}} placeholders — `zero unresolved placeholders`
  ...
```

When a check fails:

```markdown
## ❌ Errors (must fix before promoting)

### C1.3 — Zero unresolved {{X}} placeholders

- **Category**: Template Integrity
- **Detail**: unresolved: {{FAKE_PLACEHOLDER}}
- **Remediation**: Run the final regex sweep in build_summary_complete.py.
```

Every failure carries both the _observed_ state (`Detail`) and the _fix_
(`Remediation`), pointing to the exact function/file to edit.

---

## 8. Regression test (self-check)

The validator is itself regression-tested. Inject a deliberate break, confirm
detection, confirm auto-fix:

```bash
python -c "
h = open('projects/Meu-ERP/outputs/summary/AVA-FABRIC-SUMMARY-Meu-ERP-2026-04-17.html',encoding='utf-8').read()
h = h.replace('</body>', '<!-- {{FAKE_PLACEHOLDER}} --></body>', 1)
open('projects/Meu-ERP/outputs/summary/AVA-FABRIC-SUMMARY-Meu-ERP-2026-04-17.html','w',encoding='utf-8').write(h)
"

python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project Meu-ERP --no-fix
# → 47 passed · 0 warnings · 1 errors (exit 1)

python src/modules/ava-fabric-agents/summary/utils/validate_summary.py --project Meu-ERP --fix
# → 🔧 Auto-fix pass — applied: C1.3
# → 48 passed · 0 warnings · 0 errors (auto-fixed: 1)
# → ✅ All error-level checks passed (exit 0)
```

---

## 9. Adding a new rule

Every new historical fix should land here as a new rule. Steps:

### 9.1 Write the check function

In `validate_summary.py`, add:

```python
def _cN_M(ctx: Ctx) -> Result:
    found = "my-invariant-marker" in ctx.html
    return Result(found, "present" if found else "NOT found — regression of fix XXX")
```

### 9.2 Add to the catalog

Append to `CHECKS`:

```python
Check("C4.6", "Sidebar", "error",
      "New invariant description",
      "Explain what to edit in build_summary_complete.py or the template.",
      _c4_6),
```

Choose level carefully:

- `error` — blocks promotion (regression of a shipped fix).
- `warn` — drift signal that's acceptable in a partial build.
- `info` — observational only.

### 9.3 Optionally register a fix

If the regression is HTML-string-level and safe:

```python
def _fix_c4_6(ctx: Ctx) -> Optional[str]:
    if "broken-pattern" not in ctx.html:
        return None
    return ctx.html.replace("broken-pattern", "correct-pattern")

Check("C4.6", ..., _c4_6, fix=_fix_c4_6),
```

Fixes **must** be:

- Deterministic (same input → same output).
- Idempotent (running twice is a no-op).
- Bounded (only modify the intended region, not the whole file).
- HTML-only (never touch source files, template, or builder).

### 9.4 Update docs

- Add the new rule to the table in this file (section 4).
- Add it to the rule table in [`summary-validate-agent.md`](../src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md).
- Increment the rule count (`48 rules` → `49 rules`).

### 9.5 Test

Inject a deliberate violation, verify detection:

```bash
# Break it
sed -i 's/correct-pattern/broken-pattern/' projects/.../summary/AVA-FABRIC-SUMMARY-*.html
python validate_summary.py --project Meu-ERP --no-fix
# Should report the new rule as error.

# Auto-fix (if registered)
python validate_summary.py --project Meu-ERP --fix
# Should report applied_fixes: ["C4.6"].
```

---

## 10. Troubleshooting

| Symptom                                             | Likely cause                             | Remediation                                                                                                     |
| --------------------------------------------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `No AVA-FABRIC-SUMMARY-*.html in …/summary`         | Build didn't produce HTML                | Run `build_summary_complete.py` first                                                                           |
| Validator exits 1 with C2.x errors                  | Data missing from source files           | Re-run the missing agent (e.g., `/ava-asis-documentation` for C2.3/C2.4)                                        |
| Validator exits 1 with C6.1 error                   | Scanner skipped the asis folder          | Check `EXCLUDED_PATH_SEGMENTS` and `PHASE_SOURCES` in the builder                                               |
| Validator crashes with Python traceback             | Check function raised uncaught exception | Each check is wrapped in try/except that reports `validator crashed: …` — open an issue with the full traceback |
| Auto-fix reports success but check still fails      | Fix applied but didn't fully remediate   | Likely interdependent issue; second pass should handle it. If not, the fix needs refinement                     |
| `ModuleNotFoundError: yaml`                         | Missing dependency                       | `pip install pyyaml`                                                                                            |
| `node not installed — skipping parse check` on C1.5 | Node.js not in PATH                      | Install Node for stricter JS validation, or accept the warn                                                     |

---

## 11. Design principles

1. **Derived from real pain** — every rule traces to a historical bug that cost
   real debugging time.
2. **Generic across projects** — no rule hardcodes project-specific expectations.
   Optional phases become `warn`, not `error`.
3. **Read-mostly** — the validator _observes_ by default; auto-fix is opt-in
   (and even then, surgical).
4. **Fast** — all 48 checks run in <2 seconds against a 3.7 MB HTML.
5. **No JS execution** — the validator parses the HTML/JS as strings. Safe to
   run on untrusted content.
6. **Actionable** — every failure names the file and function that owns the fix.
7. **CI-friendly** — exit code is the contract; JSON output is machine-parseable.

---

## 12. Related files

| Path                                                                         | Role                                                |
| ---------------------------------------------------------------------------- | --------------------------------------------------- |
| `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`            | Validator script (~800 lines, 48 rules, 4 fixes)    |
| `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`     | Agent persona & contract                            |
| `src/modules/ava-fabric-agents/summary/agents/summary-agent.md`              | References Validation Gate hook                     |
| `src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py`      | Calls the validator as the final step               |
| `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` | The artifact under validation                       |
| `CHANGELOG.md` (root)                                                        | History of the fixes that produced the rule catalog |

---

_Last updated: 2026-04-17 · Rules: 48 · Auto-fixes: 4_
