# Phase 0 Research — ava-prototype v1.1.0

## Unknowns Resolved

---

### R1 — Heurísticas de Nielsen-Norman aplicadas a protótipos HTML

**Decision**: Aplicar as 10 heurísticas de Nielsen (1994) como regras de geração no agente.  
**Rationale**: As heurísticas são tecnologia-agnósticas e amplamente aceitas — não há conflito com a stack. O agente as implementa como regras de instrução em PT-BR, garantindo que o HTML gerado as satisfaça por construção.  
**Implementation**: Cada heurística é mapeada para um padrão de código HTML/CSS/JS concreto (ex: H1 → breadcrumb + título de página; H4 → CSS custom properties do design-system.md).

---

### R2 — Validação de formulário client-side em HTML estático (sem framework)

**Decision**: Usar JavaScript vanilla com `constraint validation API` do HTML5, complementada por lógica de feedback visual inline.  
**Rationale**: O protótipo é autocontido (sem CDN, sem Angular/React). A Constraint Validation API (`checkValidity()`, `reportValidity()`, `setCustomValidity()`) está disponível em todos os browsers modernos sem dependências externas.  
**Pattern**:

```js
form.addEventListener("submit", (e) => {
  if (!form.checkValidity()) {
    e.preventDefault();
    showValidationErrors(form);
  }
});
function showValidationErrors(form) {
  form.querySelectorAll(":invalid").forEach((field) => {
    const msg = field.closest(".field-group")?.querySelector(".error-msg");
    if (msg) msg.textContent = field.validationMessage;
    field.setAttribute("aria-invalid", "true");
    field.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}
```

**Alternatives considered**: Usar Zod/Yup → descartado (requer bundler); usar atributos HTML5 `required`/`pattern` somente → insuficiente para mensagens customizadas em PT-BR.

---

### R3 — Artefato `functional-requirements.md` como input opcional

**Decision**: Adicionar `functional-requirements.md` como input de enriquecimento (não-bloqueante).  
**Rationale**: O agente AS-IS (`ava-asis-documentation`) produz `functional-requirements.md` com regras de negócio detalhadas. Consumir esse artefato permite que o protótipo espelhe fielmente as regras do sistema legado, não apenas os fluxos do TO-BE.  
**Resolution**: O Pre-Flight Check lista o artefato como opcional (✅ se presente, ⚠️ se ausente — não bloqueia). O agente extrai campos, labels e validações específicas do negócio (ex: "CNPJ deve ser válido", "Valor mínimo de pedido: R$ 10,00").

---

### R4 — Mensagens de erro do sistema: padrão de UX

**Decision**: Implementar padrão de erro em 3 camadas: (a) modal overlay, (b) toast/snackbar, (c) inline banner.  
**Rationale**: Cada camada serve um propósito distinto segundo as heurísticas H9 e H3:

- **Modal**: erros que bloqueiam o fluxo (ex: sessão expirada, falha crítica de API)
- **Toast**: erros não-críticos que não interrompem o fluxo (ex: timeout de busca)
- **Inline banner**: avisos de degradação (ex: "Dados parcialmente carregados")  
  **Alternatives considered**: Apenas toast → insuficiente para erros bloqueantes; apenas modal → invasivo para erros menores.

---

### R5 — Impacto de segurança (Article VII)

**Decision**: Não há impacto novo no sub-pipeline de segurança.  
**Rationale**: O `ava-prototype` é um agente F3 (Prototype). Não gera código de produção, não faz chamadas HTTP reais, não persiste dados. A revisão adiciona apenas lógica de instrução para geração de HTML estático mock. Nenhum novo vetor de segurança é introduzido.  
O agente continua sem bypass do `ava-asis-security-orchestrator`.

---

### R6 — Acessibilidade: nível mínimo para protótipo

**Decision**: Implementar WCAG 2.1 nível AA para atributos semânticos e contraste. Não implementar WCAG AA para navegação por teclado completa.  
**Rationale**: O protótipo serve para demonstração com stakeholders (não é o produto final). O nível AA para atributos (`aria-*`, `role`, `label`) é suficiente para demonstrar que o design contempla acessibilidade. Navegação por teclado 100% completa é responsabilidade do frontend real.

