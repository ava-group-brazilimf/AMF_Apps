# Tasks — Spec 042: Scaffold Angular determinístico com harness de validação

> Status: **implementado e verificado end-to-end em 2026-08-21.**
>
> Ordem causal: os templates precedem o gerador que os renderiza; o gerador precede o
> verificador que o valida; ambos precedem o wiring na esteira que os invoca.
>
> **Evidência do Quality Gate** (árvore recém-gerada do `example-vcl-login`, sem
> lockfile e sem nenhuma edição manual):
>
> | Passo | Resultado |
> |---|---|
> | 1 · unit tests | 55 passed (32 gerador + 23 verificador) |
> | 2 · `verify_angular_app` | **PASS** — prereq, install (`npm install`), build, boot, health · 302.9s |
> | 3 · commit inicial | `26f2851` · 27 arquivos, `package-lock.json` versionado, `node_modules/`+`dist/`+`.artifacts/` ignorados |
> | 4 · manifest gate | **PASS** — 16/16, `blocking_missing=0` |
> | 5 · não-regressão .NET | 108 passed |
> | 5b · suíte completa vs. HEAD pristino | **0 regressões** — 472→528 testes (+56), as mesmas 33 falhas pré-existentes nos dois lados |
>
> O `dist` foi resolvido em `dist/example-vcl-login/browser` (layout v17+) e o boot
> usou porta efêmera — os dois caminhos que o script `.sh` original não cobria no Windows.
>
> A não-regressão do passo 5b foi medida com `--junit-xml` contra um `git worktree` do
> HEAD, comparando os conjuntos de falhas — não apenas as contagens. As 33 falhas
> pré-existentes (`test_run_ast_analysis`, `test_agent_wrappers`, `test_pipeline_plan`,
> `test_artifact_gate_tobe` e outras) são anteriores a esta spec e não foram tocadas.
> `tests/utils/test_mermaid_quality.py` nem coleta, por um `ModuleNotFoundError` também
> pré-existente — vale um ticket próprio.

## 1. Governança

- [x] T-001 — Criar `spec.md` com Problem Statement (B1–B6 + seis causas raiz), US1–US6,
      BDD nominal/borda/gate e Quality Gate
- [x] T-002 — Criar `plan.md` com Constitution Check, arquitetura, decisões D1–D6 e
      semântica de falha
- [x] T-003 — Criar `tasks.md` (este arquivo)

## 2. Templates versionados

- [x] T-010 — Criar `src/shared/templates/angular-scaffold/versions.yaml` mapeando major
      Angular → versões exatas de dependências (runtime e dev)
- [x] T-011 — `angular.json.tmpl` com `application` builder, `browser` como entry point,
      `polyfills: ["zone.js"]` (B5), `assets`, `configurations.production` com
      `fileReplacements` (B6) e `serve.buildTarget` (B4)
- [x] T-012 — `package.json.tmpl` com scripts `start`/`build`/`test`/`lint` e deps
      resolvidas do `versions.yaml`
- [x] T-013 — `tsconfig.json.tmpl` (base) e `tsconfig.app.json.tmpl` **self-contained, sem
      `extends`**, com `files: ["src/main.ts"]` (B1/B2) e o `paths` de
      `@ngrx/store/src/models`. O `paths` fica declarado mesmo sem NgRx instalado:
      não custa nada (nenhum import casa com ele) e deixa o tsconfig correto para
      quando `build-cycle-ngrx-agent` acrescentar a dependência
- [x] T-014 — `tsconfig.spec.json.tmpl` coerente com o target `test` do `angular.json` (B1)
- [x] T-015 — `src/index.html.tmpl`, `src/main.ts.tmpl`, `src/styles.scss.tmpl` e
      `src/favicon.ico` — extensão `.scss` alinhada ao manifest
- [x] T-016 — `src/environments/environment.ts.tmpl` e `environment.prod.ts.tmpl`,
      referenciados pelo `fileReplacements` de T-011
- [x] T-017 — `src/app/app.component.ts.tmpl`, `app.config.ts.tmpl` e `app.routes.ts.tmpl`;
      `AppComponent` importa apenas `RouterOutlet` e layout (nunca `MsalRedirectComponent`)
- [x] T-018 — Templates por BC: `{bc}.routes.ts.tmpl` e `{bc}-home.component.ts.tmpl`,
      componentes reais com `OnPush` e **todo pipe usado declarado no `imports`** (B3)
- [x] T-019 — `.gitignore.tmpl`, `.editorconfig.tmpl`, `README.md.tmpl`,
      `proxy.conf.json.tmpl` e os `.gitkeep` de `core/{auth,interceptors,guards}` e `shared/`

## 3. Gerador determinístico

- [x] T-020 — Criar `src/shared/tools/f4s_angular_scaffold.py` com CLI
      `--project --root --force --json`
- [x] T-021 — Renderizador `{{token}}` por `str.replace` (D2); cobrir o caso de token
      desconhecido remanescente no output como erro, não como texto literal
- [x] T-022 — Resolver `app_root` via `stack_source_dir(project, "angular")` de
      `f4s_deterministic_harness.py` (D3) — reusar, não reimplementar
- [x] T-023 — Resolver o major do Angular de `project-config.yaml` contra `versions.yaml`;
      major não mapeado → `ERROR` nomeando os suportados, sem escrever nada
- [x] T-024 — Derivar bounded contexts de `architecture-blueprint.md` reusando a heurística
      de `f4s_scaffold_injector.py`
- [x] T-025 — Escrita idempotente: preservar arquivo existente salvo `--force`; contabilizar
      `files_written` e `files_skipped`
- [x] T-026 — Saída JSON `{status, app_root, files_written, files_skipped, bcs}` e exit
      codes 0/1/2 na convenção dos demais scripts

