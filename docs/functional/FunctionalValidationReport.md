# Functional Validation Report — i18n Full Coverage

| Field               | Value                                        |
|---------------------|----------------------------------------------|
| Feature             | i18n Complete Bilingual Coverage (PT-BR / EN-US) |
| Trace ID            | `fa-i18n-2026-04-10-001`                     |
| Profile             | STANDARD                                     |
| Status              | **VALIDATED_WITH_RISKS**                     |
| Template            | `summary-template.html` (~2995 lines, ~175KB) |
| Agents impacted     | 41 (F1–F7) + summary aggregator (F8)         |

---

## 1. Requirement Summary

**R-01**: ALL user-visible text in the HTML summary report must respond to the sidebar language combobox — zero exceptions.

**R-02**: Translation must be "dynamic" — i18n keys are data-driven (embedded in the `D` object via `k:`, `dk:`, `nk:`, `ck:`, `rk:`, `sk:`, `gk:`, `ak:` properties), resolved at render time via `t()`. NOT a separate static translation file.

**R-03**: Language switch must complete in < 100ms. No external dependencies.

**R-04**: Preserve existing CSS class naming (`.lb`, `.ls`, `.ng`, `.ni`, `.kc`, etc.) and HTML structure.

**R-05**: Solution must align with the agent pipeline — step-03-build-html.md generates the final HTML.

---

## 2. Gap Analysis — Remaining Hardcoded Strings

### 2.1 HTML Static Text Missing `data-i18n`

| # | Location | Current text | Category |
|---|----------|-------------|----------|
| H-01 | `<title>` tag (line 5) | `AVA Fabric Summary — {{PROJECT_NAME}}` | Page title |
| H-02 | `<span class="ttag" id="tp-tech">` | `Delphi → .NET 10` | Topbar tech badge |
| H-03 | `<div class="ll" id="lbl-lang">` | `Idioma / Language` | Sidebar label (handled in JS but no `data-i18n`) |
| H-04 | `<div class="wm">` | `AVA Fabric · ava-summary · {{GENERATED_AT}} · trace: {{TRACE_ID}}` | Watermark |
| H-05 | `<button id="diag-modal-close" title="Fechar (ESC)">` | `Fechar (ESC)` | Modal close button title |
| H-06 | Security Compliance `<th>` row | `Controle`, `Status`, `Evidência` | 3 headers missing `data-i18n` |
| H-07 | IaC Resources `<th>` row | `Recurso`, `Provider`, `Ambiente`, `Tool` | 4 headers missing `data-i18n` |
| H-08 | CI Pipeline `<th>` row | `Stage`, `Tool`, `Quality Gate`, `Status` | 4 headers missing `data-i18n` |
| H-09 | CD Pipeline `<th>` row | `Ambiente`, `Estratégia`, `Aprovação`, `Rollback`, `Status` | 5 headers missing `data-i18n` |
| H-10 | Parity `<th>` row | `Divergências`, `Aprovação Wave` | 2 headers missing `data-i18n` |
| H-11 | BC TOBE `<th>` row | `ADR` header has no `data-i18n` | 1 header |
| H-12 | DB Schema `<th>` row | `PK`, `FK` without `data-i18n` | 2 headers (arguably OK as abbreviations) |

**Total static HTML gaps: 12 items (~25+ individual strings)**

### 2.2 CSS Pseudo-element with Hardcoded Text

| # | Rule | Content | Issue |
|---|------|---------|-------|
| C-01 | `.diag-wrap:hover::after` | `content:'🔍 clique para ampliar'` | CSS `content` cannot be changed by `data-i18n`. Needs JS/CSS-variable approach. |

### 2.3 JavaScript Render Functions with Hardcoded Strings

| # | Function | Hardcoded string | Fix |
|---|----------|-----------------|-----|
| J-01 | `renderKPIs()` | Uses `k.l` (PT label) instead of `t(k.k)` | Change to `k.k ? t(k.k) : k.l` |
| J-02 | `renderRisks()` | `D.risks.length + ' riscos'` | Replace with `t('lbl-risks-count')` or similar |
| J-03 | `renderOWASP()` | `D.owasp.length + ' findings'` | Replace with `t('lbl-findings')` |
| J-04 | `renderDBSchema()` | `D.sps.length + ' SPs'` | Replace with `t('lbl-sps-count')` |
| J-05 | `renderTestPlan()` | All columns: `t.t`, `t.tool`, `t.alvo`, `t.crit`, `t.cov` — hardcoded mixed PT/EN | Add i18n keys to test plan data |
| J-06 | `renderQAAgents()` | Uses `a.role` directly | Change to `a.rk ? t(a.rk) : a.role` (same pattern as `renderPhases()`) |
| J-07 | `init()` diagram fallback | `'(diagrama não disponível — execute o agente correspondente)'` | Replace with `t('lbl-no-diagram')` — key already exists! |
| J-08 | `_syncThemeBtn()` | `t==='dark'?'Claro':'Dark'` — mixed PT/EN | Use `t('theme-light')` / `t('theme-dark')` |
| J-09 | `setupDiagramZoom()` | `'Diagrama'` fallback title | Replace with `t('lbl-diagram')` |
| J-10 | `renderInvKpis()` | Inline data array with `l:` Portuguese labels | Uses `k:` keys correctly via `t()`, but the fallback labels are PT |

