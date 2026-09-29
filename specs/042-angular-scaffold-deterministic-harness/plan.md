# Plan — Spec 042: Scaffold Angular determinístico com harness de validação

## Constitution Check

- **Article I (Configuration-Driven)** — as versões do Angular e das dependências saem do
  corpo do spec e passam para `src/shared/templates/angular-scaffold/versions.yaml`,
  indexadas pelo major resolvido de `project-config.yaml → tobe_stack.frontend_version`.
  Major não mapeado reprova com `ERROR` explícito; o gerador **nunca adivinha versão**.
- **Article II / XI** — nenhum agente novo e nenhuma frontmatter alterada. A entrega é de
  scripts determinísticos mais a reescrita de um spec de scaffold. Não há SKILL.md a criar.
- **Article III** — o gate da F4S continua obrigatório e ganha um sub-gate por stack,
  executado **antes** do build.
- **Article V** — spec, plan, tasks, mensagens de log e o corpo do `angular-scaffold.md`
  permanecem em pt-BR.
- **Article VI** — cenários BDD nominal, de borda e de gate escritos em `spec.md` antes da
  implementação.
- **Article VIII** — `GENERATION_LOG.md` e o estado de retomada seguem sendo gravados pelo
  `f4s_phase_runner`; o verificador acrescenta seu próprio log em `.artifacts/` sem
  reescrever os artefatos existentes.
- **Article X** — entrada em `CHANGELOG.md`. Nenhum contrato de agente muda, logo não há
  bump de versão de agente.
- **Somente stdlib** — o repositório não tem `requirements.txt` nem `pyproject.toml`;
  `pyyaml` é importado defensivamente em `verify_scaffold.py` e `f4s_scaffold_injector.py`.
  Os dois scripts novos seguem a mesma regra: nenhuma dependência nova, nada de `jinja2`.

## Architecture

O scaffold deixa de ser um artefato interpretado e passa a ser um artefato **renderizado**.
O LLM sai do caminho crítico da compilação e só atua depois que o gate passou.

```text
project-config.yaml            architecture-blueprint.md
  tobe_stack.frontend_version    bounded contexts
            |                            |
            +--------------+-------------+
                           v
          f4s_angular_scaffold.py          <-- NOVO: gerador determinístico
                  |  renderiza %%token%% sobre
                  |  src/shared/templates/angular-scaffold/**
                  v
          outputs/tobe/source-code/angular/     <-- app_root == git repo root == build cwd
                  |
                  v
          verify_angular_app.py            <-- NOVO: install -> build -> boot -> health
                  |
            PASS  |  FAIL
                  |     \
                  v      +--> remediação (sem commit)
          commit inicial "feat(scaffold): angular workspace compilando e validado"
                  |
                  v
          codegen de features por BC (agente LLM)  <-- só começa aqui
```

Ponto de encaixe na esteira, em `f4s_phase_runner.py`:

```text
_run_scaffold_path_check          (já existe, genérico)
        |
        v
_run_stack_checks                 [C1] generaliza `_run_nuget_checks`
        |     dotnet          -> verify_nuget_packages + verify_cpm_consistency
        |     angular/react/  -> verify_scaffold --manifest <stack>
        |     blazor             (barato: só existência de arquivo)
        |     demais          -> nenhum check; o gate é aditivo
        v
run_build                         [C2] STACK_VERIFIERS redireciona por stack
              angular -> verify_angular_app --root . --json
              demais  -> DEFAULT_COMMANDS como antes
```

A divisão importa: o pré-gate confere **estrutura** e é barato; a compilação de verdade
acontece uma única vez, como o próprio comando de build. Invocar o harness nos dois
pontos significaria dois `npm ci` e dois `ng build` por feature.

## Decisões de projeto

### D1 — Templates versionados, não `ng new`

Considerado invocar o Angular CLI oficial (`npx @angular/cli@X new`) para obter uma base
garantidamente compilável. Descartado: exige rede no momento da geração, o output varia
com a versão do CLI, e a esteira precisa ser reproduzível offline. Templates versionados
custam manutenção a cada major do Angular, mas o `versions.yaml` concentra essa manutenção
num só arquivo e o gate de compilação a detecta imediatamente.

