# Guia 02 — Esteira de agentes + GitHub Copilot CLI

Rodar a esteira AVA Fabric com **100% das requisições passando pela compressão**
antes de chegarem ao Azure AI Foundry, e com a economia atribuída a cada agente.

Pré-requisito: o **passo 2 do [guia 01](01-standalone.md)** (venv instalado).
Todos os comandos rodam **da raiz do repositório**.

---

## Como funciona

```
┌──────────────────────────────────────────────────────────────────────┐
│  copilot  (GitHub Copilot CLI, modo BYOK)                            │
│     lê os agentes .md de src/modules/ava-fabric-agents/**            │
└───────────────────────────────┬──────────────────────────────────────┘
                COPILOT_PROVIDER_BASE_URL = http://127.0.0.1:8787
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│  Headroom proxy  :8787                                               │
│    comprime o contexto · registra tokens_before/after/latency_ms     │
└───────────────────────────────┬──────────────────────────────────────┘
                ANTHROPIC_TARGET_API_URL
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│  Azure AI Foundry  ...services.ai.azure.com/anthropic                │
│    wire model claude-sonnet-4-6 · janela 200.000 tokens              │
└──────────────────────────────────────────────────────────────────────┘
```

O endpoint é a superfície **Anthropic** (`/v1/messages`) do Foundry, não Azure
OpenAI. O proxy cobre `/v1/messages` e `/v1/chat/completions`.

> **Por que proxy, e não um step de compressão dentro de cada agente?** Não
> existe cliente LLM em Python neste repositório — os agentes são arquivos `.md`
> executados pelo Copilot CLI. Não há ponto de código onde interceptar. O proxy
> é a única camada por onde tudo passa.

---

## Passo 1 — Preparar as credenciais

### 1.1 Chave do Foundry

```powershell
Test-Path .copilot-key
```

Se `False`, crie o arquivo na raiz do repo contendo **apenas** a chave, sem
quebra de linha extra. Já está no `.gitignore`.

### 1.2 Copilot CLI no PATH

```powershell
where.exe copilot
```

Se não achar, instale o GitHub Copilot CLI e reabra o terminal.

### 1.3 Endpoint (só se for diferente do default)

O default está em [`headroom.yaml`](../headroom.yaml). Para sobrescrever sem
mexer em código, use uma das duas camadas:

**Por projeto** — `projects/{PROJECT}/context/project-config.yaml`:

```yaml
headroom:
  model: "claude-sonnet-4-6"
  context_limit: 200000
  proxy:
    upstream: "https://SEU-RECURSO.services.ai.azure.com/anthropic"
```

**Por ambiente** — copie `.env.example` para `.env` e ajuste
`ANTHROPIC_TARGET_API_URL`.

Confirme o que está valendo:

```powershell
python src/shared/tools/headroom/headroom_config.py -p Meu-ERP
```

---

## Passo 2 — Subir o proxy

Numa aba dedicada (deixe aberta durante toda a sessão):

```powershell
.\src\shared\tools\headroom\run_standalone.ps1
```

Ou em segundo plano:

```powershell
python src/shared/tools/headroom/headroom_tool.py proxy start
python src/shared/tools/headroom/headroom_tool.py proxy status
```

Esperado: `🟢 proxy 127.0.0.1:8787 no ar → https://…/anthropic`

---

## Passo 3 — Iniciar a sessão da esteira

```powershell
.\copilot-cli-headroom.bat
```

Confira o cabeçalho:

```
Environment variables configured:
  COPILOT_PROVIDER_TYPE=anthropic
  COPILOT_PROVIDER_BASE_URL=http://127.0.0.1:8787      <-- proxy
  COPILOT_PROVIDER_BEARER_TOKEN=****abcd
  COPILOT_PROVIDER_MODEL_ID=claude-sonnet-4
  COPILOT_PROVIDER_WIRE_MODEL=claude-sonnet-4-6
  ANTHROPIC_TARGET_API_URL=https://…/anthropic
  headroom compression=yes                              <-- confirmação
```

