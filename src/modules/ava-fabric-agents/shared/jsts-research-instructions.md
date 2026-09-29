---
name: jsts-research-instructions
description: |
  Instruções de pesquisa JS/TS: fontes confiáveis, protocolo de resolução de versões,
  guardrails por versão de framework. Consumido por ava-stack-docs-researcher e
  ava-stack-build-fixer para qualquer frontend JS/TS (Angular, React, Vue, Svelte).
version: "1.0.0"
date: 2026-06-25
---

# JS/TS Research Instructions

> Recurso compartilhado consumido por `ava-stack-docs-researcher` e `ava-stack-build-fixer`.
> Cobre **todos os frameworks JS/TS** do frontend routing table: Angular, React, Vue, Svelte.

---

## §1 — Fontes Confiáveis (URLs permitidas para `fetch_webpage`)

### Registries & Tooling (todos os frameworks)

| Domínio | Propósito | URL Pattern |
|---------|----------|-------------|
| npm Registry API | Versões e metadata | `registry.npmjs.org/{package}` |
| npm Package Page | Página pública do pacote | `npmjs.com/package/{package}` |
| TypeScript | Docs, release notes, breaking changes | `typescriptlang.org/docs` |
| GitHub — TypeScript | Releases do compilador | `github.com/microsoft/TypeScript/releases` |
| Vite | Docs, config reference, migration guide | `vite.dev/guide`, `vite.dev/config` |
| GitHub — Vite | Releases e changelogs | `github.com/vitejs/vite/releases` |
| ESLint | Docs, flat config, rules reference | `eslint.org/docs` |
| GitHub — ESLint | Releases | `github.com/eslint/eslint/releases` |
| Vitest | Docs, config, migration | `vitest.dev/guide` |
| GitHub — Vitest | Releases | `github.com/vitest-dev/vitest/releases` |
| Playwright | Docs, API reference | `playwright.dev/docs` |
| GitHub — Playwright | Releases | `github.com/microsoft/playwright/releases` |

### Angular

| Domínio | Propósito | URL Pattern |
|---------|----------|-------------|
| Angular | Docs oficiais, migration guide | `angular.dev` |
| GitHub — Angular | Releases e changelogs | `github.com/angular/angular/releases` |
| Angular Material | Docs de componentes | `material.angular.io` |
| NgRx | Docs de state management | `ngrx.io/guide` |
| GitHub — NgRx | Releases | `github.com/ngrx/platform/releases` |

### React

| Domínio | Propósito | URL Pattern |
|---------|----------|-------------|
| React | Docs oficiais, hooks, API reference | `react.dev` |
| GitHub — React | Releases e changelogs | `github.com/facebook/react/releases` |
| React Router | Docs de routing | `reactrouter.com/docs` |
| GitHub — React Router | Releases | `github.com/remix-run/react-router/releases` |
| TanStack Query | Docs de data fetching | `tanstack.com/query/latest` |
| GitHub — Zustand | Releases de state management | `github.com/pmndrs/zustand/releases` |
| Mock Service Worker (msw) | Docs de mocking de API para Vitest/RTL | `mswjs.io/docs` |
| GitHub — msw | Releases | `github.com/mswjs/msw/releases` |

### Vue

| Domínio | Propósito | URL Pattern |
|---------|----------|-------------|
| Vue | Docs oficiais, Composition API | `vuejs.org/guide` |
| GitHub — Vue Core | Releases e changelogs | `github.com/vuejs/core/releases` |
| Vue Router | Docs de routing | `router.vuejs.org` |
| Pinia | Docs de state management | `pinia.vuejs.org` |
| GitHub — Pinia | Releases | `github.com/vuejs/pinia/releases` |
| VueUse | Composables utilitários | `vueuse.org` |

### Svelte

