# Plan — Spec 039: Camada de planejamento SpecKit (`F3S`)

## Incremento 2026-08-21 — Resiliência e scaffold W0

1. Propagar `on_fail` até todos os executores e tratar `warn` como continuação auditável.
2. Tornar W0/Foundation executável e incorporar nela os scaffolds de todas as target stacks.
3. Parametrizar scaffolds com CLIs oficiais (`dotnet new` e Angular CLI), versões pinadas e argv.
4. Repetir uma vez produtores LLM que não persistirem outputs declarados.
5. Continuar a F3S após preflight intermediário falho até os reconciliadores obrigatórios.
6. Materializar contratos ausentes como placeholders `INCOMPLETE`, sem sobrescrever arquivos reais.
7. Exigir `completeness-status.json.status=READY` para liberar a F4.
8. Persistir `checks-report.json` sob o projeto e gerar `execution-log.json` deterministicamente.

## Constitution Check

- **Article I (Configuration-Driven)** — nenhum caminho, versão ou stack é fixado nos agentes
  novos. Os insumos por passo saem para `ava-pipeline.yaml` (`inputs:`) e para
  `pipeline-dag/F3S.yaml`; a stack alvo de cada task vem de `tobe_stack` do
  `project-config.yaml`. `context_manifest.py` não conhece nome de projeto nem de artefato —
  recebe tudo por parâmetro.
- **Article II (Agent Contract Standard)** — os 7 agentes abrem com frontmatter
  `name`/`version`/`description`/`allowed-tools`. `allowed-tools` **separado por vírgula**: a
  regra AT-001 de `agent_registry.validate()` reprova a forma separada por espaço que o texto
  da constituição exibe. `phase`, `module`, `inputs` e `outputs` **não** entram no frontmatter;
  o Output Contract vai no corpo, com `{project_name}` minúsculo.
- **Article III (Pipeline Execution Contract)** — ⚠️ **exige emenda**. A sequência estrita do
  Article III é `F1→F2→F3→F4→F5→F6→F7`. Esta spec insere `F3S` entre F3 e F4. A emenda
  (v1.5.0) é tarefa desta entrega, não pressuposto: sem ela o `agent_registry` resolve a fase
  do módulo novo como `"?"` e a divergência fica sem registro. O gate de saída da F3S entra na
  tabela de gates obrigatórios do mesmo artigo.
- **Article IV (Module Registration)** — módulo novo ⇒ `speckit/module.yaml` **e** o
  `module.yaml` da raiz. Ambos na Categoria 4 das tasks.
- **Article V (Language Convention)** — corpo dos agentes, templates, docstrings, comentários e
  mensagens de erro em português brasileiro. Os cenários BDD da spec em inglês, para
  rastreabilidade com os agentes de QA. Os artefatos gerados seguem `language:` do
  `project-config.yaml`, como os demais.
- **Article VI (Test-First)** — as duas suítes de check e os dois módulos de tooling nascem com
  teste. `test_context_manifest.py` e `test_task_ledger.py` são escritos antes da
  implementação; `test_artifact_gate_speckit.py` trava a coerência gate ↔ `F3S.yaml`.
- **Article VII (Security-First)** — sem impacto no sub-pipeline de segurança da F1.
  `security-architecture.md` entra como insumo obrigatório da constitution, então requisitos de
  segurança passam a ter task rastreável — hoje não têm.
- **Article VIII (Observability & Traceability)** — cada agente carrega o bloco
  `pipeline_observer.py -p {project_name} track` com `--phase F3S` e o `--version` idêntico ao
  frontmatter (`verify_agent_observability.py` reprova divergência). `trace_id` propaga do
  `project-config.yaml` para `traceability.json` e `execution-log.json` sem mutação.
- **Article X (Versioning)** — os 7 agentes nascem em `1.0.0`. Os 3 coders alterados sofrem
  **MAJOR bump**: promover `prototype_index`/`prototype_screens`/`design_tokens` de
  `OPCIONAIS` para `CRÍTICOS` é mudança de contrato de entrada. Nota de migração no
  `CHANGELOG.md`.