---

### R7 — Versioning: MINOR ou PATCH?

**Decision**: **MINOR bump — 1.0.0 → 1.1.0**  
**Rationale**: Novos comportamentos são adicionados (UX heuristics, form validation, error messages, novo input `functional-requirements.md`), mas o Output Contract não muda (mesmos 4 outputs: index.html, demo-script.md, figma-spec.md, screen-list.md). Segundo Constitution Article X: adicionar campos/comportamentos opcionais = MINOR.

---

### R8 — Consistência com `design-system.md` em projetos sem design system definido

**Decision**: Se `design-system.md` não existir, o agente usa um design system mínimo padrão baseado em CSS custom properties.  
**Rationale**: O pré-voo atual já faz fallback quando `design-system.md` ausente → O agente deve derivar um design system mínimo a partir do `bounded-context-map.md` + `user-journeys.md`, documentando no `screen-list.md` que o design system foi auto-gerado com `design_source: "auto-generated"`.

# Research: ava-stack-vue-frontend

**Feature**: `009-vue-frontend-agent`
**Phase**: 0 — Outline & Research
**Date**: 2026-07-13

---

## §1 — Composition API + `<script setup>` vs Options API

**Decision**: Composition API with `<script setup>` Single-File Component syntax — **Options API PROHIBITED**.

**Rationale**: Vue 3's recommended approach for all new projects. `<script setup>` is compile-time
syntactic sugar that reduces boilerplate, improves TypeScript inference, and is the de-facto standard
in the Vue 3 ecosystem. The Options API is still supported but discouraged for new builds; mixing APIs
within the same codebase creates cognitive load and inconsistency. The Angular agent uses strict
patterns (Standalone Components) for the same reason — consistency prevents drift.

**Alternatives considered**:

- Options API — rejected: deprecated pattern for new code; poor TypeScript inference
- Class-based components (vue-class-component) — rejected: abandoned, no Vue 3 support

---

## §2 — State Management: Pinia vs Vuex

**Decision**: Pinia (officially recommended by Vue team, replaces Vuex).

**Rationale**: Vuex 4 is in maintenance mode; Pinia is the official successor, designed for Vue 3 and
TypeScript. Pinia stores are simpler (no mutations layer), fully TypeScript-typed, and support
Composition API syntax natively. Each bounded context gets its own Pinia store module:
`src/stores/{bc-kebab}.store.ts`.

**Alternatives considered**:

- Vuex 4 — rejected: maintenance mode, no Vuex 5 planned; Pinia is the official replacement
- Zustand / Jotai — rejected: React ecosystem only
- XState — rejected: adds state-machine overhead not required for CRUD-heavy ERP migration targets

---

## §3 — Routing: Vue Router 4 + Lazy Loading

**Decision**: Vue Router 4 with `defineAsyncComponent` / `() => import()` lazy-loaded routes per BC.

**Rationale**: Vue Router 4 is the standard for Vue 3; it integrates with Vite's code-splitting by
returning a dynamic import in the route definition. Each BC gets its own route block:

```ts
{ path: '/{bc-kebab}', component: () => import('./views/{bc-kebab}/{BCName}View.vue') }
```

No sub-router-per-BC needed (keeps routing config flat). Navigation guards are registered globally.

**Alternatives considered**:

- Nuxt 3 file-based routing — rejected: adds framework overhead, conflicts with existing build pipeline
- Manual lazy loading with Suspense — rejected: Vue Router 4 handles this natively

---

## §4 — Authentication: MSAL (Azure AD) + Auth0 fallback

**Decision**: When `auth.provider == "azure-ad"` → `@azure/msal-browser` + `@azure/msal-vue`.
When other → Auth0 Vue SDK (`@auth0/auth0-vue`) or generic OIDC via `vue-auth-oidc`.

**Rationale**: The Angular agent mirrors this approach. `@azure/msal-vue` wraps `@azure/msal-browser`
with Vue plugin and composable (`useMsal()`) — same pattern as Angular's `MsalModule`.
Secrets are NEVER hardcoded: Client ID, Tenant ID, and Scopes are injected via `import.meta.env.VITE_*`
variables (Vite convention for env exposure).

