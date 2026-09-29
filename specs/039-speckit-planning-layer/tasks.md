# Tasks — Spec 039: Camada de planejamento SpecKit (`F3S`)

> Status: **em execução**. Cada incremento termina com commit + nota de progresso.
> A ordem importa: a Fase 0 é pré-requisito das demais — sem ela os artefatos gerados pelas
> fases seguintes não chegam a nenhum consumidor.

## Incremento 2026-08-21 — Resiliência e scaffold W0

- [x] T-120 — Propagar `on_fail` em `Step`, `pipeline_plan`, runner 19 e agent runner
- [x] T-121 — Tratar tools `on_fail=warn` como continuação com exit code preservado
- [x] T-122 — Tornar W0/Foundation `codegen=true` no manifesto
- [x] T-123 — Incorporar receitas `dotnet new` e Angular CLI na spec/plan/tasks da W0
- [x] T-124 — Reformular `f4s_scaffold_injector.py` para enriquecer `001-w0-foundation`
- [x] T-125 — Ordenar toda task pela task scaffold da mesma target stack
- [x] T-126 — Adicionar retry automático para outputs F3S declarados e ausentes
- [x] T-127 — Continuar após preflight F3S intermediário falho até reconciliação
- [x] T-128 — Criar `speckit_output_reconciler.py` em estágios planning/final
- [x] T-129 — Exigir `completeness-status.json.status=READY` no exit gate
- [x] T-130 — Corrigir `checks-report.json` para o diretório project-scoped
- [x] T-131 — Cobrir W0, warning, reconciliação, idempotência e gate com testes

## 1. Análise & Planejamento

- [x] T-001 — Medir a janela de injeção de contexto no projeto real: quais artefatos entram nos
      60 primeiros e em que posição caem os insumos exigidos pela F4
- [x] T-002 — Confirmar que `.html` está fora da allowlist de sufixos e que o `index.html`
      nunca poderia chegar ao coder por construção
- [x] T-003 — Confirmar pelo `execution-report` que a F4 rodou como despacho único (624.278 in
      / 82.878 out / 140 artefatos) e que os coders e `build_cycle_templates` não foram carregados
- [x] T-004 — Levantar o SpecKit da implementação anterior (`ava-fabric-agents-v2`): 4 agentes,
      `sequence`/`requires` em texto livre, gates humanos, sem validador executável
- [x] T-005 — Identificar o consumidor órfão: `readiness-gate.md` C2 exige `spec-kit/*.md` sem
      produtor, e ainda assim o gate aprovou com 92,5%
- [x] T-006 — Inventariar ativos reusáveis: `slice:` do `F1.yaml`, `GATES` do
      `artifact_gate_tobe.py`, framework `src/shared/checks/`, P2C §2, `pipeline_observer`
- [x] T-007 — Classificar os defeitos da auditoria nas 6 categorias e atribuir causa-raiz,
      artefato afetado, mitigação SpecKit e risco residual
- [x] T-008 — Decidir com o solicitante: escopo, caminho dos artefatos, fan-out e correção do
      contexto como pré-requisito

## 2. Documentação (SpecKit deste repositório)

- [x] T-010 — `specs/039-speckit-planning-layer/spec.md`
- [x] T-011 — `specs/039-speckit-planning-layer/plan.md` com Constitution Check
- [x] T-012 — `specs/039-speckit-planning-layer/tasks.md` (este arquivo)
- [x] T-013 — `docs/plan/speckit-to-be-tak.md` — dossiê com os 12 deliverables solicitados
- [x] T-014 — Emenda da constituição (v1.5.0): `F3S` na sequência do Article III e o gate de
      saída na tabela de gates obrigatórios

## 3. Fase 0 — Entrega determinística de contexto (PRÉ-REQUISITO)

- [x] T-020 — `tests/tools/test_context_manifest.py` **antes** da implementação: ausência de
      `mandatory` ⇒ exit 2; ordem de declaração preservada; glob expandido; `.html` elegível;
      passo sem `inputs` mantém o comportamento atual
- [x] T-021 — `src/shared/tools/context_manifest.py` — `resolve()`, tiers `mandatory`/`advisory`,
      globs, allowlist ampliada (`.html`, `.ts`, `.cs`, `.scss`, `.sql`, `.props`, `.csproj`)
- [x] T-022 — Mensagem de erro acionável: qual insumo faltou, qual agente o produz, qual fase
- [x] T-023 — `Step.inputs` em `pipeline_plan.py` + parse do bloco `inputs:` em `declared_steps`
- [x] T-024 — `sdk_engine.load_context()` / `run_step()` delegando ao `context_manifest`
- [x] T-025 — `ava_pipeline.py`: `--dry-run` imprime o conjunto de insumos resolvido por passo;
      `mandatory` ausente sai 2 antes de qualquer chamada de rede