`headroom compression=yes` é a confirmação de que a interceptação está ativa.

### Se aparecer `compression=no`

```
WARNING: Headroom proxy nao respondeu em http://127.0.0.1:8787.
         Degradando para o endpoint direto -- SEM compressao de contexto.
```

Isso é **por design**: o proxy fora do ar nunca bloqueia a sessão. Volte ao
passo 2, ou siga sem compressão se for intencional.

Se o proxy **está** no ar e mesmo assim aparece `compression=no`, rode o doctor:

```powershell
python src\shared\tools\headroom\headroom_tool.py doctor
```

O `.bat` sonda o proxy com o Python do venv da tool
(`src\shared\tools\headroom\.venv\Scripts\python.exe`) e cai para o `python` do
PATH só se o venv não existir — nesse caso ele avisa explicitamente. Antes, com
`python` puro, um interpretador ausente ou incompatível devolvia o mesmo
`errorlevel 1` do proxy fora do ar, e a fase inteira rodava sem compressão sem
nenhum sinal. Se o aviso de venv aparecer, rode `.\src\shared\tools\headroom\setup.ps1`.

### Porta: nunca hardcoded

O `.bat` resolve host e porta em runtime:

```powershell
python src\shared\tools\headroom\headroom_config.py --proxy-url
# http://127.0.0.1:8787
```

Isso respeita `HEADROOM_PORT`, o bloco `headroom:` do `project-config.yaml` e o
`headroom.yaml`, nessa ordem de precedência. Subir o proxy em outra porta
(`run_standalone.ps1 -Port 8788`) passou a funcionar sem editar o `.bat` — antes,
a porta era duplicada nos dois arquivos e o `.bat` continuava sondando 8787,
falhava e degradava em silêncio.

### `copilot` fora do `.bat` não passa pelo proxy

`.vscode/settings.json` injeta `HEADROOM_*` e `ANTHROPIC_TARGET_API_URL` em todo
terminal integrado, mas **não** `COPILOT_PROVIDER_BASE_URL` — só o `.bat` faz
isso. Um `copilot` rodado direto do terminal vai ao Foundry sem passar pelo proxy,
enquanto a tool naquele mesmo terminal reporta o proxy configurado e no ar: o
sintoma é `proxy-requests.jsonl` sem uma linha sequer.

Não dá para resolver no `settings.json` — o bearer token vem de `.copilot-key` e
não pode viver em arquivo versionado; um terminal meio-configurado falharia na
requisição em vez de degradar. Por isso o `doctor` passou a ter o check
`copilot → proxy`, que torna o bypass visível:

```
⚠️  copilot → proxy   COPILOT_PROVIDER_BASE_URL não definida — o copilot deste
                      shell NÃO passa pelo proxy; use copilot-cli-headroom.bat
```

### Diferença para `copilot-cli-v1.bat`

A linha que importa continua sendo uma só: `COPILOT_PROVIDER_BASE_URL`. Todo o
resto do BYOK — leitura de `.copilot-key`, `COPILOT_PROVIDER_TYPE=anthropic`,
header `anthropic-version: 2023-06-01`, `--autopilot --no-ask-user` — é idêntico.
O `copilot-cli-headroom.bat` acrescenta ainda a resolução do interpretador e da
porta descritas acima, que existem só para decidir *se* o proxy está no ar.
O `copilot-cli-v1.bat` fica intacto como rollback.

---

## Passo 4 — Rodar a esteira

Dentro da sessão do Copilot, dispare a esteira normalmente:

```
SA                    # AS-IS (F1)
SA|FULL               # AS-IS com reset
```

Ou invoque as skills (`ava-asis-*`, `ava-build-cycle-*`, `ava-qa-*`, …). Nada
muda no fluxo dos agentes — a compressão é transparente.