**MSAL Vue integration pattern**:

```ts
// main.ts
import { createApp } from "vue";
import { msalPlugin } from "@azure/msal-vue";
import { PublicClientApplication } from "@azure/msal-browser";

const msalInstance = new PublicClientApplication({
  auth: {
    clientId: import.meta.env.VITE_MSAL_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_MSAL_TENANT_ID}`,
    redirectUri: import.meta.env.VITE_MSAL_REDIRECT_URI,
  },
});

createApp(App)
  .use(router)
  .use(pinia)
  .use(msalPlugin, msalInstance)
  .mount("#app");
```

**Alternatives considered**:

- vue-oauth2-oidc — rejected: smaller community, less MSAL compatibility
- NextAuth — rejected: Next.js only

---

## §5 — Bundler: Vite

**Decision**: Vite 5 (SPA default) — consistent with React and Angular build targets.

**Rationale**: Angular uses Angular CLI (Webpack-based), React uses Vite 5 (per 008 research).
Vue 3's official scaffolding (`create-vue`) uses Vite. Provides fast HMR, native ESM, and
TypeScript strict mode without extra config. Output is a static SPA deployable to Azure Static
Web Apps or Nginx in a container.

**Required `vite.config.ts` plugin**: `@vitejs/plugin-vue` — transforms `.vue` SFC files.

**Alternatives considered**:

- Nuxt 3 (built-in Vite) — rejected: SSR overhead not needed for SPA migration targets
- Webpack — rejected: slower builds, higher config complexity vs Vite

---

## §6 — Testing: Vitest + Vue Test Utils

**Decision**: Vitest (Vite-native test runner) + Vue Test Utils v2 for unit/integration tests.
Coverage target ≥ 80% for stores, composables, and utility functions.

**Rationale**: Vitest shares Vite config (no duplicate transform pipeline), is faster than Jest
for Vite projects, and the API is Jest-compatible (trivial migration). Vue Test Utils v2 is the
official Vue 3 testing utility. Pattern mirrors React agent (Vitest + React Testing Library).

**Test patterns per BC**:

- `{bc-kebab}.store.spec.ts` — Pinia store tests (using `setActivePinia(createPinia())`)
- `{BCName}View.spec.ts` — Component mount tests (shallow render + interaction)

**Alternatives considered**:

- Jest — rejected: requires additional transform config for Vite (slower CI)
- Playwright CT — rejected: E2E overhead for unit scope; Playwright is used separately for E2E

---

## §7 — TypeScript: Strict Mode + Volar

**Decision**: `tsconfig.json` with `"strict": true` and `"skipLibCheck": true`.

**Rationale**: Consistent with Angular (strict mode required) and React (same in 008).
`skipLibCheck: true` prevents false positives from `.d.ts` files in Vue ecosystem packages
(same reason as Angular agent — NgRx / MSAL types).

**Key compiler options**:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "skipLibCheck": true,
    "jsx": "preserve",
    "lib": ["ES2020", "DOM", "DOM.Iterable"]
  }
}
```

**Alternatives considered**:

- Loose TypeScript — rejected: Constitution Article IX mandates strict mode for generated code

---

## §8 — Routing Guard: build-cycle WARN+fallback vs HARD STOP

**Decision**: `pipeline_mode == "build-cycle"` → emit `⚠️ WARN` and continue in generic mode
(do NOT HARD STOP). Set `build_cycle_fallback: true` in handoff.

**Rationale**: Unlike the Angular agent (which hard-stops on build-cycle because
`ava-build-cycle-angular` exists as a dedicated agent), no `ava-build-cycle-vue` agent exists.
A hard stop would orphan the pipeline with no recovery path. The WARN+fallback approach:

1. Keeps the pipeline running
2. Signals to the orchestrator that build-cycle Vue is not available
3. Allows the SME to decide whether to proceed with generic output or switch frameworks

This matches the spec's Scenario 2 requirement explicitly.

**Alternatives considered**:

- HARD STOP like Angular agent — rejected: creates a pipeline dead-end with no workaround
- Silent fallback (no warning) — rejected: operator must be informed of degraded behaviour

---

## §9 — XSS Mitigation for `v-html`

