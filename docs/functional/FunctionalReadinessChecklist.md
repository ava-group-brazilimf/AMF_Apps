# Functional Readiness Checklist — i18n Full Coverage

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Language combobox in sidebar | ✅ Done | PT-BR / EN-US options |
| 2 | `data-i18n` on all `<h1>` page titles | ✅ Done | ~25 pages covered |
| 3 | `data-i18n` on all `<h2>` card titles | ✅ Done | ~45 cards covered |
| 4 | `data-i18n` on all sidebar nav items | ✅ Done | ~35 nav items |
| 5 | `data-i18n` on all sidebar group labels | ✅ Done | F1–F7 groups |
| 6 | `data-i18n` on header elements (coverage, scope, status) | ✅ Done | 4 elements |
| 7 | `data-i18n` on run box labels | ✅ Done | 3 labels |
| 8 | `data-i18n` on all `<th>` table headers | ⚠️ Partial | ~18 headers missing across 5 tables |
| 9 | `t()` helper function exists | ✅ Done | `var t = function(k){...}` |
| 10 | `I18N` object with pt/en dictionaries | ✅ Done | ~275 keys each |
| 11 | `setLang()` updates `data-i18n` elements | ✅ Done | querySelectorAll loop |
| 12 | `setLang()` updates `data-i18n-title` | ✅ Done | title attributes |
| 13 | `setLang()` updates `data-i18n-placeholder` | ✅ Done | input placeholders |
| 14 | `setLang()` re-renders ALL dynamic sections | ❌ Missing | 9 render functions not called |
| 15 | `renderKPIs()` uses `t(k.k)` | ❌ Missing | Uses hardcoded `k.l` instead |
| 16 | `renderQAAgents()` uses `t(a.rk)` | ❌ Missing | Uses hardcoded `a.role` |
| 17 | No `t()` function shadowing | ❌ Bug | 3 functions shadow `t` |
| 18 | CSS pseudo-element text translatable | ❌ Missing | `.diag-wrap:hover::after` hardcoded |
| 19 | `<title>` tag updates on lang switch | ❌ Missing | Hardcoded PT |
| 20 | Theme toggle button labels translate | ❌ Missing | "Claro"/"Dark" hardcoded |
| 21 | Diagram fallback text uses `t()` | ❌ Missing | Hardcoded PT in `init()` |
| 22 | Risk/SP/findings count suffixes translated | ❌ Missing | Hardcoded in 3 functions |
| 23 | `D.testPlan` fields have i18n keys | ❌ Missing | No `k:` keys on test plan |
| 24 | `FE_LABELS_MAP` bilingual | ✅ Done | pt/en maps exist |
| 25 | Performance < 100ms on switch | ✅ Expected | Hash-map O(1) + DOM batch |

**Done: 15/25 (60%) · Partial: 1/25 (4%) · Missing: 9/25 (36%)**