### 2.4 Critical Bug: `t()` Function Shadowed in 3 Render Functions

| # | Function | Shadow variable | Impact |
|---|----------|----------------|--------|
| BUG-01 | `renderTestPlan()` | `D.testPlan.map(t=> ...)` | `t` parameter shadows global `t()` translation helper. If you try to add `t('key')` calls inside this map, it will call the test-plan item as a function instead. |
| BUG-02 | `renderOWASP()` | `const t = document.getElementById('tag-owasp')` | Same shadow problem. |
| BUG-03 | `renderDBSchema()` | `const t = document.getElementById('tag-sps')` | Same shadow problem. |

**Impact**: These 3 functions CANNOT use `t()` for translation without first renaming the shadow variable. This is a prerequisite fix.

### 2.5 Render Functions Missing from `setLang()` Re-render

The following are called in `init()` but NOT in `setLang()`, meaning language switch does NOT update them:

| # | Function | Translatable content? |
|---|----------|-----------------------|
| M-01 | `renderPatterns()` | No i18n keys on pattern names (technical terms) — **low priority** |
| M-02 | `renderBC()` | No i18n keys — dynamic data from agents — **acceptable** |
| M-03 | `renderTOBEBC()` | Hardcoded `'Clean Arch + CQRS'` string — **low** |
| M-04 | `renderPackages()` | Package names are proper nouns — **acceptable** |
| M-05 | `renderTestPlan()` | **HIGH** — Has `alvo`, `crit` columns with translatable content |
| M-06 | `renderOWASP()` | Risk count suffix needs translation — **medium** |
| M-07 | `renderDBSchema()` | SP count suffix needs translation — **medium** |
| M-08 | `renderInvKpis()` | Uses `t()` via `k:` keys — **needs adding to setLang** |
| M-09 | `renderIaCResources()` | Resource names are proper nouns — **acceptable** |

### 2.6 D Object Data Arrays Without i18n Keys

| Data Array | Fields needing keys | Priority |
|------------|-------------------|----------|
| `D.testPlan[]` | `t` (type name), `alvo` (target), `crit` (criteria) | HIGH — user-visible table content |
| `D.ciStages[]` | `s` (stage name) | MEDIUM — some are English tech terms |
| `D.cdEnvs[]` | `strat` (strategy), `rollback` | LOW — mostly technical terms |
| `D.acceptChecklist[]` | Already has `k:` keys ✓ | — |
| `D.qgates[]` | Already has `k:` keys ✓ | — |
| `D.waves[]` | Already has `sk:` keys ✓ | — |

---

## 3. Functional Readiness Score

| Dimension | Score | Notes |
|-----------|-------|-------|
| Static HTML i18n coverage | 85% | 12 items missing data-i18n |
| Dynamic JS i18n coverage | 70% | 10 render functions with gaps |
| setLang() re-render completeness | 78% | 9 functions missing from re-render |
| I18N dictionary completeness | 92% | ~275 keys exist, ~30 more needed |
| Bug-free i18n infrastructure | 60% | 3 critical `t()` shadow bugs |
| **Overall functional_readiness_score** | **77/100** | |

---

## 4. Acceptance Criteria

- [x] AC-01: Language combobox exists in sidebar with PT-BR and EN-US options
- [ ] AC-02: ALL `<th>` table headers have `data-i18n` attributes
- [ ] AC-03: ALL sidebar nav items translatable (mostly done, missing `lbl-lang`)
- [ ] AC-04: ALL page titles `<h1>` have `data-i18n` (already done ✓)
- [ ] AC-05: ALL card titles `<h2>` have `data-i18n` (already done ✓)
- [ ] AC-06: ALL render functions use `t()` for user-visible labels
- [ ] AC-07: `setLang()` re-renders ALL dynamic sections
- [ ] AC-08: CSS pseudo-element text translates on language change
- [ ] AC-09: No `t()` function shadowing in any render function
- [ ] AC-10: Language switch completes in < 100ms
- [x] AC-11: File remains self-contained (no external deps except mermaid.js)
