# Headroom — compressão de contexto do AVA Fabric

Tool determinística + proxy interceptor que reduz o contexto enviado ao endpoint
do Azure AI Foundry. Fork embedded de [`headroom-ai`](https://github.com/headroomlabs-ai/headroom)
0.33.0 via `git subtree`.

**Guias passo a passo** → [`docs/`](docs/README.md)
· [01 — Standalone](docs/01-standalone.md)
· [02 — Esteira + GitHub CLI](docs/02-esteira-github-cli.md)

Especificação completa: [`specs/031-headroom-context-compression-proxy`](../../../../specs/031-headroom-context-compression-proxy/spec.md)

---

## O que resolve

Na execução F1 de `processaERP-008` (ISSUE-002) o payload comprimido somou
**761.376 tokens**, com chamadas de subagente de até 62 minutos e 8 de 19
artefatos F1 ausentes. A spec 030 atacou o *dispatch*; esta tool ataca a
*compressão*, em três frentes:

| Frente | Como |
|---|---|
| Interceptar 100% das chamadas ao LLM | Proxy local em `127.0.0.1:8787` entre o cliente e o Foundry |
| Ler o que já está comprimido | `headroom_context.py` — único decodificador do formato Headroom no repo |
| Atribuir a economia a um agente | JSONL por projeto em `outputs/observability/headroom-metrics.jsonl` |

> **Por que proxy, e não um "step 0" em cada agente?** Não existe cliente LLM em
> Python neste repositório — os ~97 agentes são arquivos `.md` executados por um
> host surface (Copilot CLI, Copilot Chat, Claude Code). Não há ponto de código
> onde interceptar. O proxy é a única camada por onde tudo passa.

---

## Estrutura

```
src/shared/tools/headroom/
├── vendor/              fork upstream (git subtree) — NÃO editar à mão
├── headroom_config.py   config: env > project-config.yaml > headroom.yaml
├── headroom_context.py  decodificação + fatia por agente  ← o núcleo
├── headroom_tool.py     CLI (slice/decode/compress/metrics/stats/doctor/proxy)
├── mcp_server.py        MCP server `ava-headroom` (5 ferramentas)
├── headroom.yaml        defaults da tool
├── requirements.txt     headroom-ai[proxy,mcp,ml,code,memory,otel]==0.33.0
├── setup.ps1 / .sh      cria o venv isolado
├── run_standalone.*     sobe o proxy sem a esteira
├── Containerfile        build Podman/Docker (instala Rust e builda o fork)
└── podman-compose.yml
```

---

## Instalação

```powershell
.\src\shared\tools\headroom\setup.ps1            # completo
.\src\shared\tools\headroom\setup.ps1 -SkipML    # sem torch (≈ 3 GB a menos)
```

```bash
bash src/shared/tools/headroom/setup.sh --skip-ml
```

O venv fica em `.venv/`, **isolado** — o venv principal do repo continua
stdlib-only e nunca ganha `headroom-ai`.

### Fork editável × wheel PyPI

O build backend do vendor é **maturin**, que exige toolchain Rust. O `setup`
detecta `cargo`:

| `cargo` | O que acontece |
|---|---|
| presente | `pip install -e ./vendor[...]` — patches locais no fork valem imediatamente |
| ausente | `pip install headroom-ai[...]==0.33.0` (mesma versão do vendor). O fork fica como referência/patch source |

Para buildar o fork de verdade, instale Rust em <https://rustup.rs> e rode
`setup.ps1 -Force`. O `Containerfile` instala Rust e **sempre** builda o fork.

`gh` (GitHub CLI) **não** vem por pip — se precisar, instale separadamente e
deixe no PATH.

---

## Configuração

Precedência, do mais forte ao mais fraco:

1. **Ambiente** — `HEADROOM_*`, `AVA_FOUNDRY_*`, `ANTHROPIC_TARGET_API_URL`
2. **Projeto** — `projects/{p}/context/project-config.yaml` → bloco `headroom:`
3. **Tool** — `src/shared/tools/headroom/headroom.yaml`

O merge é **recursivo**: sobrescrever `proxy.port` preserva o resto do bloco
`proxy`. Nada é hardcoded em código (Artigo I da Constituição).

```powershell
python src/shared/tools/headroom/headroom_config.py -p Meu-ERP        # config efetiva
python src/shared/tools/headroom/headroom_config.py --env             # só o env do proxy
```

### O endpoint é Anthropic, não Azure OpenAI

```
https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
wire model: claude-sonnet-4-6 · janela: 200.000 tokens
```

É a superfície Anthropic (`/v1/messages`) do Foundry, consumida em BYOK — ver
`copilot-cli-v1.bat` na raiz. O proxy do headroom cobre `/v1/messages` **e**
`/v1/chat/completions`.

> ⚠️ **O headroom não tem flag `--upstream`.** O destino real é
> `--anthropic-api-url` / `ANTHROPIC_TARGET_API_URL`. Documentação que diga o
> contrário está desatualizada — ver `research.md` §1.

---

## CLI

```powershell
$T = "src/shared/tools/headroom/headroom_tool.py"

# Fatia de artefatos de um agente + custo em tokens (barato, sem LLM)
python $T -p Meu-ERP slice --agent ava-asis-db-analyzer --json

# Decodificar um artefato comprimido
python $T decode --input projects/X/outputs/asis/ast-raw/delphi/compressed/05_procedures.json

# Comprimir um arquivo
python $T -p Meu-ERP compress --input grande.json -o comprimido.json

# Creditar a economia MEDIDA pelo proxy a cada agente (fim de fase)
python $T -p Meu-ERP attribute --phase F1
python $T -p Meu-ERP attribute --dry-run        # calcula sem gravar

# Agregado do projeto, separando estimado × medido
python $T -p Meu-ERP stats

# Registro avulso (raro — os agentes NÃO chamam isto; ver § Métricas)
python $T -p Meu-ERP metrics --agent ava-asis-inventory --phase F1 `
  --original 12400 --compressed 1860 --latency-ms 320

# Diagnóstico e proxy
python $T doctor
python $T proxy start | stop | status
```

Exit codes: `0` OK · `1` degradado (motor ausente, proxy fora do ar, artefato
faltando) · `2` erro de uso.

---

## Proxy

### Standalone — sem a esteira

```powershell
.\src\shared\tools\headroom\run_standalone.ps1
.\src\shared\tools\headroom\run_standalone.ps1 -Project Meu-ERP -Port 8788
```

Não exige projeto, artefato AST nem agente rodando. Roda em primeiro plano;
Ctrl+C encerra.

### Copilot CLI através do proxy

```powershell
.\copilot-cli-headroom.bat
```

Idêntico a `copilot-cli-v1.bat`, exceto por `COPILOT_PROVIDER_BASE_URL` apontar
para o proxy. **Se o proxy não estiver no ar, degrada para o endpoint direto com
aviso** — a sessão nunca é bloqueada. `copilot-cli-v1.bat` fica intacto como
rollback.

### Outros clientes

```powershell
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8787"    # Claude Code
$env:OPENAI_BASE_URL    = "http://127.0.0.1:8787/v1" # clientes OpenAI-compatible
```

### Container

```powershell
podman-compose -f src/shared/tools/headroom/podman-compose.yml up -d
```

Publica **apenas** em `127.0.0.1:8787` e roda como usuário não-root: a chave do
Foundry trafega pelo proxy (Artigo VII).

---

## MCP

`.vscode/mcp.json` registra `ava-headroom` (nosso servidor) e `ava-headroom-cli`
(o `headroom mcp serve` upstream). Ferramentas expostas: `headroom_slice`,
`headroom_retrieve`, `headroom_decode`, `headroom_compress`, `headroom_stats`.

O MCP é **sob demanda**. Para comprimir *todas* as requisições o proxy continua
sendo obrigatório — as duas camadas são complementares.

---

## Formatos decodificados

`headroom_context.py` é o **único** lugar do repo que conhece o formato Headroom.
A pré-compressão (no analisador externo) escolhe o motor em runtime, e os dois
formatos aparecem em produção:

**[A] Motor real — string tabular do SmartCrusher**

```
[400]{columns:int,kind:string,loc:int,name:string,pk:string,schema:string}
3,table,100,TBL_000,ID_0,dbo
```

Cabeçalho `[N]{chave:tipo,…}` + **CSV RFC 4180** (aspas `"`, escape `""`, newline
dentro de campo citado, vazio = `null`). Tipos `string · int · float · bool · json`,
sufixo `?` = nullable. Decodificação **lossless**, validada em roundtrip.

