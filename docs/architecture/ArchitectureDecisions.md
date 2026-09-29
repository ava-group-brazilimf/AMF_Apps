# Architecture Decision Records — i18n Full Coverage

## ADR-i18n-001: Key-Based Dictionary with Build-Time Generation

**Status**: Proposed  
**Date**: 2026-04-10  
**Context**: The AVA Fabric summary report is a self-contained HTML file (~175KB) requiring bilingual support (PT-BR/EN-US). The user requires "dynamic translation" — NOT a separately maintained static dictionary file.

### Decision

Retain the current `I18N` object + `t()` helper architecture, but extend it with:

1. **Data-driven key resolution**: All translatable fields in the `D` object use `k:` pattern keys (already partially implemented). Render functions resolve via `t(item.k) || item.fallbackLabel`.

2. **Build-time i18n generation**: Step-03 populates the `I18N` object dynamically from agent outputs. Each agent's `summary-data` contribution includes localized labels. The summary aggregator merges them into `I18N.pt` and `I18N.en`.

3. **No runtime translation API**: The file must remain self-contained. All translations are baked in at generation time.

### Rationale

- **Performance**: Hash-map O(1) lookup. Language switch = DOM text updates + re-render of ~20 functions. Target < 100ms easily achievable.
- **Self-contained**: No external dependencies. No network calls.
- **Extensible**: Adding a new language = add `I18N.es = {...}` + `<option>` in selector.
- **"Dynamic" interpretation**: The dictionary is generated from the data, not maintained as a separate static file. Agent outputs drive the translations, making it data-driven and consistent.

### Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Runtime API translation (e.g., Azure Translator) | Violates self-contained constraint. Adds latency. |
| Separate `.json` translation files loaded via fetch | Violates self-contained HTML requirement. |
| Duplicate HTML sections (PT + EN hidden) | Doubles file size. Maintenance nightmare. |
| CSS `:lang()` pseudo-class approach | Only works for static text, not dynamic JS renders. |

### Consequences

- All 41+ agents must include bilingual labels in their summary-data output format.
- Step-03 must validate that every `k:` key in `D` exists in both `I18N.pt` and `I18N.en`.
- The I18N dictionary will grow proportionally with agent count (~30 new keys per agent).

---

## ADR-i18n-002: CSS Pseudo-Element Translation via CSS Custom Properties

**Status**: Proposed  
**Date**: 2026-04-10  
**Context**: `.diag-wrap:hover::after { content: '🔍 clique para ampliar' }` uses hardcoded Portuguese. CSS `content` property cannot be updated via `data-i18n` or `textContent`.

### Decision

Use a CSS custom property set on `<html>` by `setLang()`:

```css
:root { --txt-zoom-hint: '🔍 clique para ampliar'; }
html[lang="en-US"] { --txt-zoom-hint: '🔍 click to zoom'; }
.diag-wrap:hover::after { content: var(--txt-zoom-hint); }
```

Or set `--txt-zoom-hint` dynamically in `setLang()`:
```js
document.documentElement.style.setProperty('--txt-zoom-hint', `'${t("lbl-zoom-hint")}'`);
```

### Rationale

- Zero JS runtime cost for CSS content strings.
- CSS custom properties are supported in all modern browsers.
- Scales to any future CSS `content` strings.

### Consequences

- Need to audit all CSS `content:` declarations for hardcoded text.
- Only 1 instance found currently (`.diag-wrap:hover::after`).

---

## ADR-i18n-003: Rename Shadowed `t` Variables to Prevent Translation Bugs

**Status**: Proposed  
**Date**: 2026-04-10  
**Context**: Three render functions (`renderTestPlan`, `renderOWASP`, `renderDBSchema`) use local variables named `t` that shadow the global `t()` translation function. This is a latent bug that blocks i18n extension.

### Decision

Rename all shadowed variables:
- `renderTestPlan()`: `D.testPlan.map(t => ...)` → `D.testPlan.map(tp => ...)`  
- `renderOWASP()`: `const t = document.getElementById(...)` → `const el = document.getElementById(...)`  
- `renderDBSchema()`: `const t = document.getElementById(...)` → `const el = document.getElementById(...)`

### Rationale

This is a prerequisite for any i18n work in these functions. Without this fix, calling `t('key')` inside the map callback would throw or return unexpected results.

### Consequences

- Low risk change — purely internal variable rename.
- Must be done BEFORE adding `t()` calls to these functions.

---

## ADR-i18n-004: Step-03 i18n Validation Gate

**Status**: Proposed  
**Date**: 2026-04-10  
**Context**: The build pipeline (step-03-build-html.md) must ensure i18n completeness.

### Decision

Add a validation step to step-03:

1. After injecting data into the template, scan the `D` object for all properties matching `k:`, `dk:`, `nk:`, `ck:`, `rk:`, `sk:`, `gk:`, `ak:` patterns.
2. For each key found, verify it exists in both `I18N.pt` and `I18N.en`.
3. If any key is missing: log a warning and add a fallback entry using the raw key name.
4. Scan all `data-i18n` attributes in HTML and verify each key exists in both dictionaries.

### Rationale

Prevents runtime i18n gaps when new agents add data with new keys but forget to add translations.

### Consequences

- Adds ~5 seconds to generation time (DOM scan of ~3000 line file).
- Catches 100% of missing key issues before the report reaches the user.
