# Changelog

## [Unreleased] — 2026-08-21

### ✨ Added — Scaffold .NET determinístico com harness de validação (spec 044)

O scaffold .NET deixa de depender de interpretação de uma receita CLI pelo agente. O
novo `f4s_dotnet_scaffold.py` recebe do agente o prefixo da solution, TFM, SDK e bounded
contexts já resolvidos, consulta os templates oficiais disponíveis no SDK e cria a
solution Clean Architecture por `dotnet new`, `dotnet sln` e `dotnet add reference`.

- **`src/shared/templates/dotnet-scaffold/versions.yaml`** concentra os SDKs suportados
  por TFM. Versão não mapeada reprova antes de escrever a árvore.
- **CPM por construção**: versões emitidas por `webapi` e `xunit` são movidas para
  `Directory.Packages.props`; os `PackageReference` gerados ficam sem `Version`.
- **`verify_dotnet_solution.py`** é o novo gate `structure -> restore -> build -> test`.
  Ele combina o manifest, verificação CPM e duplicidade de referências NuGet antes de
  executar a CLI.
- **F4S** delega o build .NET ao harness e executa o manifest .NET como pré-gate.
  O manifest anterior descrevia caminhos incompatíveis com o scaffold atual e foi
  substituído pela topologia `SharedKernel + {BC}/{Domain,Application,Infrastructure,Api}`.
- **`dotnet-scaffold.md`** agora é um contrato operacional: o agente faz o pre-flight,
  fornece parâmetros explícitos e orquestra os dois scripts, sem escrever arquivos de
  template manualmente.

### ✨ Added — Scaffold Angular determinístico com harness de validação (spec 042)

O scaffold Angular deixa de ser gerado por um agente LLM interpretando prosa e passa a ser
**renderizado de templates versionados**. Motivo: o único projeto produzido pela versão
anterior não compilava, com seis defeitos simultâneos — `tsconfig.app.json` e
`tsconfig.spec.json` referenciados em `angular.json` mas nunca gerados, `tsconfig.json` sem
`files`, pipe `number` usado sem `DecimalPipe` no `imports`, `serve` sem `buildTarget`,
`polyfills: ["zone.js"]` ausente e `configurations.production` sem `fileReplacements`.

- **`src/shared/templates/angular-scaffold/`** — árvore de templates com `versions.yaml`
  mapeando major do Angular (17–20) para versões exatas de dependência. Major não mapeado
  reprova com `ERROR`; o gerador nunca adivinha versão (Article I).
- **`src/shared/tools/f4s_angular_scaffold.py`** — gerador determinístico e idempotente.
  Deriva bounded contexts do `architecture-blueprint.md` (com escape hatch `--bcs`) e
  preserva arquivos existentes salvo `--force`.
- **`src/shared/utils/verify_angular_app.py`** — gate `install → build → boot → health`.
  Porte do `verify-angular.sh` para Python, portável no Windows: porta efêmera em vez de
  `lsof`, `http.server` da stdlib em vez de `npx http-server`, `try/finally` em vez de `trap`.
  A fase health captura defeitos que passam no `ng build` e só quebram no browser (`NG0908`).

### 🔧 Changed

- **`f4s_phase_runner.py`** — `_run_nuget_checks` vira `_run_stack_checks`, com dispatch por
  stack: .NET mantém NuGet+CPM; Angular/React/Blazor ganham o gate de manifest. O commit
  inicial passa a ocorrer **depois** de gerar e validar o scaffold
  (`ensure_repo → gerar → validar → commit`), e não mais num diretório vazio — o primeiro
  ponto de retorno do repositório agora é uma estrutura comprovadamente compilando.
- **`f4s_build_runner.py`** — `angular` deixa de usar `npm ci && npm run build` e delega ao
  verificador. `react`/`vue` passam a `npm install`: `npm ci` exige lockfile e falhava num
  scaffold recém-gerado.
- **`angular-scaffold-manifest.yaml`** (v2.0.0) — resolve a contradição em que o spec mandava
  gerar `styles.css` enquanto o manifest exigia `styles.scss` como `blocking`. `.gitignore`,
  `tsconfig.spec.json` e `src/favicon.ico` passam a `blocking`.
- **`angular-scaffold.md`** — reescrito como contrato do gerador, com bloco `⛔` de invariantes
  que o codegen de features não pode quebrar.

## [Unreleased] — 2026-08-21

### Novo — execução de um agente avulso pelo runner (spec 043)

- `pipeline_runner 19.py` ganha `--agent ID -p PROJETO`: despacha UM agente, sem
  nenhum prompt. Rodar sem argumentos continua idêntico — `_parse_cli([])`
  devolve tudo `None`/`False`, e há teste que trava isso.
- Flags: `--agent`, `-p/--project`, `--phase` (só para desempatar agente
  ambíguo), `--trigger`, `--feature`, `--model`, `--headroom`, `--force-single`,
  `--dry-run`, `--list-agents`, `--json`.
- `src/shared/tools/runner_agent_cli.py` (novo): resolução em três tiers —
  esteira do runner, `agent_registry`, e erro com sugestão por similaridade.
  Módulo importável, sem `msvcrt`; 33 dos 51 testes rodam por import direto.
- **A fase vem da esteira do runner, nunca do `ava-pipeline.yaml`.** Os
  namespaces divergem (`ava-summary` é `S1`/`S4` no runner e `F8a`/`F8c`/`F8d`
  no YAML) e `run_step` faz curto-circuito por string exata de fase. Resolver
  pelo YAML pularia o builder determinístico do Summary e queimaria 128k tokens
  para produzir o que um script Python produz de graça.
- Agente com fan-out (F3S por feature, F4 por task) **recusa** o despacho avulso
  e lista os escopos disponíveis; `--force-single` assume o risco
  explicitamente. Despachá-los como passo único já gerou 26 artefatos numa
  resposta, com o contrato de seis agentes violado.
- Insumo obrigatório ausente **recusa** em vez de degradar — divergência
  deliberada da esteira, onde `_degrade_phase` existe para não travar as fases
  sucessoras. No despacho avulso não há sucessora.
- O caminho novo **não grava** `runner-state.json`, `pipeline-status.html` nem o
  relatório de remediação: um estado com um passo só corromperia a retomada de
  um run real. Teste conta as chamadas e exige zero.

### Corrigido — `load_skill` carregava o agente errado

- `load_skill` ganha precedência `0.5`: quando o chamador resolveu o agente pelo
  registry, lê a spec canônica direto. A heurística de substring continua para o
  modo interativo e os passos expandidos.
- Verificado: sem isso, `ava-tobe-migration-plan` carregava
  `summary/utils/node_modules/playwright-core/.../references/migration.md` — doc
  do Playwright, 4.736 chars — em vez da spec real de 70.765. Os 19 agentes da
  esteira não eram afetados; o defeito só mordia fora dela.

### Corrigido — um BOM UTF-8 apagava um agente do catálogo

- `agent_registry.py` passa a ler com `utf-8-sig`. O frontmatter é casado com
  âncora de início absoluto, então 3 bytes de BOM tiravam o arquivo da varredura
  em silêncio.
- Vítima: `ava-summary-remediation`. Sumia de `catalog()`, `load()` e
  `validate()`, o que derrubava `validate_plan` (step F8b), o verificador de
  observabilidade, as regras AT-00x, a geração de wrapper e a resolução de
  `spec_path` — e fazia `ava_pipeline run --all` sair com exit 2.
- Ao voltar ao catálogo, a divergência de versão dele apareceu (frontmatter
  `1.7.0`, bloco de observabilidade `1.4.1`) e foi alinhada. BOM removido: era o
  único arquivo do repositório com ele.

### Novo — gate de aprovação humana da F3S (spec 042)

- `wave6c` (`speckit_compliance_gate.py`) entre a normalização e o gate de saída:
  quando há `verdict: BLOCKED`, achado `critical`/`high`, ou veredito incoerente
  com a regra da spec do agente, o operador vê os achados e decide.
- A decisão fica gravada em `compliance-status.json` com `reviewer`,
  `reviewer_role` e `approved_at` — timestamp de NTP, com a fonte registrada e o
  fallback para relógio local sinalizado. Histórico append-only em
  `approval-log.jsonl`.
- `exit_gate` ganha `kind: human_approval`: `on_fail: block_f4` passa a valer
  para a decisão, não só para a presença do arquivo.
- Assinatura atrelada a um fingerprint (veredito + achados + `graph_checksum`);
  mudou o conteúdo, vira `expired` e o gate pergunta de novo.
- **Modo manual:** "Não" para a esteira — única exceção intencional à política
  "erro nunca trava fase", registrada no cabeçalho do `F3S.yaml` e no comentário
  de `_abort_pipeline`. **Modo automático:** pede Nome/Papel com prazo de 30s e
  segue de qualquer forma, registrando `auto_acknowledged` quando ninguém
  responde. Consequência a considerar: rodando sempre em automático, o gate é
  aviso e auditoria, não barreira.

### Corrigido

- `speckit_compliance_normalize.py` preserva o bloco `approval` ao reescrever o
  artefato; sem isso a wave6b apagava a assinatura da wave6c.
- `artifact_gate_speckit.py` resolvia o import de módulos pela raiz de **dados**
  em vez da raiz de **código** — funcionava por coincidência em produção.
- A orientação de falha do gate de saída distingue decisão pendente de artefato
  ausente: "gere-o" mandava procurar arquivo quando o que faltava era decidir.

## [Unreleased] — 2026-08-17

### Breaking — SpecKit F3S por migration wave

- Substitui as sete specs horizontais por uma spec vertical para cada wave de
  `wave-spec-manifest.json`, derivado de `wave-model.json` com fallback complementar em
  `wave-plan.md`.
- Eleva `plan-graph.json` e `task-fragment.json` para v3, `traceability.json` para v4 e
  `tasks-state.json` para v3.
- Tasks passam a preservar `source_refs[]`, `migration_wave_id` e `migration_wave_order`.
- O compilador deriva dependências entre migration waves e o gate elimina contagens estáticas.

## [2026-08-17] — F3S/F4: dependências explícitas frontend → backend (spec 040)

### Novo — classificação e integração por operação

- Cada arquivo planejado e task declara `task_type: backend|frontend`.
- Endpoints backend produzem `api:{operationId}`; telas frontend consumidoras usam o mesmo token.
- O compilador deriva `backend_dependencies` das predecessoras diretas e expõe a relação no
  `traceability.json`, `tasks.md` e `tasks-state.json`.
- CHK-SK-016 bloqueia classificação inválida ou projeção frontend → backend divergente do DAG.

### Breaking change

`ava-speckit-planning`, `ava-speckit-tasks` e o módulo SpecKit passam a v3.0.0. Novas execuções
devem regenerar `plan-graph.json` e `task-fragment.json`, pois `task_type` agora é obrigatório.
Artefatos existentes em `projects/*/outputs/` não são migrados manualmente.

---

## [2026-08-14] — F3S/F4: grafo determinístico de dependências (spec 040)

### ✨ Novo — compilação global em duas passagens

`ava-speckit-planning` v2 produz `plan-graph.json`; `ava-speckit-tasks` v2 produz um
`task-fragment.json` por feature. Nenhum agente escreve mais no `traceability.json` global.
`speckit_task_compiler.py` consolida os fragmentos, resolve ownership, produtor/consumidor,
ordem no mesmo arquivo e dependências de grupo, e deriva `traceability.json` v2 + `tasks.md`.

### ✨ Novo — validação e scheduler

- `dependency_graph.py`: referências, autorreferência, ciclos, ordem e ondas topológicas.
- CHK-SK-016..018: integridade, aciclicidade e ordem persistida.
- F3S materializa entry gate, compile, ledger init, checks e exit gate como nós executáveis.
- F4 expande uma chamada por task; somente predecessoras `verified` liberam a sucessora.
- `verify_command` roda sem shell e o exit code real é a única porta para `verified`.

### ⚠️ Breaking change

`ava-speckit-planning`, `ava-speckit-tasks` e `ava-speckit-orchestrator` passam a v2. Projetos
com `traceability.json` v1 continuam legíveis com defaults, mas uma nova F3S deve regenerar os
sidecars estruturados antes da F4. Não editar outputs existentes manualmente.

---

## [2026-08-13] — F3S: layout SpecKit, fan-out por DAG e correções do piloto (spec 039)

### 🔧 Changed — layout de saída

`projects/{p}/outputs/speckit/` → **`projects/{p}/outputs/tobe/speckit/`**, e o trio
spec/plan/tasks passa a viver em **uma pasta por feature**, no padrão SpecKit upstream:

```
outputs/tobe/speckit/specs/001-business-rules/{spec,plan,tasks}.md
                          002-api/ · 003-api-map/ · 004-backlog/
                          005-waves/ · 006-test-cases/ · 007-prototype/
```

A numeração é **determinística**, declarada em `pipeline-dag/F3S.yaml` — não descoberta em
runtime como no `create-new-feature.ps1` do upstream. O conjunto de fontes é fechado; número
inventado por LLM quebraria toda referência cruzada a cada execução.

### 🐛 Fixed — a F3S rodava como despacho único

A primeira execução real gerou os 26 artefatos em **uma** resposta: skill de 8KB (só o
`orchestrator-speckit.md`), 92.830 tokens de entrada, 68.170 de saída, 14,7 min. Os seis
corpos de agente — onde moram o schema da rastreabilidade, as 16 seções obrigatórias e os
guardrails — **nunca entraram em contexto**. É o mesmo defeito estrutural da F4 que esta spec
documentou: o motor SDK carrega só o `spec_path` do orquestrador e proíbe tools.

`foreach: {source: "dag"}` expande a fase pelas waves do `F3S.yaml`: **23 despachos**, cada um
com o corpo do agente real, sua fatia de contexto declarada e o parâmetro `feature:` no prompt.
Vale nos dois runners — `ava_pipeline.py` e `pipeline_runner 19.py`, que foi quem executou o
piloto.

### 🐛 Fixed — defeitos de conteúdo que o piloto expôs

| Achado | Correção |
|---|---|
| `traceability.json` com raiz `tasks`, sem `group`/`target_stack`/`target_files` — **o fan-out da F4 não expandia** | `tasks-agent.md` cita o schema como contrato vinculante e explica por que cada campo existe; `CHK-SK-013` valida a estrutura antes dos checks semânticos |
| `task_id` `TASK-BR-001` contra o `T-XXX-000` do schema | padrão explícito no agente, verificado por `CHK-SK-013` |
| 175 tasks emitidas como tabela, não no formato de bloco mandado | **o formato mudou para a realidade**: `traceability.json` é a autoridade legível por máquina, `tasks.md` é a tabela humana derivada. `CHK-SK-015` confere que não divergem. Blocos com 11 campos × 175 tasks não cabem no orçamento de saída |
| `total_tasks: 157` com 175 entradas | proibido declarar contagem não contada; `CHK-SK-005` confere |
| **0 de 7** specs com as 6 seções do readiness-gate C2 | bloco literal para copiar nos dois agentes de spec e nos dois templates; `CHK-SK-014` reprova, inclusive heading traduzido |
| `spec-prototype.md` sem nenhum `screen_id` | guardrail explícito: é a chave que `CHK-PROTO-002/003` casam contra o `index.html` |

### 🐛 Fixed — defeitos nas próprias suítes de verificação

| Achado | Correção |
|---|---|
| **CHK-SK-006 e 010 passavam com zero entradas** — um check anti-falso-positivo produzindo falso positivo | sem dados ⇒ reprova. Verificação sem dado não é verificação |
| Chave raiz desconhecida virava `[]` em silêncio | `CHK-SK-013` nomeia a chave encontrada e aponta o schema |
| Parser do `screen-list.md` assumia `## Warnings` antes do H1; o arquivo real tem o H1 primeiro | a tabela é localizada **pelo cabeçalho** (`Screen` + `Status`), que é a regra defensiva do próprio P2C §2.1. Sem isso, 15 telas válidas viravam "nenhuma tela `included`" |
| CHK-PROTO-006 comparava o path sem remover o base path de `servers.url` | 17/17 falsos positivos → 8 divergências reais |

### 🔧 Changed — consumidores

`readiness-gate.md` C2 → `outputs/tobe/speckit/specs/*/spec.md`; os 3 coders apontam para
`specs/007-prototype/` e `specs/{feature}/`; `artifact-map.yaml`, `context.py`,
`task_ledger.py`, `artifact_gate_speckit.py` e a tabela de Output Path Conventions da
constituição acompanham. `PHASE_ARTIFACT_CONTRACT["F3S"]` do runner 19 reflete o layout novo.

### 📋 Piloto

`projects/nopcommerce-02-cli-ava/outputs/tobe/speckit/` recebeu os 26 arquivos migrados, com
conteúdo preservado. O `execution-log.json` ganhou um bloco `migration` marcando o estado como
**PARTIAL — requires regeneration** e listando o que precisa ser regerado e por quê. Regerar:
`ava-pipeline run -p nopcommerce-02-cli-ava --phase F3S`.

---

## [2026-08-13] — Camada de planejamento SpecKit (F3S) + entrega determinística de contexto (spec 039)

### 🐛 Fixed — o defeito que motivou a entrega

`load_context()` — duplicado em `pipeline_runner 19.py` e em `sdk_engine.py` — injetava o
corpo dos **N primeiros** artefatos em ordem alfabética de `sorted(outputs.rglob("*"))`
(N = 60 no runner, 30 no CLI). Como `asis/` precede `tobe/`, **nenhum artefato TO-BE chegava
ao gerador de código**. Medido em `nopcommerce-02-cli-ava`: dos 60 injetados, 30 eram dumps
brutos de AST e 30 eram outros arquivos de `asis/`; `tobe/` contribuía com **zero**.
`prototype/index.html` sequer era elegível — `.html` estava fora da allowlist de sufixos.

Consequência medida na auditoria: protótipo 13%, regras de negócio 17%, testes 7%,
APIs 14%, ADRs 38%, `dotnet build` **FALHA** atrás de um relatório `PASS (Simulated)`.

### ✨ NOVO — `src/shared/tools/context_manifest.py`

Manifesto de contexto por passo. Cada passo declara `inputs.mandatory` e `inputs.advisory`
em `ava-pipeline.yaml`; insumo obrigatório ausente encerra o passo com **exit 2 antes de
qualquer inferência**, nomeando artefato, produtor e caminho esperado. Implementação única,
importada pelos dois runners. Passo sem `inputs:` mantém o comportamento legado byte a byte.

Efeito no passo F4 do projeto auditado: de 624.278 tokens de entrada, nenhum deles TO-BE,
para ~70.000 tokens contendo blueprint, ADRs, OpenAPI, regras de negócio, `screen-list.md`,
`design-tokens.json` e o `index.html` completo.

### ✨ NOVO — módulo `speckit` (fase F3S, 7 agentes)

Entre a F3 (protótipo) e a F4 (codegen): `ava-speckit-orchestrator`,
`ava-speckit-constitution`, `ava-speckit-specification` (um despacho por artefato-fonte),
`ava-speckit-prototype-spec`, `ava-speckit-planning`, `ava-speckit-tasks` e
`ava-speckit-compliance`. Saída em `projects/{p}/outputs/speckit/`. DAG e fatias de contexto
em `src/shared/data/pipeline-dag/F3S.yaml` — fonte única, da qual o gate **deriva** em vez
de espelhar.

### ✨ NOVO — gates determinísticos

- `speckit/utils/artifact_gate_speckit.py` — gate de entrada (`abort_f3s`) e de saída
  (`block_f4`), com os itens lidos do `F3S.yaml`.
- `src/shared/checks/suites/speckit_traceability.py` — CHK-SK-001..012. `CHK-SK-006` reabre
  o arquivo-fonte e procura a âncora declarada: é o que separa rastreabilidade verificável
  da matriz falso-positiva que a auditoria encontrou (15/15 linhas ✅ para classes
  inexistentes).
- `src/shared/checks/suites/prototype_coverage.py` — CHK-PROTO-001..007. É o gate que a
  causa-raiz RC-04 pediu explicitamente: "1 rota por linha do `screen-list.md`" e "tokens
  materializados".

### ✨ NOVO — `src/shared/tools/task_ledger.py` e fan-out da F4

`tasks-state.json` é o razão de progresso da geração de código, e `foreach:` expande a F4 em
um passo por grupo de tasks, cada um despachando o agente coder real da stack — que sob o
motor SDK nunca era carregado. A execução auditada gerou 140 arquivos em **uma** resposta de
82.878 tokens contra um teto de 128.000.

**Agentes nunca escrevem no razão.** O status sobe apenas por exit code real de `verify.ps1`,
gravado pela ferramenta. `record_result` recusa `recorded_by` que pareça um agente. Isso é um
desvio deliberado do padrão de harness para agentes de execução longa, no qual o próprio
agente marca a feature como concluída — aqui, auto-relato de conclusão é exatamente a RC-02
desta esteira.

### 🔧 Changed — contratos de entrada dos agentes coder (**MAJOR bump**)

| Agente | Versão | Mudança |
|---|---|---|
| `ava-stack-angular-frontend` | 3.0.0 → **4.0.0** | `prototype_index`, `prototype_screens`, `design_tokens` de `OPCIONAIS (WARN)` para `CRÍTICOS (HARD STOP)`; constitution/plan/tasks/spec-prototype adicionados como CRÍTICOS |
| `ava-stack-react-frontend` | 2.0.0 → **3.0.0** | idem |
| `ava-stack-dotnet-backend` | 2.2.0 → **3.0.0** | novo Step 0.4 — constitution/plan/tasks como CRÍTICOS |

> **Migração**: projetos gerados antes da F3S existir não têm `outputs/speckit/`. Rode
> `ava-pipeline run -p {projeto} --phase F3S` antes da F4, ou mantenha os coders na versão
> anterior. Na `ava-pipeline.yaml`, os artefatos SpecKit estão declarados como `advisory` no
> passo F4 justamente para não quebrar projetos em andamento.

### 🔧 Changed — outros

- `readiness-gate.md` **C2**: glob repontado de `outputs/tobe/docs/spec-kit/*.md` para
  `outputs/speckit/specs/*.md`, e passa a exigir o gate de saída da F3S em PASS. O critério
  existia desde sempre **sem produtor** — e ainda assim o gate do nopcommerce-02 aprovou com
  92,5% e `spec_kit_approved: true`, para um artefato que não existia.
- `.specify/memory/constitution.md` **v1.4.0 → v1.5.0**: F3S na sequência do Article III e os
  dois gates na tabela de gates obrigatórios. Nenhuma fase renumerada — o sufixo `F3S` foi
  escolhido para não mexer em F4..F8, que aparecem em prosa de agente e artefatos entregues.
- `agent_registry.py` e `pipeline_observer.py`: `F3S` em `PHASE_BY_MODULE`, `PHASE_ORDER` e
  `PHASE_NAMES`, com teste travando a coerência entre os dois arquivos.
- `src/shared/checks/context.py`: `html`/`html_path` viraram propriedades preguiçosas — os
  gates da F3S rodam muito antes de existir Summary HTML.
- `src/shared/checks/cli.py`: guarda UTF-8 no Windows, como nos demais tools.

### 📋 Spec

`specs/039-speckit-planning-layer/` · dossiê de arquitetura em
`docs/plan/speckit-to-be-tak.md` · evidência primária em
`projects/nopcommerce-02-cli-ava/outputs/audit/auditoria-codigo-gerado.md`.
=======
## [2026-08-18] — ava-summary-validate (1.4.2→1.5.0) + ava-summary-remediation (1.5.0→1.6.0): Deep Item Audit C12 + Remediation Loop (spec 041)

### ⚠️ BREAKING CHANGE — `validation-report.json` ID rename (C12.x → C11.39-41)

The three checks previously registered as `C12.1`, `C12.2`, `C12.3` in
`validation-report.json` have been **renumbered** to `C11.39`, `C11.40`, `C11.41`
to free the `C12` namespace for the new **Deep Item Audit** category.

**Migration guide for consumers of `validation-report.json`**:

| Old ID | New ID | Check description |
|--------|--------|-------------------|
| `C12.1` | `C11.39` | No `[INCOMPLETE]` placeholder in HTML |
| `C12.2` | `C11.40` | No unresolved `[ARTIFACT-MISSING]` marker in HTML |
| `C12.3` | `C11.41` | No `<table>` with `<thead>` but zero tbody rows (structural) |

Any CI pipeline, dashboard, or tooling that filters `validation-report.json` by
`id: "C12.1"`, `"C12.2"`, or `"C12.3"` **must be updated** to use the new IDs.
The check logic (Python functions `_c12_1`, `_c12_2`, `_c12_3`) is unchanged;
only the catalog registration IDs differ.

> **Rationale**: `deep-audit-report.json` is a **new** artifact with no pre-existing
> consumers, so this rename is MINOR (no clients of the new schema exist yet).

### ✨ NOVO — `deep-audit-report.json` (schema v1.0)

- Emitido por `validate_summary.py --deep` (nova flag, 100% retrocompatível).
- Auditoria item a item de cada seção/card/tabela/diagrama (F1–F8): 7 sub-regras C12.1–C12.7.
- Campos: `schema_version`, `generated_at`, `project`, `html_path`, `summary.{critical,high,medium,low,promotable}`, `findings[]` com `id`, `severity`, `phase`, `section`, `agent_responsible`, `artifact_path`, `finding_type`, `detail`, `root_cause`, `auto_correctable`, `suggested_fix`.
- `summary.promotable = true` quando `critical == 0 and high == 0`.

### ✨ NOVO — `--deep` flag em `validate_summary.py`

- `python validate_summary.py --project X --deep` ativa auditoria profunda C12.1–C12.7.
- Sem `--deep`: comportamento C1–C11 + C13.x permanece **absolutamente inalterado**.
- Exit code semantics idênticos com e sem a flag.

### ✨ NOVO — `run_remediation_loop()` em `remediate_summary.py`

- Loop estruturado CLEAN/PARTIAL/BLOCKED com `MAX_REMEDIATION_ATTEMPTS` configurável.
- Consome `deep-audit-report.json`; despacha correções via `_dispatch_correction()`.
- Bifurcação transiente (timeout/exit≠0) vs. estrutural (agente não registrado em module.yaml).
- Falha estrutural **não consome tentativa**; loop continua com findings restantes.
- PARTIAL aplica-se em qualquer iteração onde não há CRITICAL/HIGH — loop não continua.

### ✨ NOVO — `--force-promote` em `remediate_summary.py`

- Entrega o HTML mesmo com `final_status: BLOCKED`.
- Seta `"forced": true` no `remediation-report.json` (campo sempre presente em schema v2.0).
- Exit code permanece `1`; emite header `[WARN] FORCED PROMOTION` com lista de findings.

### 🔧 Changed — `remediation-report.json` schema v2.0

- Novos campos: `forced` (bool, default `false`), `deep_audit_summary`, `mermaid_gate`.
- `schema_version: "2.0"` adicionado.

### 🔧 Changed — `artifact-map.yaml` (v1.0.1 → v1.0.2)

- Fase `f3_prototype` adicionada (gap confirmado em 2026-08-18; phase adicionada em Constitution v1.4.0).
- Fase `f8_summary` adicionada (outputs do Summary: HTML, validation-report, deep-audit-report, remediation-report).

### 🔧 Changed — `ava-summary-validate` (v1.4.2 → v1.5.0)

- Description atualizada (PT-BR) para refletir `--deep`, `deep_audit_json` e auditoria item a item.
- `allowed-tools` inclui `Bash` (necessário para execução do script com a flag).

### 🔧 Changed — `ava-summary-remediation` (v1.5.0 → v1.6.0)

- Description atualizada (PT-BR) para refletir `--force-promote` e loop estruturado CLEAN/PARTIAL/BLOCKED.

### 🔧 Changed — `ava-summary` — hook de auto-trigger `--deep`

- Após `build_summary_comprehensive.py` concluir, invoca `validate_summary.py --deep`.
- Se `deep-audit-report.json.summary.promotable == false`, invoca `remediate_summary.py`.
- Sem `--deep`: comportamento inalterado para retrocompatibilidade.

### 🔧 Changed — `summary` module (v1.4.1 → v1.5.0)

- Bump de versão refletindo Deep Item Audit (C12) + Remediation Loop.

---

## [2026-08-17] — ava-summary / ava-summary-remediation: Mermaid Playwright Auto-Fix Gate (spec 040)

### ✨ NOVO — `mermaid_playwright_gate.py` + `gate_mermaid_probe.js`

- **Phase G** em `build_summary_comprehensive.py` e **Phase 3.5** em `remediate_summary.py`.
- Renderiza todos os diagramas Mermaid do Summary HTML em Chromium headless via Playwright.
- Aplica correções automáticas guiadas por 14 guardrails (GR-001..GR-014): `graph` → `flowchart`, direção, labels multi-linha, `subgraph` fechamento, caracteres proibidos, curly quotes, declaração de nós, nesting, C4 macros, sequence participant sanitização, state syntax, placeholder para diagrama vazio, separação de blocos ER (GR-013), modificador PK_FK inválido → PK (GR-014).
- Emite `mermaid-validation-report.json` + `.md` com status (`PASS`, `PASS_WITH_FIXES`, `FAIL_UNRESOLVED`, `SKIPPED`, `DISABLED`), counters, e registro de cada fix.
- Flags `--skip-mermaid-gate`, `--mermaid-guardrails-path`, `--mermaid-gate-max-attempts`.

### 🔧 Changed — `ava-summary` (v2.1.0 → v2.2.0)

- Description atualizada para mencionar o gate de validação Playwright (Phase G).
- Frontmatter corrigido para localização correta no topo do arquivo.

### 🔧 Changed — `ava-summary-remediation` (v1.4.2 → v1.5.0)

- Description atualizada para mencionar o gate Playwright (Phase 3.5) e as regras GR-001..GR-012.
- Seção `mermaid_gate` adicionada ao `remediation-report.json`.

### 🔧 Changed — `ava-summary-validate` (v1.4.1 → v1.4.2)

- Check **C13.2** (Mermaid Gate) adicionado — consome `mermaid-validation-report.json` e bloqueia publicação se `overall_status == FAIL`.
- Frontmatter corrigido para localização correta no topo do arquivo.

### 🔧 Changed — `render_blueprint_compatibility.py`

- Função `discover_browser_executable()` exportada para reuso pelo gate Mermaid.

### 🔧 Changed — `summary` module (v1.3.0 → v1.4.0)

- Bump de versão refletindo a adição do Mermaid Playwright Auto-Fix Quality Gate.

### 🐛 Correção — Python 3.14 `dataclass` / `importlib.util`

