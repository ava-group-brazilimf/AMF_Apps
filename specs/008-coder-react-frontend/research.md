# Research Notes: coder-react-frontend (PBI-2322)

## 1. State management: Zustand for client state, TanStack Query for server state

**Decision**: Use **Zustand** for UI/client state (modals, filters, form steps) and **TanStack Query v5**
(`@tanstack/react-query`) for all server state (GET, POST, PUT, DELETE).

**Rationale**:
- The 7 PBIs from project Sophia all involved either filter state bugs (PBI 2245/2246 → Zustand `useFilterStore`)
  or CRUD cache bugs (PBI 2250 → `queryClient.invalidateQueries` after mutation). Using one library for each
  concern cleanly separates responsibilities and matches the PBI description exactly.
- Zustand has near-zero boilerplate, works with TypeScript strict, and does not require Context providers —
  compatible with Vite + strict mode.
- TanStack Query v5 has first-class TypeScript support, built-in `onSuccess`/`onSettled` mutation callbacks
  for cache invalidation, and a `useQuery({ enabled: !!id })` pattern that satisfies PBI 2251 (Update pre-population).

**Alternatives considered**:
- Redux Toolkit: heavier boilerplate, not specified in PBI; eliminated.
- Jotai: similar to Zustand but less ecosystem adoption in IMFAI projects; eliminated.
- SWR: good for GET but lacks mutation-invalidation workflow of TanStack Query; eliminated.

---

## 2. Service layer generator: openapi-typescript (types) + fetch wrapper

**Decision**: Use **`openapi-typescript`** to generate TypeScript types from the BC's OpenAPI spec, and
write a thin typed `createApiClient(baseUrl)` wrapper using native `fetch`. Do NOT use orval (code
generator) as the primary path — it adds too much generated boilerplate; keep it as an optional note.

**Rationale**:
- PBI 2328 specifies "openapi-typescript ou orval" — openapi-typescript is lighter, generates only types
  (no runnable code that can hallucinate), and the agent can reliably produce the `createApiClient` wrapper
  from templates.
- The Angular agent uses a similar approach (type-first, then typed fetch). Structural parity requirement
  from PBI 2322 objective.
- `npx openapi-typescript {spec-path} -o src/features/{bc}/types/api.d.ts` is a deterministic command.

**Alternatives considered**:
- orval: generates full hooks + services; high risk of the agent producing inconsistent output when no spec
  is present (edge case); kept as an optional note for advanced users.
- Manual DTO duplication: explicitly prohibited by PBI 2328.

---

## 3. Build scaffolding: Vite + React Router v6

**Decision**: **Vite 5** as build tool, **React Router v6** for routing. Next.js App Router is explicitly
out of scope for v1.0.0 (spec §7 Exclusions).

**Rationale**:
- PBI 2322 objective specifies "Vite + React 18 + TypeScript strict".
- Vite 5 + `@vitejs/plugin-react` is the canonical Vite+React setup; CSP headers can be set via
  `vite-plugin-csp` or a `<meta>` tag in `index.html`.
- React Router v6 provides declarative `<Route>` and `<Navigate>` with the loader/action pattern.
  The Routing Guard uses `<Navigate to="/not-supported">` when `frontend_framework !== "react"`.

**Alternatives considered**:
- Next.js: ruled out by spec §7 (out of scope v1.0.0).
- Create React App (deprecated): eliminated.

---

## 4. Chart library: Recharts (default), schema-driven guardrail

**Decision**: Use **Recharts** as the default chart library (read from `tobe_stack.ui_library` if present,
else default to Recharts). The guardrail for X/Y axis keys is library-agnostic — it applies regardless
of which Recharts/Chart.js/Nivo component is used.

**Chart axis guardrail rule** (resolves PBI 2249):
```
ANTES de escrever qualquer componente de gráfico:
1. READ OpenAPI spec do BC → localizar o endpoint que alimenta o gráfico
2. Identificar o campo de resposta que mapeia para eixo X (ex: "period", "date", "category")
3. Identificar o campo de resposta que mapeia para eixo Y (ex: "value", "total", "count")
4. Usar SOMENTE esses nomes de campo como dataKey
5. SE não for possível determinar os campos → adicionar TODO + WARNING no ImplementationNotes.md
   e usar placeholder genérico "value" marcado com ⚠️ no comentário
```

