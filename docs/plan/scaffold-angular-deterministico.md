Ready for review
Select text to add comments on the plan
Spec 042 — Scaffold Angular determinístico com harness de validação
Context
O scaffold Angular atual (angular-scaffold.md) é um spec em prosa que um agente LLM interpreta para escrever arquivos. O resultado não compila. A análise do único projeto já gerado (example-vcl-login/.../frontend/apps-login-spa/) expôs seis defeitos independentes:

#	Defeito	Efeito
B1	tsconfig.app.json / tsconfig.spec.json referenciados em angular.json mas não gerados	ng build morre antes de compilar
B2	tsconfig.json sem files/include	ngtsc compila zero arquivos
B3	pipe number usado sem DecimalPipe no imports do standalone component	erro AOT NG8004
B4	serve sem buildTarget	ng serve falha na validação de schema
B5	polyfills: ["zone.js"] ausente	build passa, app morre no browser (NG0908)
B6	sem configurations.production / fileReplacements	environment.prod.ts é arquivo morto
Causas raiz — todas estruturais, nenhuma pontual:

A árvore do spec omite os arquivos que quebraram. angular-scaffold.md:28-47 não lista tsconfig.app.json, tsconfig.spec.json nem src/environments/. O agente gerou fielmente a árvore pedida — a árvore é que está errada.
Os guardrails corretos existem mas não vinculam. build-cycle-angular-agent.md:92-118 já cobre B1, B2 e B5, mas o spec só manda "ler como referência de engenharia".
Contradição de contrato: o spec manda styles.css; o manifest exige styles.scss com blocking: true. Um scaffold que siga o spec reprova no gate do próprio repo.
O gate que pegaria B1 não roda na esteira F4S. verify_scaffold.py --manifest angular só é invocado como linha de Bash dentro de prompts markdown. Em f4s_phase_runner.py existem apenas _run_scaffold_path_check e _run_nuget_checks — e este faz if target_stack != "dotnet": return na entrada.
npm ci sem lockfile. f4s_build_runner.py:22 usa npm ci, que exige package-lock.json — e o scaffold nunca gerou um.
Divergência de raiz. repo_root = source-code/{target_stack} (f4s_phase_runner.py:390) mas o projeto real foi escrito em source-code/frontend/apps-login-spa/. O build roda num diretório sem package.json.
Resultado pretendido: o scaffold Angular passa a ser gerado deterministicamente a partir de templates versionados, compila na primeira tentativa, é validado end-to-end (install → build → boot → health) e é commitado já compilando. O LLM só entra depois, para features por bounded context, sobre uma base que já passa no gate.

Decisões já tomadas com o usuário: templates versionados no repo (não ng new); harness completo com boot+health (não só build); o .md vira contrato do gerador.

Entrega — specs/042-angular-scaffold-deterministic-harness/
Documentar via SpecKit antes de codar, seguindo a convenção dos specs recentes (039, 040, 041): três arquivos, sem checklists/. Numeração 042 — 041 é a maior existente.

spec.md
Cabeçalho no padrão de 041/spec.md:1-7: # Agent Specification: … + Feature Branch / Created / Status: Draft / Change Type: modify-existing (scaffold + phase runner) + new-script (gerador e verificador) / Origem: análise do example-vcl-login.

Seções:

Problem Statement — a tabela B1–B6 e as seis causas raiz acima, com os file:line como evidência.
User Stories
US1 — Scaffold que compila na primeira tentativa, sem edição manual.
US2 — Validação determinística prova que o app sobe e responde, não só que compila.
US3 — Commit inicial contém uma estrutura já verificada.
US4 — Dependências instaladas com npm install na pasta do projeto.
US5 — Falha de scaffold é atribuída no próprio passo, antes do codegen de features.
US6 — Regeneração é idempotente: não sobrescreve trabalho posterior do LLM.
Acceptance Scenarios (BDD) — Nominal (gerar → validar → commitar); Edge: sem lockfile na 1ª execução, porta ocupada, major do Angular não suportado, scaffold pré-existente (idempotência), dist/ em layout v17 (dist/<app>/browser), servidor que morre durante o boot.
Quality Gate — os cinco comandos da seção Verificação abaixo.
Out of Scope — React, Vue, Blazor.
plan.md
Constitution Check — mapear contra .specify/memory/constitution.md: Article I (nenhuma versão de tecnologia hardcoded no corpo do agente → vão para versions.yaml), Article V (mensagens e docs em pt-BR), Article VI (BDD nominal + edge), Article VIII (trace_id e logs preservados), Article X (entrada em CHANGELOG.md), Article XI (nenhum agente novo — só scripts determinísticos).
Architecture — o diagrama de fluxo ensure_repo → gerar → validar → commitar e o ponto de encaixe no f4s_phase_runner.py.
Decisões de projeto — as três escolhas acordadas, mais as restrições de implementação abaixo.
Trabalho futuro — dispatch por stack pronto para React/Vue/Blazor.
tasks.md
Grupos T-0xx espelhando as seções 1–8 da implementação, no estilo de 041/tasks.md: checkbox por task, ordem causal declarada, todas começando desmarcadas.

