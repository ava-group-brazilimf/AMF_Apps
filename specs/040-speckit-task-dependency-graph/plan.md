# Plan — Spec 040: Grafo de dependências das tasks SpecKit

## Constitution Check

- **Article I** — Stack e comandos continuam vindo de `project-config.yaml` e dos planos.
- **Article II/X** — Mudança de input/output dos agentes planning/tasks/orchestrator exige bump
  MAJOR; compliance recebe bump MINOR por ampliar auditoria documental.
- **Article III** — O gate F3S permanece obrigatório e passa a validar o DAG antes da F4.
- **Article V** — Specs de agentes e artefatos humanos permanecem em pt-BR.
- **Article VI** — Cenários BDD estão em `spec.md`; testes do grafo precedem integração.
- **Article VIII** — `trace_id` permanece imutável; a ordem ganha checksum próprio.
- **Article XI** — Não há agente novo. Skills existentes continuam wrappers finos.
- **IV7** — `dependency_graph.py` e o compilador são stdlib-only.

## Architecture

Uma única biblioteca, `src/shared/tools/dependency_graph.py`, é a autoridade semântica do DAG.
Ela não conhece caminhos de projeto nem status de pipeline. O compilador SpecKit traduz os
artefatos da F3S para esse modelo; checks, ledger e runners consomem o resultado.

```text
plan-graph.json + task-fragment.json
                 |
                 v
      speckit_task_compiler.py
                 |
                 v
 traceability.json v3 + tasks.md derivados
                 |
        dependency_graph.py
          /       |       \
       checks   ledger   scheduler
```

## Dependency Inference Precedence

1. Dependência task-to-task explícita.
2. Consumidor depende do produtor declarado do artefato ou operação.
3. `create` precede `update` no mesmo arquivo.
4. Roots de grupo sucessor dependem dos terminals do grupo predecessor.
5. Sem evidência estrutural, tasks permanecem paralelas.

BR, TC, `screen_id`, stack e âncora compartilhados preservam rastreabilidade, mas não criam
arestas por si só.

## Classificação e integração frontend → backend

`task_type` é declarado no ownership arquivo a arquivo do `plan-graph.json`, copiado para o
`task-fragment.json` e validado pelo compilador. A classificação nunca é inferida por path ou
`target_stack`.

Uma integração de API usa `api:{operationId}` como contrato estável. O endpoint backend produz o
token e a tela frontend o consome; a precedência produtor/consumidor cria a aresta direta. Depois
da análise do DAG, o compilador deriva `backend_dependencies` a partir das predecessoras diretas,
preserva a projeção no ledger e a expõe na tabela humana `tasks.md`.

## Decomposição vertical por migration wave

`speckit_wave_manifest.py` lê `wave-model.json` como autoridade e usa `wave-plan.md` como
complemento/fallback. A função pura é compartilhada pela montagem do fan-out e pela CLI que
persiste o manifesto; assim, descoberta e artefato não divergem.

Cada wave gera uma spec. Somente `codegen=true` gera plan graph e fragment. Tasks carregam
`migration_wave_id`, `migration_wave_order` e `source_refs[]`. O compilador valida esses dados
contra o manifesto e cria arestas `migration_wave_dependency` entre waves executáveis.

## Implementation Phases

### Phase 1 — Core graph

Implementar validação, ciclo, ordem, ondas, ranks e serialização. Cobrir com testes unitários.

### Phase 2 — Contracts and producers

Adicionar schemas de `plan-graph`, `task-fragment` e traceability v2/v3. Atualizar planning/tasks,
templates, compliance e wrappers.

### Phase 3 — Compiler and checks

Consolidar fragments em duas passagens. Adicionar CHK-SK-016..018 e bloquear o gate F3S.

### Phase 4 — Ledger and scheduler

Validar no `init`, persistir rank/wave/verify command e substituir fan-out estático por loop
incremental task-a-task nos dois runners.

### Phase 5 — Migration and pilot

Ler v1 com defaults e warning. Executar projeto piloto, validar gate, ordem, retomada e build.

## Complexity Tracking

| Decisão | Justificativa |
|---|---|
| Fragmentos por feature | Evita concorrência e referências futuras no JSON global |
| Compilador determinístico | LLM não deve provar aciclicidade nem resolver ownership global |
| Ondas com execução sequencial inicial | Preserva determinismo e prepara paralelismo futuro |
| Schema v3 separado | Acrescenta tipos e dependências backend sem mudar a semântica do v2 |
| `task_type` explícito | Evita classificação frágil por diretório ou framework |
| `backend_dependencies` derivado | Impede que a LLM declare uma relação diferente do DAG |
| Token `api:{operationId}` | Liga tela e endpoint por identidade estável do contrato OpenAPI |
| Manifesto por wave | Faz a unidade de planejamento coincidir com a unidade de entrega |
| `source_refs[]` | Preserva BR + API + tela + teste sem escolher uma origem artificial |
| `migration_wave_dependency` | Torna a sequência do plano de migração executável pela F4 |

## Verification

```powershell
python -m pytest tests/tools/test_dependency_graph.py -q
python -m pytest tests/tools/test_speckit_task_compiler.py tests/tools/test_task_ledger.py -q
python -m pytest tests/ava-fabric-agents/speckit/test_speckit_check_suites.py -q
python -m pytest tests/tools/test_pipeline_plan.py tests/tools/test_agent_wrappers.py -q
python src/shared/tools/generate_agent_wrappers.py --check
```