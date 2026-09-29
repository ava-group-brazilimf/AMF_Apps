# Migration Factory Dashboard

Dashboard Flask que descobre projetos dinamicamente em um diretório raiz e calcula
métricas a partir do `pipeline-runner-metrics.json` de cada projeto.

Nenhum projeto está codificado no código-fonte, no template ou no `metrics.yaml`.
Incluir ou remover uma pasta em `projects/` basta para o dashboard refletir a mudança
na próxima requisição.

---

## Como executar

```bash
cd apps/migration-factory-dashboard
pip install -r requirements.txt
python run.py                      # http://127.0.0.1:5000
```

Para apontar para outro diretório de projetos sem editar arquivo nenhum:

```bash
# Windows (PowerShell)
$env:MIGRATION_FACTORY_PROJECTS_ROOT = "D:\outra\raiz\projects"; python run.py
# bash
MIGRATION_FACTORY_PROJECTS_ROOT=/outra/raiz/projects python run.py
```

### Testes

```bash
pip install -r requirements-dev.txt
python -m pytest                   # 61 testes
python scripts/validate.py         # validação §16.1 com evidências
```

---

## Estrutura

```
apps/migration-factory-dashboard/
├── config/
│   ├── app.yaml            fonte de dados (único lugar com o diretório raiz)
│   └── metrics.yaml        definição das métricas (sem lista de projetos)
├── src/mfd/
│   ├── config.py           carga + precedência de configuração
│   ├── discovery.py        ProjectDiscoveryService — só lista diretórios
│   ├── reader.py           leitura, validação e cache do JSON
│   ├── metrics.py          MetricsEngine — cálculo puro, sem I/O
│   ├── service.py          orquestração descobrir → ler → calcular
│   └── web/                Flask: rotas + template (sem acesso a disco)
├── scripts/validate.py     roteiro de validação §16.1
└── tests/                  61 testes, todos em diretórios temporários
```

As rotas Flask **não acessam o sistema de arquivos**. Toda leitura passa pelo
`DashboardService`, e o cálculo (`metrics.py`) nunca abre um arquivo — recebe payloads
já interpretados.

---

## Configuração

### Precedência do diretório raiz

1. Variável de ambiente `MIGRATION_FACTORY_PROJECTS_ROOT`
2. `projects.root_directory` em `config/app.yaml`
3. `ConfigurationError` — falha controlada, com mensagem na tela e HTTP 503 nas APIs

O diretório raiz aparece **em um único arquivo**. O `metrics.yaml` não o conhece e
recusa qualquer métrica que tente fixar uma lista de projetos.

Outras variáveis: `MIGRATION_FACTORY_APP_CONFIG` e `MIGRATION_FACTORY_METRICS_CONFIG`
apontam para arquivos de configuração alternativos.

### Caminho do arquivo de métricas