- `remediate_summary.py` e `mermaid_playwright_gate.py` pré-registram o módulo em `sys.modules` antes de `exec_module()` para evitar `NoneType' object has no attribute '__dict__'` ao importar `@dataclass` decorated classes dinamicamente.
>>>>>>> feat/apps-agents-pre-release

---

## [2026-08-10] — ava-prototype: ingestão de design do cliente (spec 039)

### 🔧 Changed — `ava-prototype` (v1.2.0 → v1.3.0)

- Consome fontes de design existentes do projeto por prioridade determinística.
- Aplica tokens client com precedência por campo e registra gaps de mapeamento.
- Adiciona `design-input-traceability.json` com fallback, severidade e integridade.
- Mantém `business-rules.md` como bloqueio obrigatório e não gera arquivos `.fig`.

## [2026-08-06] — ava-qa-orchestrator: FQ sequencial antes de ET+EC (spec 037)

### 🔧 Changed — `ava-qa-orchestrator` (v2.1.0 → v2.1.1)

- **Routing — Trigger QE (step 9)**: `ET + EC + FQ` em paralelo → dividido em 4 sub-passos:
  step 9 despacha **apenas** `ava-qa-bridge-fastqa-tobe` (FQ) sequencialmente; step 9a é o
  FQ COMPLETION GATE (conteúdo idêntico ao antigo 9c); step 9b despacha
  `ava-qa-exploratory` + `ava-qa-evidence-capture` em paralelo, independentemente do
  resultado de FQ; step 9c é o ET VERIFICATION GATE (conteúdo idêntico ao antigo 9b).
  Nenhuma instrução de conteúdo foi reescrita — apenas reordenada.
- **Agent Team QA**: linha do `ava-qa-bridge-fastqa-tobe` (Momento 2) atualizada de
  "paralelo a ET+EC" para "sequencial, imediatamente antes de ET+EC".
- **Triggers / Menu e tabela de cobertura**: ordem textual do DAG do `QE` atualizada de
  `...FT→ET→EC→FQ` para `...FT→FQ→ET→EC` (3 ocorrências).
- **4b TS COMPLETION GATE**: referência cruzada a `ava-qa-evidence-capture` atualizada de
  "(passo 9)" para "(passo 9b)".
- Passos 10 (PT) e 11 (RS) permanecem inalterados — EC continua sendo despachado (em 9b)
  antes deles.
- Spec: `specs/037-qa-fq-sequential-before-et-ec/`.

---

## [2026-08-05] — CLI de orquestração da esteira (`ava-pipeline`)

### ✨ NOVO — `src/shared/tools/ava_pipeline.py`

Substitui o `pipeline_runner.py` interativo da raiz por um CLI com subcomandos
`run` / `list` / `config` / `doctor`, `--dry-run` de custo zero, rota pelo proxy
Headroom e exit codes (`0` ok · `1` etapa falhou · `2` erro de configuração ·
`130` abortado).

- **Fonte única de configuração** — `src/shared/data/ava-pipeline.yaml` concentra
  modelo, endpoint, chave, proxy, orçamento de contexto e a **ordem da esteira**.
  Precedência igual à do `headroom.yaml`: flags do CLI > env (`AVA_PIPELINE_*` /
  `AVA_FOUNDRY_*`) > `project-config.yaml` → bloco `pipeline:` > YAML > fallback.
  `pipeline_config.py` nunca levanta: YAML ilegível ou env malformada degradam
  com aviso e mantêm a camada de baixo (IV3).
- **Parametrização pedida** — `-p/--project`, `--phase` (repetível, aceita etapa
  `F2b` ou grupo `F2`), `--all`, `--model` (com aliases), `--agent` (da esteira ou
  avulso do registry), mais `--engine`, `--from`, `--via-proxy`/`--no-proxy`,
  `--yes`, `--dry-run`, `--json`.
- **Headroom como proxy** — a URL vem de `headroom_config.py --proxy-url`, nunca
  hardcoded, e o liveness de `headroom_tool.py proxy status`, usando o venv
  isolado da tool. `mode: auto` degrada para o endpoint direto **com aviso alto**;
  `--via-proxy` aborta em vez de rodar sem compressão. A rota é a única diferença
  entre os dois caminhos: o SDK aponta para `http://host:port`, sem sufixo de path.
- **Dois motores** — `--engine sdk` (SDK Anthropic, artefatos em blocos
  `<!-- FILE: … -->`) e `--engine copilot` (delega ao `agent_runner.py`, com gate
  de artefato e telemetria). O motor `copilot` avisa quando falta o DAG da fase
  (só `F1.yaml` existe) e quando o trigger não é propagável, em vez de fingir
  cobertura.
- **Fim da heurística de spec** — o caminho do `.md` de cada agente vem do
  `agent_registry`. O runner antigo procurava por substring em `rglob("*.md")` e
  escolhia o maior candidato, podendo carregar o agente errado em silêncio.
- **`WORKSPACE` hardcoded removido** — apontava para outro checkout
  (`c:\_info\Projetos\Hub\SRC_Torre_Apps_31_07`), então o script não rodava neste
  repo. O caminho agora vem de `__file__`. O import morto de `requests` saiu.
- **`pipeline_runner.py` virou shim** — avisa da depreciação, preserva o seletor
  interativo de projeto e delega ao CLI.
- **Testes** — `tests/tools/test_pipeline_plan.py` trava a ordem das 12 etapas e
  o par planejar/executar dos dois orquestradores de dois momentos;
  `tests/tools/test_pipeline_config.py` trava a precedência e proíbe endpoint,
  modelo e porta hardcoded (checagem por AST, ignorando comentários).
- **Novos**: `ava-pipeline.bat` (atalho de raiz) e
  `src/shared/tools/requirements-pipeline.txt` (documenta a exceção ao
  stdlib-only, contida em dois módulos).

### 🐛 Correção de ordem — F6 usa `QE`, não `TPT`

A tabela `PIPELINE` do runner antigo repetia `TPT` na etapa de execução do QA,
o defeito descrito na entrada abaixo. A esteira do CLI usa `TPT` na F2c
(planejamento) e **`QE` na F6** (execução), espelhando o par `DP`/`DE` do DevOps.
A ordem F4 → F5 (`DE`) → F6 satisfaz o Pre-condition Gate do `QE`.

> ⚠️ As etapas da esteira (`F1`…`F8d`) são **ordem de execução**, não os módulos
> do `agent_registry`. Aqui F5 é DevOps Execute e F6 é QA Execute, enquanto no
> registry F5 é o módulo `qa-agents` e F6 é `devops-agents`. A divergência é
> intencional; `validate_plan` nunca compara os dois eixos.

### ⚠️ Não alterado

`copilot-cli-headroom.bat` e `copilot-cli-v1.bat` seguem intactos (restrição CA02
de `specs/033`).

---

## [2026-08-05] — QA Orchestrator em dois momentos (035-qa-orchestrator-two-moments)

### 💥 MAJOR — `ava-qa-orchestrator` v1.3.0 → v2.0.0

- **A esteira QA passa a ter dois momentos explícitos**, espelhando o padrão que o
  `ava-devops-orchestrator` já adota (`DP` Plano / `DE` Execução). **Momento 1 = `TPT`**
  (Test Plan TO-BE, após F2), **Momento 2 = `QE`** (novo — Quality Execute, após a esteira de
  código F4 Stack e a esteira DevOps Momento 2 `DE`).
- **Novo trigger `QE`** com `## Pre-condition Gate (QE)` de 4 passos bloqueantes: F2 concluída
  (`bounded-context-map.md` com ≥1 BC), planejamento `TPT` concluído (`test-plan.md` +
  `test-cases.md`), esteira de código concluída (sentinela `source-code/README.md` + backend ou
  frontend), e DevOps Momento 2 concluído (`infra/`, `iac/ci/`, `iac/cd/azure-pipelines-cd.yml`).
  Um Passo 4b não-bloqueante avisa quando `parity-test-report.md` está ausente.
- **🐛 Corrige o bug em que `RS` nunca executava.** O trigger `RS` consome
  `outputs/tobe/parity-test-report.md`, produzido pelo `ava-devops-compare-version` — agente #11
  da esteira DevOps Momento 2. Como o QA rodava em F5 e o `DE` em F6, o Passo T2 caía
  permanentemente em `RS | SKIPPED (parity-test-report.md ausente)`. Com o gate do `QE`, o
  artefato existe quando `RS` é alcançado.
- **`QS` está DEPRECADO** — vira alias que emite aviso e delega integralmente a
  §Routing — Trigger QE, incluindo o gate. Mantido por compatibilidade com o
  `master-orchestrator.md` (Step 5.1). O `## Pre-condition Gate (QS)` foi marcado como
  SUPERSEDIDO, preservado apenas como fonte do critério de detecção de bounded contexts.
- **Criadas `## Routing — Trigger PT` e `## Routing — Trigger RS`** — eram referências pendentes
  citadas 3× no arquivo sem seção correspondente, em caminho de execução ativo. `PT` é
  documentado como **verificação de disponibilidade, não dispatch**: não existe agente de parity
  test no módulo QA, o executor real é o `ava-devops-compare-version`. `RS` despacha
  `ava-qa-script-generator` em `mode: regression`.
- **`PT` e `RS` adicionados ao `## Triggers / Menu`**, de onde estavam ausentes apesar de
  aparecerem na tabela "Resumo de cobertura por trigger".
- **`FTM` entra no escopo do `QE`** (passo 3b, após `BM`, condicional ao `behavior-catalog.json`).
  Não pertence ao `TPT`: produz `outputs/qa/functional-test-matrix.md`, enquanto o `TPT` produz
  `outputs/tobe/tests/functional-test-matrix.md`.
- **`FQ` incluído no invariante terminal PT→RS**, corrigindo divergência entre a nota do menu, a
  tabela de cobertura e a lista do §Terminal Mandatory Steps. `DBI`, `CT` e `FT` também ganharam
  linha na tabela de cobertura.
- **Novo sinal `↳ ✅ [ava-qa-orchestrator] QE DEFERRED`** emitido junto à mensagem de bloqueio.
  Sem ele, o `master-orchestrator.md` (Step 5.2) executaria 4 retentativas idênticas antes de
  registrar WARN, já que a causa do bloqueio é a ordem das fases e não uma falha transitória.
- `## Output Contract` **inalterado** — os 12 artefatos permanecem idênticos; nenhum parser
  downstream é afetado. `module.yaml` e `SKILL.md` não requerem alteração.

> ⚠️ **Consequência assumida** (ver `specs/035-qa-orchestrator-two-moments/spec.md` §Exclusions):
> o `master-orchestrator.md` Step 5.1 ainda despacha `QS` em F5, antes do `DE`. O gate deferirá
> e o master avançará para F6 com WARN (comportamento já previsto — QA é não-bloqueante lá). Na
> esteira automática (`FP`), a execução QA passa a exigir invocação manual de `QE` após F6.
> **Follow-up**: mover o dispatch QA no master para depois do Step 6 passando `trigger: QE`.

## [2026-08-04] — Conversão Protótipo → Componente Frontend (034-prototype-to-component-conversion)

### 💥 MAJOR — `ava-stack-angular-frontend` v2.0.0 → v3.0.0

- **A unidade de geração passa a ser a TELA do protótipo, não o bounded context.** Os Steps
  7.3–7.6 geram uma página por tela `included` em `src/app/{bc}/pages/{screen_id}/`, com
  template escolhido pelo arquétipo (`list` / `form` / `list-detail` / `dashboard` / `content`).
  O template genérico `<ul>@for … <li>{{ item.id }}</li></ul>` foi **eliminado** e passa a ser
  proibido por assertion.
- **`prototype_screens` e `design_tokens` deixam de ser CRÍTICOS/HARD STOP** e viram OPCIONAIS
  com degradação por WARN. O `Guardrail G-DT` ganha cadeia de fallback
  (`design-tokens.json` → `:root` do `index.html` → defaults). Motivo: a Fase 3 é
  não-bloqueante na esteira (`master-orchestrator.md`) e o HARD STOP contradizia o orquestrador.
- **Novo `Step 1.2d`** — inventário do protótipo (passes P1–P4), grava
  `prototype-conversion-map.json` com `phase: "planned"` e `expected_artifacts[]`.
- **Novo `Guardrail G-P2C`** — mapeamento de constructs do protótipo → Angular, arquétipos e
  marcador anti-stub.
- **Novos componentes compartilhados**: DS-010 `breadcrumb`, DS-011 `data-table`,
  DS-012 `error-dialog`, DS-013 `help-panel`, `ToastService`, `ConfirmService`.
  DS-002 ganha `severity` e DS-007 ganha `messages` (aditivos, retrocompatíveis).
- **Novo `Step 9.5.6`** — spec por tela convertida, incluindo um `it()` por regra BR-XXXX.
- **Novo `Step 9.8`** — assertion de fidelidade bloqueante (existência + anti-stub + regras de
  negócio), com no máximo 3 iterações de reparo.
- **Novo `Step 9.9`** — build e **execução** dos testes unitários. Necessário porque o
  `ava-stack-build-validator` nunca executou testes: o `coverageThreshold` era configurado e
  jamais exercido. Sem Chrome no ambiente → `TOOLCHAIN_UNAVAILABLE`, reportado e não bloqueante.
- **Handoff** ganha `prototype_fidelity`, `screens_expected`, `screens_converted`,
  `screen_assertion`, `design_tokens_source`, `unit_tests`, `business_rules_status`,
  `api_divergences` e `p2c_warnings`.
- **Correções de conformidade (Constitution Article II)**: removida a chave `date:` do
  frontmatter; `Bash` acrescentado a `allowed-tools` (os Steps 2.17/10.1/11 já o invocavam).
- **Breaking change**: o layout de saída muda de uma página por BC para uma página por tela, e
  os paths passam de `src/app/{bc}/` para `src/app/{bc}/pages/{screen_id}/`.

### 💥 MAJOR — `ava-stack-react-frontend` v1.0.0 → v2.0.0

- **Regressão corrigida**: o agente não tinha nenhuma referência ao protótipo. A
  `specs/008-design-tokens-propagation` §1c já exigia `prototype_screens` + `design_tokens`, e a
  reescrita para v1.0.0 (2026-07-14) os removeu silenciosamente.
- Ganha o protocolo P2C completo (Steps 1.4, 5, 6.5) e as seções de paridade que nunca teve:
  `## Padrões Obrigatórios`, PRE-FLIGHT CHECK, `Guardrail G-DT`, `Guardrail G-P2C-React`,
  consumo de regras de negócio (Step 1.5), contrato de API por BC (Step 1.6), Scaffold Gate,
  `## Consistency Verification Gate`, `## Handoff`, `## Security Compliance Review Gate`,
  `## Accessibility Invariants` e `## Testing Requirements`.
- Conjunto **RX-001..RX-014** de componentes compartilhados substitui os stubs
  `Button`/`Input`/`Table`/`Modal`.
- Step 7 renomeado para **Gate de Qualidade**: install → audit → `tsc --noEmit` →
  `vitest run --coverage` → `vite build`.
- Removida a chave `date:` do frontmatter (Article II).

### ✨ Novos arquivos

- `src/modules/ava-fabric-agents/shared/prototype-conversion-protocol.md` — include
  compartilhado com as partes independentes de framework (parsing, matriz de discrepância,
  schema do `prototype-conversion-map.json`, binding de regras de negócio, junção com contrato
  de API, assertion e códigos `P2C-W001..W009`).
- `src/shared/data/patterns/react/react-patterns-reference.md` — referência vinculante de
  padrões React, contraparte da já existente para Angular.
- `src/shared/data/scaffold-manifests/react-scaffold-manifest.yaml` — não existia; sem ele,
  `verify_scaffold.py --manifest react` falhava com exit 2.

### 🐛 Fixed — `ava-stack-orchestrator`

- `orchestrator-stack.md` chamava `verify_scaffold.py --manifest angular` para o frontend
  **independentemente do framework**, reprovando qualquer projeto React/Vue/Blazor por arquivos
  que ele nunca deveria gerar. Agora o manifesto é resolvido por `{frontend_framework}`, com
  WARNING não bloqueante quando não houver manifesto para a stack.

### 🔧 Changed

- `src/modules/ava-fabric-agents/tech-stack/module.yaml` — versão do módulo 1.4.0 → 1.5.0.
- `docs/agents-catalog.md` — ambos os blocos de `ava-stack-react-frontend` e o de
  `ava-stack-angular-frontend` atualizados.

---

## [2026-07-24] — Screen Flow Batch Protocol + Completude Assertion (029-screen-flow-batch-protocol)

### 💥 MAJOR — `ava-asis-documentation` v2.x → v3.0.0

- **Novo protocolo de geração em lotes por bounded context**: para projetos com > 80 forms, o Screen Flow Mapper agora itera por BC e gera `screen-flow-{bc_slug}.mmd` intermediários em vez de single-pass inline
- **Assertion de completude obrigatória**: após geração, o agente emite `screen-flow-completeness.json` com:
  - `coverage_pct` (N_nodes / N_registry × 100)
  - `status: PASS` se ≥ 80%; `status: FAIL` + `missing_forms[]` se < 80%
  - `retry_count` — máximo 3 retries antes de elevar `human_gate_required = true`
- **REGRA ABSOLUTA anti-inline**: geração inline de mermaid sem invocação de `gen_screen_flow.py` é PROIBIDA. Bypass gera log `[FT-INLINE-GENERATION-DETECTED]` e marca sub-skill como FAILED
- **Script fallback**: se `gen_screen_flow.py` estiver ausente, fallback manual por BC ainda aplica assertion
- **Artefatos novos no Output Contract**:
  - `outputs/asis/docs/screen-flow-*.mmd` (intermediários por BC)
  - `outputs/asis/docs/screen-flow-completeness.json` (assertion JSON)
- **Checklist de readiness gate atualizado**: novo critério C0 — Screen Flow Completude (threshold 80%)
- **Documentação & catálogo atualizados**: `docs/agents-catalog.md`, `docs/full-pipeline-guide.md`, `docs/summary-validator-guide.md` refletem v3.0.0
- **Breaking change**: comportamento de geração muda de single-pass para chunked para projetos > 80 forms; ≤ 80 forms mantém single-pass mas assertion ainda é obrigatória

## [2026-07-27] — QA Orchestrator Decoupling from DevOps Parity/Regression

### 🔄 Changed — `ava-qa-orchestrator` (qa-orchestrator-agent.md)

- **Removed DevOps-coupled terminal workflow `PT → RS`**:
  - Deleted `ava-devops-cd` and `ava-devops-ci` from the orchestrator agent table.
  - Deleted trigger definitions `PT` (Parity Test AS-IS × TO-BE) and `RS` (Regression Suite).
  - Deleted entire **Routing — Trigger PT** section (71 lines): no longer invokes `ava-devops-cd` → `ava-devops-compare-version`, no longer generates `parity-test-report.md` / `wave-approval.md` from the QA orchestrator.
  - Deleted entire **Routing — Trigger RS** section: no longer converts `EQUIVALENT` parity scenarios into xUnit `[Trait("Type", "Regression")]` regression suite, no longer injects `regression-gate` stage into CI pipelines.
- **Updated mandatory-terminal note**: removed `PT → RS são etapas terminais obrigatórias` claim and the `ava-devops-cd (PT)` row from the `qa-master-report.md` summary table.
- **Rationale**: decouples F5 (QA) from F6 (DevOps) parity comparison and CI-gate injection; those responsibilities remain with `@ava-devops-compare-version` and `@ava-devops-ci` invoked directly from the DevOps orchestrator.

---

## [2026-07-25] — Podman Local Runner (029-podman-local-runner)

### ✨ New Agent — `ava-devops-podman-run` v1.0.0 (F6 — devops-agents)

- **`src/modules/ava-fabric-agents/devops-agents/agents/podman-run-agent.md`**: novo agente
  que executa de ponta a ponta o guia `docs/podman-windows-guide.md` — transforma o runbook
  manual em fluxo interativo único.
- **Passo 1 — pré-flight bloqueante**: versão do Windows, virtualização (`HypervisorPresent`),
  WSL instalado, distro em WSL **2**, winget, `podman --version`, `podman compose version`,
  RAM ≥ 8 GB e disco ≥ 20 GB. Falha bloqueante interrompe a execução e imprime a remediação
  exata de cada item (nunca instala nada de forma elevada/silenciosa).
- **Passo 0 — regra "descubra → fallback → pergunte"**: `project_name`, `source_code_path`,
  arquivos compose, serviços, portas, imagens e variáveis `${VAR}` são todos auto-descobertos;
  o usuário só é consultado quando a descoberta falha ou é ambígua.
- **Passo 2** provisiona/inicia a Podman Machine dimensionando disco, RAM e vCPUs a partir dos
  recursos reais do host; **Passo 3** materializa o `.env` a partir do `.env.example` e das
  referências `${VAR}` dos compose files, gerando senhas fortes sem exibi-las.
- **Passo 5/6** sobem a stack em modo detached com polling de saúde limitado (`wait_budget_s`,
  default 300 s) e montam as URLs a partir dos mapeamentos `ports:` — sem portas hardcoded.
- **Passo 7** classifica falhas contra a tabela de troubleshooting do guia (porta ocupada,
  healthcheck do SQL Server, disco/RAM do WSL2, ICU no Alpine, nginx na porta 80, `npm ci`,
  `MSB3202`/`NETSDK1047`, socket do Podman).
- Triggers: `PR` `PC` `PM` `PE` `PU` `PS` `PL` `PD` `PT`.
- Outputs: `podman-preflight.md`, `podman-run-report.md` (ambos em
  `outputs/tobe/iac/containers/`) e `.env` em `outputs/tobe/source-code/`.

### ✨ New File — `.github/skills/ava-devops-podman-run/SKILL.md`

- Skill user-facing que resolve o `PROJECT_NAME` (sem perguntar quando há apenas um projeto)
  e delega ao agente.

### 🔄 Changed — `devops-agents/module.yaml` v1.0.1 → v1.1.0 (MINOR)

- Registrado `ava-devops-podman-run` com `skill` e `depends_on: ava-devops-containerize`.

### 📄 Docs

- `docs/agents-catalog.md`: nova entrada na seção F6.
- SpecKit: `specs/029-podman-local-runner/` (spec, plan, tasks, checklists).

---

## [2026-07-24] — Consolidation of Test Plan Artifacts (029-consolidate-test-plan-artifacts)

### 🔥 Breaking Change — `ava-test-plan-tobe` v3.0.0 → v4.0.0 (MAJOR)

- **Output contract reduced from 15 to 4 artifacts**:
  - ✅ Retained: `test-plan.md`, `traceability-matrix.md`, `automatable-test-cases.md`, `functional-test-matrix.md`
  - ❌ Eliminated: `wave-test-plan.md`, `smoke-tests.md`, `smoke-suite-wave-{N}.md`, `smoke-suite-wave-{N}.yml`, `smoke-suite-wave-{N}.github.yml`, `load-test-plan.md`, `ui-test-plan.md`, `coverage-strategy.md`, `bdd-coverage-per-wave.md`, `security-test-strategy.md`, `coverage-gap-strategy.md`
- **Content absorption strategy**: wave thresholds inline in `test-plan.md` Section 15; security tests reference `security-architecture.md`; smoke suite concepts become inline CI strategy; coverage gap annotations in `functional-test-matrix.md`; load baselines reference `tech-framework-document.md` + `master-report.md`
- **Removed Skills subsections**: Smoke Tests, Cobertura, Performance & Carga, Testes de Tela
- **Removed canonical template sections**: Section 7 (Smoke), Section 8 (Load), Section 14 (Security Test Strategy), Section 16 (Coverage Gap Strategy)
- **Removed execution steps**: Step 5c (smoke suite per wave), Step 6b (load test plan), Step SKW (smoke dispatch block)
- **Removed triggers**: `SKW`, `CG`, `LD`, `UI`, `SS`, `ST`
- **Updated downstream consumers**:
  - `orchestrator-tobe.md`: Fase 6 outputs and Fase 7.8 inputs tables updated to 4 artifacts
  - `summary-agent.md`: Removed `D.coverageGapStrategy` field and parser
  - `build_summary_comprehensive.py`: Removed `_cgs_path` parsing block and JS injection
  - `artifact-map.yaml`: `ava-test-plan-tobe` outputs_map reduced to 4 entries
- **Updated DevOps agents** (eliminated `smoke-suite-wave-{N}.yml` dependency):
  - `cd-agent.md`: Replaced Smoke Suite Integration with inline Post-Deploy Validation from `functional-test-matrix.md`; updated Input/Output contracts; replaced `smokeGateC4` with `postDeployGate`; updated Pre-requisites Checklist
  - `cd-pipeline-generator.md`: Replaced "Per-Wave Smoke Suite Integration" with "Post-Deploy Validation (Inline, per Wave)"; updated Generation Flow file list (`post-deploy-validation.yml`, `run-post-deploy-validation.sh`); updated pipeline structure and variables (`postDeployGate`, `postDeployWebhookUrl`)
- **Updated HTML summary templates**:
  - `summary-template.html` (+ `.backup` + `.pre-patch`): Updated AG-39 file list from `smoke-tests-cd.yml` to `post-deploy-validation.yml`
  - `build_summary_comprehensive.py`: Updated comment placeholder reference
- **Updated documentation**:
  - `docs/agents-catalog.md`: Output YAML reflects 4 artifacts
  - `docs/summary-io-map.md`: Removed Coverage Gap Strategy row; updated Test Plan note
  - `docs/tobe-architecture-io-map.md`: Updated Fase 6 outputs and Fase 7.8 gate
  - `docs/tobe-input-artifacts-existence-check.md`: Updated Fase 7.8 inputs, eliminated rows

---

## [2026-07-23] — Test Cases Overview Extractor (028-test-cases-overview-extractor)

### 🔄 Changed — `summary-agent.md` v1.8.0 → v1.8.1 / `build_summary_comprehensive.py`

- **`D.testCasesContent`** now reads from `asis/qa/test-cases-overview.md` (compact: total count + first 10 rows table), generated by the new `build_test_cases_overview()` function on every summary run. Full `test-cases.md` is no longer embedded verbatim.
- **`build_test_cases_overview(asis_dir, limit=10)`** added to `build_summary_comprehensive.py` (after `build_test_cases()`). Always overwrites `test-cases-overview.md`; returns `""` when `test-cases.md` absent.
- Replaced the two-line `_tc_raw_path` / `test_cases_content` assignment with a single call: `test_cases_content = build_test_cases_overview(asis_dir)`.
- Step 0 F1 read list in `summary-agent.md` updated with `asis/qa/test-cases-overview.md`.
- `D.testCasesContent` D.\* Field Schemas and Data Source Mapping entries updated.

### ✨ Feature — `validate_summary.py` / `summary-validate-agent.md`

- Added **C11.38** (`warn`): fires when `test-cases.md` has CT- entries but `test-cases-overview.md` is absent — signals `build_test_cases_overview()` was not called.

### ✨ New File — `asis-diagnostic/utils/generate_test_cases_overview.py`

- CLI wrapper for manual overview regeneration: `python generate_test_cases_overview.py --project <name>`.
- Imports `build_test_cases_overview()` from `build_summary_comprehensive.py`; always overwrites.

---

## [2026-07-22] — Readiness Gate (Wave 1 — Pré-Build Cycle) (027-tobe-readiness-gate-wave1)

### 🔄 Changed — `ava-tobe-orchestrator` (v2.4.1 → v2.5.0)

- Added **Fase 8.1 — Readiness Gate (Wave 1 — Pré-Build Cycle)**: invokes `ava-readiness-gate` with `wave_number: 1` after Phase 8 (Azure Infra Estimator) and before Gate F2→F3 (Requestor Inspection)
- Gate is **idempotent**: skips re-invocation if `readiness-gate-status.json` already exists with `gate_decision: "APPROVED"`
- **BLOCKED decision** = full pipeline halt: Gate F2→F3, Migration Design Checklist, Strategy Align, and Package Approval are not executed
- **CONDITIONAL decision** = PM must confirm with `"Confirmo"` before proceeding to Gate F2→F3
- Agent Team table updated with `ava-readiness-gate` (phase 8.1)
- Progress Tracker updated: 14 → 15 TODO items (new item `readiness-gate`)
- Agent Completion Registry updated: `ava-readiness-gate` added
- MICRO timing tables (FULL + STATUS_ONLY) updated with `8.1-Gate` row in both Reasoning Approach and Execution Timing Output sections

---

## [2026-07-21] — Artefato Unificado de Regras de Negócio e Requisitos Funcionais (026-unified-business-rules-artifact)

### ✨ Feature — `ava-asis-documentation` v1.6.0 → v2.0.0 (MAJOR)

- **Novo trigger `BRF`**: gera `business-rules.md` com ambas as seções (`## Functional Requirements` + `## Business Rules`) em uma única execução atômica
- **Trigger `ALL`** agora despacha `BRF` em vez de RF+RN separados (DAG reduzido de 4 para 3 níveis)
- **Triggers `RF` e `RN`** mantidos para re-execuções parciais com semântica upsert
- **`functional-requirements.md` descontinuado**: conteúdo migrado para seção `## Functional Requirements` de `business-rules.md`
- Output Contract: 6 artefatos (de 7); `functional-requirements.md` removido

### ✨ Feature — `ava-asis-solution-delphi` v2.5.0 → v2.6.0 (MINOR)

- **`code-business-rules.md` descontinuado**: `BusinessRuleRegistry[]` mantido em memória para análise interna; não gera arquivo em disco
- Dados AST brutas continuam acessíveis via `01_business_rules.json`

### 🔧 Updated — 29 arquivos de agentes/scripts

- **Summary builders** (`build_summary_comprehensive.py`, `build_summary_complete.py`, `validate_summary.py`): path-fallback para leitura de FRs de `business-rules.md`
- **Orchestrator AS-IS** (`orchestrator-asis.md`): Phase B dispatch chain simplificado (VC✓ → BRF✓ → bridge-fastqa)
- **22 agentes downstream**: Input Contract atualizado de `functional-requirements.md` para `business-rules.md`
- **5 agentes coder**: fallback `code-business-rules.md` removido; fonte única `asis/docs/business-rules.md`

---

### ✨ Feature — `ava-summary` v1.7.0 → v1.8.0