Restrições de implementação
Somente stdlib. O repo não tem requirements.txt nem pyproject.toml; pyyaml é importado defensivamente (try/except ImportError). Nada de jinja2.
Substituição por {{token}} com str.replace. Não usar string.Template: $ aparece em template literals TS (${x}) e variáveis SCSS, e quebraria a renderização.
Windows é o alvo (win32). O verify-angular.sh anexo usa lsof, trap e /tmp — nenhum portável. Isso justifica a reescrita em Python, não uma tradução literal.
Implementação
1. Templates — src/shared/templates/angular-scaffold/
Árvore .tmpl que fecha B1–B6 por construção:

versions.yaml                  # major Angular -> versões exatas de deps
angular.json.tmpl              # application builder, polyfills, buildTarget,
                               #   configurations.production + fileReplacements
package.json.tmpl
tsconfig.json.tmpl
tsconfig.app.json.tmpl         # SELF-CONTAINED (sem extends) + files:["src/main.ts"]
tsconfig.spec.json.tmpl
.gitignore.tmpl  .editorconfig.tmpl  README.md.tmpl  proxy.conf.json.tmpl
src/index.html.tmpl  src/main.ts.tmpl  src/styles.scss.tmpl  src/favicon.ico
src/environments/environment{,.prod}.ts.tmpl
src/app/app.{component,config,routes}.ts.tmpl
src/app/core/{auth,interceptors,guards}/.gitkeep    src/app/shared/.gitkeep
src/app/features/_bc/{bc}.routes.ts.tmpl            # renderizado 1x por BC
src/app/features/_bc/{bc}-home.component.ts.tmpl    # placeholder compilável
tsconfig.app.json sem extends — o esbuild builder do v17 roda o TS de outro CWD e falha com "Cannot find base config file"; guardrail já documentado em build-cycle-angular-agent.md:110-118. Copiar compilerOptions inteiro e incluir o paths de @ngrx/store/src/models.
Todo componente placeholder declara no imports todo pipe que usa (fecha B3) e usa ChangeDetectionStrategy.OnPush.
Cada BC ganha um componente real, para que as rotas lazy em app.routes.ts resolvam e o AOT compile.
versions.yaml mapeia major → versões exatas; major não suportado → ERROR explícito. Nunca adivinhar versões (Article I).
2. Gerador — src/shared/tools/f4s_angular_scaffold.py
--project <name> [--root <dir>] [--force] [--json]

Ler context/project-config.yaml → app_name, tobe_stack.frontend_version.
Derivar bounded contexts de architecture-blueprint.md — reusar a heurística de f4s_scaffold_injector.py, não reimplementar.
Resolver a raiz com stack_source_dir(project, "angular") de f4s_deterministic_harness.py:45. O angular.json fica na raiz do repo git, de modo que app_root == git repo root == build cwd — corrigindo a causa raiz 6 em vez de perpetuá-la.
Renderizar. Idempotente: arquivo existente é preservado salvo --force.
JSON {status, app_root, files_written, files_skipped, bcs}.
3. Verificador — src/shared/utils/verify_angular_app.py
Porte do verify-angular.sh, na convenção dos verificadores existentes (--root, --json, {"status": PASS|FAIL|ERROR|SKIPPED}, log em .artifacts/):

Fase	Ação	Exit
0 prereq	node/npm/git no PATH, package.json presente	10
1 install	npm install se não há lockfile; npm ci se há	20
2 build	npx ng build --configuration production; localiza dist/**/index.html	30
3 boot	http.server da stdlib servindo o dist, bind na porta 0	40
4 health	poll até HTTP 200 + conteúdo esperado, depois shutdown	50
Divergências deliberadas do .sh, todas por portabilidade ou determinismo:

npm install primeiro, npm ci depois — atende o requisito explícito e resolve a causa raiz 5. O package-lock.json gerado entra no commit inicial, então da segunda execução em diante o install é reprodutível.
http.server da stdlib em vez de npx http-server — sem download extra e igual no Windows.
Porta efêmera (bind 0) em vez do check com lsof — elimina a falha "porta já em uso".
try/finally + atexit no lugar do trap.
4. Manifest — angular-scaffold-manifest.yaml
Fixar .scss (resolvendo a contradição da causa raiz 3) e acrescentar .gitignore e tsconfig.spec.json como entradas coerentes com os templates.

5. Wiring — f4s_phase_runner.py
Generalizar o gate hoje exclusivo do .NET: _run_nuget_checks → _run_stack_checks(repo_root, target_stack) com dispatch:

dotnet  -> verify_nuget_packages.py + verify_cpm_consistency.py   (comportamento atual)
angular -> verify_scaffold.py --manifest angular
           + verify_angular_app.py --root <app_root>
Encaixe após _run_scaffold_path_check e antes de run_build (~L514-555), reusando o padrão append_log + remediation_context + continue já presente. Em f4s_build_runner.py:22-24, angular deixa de usar npm ci && npm run build — o verificador passa a ser a autoridade.

6. Git — reusar, não criar
Nenhum código git novo. ensure_repo() em f4s_deterministic_harness.py:85 já faz git_init + .gitignore por stack + commit inicial, sobre f4s_git_helper.py.

A mudança é de ordem: hoje o commit inicial ocorre em f4s_phase_runner.py:400-403 num diretório vazio, antes de qualquer geração. A nova sequência:

ensure_repo -> gerar scaffold -> verify_angular_app (PASS) -> commit inicial
mensagem feat(scaffold): angular workspace compilando e validado. Se o verificador reprovar, não há commit — a esteira entra em remediação.

7. Spec .md — angular-scaffold.md
Reescrever como contrato do gerador: ## Execução (invoca os dois scripts), ## Contrato (a árvore é fixa, o agente não a reescreve) e ## Restrições ⛔ no molde de dotnet-scaffold.md:64-70, para quando o LLM tocar nesses arquivos depois: nunca remover polyfills; nunca pôr extends no tsconfig.app.json; todo pipe usado em template de standalone component deve estar no imports; nunca referenciar em angular.json arquivo não gerado.

8. Testes
tests/tools/test_f4s_angular_scaffold.py — tokens; idempotência (2ª execução não sobrescreve); N bounded contexts; major não suportado → ERROR; angular.json referencia apenas arquivos gerados (regressão de B1/B6).
tests/utils/test_verify_angular_app.py — cada fase falhando devolve seu exit code; --skip-serve; escolha install-vs-ci por presença de lockfile; porta efêmera; shutdown no finally. Fases de rede mockadas via subprocess.run.
9. CHANGELOG.md
Entrada ### ✨ Added — Spec 042 (Article X).

Verificação
# 1. Unit tests
python -m pytest tests/tools/test_f4s_angular_scaffold.py \
                 tests/utils/test_verify_angular_app.py -v

# 2. Gerar num projeto real e validar de verdade (roda npm install + ng build)
python src/shared/tools/f4s_angular_scaffold.py --project example-vcl-login --json
python src/shared/utils/verify_angular_app.py \
       --root projects/example-vcl-login/outputs/tobe/source-code/angular --json
#    esperado: {"status":"PASS"}, exit 0, as 4 fases em PASS no log

# 3. Commit inicial compilando
git -C projects/example-vcl-login/outputs/tobe/source-code/angular log --oneline
git -C projects/example-vcl-login/outputs/tobe/source-code/angular ls-files | head -30
#    package-lock.json versionado; node_modules/ e dist/ não

# 4. Manifest gate
python src/shared/utils/verify_scaffold.py --manifest angular \
       --root projects/example-vcl-login/outputs/tobe/source-code/angular

# 5. Não-regressão do caminho .NET
python -m pytest tests/tools/test_f4s_phase.py tests/utils/test_verify_cpm_consistency.py -v
Critério de aceite: o passo 2 sai PASS numa árvore recém-gerada, sem edição manual — provando que B1–B6 estão fechados na origem.

Fora de escopo
React, Vue e Blazor sofrem do mesmo padrão (spec em prosa + gate não-wired), mas ficam fora desta entrega. O dispatch em _run_stack_checks já é desenhado para recebê-los depois sem refatoração.