- **Article XI (Skill/Agent Separation)** — declarado explicitamente:

  | Agente | Dispatch | Justificativa |
  |---|---|---|
  | `ava-speckit-orchestrator` | user-facing (SKILL.md) | ponto de entrada da fase |
  | `ava-speckit-constitution` | user-facing (SKILL.md) | roda sozinho e é revisado por humano |
  | `ava-speckit-compliance` | user-facing (SKILL.md) | auditoria sob demanda, fora da esteira |
  | `ava-speckit-specification` | internal-only | recebe **qual fonte** como parâmetro de despacho; uma skill sem parâmetro seria ambígua |
  | `ava-speckit-prototype-spec` | internal-only | idem, fixado no protótipo |
  | `ava-speckit-planning` | internal-only | recebe **qual spec** |
  | `ava-speckit-tasks` | internal-only | recebe **qual plan** |

- **IV7 (stdlib-only)** — `context_manifest.py` e `task_ledger.py` são stdlib puro. Nenhuma
  dependência nova; `requirements-pipeline.txt` não muda.
- **IV3 (degradar, nunca quebrar)** — passo sem `inputs` declarado mantém o comportamento atual
  de injeção. Insumo `advisory:` ausente vira WARN. Só `mandatory:` bloqueia, e bloqueia antes
  de gastar inferência.
- **CA02 da spec 033** — `copilot-cli-headroom.bat` e `copilot-cli-v1.bat` intactos;
  `git diff --exit-code` neles faz parte da verificação.

### Pre-implementation Gates

| Gate | Situação |
|---|---|
| Agente novo tem `module.yaml` | Categoria 4, obrigatória |
| Agente user-facing tem SKILL.md | 3 de 7; os outros 4 declarados internal-only acima |
| Wrappers `.github/agents/` regenerados | `generate_agent_wrappers.py` + `--check` no CI |
| Fase mapeada no `agent_registry` | `PHASE_BY_MODULE["speckit"] = "F3S"` + emenda da constituição |
| Artefatos no Summary HTML | `artifact-map.yaml` + regras no `validate_summary.py` |

---

## Technical Context

O ponto de partida é o diagnóstico da spec §2: a esteira não sofre de prompt ruim, sofre de
entrega de contexto. Três fatos medidos governam todo o desenho abaixo.

**1. A janela de injeção nunca alcança `tobe/`.** `load_context()` ordena por caminho e corta
nos 60 primeiros (30 no motor do CLI). Os 60 do projeto real são 100% AS-IS. Qualquer artefato
novo escrito em `outputs/tobe/speckit/` cairia na mesma sombra — `speckit` ordena depois de `asis`.
Por isso a Fase 0 é pré-requisito e não melhoria adjacente: sem ela esta spec entrega
documentos que ninguém lê.

**2. `.html` nunca foi elegível.** A allowlist de sufixos é `(.md, .mmd, .yaml, .json)`. O
`index.html` — a autoridade sobre *como cada tela é*, segundo o próprio P2C §1 — não podia
chegar ao coder por construção. Nenhum ajuste de prompt corrigiria isso.

**3. A F4 é uma chamada de 82.878 tokens de saída contra teto de 128.000.** 140 arquivos em uma
resposta. O `pipeline_mode: "build-cycle"` do `project-config.yaml` não teve efeito porque o
motor SDK carrega só o `spec_path` do orquestrador e proíbe tools — os 13 coders e os 13
`build_cycle_templates` nunca foram carregados.

Ativos reusáveis, e o que cada um resolve:

| Ativo | Uso nesta entrega |
|---|---|
| `pipeline-dag/F1.yaml` (`slice:`) | vocabulário de fatia de contexto por agente — vira `inputs:` |
| `artifact_gate_tobe.py` (`GATES`) | forma do gate de entrada/saída; `base:` ganha `"speckit"` |
| `src/shared/checks/` (`Suite`/`Reporter`/CHK-IDs) | as duas suítes novas seguem o mesmo contrato |
| `ftm_traceability.py` | precedente exato de "conferir a alegação do cabeçalho contra a realidade" |
| `prototype-conversion-protocol.md` §2 | procedimento de extração do protótipo, já especificado |
| `pipeline_observer.py` | bloco de track obrigatório em cada agente |
| `agent_registry.py` | resolução de `spec_path`, validação AT-001..003 |

Restrição estrutural descoberta na análise: `CheckContext.__init__` carrega o Summary HTML de
forma ansiosa e levanta `FileNotFoundError` quando ele não existe
(`src/shared/checks/context.py:50-55`). Os gates da F3S rodam muito antes de existir summary.
`html`/`html_path` viram propriedades preguiçosas — mudança contida, sem alteração de
comportamento para as 12 suítes existentes.