## 4. Harness de validação

- [x] T-030 — Criar `src/shared/utils/verify_angular_app.py` com CLI
      `--root --timeout --path --expect --skip-serve --json` e log em `.artifacts/`
- [x] T-031 — Resolver `app_root` procurando `angular.json` na raiz e até dois níveis
      abaixo (compatibilidade com árvores legadas, D3)
- [x] T-032 — Fase 0 prereq: `node`/`npm` no PATH e `package.json` presente → exit 10
- [x] T-033 — Fase 1 install: `npm install` sem lockfile, `npm ci` com lockfile (D4) →
      exit 20
- [x] T-034 — Fase 2 build: `npx ng build --configuration production`; localizar
      `dist/**/index.html` cobrindo o layout `dist/<app>/browser` do v17+ → exit 30
- [x] T-035 — Fase 3 boot: `http.server` da stdlib sobre o dist, **bind na porta 0** (D5);
      detectar morte prematura do servidor sem esperar o timeout → exit 40
- [x] T-036 — Fase 4 health: poll até `HTTP 200` com verificação de conteúdo
      (`--expect`, default `<app-root`) → exit 50
- [x] T-037 — Shutdown garantido por `try/finally` + `atexit` (D5)
- [x] T-038 — Saída JSON `{status, phases[], app_root, log_path}` e veredito único

## 5. Manifest

- [x] T-040 — Em `angular-scaffold-manifest.yaml`, fixar `src/styles.scss` e remover a
      contradição com o spec (causa raiz 3)
- [x] T-041 — Acrescentar `.gitignore` e conferir que toda entrada `blocking: true`
      corresponde a um arquivo efetivamente produzido pelos templates

## 6. Wiring na esteira

- [x] T-050 — Renomear `_run_nuget_checks` → `_run_stack_checks(repo_root, target_stack)`
      preservando integralmente o comportamento do caminho `dotnet`
- [x] T-051 — Ramo `angular`: `verify_scaffold.py --manifest angular` seguido de
      `verify_angular_app.py --root <app_root>`
- [x] T-052 — Invocar o gate após `_run_scaffold_path_check` e antes de `run_build`,
      reusando o padrão `append_log` + `remediation_context` + `continue`
- [x] T-053 — Em `f4s_build_runner.py`, retirar `npm ci &&` do comando de `angular`
      (o verificador passa a ser a autoridade sobre install+build)
- [x] T-054 — Reordenar o commit inicial: `ensure_repo → gerar → validar (PASS) → commit`,
      com mensagem `feat(scaffold): angular workspace compilando e validado`.
      Verificador reprovando ⇒ **sem commit**

## 7. Spec de scaffold

- [x] T-060 — Reescrever `angular-scaffold.md` como contrato do gerador: `## Execução`
      invocando os dois scripts e `## Contrato` declarando a árvore como fixa
- [x] T-061 — Bloco `## Restrições ⛔` no molde de `dotnet-scaffold.md:64-70`: nunca remover
      `polyfills`; nunca pôr `extends` no `tsconfig.app.json`; todo pipe usado em template
      de standalone component deve estar no `imports`; nunca referenciar em `angular.json`
      arquivo não gerado
- [x] T-062 — Trocar "leia como referência de engenharia" por vínculo obrigatório aos
      guardrails de `build-cycle-angular-agent.md`

## 8. Testes

- [x] T-070 — `tests/tools/test_f4s_angular_scaffold.py`: substituição de tokens;
      idempotência (2ª execução preserva); N bounded contexts; major não suportado → ERROR
- [x] T-071 — Teste de regressão B1/B6: todo caminho referenciado em `angular.json`
      (`tsConfig`, `browser`, `index`, `styles`, `assets`, `fileReplacements`) existe na
      árvore gerada
- [x] T-072 — `tests/utils/test_verify_angular_app.py`: cada fase falhando devolve seu exit
      code; `--skip-serve`; escolha install-vs-ci por presença de lockfile; resolução do
      `dist/<app>/browser`; shutdown no `finally`. Rede mockada via `subprocess.run`
- [x] T-073 — Não-regressão: `tests/tools/test_f4s_phase.py` continua verde após T-050

## 9a. Decisões de escopo tomadas durante a implementação

- **Delimitador de token é `%%token%%`, não chave dupla.** Os templates contêm
  interpolação do Angular (`{{ title }}`); os dois delimitadores colidiriam e a
  verificação de "token remanescente" (T-021) daria falso positivo. Registrado em
  `plan.md` D2, cuja justificativa original (`$` do `string.Template`) era mais fraca.
- **Angular Material entra como dependência, mas o scaffold não carrega tema.** O caminho
  do arquivo de tema pré-compilado muda entre majors; referenciá-lo em `angular.json`
  reintroduziria a classe de defeito B1. O tema entra com o primeiro componente Material.
- **NgRx e MSAL não entram no `package.json` do scaffold.** São matrizes de versão de
  outros fornecedores, com peer-dependencies próprias, e nada no esqueleto os importa.
  Uma dependência que ninguém usa só acrescenta risco de `npm install` falhar.
- **`_run_stack_checks` para Angular roda só o manifest, não o harness completo.** O
  harness é invocado como o próprio comando de build (`STACK_VERIFIERS`); rodá-lo também
  como pré-gate significaria dois `npm ci` e dois `ng build` por feature.
- **Zero BCs derriváveis reprova com `ERROR`** e aponta o escape hatch `--bcs`. Inventar
  estrutura em silêncio é a causa raiz que esta spec elimina.

## 9. Documentação

- [x] T-080 — Entrada em `CHANGELOG.md` (`### ✨ Added — Spec 042`), Article X
