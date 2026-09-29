---
id: 000-scaffold
name: Scaffold Angular Frontend
component_type: frontend
stack: angular
generator: src/shared/tools/f4s_angular_scaffold.py
verifier: src/shared/utils/verify_angular_app.py
template_path: src/shared/templates/angular-scaffold
version_source: versions.yaml
manifest: angular
---

# F4S Scaffold Spec — Angular Frontend

## Objetivo

Criar a estrutura base (scaffold) da aplicação Angular no repo
`outputs/tobe/source-code/{target_stack}`. Este é o **primeiro spec** da F4S.
Todo spec posterior deve respeitar os módulos, rotas e convenções estabelecidas
aqui.

## Entradas obrigatórias

- `projects/{project_name}/context/project-config.yaml`
- `projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md`
- `projects/{project_name}/outputs/tobe/speckit/constitution.md` (se existir)
- `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-angular-agent.md`
  (leia como referência de engenharia)

## Estrutura a gerar

Gere um workspace Angular com standalone components:

```
angular.json          package.json         tsconfig.json
tsconfig.app.json     tsconfig.spec.json   proxy.conf.json
.gitignore            .editorconfig        README.md
src/
  index.html   main.ts   styles.scss   favicon.ico
  environments/environment.ts   environments/environment.prod.ts
  app/
    app.component.ts   app.config.ts   app.routes.ts
    core/{auth,interceptors,guards}/
    shared/
    features/
      {bc1}/
      {bc2}/
```

- Derive os bounded contexts de `architecture-blueprint.md`.
- Use Angular `tobe_stack.frontend_version` (ex: `17`).
- Configure TypeScript `strict: true`, lazy loading e MSAL/Auth conforme
  `constitution.md`.
- Não gere ainda componentes de telas, stores completos nem regras de negócio —
  apenas a estrutura esqueleto, dependências e configuração de build.

## Restrições

- Não altere arquivos fora de `outputs/tobe/source-code/angular`.
- O projeto deve passar em `verify_angular_app.py` com `PASS` nas quatro fases.
- O scaffold é idempotente: se algo já existir, preserve e adapte.

### ⛔ Invariantes que o codegen de features NÃO pode quebrar

- **⛔ NUNCA acrescente `extends` a `tsconfig.app.json`.** O builder esbuild do Angular
  17+ executa o TypeScript de outro working directory; um `extends` relativo falha com
  `Cannot find base config file 'tsconfig.json'`. O arquivo é self-contained por design.
- **⛔ NUNCA remova `"polyfills": ["zone.js"]` de `angular.json`.** Sem ele o build
  **passa** e a aplicação morre no browser com `NG0908` — defeito que só a fase health
  do verificador captura.
- **⛔ TODO pipe usado no template de um componente standalone deve estar em `imports`.**
  Não existe `CommonModule` implícito em standalone: `| date`, `| number`, `| currency`
  e `| async` exigem `DatePipe`, `DecimalPipe`, `CurrencyPipe` e `AsyncPipe`
  explicitamente importados. Omitir gera `NG8004` em AOT — erro de compilação, não aviso.
  Nenhum módulo do Angular Material reexporta esses pipes.
- **⛔ NUNCA referencie em `angular.json` um arquivo que não existe na árvore**
  (`tsConfig`, `browser`, `index`, `styles`, `assets`, `fileReplacements`). Cada um
  desses caminhos é conferido pelo manifest `angular-scaffold-manifest.yaml`.
- **⛔ NUNCA aponte uma rota `loadComponent`/`loadChildren` para arquivo inexistente.**
  Em AOT isso é erro de compilação, não 404 em runtime.
- **⛔ `MsalRedirectComponent` NÃO é standalone** — nunca o coloque no `imports` de um
  componente standalone. O padrão correto é factory providers (`MSAL_INSTANCE`,
  `MSAL_GUARD_CONFIG`, `MSAL_INTERCEPTOR_CONFIG`) com `importProvidersFrom(MsalModule)`
  em `app.config.ts`.
- **⛔ Ao acrescentar uma dependência, use `npm install` na pasta do projeto** e
  **commite o `package-lock.json`**. `npm ci` sem lockfile falha, e era assim que o
  build da esteira quebrava antes da spec 042.