Segunda restrição: existem **dois** runners em produção. `pipeline_runner 19.py` (versionado,
menu interativo, `PIPELINE` fixo em Python) foi o que gerou o nopcommerce-02;
`ava_pipeline.py` é o CLI declarativo. Os dois têm o mesmo `load_context`. A Fase 0 extrai a
implementação para um módulo compartilhado e os dois passam a importá-la — nada de um sétimo
espelho manual.

---

## Implementation Phases

### Fase 0 — Entrega determinística de contexto

`context_manifest.py` com `resolve(project, step_inputs, cfg) -> (context_block, missing)`.
Tiers `mandatory`/`advisory`, globs, ordem de declaração, allowlist de sufixos ampliada,
fallback para o comportamento atual quando nada é declarado. `Step` ganha `inputs`;
`ava-pipeline.yaml` declara `inputs` para F2a/F3/F3S/F4/F5/F6; os dois runners delegam.
Falta de `mandatory` sai com exit code 2 **antes** de qualquer chamada de rede.

**Verificação:** `--dry-run` da F4 lista os insumos TO-BE e do protótipo; teste prova o exit 2.

### Fase 1 — Módulo `speckit`

`speckit/module.yaml`, 7 agentes em `speckit/agents/`, 5 templates em `speckit/templates/`,
`pipeline-dag/F3S.yaml` como fonte da ordem e das fatias. Registro:
`PHASE_BY_MODULE["speckit"] = "F3S"`, `F3S` inserido em `PHASE_ORDER` depois de `F3`,
`PHASE_NAMES["F3S"]`. Emenda da constituição para o Article III. `module.yaml` da raiz.
Wrappers regenerados. 3 SKILL.md.

**Verificação:** `agent_registry.py --agent ava-speckit-constitution` resolve fase e spec_path;
`generate_agent_wrappers.py --check` limpo; `ava-pipeline list --phases` mostra a F3S.

### Fase 2 — Espinha de rastreabilidade e gates

Os dois schemas JSON, as duas suítes de check, `artifact_gate_speckit.py` **derivando** seus
itens do `F3S.yaml` (não espelhando), `CheckContext` preguiçoso, registro em `_SUITES`.

**Verificação:** as suítes reprovam nos artefatos de hoje e aprovam depois de uma F3S real; o
gate de saída bloqueia a F4 enquanto qualquer suíte estiver vermelha.

### Fase 3 — Fan-out da F4 e harness

`foreach:` no schema de passo e a expansão no laço de `ava_pipeline.py`. `task_ledger.py` com
as transições `pending → in_progress → verified | failed` movidas **apenas** por exit code
real. `verify.ps1` por stack. Preâmbulo de iteração montado pelo `context_manifest`:
constitution, últimas entradas do `ava-agents-progress.txt`, fatia do razão para o grupo,
plan/tasks do grupo, arquivos-alvo já em disco.

**Verificação:** a F4 expande em N passos; interromper e reinvocar retoma na primeira task
`pending`; teste prova que status não sobe sem exit code.

### Fase 4 — Consumidores

C2 do readiness-gate repontado. Contratos de entrada dos 3 coders (MAJOR bump).
`artifact-map.yaml` + regras do `validate_summary.py`. `CHANGELOG.md`.

**Verificação:** execução completa em projeto piloto; os sete eixos da auditoria remedidos.

---

## Complexity

| Risco | Mitigação |
|---|---|
| `F3S` em `PHASE_ORDER` quebrar consumidores | enumerar `pipeline_observer.py`, `generate_observability_report.py` e os testes antes do merge; a suíte inteira roda na verificação |
| `artifact_gate_speckit` virar sétimo espelho | deriva do `F3S.yaml` em runtime; teste de coerência reprova divergência |
| Fan-out perder coerência entre arquivos | `constitution.md` entra em **toda** chamada; o sintoma, se houver, aparece no build |
| Custo de inferência subir com N chamadas | cada chamada carrega fatia pequena; o gasto por token cai mesmo com mais chamadas — medir no piloto e registrar |
| Specs herdarem lixo da fonte | CHK-PROTO-007 propaga os warnings da fonte; a camada não maquia degradação |
| MAJOR bump dos coders quebrar projeto em andamento | nota de migração no `CHANGELOG.md`; o hard stop só dispara quando a F3S está na esteira |
