# Research — Headroom Context Compression

Levantamento executado antes da implementação (Cat. 0 do plano). Existe porque o
prompt de origem assumia uma superfície de CLI e um endpoint que **não conferem**
com a realidade. Tudo abaixo foi verificado por execução, não por documentação.

---

## 1. Superfície real da CLI (`headroom-ai` 0.30.0 / 0.33.0)

### `headroom --help` — comandos

```
agent-savings · audit-reads · capture · copilot-auth · dashboard · diff · doctor
evals · init · install · learn · loc · mcp · memory · output-savings · perf
proxy · savings · sg · tools · unwrap · update · wrap
```

### Divergências contra o prompt de origem

| Prompt de origem | Real | Impacto |
|---|---|---|
| `headroom proxy --upstream "$AZURE_OPENAI_ENDPOINT"` | **Não existe `--upstream`.** O destino Anthropic é `--anthropic-api-url` / env `ANTHROPIC_TARGET_API_URL`; o OpenAI é `--openai-api-url` / `OPENAI_TARGET_API_URL` | `headroom_config.proxy_env()` emite `ANTHROPIC_TARGET_API_URL`; há teste garantindo que `HEADROOM_UPSTREAM` **não** é emitido |
| `headroom stats` | **Não existe.** São `savings`, `perf`, `output-savings`, `agent-savings`, `dashboard` | `headroom_tool.py stats` agrega o **nosso** JSONL, não invoca a CLI |
| `--host 0.0.0.0` | Default real é `127.0.0.1` (env `HEADROOM_HOST`) | Mantido `127.0.0.1` — a chave do Foundry trafega pelo proxy (Art. VII) |
| `HEADROOM_DETECT_BACKEND=rust` como default | Não aparece nas flags de `proxy`. No Windows o detector nativo (Magika/ONNX) é recusado por padrão: *"Content detection using pure-Python backend (native Magika/ONNX detector is unsafe by default on Windows; override with HEADROOM_DETECT_BACKEND=rust)"* | Default da tool = `auto`; `rust` fica documentado para Linux/container |
| `.venv/bin/python` no `mcp.json` | Windows usa `.venv/Scripts/python.exe` | Corrigido |

### Flags de `headroom proxy` efetivamente usadas

| Flag / env | Uso nesta entrega |
|---|---|
| `--host` / `HEADROOM_HOST` | `127.0.0.1` |
| `-p, --port` / `HEADROOM_PORT` | `8787` |
| `--anthropic-api-url` / `ANTHROPIC_TARGET_API_URL` | endpoint do Foundry |
| `--backend` / `HEADROOM_BACKEND` | `anthropic` |
| `--mode` / `HEADROOM_MODE` | `token` (máxima compressão) |
| `--log-file` / `HEADROOM_LOG_FILE` | JSONL com `timestamp, request_id, model, tokens_before, tokens_after, latency_ms` |
| `--no-http2` | evita `SSLV3_ALERT_BAD_RECORD_MAC` quando muitos streams concorrentes são cancelados |
| `--request-timeout-seconds` | 600 |
| `HEADROOM_TELEMETRY=off` | telemetria anônima desligada |

### `headroom wrap copilot`

Existe e configura as variáveis BYOK do Copilot CLI automaticamente
(`--provider-type auto|anthropic|openai`, `--subscription`, `--no-proxy`, `-p`).
**Não foi adotado** como caminho principal: ele aponta para
`https://api.githubcopilot.com` (Copilot hospedado), enquanto esta esteira usa
BYOK contra o Foundry com chave própria em `.copilot-key`.
`copilot-cli-headroom.bat` mantém o controle explícito das mesmas variáveis que
`copilot-cli-v1.bat` já define, trocando apenas `COPILOT_PROVIDER_BASE_URL`.

### `headroom doctor`

`-p/--port`, `--json`. Exit `0` saudável · `1` avisos · `2` falha.
Mesma semântica adotada em `headroom_tool.py doctor`.

### API Python