- **New F1 sidebar section**: "Test Cases AS-IS" (`s-f1-tc`) parses `asis/qa/test-cases.md` (produced by `ava-asis-bridge-fastqa` Step 17b) and displays all CT-NNN entries in a 7-column table (ID, Title, Module, Priority, Type, Rules, Steps).
- **New builder function** `build_test_cases(asis_dir)` in `build_summary_comprehensive.py`: splits on `## CT-` H2 headings; extracts metadata fields and step count; injects as `D.testCases[]`; returns `[]` when file absent.
- **KPI tiles**: Total, P0 count, Functional count, Negative/Edge count.
- **Nav dot**: green when `D.testCases.length > 0`, grey otherwise. Badge `nb-tc` shows count.
- **10 new i18n keys** in PT and EN dictionaries.

### ✨ Feature — `ava-summary-validate` v1.4.0 → v1.4.1

- **New rule C11.37** (`warn`): `D.testCases` non-empty when `asis/qa/test-cases.md` has CT- headings. Non-blocking — `test-cases.md` is optional.

### ✨ Feature — `ava-summary-remediation` v1.4.0 → v1.4.1

- **Regra J** in `phase1_artifact_resolution()`: synthesizes placeholder `test-cases.md` only when both the file and `fastqa/manual_test/` are absent.

---

## [2026-07-17] — Bridge FastQA AST Simplification (v4.0.0)

### 💥 Breaking — `ava-asis-bridge-fastqa` — MAJOR version 3.3.0 → 4.0.0

#### Input Contract replaced (AST JSON artifacts replace derived documentation)

- `bridge-fastqa-asis.md`: Primary inputs changed from `functional-requirements.md` + `business-rules.md` (and 4 optional doc artifacts) to three deterministic AST JSON files — `01_business_rules.json`, `02_form_business_rules.json`, `03_database_rules.json` — with two-level path resolution (`compressed/` → `extraction/`) and hard stop if absent from both.
- New `PROCEDURE validate_ast_inputs()` replaces `PROCEDURE validate_inputs()` — emits `⛔ HARD STOP` block identifying missing files and both checked paths.

#### Lean FastQA pipeline (3 steps eliminated)

- Removed `@fastqa:estimate_effort` (was Step 10): non-essential for test case generation.
- Removed `@fastqa:ac_scope_analysis` (was Step 14): `test_case_with_fastqa` has built-in fallback.
- Removed `@fastqa:validate_scenarios` (was Step 16): QA-of-QA step; does not block test case existence.
- New step sequence: Element 2 = `load_pbi → identify_gaps → analyze_requirements → map_behaviors` (Steps 8–12); Element 3 = `test_case_with_fastqa → test_plan` (Steps 13–16). Total: 18 → 16 steps.

#### Lean test-plan.md template (9 → 5 sections)

- Removed: Architecture Tests (§4), E2E Tests (§5), Smoke Test Suite (§6), Load Test Plan (§7), Test Data Management (§8) — all required inputs not available from AST JSONs.
- Added: **Test Coverage Map** (new §4) — unified traceability table mapping `BR-NNN` / `DBR-NNN` / `form:{form_name}` rule IDs to test categories, derived directly from the three AST files.
- Template sections now: §1 Test Strategy, §2 Unit Test Scope, §3 Integration Test Scope, §4 Test Coverage Map, §5 Test Quality Gates.

#### Secondary changes

- `orchestrator-asis.md`: `artifact_contracts.ava-asis-bridge-fastqa.external_mandatory` reduced from 9 to 6 entries (removed `estimate_effort/`, `requirements_analysis/*_ac_scope.md`, `test_cases/*_validation_report.md`); dispatch prompt updated to `v4.0.0 / 16 Steps`; `size_threshold` lowered from `5000` to `3000` bytes.
- `docs/asis-diagnostic-io-map.md`: bridge-fastqa entry updated to reflect AST JSON inputs and reduced output set; cross-agent consumption table updated.

## [2026-07-22] — Readiness Gate (Wave 1 — Pré-Build Cycle) (027-tobe-readiness-gate-wave1)

### 🔄 Changed — `ava-tobe-orchestrator` (v2.4.1 → v2.5.0)

- Added **Fase 8.1 — Readiness Gate (Wave 1 — Pré-Build Cycle)**: invokes `ava-readiness-gate` with `wave_number: 1` after Phase 8 (Azure Infra Estimator) and before Gate F2→F3 (Requestor Inspection)
- Gate is **idempotent**: skips re-invocation if `readiness-gate-status.json` already exists with `gate_decision: "APPROVED"`
- **BLOCKED decision** = full pipeline halt: Gate F2→F3, Migration Design Checklist, Strategy Align, and Package Approval are not executed
- **CONDITIONAL decision** = PM must confirm with `"Confirmo"` before proceeding to Gate F2→F3
- Agent Team table updated with `ava-readiness-gate` (phase 8.1)
- Progress Tracker updated: 14 → 15 TODO items (new item `readiness-gate`)
- Agent Completion Registry updated: `ava-readiness-gate` added
- MICRO timing tables (FULL + STATUS_ONLY) updated with `8.1-Gate` row in both Reasoning Approach and Execution Timing Output sections

---

## [2026-07-21] — Artefato Unificado de Regras de Negócio e Requisitos Funcionais (026-unified-business-rules-artifact)

### ✨ Feature — `ava-asis-documentation` v1.6.0 → v2.0.0 (MAJOR)

- **Novo trigger `BRF`**: gera `business-rules.md` com ambas as seções (`## Functional Requirements` + `## Business Rules`) em uma única execução atômica
- **Trigger `ALL`** agora despacha `BRF` em vez de RF+RN separados (DAG reduzido de 4 para 3 níveis)
- **Triggers `RF` e `RN`** mantidos para re-execuções parciais com semântica upsert
- **`functional-requirements.md` descontinuado**: conteúdo migrado para seção `## Functional Requirements` de `business-rules.md`
- Output Contract: 6 artefatos (de 7); `functional-requirements.md` removido

### ✨ Feature — `ava-asis-solution-delphi` v2.5.0 → v2.6.0 (MINOR)

- **`code-business-rules.md` descontinuado**: `BusinessRuleRegistry[]` mantido em memória para análise interna; não gera arquivo em disco
- Dados AST brutas continuam acessíveis via `01_business_rules.json`

### 🔧 Updated — 29 arquivos de agentes/scripts

- **Summary builders** (`build_summary_comprehensive.py`, `build_summary_complete.py`, `validate_summary.py`): path-fallback para leitura de FRs de `business-rules.md`
- **Orchestrator AS-IS** (`orchestrator-asis.md`): Phase B dispatch chain simplificado (VC✓ → BRF✓ → bridge-fastqa)
- **22 agentes downstream**: Input Contract atualizado de `functional-requirements.md` para `business-rules.md`
- **5 agentes coder**: fallback `code-business-rules.md` removido; fonte única `asis/docs/business-rules.md`

---

### ✨ Feature — `ava-summary` v1.7.0 → v1.8.0

- **New F1 sidebar section**: "Test Cases AS-IS" (`s-f1-tc`) parses `asis/qa/test-cases.md` (produced by `ava-asis-bridge-fastqa` Step 17b) and displays all CT-NNN entries in a 7-column table (ID, Title, Module, Priority, Type, Rules, Steps).
- **New builder function** `build_test_cases(asis_dir)` in `build_summary_comprehensive.py`: splits on `## CT-` H2 headings; extracts metadata fields and step count; injects as `D.testCases[]`; returns `[]` when file absent.
- **KPI tiles**: Total, P0 count, Functional count, Negative/Edge count.
- **Nav dot**: green when `D.testCases.length > 0`, grey otherwise. Badge `nb-tc` shows count.
- **10 new i18n keys** in PT and EN dictionaries.

### ✨ Feature — `ava-summary-validate` v1.4.0 → v1.4.1

- **New rule C11.37** (`warn`): `D.testCases` non-empty when `asis/qa/test-cases.md` has CT- headings. Non-blocking — `test-cases.md` is optional.

### ✨ Feature — `ava-summary-remediation` v1.4.0 → v1.4.1

- **Regra J** in `phase1_artifact_resolution()`: synthesizes placeholder `test-cases.md` only when both the file and `fastqa/manual_test/` are absent.

---

## [2026-07-17] — Bridge FastQA AST Simplification (v4.0.0)

### 💥 Breaking — `ava-asis-bridge-fastqa` — MAJOR version 3.3.0 → 4.0.0

#### Input Contract replaced (AST JSON artifacts replace derived documentation)

- `bridge-fastqa-asis.md`: Primary inputs changed from `functional-requirements.md` + `business-rules.md` (and 4 optional doc artifacts) to three deterministic AST JSON files — `01_business_rules.json`, `02_form_business_rules.json`, `03_database_rules.json` — with two-level path resolution (`compressed/` → `extraction/`) and hard stop if absent from both.
- New `PROCEDURE validate_ast_inputs()` replaces `PROCEDURE validate_inputs()` — emits `⛔ HARD STOP` block identifying missing files and both checked paths.

#### Lean FastQA pipeline (3 steps eliminated)

- Removed `@fastqa:estimate_effort` (was Step 10): non-essential for test case generation.
- Removed `@fastqa:ac_scope_analysis` (was Step 14): `test_case_with_fastqa` has built-in fallback.
- Removed `@fastqa:validate_scenarios` (was Step 16): QA-of-QA step; does not block test case existence.
- New step sequence: Element 2 = `load_pbi → identify_gaps → analyze_requirements → map_behaviors` (Steps 8–12); Element 3 = `test_case_with_fastqa → test_plan` (Steps 13–16). Total: 18 → 16 steps.

#### Lean test-plan.md template (9 → 5 sections)

- Removed: Architecture Tests (§4), E2E Tests (§5), Smoke Test Suite (§6), Load Test Plan (§7), Test Data Management (§8) — all required inputs not available from AST JSONs.
- Added: **Test Coverage Map** (new §4) — unified traceability table mapping `BR-NNN` / `DBR-NNN` / `form:{form_name}` rule IDs to test categories, derived directly from the three AST files.
- Template sections now: §1 Test Strategy, §2 Unit Test Scope, §3 Integration Test Scope, §4 Test Coverage Map, §5 Test Quality Gates.

#### Secondary changes

- `orchestrator-asis.md`: `artifact_contracts.ava-asis-bridge-fastqa.external_mandatory` reduced from 9 to 6 entries (removed `estimate_effort/`, `requirements_analysis/*_ac_scope.md`, `test_cases/*_validation_report.md`); dispatch prompt updated to `v4.0.0 / 16 Steps`; `size_threshold` lowered from `5000` to `3000` bytes.
- `docs/asis-diagnostic-io-map.md`: bridge-fastqa entry updated to reflect AST JSON inputs and reduced output set; cross-agent consumption table updated.

## [2026-07-20] — `ava-asis-db-analyzer` v1.5.0: Script Enforcement & AST Completeness Validation

### ✨ Added

- **ER Diagram — Script Execution Gate (mandatory)**: `er-diagram.mmd` MUST now be produced exclusively by `python src/shared/tools/gen_er_diagram.py` piped through `validate_diagram.py`, never via direct `Write`.
- **DFM-to-DDL Transformation**: deterministic rules for consuming `04_database_schemas.json` (Delphi AST):
  - Unit-name-to-table-name: `CamelCase` → `UPPER_SNAKE_CASE` with `U` prefix stripping
  - DFM-field-to-DDL-column mapping with explicit type table (Integer→int, String→string, etc.)
- **Post-Generation Completeness Assertion**: new mandatory gate using in-memory counters (`diagram_entity_count >= 0.8 * schema_table_count`). Fails with `human_gate_required = true` on silent data loss.

### 🔧 Changed

- Updated `src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md` from version `1.4.0` → `1.5.0`.
- Strengthened PRE-WRITE VALIDATION GATE to explicitly prohibit `er-diagram.mmd` generation via `Write` for ER diagrams (redirect to Script Execution Gate).

### Files changed

- src/modules/ava-fabric-agents/asis-diagnostic/agents/db-analyzer/db-analyzer.md
- CHANGELOG.md

---

## [1.2.0] — 2026-07-21

### Changed

- `ava-prototype`: `design-system.md` e `user-journeys.md` reclassificados como entradas opcionais.
- `ava-prototype`: `outputs/asis/docs/business-rules.md` adicionado como entrada primária obrigatória.
- `ava-prototype`: Pre-flight substituído pelo formato de tabela canônico (OBRIGATÓRIO/OPCIONAL/BLOQUEADO/DECISÃO).
- `ava-prototype`: Prompt de confirmação adicionado quando artefatos opcionais estão ausentes.
- `ava-prototype`: Entradas de início e fim gravadas em `outputs/tobe/prototype/execution-log.json` em todos os caminhos de execução.

## [2026-07-21] — ava-tobe-orchestrator v2.4.2

### Fixed

- `ava-tobe-orchestrator` v2.4.2: Removida obrigatoriedade bloqueante de `master-report.md` no trigger `SD`. O arquivo passa a ser verificado com aviso não-bloqueante (`[AVISO]`); o pipeline prossegue com os artefatos AS-IS presentes. Gate de artefatos essenciais (`bounded-context-map.md`, `architecture-blueprint.md`, `db-analysis-report.md`) permanece bloqueante quando todos ausentes.

## [2026-07-21] — F1 Orchestrator: Summary hook agora exige template via script (022-asis-orchestrator-summary-template-fix)

- **ava-asis-orchestrator v2.21.1** (PATCH)
- Problema: ao executar em modo SA, o hook `SAS` despachava `ava-summary` sem
  mandar usar `build_summary_comprehensive.py`, permitindo geração HTML inline
  não-conforme com o template AVA Fabric.
- Fix: seção "Hook: AVA Summary" inclui agora instrução obrigatória de uso do
  script, bloco `success_criteria` (assinatura + tamanho > 150 KB) e validação
  pós-execução com aviso `⚠️ SUMMARY TEMPLATE MISMATCH` quando a assinatura não
  é encontrada. Modo SKIP inalterado.

## [2026-07-15] — Novo agente Blazor WebAssembly com MSAL, Fluxor e MudBlazor

### ✨ Added — `ava-stack-blazor-frontend` — geração frontend Blazor production-ready

- `src/modules/ava-fabric-apps-agents/ava-stack-blazor-frontend.md` (NOVO): agente especializado para geração de aplicações Blazor WebAssembly com suporte a .NET configurável via `tobe_stack.frontend_version` (fallback para `tobe_stack.backend_version`), autenticação Azure AD via MSAL.NET, gerenciamento de estado com Fluxor e design system baseado em MudBlazor.
- Adicionado **Routing Guard** obrigatório com validação de `pipeline_mode` em `project-config.yaml`, bloqueando execução quando configurado como `build-cycle` e permitindo apenas `generic`.

## [2026-06-17] — PBI 2103 Azure calculator readiness

### ✨ Added

- Added probabilistic preprocessing requirements to the TO-BE Azure infra estimator for access CSV analysis (`CLIENTE`, `Usuarios`) including concurrency range and uncertainty outputs.
- Added trigger contract extensions for calculator-oriented execution paths: `CA` (concurrency), `TA` (throughput), `AP` (provisioning plan without costs).
- Added new output artifacts in the estimator contract: `concurrency-report.md`, `throughput-metrics.md`, `azure-provisioning-planV1.md`.
- Added `src/shared/utils/validate_azure_prices.py` — live Azure Retail Prices API validator (no auth, public endpoint). Queries `prices.azure.com` per-meter, computes line-item delta % vs generated estimates, outputs `PASS_EXACT` / `PASS_NEAR` / `FAIL` / `BLOCKED`. Supports `--json-out` for machine-readable output consumed by the agent.
- Embedded verified meter reference table (14 services, region: `brazilsouth`) in the agent definition — meters confirmed by live API probing. Critical finding: Log Analytics PAYG = **$4.60/GB** (not flat fee) — 30 GB/day prod = $4,140/mo, not ~$90.

### 🔧 Changed

- Updated agent `ava-tobe-azure-infra-estimator` to version `1.2.0` (from 1.1.0).
- Added `Run` to `allowed-tools` — agent can now invoke `validate_azure_prices.py` directly.
- Split Step 7 into Step 7.1 (mandatory live API price fetch) and Step 7.2 (report assembly from JSON).
- Banned `~$X` approximate prices in agent output — all costs must originate from live API JSON.
- Added `live-api` source tag for prices fetched from Azure Retail Prices API.

### 🐛 Fixed

- SQL Database meter filters corrected: productName must be `SQL Database Single/Elastic Pool General Purpose - Compute Gen5` (not generic skuName query).
- Redis: Classic C0/C1/C2 not available in brazilsouth — mapped to E-series (E1/E10).
- Container Registry: meterName must be `Basic Registry Unit` / `Standard Registry Unit` (not `Registry Unit`).
- Log Analytics: correct meter is `serviceName='Log Analytics'`, meterName=`Analytics Logs Data Ingestion` at $4.60/GB.
- App Gateway WAF v2: no single WAF meter exists — uses Standard Fixed Cost as fixed-charge baseline.
- Added fallback filter support in `fetch_price()` for meters with region-specific skuName variants.

### Files changed

- src/modules/ava-fabric-agents/tobe-architecture/agents/azure-infra-estimator-tobe.md
- src/shared/utils/validate_azure_prices.py (new)
- src/shared/utils/probe_meters.py (new — dev utility, not production)
- src/shared/utils/probe2.py (new — dev utility)
- src/shared/utils/probe_sql.py (new — dev utility)
- CHANGELOG.md
  Project: **Meu-ERP** · Date: **2026-04-15 → 2026-04-17** · Template: `AVA Fabric Summary Template v1.0`

---

## [2026-04-17] — Session summary

Scope of this session: make the Summary HTML a production-grade deliverable for any AVA Fabric project. Covers the template (`summary-template.html`), the builder (`build_summary_complete.py`), several TO-BE documents, new F4 (QA) and F5 (Prototype) outputs, and a config-naming bug.

---

### ✨ Added — new features

#### Sidebar · per-phase Deliverables submenu

- Every phase group (F1–F7) in the left sidebar now has an expandable **"📦 Entregáveis / Deliverables"** submenu that lists the real files of that phase.
- Data-driven: reads `D.fileTree[phase]` populated by the builder — works for any future project without template changes.
- Clicking a file renders content in a new central section `#s-deliverable-view` (markdown → HTML, JSON → pretty-printed, Mermaid → SVG, **HTML → inline iframe**).
- **Graceful fallback**: phases with no files show a "Sem entregáveis" item in the sidebar and a friendly card in the center with shortcuts to File Explorer and Artefatos.
- **Category grouping** (8 semantic buckets): Diagrams · Security · Requirements & Docs · QA & Tests · Database · Architecture & Analysis · Planning & Sizing · Other Artifacts. Classification is rule-based on extension + filename patterns (file `er-diagram.mmd` → Diagrams, `security-map.md` → Security, etc.) — agnostic to project.
- Each category is **collapsible** with a caret; default closed; state preserved across language switches.
- Labels are **i18n-aware** (PT/EN) and follow the language combobox via `setLang()` which re-renders the submenu idempotently (preserves expanded categories).

#### F4 — QA phase (full)

- 10 new deliverables under `projects/Meu-ERP/outputs/qa/`:
  - `quality-strategy.md` — strategy, gates, metrics
  - `qa-master-report.md` — consolidated F4 report
  - `gaps-requirements-report.md` — 11 requirement gaps
  - `behavior-mapping-report.md` — 18 Given-When-Then
  - `scenario-generator-report.md` — 26 scenarios
  - `test-case-generator-report.md` — 27 seed test cases
  - `script-generator-report.md` — xUnit + Testcontainers + Playwright + k6 + ZAP + axe-core snippets
  - `defect-identifier-report.md` — triage matrix, SLAs, defect YAML template
  - `exploratory-report.md` — 6 SBTM charters
  - `evidence-capture-report.md` — storage layout, LGPD retention, chain-of-custody
- All written in English per `language: "en"` in `agent-task-config.yaml`.
- 9 new entries in `ARTIFACT_MAP` (orchestrator + 8 QA sub-agents) — status tracker advances F4 from pending to done.

#### F5 — Prototype (navigable wireframe)

- New `projects/Meu-ERP/outputs/tobe/prototype/`:
  - `index.html` — self-contained 12-screen prototype (Login, Dashboard, AP list/write-off/new, AR list, Bank reconciliation, Customers/Suppliers, Chart of Accounts, Audit Trail, Settings + drawer), uses `designer-system.md` tokens.
  - `demo-script.md` — 20–25 min stakeholder walkthrough.
  - `figma-spec.md` — tokens, 10 components, 12 frames ready for Figma hand-off.
  - `README.md` — entry point + run instructions.
- `ava-prototype` added to `ARTIFACT_MAP`.
- F3/F4 phase in the sidebar now maps to this prototype folder only (`PHASE_FOLDER_MAP.f3f4 = 'prototype'`), ending duplication with F2.

#### F1 AS-IS — missing sequence diagrams

- `asis/diagrams/seq-baixa-titulo-cp.mmd` — AP write-off flow, highlights 4 SQLs without transaction (R-003).
- `asis/diagrams/seq-cadastro-conta-pagar.mmd` — AP create flow, highlights SQL Injection (R-001) + race on `max(id)+1` (R-005).

#### Dashboard sections populated

- **KPIs & Métricas**: every card reads from `metrics.json`.
- **Complexidade Ciclomática**: parsed from `metrics.json.complexity.highest_cc_files`.
- **Business Rules**: 24 entries parsed from `business-rules.md`.
- **Documentation & Requirements**: 20 entries parsed from `functional-requirements.md`.
- **Test Baseline**: 14 rows + 20 gaps parsed from `test-map.md` / `test-gaps.md`.
- **Fluxo de Telas**: 22-form inventory table + Mermaid navigation diagram parsed from `screen-navigation-map.md`.
- **API Surface TO-BE**: 4 endpoints parsed from `tobe/docs/openapi/meu-erp-finance-v1.yaml`.
- **Artefatos — AG-02** (and every other chip card): `{{ARTIFACT_INVENTORY_JSON}}` now populated via `build_artifact_inventory()` — 73 artifacts across 11 agent chips.

#### HTML deliverable renderer (new)

- Clicking any `.html` file in the Deliverables submenu (e.g., F3/F4 prototype) renders it **inline as a sandboxed iframe** (`srcdoc`) — 82 vh, `allow-scripts allow-forms`, same-origin disabled. Source viewable via collapsible `<details>`.

#### Mermaid render pipeline — `renderMermaidSafely()`

- Single entry point for every Mermaid render in the template:
  - Uses `mermaid.render(id, source)` to get the SVG as a string (not injected yet).
  - Sanitizes `width="-N"`/`height="-N"` → `"0"` in the SVG string **before** insertion — eliminates the noisy `<rect> attribute width: A negative value is not valid` browser console errors at the source.
  - Wraps the sanitized SVG in `.mmd-view` and replaces the target element.
- Called by: `renderStaticDiagrams` (10 static diagrams), `renderDeliverableContent` (.mmd branch), `renderScreenNavigation`.
- Each render is isolated — one broken diagram cannot break the others.

---

### 🔧 Changed — template

- **Template data contract**: new JS fields injected by the builder — `ccTop`, `bizRules`, `funcReqs`, `testMap`, `testGaps`, `screenMermaid`, `screenForms`, `apiEndpoints`, `staticDiagrams`, `arts` (populated for real now).
- **`PHASE_FOLDER_MAP`**: `f3f4` remapped from `'tobe'` to `'prototype'` — ends F3/F4 replicating F2's files.
- **`DELIV_CATEGORIES` constant**: 8-category classifier with PT/EN labels, used by `buildDeliverableSubmenu`.
- **`init()` pipeline**: renderStaticDiagrams + renderScreenNavigation called post-mermaid-init; `initDeliverableSubmenus` called once at init and re-called by `setLang()` for language toggling.
- **`setLang()`**: added re-render of deliverable submenu (idempotent).
- **Deliverable category body**: collapsible via `toggleDelivCategory(catId)`, default closed, expanded state preserved in `DelivState.expanded`.
- **Source HTML of `.mmd` files** now shown in a `<details>` block below the rendered SVG.

### 🔧 Changed — builder (`build_summary_complete.py`)

- **Multi-phase scanner**: `build_file_tree_with_content()` now walks every known phase folder (`asis`, `tobe`, `prototype`, `qa`, `deliverables`, `devops`, `summary`) instead of just `asis/`. `prototype/` is promoted to a top-level key so F3/F4 shows only its files.
- **Scanner exclusions** (`EXCLUDED_PATH_SEGMENTS`): `source-code`, `tests`, `config`, `__pycache__`, `.git`, `node_modules` — keeps the deliverable surface about documentation and diagrams, not codebase.
- **READABLE_EXTS** pared down: removed `cs`, `ts`, `tsx`, `js`, `jsx`, `py`, `sh`, `css`, `scss`, `sass`, `bat`, `ps1`, `csproj`, `sln`, `pas`, `dfm`, `dpr`, `dproj`, `bicep`, `tf`, `env` — source code no longer embedded in summary. TO-BE Deliverables count went from 112 → 36.
- **`ARTIFACT_MAP`**:
  - Added F2 agents: `ava-tobe-orchestrator`, `ava-tobe-architecture-design`, `ava-tobe-architecture-technical`, `ava-tobe-measure-size`, `ava-tobe-migration-plan`, `ava-docs-tobe`, `ava-test-plan-tobe`.
  - Added F3 agents: `ava-stack-orchestrator`, `ava-stack-dotnet-backend`, `ava-stack-angular-frontend`.
  - Added F4 agents: `ava-qa-orchestrator` + 8 sub-agents.
  - Added F5: `ava-prototype`.
  - Added F8: `ava-summary`.
  - **Removed**: `ava-coder-dotnet` (agent dropped from workflow).
- **`build_artifact_inventory()`**: now actually called; result injected via `{{ARTIFACT_INVENTORY_JSON}}`.
- **New helpers**:
  - `build_all_substitutions()` — computes 180 placeholders from `metrics.json`, `risk-register.json`, `pattern-classifications.json`, diagrams.
  - `parse_complexity_top10`, `parse_business_rules`, `parse_functional_requirements`, `parse_test_map`, `parse_screen_navigation`, `parse_openapi_endpoints`, `collect_static_diagrams` — 7 data extractors feeding the template.
  - `_sanitize_mermaid` — strips emojis, replaces `→`/`—`/`–` with ASCII equivalents. Applied to every `.mmd` before injection.
  - `_load_mermaid_js` — inlines `mermaid.min.js` (3 091 KB) for offline rendering.
- **JSON injection hardening**: all JSON strings emitted into `<script>` go through `.replace('</', '<\\/')` so embedded content can never close the script tag.
- **Final placeholder sweep**: unresolved `{{X_JSON}}` → `{}`, any other `{{X}}` → `""` — generated JS is always valid, even when the builder doesn't know a placeholder.
- **Pre-existing bug fix**: `build_agent_status_map` was being called with 1 arg instead of 2 (missing `outputs_base`) — fixed.
- **TO-BE folder separation**: scanner skips `tobe/prototype/**` because it's promoted to a dedicated phase key, preventing duplication.

### 🔧 Changed — configuration

- **`projects/Meu-ERP/context/project-config.yaml`** (new, copy of `agent-task-config.yaml`): agents read `project-config.yaml` via their .md definitions (51 references) while skill entry-points read `agent-task-config.yaml` (40+ references). Dual-file strategy keeps both working without code churn.
- **`shared-context.md`**: versioned to v6.1 → v6.2 → v6.3 → v6.4 with tracker updates for F4, F5 and summary regeneration entries.

### 🔧 Changed — TO-BE artifacts (language fix)

Translated from Portuguese to English in-place (`language: "en"` in config was being ignored before). 20 files:

- Root: `architecture-blueprint.md`, `api-map.md`, `ado-work-items.md`, `bounded-context-map.md`, `coding-standards.md`, `cost-estimate.md`, `designer-system.md`, `effort-calculator.md`, `infra-sizing.md`, `migration-plan.md`, `sizing-report.md`, `solution-structure.md`, `tech-framework-document.md`, `test-plan.md`, `user-journeys.md`, `wave-plan.md`
- `docs/`: `technical-design-document.md`, `CHANGELOG.md`
- `docs/adrs/`: ADR-001, 002, 003, 004, 005, 006, 007
- `config/`: `quality-gates.md`
- `tests/`: `coverage-strategy.md`
- `source-code/`: `README.md` + `ContaCorrente.Banco/README.md`

Filenames **kept unchanged** per i18n rule (technical identifiers preserved to avoid breaking 51+ cross-references in agent docs, ARTIFACT_MAP, shared-context).

### 🔧 Changed — CSVs

- `docs/azure-devops-workitems-revisao-agentes_all.csv`: added `Category` column (AS-IS Diagnostic · Migration Design · Build Cycle · Delivery & Handover) for all 42 agent review tasks.
- `docs/data.csv`: added `Category` column (adds Platform & Tooling category) for all 163 Azure DevOps work items including Tasks traced to their Parent PBI.

### 🔧 Changed — `tobe-architecture` module

- `module.yaml`: `ava-coder-dotnet` removed from agent registration.
- `workflows/design-dotnet/workflow.md`: `code-generation` step removed; `documentation` step now depends on `technical` directly.

---

### 🗑 Removed

- **Sidebar nav items** removed from F1 group: "Diagramas C4", "Arquitetura Overall", "Processos BPMN", "Seq. Diagrams" — the same content is now in "📦 Entregáveis" categorized.
- **Sidebar nav item** removed from F2 group: "Código Gerado" (obsolete after coder-dotnet removal).
- **Topbar menu** "Artefatos" removed from execution-run header.
- **Screen Flow diagram card** removed (user requested, then restored, then removed again — current: removed; Inventário de Formulários card remains).
- **Old summary HTMLs** removed per guardrail (`AVA-FABRIC-SUMMARY-Meu-ERP-2026-04-15.html`, `…-2026-04-16.html`) before each regeneration.
- **`setTimeout(_patchNegRects, ...)` polling** removed — negative-width sanitization is now done on the SVG string before DOM insertion.
- **Broad `mermaid.run({querySelector:...})` after renderStaticDiagrams** removed — per-element rendering replaces it.

---

### 🐛 Fixed — defects