### D2 — Delimitador `%%token%%`

Duas alternativas foram descartadas:

- **`string.Template`** usa `$` como delimitador, e os templates contêm TypeScript com
  template literals (`${x}`) e SCSS com variáveis `$nome`. A renderização quebraria ou
  exigiria escapar o código todo.
- **Chave dupla (`{{token}}`)** colide com a interpolação do Angular. `app.component.ts`
  contém literalmente `<h1>{{ title }}</h1>`, que o renderizador tentaria substituir — e
  a verificação de "token remanescente" acusaria falso positivo em todo template com
  interpolação.

`%%token%%` não aparece em nenhuma sintaxe de TypeScript, HTML de Angular, SCSS ou JSON,
o que torna a checagem de token não resolvido confiável.

### D3 — O `app_root` é a raiz do repo git

`f4s_phase_runner.py:390` já define `repo_root = source-code/{target_stack}` e é ali que o
`git_init` e o build acontecem. O projeto real, porém, foi escrito em
`source-code/frontend/apps-login-spa/` — duas pastas abaixo, deixando o build num diretório
sem `package.json`. O gerador coloca o `angular.json` na raiz do repo, unificando
`app_root == git repo root == build cwd`.

O verificador, ainda assim, resolve o `app_root` procurando o `angular.json` na raiz e até
dois níveis abaixo, para continuar funcionando sobre árvores legadas.

### D4 — `npm install` na primeira execução, `npm ci` nas seguintes

Requisito explícito do usuário e correção da causa raiz 5: `npm ci` exige lockfile e falha
num scaffold recém-gerado. A fase install escolhe pela presença do `package-lock.json`.
O lockfile gerado entra no commit inicial, então da segunda execução em diante o install
volta a ser reprodutível — atendendo ao requisito sem abrir mão do determinismo.

### D5 — Porte em Python, não tradução do `.sh`

O `verify-angular.sh` de referência usa `lsof`, `trap`, `/tmp` e process substitution.
A plataforma alvo é Windows. Três substituições, todas com ganho próprio:

| `.sh` | Python | Ganho |
|---|---|---|
| `lsof -i :PORT` + falha se ocupada | `bind` na porta 0 | elimina a classe de falha "porta ocupada" |
| `npx http-server` | `http.server` da stdlib | sem download extra, sem rede além do install |
| `trap cleanup EXIT INT TERM` | `try/finally` + `atexit` | shutdown garantido e portável |

### D6 — Os placeholders por BC são componentes reais

`app.routes.ts` declara rotas lazy por bounded context. Uma rota `loadComponent` apontando
para um arquivo inexistente é erro de compilação. Cada BC portanto recebe um componente
mínimo porém real — com `ChangeDetectionStrategy.OnPush` e com todos os pipes que usa
declarados no `imports`, fechando B3 por construção.

## Semântica de falha

| Situação | Comportamento |
|---|---|
| Major do Angular não mapeado em `versions.yaml` | `ERROR`, nenhum arquivo escrito |
| Arquivo já existe e não há `--force` | preservado, contabilizado em `files_skipped` |
| Fase do verificador falha | exit code próprio da fase (10/20/30/40/50); **sem commit** |
| Servidor morre durante o boot | reportado como fase boot, sem esperar o timeout inteiro |
| `verify_scaffold` acusa `blocking_missing > 0` | `run_build` não é invocado; passo entra em remediação |

## Trabalho futuro (fora do escopo desta spec)

- Estender `_run_stack_checks` para React, Vue e Blazor, que têm o mesmo padrão de spec em
  prosa com gate desconectado. O dispatch já nasce preparado.
- Um `verify_angular_config.py` para defeitos de *conteúdo* em `angular.json` (B4/B5/B6)
  sobre árvores que o LLM editou depois do scaffold. Nesta spec esses defeitos são
  fechados na origem pelos templates, e o harness os detectaria de qualquer forma na fase
  health — mas um verificador dedicado daria diagnóstico mais preciso.