- [x] T-026 — `pipeline_runner 19.py` importa o mesmo módulo; entradas de `PIPELINE` ganham
      `inputs` lidos do YAML (sem cópia manual)
- [x] T-027 — Declarar `inputs` para F2a, F3, F4, F5 e F6 em `ava-pipeline.yaml` — a F4 é a
      lacuna que esta investigação expôs
- [x] T-028 — Verificar: `--dry-run` da F4 lista blueprint, openapi, regras-negocio,
      `index.html`, `screen-list.md` e `design-tokens.json` entre os obrigatórios

## 4. Fase 1 — Módulo `speckit`

- [x] T-030 — `src/modules/ava-fabric-agents/speckit/module.yaml`
- [x] T-031 — `agents/orchestrator-speckit.md` — `ava-speckit-orchestrator`, trigger `SK`
- [x] T-032 — `agents/constitution-agent.md` — `ava-speckit-constitution`, trigger `GC`
- [x] T-033 — `agents/specification-agent.md` — `ava-speckit-specification`, trigger `GS`,
      despachado uma vez por artefato-fonte
- [x] T-034 — `agents/prototype-spec-agent.md` — `ava-speckit-prototype-spec`, trigger `GP`,
      procedimento de extração reusando P2C §2
- [x] T-035 — `agents/planning-agent.md` — `ava-speckit-planning`, trigger `GL`
- [x] T-036 — `agents/tasks-agent.md` — `ava-speckit-tasks`, trigger `GT`
- [x] T-037 — `agents/compliance-agent.md` — `ava-speckit-compliance`, trigger `AC`
- [x] T-038 — Bloco de observabilidade em cada agente, `--phase F3S`, `--version` idêntico ao
      frontmatter
- [x] T-039 — Templates: `constitution-template.md`, `spec-template.md`,
      `prototype-spec-template.md`, `plan-template.md`, `tasks-template.md` — com as 10 seções
      obrigatórias **e** as 6 seções do readiness-gate C2
- [x] T-040 — `src/shared/data/pipeline-dag/F3S.yaml` — ordem, dependências e fatias por agente
- [x] T-041 — `agent_registry.py`: `PHASE_BY_MODULE["speckit"]`, `PHASE_ORDER`, `PHASE_NAMES`
- [x] T-042 — Enumerar e ajustar os consumidores de `PHASE_ORDER`/`PHASE_NAMES`
      (`pipeline_observer.py`, `generate_observability_report.py`, testes)
- [x] T-043 — `module.yaml` da raiz — módulo novo
- [x] T-044 — Passos da F3S em `ava-pipeline.yaml`, entre F3 e F4, com `inputs` declarados
- [x] T-047 — `pipeline_runner 19.py`: F3S em `PIPELINE`, `PHASE_GROUPS` e
      `PHASE_ARTIFACT_CONTRACT`. **Lacuna encontrada em revisão**: a T-026 cobriu só a
      propagação de `inputs`; sem esta task o runner de produção — o mesmo que gerou o
      projeto auditado — rodaria a esteira sem a F3S, em silêncio
- [x] T-048 — 5 testes de continência YAML ↔ runner 19 em `test_pipeline_plan.py`, para que
      acrescentar fase em um só dos dois volte a reprovar no CI
- [x] T-045 — 3 SKILL.md (orchestrator, constitution, compliance); os outros 4 internal-only
- [x] T-046 — `python src/shared/tools/generate_agent_wrappers.py` + `--check`

## 5. Fase 2 — Rastreabilidade e gates

- [x] T-050 — `src/shared/schemas/speckit-traceability.schema.json`
- [x] T-051 — `src/shared/schemas/speckit-task-state.schema.json`
- [x] T-052 — `CheckContext.html` / `.html_path` preguiçosos, sem alterar as 12 suítes existentes
- [x] T-053 — `suites/speckit_traceability.py` — CHK-SK-001..012
- [x] T-054 — `suites/prototype_coverage.py` — CHK-PROTO-001..007
- [x] T-055 — Registrar as duas suítes em `checks/__init__.py::_SUITES` e no `--suite` do `cli.py`
- [x] T-056 — `speckit/utils/artifact_gate_speckit.py` — gates de entrada e saída, itens
      **derivados** do `F3S.yaml`, `base:` com `"speckit"`