```python
compress(messages: list[dict], model: str = 'claude-sonnet-4-5-20250929',
         model_limit: int = 200000, optimize: bool = True,
         config: CompressConfig | None = None) -> CompressResult

CompressConfig(compress_user_messages=False, compress_system_messages=True,
               protect_recent=4, protect_analysis_context=True,
               target_ratio=None, min_tokens_to_compress=250, …)

CompressResult(messages, tokens_before, tokens_after, tokens_saved,
               compression_ratio, transforms_applied)
```

---

## 2. Endpoint real da esteira

`copilot-cli-v1.bat` (raiz do repo):

```bat
set ENDPOINT=https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
set DEPLOYMENT_NAME=claude-sonnet-4-6
set "COPILOT_PROVIDER_TYPE=anthropic"
set "COPILOT_PROVIDER_BASE_URL=%ENDPOINT%"
set "COPILOT_PROVIDER_HEADERS=anthropic-version: 2023-06-01"
```

É a superfície **Anthropic** (`/v1/messages`) do Azure AI Foundry — não Azure
OpenAI. O proxy do headroom cobre `/v1/messages` **e** `/v1/chat/completions`,
então é compatível.

**Consequência para o gap L1** de `docs/plan/headroom-integration-implementation.md`:
aquele plano registrava como defeito "a pré-compressão comprime para Claude 200K
enquanto a inferência roda em Foundry (128K)". Como o Foundry aqui **é** Claude
com janela de 200K, o número está certo. O gap L1 não procede; o que esta entrega
faz é tornar o limite explícito e configurável (`context_limit`), não alterá-lo.

---

## 3. Formato de saída da pré-compressão (determinado empiricamente)

`headroom_precompress.py` (repo externo `ava-fabric-delphi-analyzer`) escolhe o
motor em runtime: usa `headroom.compress()` se `headroom-ai` estiver instalado,
senão um `SmartCrusher-lite` local. **Os dois formatos aparecem em produção.**

### [A] Motor real — string tabular do SmartCrusher

Sonda: 400 tabelas + 120 stored procedures num artefato AST sintético.

```
"[400]{columns:int,kind:string,loc:int,name:string,pk:string,schema:string}\n
3,table,100,TBL_000,ID_0,dbo\n4,table,101,TBL_001,ID_1,dbo\n…"
```

- Cabeçalho `[N]{chave:tipo,…}` — `N` = nº de linhas, chaves em **ordem alfabética**
- Corpo: **CSV RFC 4180** — `"` para citar, `""` para escapar aspas, newline
  permitido dentro de campo citado, campo vazio = `null`
- Tipos: `string` · `int` · `float` · `bool` · `json`; sufixo `?` = nullable
- `json` = objeto serializado dentro de um campo CSV citado

Sonda de escaping (60 linhas com vírgula, aspas, newline, nulo, dict aninhado):

```
HEADER: [60]{desc:string,flag:bool,loc:int,name:string,nested:json?,opt:string?,ratio:float}
ROW   : '"com, virgula",true,10,item_0,,x,1.5'
ROW   : '"com ""aspas""",false,11,item_1,,x,2.5'
ROW   : '"com'                                    <- newline DENTRO do campo citado
ROW   : 'newline",true,12,item_2,,x,3.5'
ROW   : 'simples 4,true,14,item_4,"{""a"":1}",x,5.5'
```

→ **obriga `csv.reader`**; `split("\n")` corromperia as linhas com newline embutido.

### [B] Motor fallback — `factored_array`

```json
{"__headroom__": "factored_array", "schema": ["name", "loc"],
 "count": 400, "kept": 90, "sampled": true, "rows": [["a", 1], …]}
```

`sampled: true` significa **perda real** (`kept` < `count`): o fallback mantém
30% do topo, as linhas anômalas e 15% do fim quando passa de 200 linhas. Daí
`decode_report()` expor `rows_dropped` — o consumidor precisa saber que está
lendo uma amostra.

