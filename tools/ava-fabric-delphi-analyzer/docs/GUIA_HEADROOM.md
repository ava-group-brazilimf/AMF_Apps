# Guia — uso do Headroom na pré-compressão

O estágio 2 (`src/headroom_precompress.py`) comprime os 8 artefatos JSON antes de
entrarem no contexto do agente. Ele opera em dois modos, detectados automaticamente.

## Modo A — Headroom real (recomendado)

```bash
pip install "headroom-ai[all]"
python src/run_pipeline.py ./examples/Meu-ERP \
    --extraction ./.ava-fabric/extraction --compressed ./.ava-fabric/compressed
```

Internamente, cada artefato é passado a `headroom.compress()`:

```python
from headroom import compress, CompressConfig
cfg = CompressConfig(compress_user_messages=True, protect_recent=0,
                     min_tokens_to_compress=100)
res = compress([{"role": "user", "content": artefato_json}],
               model="claude-sonnet-4-5-20250929", config=cfg)
# res.messages[-1]["content"]  -> conteúdo comprimido
# res.tokens_before / res.tokens_after / res.compression_ratio / res.transforms_applied
```

O pipeline do Headroom aplica **CacheAligner** (estabiliza o prefixo) e roteia para o
**SmartCrusher** (fatora/deduplica arrays homogêneos, preserva anomalias). A
compressão é **reversível** (CCR): o original fica cacheado e pode ser recuperado.

Números de referência no Meu-ERP (Headroom real):

| Artefato               |        tokens_in |       tokens_out |         redução | transform     |
| ---------------------- | ---------------: | ---------------: | ----------------: | ------------- |
| 05_procedures          |           40.703 |           16.092 |           −60,5% | smart_crusher |
| 03_database_rules      |            2.225 |              854 |           −61,6% | smart_crusher |
| 02_form_business_rules |            7.383 |            3.804 |           −48,5% | smart_crusher |
| 04_database_schemas    |            2.593 |            1.399 |           −46,0% | smart_crusher |
| **TOTAL (8)**    | **54.907** | **23.567** | **−57,1%** |               |

## Modo B — Fallback SmartCrusher-lite (sem dependência)

Se `headroom-ai` não estiver instalado, usa-se o fallback embutido: fatora arrays de
objetos homogêneos (schema declarado uma vez + linhas como tuplas), mantém head/tail
e preserva itens com erro/anomalia. É mais agressivo estruturalmente (~−77% no
procedures) mas não é reversível como o CCR do Headroom. Use o real em produção.

## Onde encaixa o CacheAligner

O envelope dos artefatos (`src/schemas.py`) isola os campos voláteis (`generated_at`,
`run_id`) num bloco `_volatile` no **fim** do JSON. Isso mantém o prefixo estável
entre execuções — casando com o CacheAligner do Headroom e com o `cache_control: ephemeral` da Anthropic, para maximizar cache-hit quando os artefatos entram num
prompt multi-módulo.

## manifest.json

Cada run grava `compressed/manifest.json` com `engine` (headroom|fallback),
`tokens_in/out`, `reduction_pct` e `transforms` por artefato — pronto para alimentar
o `metrics.jsonl` de observabilidade do AVA Fabric.