**Rationale**: PBI 2249 reported "bug na plotagem de gráficos" — the root cause was the agent inventing
`dataKey` strings not present in the API response, causing Recharts to render an empty chart. The guardrail
forces schema lookup before axis assignment.

---

## 5. Modal pattern: local boolean state, typed props interface

**Decision**: Generate Modals using **local `useState<boolean>(false)`** for `isOpen` managed by the
parent component, with a typed interface:
```typescript
interface {ModalName}Props {
  isOpen: boolean;
  onClose: () => void;
  // ...domain props
}
```

**Rationale**: PBI 2244 ("agente não reconhecia modais") and PBI 2251 ("formulário de Update incompleto")
both stemmed from the STUB hallucinating Modal structure. The typed interface is explicit, non-ambiguous,
and parity with Angular's `@Input()` pattern.

---

## 6. FilterPanel: Zustand store with `useMemo` combining all active filters

**Decision**: Generate a `useFilterStore` Zustand store with a `filters` map; the FilterPanel component
derives `filteredData` via `useMemo(() => data.filter(item => allFiltersPass(item, filters)), [data, filters])`.

**Root cause of PBI 2245/2246**: The STUB generated a `filters.forEach` that applied filters sequentially
with early return on the first match, not AND-conjunction. The `useMemo` + `allFiltersPass` pattern
forces all criteria to be applied simultaneously before an item passes through.

---

## 7. Security Compliance Gate: CSP, XSS, PII

**Decision**: The Security Compliance Review Gate (same pattern as Angular agent) runs as the final step
**after code generation and before handoff**. It checks:
1. **PII in localStorage**: regex scan for `localStorage.setItem` with keys/values matching `name|email|cpf|token|senha|password|phone`
2. **CSP**: `index.html` must contain a `<meta http-equiv="Content-Security-Policy">` tag OR `vite-plugin-csp` is listed as a dependency in `package.json`
3. **XSS via `dangerouslySetInnerHTML`**: any usage must be accompanied by `DOMPurify.sanitize()` on the same string

---

## 8. Required scaffolding files (non-negotiable, parity with Angular agent)

The following files MUST be generated for every React project to avoid `vite build` failures:

| File | Reason if absent |
|------|-----------------|
| `index.html` | Vite entry point — build fails: `Could not resolve entry module 'index.html'` |
| `src/main.tsx` | React DOM root — build fails: cannot find module |
| `src/App.tsx` | Root component — required by `main.tsx` |
| `vite.config.ts` | Build config — `plugin-react` required for JSX transform |
| `tsconfig.json` | TypeScript config — `"strict": true`, `"skipLibCheck": true` |
| `vitest.config.ts` | Test config — references `jsdom` environment |

---

## 9. Test Scaffolder: Vitest + React Testing Library

**Decision**: Generate `{ComponentName}.spec.tsx` alongside every component using:
- `vitest` (not Jest globals)
- `@testing-library/react` for render + interaction
- `@testing-library/user-event` for realistic events
- `vi.mock(...)` for service hooks

Minimum test coverage per component:
1. Smoke render (renders without error)
2. Primary interaction (button click / form submit)
3. Service mock (mocked `useQuery`/`useMutation` returns expected data)

---

## 10. stub-registry.yaml and module.yaml updates

**stub-registry.yaml**: entry at line ~81 must have `status` changed from `STUB` to `COMPLETE`.
Additional note to keep: `notes: Also needs build-cycle variants: build-cycle-react, build-cycle-react-state.`

**module.yaml** (`tech-stack`): `ava-stack-react-frontend` entry must have `status: stub` removed.

**orchestrator-stack.md**: routing comment for `react` frontend must be updated to remove "STUB" warning
and confirm the agent is active.