### O que acontece por baixo

1. Toda requisição do Copilot vai para `127.0.0.1:8787`
2. O proxy comprime o contexto e encaminha ao Foundry
3. Cada agente, ao terminar, chama `pipeline_observer.py track` — e esse `track`
   **também** grava a linha do headroom (`source: "self-report"`)
4. O orquestrador da fase, ao encerrar, roda `headroom_tool.py attribute --phase FN`,
   que cruza a janela de execução de cada agente com o log do proxy e grava a
   economia **medida** (`source: "proxy"`)

> **Nenhum agente comum tem instrução de headroom no `.md`, e isso é deliberado.**
> A compressão vem do proxy — nada dentro do agente a liga ou desliga. E a
> atribuição vem do hook no `track`, que **101 agentes** já chamam: 1 arquivo em vez
> de 105, sem uma segunda diretiva `Bash:` que o LLM possa pular. O bloco de
> observabilidade é mantido à mão em ~100 arquivos e já havia produzido 51
> inconsistências (3 agentes reportando o id de outro, 6 com a fase errada);
> duplicar essa superfície pioraria os dados em vez de melhorá-los. Ver `specs/032`.

**Cobertura**: F1 a F8, todos os 101 agentes despacháveis.

Os únicos com bloco explícito são os **6 orquestradores de fase** — não para
comprimir, mas porque só eles têm a visão de fase necessária para consolidar:

| Orquestrador                | Fase | Consolida                                   |
| --------------------------- | ---- | ------------------------------------------- |
| `ava-asis-orchestrator`   | F1   | `attribute --phase F1`                    |
| `ava-tobe-orchestrator`   | F2   | `attribute --phase F2`                    |
| `ava-stack-orchestrator`  | F4   | `attribute --phase F4`                    |
| `ava-qa-orchestrator`     | F5   | `attribute --phase F5`                    |
| `ava-devops-orchestrator` | F6   | `attribute --phase F6`                    |
| `ava-master-orchestrator` | —   | `attribute` (esteira inteira) + `stats` |

Os 5 agentes que consomem artefatos AST mantêm um `Step 1.1` reduzido, só com a
consulta de `slice` (qual fatia ler) — o registro de economia saiu de lá para não
duplicar a contagem do hook.

---

## Passo 5 — Reduzir o contexto antes do dispatch

O proxy comprime o que é enviado. Enviar menos, de saída, é ainda melhor — e é
o que a `AGENT_ARTIFACT_SLICE` faz.

```powershell
# Orçamento total do projeto e modo de execução
python src/modules/ava-fabric-agents/asis-diagnostic/utils/context_budget.py `
  --project processaERP-008 --json

# Fatia de UM agente
python src/shared/tools/headroom/headroom_tool.py -p processaERP-008 slice `
  --agent ava-asis-db-analyzer
```

```
🧮 Headroom slice :: processaERP-008 :: ava-asis-db-analyzer
   artefatos : 03_database_rules, 04_database_schemas, 05_procedures
   tokens    : 559,144 de 200,000 (279.6% do limite)
   compressed: ...\ast-raw\delphi\compressed
```

As duas ferramentas leem o **mesmo** dict canônico — `slice` mostra a fatia de um
agente, `context_budget` decide o `execution_mode` (`subagent` / `inline` /
`bc_scoped`) do orquestrador.

> ⛔ **Nenhum agente deve receber o payload completo.** Foi a causa-raiz RC-1 da
> ISSUE-002: 761.376 tokens por `runSubagent`, chamadas de até 62 minutos e 8 de
> 19 artefatos F1 não gerados.

---

## Passo 6 — Conferir a economia

### Por agente (esteira)

```powershell
python src/shared/tools/headroom/headroom_tool.py -p processaERP-008 stats
```

Saída (exemplo ilustrativo — os totais refletem o baseline medido em
`processaERP-008` em 2026-07-28; a quebra por agente é fictícia):