| Domínio | Propósito | URL Pattern |
|---------|----------|-------------|
| Svelte | Docs oficiais, runes, migration | `svelte.dev/docs` |
| GitHub — Svelte | Releases e changelogs | `github.com/sveltejs/svelte/releases` |
| SvelteKit | Docs de full-stack framework | `svelte.dev/docs/kit` |
| GitHub — SvelteKit | Releases | `github.com/sveltejs/kit/releases` |

### Auth (cross-framework)

| Domínio | Propósito | URL Pattern |
|---------|----------|-------------|
| MSAL JS | Docs da lib de auth Azure AD | `github.com/AzureAD/microsoft-authentication-library-for-js` |
| MSAL Browser | API reference | `github.com/AzureAD/microsoft-authentication-library-for-js/tree/dev/lib/msal-browser` |
| MSAL React | Wrapper React | `github.com/AzureAD/microsoft-authentication-library-for-js/tree/dev/lib/msal-react` |
| MSAL Angular | Wrapper Angular | `github.com/AzureAD/microsoft-authentication-library-for-js/tree/dev/lib/msal-angular` |

> ⛔ URLs fora desta lista NÃO são fontes confiáveis para resolução de versões e patterns.
> Blog posts, StackOverflow, Medium e tutoriais de terceiros NÃO devem ser usados como fonte de verdade.

---

## §2 — Protocolo de Resolução por Tipo de Dependência

| Tipo | Regra de Versão | Exemplo |
|------|----------------|---------|
| `@angular/*` | Alinhar com `frontend_version` | Angular 19 → `^19.x.x` |
| `@ngrx/*` | Mesma major version do Angular | Angular 19 → `^19.x.x` |
| `react`, `react-dom` | Alinhar com `frontend_version` | React 19 → `^19.x.x` |
| `vue` | Alinhar com `frontend_version` | Vue 3 → `^3.x.x` |
| `svelte` | Alinhar com `frontend_version` | Svelte 5 → `^5.x.x` |
| `typescript` | Latest stable compatível com o framework | Angular 19 → `~5.6.x` |
| `vite` | Latest stable (major alinhado com framework) | `^6.x` ou `^7.x` |
| `vitest` | Mesma major que Vite | Vite 7 → `^3.x` |
| `@azure/msal-browser` | Latest stable ≥ 3.x | `^3.x` |
| `@azure/msal-react` | Latest stable ≥ 2.x | `^2.x` |
| `@azure/msal-angular` | Latest stable ≥ 4.x | `^4.x` |
| Pacotes de terceiros | Latest stable compatível | Zustand, Pinia, DOMPurify, etc. |

### Resolução de Versão — Procedimento

```
PARA CADA pacote na lista:
  1. Executar: npm view {packageName} version
     → Extrair latest stable version
  2. SE comando falhar:
     → fetch_webpage: registry.npmjs.org/{packageName}
     → Extrair campo "dist-tags.latest" do JSON
  3. SE ambos falharem:
     → ⛔ BLOCKED: "Não foi possível resolver versão para {packageName}"
     → NÃO usar versão de training data como fallback

  4. Verificar compatibilidade com framework:
     → npm view {packageName} peerDependencies --json
     → SE peerDependencies inclui framework version incompatível → WARN
```

### Verificação de Compatibilidade por Framework

```
PARA CADA pacote resolvido:
  → Verificar engines.node em package.json (SE < Node 20 → WARN)
  → Verificar peerDependencies contra versão do framework alvo
  → Verificar se pacote suporta ESM (type: "module" ou exports field)
```

---

## §3 — Guardrails Específicos por Versão de Framework

### TypeScript (cross-framework)