**[B] Motor fallback — `factored_array`**

```json
{"__headroom__": "factored_array", "schema": [...], "count": 400,
 "kept": 90, "sampled": true, "rows": [[...]]}
```

`sampled: true` é **perda real**. `decode_report()` expõe `rows_dropped`.

```python
from headroom_context import decode_headroom, read_artifact, build_agent_context

doc = decode_headroom(json.loads(texto))        # recursivo, idempotente
schemas = read_artifact("processaERP-008", "04_database_schemas")
ctx = build_agent_context("processaERP-008", "ava-asis-db-analyzer")
```

---

## Métricas

**Nenhum agente comum precisa de instrução de headroom.** A compressão vem do
proxy, e a atribuição vem de um hook em `pipeline_observer.cmd_track` — que os
~98 agentes já chamam. Ver `specs/032`.

Três origens, distinguidas pelo campo `source` do JSONL:

| `source` | Quem grava | Quando | Sabe | Não sabe |
|---|---|---|---|---|
| `self-report` | hook do `track` | a cada agente, F1–F8 | agent_id, fase, tokens, duração | **quanto** foi comprimido |
| `proxy` | `attribute` | fim de fase, pelo orquestrador | compressão **medida** | o que não passou pelo proxy |
| `manual` | `metrics` | uso avulso | o que você informar | — |