```
📊 Headroom stats :: processaERP-008
   chamadas : 12  (erros: 0)
   tokens   : 1,194,239 → 761,376  (-36.2%)
   economia : 432,863 tokens
   ── por agente ──
   ava-asis-db-analyzer                     4x    559,144 →   187,300  (-66.5%)
   ava-asis-inventory                       3x     72,434 →    11,200  (-84.5%)
```

JSONL bruto:

```powershell
Get-Content projects\processaERP-008\outputs\observability\headroom-metrics.jsonl -Tail 5
```

### Por requisição (proxy)

```powershell
$H = "src\shared\tools\headroom\.venv\Scripts\headroom.exe"
& $H perf --hours 24
& $H savings
& $H dashboard
Get-Content .headroom\proxy-requests.jsonl -Tail 5
```

### Relatórios da esteira

Os relatórios existentes continuam funcionando sem mudança:

```powershell
python src/shared/tools/pipeline_observer.py -p processaERP-008 dashboard
python src/shared/tools/pipeline_observer.py -p processaERP-008 report
```

---

## Passo 7 — MCP no VSCode (opcional)

Recarregue a janela e rode **MCP: List Servers**. Devem aparecer `ava-headroom`
e `ava-headroom-cli`, com as ferramentas `headroom_slice`, `headroom_retrieve`,
`headroom_decode`, `headroom_compress`, `headroom_stats`.

O `.vscode/settings.json` também redireciona o **Copilot Chat** para o proxy:

```json
"github.copilot.advanced": {
  "debug.overrideProxyUrl": "http://127.0.0.1:8787"
}
```

> O MCP é **sob demanda** — comprime o que for pedido explicitamente. Para
> comprimir *todas* as requisições, o proxy continua obrigatório. As duas
> camadas são complementares.

---

## Encerrar a sessão

```powershell
# 1. sair do copilot
exit

# 2. derrubar o proxy
python src/shared/tools/headroom/headroom_tool.py proxy stop
#    (ou Ctrl+C na aba do run_standalone)

# 3. consolidar
python src/shared/tools/headroom/headroom_tool.py -p processaERP-008 stats
python src/shared/tools/pipeline_observer.py -p processaERP-008 finalize --auto-report
```

---

## Rollback — 3 níveis independentes

| Nível | Ação                                                    | Efeito                                                                                                  |
| ------ | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 1      | `headroom: {enabled: false}` no `project-config.yaml` | Desliga a tool naquele projeto                                                                          |
| 2      | Usar`copilot-cli-v1.bat`                                | Volta ao endpoint direto, sem proxy. O arquivo está intacto                                            |
| 3      | `git rm -r src/shared/tools/headroom`                   | Remove a tool.`context_budget.py` não é afetado; os consumidores caem num `decode_headroom` no-op |

---

## Troubleshooting