### Validação de roundtrip

`compress()` → `decode_headroom()` sobre 520 linhas com todos os casos difíceis:

```
transforms      : ['router:smart_crusher:0.02']
tokens          : 14994 -> 5049          (-66,3%)
report          : {'table_strings': 2, 'rows_total': 520, 'rows_dropped': 0}
items     : OK  lossless  (n=120)
tables    : OK  lossless  (n=400)
idempotent: True
passthrough: True
```

> Este formato **não é documentado publicamente**. Repetir esta validação após
> todo `git subtree pull` — é o único sinal de que o upstream não mudou o
> encoding sob nossos pés.

---

## 4. Baseline de compressão em produção

`processaERP-008`, medido em 2026-07-28 (`docs/plan/headroom-integration-implementation.md`):

| Métrica | Valor |
|---|---|
| Bytes | 6,99 MB → 2,67 MB |
| Tokens | 1.194.239 → 761.376 (**−36,2%**) |
| Duração | 7.157 ms |
| Melhor artefato | `01_business_rules` −52,9% |
| Pior artefato | `09_test_coverage` −6,0% |

Os 761.376 tokens resultantes são exatamente o que a ISSUE-002 identificou como
RC-1. Conclusão registrada no plano original e confirmada aqui: *"o gargalo não é
a taxa de compressão — é o escopo"*. Por isso o fatiamento por agente
(specs/030) e o proxy (esta spec) atacam ângulos diferentes do mesmo problema.

---

## 5. Estado do repositório que condicionou o desenho

| Constatação | Verificação | Consequência de projeto |
|---|---|---|
| Nenhum cliente LLM em Python | `grep -rE '^\s*(import\|from)\s+(openai\|anthropic\|azure\|litellm\|langchain)' --include=*.py` → 0 | O `HeadroomStep` do prompt é inexequível; interceptação só via proxy |
| Repo é stdlib-only | Sem `requirements.txt`/`pyproject.toml` na raiz; `yaml` importado com `try/except` | Venv isolado; consumidores importam a tool defensivamente |
| Sem registry de tools | `src/shared/tools/__init__.py` tem 1 linha de comentário | Registro = linha no README + comando literal no agente |
| Fatia canônica já existe | `context_budget.AGENT_ARTIFACT_SLICE`, 19 agentes (specs/030) | Importar, nunca duplicar (IV1) |
| Indireção em agente não funciona | `observability-self-report.md` v2.2.0 | Comando literal inline em cada agente |
| `.gitignore` ignora o **diretório** `.vscode` | `git check-ignore -v .vscode/mcp.json` → linha 70 | Trocado por `.vscode/*` + negações; o git não reabre arquivos dentro de diretório ignorado |
| `.env.*` casa com `.env.example` | `git check-ignore -v .env.example` | Negação `!.env.example` |
| Sem toolchain Rust na máquina | `cargo` ausente; build backend do vendor é maturin | `setup.*` cai para o wheel PyPI da mesma versão |

---

## 6. Decisões descartadas

| Alternativa | Por que não |
|---|---|
| Dependência pip em vez de subtree | Recomendada, mas o usuário optou pelo fork embedded para poder patchear o motor |
| `headroom wrap copilot` como entrada | Roteia para o Copilot hospedado; a esteira é BYOK contra o Foundry |
| Ler `compressed/` por padrão no `sql_ir_generator` | O motor fallback amostra linhas — perderia entidades em silêncio num gerador determinístico. `extraction/` continua preferido, `compressed/` é fallback |
| Criar `AGENT_ARTIFACT_MAP` em `headroom_context` (proposto no plano antigo) | Criaria uma segunda fonte canônica concorrente com specs/030 |
| Instrumentar os ~97 agentes | Só 5 consomem artefatos AST hoje; o resto geraria linhas com economia zero |
| `metrics-agents.jsonl` na raiz (pedido no prompt) | Fica fora da árvore de observabilidade existente e não é por projeto; movido para `outputs/observability/` |