As linhas `self-report` trazem `original_tokens: null` de propósito: o agente não
conhece o tamanho pré-compressão, e inventar o número seria pior que admitir a
lacuna. Quem preenche isso é o `attribute`.

### Como `attribute` credita a economia

O proxy sabe **quanto** comprimiu; o observer sabe **quando** cada agente rodou.
`attribute` cruza os dois:

- janela do agente = `[end_time − duration_ms, end_time]` — o estado grava
  `start == end`, porque os agentes só informam `--duration-ms`
- fusos: proxy em **UTC**, observer em **BRZ (-03:00)**
- 1 agente na janela → atribuição integral (`exclusive`)
- N agentes (dispatch paralelo) → `1/N` para cada, marcado `ambiguous`
- nenhum → bucket `__unattributed__`

A soma fecha: **atribuído + órfão == total do proxy**.

O JSONL fica em `projects/{project}/outputs/observability/headroom-metrics.jsonl`,
ao lado de `agent-events.jsonl` e `pipeline-run-state.json`.

### Consistência dos agentes

A identidade de cada agente vive em três lugares que já divergiram (51 violações
antes de `specs/032`). O gate:

```powershell
python src/shared/utils/verify_agent_observability.py
python src/shared/tools/agent_registry.py
```

---

## Manutenção do fork

```powershell
git subtree pull --prefix src/shared/tools/headroom/vendor `
  https://github.com/headroomlabs-ai/headroom.git main --squash

.\src\shared\tools\headroom\setup.ps1 -Force
python -m pytest tests/tools/ -q
```

> ⚠️ **Revalide o roundtrip depois de todo `git subtree pull`.** O encoding
> tabular `[N]{k:t}\n<csv>` **não é documentado publicamente** — foi determinado
> empiricamente. Se o upstream mudar o formato, os testes de unidade continuam
> passando (usam fixtures) mas a leitura de artefatos reais quebra em silêncio.
> Procedimento em `specs/031-.../quickstart.md` §10.

Se precisar patchear o motor: edite em `vendor/`, commite normalmente e use
`git subtree push`. Com Rust instalado o `setup` já roda o fork em modo editável.

---

## Troubleshooting

| Sintoma | Causa provável | Ação |
|---|---|---|
| `Content detection using pure-Python backend…` | No Windows o detector nativo Magika/ONNX é recusado por padrão | Cosmético. Em Linux/container defina `HEADROOM_DETECT_BACKEND=rust` |
| `doctor` → `venv isolado: ausente` | `setup` não rodou | `.\setup.ps1` |
| `doctor` → `motor: indisponível` | `headroom-ai` fora do venv/PATH | `.\setup.ps1 -Force`. A esteira continua rodando: decodificação é stdlib |
| `slice` → `compressed: (ausente)` | Step 0 (AST) não rodou | Rode a extração AST; o `slice` degrada, não bloqueia |
| `copilot-cli-headroom.bat` → `compression=no` | Proxy fora do ar | `run_standalone.ps1` ou `headroom_tool.py proxy start` |
| `pip install -e ./vendor` falha com maturin/cargo | Sem toolchain Rust | Deixe o `setup` cair no wheel PyPI, ou instale <https://rustup.rs> |
| `SSLV3_ALERT_BAD_RECORD_MAC` | HTTP/2 com muitos streams cancelados | Já mitigado: o proxy sobe com `--no-http2` |

---

## Invariantes

| # | Invariante | Verificação |
|---|---|---|
| IV1 | Uma única fonte de fatia por agente — `context_budget.AGENT_ARTIFACT_SLICE` | `grep -rn "AGENT_ARTIFACT_MAP" src/` vazio |
| IV2 | Um único decodificador do formato Headroom | `grep -rn "__headroom__" src/ --exclude-dir=vendor` → só `headroom_context.py` |
| IV3 | A esteira roda sem `headroom-ai` instalado | `pytest tests/utils/ -q` com o venv da tool ausente |
| IV4 | Sem colisão de import — nenhum `headroom.py` nesta pasta | o acesso ao upstream é `sys.path.insert(VENDOR_DIR)` |
| IV5 | Convenção de tool do repo (argparse + dispatch dict, sem `logging`, BRZ, UTF-8 guard) | leitura de código |
