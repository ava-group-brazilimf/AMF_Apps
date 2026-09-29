# Data Model: Design Tokens Propagation

**Feature**: `008-design-tokens-propagation`
**Date**: 2026-07-08

---

## Core Artifact: `design-tokens.json`

Produced by `ava-prototype`. Consumed by `ava-stack-angular-frontend` and (future)
`ava-stack-react-frontend`.

### Fields

| Field path | Type | Required | Description |
|-----------|------|----------|-------------|
| `schema_version` | `string` | ✅ | Fixed `"1.0"` for this spec |
| `generated_by` | `string` | ✅ | Always `"ava-prototype"` |
| `project_name` | `string` | ✅ | Resolved from `project-config.yaml` |
| `spacing.base_unit` | `string` | ✅ | Root spacing unit (e.g. `"8px"`) |
| `spacing.xs` | `string` | ✅ | Extra-small step |
| `spacing.sm` | `string` | ✅ | Small step |
| `spacing.md` | `string` | ✅ | Medium step |
| `spacing.lg` | `string` | ✅ | Large step |
| `spacing.xl` | `string` | ✅ | Extra-large step |
| `spacing.xxl` | `string` | ✅ | Double extra-large step |
| `colors.primary` | `string` | ✅ | Primary brand color (hex or CSS value) |
| `colors.secondary` | `string` | ✅ | Secondary color |
| `colors.background` | `string` | ✅ | Page background color |
| `colors.surface` | `string` | ✅ | Card/panel surface color |
| `colors.on_primary` | `string` | ✅ | Text on primary (contrast) |
| `colors.error` | `string` | ✅ | Error state color |
| `colors.warning` | `string` | ✅ | Warning state color |
| `colors.success` | `string` | ✅ | Success state color |
| `typography.font_family_base` | `string` | ✅ | Body font stack |
| `typography.font_family_heading` | `string` | ✅ | Heading font stack |
| `typography.font_size_base` | `string` | ✅ | Default body font size |
| `typography.font_size_sm` | `string` | ✅ | Small text size |
| `typography.font_size_lg` | `string` | ✅ | Large text size |
| `typography.line_height_base` | `string` | ✅ | Default line-height ratio |
| `layout.sidebar_width` | `string` | ✅ | Full sidebar width (px or rem) |
| `layout.sidebar_collapsed_width` | `string` | ✅ | Collapsed sidebar width |
| `layout.header_height` | `string` | ✅ | Top header/toolbar height |
| `layout.content_padding` | `string` | ✅ | Main content area padding |
| `layout.max_content_width` | `string` | ✅ | Maximum content column width |

Optional per-token metadata (appended when source is not the prototype HTML):

| Field path | Type | When present |
|-----------|------|--------------|
| `*.source` | `string` | `"prototype-derived"` \| `"design-system-fallback"` \| `"default"` |

### Validation Rules

1. All required fields must be present and non-empty strings.
2. Dimension values (`spacing.*`, `layout.*`, `typography.font_size_*`) must end with a
   valid CSS unit: `px`, `rem`, `em`, `%`, or be a bare number string for unitless properties.
3. Color values (`colors.*`) must be valid CSS color strings (hex, rgb, hsl, or named colors).
4. `schema_version` must be exactly `"1.0"` (warn, do not block, on mismatch).

---

## Angular Input Contract Extension

Two new mandatory fields added to `coder-angular-frontend.md` Input Contract:

| Field | Type | Validation |
|-------|------|-----------|
| `prototype_screens` | `file` | Path: `projects/{project_name}/outputs/tobe/prototype/screen-list.md`. HARD STOP if absent. |
| `design_tokens` | `file` | Path: `projects/{project_name}/outputs/tobe/prototype/design-tokens.json`. HARD STOP if absent. |

---

## CSS Token Map (Angular output)

The G-DT guardrail produces a `:root` block appended to `styles.scss`:

```scss
:root {
  /* === Layout tokens (from design-tokens.json) === */
  --sidebar-width:          {layout.sidebar_width};
  --sidebar-collapsed-width: {layout.sidebar_collapsed_width};
  --header-height:          {layout.header_height};
  --content-padding:        {layout.content_padding};
  --max-content-width:      {layout.max_content_width};

  /* === Spacing tokens === */
  --spacing-xs:  {spacing.xs};
  --spacing-sm:  {spacing.sm};
  --spacing-md:  {spacing.md};
  --spacing-lg:  {spacing.lg};
  --spacing-xl:  {spacing.xl};
  --spacing-xxl: {spacing.xxl};

  /* === Color tokens === */
  --color-primary:    {colors.primary};
  --color-secondary:  {colors.secondary};
  --color-background: {colors.background};
  --color-surface:    {colors.surface};
  --color-on-primary: {colors.on_primary};
  --color-error:      {colors.error};
  --color-warning:    {colors.warning};
  --color-success:    {colors.success};

  /* === Typography tokens === */
  --font-family-base:    {typography.font_family_base};
  --font-family-heading: {typography.font_family_heading};
  --font-size-base:      {typography.font_size_base};
  --font-size-sm:        {typography.font_size_sm};
  --font-size-lg:        {typography.font_size_lg};
  --line-height-base:    {typography.line_height_base};
}
```

### State Transitions

```
prototype execution (ava-prototype)
  → design-system.md read ✅
  → wireframes generated
  → design-tokens.json written   [NEW STATE]

frontend codegen (ava-stack-angular-frontend)
  → Pre-Flight Check
    → design-tokens.json PRESENT ✅ → G-DT guardrail executes
    → design-tokens.json ABSENT  ❌ → HARD STOP
  → G-DT: token map built
  → styles.scss written with :root block   [NEW OUTPUT]
  → AppShell, Sidebar, Header generated with var() references
```