| #   | Issue                                                              | Root cause                                                                                                                         | Resolution                                                                                                   |
| --- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 1   | Mermaid diagrams showed raw code in AS-IS Architecture             | `renderStaticDiagrams()` was defined but never called; broad `mermaid.run` rejected on any single-diagram error, skipping the rest | Per-element `mermaid.run({nodes:[pre]})` then refactored to `renderMermaidSafely()` using `mermaid.render()` |
| 2   | `<rect> attribute width: A negative value is not valid` in console | Mermaid v11 emits `width="-37.5"` in subgraphs; post-hoc DOM patch ran too late                                                    | Sanitize SVG **string** before it hits the DOM                                                               |
| 3   | `[Mermaid] Could not find a suitable point` on TO-BE C4            | Dagre routing warning rejected the promise in `mermaid.run`                                                                        | `mermaid.render()` returns the SVG even with routing warnings; diagram renders with one unlabeled edge       |
| 4   | TO-BE artifacts in Portuguese despite `language: "en"`             | Agents read `project-config.yaml`; Meu-ERP only had `agent-task-config.yaml`                                                       | Copied to `project-config.yaml` + translated 20 drifted files                                                |
| 5   | F2 Deliverables submenu empty                                      | Builder scanned only `asis/` folder                                                                                                | Multi-phase scanner walks all phase folders                                                                  |
| 6   | F3/F4 Deliverables replicated F2 files                             | `PHASE_FOLDER_MAP.f3f4 = 'tobe'`                                                                                                   | Promoted `tobe/prototype/` to dedicated phase key and remapped f3f4                                          |
| 7   | Phase execution tracker stuck at 8/40                              | `ARTIFACT_MAP` missing F2/F3/F4/F5/F8 entries                                                                                      | 28/40 after adding 20 new artifact entries                                                                   |
| 8   | API Surface TO-BE empty                                            | No parser for OpenAPI; no render function                                                                                          | Added `parse_openapi_endpoints` + `renderAPISurface()`                                                       |
| 9   | Fluxo: Baixa CP / Cadastro CP diagrams missing                     | `.mmd` files didn't exist and builder pointed at wrong filename                                                                    | Created `.mmd` files and fixed builder paths                                                                 |
| 10  | Artefatos — AG-02 (all chip cards) empty                           | `{{ARTIFACT_INVENTORY_JSON}}` hardcoded to `'{}'`                                                                                  | Wired `build_artifact_inventory()` result                                                                    |
| 11  | Deliverables categories stuck in Portuguese after language toggle  | `setLang()` didn't re-render the submenu                                                                                           | Added idempotent re-render call                                                                              |
| 12  | Prototype index.html shown as raw text                             | No branch for `.html` in `renderDeliverableContent`                                                                                | Added iframe `srcdoc` branch                                                                                 |
| 13  | MMD files shown as raw text in Deliverables                        | `_escHtml + innerHTML` mangled `<br/>`/`<i>` tags in Mermaid labels                                                                | `textContent` via DOM API                                                                                    |
| 14  | Screen Flow "Syntax error in text"                                 | `.mmd` content had emojis, `→`, `—` that Mermaid v11 refuses                                                                       | Added `_sanitize_mermaid` to parser                                                                          |
| 15  | `build_agent_status_map()` missing arg crash                       | Pre-existing bug: `TypeError: missing 1 required positional argument: 'outputs_base'`                                              | Passed `outputs_dir` through                                                                                 |
| 16  | Summary HTML file:// unsafe origin warning                         | Cosmetic browser warning for self-references                                                                                       | Mermaid `securityLevel: 'loose'` handles it; warning is non-fatal                                            |
| 17  | Sidebar nav items pointed to removed sections                      | Old F1 diagram items weren't cleaned up when categorization was introduced                                                         | Removed orphan nav items from sidebar                                                                        |
| 18  | `</script>` in embedded content closed the script tag              | JSON injection didn't escape `</`                                                                                                  | All JSON outputs pass through `.replace('</', '<\\/')`                                                       |
| 19  | Many `{{PLACEHOLDER}}` leftovers broke JS parsing                  | Builder had no final sweep                                                                                                         | Final regex sweep replaces unknown `{{X_JSON}}` → `{}`, `{{X}}` → `""`                                       |

---

### 🧪 Tested

Every rebuild run through:

1. `python build_summary_complete.py --project Meu-ERP` → `SUCESSO` + "Assinatura VÁLIDA".
2. `node --check` on the main `<script>` → JS OK.
3. Data presence checks: `ccTop`, `bizRules`, `funcReqs`, `testMap`, `screenMermaid`, `apiEndpoints`, `staticDiagrams`, `D.arts`, `fileTree[phase]` — all populated.
4. Browser-based visual checks across 12 UX regression scenarios (KPIs, tables, diagrams, Deliverables submenu, language toggle, prototype iframe, etc.).

---

### 📊 Final output counts (`v13`)

- **Summary HTML**: 3.7 MB, signature `AVA Fabric Summary Template v1.0`.
- **Phase folders scanned**: asis (38) · tobe (36) · prototype (4) · qa (10) · summary (1) = **89 artifacts**, 147 with embedded content.
- **Agents done**: 28/40 (F1 · F2 · F3 · F4 · F5 · F8).
- **Structured data**: 6 CC rows · 24 business rules · 20 functional requirements · 14 test map rows · 20 test gaps · 22 screen forms · 4 API endpoints · **10 static diagrams** (C4 context/container/component, class, component-map, 2 sequence, ER, TO-BE C4, Gantt).
- **Agent inventory**: 73 artifacts catalogued across 11 chip cards.

---

### 🔒 Guardrails upheld throughout the session

- Every rebuild: old HTML removed **before** generation (guardrail 3).
- Template loaded **explicitly** from `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` (guardrail 1).
- Signature `AVA Fabric Summary Template v1.0` validated after every build (guardrail 4).
- **Zero** HTML generated manually, inline, or from other projects (guardrail 2).
- **Zero** output written to `projects/_template/`.
- JSON outputs hardened against `</script>` injection.
- Filenames and identifiers preserved per i18n rule even when translating content.

---

### 📝 Files created in this session

- `CHANGELOG.md` (this file)
- `projects/Meu-ERP/context/project-config.yaml`
- `projects/Meu-ERP/outputs/asis/diagrams/seq-baixa-titulo-cp.mmd`
- `projects/Meu-ERP/outputs/asis/diagrams/seq-cadastro-conta-pagar.mmd`
- `projects/Meu-ERP/outputs/qa/` (10 reports)
- `projects/Meu-ERP/outputs/tobe/prototype/` (4 files: index.html, demo-script.md, figma-spec.md, README.md)
- `projects/Meu-ERP/outputs/summary/AVA-FABRIC-SUMMARY-Meu-ERP-2026-04-17.html` (v13)

### 📝 Files modified

- `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` — 10+ distinct changes
- `src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py` — 15+ distinct changes
- `src/modules/ava-fabric-agents/tobe-architecture/module.yaml` — removed `ava-coder-dotnet`
- `src/modules/ava-fabric-agents/tobe-architecture/workflows/design-dotnet/workflow.md` — removed `code-generation` step
- `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` — removed `ava-coder-dotnet` entry
- `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` — removed from ALL_AGENTS
- `projects/Meu-ERP/context/shared-context.md` — v6.1 → v6.4
- All TO-BE docs translated to English (listed above)
- `docs/azure-devops-workitems-revisao-agentes_all.csv` — added Category column
- `docs/data.csv` — added Category column

---

## [2026-07-15] — Novo agente Blazor WebAssembly com MSAL, Fluxor e MudBlazor

### ✨ Added — `ava-stack-blazor-frontend` — geração frontend Blazor production-ready

- `src/modules/ava-fabric-apps-agents/ava-stack-blazor-frontend.md` (NOVO): agente especializado para geração de aplicações Blazor WebAssembly com suporte a .NET configurável via `tobe_stack.frontend_version` (fallback para `tobe_stack.backend_version`), autenticação Azure AD via MSAL.NET, gerenciamento de estado com Fluxor e design system baseado em MudBlazor.
- Adicionado **Routing Guard** obrigatório com validação de `pipeline_mode` em `project-config.yaml`, bloqueando execução quando configurado como `build-cycle` e permitindo apenas `generic`.
- Implementado scaffold raiz completo para projetos Blazor WASM, incluindo geração determinística de `.csproj`, `Program.cs`, `App.razor`, `_Imports.razor`, `MainLayout`, `NavMenu`, `Dashboard`, `appsettings.json` e demais artefatos obrigatórios para garantir compilação (`dotnet build`) sem falhas.
- Adicionadas regras de governança frontend, soberania de dados, invariantes de segurança (MSAL, PII, XSS, placeholders obrigatórios para segredos) e acessibilidade (WCAG 2.1 AA).
- Incluído suporte padrão a **MSAL.NET**, `AuthorizationMessageHandler`, `AuthService`, fluxo de login/logout, `AuthorizeRouteView`, `RedirectToLogin` e páginas de autenticação.
- Adicionado conjunto de serviços transversais (`ErrorService`, `LoadingService`, `MoneyFormatService`) e componentes compartilhados (`LoadingOverlay`, `ErrorBanner`, `EmptyState`, `PageHeader`, `StatusChip`, `ConfirmDialog`, `FormError`, `InfoCard` e `ActionToolbar`).
- Implementada arquitetura Fluxor por Bounded Context com geração automática de `State`, `Actions`, `Reducers` e `Effects`, incluindo integração com serviços HTTP e registro automático no container DI.
- Adicionado pipeline de geração de páginas, serviços e modelos por Bounded Context, incluindo dashboard consolidado, navegação dinâmica e integração automática ao menu lateral.
- Criado **Scaffold Gate** bloqueante baseado em `verify_scaffold.py`, impedindo avanço da esteira quando artefatos obrigatórios estiverem ausentes.
- Implementado **Consistency Verification Gate** para validação de cobertura de BCs, rotas, Fluxor, autenticação, acessibilidade, segurança e integridade do scaffold antes do handoff.
- Implementado **Security Compliance Review Gate**, gerando `SecurityComplianceReport-Frontend.md` a partir da análise do código produzido em relação ao documento `security-architecture.md`.
- Incluída geração automática dos artefatos de entrega `ImplementationNotes.md`, `ChangedScreens.md` e relatório de conformidade de segurança frontend para consumo do `ava-stack-orchestrator`.
- Definido contrato formal de handoff com validação obrigatória de `build`, `scaffold_gate`, `security_compliance`, `trace_id` e inventário completo de artefatos gerados.

## [2026-07-13] — Summary: F1 Banco de Dados AS-IS — visão consolidada, `business-logic-in-db.md` nunca lido, 4 fallbacks AST desatualizados (Addendum D a 015-summary-remediation-agent)

## [1.1.0] — 2026-07-15

### Added (ava-prototype)

- Regras de UX baseadas nas 10 heurísticas de Nielsen-Norman (H1–H10), com instruções HTML/CSS/JS correspondentes a cada heurística
- Validação de formulários client-side usando Constraint Validation API (sem CDN): `validateForm()`, `getFieldErrorMessage()`, limpeza de erros via `form.reset()` após sucesso
- Padrões de mensagem de erro do sistema em 3 camadas: modal bloqueante (`showErrorModal()`), toast não-bloqueante (`showErrorToast()`), inline banner de degradação
- Input opcional `functional-requirements.md` (AS-IS) para enriquecer protótipo com terminologia e regras de negócio do legado
- Seção `## UX Heuristics Checklist` obrigatória no `figma-spec.md` — tabela H1–H10 × telas geradas
- Seção `## Cenários de Erro (CA03)` e `## Atalhos de Teclado (H7)` obrigatórias no `demo-script.md`
- Campos adicionais em `prototype_gate_result`: `ux_heuristics_applied`, `form_validation_applied`, `error_pattern_applied`
- RNF04: instrução explícita de deferimento de telas (status `"deferred"`) para projetos com mais de 15 telas
- Campo `skill: ava-prototype` no `module.yaml` (requisito da Constitution Article IV para agentes user-facing)
- Marcadores ★/○ (obrigatório/opcional) na seção `## Pre-Execution — Leitura Obrigatória`

### Changed (ava-prototype)

- Versão atualizada: 1.0.0 → 1.1.0 (frontmatter + module.yaml + observabilidade)
- Campo `UX rules` adicionado ao bloco de metadata HTML de rastreabilidade por tela
- Condições de `status: "PASS"` em `prototype_gate_result` expandidas para incluir `form_validation_applied` e `ux_heuristics_applied` (H1, H4, H6, H9 mínimos)
- `screen-list.md` agora documenta 3 status: `included`, `excluded`, `deferred`
- `SKILL.md` de `.github/skills/ava-prototype/SKILL.md` atualizado com leitura opcional de `functional-requirements.md` e descrição revisada

### 🐛 Fixed

- `build_summary_comprehensive.py` — 4 leituras de fallback AST corrigidas de `delphi-ast-raw/extraction/` (variante bruta/desatualizada) para `delphi-ast-raw/compressed/` (variante corrigida, mesma convenção de `specs/010-asis-agents-ast-artifact-consumption`): `_count_db_insert_points()` (`03_database_rules.json` + `04_database_schemas.json`), Source E do schema (`04_database_schemas.json`), fallback AST de Stored Procedures (`05_procedures.json`).
- `validate_summary.py` (`_c11_23`) — encontrado durante a verificação: o próprio guard de regressão do KPI "Pontos de INSERT no código" reimplementava a mesma leitura com o mesmo path desatualizado (`extraction/`), então concordaria silenciosamente com o bug do builder em vez de detectá-lo. Corrigido para `compressed/`.
- `build_summary_comprehensive.py` — `sp_biz_count_val` (KPI "SPs com Regra de Negócio") era um valor hardcoded `"0"`, nunca alimentado por nenhum parser. `business-logic-in-db.md` (4º artefato de `db-analyzer.md`) estava citado apenas no subtítulo estático da UI, nunca lido/parseado em lugar nenhum do builder.

### ✨ Added

- `build_summary_comprehensive.py` — novo `_parse_business_logic_in_db()`, alimentando o KPI real e um novo card consolidado.
- `summary-template.html` — novo card "Lógica de Negócio no Banco" (`#card-bizlogic-wrap`/`#tb-bizlogic`), consolidado na mesma seção "Banco de Dados AS-IS" junto com Schema/ER/Stored Procedures.
- `remediate_summary.py` (Fase 1, nova Regra I) — sintetiza `business-logic-in-db.md` apenas quando é provadamente seguro (0 stored procedures confirmadas em `stored-procedures-map.md`); nunca fabrica a alegação quando SPs existem mas o arquivo está genuinamente ausente (lacuna real a montante).
- `validate_summary.py` — novo `C11.35` (guarda de código-fonte: os 4 fallbacks AST nunca regridem para `extraction/`) e `C11.36` (`D.dbBizLogic` nunca vazio com findings `CRITICAL` reais).

### 🔧 Changed

- `summary-agent.md` (1.6.0→1.7.0) — Step 0 e árvore de fases do F1 "Banco de Dados" atualizados: `business-logic-in-db.md` adicionado, 3 fallbacks AST documentados com o path `compressed/` correto.
- `summary-remediation-agent.md` (1.3.0→1.4.0) — Regra I documentada (Fase 1); nova linha na tabela de heurísticas (Fase 5), guardada por `C11.35`/`C11.36`.
- Documentado em `docs/summary-io-map.md` (4 linhas de "Banco de Dados AS-IS" corrigidas + 1 nova linha para `business-logic-in-db.md`; linha "Volume BD INSERT" do Resumo Executivo também corrigida, mesmo bug de path) e `specs/015-summary-remediation-agent/spec.md`+`plan.md` (Addendum D, itens 52-55, Guardrail 9, CA11/CA12).

## [2026-07-13] ΓÇö Summary: F1 Test Baseline AS-IS ΓÇö bug de path `asis/qa/`, `test-baseline.md` nunca lido, fallback AST desatualizado, mascaramento de dados pela remedia├º├úo (Addendum C a 015-summary-remediation-agent)

### 🐛 Fixed

- `build_summary_comprehensive.py` (`build_test_map`) — causa raiz: `test-qa-asis.md` sempre grava seus 4 artefatos em `outputs/asis/qa/`, mas o builder só lia `outputs/asis/` raiz, deixando "Test Baseline AS-IS" sempre vazio em qualquer projeto real. Novo helper `_resolve_qa_artifact()` prioriza `asis/qa/`, com fallback para a raiz legada. Removida também uma chamada duplicada e inofensiva de `build_test_map()`/`build_risk_data()`/`parse_bounded_contexts()` encontrada durante a correção.
- `build_summary_comprehensive.py` — fallback AST corrigido de `delphi-ast-raw/extraction/09_test_coverage.json` (desatualizado) para `delphi-ast-raw/compressed/09_test_coverage.json`, alinhando com a convenção já estabelecida em `specs/010-asis-agents-ast-artifact-consumption`.
- `remediate_summary.py` (Fase 1, Regra C) — corrigido bug de mascaramento: a regra escrevia um placeholder falso ("nenhum teste encontrado" / "0% coverage") sempre que a raiz legada estava vazia, mesmo com dados reais presentes em `asis/qa/` ou evidência real de testes no AST JSON. Agora verifica `asis/qa/` e o AST antes de sintetizar qualquer placeholder — nunca mais mascara um bug real com dado fabricado.

### ✨ Added

- `build_summary_comprehensive.py` — novo parser de fallback para `test-baseline.md` (4º artefato de `test-qa-asis.md`, nunca lido antes), extraindo a tabela "Baseline per Module".
- `validate_summary.py` — novo `C11.34`: garante que `D.testMap` nunca fique vazio quando dados reais existem em `asis/qa/`, na raiz legada, ou no AST JSON com testes reais detectados.
- `summary-template.html` — wrapper `#card-testgaps-wrap` (paridade com `#card-testmap-wrap`, já existente) para ocultar o card "Gaps de Cobertura" quando vazio.

### 🔧 Changed

- `summary-agent.md` (1.5.0→1.6.0) — Step 0 checklist, Output HTML Structure e Data Source Mapping do F1 Test Baseline corrigidos para `asis/qa/` + os 4 arquivos + verificação do AST JSON.
- `summary-remediation-agent.md` (1.2.0→1.3.0) — Fase 1 Regra C documentada com a nova heurística; nova linha na tabela de "Heurísticas de conteúdo obrigatórias" (Fase 5), guardada por `C11.34`.
- Documentado em `docs/summary-io-map.md` (3 linhas F1/Test Baseline corrigidas de "✅ Funcional" — nunca verificado contra o Output Contract real — para o bug real + correção aplicada) e `specs/015-summary-remediation-agent/spec.md`+`plan.md` (Addendum C, itens 48-51, Guardrail 8, CA09/CA10).

## [2026-07-13] ΓÇö TO-BE: Corre├º├úo de refer├¬ncias de path quebradas (017-tobe-path-corrections)

### 🐛 Fixed

- `database-policy-tobe.md` + `orchestrator-tobe.md` — `outputs/asis/db/triggers-map.md` (fonte 7 da Política de Banco TO-BE) anotado como lacuna estrutural permanente: nenhum agente AS-IS produz este artefato sob nenhum nome (`db-analyzer.md` só grava `db-type.json`, `schema-inventory.md`, `er-diagram.mmd`, `stored-procedures-map.md`, `business-logic-in-db.md`, `db-quality-report.md`, `db-analysis-report.md`).
- `designer-system-tobe.md` — `outputs/asis/docs/screen-flow.md` corrigido para `outputs/asis/docs/screen-flow.mmd` (o skill FT de `documentation-asis.md` só produz a variante Mermaid, nunca `.md`).
- `orchestrator-tobe.md` — `outputs/asis/docs/test-plan.md` (gate F1 bridge-fastqa, Fase 7.8) corrigido para `outputs/asis/qa/test-plan.md` (segmento de diretório errado; `bridge-fastqa-asis.md` grava em `qa/`, não `docs/`).
- `test-plan-tobe.md` — 15 ocorrências de `outputs/tobe/docs/architecture-technical.md` (nenhum agente produz este nome) corrigidas para `outputs/tobe/docs/tech-framework-document.md` (o artefato real de `architecture-technical-tobe.md`).
- `user-journeys-tobe.md` — `outputs/tobe/architecture-design.md` (sem produtor) corrigido para `outputs/tobe/docs/architecture-blueprint.md`.
- `azure-infra-estimator-tobe.md` — `outputs/tobe/architecture-design-tobe.md` (sem produtor, Read Priority entrada 2) corrigido para `outputs/tobe/docs/architecture-blueprint.md`, em 6 ocorrências (Read Priority, tabela de decisão de `estimation_profile`, READ ATTEMPT LOG e 2 cenários BDD).
- `developer-guide-tobe.md` — `outputs/tobe/docs/test-plan-tobe.md` corrigido para `outputs/tobe/test-plan.md` (sem segmento `docs/`), na tabela de Input Contract e em 2 referências de prosa na Seção 7 do template.

### 🔧 Changed

- Documentado em `docs/tobe-architecture-io-map.md` (§4.6, §4.7, §4.8, §4.9, §4.11 atualizados com status de resolução; §4.16 e §4.17 novos, cobrindo os 2 bugs de referência a artefatos AS-IS encontrados nesta investigação).
- `docs/tobe-input-artifacts-existence-check.md` — nova seção de fechamento (§4) explicando que, das 85 linhas "NÃO" originalmente auditadas contra o projeto `Meu-ERP-008-AST-LLM-Master-Orchestrator`, apenas 7 eram bugs de path genuínos (as demais refletem um projeto gerado por convenção de path anterior à consolidação atual dos Output Contracts, ou fases simplesmente não executadas naquele projeto).
- 7 agentes com bump PATCH (bugfix pontual, sem mudança de forma de Input/Output Contract): `orchestrator-tobe.md` (2.4.0→2.4.1), `database-policy-tobe.md` (1.0.0→1.0.1), `designer-system-tobe.md` (1.0.0→1.0.1), `test-plan-tobe.md` (3.2.0→3.2.1), `user-journeys-tobe.md` (1.0.0→1.0.1), `azure-infra-estimator-tobe.md` (1.1.0→1.1.1), `developer-guide-tobe.md` (1.1.0→1.1.1).

## [2026-07-12] ΓÇö TO-BE: Guardrail de consumo exclusivo de artefatos + escalonamento de artefato ausente (016-tobe-artifact-only-guardrail)

### ✨ Added

- Novo arquivo de governança `src/modules/ava-fabric-agents/shared/artifact-only-consumption-protocol.md` (`@artifact-only-consumption-protocol`), aplicado por `orchestrator-tobe.md` e todos os 20 agentes despachados em `tobe-architecture/agents/`: (1) proíbe releitura de código-fonte legado (`repository_path`, `.pas`/`.dfm`/`.dpr`) e varredura arquivo-a-arquivo de `outputs/tobe/source-code/` já gerado; (2) padroniza o relatório de escalonamento `⛔ [ARTIFACT GATE FAILED]` para artefato de entrada obrigatório ausente — com Opção A/B/C e aguardando aprovação explícita do usuário — substituindo o degrade silencioso/hard-stop sem relatório usado até então de forma inconsistente entre agentes.
- Nova seção `## Dispatch Protocol` em `orchestrator-tobe.md`, exigindo `Read()` da spec completa de cada sub-agente antes do despacho — espelha o fix de `specs/013-master-orchestrator-mandatory-spec-read`, agora fechando a mesma lacuna na esteira TO-BE (F2), sinalizada como PBI futuro na seção de Exclusions daquela spec.

### 🐛 Fixed

- `risk-mitigation-tobe.md` — path de input `outputs/tobe/migration-plan.md` corrigido para `outputs/tobe/docs/migration-plan.md` (segmento `docs/` ausente fazia o input nunca resolver).
- `azure-infra-estimator-tobe.md` — Read Priority path (1) corrigido de `outputs/tobe/sizing-report.md` para `outputs/tobe/docs/sizing-report.md`.

### 🔧 Changed

- `test-plan-tobe.md` — input `architecture-technical.md` reclassificado de obrigatório para não-bloqueante (nenhum agente produz esse arquivo; o rótulo agora reflete o degrade que já ocorria na prática).
- `designer-system-tobe.md` — input `outputs/asis/docs/screen-flow.md` revisado; já era não-bloqueante (enriquecimento de prioridade 5, fora do `## Gate`), nenhuma mudança de comportamento necessária.
- Documentado em `docs/tobe-architecture-io-map.md` (§3, §4.4, §4.6, §4.7, §4.8).

## [2026-07-12] ΓÇö Summary: Step 0 (leitura obrigat├│ria por fase), elimina├º├úo de dados est├íticos/hardcoded, fix de `load_project_config()` (Addendum B a 015-summary-remediation-agent)

### 🐛 Fixed

- `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` — `load_project_config()` usava um parser de linha via regex que (a) descartava silenciosamente qualquer chave com comentário `# ...` no final da linha — praticamente todos os campos em um `project-config.yaml` real — e (b) nunca conseguia interpretar seções YAML aninhadas (`tobe_stack:`, `architecture_patterns:`, etc. sempre resolviam para `{}`). Isso degradava `SCOPE`, `LEGACY_TECH`, `TOBE_BACKEND_VERSION`, `TOBE_FRONTEND_VERSION` para os valores hardcoded default, independente da configuração real do projeto. Corrigido para usar `yaml.safe_load()` (PyYAML, já dependência do módulo), com o parser regex mantido apenas como fallback quando PyYAML não está disponível. Verificado: um `project-config.yaml` real com 34 chaves de nível superior e um bloco `tobe_stack` aninhado, antes reduzido a um dict quase vazio, agora é interpretado corretamente na íntegra.
- "Volume BD INSERT" (KPI Resumo Executivo/F1) sempre exibia `N/D` — nenhum parser jamais existiu. Nova `_count_db_insert_points()` conta operações `insert` em `03_database_rules.json`, com fallback em `04_database_schemas.json`.
- F1: card "Identified Patterns" e 9 campos de Security Review (OWASP compliance, achados suplementares) eram parseados em `D.*` mas nunca renderizados — restaurados via `renderPatterns()`, novo `renderOwaspCompliance()`/`renderSecuritySupplemental()`.
- F2: pacotes NuGet, Quality Gates, KPIs de Sizing, Effort by BC, Sizing Azure, Migration Waves, Test Plan e pills de Stack&Patterns eram arrays hardcoded literais no template — substituídos por placeholders `{{X_JSON}}` populados por 11 novas funções de parsing.
- F3/F4/F5: chips de protótipo eram lista fixa hardcoded; títulos de Backend/Frontend usavam nome de framework literal; tabelas de Cenários & Casos e Evidências ficavam permanentemente vazias (sem parser) — corrigidos com glob real, placeholders de versão e novos parsers (`parse_scenario_register`, `parse_defects`).
- F6/F7: `ARTIFACT_MAP` divergia do `## Output Contract` real de 6 agentes, causando status "ausente" falso; dados de IaC/CI/CD e a tabela de Security Compliance eram hardcoded/mortos; checklists de Pre-Delivery/Acceptance eram sempre "verde" independente de evidência real; nav dots de F6/F7 nunca acendiam (bug de troca de chaves no `dotMap`). Todos corrigidos — checklists agora honestos (`false` quando não há evidência).

### ✨ Added

- **Step 0 — Leitura Obrigatória de Artefatos**: `summary-agent.md` e `summary-remediation-agent.md` agora abrem com um checklist explícito `Read: {path}` por fase (Resumo Executivo, F1–F7), derivado de `docs/summary-io-map.md`, tornando auditável quais arquivos cada fase é contratualmente obrigada a ler antes de gerar sua seção do HTML.
- `validate_summary.py` — `C11.22`–`C11.33` (12 novas regras) guardando contra regressão de todos os itens acima: placeholders derivados de config resolvidos e cruzados com `project-config.yaml` (C11.22), Volume BD INSERT data-driven (C11.23), card Patterns religado (C11.24), 9 campos de segurança com caminho de renderização (C11.25), paleta VCL não revertida ao hardcode antigo (C11.26), dados F2 via placeholders `{{X_JSON}}` (C11.27), títulos Backend/Frontend dinâmicos (C11.28), tabelas Scenarios/Defects religadas (C11.29), mapeamento nav-dot F6/F7 correto com auto-fix (C11.30), dados F6/F7 IaC/CI/CD/security-report não hardcoded (C11.31), checklists de entrega não "sempre verde" (C11.32), chips de protótipo não revertidos a lista fixa (C11.33).

### 🔧 Changed

- Total de regras únicas do validador: 86 → **97**.
- `summary-agent.md` v1.4.0 → v1.5.0, `summary-remediation-agent.md` v1.1.0 → v1.2.0.
- Documentado como Addendum B em `specs/015-summary-remediation-agent/spec.md` (spec existente atualizada, sem nova spec).

- `parse_tobebn()` (`build_summary_comprehensive.py`) ΓÇö encontrado durante a revalida├º├úo de ponta a ponta: `Meu-ERP-002` tem `tobe/docs/regras-negocio.md` real, mas em um formato de se├º├╡es ("## Business Rules Preservation Map" / `### BC-NN ΓÇö Nome` / tabela `BR-NNN`) diferente do que o parser reconhecia (`## M├⌐tricas`, `RN-BCxx-yy`) ΓÇö como o arquivo n├úo estava vazio, o fallback para AS-IS nunca era acionado, deixando `D.tobebn` silenciosamente vazio (`C11.16`). Corrigido: quando o arquivo existe mas nenhuma se├º├úo reconhecida ├⌐ encontrada (`metrics`/`traceability` ambos vazios), aplica o mesmo fallback AS-IS usado para arquivo ausente.

### ✅ Verification

- `build_summary_comprehensive.py`: sintaxe válida (`ast.parse`), rebuild limpo (`✅ SUCCESS!`, zero placeholders não resolvidos) em `Meu-ERP-008-AST-LLM-Master-Orchestrator`, `Meu-ERP-001`, `Meu-ERP-002`, `Meu-ERP-004`.
- `summary-template.html`: divs balanceadas (807 abertura / 807 fechamento).
- `validate_summary.py` ΓÇö revalida├º├úo completa nos 4 projetos afetados por este engagement:
  - **Meu-ERP-008-AST-LLM-Master-Orchestrator**: 98 passed, 0 warnings, 0 errors.
  - **Meu-ERP-002**: 98 passed, 0 warnings, 0 errors (ap├│s o fix de `parse_tobebn()` acima).
  - **Meu-ERP-004**: 98 passed, 0 warnings, 0 errors.
  - **Meu-ERP-001**: 97 passed, 0 warnings, 1 erro pr├⌐-existente e n├úo relacionado (`C2.2`, `complexity-map.md` ausente ΓÇö requer re-execu├º├úo de `ava-asis-inventory`, n├úo ├⌐ um bug de exibi├º├úo do Summary).

## [2026-07-12] ΓÇö Summary: contagem exata de riscos, Eventos "em desenvolvimento", garantia de credibilidade do agente de remedia├º├úo (Addendum A.2 a 015-summary-remediation-agent)

### 🐛 Fixed

