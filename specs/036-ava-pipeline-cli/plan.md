# Plan — Spec 036: CLI de orquestração da esteira (`ava-pipeline`)

## Constitution Check

- **Nenhum agente é criado ou alterado.** Nenhum `.md` de agente, `module.yaml` ou `SKILL.md` é
  tocado — Category 4 (Module Registration, Article IV) e Category 1.5 (Skill/Agent split,
  Article XI) = **N/A**. Não há version bump de agente.
- **Article I (Configuration-Driven) é o eixo da entrega.** Modelo, endpoint, chave, porta do proxy
  e a ordem da esteira saem do código para `src/shared/data/ava-pipeline.yaml`. A conformidade é
  **verificada por teste**, não por revisão: `test_pipeline_config.py` faz parse AST dos módulos e
  reprova constantes `8787`, `127.0.0.1`, endpoint do Foundry e ids de modelo em código.
- **Article III (Pipeline Execution Contract)** — a sequência executada é declarada em
  `pipeline.steps` e travada por teste. A divergência entre etapa da esteira e fase do módulo
  (esteira F5=DevOps / F6=QA vs. `PHASE_BY_MODULE` F5=`qa-agents` / F6=`devops-agents`) é
  **intencional e documentada** em spec §3.2; o validador nunca compara os dois eixos.
- **Article V (Language Convention)** — docstrings, comentários, mensagens de erro e o guia em
  português brasileiro. Os cenários BDD da spec em inglês, para rastreabilidade com os agentes de QA.
- **Article VI (Test-First)** — 46 testes cobrem ordem, precedência, seletores, rota e degradação.
- **Article VII (Security-First)** — sem impacto no sub-pipeline de segurança. `security_enabled_asis`
  segue governado pelo `project-config.yaml`. A chave nunca é impressa; o `doctor` reporta só o nome
  do arquivo.
- **Article X (Versioning)** — entrega de tooling sem agente versionado; entrada em `CHANGELOG.md`
  mesmo assim, por mudar o ponto de entrada da esteira.
- **IV7 (repo stdlib-only)** — exceção consciente, contida em dois módulos e declarada em
  `requirements-pipeline.txt`. `anthropic` é importado **dentro** de `make_client()`, então
  `--engine copilot` não paga a dependência.
- **IV3 (degradar, nunca quebrar)** — `load_config` nunca levanta; env malformada e YAML ilegível
  degradam com aviso mantendo a camada de baixo.
- **CA02 da spec 033 (restrição inviolável)** — `copilot-cli-headroom.bat` e `copilot-cli-v1.bat`
  intactos; `git diff --exit-code` neles faz parte da verificação.

## Technical Context

O ponto de partida é `pipeline_runner.py` na raiz: 597 linhas, interativo, com `WORKSPACE` fixo
apontando para outro checkout, tabela `PIPELINE` de 18 passos escrita à mão, e chamada direta ao
Foundry pelo SDK Anthropic.

Três ativos do repositório permitem não reescrever nada disso do zero:

| Ativo | O que já resolve |
|---|---|
| `agent_registry.py` | Catálogo canônico dos 107 agentes: `path`, `version`, `module`, `phase`, `dispatchable`, `deprecated`. Elimina a heurística de `load_skill()` |
| `headroom_config.py` / `headroom_tool.py` | URL efetiva e liveness do proxy, já com env e project-config aplicados. Elimina host/porta hardcoded |
| `agent_runner.py` | Execução por processo isolado com gate de artefato e telemetria. Vira o motor `copilot` em vez de ser reimplementado |

O `headroom.yaml` também serve de **modelo de contrato**: cabeçalho de precedência, `_deep_merge`,
`_ENV_MAP`, degradação silenciosa para o fallback. O `pipeline_config.py` é um porte fiel dele — não
uma invenção nova — para que quem já conhece um conheça o outro.

### Decisões que moldam a implementação

1. **`steps:` declarado no YAML, não derivado do registry.** A ordem é decisão de processo; o
   registry sabe que agentes existem, não em que ordem rodá-los. O anti-espelho é o
   `validate_plan()`, que reprova agente inexistente/deprecado/não-despachável com exit 2.
2. **Motor híbrido.** `sdk` preserva o comportamento que já funcionava (blocos `<!-- FILE: … -->`);
   `copilot` reusa o `agent_runner`. Sem migração forçada.
3. **Rota como único ponto de variação do proxy.** `base_url` é a URL do proxy ou o endpoint —
   nada mais muda entre os dois caminhos.