`projects.metrics.relative_directory` + `file_name` são configuráveis. O separador pode
ser `\` ou `/` — a configuração funciona igual no Windows e em runners Linux.

---

## Esquema do `pipeline-runner-metrics.json`

Levantado a partir dos arquivos reais em `projects/*/outputs/pipeline_runner/`.
Os quatro arquivos analisados tinham **esquema idêntico**: 24 campos, sem variação.

| Campo | Tipo | Observação |
|---|---|---|
| `execution_id` | string | obrigatório |
| `project_name` | string | obrigatório |
| `execution_mode` | string | valores reais: `full`, `manual` |
| `execution_status` | string | valores reais: `completed_with_warnings`, `running` |
| `start_time_utc` | string | ISO-8601 com sufixo `Z`; pode vir vazio |
| `end_time_utc` | string | idem |
| `total_duration_seconds` | number | janela do run, com ociosidade |
| `total_hours` | string | `HH:MM:SS`, redundante com o campo acima |
| `token_metrics.total_tokens` | int | |
| `token_metrics.token_in` | int | |
| `token_metrics.token_out` | int | |
| `phase_metrics[]` | array | uma entrada por fase do DAG |
| `phase_metrics[].phase_name` | string | ex.: `F1a`, `F3S:specification:001-w0-foundation` |
| `phase_metrics[].status` | string | valores reais: `executed`, `degraded`, `validation_failed` |
| `phase_metrics[].start_time_utc` | string | pode vir vazio quando não reconstruído |
| `phase_metrics[].end_time_utc` | string | idem |
| `phase_metrics[].duration_seconds` | number | `0` significa fase sem medição |
| `phase_metrics[].total_hours` | string | `HH:MM:SS` |
| `phase_metrics[].token_usage.total_tokens` | int | |
| `phase_metrics[].token_usage.token_in` | int | |
| `phase_metrics[].token_usage.token_out` | int | |

### Métricas não implementáveis

A §8 pede para identificar campos de **agentes, ferramentas, artefatos, tentativas,
erros e avisos**. Nenhum deles existe no arquivo real — o `pipeline-runner-metrics.json`
descreve execução, fases, duração e tokens, e nada mais. Conforme a regra "não inventar
campos", **nenhuma métrica foi criada para eles**. Se o pipeline runner passar a emitir
esses campos, basta acrescentar entradas no `metrics.yaml`; nenhum código muda.

Duas consequências práticas dos dados reais:

- `duration_seconds: 0` **não** significa erro. É uma fase determinística (ferramenta)
  ou uma fase reexecutada sem telemetria persistida.
- `status: validation_failed` aparece no acervo real e não estava previsto na
  especificação. É reconhecido e classificado como fase degradada.

---

## Classificação de leitura (§8.1)

| Status | Quando |
|---|---|
| `available` | arquivo lido, esquema completo |
| `partially_available` | lido, mas faltam campos não obrigatórios — as métricas possíveis são exibidas |
| `metrics_unavailable` | projeto existe, arquivo não |
| `empty_file` | arquivo com 0 bytes ou só espaços |
| `invalid_json` | JSON malformado |
| `incompatible_schema` | raiz não é objeto, ou falta `execution_id`/`project_name` |
| `read_error` | sem permissão, encoding errado, ou arquivo instável durante a leitura |

Um projeto em qualquer estado de erro **não interrompe** os demais, e continua listado
no dashboard com a justificativa.

---

## Métricas

`config/metrics.yaml` define 18 métricas de projeto e 37 de portfólio. Cada uma declara
`scope: project` ou `scope: portfolio` e um `calculation.type`. Os tipos suportados:

**Projeto** — `field`, `duration`, `count_items`, `count_items_where`, `sum_items`,
`ratio`, `percentage`, `max_item_by`, `min_item_by`, `token_cost`.

**Portfólio** — `count_projects`, `count_by_status`, `sum_metric`, `average_metric`,
`minimum_metric`, `maximum_metric`, `ratio_metrics` (com `scale` opcional),
`percentage_metrics`, `weighted_average_metric`, `count_by_project_field`,
`count_metric_value`, `latest_value`.

Não há `eval`: cada tipo é um método registrado. Uma métrica mal configurada vira
"indisponível" com justificativa, sem derrubar a página.

Acrescentar uma métrica é editar o `metrics.yaml` — as rotas e o template não mudam,
porque ambos iteram sobre a lista calculada e respeitam `display_type` (`card` ou `table`).

### Custo estimado

`settings.token_cost` traz a tarifa (US$ 3,00/M entrada e US$ 15,00/M saída), valor
documentado nos próprios `execution-report` da Factory para `claude-sonnet-4-6`. Ajuste
ali para reprecificar todo o portfólio.

---

## Interface

A rota `/` entrega o **Control Tower** — o mesmo layout, menu, abas e gráficos do
`migration-factory-dashboard.html`, agora alimentado pela descoberta dinâmica.
São sete abas: Executive Overview, Pipeline Performance, Token Analytics, FinOps,
Quality & Operations, Factory Operations e Custo por Modelo.

O HTML é uma **casca**: os dados vêm de `GET /api/dashboard-data`. O servidor descobre
os projetos, lê cada `pipeline-runner-metrics.json`, aplica o filtro e calcula as
métricas do `metrics.yaml` sobre o recorte. Trocar um filtro refaz a chamada — por isso
os KPIs e os gráficos **nunca discordam**: saem do mesmo recorte, calculado uma vez.

Cada aba tem link direto: `/#/exec`, `/#/perf`, `/#/token`, `/#/fin`, `/#/qual`,
`/#/fact`, `/#/model`.

### O que vem do metrics.yaml e o que é derivado

- **Cards de KPI** — vêm do `metrics.yaml`. O rótulo do card é o `name` da métrica, o
  valor é formatado por `format`. Renomear ou desabilitar uma métrica muda o dashboard
  sem tocar em código.
- **Séries dos gráficos** (por fase, por dia, heatmap, Pareto, waterfall, macrofases) —
  derivadas no cliente a partir dos **mesmos runs** devolvidos pela API. São recortes
  visuais dos dados, não métricas configuráveis. Três KPIs continuam derivados por
  dependerem desse agrupamento e estão marcados com "(derivado)" na tela:
  `Cost per Phase`, `phase_failure_rate` e `Avg Pipeline Health Score`.
- **Tarifa de custo** — `settings.token_cost` no `metrics.yaml`, exibida somente leitura
  na barra de filtros. A aba "Custo por Modelo" é um simulador *what-if* do lado do
  cliente e não altera nenhuma métrica.

`/detalhe` mantém a visão tabular por projeto, útil para diagnosticar a descoberta.

---

## Acompanhamento em tempo real

O atributo de acompanhamento é o **`execution_status`** do
`pipeline-runner-metrics.json`. O painel o trata assim:

| Valor | Exibição | Conta como |
|---|---|---|
| `running` | **Em execução** (ponto pulsante) | `executions_in_progress` |
| `completed` | Concluída | `successful_executions` |
| `completed_with_warnings` | Com avisos | `executions_with_warnings` |
| `aborted`, `failed` | Abortada | `failed_executions` |
| `interrupted` | Interrompida | `interrupted_executions` |

Enquanto houver ao menos uma execução `running`:

- a topbar mostra **"● N em execução"**;
- a Executive Overview abre com uma faixa laranja listando os projetos em curso e o
  contador da próxima leitura;
- o cliente **repolla sozinho** na cadência de `refresh.interval_seconds`
  (`config/app.yaml`, padrão 30 s). Sem nenhuma execução em curso, o polling para.

Cada leitura — automática ou pelo botão **Atualizar** — compara o `execution_status` de
cada projeto com o da leitura anterior. Toda transição vira um aviso no topo da página
(`cadastro-funcionarios-04: Em execução → Com avisos`), inclusive projetos que entraram
ou saíram do escopo.

Nada disso depende de cache quente: a chave do cache inclui `mtime` e tamanho, então um
arquivo que o pipeline acabou de gravar é sempre relido. Os tokens e as fases de uma
execução em curso crescem a cada leitura.

---

## APIs

| Rota | Método | Retorno |
|---|---|---|
| `/` | GET | Control Tower (casca HTML) |
| `/detalhe` | GET | visão tabular por projeto |
| `/api/dashboard-data` | GET | runs do escopo + métricas recalculadas sobre ele |
| `/api/projects` | GET | lista atual de projetos descobertos |
| `/api/metrics` | GET | métricas consolidadas e por projeto |
| `/api/refresh` | **POST** / GET | redescobre, relê e recalcula |
| `/api/health` | GET | liveness |

`/api/dashboard-data` aceita `project` (repetível), `status`, `mode`, `from` e `to`.

`/api/metrics` aceita `?project=<id>` e `?scope=portfolio|project`, e devolve
`available_metrics` / `unavailable_metrics`.

### Por que `/api/refresh` aceita GET

A §11.1 pede POST preferencialmente. POST é o método documentado. **GET foi mantido**
porque a operação é integralmente somente-leitura — ela não modifica nenhum arquivo de
origem, apenas relê o disco — e isso permite acioná-la do navegador e de healthcheck sem
ferramenta extra. O campo `method` na resposta indica qual foi usado.

### O que as respostas nunca expõem

Stack trace, caminho absoluto, variável de ambiente, mensagem crua do sistema
operacional ou configuração sensível. `metrics_file` sai como caminho **relativo**
(`<projeto>/outputs/pipeline_runner/pipeline-runner-metrics.json`). Caminhos completos
existem só no log local, para diagnóstico.

---

## Atualização e cache

A estratégia obrigatória é **por requisição** (`refresh.strategy: request`): cada acesso
refaz a descoberta, compara com a leitura anterior, relê o que mudou e recalcula. Não há
serviço em background.

O cache em memória é **opcional** (`projects.cache.enabled`) e guarda apenas conteúdo de
arquivo já lido, com chave `(caminho, mtime, tamanho)`:

- um arquivo alterado muda a chave e é relido — invalidação automática;
- o cache **não** guarda a lista de projetos, então nunca impede a descoberta de um
  projeto novo nem preserva um projeto removido;
- `DashboardService.clear_cache()` esvazia; `cache.enabled: false` desliga.

### Leitura consistente (§9.2)

O arquivo pode estar sendo gravado pelo pipeline. Antes de ler, o leitor captura
`mtime_ns` e tamanho; depois de ler, captura de novo. Se mudaram, tenta outra vez até
`read.stability_retries`. Persistindo a instabilidade, o projeto fica com
`read_error` e a mensagem "arquivo sendo gravado pelo pipeline; leitura temporariamente
indisponível" — os demais projetos seguem normalmente.

O arquivo é aberto somente para leitura. Nada é bloqueado, renomeado, movido ou alterado.

---

## Log

Cada leitura registra: projeto identificado, caminho do arquivo, data/hora, se o arquivo
foi encontrado, se é válido, erro de leitura, e quais projetos entraram ou saíram desde a
leitura anterior.

---

## Limites conhecidos

- **MAX_PATH no Windows.** O caminho completo inclui
  `outputs/pipeline_runner/pipeline-runner-metrics.json` (52 caracteres) além do nome do
  projeto e da raiz. Em raízes já profundas, nomes de projeto muito longos podem estourar
  o limite de 260 caracteres e o arquivo fica inacessível. O teste de nome longo usa 56
  caracteres por isso.
- **`ignored_directories` não inclui `_template`.** A lista é exatamente a da
  especificação, então `projects/_template` aparece como `metrics_unavailable`. Se não for
  um projeto real, acrescente-o à lista em `config/app.yaml` — é configuração, não código.
- **Teste de permissão de diretório** (§15.1 #21) é pulado no Windows: `chmod` não remove
  permissão de leitura de diretório lá. Ele roda em Linux/macOS.

---

## Cobertura de testes

61 testes cobrindo os 25 cenários da §15.1:

| # | Cenário | Teste |
|---|---|---|
| 1 | um projeto válido | `test_discovers_single_valid_project` |
| 2 | múltiplos projetos | `test_discovers_multiple_projects_sorted` |
| 3 | arquivo válido | `test_reads_valid_metrics_file` |
| 4 | sem pasta `outputs` | `test_project_without_outputs_directory` |
| 5 | sem pasta `pipeline_runner` | `test_project_without_pipeline_runner_directory` |
| 6 | sem o arquivo | `test_project_without_metrics_file_is_still_registered` |
| 7 | arquivo vazio | `test_empty_file`, `test_whitespace_only_file` |
| 8 | JSON inválido | `test_invalid_json`, `test_root_element_must_be_object` |
| 9 | esquemas diferentes | `test_schema_variation_is_tolerated` |
| 10 | projeto incluído depois | `test_new_project_is_detected_on_next_discovery` |
| 11 | projeto removido depois | `test_removed_project_disappears` |
| 12 | arquivo alterado depois | `test_cache_is_invalidated_when_file_changes` |
| 13 | removido fora da consolidação | `test_removed_project_is_excluded_from_portfolio` |
| 14 | inválido não bloqueia os outros | `test_invalid_file_does_not_block_other_projects` |
| 15 | métricas por projeto | `test_project_metrics_are_computed` |
| 16 | métricas de portfólio | `test_portfolio_metrics` |
| 17 | invalidação de cache | `test_cache_is_invalidated_when_file_changes` |
| 18 | arquivo alterado durante a leitura | `test_file_changing_during_read_is_retried_then_reported` |
| 19 | raiz por variável de ambiente | `test_environment_variable_overrides_yaml` |
| 20 | raiz inexistente | `test_missing_root_directory_raises_configuration_error` |
| 21 | raiz sem permissão | `test_root_without_read_permission` (Linux/macOS) |
| 22 | pastas técnicas ignoradas | `test_technical_directories_are_ignored` |
| 23 | nome com espaços | `test_project_name_with_spaces` |
| 24 | nome longo | `test_very_long_project_name` |
| 25 | dados não se misturam | `test_project_data_is_not_mixed` |

Nenhum teste que cria, altera ou remove arquivos usa o diretório real. `test_real_data.py`
lê `projects/` somente para leitura e compara o SHA-256 de todos os arquivos antes e
depois, provando que nada foi tocado.