| Versão | Guardrail | Referência |
|--------|-----------|-----------|
| TS 5.7+ | `--isolatedDeclarations` recomendado para DX | typescriptlang.org |
| TS 5.5+ | `--isolatedModules` obrigatório para Vite (esbuild/SWC) | vite.dev |
| TS 5.0+ | Stage 3 decorators (`experimentalDecorators` → `--experimentalDecorators` off) | Angular 17+ usa TC39 decorators |
| TS 5.0+ | `satisfies` operator preferido sobre `as` para type narrowing | typescriptlang.org |
| Todos | `strict: true` obrigatório em `tsconfig.json` | frontend-governance.md |
| Todos | `noImplicitAny: true` obrigatório | frontend-governance.md |
| Todos | `skipLibCheck: true` recomendado (previne erros em `node_modules`) | prática padrão |

### Vite (cross-framework)

| Versão | Guardrail | Referência |
|--------|-----------|-----------|
| Vite 7 (2026+) | Usa Rolldown como bundler (substitui Rollup) — breaking para plugins Rollup custom | vite.dev/guide |
| Vite 6+ | `import.meta.env` substitui `process.env` — variáveis DEVEM ter prefixo `VITE_` | vite.dev/guide |
| Vite 6+ | `vite.config.ts` usa `defineConfig` — NÃO usar export default literal | vite.dev/config |
| Vite 5+ | `optimizeDeps.include` pode ser necessário para pacotes CJS | vite.dev/guide |

### ESLint (cross-framework)

| Versão | Guardrail | Referência |
|--------|-----------|-----------|
| ESLint 9+ | Flat config OBRIGATÓRIO (`eslint.config.js`) — `.eslintrc.*` é legacy | eslint.org |
| ESLint 9+ | `defineConfig()` + `globalIgnores()` helpers recomendados | eslint.org |
| ESLint 9+ | `@typescript-eslint/eslint-plugin` → usar `typescript-eslint` (pacote unificado) | typescript-eslint.io |

### React

| Versão | Guardrail | Referência |
|--------|-----------|-----------|
| React 19 | `use client` / `use server` directives para RSC boundaries | react.dev |
| React 19 | `ref` como prop (não mais `forwardRef`) | react.dev |
| React 19 | `useActionState` substitui `useFormState` | react.dev |
| React 19 | `<form action={fn}>` pattern para mutations | react.dev |
| React 18+ | Strict Mode renderiza componentes 2x em dev | react.dev |
| React 18+ | `createRoot` obrigatório (não mais `ReactDOM.render`) | react.dev |
| React 18+ | Suspense + lazy obrigatório para code splitting | react.dev |

### Vue

| Versão | Guardrail | Referência |
|--------|-----------|-----------|
| Vue 3.5+ | `useTemplateRef()` substitui `ref` attribute para template refs | vuejs.org |
| Vue 3.4+ | `defineModel()` macro para v-model em components | vuejs.org |
| Vue 3.3+ | `defineSlots()` e `defineOptions()` macros novas | vuejs.org |
| Vue 3+ | Composition API (`<script setup>`) obrigatório — Options API é legacy | vuejs.org |
| Vue 3+ | `createApp()` obrigatório (não mais `new Vue()`) | vuejs.org |
| Vue 3+ | Teleport, Suspense, Fragments nativos | vuejs.org |

### Svelte

| Versão | Guardrail | Referência |
|--------|-----------|-----------|
| Svelte 5 | Runes obrigatórias: `$state`, `$derived`, `$effect` substituem stores reativos | svelte.dev |
| Svelte 5 | `$props()` substitui `export let` para declarar props | svelte.dev |
| Svelte 5 | Snippets (`{#snippet}`) substituem slots | svelte.dev |
| Svelte 5 | `$bindable()` para props com two-way binding | svelte.dev |
| Svelte 5 | Event handlers: `onclick` (lowercase, não `on:click`) | svelte.dev |
| Svelte 4→5 | Migration automática via `npx sv migrate svelte-5` | svelte.dev |

---

## §4 — Referência Cruzada com Políticas Existentes