- `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` — `C11.20` estava apenas verificando "não vazio"; fortalecida para comparar a contagem exata de itens de `D.risks` contra a contagem real no arquivo-fonte (`risk-register.json`/`.md`), detectando também sub/super-contagem, não só o caso vazio.
- `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` — `sanitize_mmd()`: nova sub-regra na "Compatibility Rule 2" para o padrão `+setters/getters()` (chamada de método composta separada por `/`, sem `: ...`) — a regra existente só cobria `+setters/getters: ...`. Corrigido em `Meu-ERP-004` (`component-diagram.mmd`, na verdade um `classDiagram`).
- `parse_func_reqs()` (`build_summary_comprehensive.py`) — o "Format 3" (headers `### FR-NNN: Título`) exigia IDs no formato `FR-\d+` puro; IDs com prefixo de módulo (`FR-CP-01`, `FR-CR-01`, formato real usado por `ava-asis-documentation` em `Meu-ERP-004`) nunca eram reconhecidos, então `D.funcReqs` ficava sempre vazio (12 requisitos reais, 0 exibidos). Regex corrigida para aceitar o segmento de módulo opcional, igual ao padrão já usado em `parse_biz_rules()`.
- **Gap de processo identificado pelo usuário**: um fix documentado e correto a nível de código (Addendum A) não repara retroativamente um projeto até o agente de remediação ser de fato re-executado contra ele — `Meu-ERP-001` ainda exibia o erro de parse Mermaid em `diag-solution` (`# Ex: "Meu-ERP", "Projeto-X"` vazado) numa build gerada _depois_ do Addendum A, porque o arquivo `solution-structure.mmd` corrompido (sintetizado antes do fix) nunca tinha sido re-sanitizado. Confirmado: a autocura já funcionava (Fase 3), só faltava a execução.

### ✨ Added

- Menu F1-AS-IS → "Eventos, Filas & Pub/Sub" nunca mais exibe uma grade de KPIs zerada + tabela vazia — quando `D.events` está vazio, exibe "Essas informações estão em desenvolvimento e serão exibidas no futuro." (`renderEvents()`, novo `#events-empty-state`, i18n `msg-events-wip`). Nova regra `C11.21`.
- **Heurísticas de conteúdo documentadas explicitamente** em `summary-remediation-agent.md` (Fase 5): (1) contagens exibidas devem sempre igualar a contagem real no arquivo-fonte; (2) menus sem dado coletado devem comunicar "em desenvolvimento", nunca uma grade de zeros.
- **Guardrail de credibilidade (novo, Fase 7)**: o agente de remediação só pode emitir "✅ Concluído" quando `errors_after == 0`. Caso contrário, emite "⚠️ Concluído com pendências" listando cada erro remanescente — nunca mais declara sucesso com um diagrama quebrado ou menu incorreto ainda presente. `remediate_summary.py` atualizado para refletir essa regra no sinal de conclusão (antes sempre imprimia "✅ Concluído" independente do resultado).

### 🔧 Changed

- Total de regras do validador: 85 → **86**.
- `summary-agent.md` v1.3.0 → v1.4.0, `summary-validate-agent.md` v1.2.0 → v1.3.0, `summary-remediation-agent.md` v1.0.0 → v1.1.0.
- Documentado como Addendum A.2 em `specs/015-summary-remediation-agent/{spec,plan,tasks}.md` (spec existente atualizada, sem nova spec).

### ✅ Verification — agente de remediação executado em sua totalidade

Rodado `ava-summary-remediation` de ponta a ponta contra os 4 projetos afetados, cada um revalidado até `errors_after == 0` (ou pendência genuína e legítima reportada honestamente):

- **Meu-ERP-008-AST-LLM-Master-Orchestrator**: ✅ 0 erros.
- **Meu-ERP-004**: ✅ 0 erros (após corrigir os 2 bugs reais acima).
- **Meu-ERP-002**: ✅ 0 erros, 0 warnings (inclusive resolveu uma limitação conhecida anterior via auto-fix).
- **Meu-ERP-001**: ⚠️ 1 pendência genuína (`C2.2` — `complexity-map.md` ausente, requer re-execução de `ava-asis-inventory`; não é um bug de exibição). O erro específico reportado pelo usuário (`diag-solution` Mermaid parse error) está **confirmado eliminado** — 0 ocorrências de `# Ex:`/aspas corrompidas em nenhum dos 4 HTMLs finais.

## [2026-07-12] ΓÇö Summary: Risk Register sempre zerado em projetos do pipeline AST (Addendum A.1 a 015-summary-remediation-agent)

### 🐛 Fixed

- `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` — `build_risk_data()` só lia `risk-register.json`; o pipeline de extração AST (ex: AST-LLM Master Orchestrator) produz `risk-register.md` em vez de `.json`, então o menu F1-AS-IS → Riscos sempre exibia "0 RISCOS" mesmo com o registro de riscos totalmente preenchido. Adicionado `_parse_risk_register_md()` — parser de tabela markdown orientado por cabeçalho (tolerante a reordenação/ausência de colunas), usado como fallback sempre que `risk-register.json` estiver ausente ou vazio; extrai opcionalmente um resumo de mitigação de subseções `### RISK-NNN: Título` / `**Mitigation:**` quando existem. `CAT_MAP` estendido com as categorias adicionais desse formato (Testing, Data, Business Rule, Integration).
- `src/modules/ava-fabric-agents/summary/utils/validate_summary.py` — nova regra `C11.20`: garante que `D.risks` não fique vazio sempre que `risk-register.json` OU `risk-register.md` tiver dados reais. Total de regras: 84 → **85**.
- Contagem de regras atualizada em `summary-agent.md` (v1.2.0 → v1.3.0) e `summary-validate-agent.md` (v1.1.0 → v1.2.0).
- Documentado como Addendum A.1 em `specs/015-summary-remediation-agent/{spec,plan,tasks}.md` (spec existente atualizada, sem nova spec, conforme instrução explícita).

Verifica├º├úo: `Meu-ERP-008-AST-LLM-Master-Orchestrator` ΓÇö 17/17 riscos agora populados corretamente no Risk Register, `validate_summary.py` 85/85 checks, 0 erros; agente de remedia├º├úo re-executado de ponta a ponta ΓÇö idempotente, 0 pend├¬ncias. `Meu-ERP-002` (fonte `.json` pr├⌐-existente) ΓÇö sem regress├úo, mesmas 2 falhas pr├⌐-existentes e n├úo relacionadas de antes (`C3.7`, `C11.16`).

## [2026-07-10] ΓÇö Summary: corrige corrup├º├úo de diagramas Mermaid, KPIs N/D e integra pipeline de extra├º├úo AST (Addendum a 015-summary-remediation-agent)

### 🐛 Fixed — bug crítico compartilhado em `sanitize_mmd()`

- `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` — `sanitize_mmd()` → `_fix_seq_alias()` não era idempotente: toda re-execução (build ou remediação) sobre um alias `actor X as "Nome"` já entre aspas adicionava 2 caracteres de aspas por lado, corrompendo progressivamente diagramas de sequência (`"Nome"` → `"'Nome'"` → `"'''Nome'''"` → ...; um caso real chegou a 9 aspas por lado). Corrigido removendo qualquer aspas pré-existente antes de processar — também autocura arquivos já corrompidos em uma única passada, verificado contra um arquivo real de produção.
- Placeholder `{{ASIS_ARCH_BLUEPRINT_DIAGRAM}}` nunca foi ligado a nenhuma fonte (apenas o equivalente TO-BE existia) — o diagrama "Blueprint Architecture" AS-IS renderizava como caixa vazia. Adicionada a substituição faltante lendo `asis/diagrams/architecture-blueprint.mmd`.
- KPIs "Complexidade ≥10"/"Camadas"/"Módulos" exibindo `N/D` mesmo com dados reais disponíveis: `COMPLEX_METHODS` procurava um campo inexistente (`high_complexity_methods` em vez de `highest_cc_files`) e usava o padrão `x or "N/D"`, que trata um `0` legítimo como "sem dado"; `LAYER_COUNT` procurava `bounded_contexts` em vez do `layer_breakdown` do pipeline AST; `MODULE_COUNT` tinha a mesma armadilha de truthiness. Corrigido o mapeamento de campos e substituído o padrão por um helper `_first_not_none()`.
- `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py` — `_read_project_config()` capturava o comentário YAML inteiro (`# Ex: "Meu-ERP", "Projeto-X"`) junto com o valor de `project_name`, vazando texto de comentário para dentro de diagramas TO-BE sintetizados (erro de parse Mermaid `Expecting ... got 'STR'`). Corrigido para parar em um `#` não citado.
- O marcador de proveniência `# synthesized-by-FS` era escrito como primeira linha literal de arquivos `.mmd` sintetizados, quebrando a detecção de tipo de diagrama do Mermaid ("No diagram type detected") — movido para um comentário `%%` (sintaxe válida do Mermaid) ao final do arquivo. Fase 3 do agente de remediação agora também detecta e corrige esse padrão legado em arquivos já existentes (`_repair_legacy_leading_tag`, `_repair_leaked_yaml_comment` — nova **Guardrail 7**, exceção estreita à regra de nunca sobrescrever `outputs/`: só repara arquivos que carregam a própria tag de proveniência do agente).
- Gap List: gaps com `severity: "P0".."P3"` nunca eram mapeados para o campo de complexidade, fazendo gaps críticos (P0) serem exibidos como severidade média e sub-contados no Migration Risk Score.

### ✨ Added — integração opcional com o pipeline de extração AST

- Quando `outputs/asis/delphi-ast-raw/extraction/*.json` existe (pipeline de extração AST mais recente), os seguintes trechos passam a usar essa fonte como fallback adicional, sem nunca assumir sua presença nem hardcodar projeto/stack: Fluxo de Telas (`02_form_business_rules.json`), novo card "LOC by Bounded Context" em Inventário & Métricas (`inventory.md`), Test Baseline (`09_test_coverage.json`), Banco de Dados AS-IS — Schema Inventory e Stored Procedures (`04_database_schemas.json`, `05_procedures.json`).

### 🔧 Changed — limpeza de UI e regras de ocultação

- Unificadas as listas de ocultação de KPI (`KPI_HIDDEN_IF_ZERO`/`KPI_HIDDEN_IF_ND` → `KPI_HIDDEN_IF_EMPTY`, mesmo para a faixa de KPIs de BD e de Inventário) e estendida para cobrir `kpi-layers`/`kpi-modules` — qualquer tile com valor `0` ou `N/D` agora é removido da visualização, não apenas os 7 originais.
- Removidas permanentemente as tabelas "Arquivos por Tipo", "Estrutura de Camadas" e "Complexidade Ciclomática" do template (`D.ccTop` continua populado e validado por C2.2/C2.10, apenas deixou de ser renderizado).
- `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`: novas regras `C11.18`/`C11.19` (guardam a remoção das duas tabelas), `C11.10` reescrita para exigir ausência total da tabela de Complexidade Ciclomática, `C11.1`/`C11.2` reescritas para verificar o mecanismo de guarda (`KPI_HIDDEN_IF_EMPTY`) em vez do valor bruto pré-filtro. Total de regras: 82 → **84**.
- Contagem de regras atualizada em `summary-agent.md` e `summary-validate-agent.md`.
- Documentado como Addendum A em `specs/015-summary-remediation-agent/{spec,plan,tasks}.md` (spec existente atualizada, sem nova spec).

Verifica├º├úo: rebuild + valida├º├úo completa em `Meu-ERP-008-AST-LLM-Master-Orchestrator` (projeto com pipeline AST) ΓÇö 84/84 checks, 0 erros, 0 warnings; e em `Meu-ERP-001` (sem pasta AST) ΓÇö build ok, sem regress├úo (├║nicas 2 falhas remanescentes s├úo pr├⌐-existentes e fora de escopo: `complexity-map.md` ausente e diagrama gantt removido por feature anterior).

## [2026-07-09] ΓÇö ava-summary-remediation: novo agente de reparo p├│s-pipeline + 22 corre├º├╡es de exibi├º├úo no Summary

### ✨ Added — `ava-summary-remediation` (novo agente, F8/Summary)

- `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md` (v1.0.0, NOVO): agente independente de reparo pós-pipeline — audita um Summary HTML já gerado (ou artefatos incompletos em `outputs/`), resolve o que for seguro sem re-executar agentes upstream, reconstrói via `build_summary_comprehensive.py` e revalida via `validate_summary.py`. Fases 0–7 (auditoria, resolução de artefatos, síntese de diagramas, sanitização Mermaid, reconciliação de segurança, guardas de conteúdo/UI, rebuild, relatório).
- `.github/skills/ava-summary-remediation/SKILL.md` (NOVO): rotina de skill padrão (resolve `project_name`, delega ao agente).
- `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py` (NOVO): implementação Python das Fases 0–7; reaproveita `sanitize_mmd()` de `build_summary_comprehensive.py` e roda o validador em processo (`_load_ctx`/`_run_checks`/`_try_auto_fix`/`_format_json`) já que `validate_summary.run_all()` não persiste `validation-report.*` em disco. Escreve `remediation-report.md`/`.json`.
- Registrado em `src/modules/ava-fabric-agents/summary/module.yaml` (v1.0.0 → v1.1.0) e em `.github/copilot-instructions.md` (tabela F8 — Summary).

### 🔧 Changed — 22 problemas de exibição corrigidos permanentemente no builder/template/validador

- `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html`:
  - `renderKPIs()` oculta os tiles Classes/M├⌐todos/Complexidade/Endpoints/Telas-Forms quando `0` e Tabelas BD/Volume BD Insert quando `N/D`.
  - Removido permanentemente o tile "Componentes (fcid)", a coluna ID da tabela de Riscos (`R-???` quebrado), o card "Rules Categories", o card+tab "Screen Rules", o card "Artefatos ΓÇö AG-10" (Blueprint C4), os tiles Aprovados/Padr├╡es DDD/Squad e a tabela "BCs Refinados" (Bounded Context TO-BE).
  - `renderBC()`, `renderReqsTable()`/`renderRulesTable()`, `renderInvKpis()`, `renderTestTables()`, `renderDBKpis()`/`renderDBSchema()` agora ocultam colunas/submenus/cards vazios (Bounded Context Map AS-IS, Functional Requirements, Business Rules, Inventory & Metrics, Test Baselines, Banco de Dados AS-IS).
  - Removido o token `AG-NN` (fora de ordem/incorreto) de todas as bylines de card, t├¡tulos de card i18n e do array `AGENTS[]` (Phase Tracking) ΓÇö mantendo os identificadores internos (`ag01-role`, `chips-ag02`, etc.) intocados.
- `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`:
  - `parse_tobebn()` agora recebe fallback de `D.bizRules` (AS-IS) quando `tobe/docs/regras-negocio.md` est├í ausente/vazio ΓÇö Regras de Neg├│cio TO-BE deixa de ficar vazia mesmo quando as regras j├í foram capturadas no AS-IS.
  - Removido `value-chain` da classifica├º├úo de Deliverables (`_classify` em `build_file_tree`).
  - Corrigidos dois bugs reais no parser de `complexity-map.md`: regex de header muito restritiva (n├úo reconhecia `## Method Complexity by Module`) e checagem de fim-de-se├º├úo que confundia `###` com `##`, zerando `D.ccTop` em projetos com esse layout.
- `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`: nova categoria **C11 ΓÇö Content Completeness & UI Cleanup** (`C11.1`ΓÇô`C11.17`, 6 com auto-fix), guardando regress├úo de todos os itens acima. Total de regras: 65 ΓåÆ **82**.
- `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md` (v1.1.0, NOVO campo version/date) e `summary-agent.md` (v1.1.0 ΓåÆ v1.2.0): contagem de regras e cat├ílogo atualizados (`~55` ΓåÆ `82`); tabela de categorias esclarece que C10 (Security Schema) permanece documentada mas n├úo implementada (debt pr├⌐-existente, fora de escopo desta feature).
- Documentado via SpecKit em `specs/015-summary-remediation-agent/{spec,plan,tasks}.md`.

## [2026-07-07] — Unicode-Safe Regex Guardrail (007)

### Changed

