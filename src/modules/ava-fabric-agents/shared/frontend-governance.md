# Frontend Governance — Padrões Compartilhados

> **Versão:** 2.0.0 · **Data:** 2026-06-25
> Referenciado por: `coder-angular-frontend.md`, `coder-react-frontend.md`, `coder-vue-frontend.md`,
> `build-cycle-angular-agent.md`, `build-cycle-ngrx-agent.md`, `build-validator-agent.md`, `build-fixer-agent.md`
> Instruções de pesquisa: `jsts-research-instructions.md`, `dotnet-research-instructions.md`

---

## Data Sovereignty — Regra Absoluta

> ⛔ Nenhum dado do workspace (código, configs, artefatos, segredos) pode ser enviado
> para ambientes externos. Apenas GET/HEAD para documentação pública é permitido.
> Qualquer `curl`, `Invoke-WebRequest` ou equivalente com body ou dados do workspace
> é BLOQUEADO antes da execução.

---

## Security Invariants (OBRIGATÓRIOS — todos os frameworks JS/TS)

### XSS — Proteção por Framework

| Framework | API Perigosa | ⛔ PROIBIDO | ✅ Mitigação Obrigatória |
|-----------|-------------|-----------|-------------------------|
| Angular | `[innerHTML]` | Binding direto com dado de API | `DomSanitizer.sanitize()` ou `DomSanitizer.bypassSecurityTrustHtml()` com dado pré-sanitizado |
| React | `dangerouslySetInnerHTML` | `{{ __html: apiData }}` sem sanitização | `DOMPurify.sanitize(html)` antes do binding |
| Vue | `v-html` | `v-html="apiData"` sem sanitização | `DOMPurify.sanitize(html)` antes do binding |
| Svelte | `{@html}` | `{@html apiData}` sem sanitização | `DOMPurify.sanitize(html)` antes do binding |

> Para React, Vue e Svelte: instalar `dompurify` (`npm install dompurify @types/dompurify`) e sanitizar
> ANTES de passar ao binding. Angular possui `DomSanitizer` nativo — NÃO usar `DOMPurify` em Angular.

### Secrets — Configuração por Build Tool

| Build Tool | ⛔ PROIBIDO | ✅ Padrão Obrigatório |
|-----------|-----------|---------------------|
| Angular CLI | Hardcodar tokens, client IDs, URLs de API | `environment.ts` / `environment.prod.ts` |
| Vite (React, Vue, Svelte) | Hardcodar tokens, client IDs, URLs de API | `.env` / `.env.production` + `import.meta.env.VITE_*` |

> Variáveis de ambiente Vite DEVEM ter prefixo `VITE_` para serem expostas ao client bundle.
> Para CI/CD, usar token substitution: `#{TOKEN}#` em valores de `.env.production`.

### PII/Logs (todos os frameworks)

- **Nunca** logar dados pessoais (nome, email, CPF) — apenas IDs e códigos de erro
- **Nunca** persistir PII em `localStorage` ou `sessionStorage` sem criptografia
- Logs de telemetria devem usar IDs anônimos — nunca dados identificáveis

### Input Validation — por Framework

| Framework | ⛔ PROIBIDO | ✅ Padrão Obrigatório |
|-----------|-----------|---------------------|
| Angular | `[(ngModel)]` template-driven | `ReactiveFormsModule` + `FormGroup`/`FormControl` + `Validators` |
| React | Submissão sem validação client-side | `React Hook Form` + `Zod` ou `Yup` schema validation |
| Vue | Submissão sem validação client-side | `VeeValidate` + `Zod` ou `Yup` schema validation |
| Svelte | Submissão sem validação client-side | `superforms` + `Zod` ou validação manual com `$state` |

> Validators devem ser funções puras, testáveis isoladamente. Schemas Zod são preferidos
> para validação compartilhável entre client e server.

---

## Transition Notifications — Formato Padrão

Todo agente frontend DEVE emitir na primeira linha de cada resposta:

```
↳ 🔄 [{nome-do-agente}] Working...
```

E na conclusão:

```
↳ ✅ [{nome-do-agente}] Completed → {próximo passo}
```

| Agente | Início | Conclusão |
|---|---|---|
| `ava-stack-angular-frontend` | `↳ 🔄 [ava-stack-angular-frontend] Working...` | `↳ ✅ [ava-stack-angular-frontend] Completed → retornando ao ava-stack-orchestrator` |
| `ava-build-cycle-angular` | `↳ 🔄 [ava-build-cycle-angular] Working...` | `↳ ✅ [ava-build-cycle-angular] Completed → próximo: @ava-build-cycle-ngrx` |
| `ava-build-cycle-ngrx` | `↳ 🔄 [ava-build-cycle-ngrx] Working...` | `↳ ✅ [ava-build-cycle-ngrx] Completed → Build Cycle encerrado` |

---

## Consistency Verification Gate — Checklist Padrão

Antes de executar o Handoff final, verificar conforme o framework:

### Angular

- [ ] Todos os BCs detectados têm `routes.ts`, `service.ts` e `models/` gerados
- [ ] Nenhum componente gerado referencia arquivo não existente em `loadComponent`/`loadChildren`
- [ ] `angular.json` não referencia arquivos (`assets`, `styles`, `favicon`) não gerados nesta sessão
- [ ] `msal.config.ts` não contém nenhum valor hardcoded (Client ID, Tenant ID, Scope)
- [ ] Todos os `import` path depths estão corretos (3 levels para `core/`, 4 levels para `environments/`)

### React (Vite)

- [ ] Todos os BCs detectados têm `routes.tsx`, `api.ts` (ou `service.ts`) e `types/` gerados
- [ ] `index.html` existe na raiz do projeto frontend com `<script type="module" src="/src/main.tsx">`
- [ ] `vite.config.ts` usa `defineConfig` e referencia apenas plugins instalados
- [ ] `tsconfig.json` tem `strict: true`, `noImplicitAny: true`, `skipLibCheck: true`
- [ ] `.env` e `.env.production` existem; variáveis usam prefixo `VITE_`
- [ ] Nenhum `import` referencia módulo não existente (verificar via `npx tsc --noEmit`)
- [ ] Auth config não contém valores hardcoded (Client ID, Tenant ID)

### Vue (Vite)

- [ ] Todos os BCs detectados têm `router/index.ts`, `api/` (ou `composables/`) e `types/` gerados
- [ ] `index.html` existe na raiz com `<script type="module" src="/src/main.ts">`
- [ ] `vite.config.ts` usa `defineConfig` com `@vitejs/plugin-vue`
- [ ] `tsconfig.json` e `tsconfig.app.json` existem com `strict: true`
- [ ] `.env` e `.env.production` existem; variáveis usam prefixo `VITE_`
- [ ] Pinia stores declarados com `defineStore()` e registrados em `main.ts`
- [ ] Auth config não contém valores hardcoded

### Svelte (Vite / SvelteKit)

- [ ] Todos os BCs detectados têm rota, service e types gerados
- [ ] `index.html` existe (Vite) ou `+page.svelte` / `+layout.svelte` existem (SvelteKit)
- [ ] `vite.config.ts` usa `defineConfig` com `@sveltejs/vite-plugin-svelte`
- [ ] `tsconfig.json` e `svelte.config.js` existem
- [ ] `.env` e `.env.production` existem; variáveis usam prefixo `VITE_`
- [ ] Auth config não contém valores hardcoded

Se qualquer item falhar → corrigir antes do Handoff. Não reportar `COMPLETED` com inconsistências abertas.