| Sintoma                                                                                 | Causa                                                                                                                                                                                                                          | Ação                                                                                                                                                                                      |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `headroom compression=no`                                                             | Proxy fora do ar                                                                                                                                                                                                               | Passo 2. A sessão continua funcionando sem compressão                                                                                                                                     |
| `ERROR: .copilot-key not found`                                                       | Chave ausente                                                                                                                                                                                                                  | Passo 1.1                                                                                                                                                                                   |
| `Warning: copilot not found on PATH`                                                  | Copilot CLI não instalado                                                                                                                                                                                                     | Passo 1.2                                                                                                                                                                                   |
| **401 / 403** vindo do Foundry                                                    | Chave inválida ou header não repassado                                                                                                                                                                                       | Teste sem proxy (`copilot-cli-v1.bat`). Se funcionar lá e falhar aqui, o problema é o encaminhamento do proxy — verifique `ANTHROPIC_TARGET_API_URL` em `headroom_config.py --env` |
| `Model 'claude-sonnet-4-6' not found on provider at http://127.0.0.1:8787 (HTTP 404)` | O Copilot valida o*wire model* com `GET /v1/models/{modelo}`. Essa rota é **passthrough** no headroom (encaminha, não responde local), e a superfície Anthropic do Foundry não parece servir metadados de modelo | Ver[Anexo A](#anexo-a--model-not-found-http-404-no-copilot-cli)                                                                                                                              |
| **404** genérico no upstream                                                     | URL do upstream errada                                                                                                                                                                                                         | O caminho tem que terminar em`/anthropic`. Confira com `python src/shared/tools/headroom/headroom_config.py --env`                                                                      |
| Timeout em prompt grande                                                                | Payload acima da janela                                                                                                                                                                                                        | `context_budget.py --json` → use `execution_mode` `inline` ou `bc_scoped`                                                                                                          |
| `stats` → `nenhuma métrica registrada`                                            | Nenhum agente chamou`track` ainda                                                                                                                                                                                            | O hook só grava no`track`. Confira `agent-events.jsonl`; se ele também estiver vazio, nenhum agente se auto-reportou                                                                  |
| `attribute` → `nenhuma requisição no log do proxy`                               | A sessão não passou pelo proxy, ou`HEADROOM_LOG_FILE` está desligado                                                                                                                                                      | Confira`headroom_config.py --env` e `.headroom/proxy-requests.jsonl`. O comando não inventa números — sai com código 1                                                              |
| Fatia grande em`__unattributed__`                                                     | Agentes que não chamaram`track`, ou `duration_ms` subestimado                                                                                                                                                             | `verify_agent_observability.py` acha os sem bloco. A falha é para o lado seguro: órfão, não atribuição errada                                                                       |
| `⚠️ N ambíguas` no `attribute`                                                   | Dispatch paralelo — janelas sobrepostas                                                                                                                                                                                       | Esperado. Cada requisição foi dividida em`1/N`; o rótulo existe para você não ler o número como exato                                                                               |
| `slice` → `compressed: (ausente)`                                                  | Step 0 (AST) não rodou                                                                                                                                                                                                        | Rode a extração AST. O`slice` degrada, não bloqueia                                                                                                                                    |
| Números do`stats` e do `perf` divergem                                             | São camadas distintas                                                                                                                                                                                                         | `stats` = auto-reporte dos agentes; `perf` = todas as requisições. Ver [README dos guias](README.md)                                                                                   |
| `SSLV3_ALERT_BAD_RECORD_MAC`                                                          | HTTP/2 com streams cancelados                                                                                                                                                                                                  | Já mitigado — o proxy sobe com`--no-http2`                                                                                                                                              |

---

## Checklist da sessão

- [ ] `.copilot-key` existe · `copilot` no PATH
- [ ] `headroom_tool.py doctor` sem ⚠️ em `venv`, `cli` e `motor`
- [ ] `proxy status` → 🟢 no ar
- [ ] `copilot-cli-headroom.bat` → `headroom compression=yes`
- [ ] `context_budget.py --json` consultado antes do dispatch dos agentes
- [ ] Ao final: `stats` + `perf` + `pipeline_observer finalize`

---

## Anexo A — `Model not found` (HTTP 404) no Copilot CLI

```
Model 'claude-sonnet-4-6' not found on provider at http://127.0.0.1:8787 (HTTP 404).
  Check that the model is available on your provider.
```

### O que já está descartado

Investigação feita em 2026-07-30 contra o proxy rodando. **O proxy não é a causa**:

| Verificação                                                                                              | Resultado                                                                                                                                                              |
| ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Saúde do proxy (`GET /health`)                                                                          | `healthy`, `rust_core: loaded`, `backend: anthropic`                                                                                                             |
| Upstream resolvido (`GET /admin/upstream`)                                                               | `https://…services.ai.azure.com/anthropic` — correto                                                                                                               |
| Montagem da URL (`build_copilot_upstream_url`)                                                           | `/v1/messages` → `…/anthropic/v1/messages`, **idêntica** à do modo direto                                                                                |
| Reescrita do nome do modelo (`sanitize_anthropic_model_id`)                                              | no-op para`claude-sonnet-4-6`                                                                                                                                        |
| Base URL do`.bat`                                                                                        | Correta: para`provider_type=anthropic` o próprio headroom usa a **raiz** (`http://127.0.0.1:8787`). O sufixo `/v1` só vale para `provider_type=openai` |
| Comparação direta × proxy, sem credencial, em`/v1/messages`, `/v1/models` e `/v1/models/{modelo}` | **Os seis retornam o mesmo status (401)** — o proxy responde exatamente como o endpoint direto                                                                  |

### A causa provável

O Copilot CLI valida o *wire model* pedindo `GET /v1/models/{modelo}` ao provider.
No headroom essa rota é **passthrough** (`providers/proxy_routes.py`): ele encaminha
ao upstream e devolve a resposta — não responde localmente. Se a superfície
Anthropic do Foundry não implementa metadados de modelo, ela devolve 404 e o
Copilot reporta exatamente a mensagem acima.

Isso explica por que o modo direto funciona e o modo proxy não: o Copilot
aparentemente pula essa validação quando o host é o do provider conhecido, e a
executa quando o host é local/desconhecido.

> **Esta última parte é hipótese, não fato verificado.** Reproduzir exige a chave
> do Foundry, e o `.copilot-key` não estava presente nesta cópia de trabalho.

### Comando que separa as causas

Com a chave em mãos, rode da raiz do repo:

```powershell
$k = (Get-Content .copilot-key -Raw).Trim()
$h = @{ "x-api-key"=$k; "anthropic-version"="2023-06-01"; "content-type"="application/json" }
$EP = "https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic"

# A) o Foundry serve metadados de modelo?
try { (Invoke-WebRequest "$EP/v1/models/claude-sonnet-4-6" -Headers $h -UseBasicParsing).StatusCode }
catch { "A) HTTP " + [int]$_.Exception.Response.StatusCode }

# B) a inferência em si funciona pelo proxy?
$b = '{"model":"claude-sonnet-4-6","max_tokens":8,"messages":[{"role":"user","content":"ping"}]}'
try { (Invoke-WebRequest "http://127.0.0.1:8787/v1/messages" -Headers $h -Method POST -Body $b -UseBasicParsing).StatusCode }
catch { "B) HTTP " + [int]$_.Exception.Response.StatusCode }
```

Leitura do resultado:

| A   | B   | Diagnóstico                                                                                                  | Correção                                                                             |
| --- | --- | ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 404 | 200 | Confirmado: o Foundry não serve`/v1/models`; a inferência funciona. O 404 é só a validação do Copilot | O proxy precisa responder`/v1/models/{id}` **localmente** em vez de encaminhar |
| 404 | 404 | O upstream está errado                                                                                       | Revisar`ANTHROPIC_TARGET_API_URL`                                                    |
| 200 | 200 | Nada quebrado nesses dois caminhos                                                                            | A falha está noutro ponto do handshake — capture com`headroom perf --raw`          |
| —  | 401 | Credencial não chegou ao upstream                                                                            | Comparar os headers enviados com os de`copilot-cli-v1.bat`                           |

### Contornos

1. **Voltar ao direto** — `copilot-cli-v1.bat` continua intacto. Perde-se a
   compressão do Copilot CLI, mas a tool (fatia, decode, métricas) segue valendo.
2. **Claude Code em vez do Copilot CLI** — `ANTHROPIC_BASE_URL=http://127.0.0.1:8787`.
   O Claude Code não faz essa validação de modelo, então o caminho comprimido
   funciona.
3. **Shim local para `/v1/models/{id}`** — a correção definitiva se o cenário
   A=404/B=200 se confirmar. Ainda não implementada.