| Política | Referência | Propósito |
|----------|-----------|-----------|
| Frontend Governance | `@frontend-governance` (`src/modules/ava-fabric-agents/shared/frontend-governance.md`) | Security invariants multi-framework, XSS, secrets, PII |
| Angular Patterns | `@angular-patterns-reference` (`src/shared/data/patterns/angular/angular-patterns-reference.md`) | Naming, Smart/Dumb, Reactive Forms, pipes |
| Build Validator | `@build-validator-agent` (`src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md`) | Pipeline de validação determinística |
| Build Fixer | `@build-fixer-agent` (`src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md`) | Correções automáticas de compilação |
| .NET Research | `@dotnet-research-instructions` (`src/modules/ava-fabric-agents/shared/dotnet-research-instructions.md`) | Análogo para backend .NET |

---

## §5 — Protocolo de Pesquisa por Pacote (5 Passos)

Para cada pacote identificado em `package.json` ou `project-config.yaml`:

| Passo | Ação | Ferramenta | Output |
|-------|------|-----------|--------|
| P1 — Discover latest | `npm view {packageName} version` | Bash | Versão latest stable |
| P2 — Check CVE | `npm audit --json` | Bash | Status CVE (clean/vulnerable) |
| P3 — Fetch docs oficiais | URLs de §1 conforme framework do pacote | fetch_webpage | Docs, breaking changes, migration guide |
| P4 — Fetch changelog | GitHub releases do pacote | fetch_webpage / github_text_search | Release notes, breaking changes entre versões |
| P5 — Consolidar | Agregar no bundle (versão, breaking changes, patterns, guardrails) | Write | Entrada no bundle §1-§6 |

### Regras de Fallback

```
SE P1 falhar → tentar P1b (npm registry API via fetch_webpage: registry.npmjs.org/{pkg})
SE P1b falhar → ⛔ BLOCKED para este pacote (NÃO usar versão de training data)
SE P3 falhar → registrar WARNING no bundle, continuar com P4
SE P4 falhar → registrar WARNING no bundle, continuar com P5
```

### Pacotes Cross-Framework Obrigatórios na Pesquisa

Independente do framework, SEMPRE pesquisar estes pacotes:

| Pacote | Propósito |
|--------|----------|
| `typescript` | Compilador TypeScript |
| `vite` (se Vite-based) | Build tool |
| `eslint` + `typescript-eslint` | Linting |
| `vitest` (se presente) | Test runner |
| `@azure/msal-browser` (se auth Azure AD) | Auth library |
| `dompurify` (se presente) | XSS sanitization |

---

## §6 — Breaking Changes Conhecidos por Versão de Framework

### React 19 (2024+)

1. **React Server Components (RSC)** — `'use client'` directive obrigatória para client components em frameworks RSC-enabled (Next.js App Router).
2. **`forwardRef` removido** — `ref` agora é uma prop regular; não é necessário `forwardRef`.
3. **`useFormState` → `useActionState`** — API renomeada; `useFormState` deprecated.
4. **Context como provider** — `<Context>` substitui `<Context.Provider>`; `.Provider` deprecated.
5. **Cleanup em refs** — ref callbacks suportam função de cleanup (retorno); evitar side effects diretos.
6. **`use()` hook** — leitura de promises e context com `use()` (substitui patterns com `useEffect` para data fetching).

### React 18 (2022+)

1. **`createRoot`** obrigatório — `ReactDOM.render()` removido.
2. **Automatic Batching** — `setState` em event handlers, timeouts e promises são batched automaticamente.
3. **Strict Mode dupla renderização** — componentes renderizam 2x em dev para detectar side effects.

### Vue 3.5 (2024+)

1. **`useTemplateRef()`** — novo hook para template refs; `ref` attribute para elementos DOM mantido mas hook é preferido.
2. **Reactive Props Destructure** — `defineProps()` retorno pode ser desestruturado reativamente (experimental → stable).
3. **`useId()`** — geração de IDs SSR-safe (equivalente ao `useId()` do React 18).

### Vue 3.4 (2024+)