- [x] T-057 — `tests/ava-fabric-agents/speckit/test_artifact_gate_speckit.py` — coerência
      gate ↔ `F3S.yaml`; divergência é erro, não aviso
- [x] T-058 — Verificar: as suítes reprovam nos artefatos de hoje com mensagem acionável

## 6. Fase 3 — Fan-out da F4 e harness de agente longo

- [x] T-060 — `tests/tools/test_task_ledger.py` **antes** da implementação: status só sobe com
      exit code real; retomada escolhe a próxima task certa; escrita vinda de agente é rejeitada
- [x] T-061 — `src/shared/tools/task_ledger.py` — leitura/escrita, transições, `attempts`,
      `evidence`, `--summary`
- [x] T-062 — `Step.foreach` + expansão no laço de `ava_pipeline.py`
- [x] T-063 — Resolução do agente coder por `target_stack` de cada grupo de tasks
- [x] T-064 — `speckit/templates/verify.ps1.tmpl` — restore, build, test, lint por stack
- [x] T-065 — Preâmbulo de iteração no `context_manifest`: constitution, últimas entradas do
      `ava-agents-progress.txt`, fatia do razão, plan/tasks do grupo, arquivos-alvo em disco
- [x] T-066 — `ava-agents-progress.txt` escrito pelo agente, **sem** afirmação de status
- [x] T-067 — Checksum do `traceability.json` no gate de saída — imutável depois da F3S
- [x] T-068 — Verificar: interromper a F4 e reinvocar retoma na primeira task `pending`

## 7. Fase 4 — Consumidores

- [x] T-070 — `readiness-gate.md` C2 → `outputs/tobe/speckit/specs/*.md`, mantendo as 6 seções
- [x] T-071 — `coder-angular-frontend.md`: prototype/tokens de `OPCIONAIS` para `CRÍTICOS`;
      constitution/plan/tasks como `CRÍTICOS`; MAJOR bump
- [x] T-072 — `coder-react-frontend.md` — idem
- [x] T-073 — `coder-dotnet-backend.md`: constitution/plan/tasks como `CRÍTICOS`; MAJOR bump
- [x] T-074 — `summary/data/artifact-map.yaml` — 7 agentes e seus artefatos → seções do HTML
- [ ] T-075 — Regras novas em `summary/utils/validate_summary.py` — **adiado**: as 55 regras
      atuais são acopladas ao HTML já emitido; acrescentar seções F3S sem um relatório real
      da fase produziria regra sem fixture. Fazer junto com o piloto (T-094).
- [x] T-076 — `CHANGELOG.md` com nota de migração do MAJOR bump dos coders

## 8. Testes

- [x] T-080 — `test_context_manifest.py` verde
- [x] T-081 — `test_task_ledger.py` verde
- [x] T-082 — `test_artifact_gate_speckit.py` verde
- [x] T-083 — `test_pipeline_plan.py` atualizado: a ordem declarada agora inclui a F3S
- [x] T-084 — `test_agent_registry.py` atualizado: `F3S` e os 7 agentes
- [x] T-085 — `python -m pytest tests/ -q` sem regressão além das falhas pré-existentes

## 9. Verificação & Qualidade

- [x] T-090 — `ava-pipeline list --phases` mostra a F3S entre F3 e F4
- [x] T-091 — `--dry-run` de todos os seletores sai 0 sem chamada de rede
- [x] T-092 — `generate_agent_wrappers.py --check` limpo
- [x] T-093 — `git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat` — CA02
- [ ] T-094 — Execução real da F3S em projeto piloto; árvore completa em `outputs/tobe/speckit/`
- [ ] T-095 — As duas suítes verdes; gate de saída libera a F4
- [ ] T-096 — Execução completa; `dotnet build` real; os sete eixos da auditoria remedidos

## Pendente para execução do operador

> As tasks abaixo exigem **inferência real** (VPN, chave do Foundry, ~1 fase de esteira).
> Tudo o que é verificável sem custo de LLM já está entregue e testado.


- Rotacionar as credenciais expostas em
  `projects/nopcommerce-02-cli-ava/outputs/tobe/source-code/.env` — fora do escopo desta spec,
  registrado aqui porque a auditoria o classificou como P0
- Aprovar a emenda v1.5.0 da constituição (T-014) antes do merge da Fase 1

## Completion Checklist

- [x] Fase 0 entregue e verificada — insumos TO-BE chegam à F4
- [x] 7 agentes registrados, despacháveis, com wrappers em dia
- [x] Gates determinísticos bloqueando de fato
- [x] F4 expandindo em N passos com razão resumível
- [x] Consumidores atualizados
- [ ] Piloto medido contra os sete eixos da auditoria