4. **`REPO_ROOT = SCRIPT_DIR.parents[2]`** para arquivos em `src/shared/tools/` (o `headroom_config.py`
   usa `parents[3]` por estar um nível mais fundo). Erro fácil de cometer e silencioso: aponta para
   fora do repo, o YAML não é encontrado e o fallback assume sem avisar.

## Implementation Phases

### Phase 1 — Configuração
- `src/shared/data/ava-pipeline.yaml` com blocos `foundry`, `models`, `proxy`, `execution`,
  `context`, `dns_overrides` e `steps`
- Cabeçalho de precedência e o aviso de divergência de eixos como comentário no próprio YAML

### Phase 2 — Loader
- `pipeline_config.py`: `load_config`, `resolve_model`, `api_key`, `proxy_url`, `proxy_alive`
- `_ENV_MAP` com 10 variáveis; `_FALLBACK_DEFAULTS` com `steps: []` (falhar alto sem o YAML)
- CLI auxiliar: `--show`, `--model`, `--endpoint` (linha crua, consumível por `.bat`)

### Phase 3 — Plano
- `pipeline_plan.py`: `Step`, `declared_steps`, `build_plan`, `validate_plan`, `format_table`
- Seletores `--phase` (etapa ou grupo), `--agent` (esteira ou avulso), `--from`
- Enriquecimento com `spec_path`/`version`/`module`/`registry_phase` do `agent_registry`

### Phase 4 — Motor SDK
- `sdk_engine.py`: `Route`, `apply_dns_overrides`, `make_client`, `ping`, `load_skill`,
  `load_context`, `build_system_prompt`, `parse_and_write_outputs`, `run_step`,
  `estimate_prompt_chars`
- Guarda de path na escrita de artefatos; remoção das regex mortas

### Phase 5 — CLI
- `ava_pipeline.py`: subcomandos `run` / `list` / `config` / `doctor`
- `resolve_route` com os três modos; banner; `--dry-run`; prompt interativo; `run.json`
- `copilot_argv`: sem `--agent` quando a etapa é o orquestrador da fase; avisos de DAG ausente e
  de trigger não propagado

### Phase 6 — Entrada e dependências
- `ava-pipeline.bat` na raiz; `requirements-pipeline.txt`
- `pipeline_runner.py` → shim com aviso de depreciação e seletor de projeto

### Phase 7 — Testes
- `test_pipeline_plan.py` — ordem das 12 etapas, par planejar/executar, seletores, degradação
- `test_pipeline_config.py` — precedência, merge, modelo, chave, rota, anti-hardcode por AST

### Phase 8 — Documentação
- `docs/guia-ava-pipeline-cli.md` — 16 seções, referência de todos os parâmetros, receitas,
  solução de problemas, migração
- `CHANGELOG.md`

### Phase 9 — Verify
- `list --phases`, `doctor`, `--dry-run` de todos os seletores
- `pytest tests/` e `git diff --exit-code` nos dois `.bat`
- Confirmar que falhas remanescentes da suíte são pré-existentes (worktree do HEAD limpo)

## Complexity

| Risco | Mitigação |
|---|---|
| `steps:` vira o sexto espelho manual | O YAML declara só ordem/trigger; identidade e caminho vêm do registry, com `validate_plan` reprovando divergência (exit 2) e teste no CI |
| Alguém "alinha" a numeração da esteira com o registry | Divergência documentada na spec, no comentário do YAML, na docstring do módulo e num teste que afirma as duas metades |
| Regressão do trigger da F6 | `test_orquestradores_de_dois_momentos_nao_repetem_o_trigger` reprova `TPT` repetido |
| Degradação silenciosa para rota direta | Aviso explícito em `auto`; `--via-proxy` aborta; a rota aparece no banner de todo run |
| `REPO_ROOT` errado assumindo o fallback sem avisar | `test_repo_root_aponta_para_o_repo` e `test_yaml_vence_o_fallback` (12 steps) |
| Motor `copilot` fingindo cobertura | Aviso por etapa quando falta o DAG e quando o trigger não é propagável; ambos visíveis no `--dry-run` |
| Endpoint/modelo voltarem para o código | Teste por AST em `pipeline_config.py` e `ava_pipeline.py` |
| Caminho de artefato malicioso vindo do modelo | Guarda em `parse_and_write_outputs`: nada fora de `projects/{PROJETO}/` é escrito |