1. **`defineModel()`** — macro para v-model customizado em componentes; substitui pattern `props + emit`.
2. **Parser mais rápido** — melhoria de performance, sem breaking changes diretos.

### Vue 3 (breaking vs Vue 2)

1. **`new Vue()` → `createApp()`** — API de montagem completamente diferente.
2. **Composition API** — `<script setup>` é o padrão; Options API suportada mas desencorajada.
3. **Filters removidos** — usar computed properties ou métodos.
4. **`$on`, `$off`, `$once` removidos** — usar EventBus externo (mitt) ou provide/inject.
5. **Múltiplos `v-model`** — suportado nativamente (`v-model:title`, `v-model:content`).

### Svelte 5 (2024+)

1. **Runes** — sistema de reatividade completamente novo: `$state`, `$derived`, `$effect` substituem `let`, `$:` e stores.
2. **`$props()`** — substitui `export let` para declarar props.
3. **Snippets** — `{#snippet}` substitui slots para composição de conteúdo.
4. **Event handlers** — `onclick` (atributo, lowercase) substitui `on:click` (diretiva).
5. **`$bindable()`** — props com two-way binding explícito.
6. **`$inspect()`** — substituição para `console.log` reativo em dev.

### Svelte 4 (2023)

1. **Mínimo Node 16** — drop support para Node 14.
2. **Transition API** — local transitions por padrão (antes eram globais).

### Vite 7 (2026+)

1. **Rolldown** — novo bundler substitui Rollup; plugins Rollup custom podem quebrar.
2. **Environment API** — nova API para SSR e multi-environment builds.

### Vite 6 (2025)

1. **`import.meta.env`** — variáveis de ambiente DEVEM ter prefixo `VITE_` para serem expostas ao client.
2. **Default `target`** — muda para browsers com suporte a `import.meta`.
3. **CSS `url()` rebase** — comportamento de resolução de URLs em CSS alterado.

### ESLint 9 (2024+)

1. **Flat config obrigatório** — `.eslintrc.*` não suportado por padrão; usar `eslint.config.js`.
2. **`defineConfig()`** — helper para type-safe config (ESLint 9.x).
3. **`globalIgnores()`** — substitui `.eslintignore` file.
4. **Formatters removidos** — `eslint --format` embutidos limitados; usar `@eslint/json` para JSON output.

### Vitest 4 (2026+)

1. **Requires Vite ≥ 6** — não compatível com Vite 5.
2. **`vi.mock()` scoping** — mock scoping mais restrito por padrão.
3. **Node 20+** — mínimo Node.js 20.

### APIs Deprecadas Conhecidas (Cross-Framework)

| API Deprecada | Framework | Versão | Substituto | Referência |
|---------------|-----------|--------|------------|-----------|
| `ReactDOM.render()` | React | 18+ | `createRoot().render()` | react.dev |
| `forwardRef()` | React | 19+ | `ref` como prop | react.dev |
| `useFormState()` | React | 19+ | `useActionState()` | react.dev |
| `<Context.Provider>` | React | 19+ | `<Context>` direto | react.dev |
| `new Vue()` | Vue | 3+ | `createApp()` | vuejs.org |
| Options API | Vue | 3+ | `<script setup>` Composition API | vuejs.org |
| `$on`, `$off`, `$once` | Vue | 3+ | `mitt` ou `provide/inject` | vuejs.org |
| `export let` (props) | Svelte | 5+ | `$props()` | svelte.dev |
| `$:` (reactive) | Svelte | 5+ | `$derived()`, `$effect()` | svelte.dev |
| `on:click` | Svelte | 5+ | `onclick` (atributo) | svelte.dev |
| slots | Svelte | 5+ | `{#snippet}` | svelte.dev |
| `.eslintrc.*` | ESLint | 9+ | `eslint.config.js` (flat config) | eslint.org |
| `eslintignore` | ESLint | 9+ | `globalIgnores()` em config | eslint.org |