- G10: added `ValidationException` class to SharedKernel exception hierarchy (`sealed class ValidationException : DomainException` → HTTP 400)
- G10: added `ValidationException` arm to `GlobalExceptionHandler.TryHandleAsync` switch expression (inserted before `DomainException` — required for correct C# pattern-match ordering)
- Routing guard: updated stale "G1-G9 existentes" to "G1-G10 existentes"

### 🐛 Fixed

- `ava-stack-dotnet-backend` v1.0.0 → v1.0.1 — Guardrail **G10**: padrão `[a-zA-Z]` proibido para campos de texto PT-BR; `\p{L}` obrigatório em `[RegularExpression]`. Nomes como José, João, Márcia são agora aceitos pelo modelo gerado.
- `ava-stack-angular-frontend` v1.0.0 → v1.0.1 — **GUARDRAIL (Unicode Regex PT-BR)**: `/^[a-zA-Z\s]+$/` proibido em `Validators.pattern`; `/^[\p{L}\s\-']+$/u` obrigatório. One-liner adicionado à lista de princípios técnicos.

### ✨ Added

- `angular-patterns-reference.md` v1.0.0 → v1.0.1 — Nova seção **PT-BR Validation Patterns** com tabela de padrões canônicos para Angular (`Validators.pattern + flag u`) e C# (`[RegularExpression] + \p{L}`), incluindo CPF, CNPJ, CEP, telefone e e-mail. cada agente registra suas próprias métricas

---

## [2026-07-03] — Agent Self-Observability: cada agente registra suas próprias métricas

### ✨ Added — `pipeline_observer.py` — snapshot por agente

- `src/shared/tools/pipeline_observer.py`: `cmd_track` agora também grava um snapshot individual em `projects/{project_name}/outputs/observability/{agent_name}/metrics.json` + `events.jsonl`, além do estado agregado já existente. Totalmente retrocompatível — nenhuma mudança de sintaxe para quem já chama `track`.
- `src/modules/ava-fabric-agents/shared/observability-self-report.md` (NOVO): documento de governança compartilhado, no mesmo padrão de `@governance-apps`, definindo como qualquer agente se auto-registra (incluindo fallback para invocação standalone e isolamento de falhas — observabilidade nunca bloqueia a tarefa principal do agente).
- Referência `> Apply: [@observability-self-report](...)` inserida em 97 de 101 arquivos de agente (todos os módulos F1–F8 + prototype + master-orchestrator). Excluídos: os 4 arquivos `db-analyzer/skills/*.md` (inline, não despachados independentemente).
- Corrigido crash de encoding Unicode (`UnicodeEncodeError` em consoles Windows `cp1252`) nos comandos `dashboard`/`finalize --auto-report`/`report` de `pipeline_observer.py` e `agent_observability.py`.

## [2026-07-03] ΓÇö PBI-2076: Fix adr-tobe output path ambiguity, slug naming lock e gate F2

### 🐛 Fixed

- `src/modules/ava-fabric-agents/tobe-architecture/agents/adr-tobe.md` — v1.0.0 → v1.1.0:
  - **Falha 1 (output path):** todas as 13 ocorrências de `docs/decisions/` corrigidas para o path absoluto `projects/{project_name}/outputs/tobe/docs/decisions/` — eliminada a ambiguidade que fazia o LLM gravar em `outputs/tobe/decisions/` em vez de `outputs/tobe/docs/decisions/`.
  - **Falha 2 (slug naming):** adicionado aviso CANÔNICO IMUTÁVEL no checklist e na seção Guardrails. Os 8 slugs são agora listados explicitamente e declarados indisponíveis para reordenação ou derivação de conteúdo. Removida formulação genérica `ADR-{NNN}-{kebab-slug}.md`.
- `src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md` — v2.1.0 → v2.2.0:
  - **Falha 3 (gate silencioso):** gates de entrada das Fases 1.4 e 1.5 reforçados de simples "interromper e alertar" para blocos `⛔ HARD STOP` com invariante absoluta explícita — proibindo o LLM de continuar o pipeline, invocar agentes downstream ou reportar COMPLETE quando o ADR-002 está ausente.
- `src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md` — v1.1.0 → v1.2.0:
  - **F3 Scaffold Gate (novo):** step 3.3 expandido de verificação única de `README.md` para 3 sub-checks com `verify_scaffold.py`: README sentinela + scaffold backend (manifest derivado de `tobe_stack.backend_framework`) + scaffold frontend (manifest derivado de `tobe_stack.frontend_framework`). Qualquer falha → `⛔ HARD STOP` com mensagem de diagnóstico, retry (max 2x) e Human Gate. Resolve o problema de frontend/backend não sendo criados sem detecção.

---

## [2026-06-22] ΓÇö ava-build-cycle-java-scaffold: implementa├º├úo completa

### ✨ Added

- `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-java-scaffold.md` — agente `ava-build-cycle-java-scaffold` implementado (v1.0.0). Equivalente Java do `build-cycle-dotnet-scaffold-agent.md`. Cobre: Routing Guard, Dependency Validation Gate (Step 0), leitura de contexto com override resolution, resolução de versões via Maven Central API (sem fallback silencioso), geração de parent pom.xml (BOM), módulos SharedKernel e Contracts, 4 módulos por BC (domain/application/infrastructure/api), módulo Host com `spring-boot-maven-plugin` exclusivo, módulos de testes (unit + integration com Testcontainers), docker-compose multi-vendor (PostgreSQL/MySQL/SQLServer + Redis), Security Gate estrutural e KeyVaultOnboarding.md. `implementation.status: COMPLETED`.

### 🔧 Changed

- `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` — v1.2.0 → v1.3.0: routing build-cycle `spring-boot` atualizado de `[java-scaffold 🚧 STUB, java-persistence 🚧 STUB]` para `[java-scaffold, java-persistence 🚧 STUB]`; adicionada referência ao template `build-cycle-java-scaffold.md`.
- `src/modules/ava-fabric-agents/tech-stack/agents/coder-java-backend.md` — v1.0.0 → v1.1.0: Routing Guard atualizado de "fallback automático para generic" para `⛔ STOP` com redirecionamento explícito para `@ava-build-cycle-java-scaffold` (agora implementado).
- `src/shared/data/stub-registry.yaml` — `build-cycle-java-scaffold`: `status: STUB` → `status: COMPLETE`; removido `# to be created`; notes atualizadas. `coder-java-backend` notes atualizadas. Summary: 17 → 16 stubs.

---

## [2026-07-02] ΓÇö ava-devops-iac-k8s-native v1.0.0: Implementa├º├úo completa do agente IaC Kubernetes-Native

### Γ£¿ Added

- **`src/modules/ava-fabric-agents/devops-agents/agents/iac-k8s-native-agent.md`** (v0.1.0-stub ΓåÆ v1.0.0)
  - Stub substitu├¡do por agente completamente implementado
  - 10 CRITICAL INVARIANTS (CI-K1ΓÇªCI-K10): caminho de sa├¡da, ambientes dev/hml/prd, proibi├º├úo de segredos inline, containers non-root, tags de imagem fixadas, resource limits, NetworkPolicy deny-all, health probes, image pull secrets, divis├úo do Helm chart
  - Routing Guard: detecta artefatos K8s existentes e solicita confirma├º├úo antes de sobrescrever
  - Contrato de Entrada espelhando `iac-azure-agent.md`: `project_name`, `registry`, `image_tag`, `secret_store`, `secret_store_ref`, `trace_id`
  - Cat├ílogo completo de recursos K8s: Namespace, ServiceAccount, RBAC, Deployment (backend + frontend), Service, HPA, PDB, Ingress, ConfigMap, ExternalSecret (ESO v1beta1), NetworkPolicy, ServiceMonitor
  - 14 templates Helm com todos os padr├╡es de seguran├ºa mandat├│rios (`readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `topologySpreadConstraints`)
  - Kustomize overlays para `dev`, `hml`, `prd` com patches de r├⌐plicas e recursos por ambiente
  - Values files separados por ambiente: `values-dev.yaml`, `values-hml.yaml`, `values-prd.yaml`
  - 6 Passos de Execu├º├úo com verifica├º├úo de depend├¬ncias (Γ¢ö BLOQUEADO) e gate de depend├¬ncia bloqueante
  - Bloco de handoff ao orquestrador: `implementation.status: COMPLETED`
  - Suporte a 4 secret stores: `azure-keyvault`, `aws-secrets-manager`, `hashicorp-vault`, `kubernetes`
  - Gatilhos: `IK` (completo), `IKH` (Helm only), `IKK` (Kustomize only), `IKV` (validar), `IKD` (diff)

- **`.github/skills/ava-devops-iac-k8s-native/SKILL.md`** ΓÇö criado (Step 2 do protocolo de registro de agente)
  - Wrapper de roteamento seguindo o padr├úo de `ava-devops-iac-azure/SKILL.md`

### ≡ƒöº Changed

- **`.github/copilot-instructions.md`** ΓÇö `@ava-devops-iac-k8s-native` adicionado ├á tabela F6 DevOps
- **`src/shared/data/stub-registry.yaml`** ΓÇö `id: iac-k8s-native` atualizado: `status: STUB` ΓåÆ `status: COMPLETE`; campo `completed_date: "2026-07-02"` adicionado
- **`src/modules/ava-fabric-agents/master-orchestrator/agents/master-orchestrator.md`** ΓÇö removido coment├írio `# ≡ƒÜº STUB` da linha de dispatch de `@ava-devops-iac-k8s-native`

---

## [2026-07-25] ΓÇö Unify `ava-test-plan-tobe` and retire the former consolidated test-plan agent

### ≡ƒöº Changed

- **`src/modules/ava-fabric-agents/tobe-architecture/agents/test-plan-tobe.md`** ΓÇö bumped to **v5.0.0**. Absorbed responsibilities, inputs and outputs from the former consolidated test-plan agent:
  - Input Contract now uses `outputs/asis/docs/regras-negocio.md` (fallback `business-rules.md`) as canonical BR/FR source and adds optional enrichers: OpenAPI specs, coexistence strategy, user journeys, risk-mitigation-plan, AS-IS `test-cases.md` and `gap_analysis.md`.
  - Output Contract expanded to six artifacts: `test-plan.md`, `test-cases.md`, `gap-analysis.md`, `functional-test-matrix.md`, `traceability-matrix.md`, `automatable-test-cases.md`.
  - New Step 1f loads enrichers; Steps 5b.2 and 5c materialize `test-cases.md` and `gap-analysis.md`.
  - Canonical template expanded from 16 to 18 sections, adding §10 Coexistence Tests and §11 Risk-Based Tests.
  - Pipeline Validation YAML synchronized to validate all 18 sections.

### β£ Removed

- **`src/modules/ava-fabric-agents/tobe-architecture/agents/test-plan-consolidated-tobe.md`** ΓÇö deleted; logic merged into `test-plan-tobe.md`.
- **`.github/skills/ava-tobe-test-plan-consolidated/SKILL.md`** ΓÇö deleted.

> The legacy agent ID was `ava-tobe-test-plan-consolidated`; it is now superseded by `ava-test-plan-tobe` v5.0.0.

### ≡ƒöº Changed

- **`src/modules/ava-fabric-agents/tobe-architecture/agents/orchestrator-tobe.md`** ΓÇö removed Fase 7.8 and all references to the retired consolidated test-plan agent. Updated execution order and fallback phase lists.
- **`src/modules/ava-fabric-agents/tobe-architecture/module.yaml`** ΓÇö removed consolidated agent entry; version bumped `1.3.1` ΓåÆ `1.3.2`.
- **`src/modules/ava-fabric-agents/qa-agents/agents/bridge-fastqa-tobe.md`** ΓÇö upstream for `test-cases.md` updated to `ava-test-plan-tobe`.
- **`src/modules/ava-fabric-agents/qa-agents/agents/qa-orchestrator-agent.md`** ΓÇö FQ pre-condition now points to `@ava-test-plan-tobe` trigger `TP`.
- **`docs/tobe-architecture-io-map.md`** ΓÇö removed Fase 7.8 row and consolidated agent references.
- **`docs/tobe-input-artifacts-existence-check.md`** ΓÇö removed Fase 7.8 entries.
- **`docs/plan/guarail-artifact-only-tobe-orchestrator.md`** ΓÇö removed consolidated agent from agent list.
- **`specs/016-tobe-artifact-only-guardrail/spec.md`** and **`specs/016-tobe-artifact-only-guardrail/tasks.md`** ΓÇö removed consolidated agent references.
- **`specs/028-tobe-orchestrator-v280/spec.md`** ΓÇö marked the consolidated test-plan agent as superseded by `ava-test-plan-tobe` v5.0.0.

---

## [2026-07-01] ΓÇö Reliability pipeline: Podman/MSYS2, CVE exceptions, lockfile sync e ESLint scaffold

### Γ£¿ Added ΓÇö `build_runner.py` ΓÇö suporte a Podman e node_version override (staged)

- `src/shared/utils/build_runner.py`: adicionado suporte a runtime **Podman** via flag `--runtime podman`. Em ambientes Windows + Git Bash / MSYS2, Podman requer paths nativos (`C:/...`) em vez do formato MSYS2 (`//c/...`) usado pelo Docker Desktop ΓÇö `--normalize-path` agora detecta o runtime e emite o formato correto.
- `resolve_image()` recebe novo par├ómetro `node_version`: para frameworks frontend Node-based (Angular, React, Vue, Svelte) a vers├úo do framework (ex: Angular 17) Γëá vers├úo do Node.js. `--node-version` permite passar `tobe_stack.node_version` do `project-config.yaml` explicitamente; emite warning se os valores diferirem.

### ≡ƒöº Changed ΓÇö `ava-stack-build-validator` ΓÇö guardrails de frontend e CVE policy (staged)

- **Guardrail frontend_version Γëá node_version (NOVO)**: proibido usar `--image {framework} {frontend_version}` para resolver `NODE_IMAGE`. O agente deve usar `tobe_stack.node_version` do `project-config.yaml` diretamente (`node:{node_version}-alpine`).
- **Step F3.5 ΓÇö CVE Policy Resolution (NOVO)**: l├¬ `quality_gates.cve_policy.accepted_exceptions` do `project-config.yaml`. Suporta modo `zero_tolerance` (padr├úo) e `exceptions_allowed` com expira├º├úo por data (`expiry` ISO). Exce├º├╡es expiradas s├úo tratadas como bloqueantes automaticamente.
- **Fix #6 ΓÇö Lockfile sync**: se `npm ci` falhar com "package.json and package-lock.json are out of sync", o agente verifica `fix_result.lockfile_updated` do fixer ΓÇö se `false`, dispara novo ciclo explicitamente solicitando regenera├º├úo do lockfile.
- **Step F3 ΓÇö ESLint detection**: detecta tanto flat config (`eslint.config.js`) quanto legacy (`.eslintrc.*`); se nenhum existir ΓåÆ SKIP lint com WARN "No ESLint config found" (n├úo bloqueia).
- **Podman path normalization**: comandos `build_runner.py --normalize-path` passam `--runtime {CONTAINER_CLI}` para garantir paths corretos em ambientes MSYS2.

### ≡ƒöº Changed ΓÇö `ava-stack-build-fixer` ΓÇö protocolo de lockfile obrigat├│rio (staged)

- **Protocolo de Lockfile (NOVO)**: qualquer corre├º├úo que altere `package.json` (install/remove/update) DEVE executar `npm install` no container para regenerar `package-lock.json` antes de retornar `fix_result`. Campo `lockfile_updated: boolean` adicionado ao contrato de sa├¡da. Γ¢ö PROIBIDO retornar sem regenerar o lockfile se `package.json` foi modificado.

### ≡ƒöº Changed ΓÇö `ava-stack-angular-frontend` ΓÇö ESLint scaffolding obrigat├│rio (staged)

- **Depend├¬ncias ESLint adicionadas ao `package.json` gerado**: `@angular-eslint/{builder,eslint-plugin,eslint-plugin-template,schematics}` (vers├úo `^{frontend_version}.0.0`), `@typescript-eslint/{eslint-plugin,parser}` (`^7.2.0`) e `eslint` (`^8.57.0`).
- **Target `lint` adicionado ao `angular.json`**: `@angular-eslint/builder:lint` com patterns `src/**/*.ts` + `src/**/*.html`.
- **Arquivo `.eslintrc.json` gerado obrigatoriamente** (Step 2.2.1): config estendendo `eslint:recommended` + `@typescript-eslint/recommended` + `@angular-eslint/recommended` para TS, e `@angular-eslint/template/recommended` para HTML. Sem este arquivo o Step F3 do build-validator emite WARN.

### ≡ƒöº Changed ΓÇö `projects/Meu-ERP/context/project-config.yaml` (staged)

- Adicionado campo `tobe_stack.node_version` e se├º├úo `quality_gates.cve_policy.accepted_exceptions` com entradas de exemplo para pacotes Angular 17.x com campo `expiry`.

---

## [2026-06-25] ΓÇö Scaffold Gate: enforcement determin├¡stico de arquivos obrigat├│rios p├│s-codegen

### Γ£¿ Added ΓÇö Scaffold Manifests + `verify_scaffold.py` (v1.0.0)

- `src/shared/data/scaffold-manifests/angular-scaffold-manifest.yaml` ΓÇö manifest YAML listando 14 arquivos obrigat├│rios de qualquer projeto Angular (config, entry-points, app-bootstrap, environments). Cada entry: `path`, `category`, `blocking`, `error_if_missing`.
- `src/shared/data/scaffold-manifests/dotnet-scaffold-manifest.yaml` ΓÇö manifest YAML listando 11 arquivos obrigat├│rios de qualquer projeto .NET Clean Architecture (solution-root, domain/application/infrastructure/api layers, test-projects). Suporta glob patterns (`*.sln`, `src/*/MeuERP.*.csproj`).
- `src/shared/utils/verify_scaffold.py` ΓÇö script determin├¡stico de verifica├º├úo de exist├¬ncia de arquivos. L├¬ manifest YAML, verifica `os.path.exists()` para cada path relativo ao root, suporta globs e fallback paths. Sa├¡da JSON com `status`, `found`, `missing`, `blocking_missing`. Exit code 0 (PASS) / 1 (FAIL) / 2 (ERROR). Sem depend├¬ncia PyYAML (parser interno).

### ≡ƒöº Changed ΓÇö `ava-stack-angular-frontend` (coder-angular-frontend.md)

- **Step 2.17 ΓÇö Scaffold Gate (BLOQUEANTE)**: substitu├¡do "Confirmar arquivos gerados" (display-only) por execu├º├úo real de `verify_scaffold.py --manifest angular`. HARD STOP se `blocking_missing > 0`. Bloco visual PASS/FAIL com lista de missing files.
- **Step 10.1 ΓÇö Consistency Verification Gate**: adicionada nova se├º├úo "SCAFFOLD MANIFEST (determin├¡stico)" com invoca├º├úo de `verify_scaffold.py` antes dos guardrails de build.
- **Handoff section**: campo `outputs_generated` removido; adicionados `scaffold_gate: PASS` e `artifacts: [...]` (array obrigat├│rio conforme `agent-result.schema.json`). Regra de bloqueio: NUNCA reportar COMPLETED se scaffold_gate falhou ou artifacts vazio.

### ≡ƒöº Changed ΓÇö `ava-stack-orchestrator` (orchestrator-stack.md, v1.4.0)

- **Step 5.5 ΓÇö Post-Codegen Scaffold Verification (NOVO)**: novo step BLOQUEANTE entre Step 5 (frontend codegen) e Step 6 (contract validation). Executa `verify_scaffold.py` para ambos backend (dotnet manifest) e frontend (angular manifest). Se FAIL ΓåÆ HARD STOP com lista de arquivos faltantes e agente respons├ível.
- **Agent Completion Registry ΓÇö `artifacts_confirmed` logic (NOVO)**: campo `artifacts_confirmed` agora tem l├│gica condicional expl├¡cita ΓÇö setar `true` SOMENTE se verify_scaffold retornar PASS; se FAIL ΓåÆ `false` + N├âO despachar build-validator + retry do codegen agent (max 2 tentativas).

### ≡ƒöº Changed ΓÇö `ava-stack-build-validator` (build-validator-agent.md)

- **Step B0.5 ΓÇö Source File Pre-Gate .NET (NOVO)**: novo step BLOQUEANTE entre B0 (Toolchain Pre-Gate) e B1 (Restore). Executa `verify_scaffold.py --manifest dotnet`. Se FAIL ΓåÆ emite `SCAFFOLD_INCOMPLETE` e ABORT imediato (n├úo tenta dotnet restore).
- **Step F0.5 ΓÇö Source File Pre-Gate Angular (NOVO)**: novo step BLOQUEANTE entre F0 (Toolchain Pre-Gate) e F1 (Install). Executa `verify_scaffold.py --manifest angular`. Se FAIL ΓåÆ emite `SCAFFOLD_INCOMPLETE` e ABORT imediato (n├úo tenta npm ci).
- **Output Contract**: novo status `SCAFFOLD_INCOMPLETE` adicionado ao enum de retorno.

### ≡ƒöº Changed ΓÇö `ava-stack-dotnet-backend` (coder-dotnet-backend.md)

- **Handoff ΓÇö Scaffold Verification Gate (NOVO)**: se├º├úo pr├⌐-handoff que executa `verify_scaffold.py --manifest dotnet` obrigatoriamente antes de emitir `Γå│ Γ£à`. HARD STOP se FAIL. Campo `scaffold_gate: PASS` e `artifacts: [...]` adicionados ao Handoff Report.

---

## [2026-06-25] ΓÇö Esteira de Confiabilidade: docs-researcher + build-validator + build-fixer

### Γ£¿ Added ΓÇö `ava-stack-docs-researcher` (v1.0.0)

- `src/modules/ava-fabric-agents/tech-stack/agents/docs-researcher-agent.md` ΓÇö novo agente cross-cutting pr├⌐-codegen. Pesquisa documenta├º├úo atualizada de pacotes/frameworks via fontes oficiais (NuGet API, npm, fetch_webpage, github_text_search). Gera `docs-research-bundle.md` (┬º1-┬º6: vers├╡es resolvidas, breaking changes, APIs deprecadas, patterns, snippets, guardrails) + `resolved-packages.json`. Cache TTL 24h. Suporta protocolos .NET e Angular; outras stacks emitem WARNING e prosseguem (non-blocking).
- `.github/skills/ava-stack-docs-researcher/SKILL.md` ΓÇö skill de roteamento (padr├úo stack).

### Γ£¿ Added ΓÇö `ava-stack-build-validator` (v1.0.0)

- `src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md` ΓÇö novo agente post-codegen gate. Executa valida├º├úo determin├¡stica: Toolchain Pre-Gate (SDK check), Restore, Build por Camada (isolamento DDD), Build SLN (integra├º├úo inter-BC), Lint/Static Analysis (WARN-only), CVE Scan (BLOQUEANTE), HintPath Check (BLOQUEANTE). Protocolo de retry com max 5 itera├º├╡es via dispatch do build-fixer. Suporta .NET (full pipeline 8 steps), Angular (5 steps), e stubs para Java/Python/Go/Node.
- `.github/skills/ava-stack-build-validator/SKILL.md` ΓÇö skill de roteamento (padr├úo stack).

### Γ£¿ Added ΓÇö `ava-stack-build-fixer` (v1.0.0)

- `src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md` ΓÇö sub-agent de corre├º├úo invocado exclusivamente pelo build-validator. Classifica erros por 12 categorias (CS0246, NU1605, CA1305, CS1998, CVE, HintPath, etc.), pesquisa solu├º├úo via docs oficiais (fetch_webpage, github_text_search), aplica corre├º├╡es cir├║rgicas. Limites: 5 tentativas m├íx por ciclo, 3 tentativas por erro antes de UNRESOLVABLE. Suporta .NET, Angular, Java, Python, Go.

### Γ£¿ Added ΓÇö `dotnet-research-instructions.md` (v1.0.0)

- `src/modules/ava-fabric-agents/shared/dotnet-research-instructions.md` ΓÇö recurso compartilhado consumido pelo docs-researcher e build-fixer. Cont├⌐m: ┬º1 Fontes confi├íveis (12 dom├¡nios permitidos), ┬º2 Protocolo de resolu├º├úo por tipo de depend├¬ncia, ┬º3 Guardrails por vers├úo .NET (10/9/8), ┬º4 Refer├¬ncia cruzada com pol├¡ticas existentes, ┬º5 Protocolo de pesquisa 5 passos, ┬º6 Breaking changes conhecidos.

### ≡ƒöº Changed ΓÇö `ava-stack-orchestrator` (v1.3.0 ΓåÆ v1.4.0)

- **Agent Team**: 3 novos agentes na se├º├úo "Cross-cutting agents (reliability pipeline)"
- **Step 1.5 ΓÇö Documentation Research (NOVO)**: invoca `ava-stack-docs-researcher` com cache check 24h; resultado como input obrigat├│rio para Steps 3 e 5; non-blocking se BLOCKED
- **Steps 3 e 5 ΓÇö Backend/Frontend Codegen (MODIFICADO)**: adicionado `additional_context: docs-research-bundle.md` no dispatch dos coder agents
- **Step 6a ΓÇö Build Validation Backend (NOVO)**: invoca `ava-stack-build-validator` target=backend; HARD STOP se FAIL ap├│s 5 ciclos ou TOOLCHAIN_UNAVAILABLE
- **Step 8a ΓÇö Build Validation Frontend (NOVO)**: invoca `ava-stack-build-validator` target=frontend; HARD STOP se FAIL
- **Agent Completion Registry**: 3 novos IDs (`ava-stack-docs-researcher`, `ava-stack-build-validator-backend`, `ava-stack-build-validator-frontend`)
- **Timing Tables**: MACRO com 3 novas fases (Docs Research, Build Valid BE, Build Valid FE); MICRO com 3 novas linhas
- **Output Contract**: adicionados `docs_research` (bundle + resolved_packages) e `build_validation` (reports + status)

### ≡ƒöº Changed ΓÇö `ava-tobe-orchestrator` (v2.1.0)

- **Agent Team table**: 2 novos agentes (`Docs Researcher` Fase 4.65, `Build Validator` Fase 5.5)
- **Fase 4.7**: Input #5 adicionado (`docs-research-bundle.md`, non-blocking) + nota de enriquecimento
- **Fase 5.5**: Adicionada nota de delega├º├úo ao `ava-stack-build-validator` (valida├º├úo determin├¡stica externalizada)

### ≡ƒöº Changed ΓÇö `coder-dotnet-backend.md` (v1.0.0)

- **Se├º├úo "Input Adicional ΓÇö Docs Research Bundle" (NOVA)**: protocolo de leitura do bundle antes do codegen; usar vers├╡es ┬º1, aplicar guardrails ┬º6, consultar snippets ┬º5, verificar APIs deprecadas ┬º3; non-blocking se ausente

### ≡ƒöº Changed ΓÇö `backend-context-protocol.md`

- **@backend-common-failure-modes**: novo FM-8 ΓÇö "Vers├úo obsoleta de pacote usada pelo LLM" com instru├º├úo para ler docs-research-bundle.md antes de gerar c├│digo

### ≡ƒöº Changed ΓÇö `stub-registry.yaml`

- 3 novas entradas `COMPLETE`: `docs-researcher`, `build-validator`, `build-fixer` na se├º├úo "F3 Cross-Cutting (Reliability Pipeline)"
- Summary atualizado para refletir 3 cross-cutting COMPLETE adicionais

### ≡ƒöº Changed ΓÇö `.github/copilot-instructions.md`

- Tabela F3: 2 novas linhas (`@ava-stack-docs-researcher`, `@ava-stack-build-validator`)

---

## [2026-06-25] ΓÇö FastQA TO-BE Bridge: API black-box tests, POISED/VADER exploratory, QA Master Report template

### Γ£¿ Added ΓÇö `ava-qa-bridge-fastqa-tobe` (v1.0.0)

- `src/modules/ava-fabric-agents/qa-agents/agents/bridge-fastqa-tobe.md` ΓÇö novo Bridge Agent entre pipeline TO-BE e ecossistema FastQA. Gera testes de API black-box (Playwright/TypeScript), testes explorat├│rios live (POISED/VADER por Bounded Context) e automa├º├úo externa. Escopo complementar ao pipeline AVA interno: cobre camada de testes EXTERNOS contra API deployed, enquanto AVA cobre testes INTERNOS (Unit/Integration/Contract dentro do .sln). 5 Elementos: Environment Setup (archive + config swap), PBI TO-BE Generator (11 CTs dos Grupos 2/3/5), FastQA Pipeline Streamlined (load_pbi ΓåÆ map_behaviors), Test Design (Gherkin API), Exploratory API Testing (POISED bc01+bc02, VADER bc03), Automation Script Generation (Playwright/TS). Trigger: `FQ`.
- `.github/skills/ava-qa-bridge-fastqa-tobe/SKILL.md` ΓÇö skill de roteamento (padr├úo QA).
- `fastqa/scripts/project_config.tobe.json` ΓÇö override de configura├º├úo FastQA para fase TO-BE (platform=API, format=gherkin, test_levels=[Integration, API, Security, Exploratory]). Usado pelo bridge para swap tempor├írio de config sem impactar execu├º├╡es AS-IS.

### ≡ƒöº Changed ΓÇö `ava-qa-orchestrator` (v1.3.0 ΓåÆ v1.4.0)

- **Agent Team QA**: novo agente `ava-qa-bridge-fastqa-tobe` (FastQA TO-BE, paralelo a ET+EC ap├│s AS)
- **Triggers**: `FQ` (FastQA TO-BE ΓÇö bridge para FastQA: API black-box, POISED/VADER, automa├º├úo externa) com Pre-condition Gate (test-cases.md + OpenAPI specs)
- **Output Contract**: 3 novos artefatos FastQA (`gherkin-scenarios.md`, `exploratory-api-report.md`, `automation-summary.md`)
- **Routing ΓÇö Trigger QS (step 9)**: `ET + EC` ΓåÆ `ET + EC + FQ` em paralelo; adicionado ┬º9c FQ Completion Gate
- **Terminal Mandatory Steps**: `FQ` adicionado ├á lista de triggers que executam PTΓåÆRS automaticamente
- **Pre-condition Gate (FQ)**: 3 passos (test-cases.md existe + cont├⌐m CTs API/RN/Security + OpenAPI specs existem)
- **Routing ΓÇö Trigger FQ**: delega├º├úo ao bridge-fastqa-tobe com 5 elementos + publica├º├úo em `outputs/tobe/qa/fastqa/`
- **┬ºQA Master Report ΓÇö Test Summary Template (NOVO)**: template obrigat├│rio para `qa-master-report.md` com:
  - Tabela "Testes Gerados por tipo e agente" (16 tipos ├ù 8 colunas: Gerados/Execut├íveis/Executados/Pass/Fail/Skip/Cobertura)
  - M├⌐tricas de Cobertura (6 gates: line, branch, BR, FR, OpenAPI ops, architecture violations)
  - Resumo por Camada ΓÇö Pir├ómide (Unit 70% / Integration 20% / E2E+Smoke 10%)
  - Agentes Executados (13 agentes com status e contagem de artefatos)
  - 10 Regras de Preenchimento (fontes de dados para cada linha da tabela)

### ≡ƒöº Changed ΓÇö `docs/agents-catalog.md` (v1.4 ΓåÆ v1.5)

- **Total de agentes**: 50 ΓåÆ 53
- **F5 ΓÇö QA Agents**: 10 ΓåÆ 13 agentes
- 3 novas entradas: `ava-qa-contract-test-generator`, `ava-qa-frontend-test-generator`, `ava-qa-bridge-fastqa-tobe` com campos Arquivo, Papel, Trigger, Inputs obrigat├│rios e Output

### ≡ƒöº Changed ΓÇö `module.yaml`

- `qa-agents` coment├írio: `9 agentes ΓÇö qualidade e automa├º├úo` ΓåÆ `13 agentes ΓÇö qualidade, automa├º├úo e bridge FastQA`

---

## [2026-06-24] ΓÇö ava-build-cycle-java-persistence: implementa├º├úo completa

### Γ£¿ Added

- `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-java-persistence.md` ΓÇö agente `ava-build-cycle-java-persistence` implementado (v1.0.0). Equivalente Java do `build-cycle-efcore-agent.md`. Cobre:
  - **Routing Guard duplo** (`pipeline_mode == build-cycle` AND `backend_framework == spring-boot`) + abort com mensagem direcionando ao agente gen├⌐rico
  - **Gate F2 de pr├⌐-condi├º├╡es**: verifica `architecture-blueprint.md`, `security-architecture.md`, `readiness-gate-status.json` (APPROVED) e artefatos do scaffold Java em `outputs/tobe/source-code/`
  - **Guardrails Java-espec├¡ficos** (G-P1 a G-P6): `@SQLRestriction` vs `@Where` depreciado, `@SQLDelete` com schema qualificado, `@EntityGraph` obrigat├│rio para associa├º├╡es lazy, ordem Lombok ΓåÆ MapStruct em annotation processors, `@Transactional` proibido em m├⌐todos `private`, vers├╡es via Maven Central sem fallback hardcoded
  - **Step 1.5 ΓÇö Maven Central Compatibility Assert**: resolu├º├úo din├ómica via `search.maven.org` + CVE check via OSV API; BLOCKED se API inacess├¡vel (nunca usar vers├╡es de treinamento)
  - **Step 2 ΓÇö Classes base compartilhadas**: `AuditableBaseEntity` (`@MappedSuperclass` + `@EntityListeners(AuditingEntityListener.class)` + `@CreatedDate`/`@LastModifiedDate`/`@CreatedBy`/`@LastModifiedBy`), `SoftDeletableBaseEntity` (`@SQLRestriction("deleted_at IS NULL")` + `softDelete()` method), `JpaAuditingConfig` com `AuditorAware<String>` resolvendo via `SecurityContextHolder`
  - **Step 3 ΓÇö Por BC**: declara├º├úo de depend├¬ncias Maven/Gradle (sem vers├úo para pacotes do Spring BOM), JPA entity annotations (`@Entity`, `@Table`, `@SQLDelete`, `@SQLRestriction`), `I{Entity}Repository` (domain ΓÇö sem imports Spring), `{Entity}JpaRepository` (package-private Spring Data) + `{Entity}RepositoryAdapter` (implements domain interface), `JdbcClient` read model com record projections type-safe, `{BC}PersistenceConfig` (`@Configuration` + Hikari settings), snippet `application.yml` com refer├¬ncias Key Vault
  - **Step 4 ΓÇö Flyway**: `V1__{bc}_{entity}_initial.sql` por entidade com schema, campos de auditoria e soft delete condicionais; `FlywayInstructions.md` por BC com comandos Maven/Gradle
  - **Output Contract** com `implementation.status: COMPLETED`, artefatos mapeados por BC, `next_agent: ava-build-cycle-java-api`
  - **Layer Boundary Contract**: tabela expl├¡cita (Domain/Application nunca importam Spring Data) + sugest├úo de ArchUnit para CI
  - **9 Failure Modes** definidos com a├º├úo BLOCKED ou WARN por cen├írio
  - **Nota sobre Unit of Work**: documenta que `@Transactional` substitui `IUnitOfWork` no stack Java ΓÇö nenhuma interface gerada desnecessariamente

### ≡ƒöº Changed

- `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` ΓÇö vers├úo `1.4.0` ΓåÆ `1.5.0`, data `2026-06-22` ΓåÆ `2026-06-24`. Step 0.4: rota `"spring-boot"` atualizada ΓÇö `ava-build-cycle-java-persistence` removido indicador `≡ƒÜº STUB`; adicionada refer├¬ncia ao template `tech-stack/templates/build-cycle-java-persistence.md`.
- `src/shared/data/stub-registry.yaml` ΓÇö nota do `coder-java-backend` atualizada referenciando `build-cycle-java-persistence` como COMPLETE; nova entrada `build-cycle-java-persistence` com `status: COMPLETE`, routing key, refer├¬ncia ao template e descri├º├úo completa dos artefatos e depend├¬ncias.

---

## [2026-06-24] ΓÇö QA Pipeline expansion: Contract Tests + Frontend Tests + Application/API layers

### Γ£¿ Added ΓÇö `ava-qa-contract-test-generator` (v1.0.0)

- `src/modules/ava-fabric-agents/qa-agents/agents/contract-test-generator-agent.md` ΓÇö novo agente de gera├º├úo de testes de contrato (consumer-driven) com PactNet. L├¬ specs OpenAPI e c├│digo de controllers/services para identificar consumer-provider pairs e produzir testes automatizados. Input Contract: 4 artefatos obrigat├│rios + 4 opcionais. Output: consumer tests, provider verification tests, pact files JSON, .csproj, report em `outputs/qa/contract-tests/`. Quality Gates: build exit 0, ΓëÑ80% cobertura de opera├º├╡es OpenAPI, ΓëÑ1 pact por BC. Trigger: `CT`.
- `.github/skills/ava-qa-contract-test-generator/SKILL.md` ΓÇö skill de roteamento (padr├úo QA).

### Γ£¿ Added ΓÇö `ava-qa-frontend-test-generator` (v1.0.0)

- `src/modules/ava-fabric-agents/qa-agents/agents/frontend-test-generator-agent.md` ΓÇö novo agente de QA frontend: testes unit├írios Angular com Jest + Angular Testing Library. Cobre componentes (Smart/Dumb), servi├ºos HTTP e stores NgRx com queries de comportamento (`getByRole`, `getByText`). Quality gates: `npm test` exit 0, ΓëÑ80% componentes cobertos, 3 estados obrigat├│rios para page components (loading/empty/error).
- `src/modules/ava-fabric-agents/qa-agents/module.yaml` ΓÇö ambos agentes registrados no m├│dulo QA.
- `.github/skills/ava-qa-frontend-test-generator/SKILL.md` ΓÇö skill de roteamento stack-agnostic.

### ≡ƒöº Changed ΓÇö `ava-qa-orchestrator` (v1.2.0 ΓåÆ v1.3.0)

- **Agent Team QA**: 2 novos agentes ap├│s `ava-qa-db-integrity-test`: `ava-qa-contract-test-generator` e `ava-qa-frontend-test-generator`
- **Triggers**: `CT` (Contract Tests ΓÇö PactNet) e `FT` (Frontend Tests ΓÇö Jest + ATL) com Pre-condition Gates (CT: OpenAPI specs + controllers; FT: componentes Angular)
- **Routing ΓÇö Trigger QS**: sequ├¬ncia expandida de 10 para 13 steps ΓÇö adicionados DBI (6), CT (7) e FT (8); steps subsequentes renumerados 9ΓÇô13

### ≡ƒöº Changed ΓÇö `ava-qa-script-generator` (v1.2.0 ΓåÆ v1.4.0)

- **v1.3.0 ΓÇö Application + API test layers**: Input Contract expandido (4 novos artefatos opcionais); Step 4B (Application Layer Unit Tests para Services + Validators FluentValidation); Step 5B (API Integration Tests via `WebApplicationFactory` ΓÇö status codes, schema validation, security headers, SQL injection, XSS); Output Contract com `cs_api_tests` e `cs_application_tests`; 3 novos Quality Gates
- **v1.4.0 ΓÇö Tabela de projetos .sln**: tabela expl├¡cita de projetos no `.sln` (Unit, Integration, Contract, Parity) com paths relativos e GUID patterns; `{ProjectName}.ContractTests` gerado pelo `contract-test-generator`, refer├¬ncia mantida pelo `script-generator`

### ≡ƒöº Changed ΓÇö `ava-devops-ci` (v1.2.0 ΓåÆ v1.3.0)

- Steps de teste granulares: `test:unit`, `test:integration`, `test:contract`, `test:frontend`
- 3 novos Quality Gates: Contract tests pass, Frontend coverage (ΓëÑ70%), Frontend tests pass
- Multi-Project Test Detection: detec├º├úo autom├ítica via glob ΓÇö projetos ausentes n├úo geram steps
- Markers M7/M8 (Wave 4): condicionais para Contract Tests e Frontend Tests em GitHub Actions e Azure DevOps

### ≡ƒöº Changed ΓÇö `.github/copilot-instructions.md`

- Se├º├úo "F4 ΓÇö QA Agents": adicionadas entradas `@ava-qa-contract-test-generator` e `@ava-qa-frontend-test-generator` ├á tabela de skills

---

## [2026-07-01] ΓÇö ava-devops-iac-gcp v1.0.0: Implementa├º├úo do agente IaC GCP

### Γ£¿ Added ΓÇö `ava-devops-iac-gcp` (v0.1.0-stub ΓåÆ v1.0.0)

- `src/modules/ava-fabric-agents/devops-agents/agents/iac-gcp-agent.md` — agente implementado (era stub). Gera Terraform (google ~> 6.0, google-beta ~> 6.0, random ~> 3.6) + Cloud Deployment Manager para toda a infraestrutura GCP da solução.
- **10 módulos Terraform** com código canônico: `networking` (VPC + Subnets + Firewall + VPC Connector), `iam` (Service Account + Workload Identity), `secret-manager`, `cloud-run` (Cloud Run v2 Backend + Frontend + Serverless NEG), `gke` (GKE Cluster + Node Pool privado), `artifact-registry` (condicional), `cloud-sql` (IP privado + SSL + backup), `memorystore` (Redis 7.0 + Auth + TLS), `monitoring` (4 golden signals), `cloud-armor` (WAF OWASP + LB Global + HTTPS redirect).
- **10 invariantes críticos** (CI-GCP-1..10): path de saída, ambientes dev/hml/prd, engine do banco via ADR-002, sem secrets hardcoded, providers fixados, Artifact Registry condicional, módulos separados, Cloud Armor preview/enforce, Workload Identity.
- **5 guardrails Cloud Deployment Manager** (CDM-1..5): tipos versionados, secrets nunca em configs de ambiente, referências via `$(ref.X.outputs.Y)`, `metadata.dependsOn` obrigatório.
- **Dependency Gate**: 3 artefatos bloqueantes (project-config.yaml, architecture-blueprint.md, ADR-002-\*.md).
- **Routing Guard**: detecta `.tf` existentes em `outputs/tobe/infra/gcp/` e para antes de sobrescrever.
- **Handoff block** com `implementation.status: COMPLETED` (não mais STUB).
- **3 ambientes**: `dev`, `hml`, `prd` — tabela de tfvars + environments CDM por ambiente.
- `.github/skills/ava-devops-iac-gcp/SKILL.md` — skill de roteamento criada.
- `src/shared/data/stub-registry.yaml` — status atualizado: `STUB` → `COMPLETE` para `iac-gcp`.
- `.github/copilot-instructions.md` — linha `@ava-devops-iac-gcp` adicionada na tabela F7.
- `master-orchestrator.md` — aviso `# 🚧 STUB` removido do dispatch `@ava-devops-iac-gcp`.

## [2026-06-25] — ava-devops-iac-aws v1.0.0: AWS IaC (Terraform + CDK) implementado

### Γ£¿ Added ΓÇö `ava-devops-iac-aws` (STUB 0.1.0-stub ΓåÆ v1.0.0)

- **Agente implementado do zero** a partir do stub: `devops-agents/agents/iac-aws-agent.md`
- **9 Invariants Cr├¡ticos** (CI-1 a CI-9): output path `outputs/tobe/iac/aws/`, environments `dev/hml/prd`, secrets via Secrets Manager, provider `aws ~> 5.0`, state S3 + DynamoDB lock
- **Routing Guard**: detecta `.tf` j├í existente em `iac/aws/` e bloqueia reexecu├º├úo sem confirma├º├úo
- **8 m├│dulos Terraform** com HCL completo e security-hardened:
  - `networking/` ΓÇö VPC, subnets pub/priv, IGW, NAT GW, SGs (alb/app/data), ALB, HTTPS redirect
  - `secrets-manager/` ΓÇö KMS CMK (rotation enabled), Secrets Manager para RDS/Cache/Cognito
  - `ecs/` ΓÇö ECS Fargate cluster, Task Definition, Fargate Service, IAM Task/Execution roles
  - `eks/` ΓÇö EKS cluster (v1.30), OIDC provider, IRSA, managed node group
  - `ecr/` ΓÇö ECR (IMMUTABLE tags, scan_on_push, lifecycle policy 14d)
  - `rds/` ΓÇö RDS instance, subnet group, parameter group (`rds.force_ssl=1`), Multi-AZ prd
  - `elasticache/` ΓÇö Redis 7.1, TLS, auth token via Secrets Manager, KMS CMK
  - `cloudwatch/` ΓÇö Log Groups (30/90/365d), RDS CPU alarm, Cache evictions alarm, X-Ray Group, Dashboard
  - `cognito/` ΓÇö User Pool (SRP, no implicit, MFA REQUIRED hml/prd), App Client, client secret no SM
  - `cloudfront/` ΓÇö Distribution, WAF WebACL v2 (3 managed rule sets, COUNT/BLOCK por env)
- **Terraform Root Files**: `versions.tf`, `locals.tf`, `variables.tf`, `outputs.tf`, `main.tf`
- **Environment Configs**: `environments/dev|hml|prd/backend.tf` + `terraform.tfvars` com pr├⌐-req S3/DynamoDB
- **AWS CDK TypeScript**: `bin/app.ts`, 8 stacks (`networking`, `secrets-manager`, `compute`, `database`, `cache`, `observability`, `auth`, `frontend`), `lib/config/dev|hml|prd.json`, `package.json` (aws-cdk-lib ~2.140.0), `cdk.json`
- **Handoff block** com `implementation.status: COMPLETED` e `outputs_generated` listados
- **Triggers**: `IA-AWS`, `IAT-AWS`, `IACD-AWS`, `IAV-AWS`, `IAP-AWS`
- **SKILL.md** criado: `.github/skills/ava-devops-iac-aws/SKILL.md`
- **Registrado** em `.github/copilot-instructions.md` (tabela F6 — DevOps)
- **stub-registry.yaml** atualizado: `iac-aws` → `status: COMPLETE`

## [2026-06-26] — ava-stack-react-frontend v1.0.0: React 18 frontend codegen

### Γ£¿ Added

- `src/modules/ava-fabric-agents/tech-stack/agents/coder-react-frontend.md` (v1.0.0) ΓÇö agente de gera├º├úo de frontend React 18 + Vite + TypeScript 5 + Zustand + MSAL React + React Router v6. Implementa├º├úo completa substituindo o stub anterior (v0.1.0-stub). Contrato de interface id├¬ntico ao `coder-angular-frontend.md`:
  - **Step 1** ΓÇö Pre-flight check: resolve `project_name`, l├¬ `project-config.yaml`, `ConfigStack.yaml`, `bounded-context-map.md`; deriva vari├íveis de vers├úo (`react_pkg_version`, `msal_react_version`, `zustand_version`, etc.).
  - **Step 2** ΓÇö Scaffold raiz Vite: 14 arquivos (`package.json`, `vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `index.html`, `src/main.tsx`, `src/App.tsx`, `src/env.ts`, `.env.example`, `.gitignore`, `vitest.config.ts`, `src/test-setup.ts`, `.eslintrc.cjs`, `src/index.css`).
  - **Step 3** ΓÇö Core module: `apiClient` Axios, `errorInterceptor`, `loadingInterceptor`, `AuthGuard`, Zustand `errorStore` e `loadingStore`.
  - **Step 4** ΓÇö MSAL Authentication: `msalConfig` (SessionStorage, piiLogging=false), `authInterceptor`, `AuthContext` + `useAuth` hook, `LoginPage`.
  - **Step 5** ΓÇö Shared Library: 9 componentes DS (`LoadingSpinner`, `ErrorBanner`, `EmptyState`, `PageHeader`, `StatusChip`, `ConfirmDialog`, `FormError`, `InfoCard`, `ActionToolbar`) + `formatMoney` utility + barrel `index.ts`.
  - **Step 6** ΓÇö Zustand stores por BC: contrato m├¡nimo `items/selectedId/loading/error` + selectors exportados.
  - **Step 7** ΓÇö Feature modules por BC: `types.ts`, `service.ts` (Axios), `useXxx.ts` hook, `XxxListPage.tsx`, `XxxDetailPage.tsx`.
  - **Step 8** ΓÇö OpenAPI TypeScript client: instru├º├úo `openapi-typescript`; graceful warning se spec ausente.
  - **Step 9** ΓÇö React Router v6: lazy loading por BC com `React.lazy()` + `Suspense` + `AuthGuard`.
  - **Step 10** ΓÇö Testes: `renderWithProviders` wrapper, hook tests + ListPage integration tests (RTL + Vitest), `formatMoney.test.ts`.
  - **Step 11** ΓÇö Documenta├º├úo: `ImplementationNotes.md` + `ChangedScreens.md`.
  - Security Compliance Review Gate + Handoff (`implementation.status: COMPLETED`) id├¬nticos ao agente Angular.
- `.github/skills/ava-stack-react-frontend/SKILL.md` ΓÇö SKILL de roteamento criada.

### ≡ƒöº Changed

- `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` (v1.3.0 ΓåÆ v1.4.0) ΓÇö tabela frontend routing: `react` marcado como `Γ£à Implemented`.
- `.github/copilot-instructions.md` ΓÇö entrada `@ava-stack-react-frontend` atualizada: removido `(≡ƒÜº stub)`, adicionada descri├º├úo de stack.
- `src/shared/data/stub-registry.yaml` ΓÇö `coder-react-frontend`: `status: STUB ΓåÆ COMPLETE`.

---

## [2026-06-23] ΓÇö Bridge FastQA QA output directory publication

### ≡ƒöº Changed ΓÇö `ava-asis-bridge-fastqa` (v3.2.0 ΓåÆ v3.3.0)

- **QA Output Directory**: Artefatos de QA agora s├úo publicados em `projects/{project_name}/outputs/asis/qa/` para consumo por fases downstream do pipeline
- **Step 17 ΓÇö Test Plan copy**: destino alterado de `outputs/asis/docs/test-plan.md` para `outputs/asis/qa/test-plan.md`
- **Step 17b ΓÇö Publish QA Artifacts (NOVO)**: novo step que:
  1. Copia `fastqa/manual_test/gap_analysis/PBI-{N}_gaps.md` ΓåÆ `outputs/asis/qa/gap-analysis.md`
  2. Agrega todos os `fastqa/manual_test/test_cases/{funcionalidade}/PBI-{N}.md` em arquivo consolidado ΓåÆ `outputs/asis/qa/test-cases.md`
  3. Confirma presen├ºa do `test-plan.md` no diret├│rio QA (copiado no Step 17 item 3)
- **Output Contract**: adicionada se├º├úo "QA Output Directory (Publica├º├úo)" com os 3 artefatos publicados no `outputs/asis/qa/`
- **Guardrail atualizado**: regra "NUNCA gravar em outputs/" agora excepciona `outputs/asis/qa/` para publica├º├úo de artefatos QA
- **Completion Signal (Step 18)**: adicionado bloco "QA Output Publication" com status de cada artefato publicado
- Refer├¬ncia `docs/test-plan.md` ΓåÆ `qa/test-plan.md` nos guardrails

### ≡ƒ¥¢ Fixed ΓÇö `ava-asis-orchestrator` (v2.17.1 ΓåÆ v2.17.2)

- **Path inconsistency fix**: Todas as refer├¬ncias a `docs/test-plan.md` atualizadas para `qa/test-plan.md` em alinhamento com `bridge-fastqa-asis.md` v3.3.0:
  - `artifact_contracts.ava-asis-bridge-fastqa.mandatory`: `"docs/test-plan.md"` ΓåÆ `"qa/test-plan.md"`
  - `size_threshold` key: `"docs/test-plan.md"` ΓåÆ `"qa/test-plan.md"`
  - `verify_artifacts()` IF condition path
  - `dispatch_bridge_fastqa()` SubAgent prompt path
  - Step 3.4 valida├º├úo bridge-fastqa path + retry instruction
  - Dispatch schedule comment (line 176)

### ≡ƒ¥¢ Fixed ΓÇö `summary-agent.md` + `build_summary_comprehensive.py` + `artifact-map.yaml`

- `summary-agent.md`: refer├¬ncia textual `docs/test-plan.md` ΓåÆ `qa/test-plan.md` na se├º├úo F1 Test Baseline
- `build_summary_comprehensive.py` (ARTIFACT_MAP): path `"asis/docs/test-plan.md"` ΓåÆ `"asis/qa/test-plan.md"`
- `artifact-map.yaml`: entry `test_plan_asis.path` de `"project/outputs/asis/docs/test-plan.md"` ΓåÆ `"project/outputs/asis/qa/test-plan.md"`

---

## [2026-06-24] — ava-stack-go-backend: implementação completa

### Γ£¿ Added ΓÇö `ava-stack-go-backend` (v0.1.0-stub ΓåÆ v1.0.0)

- **Agente implementado** (`tech-stack/agents/coder-go-backend.md`): substitui├º├úo completa do stub por agente production-ready para Go 1.22 + Gin + GORM
- **Routing Guard**: build-cycle Go ΓåÆ fallback autom├ítico para generic com warning (mesmo padr├úo do Java)
- **Gate F2**: bloqueia gera├º├úo se `architecture-blueprint.md`, `security-architecture.md` ou `readiness-gate-status.json` estiverem ausentes ou n├úo-APPROVED
- **Stack Can├┤nica**: 7 campos lidos de `project-config.yaml`; zero valores hardcoded
- **9 Regras Inviol├íveis**: `context.Context` obrigat├│rio, interfaces > concretes, `errors.Is/As`, UUID PKs, Key Vault, `govulncheck`, `go build ./...` ZERO erros
- **G1ΓÇôG9 Guardrails**: GORM soft-delete, verifica├º├úo de membros de dom├¡nio, propaga├º├úo de `context`, Key Vault secrets, JWT JWKS RS256/ES256, health endpoint p├║blico, CORS expl├¡cito, OTel condicional, completude de `go.mod`
- **Resolu├º├úo de vers├╡es**: `proxy.golang.org/{module}/@latest`; BLOCKED se inacess├¡vel
- **Clean Architecture**: `domain / usecase / infrastructure / delivery` com separa├º├úo obrigat├│ria domain Γåö GORM model
- **Security Compliance Gate**: procedimento ┬º3ΓÇô┬º9, relat├│rio `SecurityComplianceReport-Backend.md`, Gate Rule
- **Handoff**: `implementation.status: COMPLETED`, `build: PASS (go build ./...)`
- **SKILL.md criada** (`.github/skills/ava-stack-go-backend/SKILL.md`): wrapper de roteamento padr├úo
- **stub-registry.yaml**: `status: STUB ΓåÆ COMPLETE` com notes
- **orchestrator-stack.md**: tabela backend `≡ƒÜº STUB ΓåÆ Γ£à Implemented` para `gin`
- **copilot-instructions.md**: `@ava-stack-go-backend` adicionado ├á tabela F3

---

## [2026-06-22] — ava-build-cycle-python-scaffold: implementação completa

### ✨ Added

- `src/modules/ava-fabric-agents/tech-stack/templates/build-cycle-python-scaffold.md` — agente `ava-build-cycle-python-scaffold` implementado (v1.0.0). Equivalente Python do `build-cycle-dotnet-scaffold-agent.md`. Cobre: Routing Guard duplo (`pipeline_mode == build-cycle` AND `backend_framework == fastapi`), Gate F2 de pré-condições, Step 1.6 de resolução dinâmica de versões via PyPI API + OSV (sem hardcoding), geração de `pyproject.toml` raiz, `.python-version`, `.editorconfig`, `.gitignore`, `alembic.ini`, módulo `shared/` (Entity, AggregateRoot, ValueObject, Result, Error, PagedList), estrutura por BC em Clean Architecture (`domain/application/infrastructure/api`), `conftest.py` com fixtures async SQLite in-memory, `docker-compose.yml` condicional por `persistence.db_engine` (PostgreSQL/MSSQL), security gate via `pip-audit` + import gate, `KeyVaultOnboarding.md` Python-specific. Output Contract com `implementation.status: COMPLETED`.

### 🔧 Changed

- `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` — versão `1.2.0` → `1.3.0`, data `2026-06-12` → `2026-06-22`. Step 0.4: rota `"fastapi"` removido indicador `🚧 STUB`; adicionada referência ao template `tech-stack/templates/build-cycle-python-scaffold.md`.
- `src/shared/data/stub-registry.yaml` — nota do `coder-python-backend` atualizada referenciando scaffold como COMPLETE; nova entrada `build-cycle-python-scaffold` com `status: COMPLETE`, routing key e descrição dos próximos agentes pendentes (`build-cycle-python-persistence`, `build-cycle-python-api`).
- `.github/copilot-instructions.md` — tabela F3: nova linha `@ava-build-cycle-python-scaffold` com routing key e descrição de artefatos gerados.

---

## [2026-06-19] ΓÇö ava-stack-java-backend + Bridge FastQA template restructure + Orchestrator dispatch guarantees

### Γ£¿ Added ΓÇö `ava-stack-java-backend` (v1.0.0)

- `src/modules/ava-fabric-agents/tech-stack/agents/coder-java-backend.md` ΓÇö agente implementado. Substitui stub `0.1.0-stub`. Contrato de output id├¬ntico ao `coder-dotnet-backend.md`: Routing Guard, 9 Guardrails Java (G1ΓÇôG9), Clean Architecture Template, Dependency Validation Gate, Security Compliance Review Gate e Handoff block com `implementation.status: COMPLETED`.
- `.github/skills/ava-stack-java-backend/SKILL.md` ΓÇö thin routing wrapper para o agente Java.

### ≡ƒöº Changed ΓÇö `ava-asis-bridge-fastqa` (v3.1.0 ΓåÆ v3.2.0)

- **Test Plan template** reestruturado: de 19 se├º├╡es administrativas para 9 se├º├╡es t├⌐cnicas alinhadas ├á pir├ómide de testes (Unit ΓåÆ Integration ΓåÆ E2E ΓåÆ Architecture ΓåÆ Smoke ΓåÆ Load ΓåÆ Data ΓåÆ Gates)
- Removidas se├º├╡es redundantes (Escopo In/Out, Entry/Exit Criteria, Distribui├º├úo por Tag, Gest├úo de Defeitos, Hist├│rico, etc.)
- Tabela "Regras de Preenchimento" reescrita mapeando ┬º1ΓÇô┬º9 ├ás fontes de dados AS-IS
- `validate_test_plan` atualizado para validar 9 se├º├╡es obrigat├│rias

### ≡ƒöº Changed ΓÇö `ava-asis-bridge-fastqa` (v3.0.0 ΓåÆ v3.1.0)

- Adicionada se├º├úo `## 2. Estrat├⌐gia de Testes e Cobertura` ao template do Test Plan (Pir├ómide de Testes, Abordagem de Cobertura, T├⌐cnicas de Teste)
- Se├º├╡es renumeradas de 18 para 19; refer├¬ncias atualizadas (guardrails, `validate_test_plan`, orchestrator dispatch)

### ≡ƒöº Changed ΓÇö `ava-asis-orchestrator` (v2.17.0 ΓåÆ v2.17.1)

- Refer├¬ncia de vers├úo bridge-fastqa v3.0.0 ΓåÆ v3.1.0 no dispatch prompt e `artifact_contracts`
- Template test-plan.md "18 se├º├╡es" ΓåÆ "19 se├º├╡es" (nova se├º├úo Estrat├⌐gia de Testes)

### Γ£¿ Added ΓÇö `ava-asis-orchestrator` (v2.16.0 ΓåÆ v2.17.0)

- **Regra Fundamental #8 `NON-BLOCKING Γëá OPTIONAL`**: `blocking: false` aplica-se exclusivamente a gates downstream; dispatch e execu├º├úo continuam obrigat├│rios; `pending` com trigger satisfeito = DISPATCH FAILURE
- Campo `dispatch_confirmed: boolean` no Agent Completion Registry
- Se├º├úo `### Dispatch Procedure ΓÇö bridge-fastqa (OBRIGAT├ôRIO)` ΓÇö procedimento formal com 4 steps e gate de falha expl├¡cito
- Bloco `DISPATCH AUDIT` no Streaming COLLECT Protocol ΓÇö detecta dispatch failures em tempo real
- Step 3.4 refatorado com CASE branches expl├¡citos (`completed`, `running`, `pending + dispatch_confirmed==false`, `failed`)
- Se├º├úo `### Pre-Gate: Pending Agent Remediation (MANDATORY)` ΓÇö garante que nenhum agente permanece em `pending` ao final

### ≡ƒöº Changed ΓÇö misc

- `src/shared/data/stub-registry.yaml` ΓÇö `coder-java-backend`: `status: STUB` ΓåÆ `status: COMPLETE`
- `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` ΓÇö tabela de routing backend: `spring-boot` atualizado de `≡ƒÜº STUB` para `Γ£à Implemented`
- `.github/copilot-instructions.md` ΓÇö removido indicador `(≡ƒÜº stub)` da linha `@ava-stack-java-backend`

---

## [2026-06-18] ΓÇö Bridge FastQA Elemento 3 + Orchestrator bridge integration + ava-stack-python-backend

### Γ£¿ Added ΓÇö `ava-asis-bridge-fastqa` (v2.0.0 ΓåÆ v3.0.0)

- **Elemento 3 ΓÇö Test Design & Plan**: orquestra 4 agentes FastQA adicionais (Steps 14ΓÇô17)
- Step 14: `@fastqa:ac_scope_analysis` com enriquecimento via behaviors file
- Step 15: `@fastqa:test_case_with_fastqa` em formato Step by Step, Portugu├¬s, escopo total
- Step 16: `@fastqa:validate_scenarios` com 5 fases de valida├º├úo e loop de autocorre├º├úo
- Step 17: `@fastqa:azdo_create_test_plan` em modo 100% local (sem API REST / TypeScript / MCP)
- Test Plan template com 18 se├º├╡es (suites por m├│dulo, rastreabilidade FRΓåÆSuiteΓåÆTC, entry/exit criteria)
- Guardrails expandidos para Elemento 3 (modo local, sem wizard, formato/idioma/escopo fixos)

### Γ£¿ Added ΓÇö `ava-asis-orchestrator` (v2.15.0 ΓåÆ v2.16.0)

- `ava-asis-bridge-fastqa` integrado ao DAG ΓÇö trigger `on(RFΓ£ô + RNΓ£ô)`, non-blocking, Phase B
- Agent Team table, DAG diagram, Dispatch Schedule atualizados com bridge-fastqa
- `artifact_contracts` com contrato para bridge-fastqa (mandatory: `docs/test-plan.md`, external_mandatory: 9 artefatos FastQA)
- Output Contract e timing tables atualizados para 15 sub-agents
- Orchestration Completion Gate atualizado para 9 agentes

### Γ£¿ Added ΓÇö `ava-stack-python-backend` (v1.0.0)

- `src/modules/ava-fabric-agents/tech-stack/agents/coder-python-backend.md` ΓÇö agente implementado (anteriormente stub `v0.1.0-stub`). Routing Guard, 9 Guardrails (G1ΓÇôG9) Python/FastAPI, Clean Architecture Template, 5 Skills geradores, Security Compliance Review Gate, Handoff com `implementation.status: COMPLETED`.
- `.github/skills/ava-stack-python-backend/SKILL.md` ΓÇö wrapper de roteamento.

### ≡ƒöº Changed ΓÇö misc

- `src/shared/data/stub-registry.yaml` ΓÇö `coder-python-backend`: `status: STUB` ΓåÆ `status: COMPLETE`
- `src/modules/ava-fabric-agents/tech-stack/agents/orchestrator-stack.md` ΓÇö `ava-stack-python-backend` `≡ƒÜº STUB` ΓåÆ `Γ£à Implemented`
- `.github/copilot-instructions.md` ΓÇö removido `(≡ƒÜº stub)` da entrada `@ava-stack-python-backend`

---

## [2026-06-17] ΓÇö Bridge FastQA agent creation

### Γ£¿ Added ΓÇö `ava-asis-bridge-fastqa` (v1.0.0 ΓåÆ v2.0.0)

- **v1.0.0**: Cria├º├úo do Bridge Agent (Elemento 1 ΓÇö PBI Generator) ΓÇö dependency gate FR+BR, PBI number via glob+max+1 (faixa ΓëÑ10001), template PBI compat├¡vel com `@fastqa:load_pbi` Modo B, enriquecimento opcional, limite 30 cen├írios
- **v2.0.0**: Adicionado Elemento 2 ΓÇö FastQA Pipeline Orchestration ΓÇö orquestra 5 agentes FastQA em sequ├¬ncia serial (`load_pbi ΓåÆ identify_gaps ΓåÆ estimate_effort ΓåÆ analyze_requirements ΓåÆ map_behaviors`), gates inter-step, completion signal expandido

---

## [2026-05-21] ΓÇö Orchestrator hardening: retry exhaustion, size limits, Phase A gate, repo validation

### Γ£¿ Added ΓÇö `ava-asis-orchestrator`

- **v2.15.0 ΓÇö Retry Exhaustion Policy**: ap├│s 4 tentativas sem sucesso, agente marcado `FAILED` definitivo (`retry_exhausted: true`); pipeline continua com dados parciais; HG apenas se >50% Phase A falharem ou `risk_level: critical`; `pipeline_failed_agents[]` registrado para master-report
- **v2.14.0 ΓÇö Size Limits**: tetos de 50 MB (`master-report.md`) e 10 MB (`.json`); estrat├⌐gia de truncamento campo a campo; `check_size_limits()` com nota inline obrigat├│ria; truncamento n├úo bloqueia esteira
- **v2.13.0 ΓÇö Phase A Gate Formal**: `evaluate_phase_a_all()` como gate duplo (`status=completed` + `artifacts_confirmed=true`); Streaming COLLECT com branch expl├¡cito para `BLOCKED`; Guardrails com invariantes para o gate

### ≡ƒöº Changed ΓÇö `ava-asis-orchestrator`

- **v2.12.0 ΓÇö Repo Validation**: Step 1 expandido com verifica├º├úo de `repository_path` via Bash + presen├ºa de `.pas`; falha encerra pipeline imediatamente sem retries

---

## [2026-05-20] ΓÇö Orchestrator artifact verification

### Γ£¿ Added ΓÇö `ava-asis-orchestrator` (v2.11.0)

- Se├º├úo `### Artifact Output Contract per Agent` ΓÇö lookup table de arquivos obrigat├│rios por agente (12 agentes)
- Sub-protocolo `### Post-Completion Artifact Verification` ΓÇö verifica exist├¬ncia e `size > 0` ap├│s `Γå│ Γ£à`; falha causa `status: failed` + adi├º├úo ├á `retry_queue`
- Campo `artifacts_missing: string[]` no Agent Completion Registry

---

## [2026-05-12] ΓÇö Orchestrator security validation fixes

### ≡ƒ¥¢ Fixed ΓÇö `ava-asis-orchestrator`

- **v2.9.0**: Threshold `artifacts_confirmed < 28` ΓåÆ `< 29`; `force_artifact_generation` ΓåÆ `force_full_artifact_generation`; `agent_chain` adicionado ao dispatch do security
- **v2.10.0**: Valida├º├úo dos 7 sub-agent JSONs no Streaming COLLECT; rejeita COMPLETION_SIGNAL se JSON ausente/vazio/sint├⌐tico; FP Workflow expandido com checks AG-04/AG-05/AG-06

---

## [2026-05-09] ΓÇö Security findings validation

### ≡ƒ¥¢ Fixed ΓÇö `ava-asis-orchestrator` (v2.6.1)

- Streaming COLLECT: valida├º├úo adicional ao receber COMPLETION_SIGNAL do security-orchestrator ΓÇö se `findings_total <= 1` ou `artifacts_confirmed < 28`, for├ºar retry com `force_full_artifact_generation:true`

---

## [2026-05-07] ΓÇö Security profile removal

### ≡ƒöº Changed ΓÇö `ava-asis-orchestrator`

- **v2.2.0**: Removida l├│gica tiered RAPID/STANDARD/DEEP ΓÇö perfil fixo `DEEP` incondicional
- **v2.3.0**: Retry mapping atualizado ΓÇö `profile atual` ΓåÆ `trigger completo`
- **v2.4.0**: Removido conceito `security_profile` ΓÇö dispatch `{ security_profile: "DEEP" }` ΓåÆ `{ source.type: "code" }`; se├º├úo renomeada para `Security Execution`
- **v2.5.0**: Agent Team table: `(DEEP)` ΓåÆ `(cobertura total)`
- **v2.6.0**: Streaming COLLECT com tratamento expl├¡cito do evento `security_orchestrator.completed`; compatibilidade com `security-orchestrator-asis` v1.9.0

---

## [2026-06-17] ΓÇö Baseline Test Generator Agent v1.0.0

Scope: implementa├º├úo do agente `ava-asis-baseline-test-generator` para transformar o
`behavior-catalog.json` (produzido por `ava-qa-behavior-mapping`) em casos de teste
concretos do sistema AS-IS ΓÇö com dados reais de entrada extra├¡dos do c├│digo-fonte,
sa├¡das esperadas observadas no legado, pr├⌐-condi├º├╡es detalhadas e passos de execu├º├úo
passo-a-passo ΓÇö construindo o cat├ílogo de baseline que alimenta os testes de paridade
em cada Build Cycle.

### Γ£¿ Added

- **`src/modules/ava-fabric-agents/asis-diagnostic/agents/baseline-test-generator-asis.md`** ΓÇö v1.0.0 (novo):
  - Role & Persona: QA Engineer s├¬nior especializado em cat├ílogos de baseline para testes de paridade.
  - **Input Contract** com 13 artefatos (4 obrigat├│rios Γ£à, 9 opcionais Γ¼£):
    `behavior-catalog.json`, `business-rules.md`, `functional-requirements.md`,
    `test-execution-plan-asis.md` obrigat├│rios; `behavior-mapping-report.md`,
    `bounded-context-map.md`, `screen-navigation-map.md`, `screen-rules.md`, `db/schema-inventory.md`,
    `db/stored-procedures-map.md`, `test-baseline.md`, `test-coverage-asis.md`, `shared-context.md`
    opcionais.
  - **Dependency Gate** (HARD BLOCK): bloqueia com Γ¢ö se qualquer artefato obrigat├│rio ausente,
    com mensagem estruturada (path + agente produtor + skill para executar).
  - **Output Contract** com 3 sa├¡das em `outputs/asis/qa/`:
    `test-cases-baseline-asis.json` (schema can├┤nico), `test-cases-baseline-asis.md` (leg├¡vel
    para revis├úo + sign-off), `baseline-evidence/BTC-{NNN}-evidence.md` (uma por caso de teste).
  - **Schema `test-cases-baseline-asis.json`**: campos `id` (BTC-NNN), `bh_id`, `bc_id`,
    `bc_name`, `title`, `scenario_type` (5 valores can├┤nicos), `priority` (P0ΓÇôP3), `br_ids[]`,
    `fr_ids[]`, `preconditions[]`, `input_data{}` (com `_evidence` obrigat├│rio por campo),
    `execution_steps[]`, `expected_output{}` (com sentinels `[RUNTIME_DEPENDENT]`,
    `[NEEDS_VALIDATION]`, `[FORMULA_VALIDATED]`), `validation_rules[]`, `evidence{}`,
    `tags[]`, `status` (READY/NEEDS_VALIDATION/BLOCKED), `notes`.
  - **Core Workflow em 4 STEPS obrigat├│rios**: STEP 0 (configura├º├úo + NTP), STEP 1 (indexa├º├úo
    de todos os artefatos), STEP 2 (gera├º├úo por comportamento ΓÇö 9 sub-passos por BH├ùtipo),
    STEP 3 (ordena├º├úo + valida├º├úo de cobertura), STEP 4 (grava├º├úo at├┤mica dos artefatos).
  - **STEP 2 ΓÇö Algoritmo de gera├º├úo por comportamento**: determina tipos de cen├írio a gerar
    (happy obrigat├│rio; sad/edge/boundary/negative por heur├¡sticas do c├│digo); deriva
    preconditions do BH + screen-navigation-map; extrai input_data via Grep no repository_path
    com evid├¬ncia arquivo:linha; converte Gherkin do test-execution-plan em passos imperativos;
    deriva expected_output do BH.expected_outcome + busca de ShowMessage/raise Exception no c├│digo;
    constr├│i validation_rules por BR cr├¡ticas; atribui tags e status por completude de evid├¬ncias.
  - **M├⌐tricas de cobertura**: `coverage_bh` (% de BH com ΓëÑ1 BTC), `coverage_br`
    (% de BR P0+P1 cobertas), `coverage_fr` (% de FR cobertas) ΓÇö com warnings em <80% e
    critical gate em <50% para coverage_bh.
  - **Format Contract** para `test-cases-baseline-asis.md`: estrutura com Sum├írio Executivo,
    Dashboard por BC, tabela de Comportamentos sem Caso de Teste, cat├ílogo de BTC agrupados
    por BC com heading `### BC-NN: nome`, cada BTC com tabela de metadados, pr├⌐-condi├º├╡es,
    input_data, passos, expected_output, regras validadas.
  - **10 guardrails**: sem hardcoding de stack, sem dados inventados, fail fast sem fallback,
    JSON at├┤mico, cobertura declarada n├úo inflada, evid├¬ncia Γëñ30 linhas por arquivo,
    proibi├º├úo de Mermaid/diagramas, consist├¬ncia com golden-dataset schema, i18n via
    governance-apps, sinal de conclus├úo can├┤nico.
  - **Sinal de conclus├úo**: `Γå│ Γ£à [ava-asis-baseline-test-generator] Completed`.

- **`.github/skills/ava-asis-baseline-test-generator/SKILL.md`** (novo):
  - Routing wrapper padr├úo: resolve PROJECT_NAME via project-config.yaml, l├¬ contexto do
    projeto (agent-task-config + shared-context), exibe aviso sobre os 4 artefatos obrigat├│rios,
    roteia para o agente `.md`.
  - Documenta os 3 outputs prim├írios e menciona que ├⌐ consumido por `@ava-asis-golden-dataset-capture`.

### ≡ƒöº Changed

- **`.github/copilot-instructions.md`** ΓÇö tabela F1 AS-IS Diagnostic:
  - Adicionada linha `@ava-asis-baseline-test-generator` entre `@ava-asis-test-qa` e
    `@ava-asis-golden-dataset-capture` com descri├º├úo completa do prop├│sito do agente.

---

## [2026-06-17] ΓÇö Behavior Mapping Agent v1.0.0

Scope: implementa├º├úo completa do agente `ava-qa-behavior-mapping` para varrer o c├│digo-fonte
legado Delphi (`.pas`, `.dfm`, stored procedures, views, triggers) e correlacionar com a
documenta├º├úo funcional AS-IS, catalogando todos os comportamentos de neg├│cio por bounded context
que devem ser preservados no TO-BE.

### Γ£¿ Added

- **`src/modules/ava-fabric-agents/qa-agents/agents/behavior-mapping-agent.md`** ΓÇö v1.0.0 (novo):
  - Role & Persona: especialista em engenharia reversa de comportamento de sistema legado Delphi.
  - **Input Contract** com 17 artefatos (5 obrigat├│rios Γ£à, 12 opcionais Γ¼£):
    `bounded-context-map.md`, `architecture-blueprint.md`, `pattern-classifications.json`,
    `functional-requirements.md`, `business-rules.md` como entradas obrigat├│rias;
    VCL lifecycle, data access profile, DB artifacts (SPs, triggers, views, schema),
    screen rules, screen navigation, value chain, inventory e gaps/risks como opcionais.
  - **Dependency Tree Validation**: gate obrigat├│rio que bloqueia execu├º├úo com mensagem
    estruturada (path ausente + agente produtor + comando de execu├º├úo) se qualquer artefato
    obrigat├│rio estiver ausente.
  - **Output Contract** com `behavior-catalog.json` (array JSON raiz, schema fixo com 14 campos)
    e `behavior-mapping-report.md` estruturado; ambos consumidos por `ava-qa-scenario-generator`
    e `ava-qa-test-case-generator` (trigger FTM).
  - **Schema `behavior-catalog.json`**: campos `id` (BH-NNNN), `bc_id`, `bc_name`, `title`,
    `category` (7 valores can├┤nicos), `criticality` (4 valores), `description`, `trigger`,
    `preconditions`, `expected_outcome`, `evidence` (source_files + db_artifacts + fr_ids +
    br_ids + screen), `migration_risk`, `migration_notes`, `status` (DOCUMENTED/IMPLICIT/UNDOCUMENTED),
    `fr_to_bh_index`.
  - **Algoritmo de execu├º├úo em 6 passos obrigat├│rios**: LOAD-CONTEXT, SOURCE-SCAN, CORRELATION,
    CATALOG-BUILD, REPORT-WRITE, COMPLETION-SIGNAL.
  - SOURCE-SCAN com 5 dimens├╡es por BC: forms (.pas+.dfm, event handlers, SQL inline),
    units de neg├│cio, stored procedures e triggers, views, screen rules.
  - CORRELATION com crit├⌐rios objetivos de `status` (DOCUMENTED/IMPLICIT/UNDOCUMENTED) e
    `criticality` (CRITICAL/HIGH/MEDIUM/LOW) e `migration_risk` baseados em evid├¬ncia t├⌐cnica.
  - CATALOG-BUILD com m├⌐tricas m├¡nimas esperadas (ΓëÑ5 BH por BC n├úo-trivial) e escrita at├┤mica.
  - REPORT-WRITE com estrutura padronizada: Executive Summary, Coverage Dashboard por BC,
    Behavior Catalog detalhado, se├º├úo de riscos (IMPLICIT/UNDOCUMENTED), Gap Analysis vs TO-BE.
  - COMPLETION-SIGNAL com sinal can├┤nico `Γå│ Γ£à [ava-qa-behavior-mapping] Completed`.
  - 6 guardrails: fail-fast sem fallback silencioso, evid├¬ncia obrigat├│ria, sem hardcoding de
    stack, JSON at├┤mico, limites de tamanho com particionamento por BC, i18n via governance-apps.

### ≡ƒöº Changed

- **`.github/skills/ava-qa-behavior-mapping/SKILL.md`** ΓÇö atualizado:
  - Descri├º├úo expandida refletindo o novo escopo (varredura de c├│digo legado + correla├º├úo funcional).
  - Se├º├úo de resolu├º├úo de PROJECT_NAME completa com fallback interativo.
  - Leitura de contexto do projeto (project-config + agent-task-config + shared-context).
  - Instru├º├úo de execu├º├úo com aviso sobre os 6 passos obrigat├│rios.
- **`.github/copilot-instructions.md`** ΓÇö tabela F4 QA Agents:
  - Descri├º├úo de `@ava-qa-behavior-mapping` expandida para refletir o escopo real:
    cat├ílogo de comportamentos AS-IS a partir de c├│digo Delphi por bounded context.

---

Scope: refatora├º├úo completa do agente `ava-qa-exploratory` para conduzir sess├╡es estruturadas
de Exploratory Testing no sistema legado AS-IS, descobrindo comportamentos impl├¡citos, regras
de neg├│cio n├úo documentadas, depend├¬ncias ocultas, fluxos alternativos, caminhos de exce├º├úo
e edge cases. Complementa o Golden Dataset e o cat├ílogo de testes AS-IS.

### ≡ƒöº Changed

- **`src/modules/ava-fabric-agents/qa-agents/agents/exploratory-agent.md`** ΓÇö v1.0.0 ΓåÆ v2.0.0:
  - Input Contract expandido: +7 artefatos opcionais AS-IS (`architecture-blueprint.md`,
    `pattern-classifications.json`, `bounded-context-map.md`, `screen-navigation-map.md`,
    `events-pubsub-inventory.md`, `gap-list-report.md`, `test-coverage-asis.md`,
    `golden-dataset.json`).
  - Pre-condition Gate aprimorado: 3 passos (master-report BLOCK, functional-requirements WARN,
    golden-dataset INFO).
  - STEP 3 EXECUTE-EXPLORATION expandido de 3 para **6 dimens├╡es**: Comportamentos Impl├¡citos,
    Edge Cases, Regras de Neg├│cio Ocultas, **Depend├¬ncias Ocultas** (novo), **Fluxos Alternativos**
    (novo), **Caminhos de Exce├º├úo** (novo).
  - Heur├¡sticas por tecnologia: tabela Delphi/VCL expandida para 12 heur├¡sticas (era 8 gen├⌐ricas)
    com foco em VCL event handlers, DataModule compartilhado, COM/ActiveX, transa├º├╡es impl├¡citas;
    adicionadas tabelas separadas para VB6/VB.NET, COBOL e PowerBuilder.
  - Schema `findings-catalog.json` enriquecido: novos campos `heuristic`, `linked_br`,
    `golden_dataset_gap`; 3 novos tipos (`HIDDEN_DEPENDENCY`, `ALTERNATIVE_FLOW`, `EXCEPTION_PATH`).
  - Prioriza├º├úo de sess├╡es por risco: 4 crit├⌐rios expl├¡citos (HIGH BCs ΓåÆ cobertura 0% ΓåÆ
    Two-Tier/SP patterns ΓåÆ eventos pub-sub).
  - `tobe-preservation-list.md` expandida: 2 se├º├╡es separadas MUST_PRESERVE e SHOULD_PRESERVE
    com coluna `Heur├¡stica` adicionada.
  - `exploratory-report.md` expandida: 2 novas se├º├╡es (`Golden Dataset Gaps`,
    `Findings de Alto Impacto HIGH`); tabela Executive Summary com 6 tipos ├ù 4 severidades;
    Handoff section atualizado com refer├¬ncias a `ava-asis-golden-dataset` e
    `ava-qa-test-case-generator`.
  - STEP 6 SELF-VALIDATION aprimorado: valida├º├úo de JSON v├ílido + completion signal can├┤nico
    `Γå│ Γ£à [ava-qa-exploratory] Completed` com contadores.
  - `allowed-tools`: adicionado `Grep` (necess├írio para an├ílise de padr├╡es em c├│digo-fonte).

- **`.github/skills/ava-qa-exploratory/SKILL.md`** ΓÇö v1.0.0 ΓåÆ v2.0.0:
  - Frontmatter atualizado com `version` e `date`.
  - Description atualizada refletindo 6 dimens├╡es de explora├º├úo.
  - Lista completa de artefatos AS-IS consultados adicionada ao routing wrapper.
  - Leitura de `project-config.yaml` adicionada explicitamente ├á lista de contexto.

---

## [2026-06-16] ΓÇö Golden Dataset Capture Agent #1587

Scope: new F1 AS-IS agent that executes the AS-IS test catalog against the legacy system via static analysis and builds the Golden Dataset ΓÇö source of truth for parity tests in each Build Cycle.

### Γ£¿ Added

- **`src/modules/ava-fabric-agents/asis-diagnostic/agents/golden-dataset-capture-asis.md`** ΓÇö new agent v1.0.0.
  Static Analysis Capture (single mode ΓÇö no HTTP calls), Dependency Gate, STEP 0ΓÇô4 workflow, golden-dataset.json canonical schema (aligned to ava-devops-compare-version contract), Coverage Gate (80% warning, 50% critical), Format Contracts for capture-report.md and execution-log.md, per-TC evidence files, guardrails (anti-hallucination, atomic Write, UUID via Bash, NTP timestamp, no network calls).
- **`.github/skills/ava-asis-golden-dataset-capture/SKILL.md`** ΓÇö routing wrapper populated.
- **`src/modules/ava-fabric-agents/asis-diagnostic/shared/output-paths.md`** ΓÇö Golden Dataset Capture section with 4 canonical paths under `outputs/qa/`.
- **`.github/copilot-instructions.md`** ΓÇö `@ava-asis-golden-dataset-capture` registered in F1 skills table.
- **`projects/_template/context/project-config.yaml`** ΓÇö `golden_dataset_enabled_asis: true` (default true ΓÇö static analysis, zero external dependencies).

### ≡ƒöº Changed

- **`src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md`** ΓÇö v2.14.0 ΓåÆ v2.15.0:
  - Agent Team table: added `golden-dataset-capture` row (Phase B, non-blocking, conditional on `golden_dataset_enabled_asis`).
  - DAG legend: added `ΓÇá` note for golden-dataset-capture.
  - `dispatch_schedule.phase_b`: added rule `on(test-qa:QAΓ£ô) ΓåÆ golden-dataset-capture` with condition `golden_dataset_enabled_asis == true`.
  - `artifact_contracts`: added `ava-asis-golden-dataset-capture` contract with `base_path_override` for `outputs/qa/`.
  - Security Execution section: added **Guard ΓÇö golden_dataset_enabled_asis: false** block.
  - Consistency Gate: added **C2c ΓÇö ARTIFACT-COMPLETE-GOLDEN-DATASET** (conditional WARN, not BLOCK).

## [2026-04-17] ΓÇö Session summary

Scope of this session: make the Summary HTML a production-grade deliverable for any AVA Fabric project. Covers the template (`summary-template.html`), the builder (`build_summary_complete.py`), several TO-BE documents, new F4 (QA) and F5 (Prototype) outputs, and a config-naming bug.

---

### Γ£¿ Added ΓÇö new features

#### Sidebar · per-phase Deliverables submenu

- Every phase group (F1–F7) in the left sidebar now has an expandable **"📦 Entregáveis / Deliverables"** submenu that lists the real files of that phase.
- Data-driven: reads `D.fileTree[phase]` populated by the builder — works for any future project without template changes.
- Clicking a file renders content in a new central section `#s-deliverable-view` (markdown → HTML, JSON → pretty-printed, Mermaid → SVG, **HTML → inline iframe**).
- **Graceful fallback**: phases with no files show a "Sem entregáveis" item in the sidebar and a friendly card in the center with shortcuts to File Explorer and Artefatos.
- **Category grouping** (8 semantic buckets): Diagrams · Security · Requirements & Docs · QA & Tests · Database · Architecture & Analysis · Planning & Sizing · Other Artifacts. Classification is rule-based on extension + filename patterns (file `er-diagram.mmd` → Diagrams, `security-map.md` → Security, etc.) — agnostic to project.
- Each category is **collapsible** with a caret; default closed; state preserved across language switches.
- Labels are **i18n-aware** (PT/EN) and follow the language combobox via `setLang()` which re-renders the submenu idempotently (preserves expanded categories).

#### F4 — QA phase (full)

- 10 new deliverables under `projects/Meu-ERP/outputs/qa/`:
  - `quality-strategy.md` ΓÇö strategy, gates, metrics
  - `qa-master-report.md` ΓÇö consolidated F4 report
  - `gaps-requirements-report.md` ΓÇö 11 requirement gaps
  - `behavior-mapping-report.md` ΓÇö 18 Given-When-Then
  - `scenario-generator-report.md` ΓÇö 26 scenarios
  - `test-case-generator-report.md` ΓÇö 27 seed test cases
  - `script-generator-report.md` ΓÇö xUnit + Testcontainers + Playwright + k6 + ZAP + axe-core snippets
  - `defect-identifier-report.md` ΓÇö triage matrix, SLAs, defect YAML template
  - `exploratory-report.md` ΓÇö 6 SBTM charters
  - `evidence-capture-report.md` ΓÇö storage layout, LGPD retention, chain-of-custody
- All written in English per `language: "en"` in `agent-task-config.yaml`.
- 9 new entries in `ARTIFACT_MAP` (orchestrator + 8 QA sub-agents) ΓÇö status tracker advances F4 from pending to done.

#### F5 — Prototype (navigable wireframe)

- New `projects/Meu-ERP/outputs/tobe/prototype/`:
  - `index.html` ΓÇö self-contained 12-screen prototype (Login, Dashboard, AP list/write-off/new, AR list, Bank reconciliation, Customers/Suppliers, Chart of Accounts, Audit Trail, Settings + drawer), uses `designer-system.md` tokens.
  - `demo-script.md` ΓÇö 20ΓÇô25 min stakeholder walkthrough.
  - `figma-spec.md` ΓÇö tokens, 10 components, 12 frames ready for Figma hand-off.
  - `README.md` ΓÇö entry point + run instructions.
- `ava-prototype` added to `ARTIFACT_MAP`.
- F3/F4 phase in the sidebar now maps to this prototype folder only (`PHASE_FOLDER_MAP.f3f4 = 'prototype'`), ending duplication with F2.

#### F1 AS-IS — missing sequence diagrams

- `asis/diagrams/seq-baixa-titulo-cp.mmd` — AP write-off flow, highlights 4 SQLs without transaction (R-003).
- `asis/diagrams/seq-cadastro-conta-pagar.mmd` — AP create flow, highlights SQL Injection (R-001) + race on `max(id)+1` (R-005).

#### Dashboard sections populated

- **KPIs & Métricas**: every card reads from `metrics.json`.
- **Complexidade Ciclomática**: parsed from `metrics.json.complexity.highest_cc_files`.
- **Business Rules**: 24 entries parsed from `business-rules.md`.
- **Documentation & Requirements**: 20 entries parsed from `functional-requirements.md`.
- **Test Baseline**: 14 rows + 20 gaps parsed from `test-map.md` / `test-gaps.md`.
- **Fluxo de Telas**: 22-form inventory table + Mermaid navigation diagram parsed from `screen-navigation-map.md`.
- **API Surface TO-BE**: 4 endpoints parsed from `tobe/docs/openapi/meu-erp-finance-v1.yaml`.
- **Artefatos ΓÇö AG-02** (and every other chip card): `{{ARTIFACT_INVENTORY_JSON}}` now populated via `build_artifact_inventory()` ΓÇö 73 artifacts across 11 agent chips.

#### HTML deliverable renderer (new)

- Clicking any `.html` file in the Deliverables submenu (e.g., F3/F4 prototype) renders it **inline as a sandboxed iframe** (`srcdoc`) — 82 vh, `allow-scripts allow-forms`, same-origin disabled. Source viewable via collapsible `<details>`.

#### Mermaid render pipeline — `renderMermaidSafely()`

- Single entry point for every Mermaid render in the template:
  - Uses `mermaid.render(id, source)` to get the SVG as a string (not injected yet).
  - Sanitizes `width="-N"`/`height="-N"` ΓåÆ `"0"` in the SVG string **before** insertion ΓÇö eliminates the noisy `<rect> attribute width: A negative value is not valid` browser console errors at the source.
  - Wraps the sanitized SVG in `.mmd-view` and replaces the target element.
- Called by: `renderStaticDiagrams` (10 static diagrams), `renderDeliverableContent` (.mmd branch), `renderScreenNavigation`.
- Each render is isolated ΓÇö one broken diagram cannot break the others.

---

### ≡ƒöº Changed ΓÇö template

- **Template data contract**: new JS fields injected by the builder ΓÇö `ccTop`, `bizRules`, `funcReqs`, `testMap`, `testGaps`, `screenMermaid`, `screenForms`, `apiEndpoints`, `staticDiagrams`, `arts` (populated for real now).
- **`PHASE_FOLDER_MAP`**: `f3f4` remapped from `'tobe'` to `'prototype'` ΓÇö ends F3/F4 replicating F2's files.
- **`DELIV_CATEGORIES` constant**: 8-category classifier with PT/EN labels, used by `buildDeliverableSubmenu`.
- **`init()` pipeline**: renderStaticDiagrams + renderScreenNavigation called post-mermaid-init; `initDeliverableSubmenus` called once at init and re-called by `setLang()` for language toggling.
- **`setLang()`**: added re-render of deliverable submenu (idempotent).
- **Deliverable category body**: collapsible via `toggleDelivCategory(catId)`, default closed, expanded state preserved in `DelivState.expanded`.
- **Source HTML of `.mmd` files** now shown in a `<details>` block below the rendered SVG.

### ≡ƒöº Changed ΓÇö builder (`build_summary_complete.py`)

- **Multi-phase scanner**: `build_file_tree_with_content()` now walks every known phase folder (`asis`, `tobe`, `prototype`, `qa`, `deliverables`, `devops`, `summary`) instead of just `asis/`. `prototype/` is promoted to a top-level key so F3/F4 shows only its files.
- **Scanner exclusions** (`EXCLUDED_PATH_SEGMENTS`): `source-code`, `tests`, `config`, `__pycache__`, `.git`, `node_modules` ΓÇö keeps the deliverable surface about documentation and diagrams, not codebase.
- **READABLE_EXTS** pared down: removed `cs`, `ts`, `tsx`, `js`, `jsx`, `py`, `sh`, `css`, `scss`, `sass`, `bat`, `ps1`, `csproj`, `sln`, `pas`, `dfm`, `dpr`, `dproj`, `bicep`, `tf`, `env` ΓÇö source code no longer embedded in summary. TO-BE Deliverables count went from 112 ΓåÆ 36.
- **`ARTIFACT_MAP`**:
  - Added F2 agents: `ava-tobe-orchestrator`, `ava-tobe-architecture-design`, `ava-tobe-architecture-technical`, `ava-tobe-measure-size`, `ava-tobe-migration-plan`, `ava-docs-tobe`, `ava-test-plan-tobe`.
  - Added F3 agents: `ava-stack-orchestrator`, `ava-stack-dotnet-backend`, `ava-stack-angular-frontend`.
  - Added F4 agents: `ava-qa-orchestrator` + 8 sub-agents.
  - Added F5: `ava-prototype`.
  - Added F8: `ava-summary`.
  - **Removed**: `ava-coder-dotnet` (agent dropped from workflow).
- **`build_artifact_inventory()`**: now actually called; result injected via `{{ARTIFACT_INVENTORY_JSON}}`.
- **New helpers**:
  - `build_all_substitutions()` ΓÇö computes 180 placeholders from `metrics.json`, `risk-register.json`, `pattern-classifications.json`, diagrams.
  - `parse_complexity_top10`, `parse_business_rules`, `parse_functional_requirements`, `parse_test_map`, `parse_screen_navigation`, `parse_openapi_endpoints`, `collect_static_diagrams` ΓÇö 7 data extractors feeding the template.
  - `_sanitize_mermaid` ΓÇö strips emojis, replaces `ΓåÆ`/`ΓÇö`/`ΓÇô` with ASCII equivalents. Applied to every `.mmd` before injection.
  - `_load_mermaid_js` ΓÇö inlines `mermaid.min.js` (3 091 KB) for offline rendering.
- **JSON injection hardening**: all JSON strings emitted into `<script>` go through `.replace('</', '<\\/')` so embedded content can never close the script tag.
- **Final placeholder sweep**: unresolved `{{X_JSON}}` ΓåÆ `{}`, any other `{{X}}` ΓåÆ `""` ΓÇö generated JS is always valid, even when the builder doesn't know a placeholder.
- **Pre-existing bug fix**: `build_agent_status_map` was being called with 1 arg instead of 2 (missing `outputs_base`) ΓÇö fixed.
- **TO-BE folder separation**: scanner skips `tobe/prototype/**` because it's promoted to a dedicated phase key, preventing duplication.

### ≡ƒöº Changed ΓÇö configuration

- **`projects/Meu-ERP/context/project-config.yaml`** (new, copy of `agent-task-config.yaml`): agents read `project-config.yaml` via their .md definitions (51 references) while skill entry-points read `agent-task-config.yaml` (40+ references). Dual-file strategy keeps both working without code churn.
- **`shared-context.md`**: versioned to v6.1 ΓåÆ v6.2 ΓåÆ v6.3 ΓåÆ v6.4 with tracker updates for F4, F5 and summary regeneration entries.

### ≡ƒöº Changed ΓÇö TO-BE artifacts (language fix)

Translated from Portuguese to English in-place (`language: "en"` in config was being ignored before). 20 files:

- Root: `architecture-blueprint.md`, `api-map.md`, `ado-work-items.md`, `bounded-context-map.md`, `coding-standards.md`, `cost-estimate.md`, `designer-system.md`, `effort-calculator.md`, `infra-sizing.md`, `migration-plan.md`, `sizing-report.md`, `solution-structure.md`, `tech-framework-document.md`, `test-plan.md`, `user-journeys.md`, `wave-plan.md`
- `docs/`: `technical-design-document.md`, `CHANGELOG.md`
- `docs/adrs/`: ADR-001, 002, 003, 004, 005, 006, 007
- `config/`: `quality-gates.md`
- `tests/`: `coverage-strategy.md`
- `source-code/`: `README.md` + `ContaCorrente.Banco/README.md`

Filenames **kept unchanged** per i18n rule (technical identifiers preserved to avoid breaking 51+ cross-references in agent docs, ARTIFACT_MAP, shared-context).

### ≡ƒöº Changed ΓÇö CSVs

- `docs/azure-devops-workitems-revisao-agentes_all.csv`: added `Category` column (AS-IS Diagnostic ┬╖ Migration Design ┬╖ Build Cycle ┬╖ Delivery & Handover) for all 42 agent review tasks.
- `docs/data.csv`: added `Category` column (adds Platform & Tooling category) for all 163 Azure DevOps work items including Tasks traced to their Parent PBI.

### ≡ƒöº Changed ΓÇö `tobe-architecture` module

- `module.yaml`: `ava-coder-dotnet` removed from agent registration.
- `workflows/design-dotnet/workflow.md`: `code-generation` step removed; `documentation` step now depends on `technical` directly.

---

### ≡ƒùæ Removed

- **Sidebar nav items** removed from F1 group: "Diagramas C4", "Arquitetura Overall", "Processos BPMN", "Seq. Diagrams" ΓÇö the same content is now in "≡ƒôª Entreg├íveis" categorized.
- **Sidebar nav item** removed from F2 group: "C├│digo Gerado" (obsolete after coder-dotnet removal).
- **Topbar menu** "Artefatos" removed from execution-run header.
- **Screen Flow diagram card** removed (user requested, then restored, then removed again ΓÇö current: removed; Invent├írio de Formul├írios card remains).
- **Old summary HTMLs** removed per guardrail (`AVA-FABRIC-SUMMARY-Meu-ERP-2026-04-15.html`, `ΓÇª-2026-04-16.html`) before each regeneration.
- **`setTimeout(_patchNegRects, ...)` polling** removed ΓÇö negative-width sanitization is now done on the SVG string before DOM insertion.
- **Broad `mermaid.run({querySelector:...})` after renderStaticDiagrams** removed ΓÇö per-element rendering replaces it.

---

### ≡ƒ¥¢ Fixed ΓÇö defects

| #   | Issue                                                              | Root cause                                                                                                                         | Resolution                                                                                                   |
| --- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 1   | Mermaid diagrams showed raw code in AS-IS Architecture             | `renderStaticDiagrams()` was defined but never called; broad `mermaid.run` rejected on any single-diagram error, skipping the rest | Per-element `mermaid.run({nodes:[pre]})` then refactored to `renderMermaidSafely()` using `mermaid.render()` |
| 2   | `<rect> attribute width: A negative value is not valid` in console | Mermaid v11 emits `width="-37.5"` in subgraphs; post-hoc DOM patch ran too late                                                    | Sanitize SVG **string** before it hits the DOM                                                               |
| 3   | `[Mermaid] Could not find a suitable point` on TO-BE C4            | Dagre routing warning rejected the promise in `mermaid.run`                                                                        | `mermaid.render()` returns the SVG even with routing warnings; diagram renders with one unlabeled edge       |
| 4   | TO-BE artifacts in Portuguese despite `language: "en"`             | Agents read `project-config.yaml`; Meu-ERP only had `agent-task-config.yaml`                                                       | Copied to `project-config.yaml` + translated 20 drifted files                                                |
| 5   | F2 Deliverables submenu empty                                      | Builder scanned only `asis/` folder                                                                                                | Multi-phase scanner walks all phase folders                                                                  |
| 6   | F3/F4 Deliverables replicated F2 files                             | `PHASE_FOLDER_MAP.f3f4 = 'tobe'`                                                                                                   | Promoted `tobe/prototype/` to dedicated phase key and remapped f3f4                                          |
| 7   | Phase execution tracker stuck at 8/40                              | `ARTIFACT_MAP` missing F2/F3/F4/F5/F8 entries                                                                                      | 28/40 after adding 20 new artifact entries                                                                   |
| 8   | API Surface TO-BE empty                                            | No parser for OpenAPI; no render function                                                                                          | Added `parse_openapi_endpoints` + `renderAPISurface()`                                                       |
| 9   | Fluxo: Baixa CP / Cadastro CP diagrams missing                     | `.mmd` files didn't exist and builder pointed at wrong filename                                                                    | Created `.mmd` files and fixed builder paths                                                                 |
| 10  | Artefatos — AG-02 (all chip cards) empty                           | `{{ARTIFACT_INVENTORY_JSON}}` hardcoded to `'{}'`                                                                                  | Wired `build_artifact_inventory()` result                                                                    |
| 11  | Deliverables categories stuck in Portuguese after language toggle  | `setLang()` didn't re-render the submenu                                                                                           | Added idempotent re-render call                                                                              |
| 12  | Prototype index.html shown as raw text                             | No branch for `.html` in `renderDeliverableContent`                                                                                | Added iframe `srcdoc` branch                                                                                 |
| 13  | MMD files shown as raw text in Deliverables                        | `_escHtml + innerHTML` mangled `<br/>`/`<i>` tags in Mermaid labels                                                                | `textContent` via DOM API                                                                                    |
| 14  | Screen Flow "Syntax error in text"                                 | `.mmd` content had emojis, `→`, `—` that Mermaid v11 refuses                                                                       | Added `_sanitize_mermaid` to parser                                                                          |
| 15  | `build_agent_status_map()` missing arg crash                       | Pre-existing bug: `TypeError: missing 1 required positional argument: 'outputs_base'`                                              | Passed `outputs_dir` through                                                                                 |
| 16  | Summary HTML file:// unsafe origin warning                         | Cosmetic browser warning for self-references                                                                                       | Mermaid `securityLevel: 'loose'` handles it; warning is non-fatal                                            |
| 17  | Sidebar nav items pointed to removed sections                      | Old F1 diagram items weren't cleaned up when categorization was introduced                                                         | Removed orphan nav items from sidebar                                                                        |
| 18  | `</script>` in embedded content closed the script tag              | JSON injection didn't escape `</`                                                                                                  | All JSON outputs pass through `.replace('</', '<\\/')`                                                       |
| 19  | Many `{{PLACEHOLDER}}` leftovers broke JS parsing                  | Builder had no final sweep                                                                                                         | Final regex sweep replaces unknown `{{X_JSON}}` → `{}`, `{{X}}` → `""`                                       |

---

### ≡ƒº¬ Tested

Every rebuild run through:

1. `python build_summary_complete.py --project Meu-ERP` → `SUCESSO` + "Assinatura VÝLIDA".
2. `node --check` on the main `<script>` → JS OK.
3. Data presence checks: `ccTop`, `bizRules`, `funcReqs`, `testMap`, `screenMermaid`, `apiEndpoints`, `staticDiagrams`, `D.arts`, `fileTree[phase]` — all populated.
4. Browser-based visual checks across 12 UX regression scenarios (KPIs, tables, diagrams, Deliverables submenu, language toggle, prototype iframe, etc.).

---

### ≡ƒôè Final output counts (`v13`)

- **Summary HTML**: 3.7 MB, signature `AVA Fabric Summary Template v1.0`.
- **Phase folders scanned**: asis (38) ┬╖ tobe (36) ┬╖ prototype (4) ┬╖ qa (10) ┬╖ summary (1) = **89 artifacts**, 147 with embedded content.
- **Agents done**: 28/40 (F1 ┬╖ F2 ┬╖ F3 ┬╖ F4 ┬╖ F5 ┬╖ F8).
- **Structured data**: 6 CC rows ┬╖ 24 business rules ┬╖ 20 functional requirements ┬╖ 14 test map rows ┬╖ 20 test gaps ┬╖ 22 screen forms ┬╖ 4 API endpoints ┬╖ **10 static diagrams** (C4 context/container/component, class, component-map, 2 sequence, ER, TO-BE C4, Gantt).
- **Agent inventory**: 73 artifacts catalogued across 11 chip cards.

---

### ≡ƒöÆ Guardrails upheld throughout the session

- Every rebuild: old HTML removed **before** generation (guardrail 3).
- Template loaded **explicitly** from `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` (guardrail 1).
- Signature `AVA Fabric Summary Template v1.0` validated after every build (guardrail 4).
- **Zero** HTML generated manually, inline, or from other projects (guardrail 2).
- **Zero** output written to `projects/_template/`.
- JSON outputs hardened against `</script>` injection.
- Filenames and identifiers preserved per i18n rule even when translating content.

---

### ≡ƒô¥ Files created in this session

- `CHANGELOG.md` (this file)
- `projects/Meu-ERP/context/project-config.yaml`
- `projects/Meu-ERP/outputs/asis/diagrams/seq-baixa-titulo-cp.mmd`
- `projects/Meu-ERP/outputs/asis/diagrams/seq-cadastro-conta-pagar.mmd`
- `projects/Meu-ERP/outputs/qa/` (10 reports)
- `projects/Meu-ERP/outputs/tobe/prototype/` (4 files: index.html, demo-script.md, figma-spec.md, README.md)
- `projects/Meu-ERP/outputs/summary/AVA-FABRIC-SUMMARY-Meu-ERP-2026-04-17.html` (v13)

### ≡ƒô¥ Files modified

- `src/modules/ava-fabric-agents/summary/templates/html/summary-template.html` ΓÇö 10+ distinct changes
- `src/modules/ava-fabric-agents/summary/utils/build_summary_complete.py` ΓÇö 15+ distinct changes
- `src/modules/ava-fabric-agents/tobe-architecture/module.yaml` ΓÇö removed `ava-coder-dotnet`
- `src/modules/ava-fabric-agents/tobe-architecture/workflows/design-dotnet/workflow.md` ΓÇö removed `code-generation` step
- `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml` ΓÇö removed `ava-coder-dotnet` entry
- `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py` ΓÇö removed from ALL_AGENTS
- `projects/Meu-ERP/context/shared-context.md` ΓÇö v6.1 ΓåÆ v6.4
- All TO-BE docs translated to English (listed above)
- `docs/azure-devops-workitems-revisao-agentes_all.csv` ΓÇö added Category column
- `docs/data.csv` ΓÇö added Category column
