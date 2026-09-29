# Tasks — Spec 036: CLI de orquestração da esteira (`ava-pipeline`)

> Status: **todas concluídas**. 46 testes verdes; suíte completa em 209 passed com 4 falhas
> pré-existentes (confirmadas em worktree do HEAD limpo).

## 1. Análise & Planejamento

- [x] T-001 — Mapear o funcionamento do `pipeline_runner.py`: patch de DNS, `WORKSPACE`, tabela
      `PIPELINE`, menus, `load_skill`, `load_context`, `parse_and_write_outputs`, chamada ao SDK
- [x] T-002 — Levantar dependências e pré-requisitos reais (Python, `anthropic`, `pyyaml`, VPN,
      `.copilot-key`) e confirmar versões instaladas
- [x] T-003 — Comparar com `copilot-cli-headroom.bat`: resolução da URL do proxy, liveness,
      degradação, `ANTHROPIC_TARGET_API_URL`
- [x] T-004 — Confirmar que o proxy aceita `POST /v1/messages`, encaminha auth verbatim e faz
      passthrough de SSE; e que os 404 conhecidos vêm de `/v1/models/{id}`, rota exclusiva do Copilot CLI
- [x] T-005 — Inventariar os ativos reusáveis: `agent_registry.py`, `agent_runner.py`,
      `headroom_config.py`, `headroom_tool.py`, `pipeline-dag/`
- [x] T-006 — Identificar a divergência de trigger da F6 contra o `ava-qa-orchestrator` v2.0.0 e
      confirmar com o usuário (`TPT` → `QE`)

## 2. Configuração (fonte única)

- [x] T-010 — Criar `src/shared/data/ava-pipeline.yaml` com cabeçalho de precedência no modelo do
      `headroom.yaml`
- [x] T-011 — Bloco `foundry` (endpoint, `api_key_file`, `anthropic_version`, `max_tokens`)
- [x] T-012 — Bloco `models` (`default`, `provider_model_id`, `aliases`)
- [x] T-013 — Bloco `proxy` (`mode`, `url_command`, `status_command`, `prefer_tool_venv`) — sem
      host/porta literais
- [x] T-014 — Blocos `execution`, `context` e `dns_overrides` (este último desligado por padrão)
- [x] T-015 — Bloco `steps` com as 12 etapas, `phase`/`group`/`agent`/`trigger`/`label`
- [x] T-016 — Comentar no YAML a divergência intencional entre etapa da esteira e fase do módulo

## 3. Loader de configuração

- [x] T-020 — `pipeline_config.py` com `_FALLBACK_DEFAULTS`, `_ENV_MAP` (10 vars), `_deep_merge`,
      `_set_path`, `_read_yaml`
- [x] T-021 — `load_config` com a precedência env > project-config > YAML > fallback; nunca levanta
- [x] T-022 — `resolve_model` com expansão de alias e `--model` vencendo tudo
- [x] T-023 — `api_key` / `api_key_path` com erro acionável quando ausente ou vazio
- [x] T-024 — `_tool_python` preferindo o venv isolado do headroom; `_run_tool`, `proxy_url`,
      `proxy_alive`
- [x] T-025 — CLI auxiliar `--show` / `--model` / `--endpoint`
- [x] T-026 — Corrigir `REPO_ROOT` para `parents[2]` (o arquivo está um nível acima do
      `headroom_config.py`); sem isso o YAML não era encontrado e o fallback assumia em silêncio

## 4. Plano da esteira

- [x] T-030 — `pipeline_plan.py` com o dataclass `Step` (inclui `spec_path`, `registry_phase`, `ad_hoc`)
- [x] T-031 — `declared_steps` com validação de forma e detecção de `phase` duplicada
- [x] T-032 — `_enrich` resolvendo `spec_path`/`module`/`version` pelo `agent_registry`
- [x] T-033 — `build_plan` com `--phase` (etapa ou grupo), `--agent` (esteira ou avulso) e `--from`
- [x] T-034 — `validate_plan` conferindo existência, despachabilidade, deprecação e spec em disco —
      **sem** comparar `step.phase` com `registry.phase`
- [x] T-035 — `format_table` e CLI de depuração do módulo

## 5. Motor SDK

- [x] T-040 — `sdk_engine.py` com `Route` e cores ANSI compartilhadas
- [x] T-041 — `apply_dns_overrides` condicionado a `dns_overrides.enabled`
- [x] T-042 — `make_client` com `import anthropic` dentro da função e mensagem apontando o
      `requirements-pipeline.txt`
- [x] T-043 — `load_skill` lendo `step.spec_path` direto (fim da heurística de substring)
- [x] T-044 — `load_context` com limites vindos da config e exclusão do próprio `output_subdir`
- [x] T-045 — `build_system_prompt` preservando o contrato `<!-- FILE: … -->`
- [x] T-046 — `parse_and_write_outputs` com guarda de path contra escrita fora de `projects/{P}/`
- [x] T-047 — Remover `_WRITE_BLOCK` e `_MD_FILE_BLOCK` (código morto) e o `import requests` não usado
- [x] T-048 — `run_step` com streaming, escrita de artefatos e log `.md` por passo
- [x] T-049 — `estimate_prompt_chars` para o `--dry-run`

## 6. CLI