**Decision**: DOMPurify sanitization mandatory before any `v-html` binding.

**Rationale**: Per `frontend-governance.md §XSS`, `v-html` is the Vue equivalent of React's
`dangerouslySetInnerHTML`. The governance file specifies: "instalar `dompurify` + sanitizar
ANTES de passar ao binding". No raw API data may flow directly into `v-html`.

```ts
import DOMPurify from "dompurify";
const safeHtml = computed(() => DOMPurify.sanitize(props.rawHtml));
// <div v-html="safeHtml" />
```

**Alternatives considered**:

- vue-dompurify-html directive — acceptable, wraps DOMPurify; either approach is valid

---

## §10 — UI Library: Runtime Resolution

**Decision**: UI library resolved from `tobe_stack.ui_library` in `project-config.yaml` at runtime.
Agent supports Vuetify 3, PrimeVue 4, and Naive UI. Default (absent) → no UI framework, basic
Vite CSS. Constitution Article I forbids hardcoding.

**Resolution table** (agent reads this at Step 1 via ConfigStackDotNet.yaml):

| `tobe_stack.ui_library` value | Package                      | Import pattern                |
| ----------------------------- | ---------------------------- | ----------------------------- |
| `"vuetify"`                   | `vuetify@^3` + `@mdi/font`   | `app.use(vuetify)`            |
| `"primevue"`                  | `primevue@^4` + `primeicons` | `app.use(PrimeVue)`           |
| `"naive-ui"`                  | `naive-ui`                   | Tree-shakeable direct imports |
| absent / other                | (none)                       | Plain CSS modules             |

---

## §11 — Security Compliance Review Gate

**Decision**: Follow identical procedure to `coder-angular-frontend.md` Security Compliance
Review Gate — read `security-architecture.md`, classify controls V-01..V-13, write
`SecurityComplianceReport-Frontend.md`.

**Differences from Angular**:

- Framework substitutions: `DomSanitizer` → `DOMPurify`, `[innerHTML]` → `v-html`
- No NgRx interceptor concept → Axios interceptor or Fetch wrapper
- `environment.ts` → `import.meta.env.VITE_*`

**Output path** (same as Angular):
`projects/{project_name}/outputs/tobe/docs/security/SecurityComplianceReport-Frontend.md`

---

## §12 — `implementation-status.json` Schema Reuse

**Decision**: Reuse the schema introduced in `008-react-frontend-build-cycle` with
`agent: "ava-stack-vue-frontend"`. No schema changes required; the schema is
framework-agnostic (`agent` field is a free string).

**Output path** (same as Angular and React):
`projects/{project_name}/outputs/tobe/source-code/frontend/implementation-status.json`

**Resolved from**: [contracts/implementation-status-contract.md](contracts/implementation-status-contract.md)

---

## Summary of Resolved Unknowns

| Unknown                    | Decision                                  | Source                                  |
| -------------------------- | ----------------------------------------- | --------------------------------------- |
| Composition API syntax     | `<script setup>` — Options API PROHIBITED | Vue 3 official docs + Angular precedent |
| State management           | Pinia (official Vuex replacement)         | Vue team recommendation                 |
| Routing                    | Vue Router 4 + lazy `() => import()`      | Standard Vue 3 routing                  |
| Auth (azure-ad)            | `@azure/msal-browser` + `@azure/msal-vue` | MSAL Vue official plugin                |
| Bundler                    | Vite 5 + `@vitejs/plugin-vue`             | create-vue default                      |
| Testing                    | Vitest + Vue Test Utils v2 ≥ 80%          | Vite ecosystem standard                 |
| TypeScript                 | strict + skipLibCheck                     | Same as Angular/React agents            |
| build-cycle guard          | WARN + fallback (no HARD STOP)            | No `ava-build-cycle-vue` agent exists   |
| XSS mitigation             | DOMPurify before `v-html`                 | `frontend-governance.md`                |
| UI library                 | Runtime from `tobe_stack.ui_library`      | Constitution Article I                  |
| Security gate              | Identical to Angular agent                | `coder-angular-frontend.md` pattern     |
| implementation-status.json | Reuse 008 schema                          | Schema is framework-agnostic            |