- [x] T-050 — `ava_pipeline.py` com `argparse` de subcomandos e docstring com tabela de exit codes
- [x] T-051 — `resolve_route` com os modos `auto` / `require` / `off`
- [x] T-052 — `cmd_run`: validação de projeto, plano, banner, `--dry-run`, laço de execução
- [x] T-053 — `ask_permission` e `status_bar` preservando o fluxo interativo
- [x] T-054 — `select_phases_interactive` para `run` sem seletor
- [x] T-055 — `copilot_argv` omitindo `--agent` quando a etapa é o orquestrador da fase
- [x] T-056 — Aviso de DAG ausente e de trigger não propagado no motor `copilot`
- [x] T-057 — `cmd_list` (`--phases` / `--agents` / `--phase`)
- [x] T-058 — `cmd_config` e `cmd_doctor` (proxy fora do ar não reprova)
- [x] T-059 — `_write_run_state` gravando `outputs/.runs/{run_id}/run.json`

## 7. Entrada e dependências

- [x] T-060 — `ava-pipeline.bat` na raiz, repassando `%*` verbatim, sem nenhum valor de config
- [x] T-061 — `requirements-pipeline.txt` documentando a exceção ao stdlib-only
- [x] T-062 — `pipeline_runner.py` → shim com aviso de depreciação, seletor de projeto e delegação

## 8. Testes

- [x] T-070 — `test_pipeline_plan.py`: ordem exata das 12 etapas (item a item)
- [x] T-071 — Par planejar/executar dos dois orquestradores de dois momentos
- [x] T-072 — Ordem relativa: F2b<F5, F2c<F6, F4<F6 e F5<F6 (pré-requisito do `QE`)
- [x] T-073 — `spec_path` vem do registry e o arquivo existe
- [x] T-074 — Divergência de eixos afirmada nas duas metades, com `validate_plan` tolerando
- [x] T-075 — Seletores: grupo, etapa, ordem do YAML, agente duplicado, agente avulso, `--from`
- [x] T-076 — Degradação: sem `steps`, passo incompleto, `phase` duplicada, agente desconhecido
- [x] T-077 — Formato do prompt (`@agente | trigger | project: P`)
- [x] T-078 — `test_pipeline_config.py`: ancoragem do `REPO_ROOT` e existência do YAML
- [x] T-079 — Precedência das quatro camadas, coerção de tipos, env malformada e env vazia
- [x] T-080 — Merge recursivo em dicts, substituição total de listas, base não mutada
- [x] T-081 — Modelo: CLI vence, alias expande, valor sem alias passa direto
- [x] T-082 — API key ausente e vazia
- [x] T-083 — Anti-hardcode por AST em `pipeline_config.py` e `ava_pipeline.py`
- [x] T-084 — `resolve_route`: proxy no ar, sem sufixo de path, degradação avisada, `require`
      abortando, `off` não sondando

## 9. Documentação

- [x] T-090 — `docs/guia-ava-pipeline-cli.md` com 16 seções e índice navegável
- [x] T-091 — Referência de todos os parâmetros, agrupada por finalidade, com pares mutuamente
      exclusivos marcados
- [x] T-092 — Exemplos dos três comportamentos de `--agent`, seleção por grupo/etapa e `--from`
- [x] T-093 — Sete receitas, tabela de solução de problemas e seção de migração
- [x] T-094 — Verificar cada saída citada executando o comando real (inclusive renderizar
      `ask_permission` para conferir o bloco do prompt interativo)
- [x] T-095 — Entrada em `CHANGELOG.md`
- [x] T-096 — Spec Kit 036 (`spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`)

## 10. Verificação & Qualidade

- [x] T-100 — `list --phases` emite os 12 passos na ordem declarada
- [x] T-101 — `doctor -p MeuERP-002` todo verde (exit 0)
- [x] T-102 — `--dry-run` de `--all`, `--phase F2`, `--phase F2b`, `--agent` (esteira e avulso),
      `--from F4` e `--engine copilot` — todos exit 0, sem rede
- [x] T-103 — Erros de configuração saem 2: projeto inexistente, agente desconhecido
- [x] T-104 — Precedência verificada em execução real (`AVA_FOUNDRY_MODEL`)
- [x] T-105 — `--no-proxy` força rota direta; rota padrão usa o proxy quando no ar
- [x] T-106 — `ava-pipeline.bat` e o shim `pipeline_runner.py` funcionando
- [x] T-107 — `pytest tests/tools/test_pipeline_*.py` — 46 passed
- [x] T-108 — `git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat` sem saída (CA02)
- [x] T-109 — Confirmar em worktree do HEAD limpo que as 4 falhas da suíte completa são
      pré-existentes e não tocam os arquivos desta entrega

## Pendente para execução do operador

- [ ] T-110 — Execução real com inferência via proxy (`run -p PROJ --phase F8a --via-proxy --yes`),
      que gera a primeira linha em `.headroom/proxy-requests.jsonl` e permite confirmar o bug
      registrado em spec §7 (`headroom_tool.py attribute`)

## Completion Checklist

- [x] Nenhum agente, `module.yaml` ou `SKILL.md` alterado
- [x] Nenhum endpoint, modelo ou porta hardcoded em código (verificado por AST)
- [x] Ordem da esteira travada por teste
- [x] Os dois `.bat` de sessão interativa intactos
- [x] Ponto de entrada antigo preservado por shim
- [x] `CHANGELOG.md` atualizado
- [x] Guia de uso publicado em `docs/`
