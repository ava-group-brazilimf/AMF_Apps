# Quickstart — Atribuição em Toda a Esteira

Verificação manual, do mais barato ao mais caro. Os passos **1–6** rodam offline, sem o
venv da tool e sem proxy. O passo **7** exige execução real.

Rode tudo da raiz do repositório.

---

## 1 · Registro canônico

```powershell
python src/shared/tools/agent_registry.py
python src/shared/tools/agent_registry.py --agent ava-qa-exploratory
python src/shared/tools/agent_registry.py --catalog | Select-Object -First 5
```

**Esperado**: `105 arquivos (101 despacháveis)`, agrupados F1→F8 + transversal. Nenhuma
fase `?` — isso denunciaria um módulo fora de `PHASE_BY_MODULE`. As flags são
`T`=track · `O`=orquestrador · `D`=depreciado · `S`=stub.

## 2 · Consistência do auto-reporte

```powershell
python src/shared/utils/verify_agent_observability.py
python src/shared/utils/verify_agent_observability.py --json | Select-Object -First 8
```

**Esperado**: `✅ nenhuma violação`, exit 0. A linha de base antes desta entrega era
**51** (3×E1 · 6×E2 · 31×E3 · 3×E4 · 7×E5 · 1×E6).

Para ver o gate funcionando, quebre um agente de propósito num branch descartável:

```powershell
# troque --phase F5 por F1 em qualquer agente de qa-agents
python src/shared/utils/verify_agent_observability.py    # deve reportar E2 e sair 1
git checkout -- src/modules/ava-fabric-agents/qa-agents/
```

## 3 · Catálogo único

```powershell
python -c @'
import importlib.util, sys
sys.path.insert(0, "src/shared/tools")
import agent_registry
esperado = len(agent_registry.catalog())
for p, n in [("src/shared/tools/pipeline_observer.py","observer"),
             ("src/shared/tools/generate_observability_report.py","report")]:
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    print(f"{n:<9} {len(m.AGENT_CATALOG)} (estatico {len(m._STATIC_AGENT_CATALOG)}) esperado {esperado}")
'@
```

**Esperado**: os dois com **100**, estático 56. Antes eram duas listas manuais de 56 que
divergiam entre si (`ava-tobe-orchestrator` 2.1.0 × 2.3.0) e omitiam 52 agentes.

## 4 · Hook do `track` — cobertura sem editar agentes

```powershell
python src/shared/tools/pipeline_observer.py -p Meu-ERP init --run-type standalone --model "Claude Sonnet 4.6"
python src/shared/tools/pipeline_observer.py -p Meu-ERP track `
  --agent ava-qa-exploratory --phase F5 --version 2.0.0 `
  --model "Claude Sonnet 4.6" --status completed `
  --tokens-in 48000 --tokens-out 9000 --duration-ms 42000

Get-Content projects\Meu-ERP\outputs\observability\headroom-metrics.jsonl -Tail 1
```

**Esperado**: uma linha `"source": "self-report"` com `agent_id`, `phase`, tokens e
duração — para um agente F5 que **não** tem nenhuma instrução de headroom no `.md`.
`original_tokens` vem `null`: o agente não conhece o tamanho pré-compressão.

## 5 · Degradação sem a tool

```powershell
Rename-Item src\shared\tools\headroom\headroom_config.py headroom_config.py.bak
python src/shared/tools/pipeline_observer.py -p Meu-ERP track `
  --agent ava-qa-exploratory --phase F5 --version 2.0.0 --status completed --duration-ms 1000
Rename-Item src\shared\tools\headroom\headroom_config.py.bak headroom_config.py
```

**Esperado**: o `track` imprime o JSON normalmente e apenas **não** acrescenta a linha do
headroom. O hook é silencioso por design (IV3).

## 6 · Atribuição pelo proxy

```powershell
python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP attribute --dry-run
python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP attribute
python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP stats
```

**Esperado** (com um `.headroom/proxy-requests.jsonl` real):

- agente que rodou sozinho → `attribution: exclusive`, tokens integrais
- agentes em paralelo → metade cada, marcados `⚠️ N ambíguas (até Nx)`
- requisições fora de qualquer janela → linha `__unattributed__`
- **conservação**: atribuído + órfão == total do proxy
- `stats` separa `self-report` (volume estimado) de `proxy` (compressão medida)

Sem log do proxy, `attribute` sai com código 1 e explica o porquê — não inventa números.

## 7 · Ponta a ponta *(exige proxy no ar e a chave do Foundry)*

```powershell
.\src\shared\tools\headroom\run_standalone.ps1        # aba 1
.\copilot-cli-headroom.bat                            # aba 2 — rode uma fase (ex.: SA)
```

Ao final:

```powershell
src\shared\tools\headroom\.venv\Scripts\headroom.exe perf --hours 1
python src/shared/tools/headroom/headroom_tool.py -p <PROJETO> attribute
python src/shared/tools/headroom/headroom_tool.py -p <PROJETO> stats
```

**Esperado**: o total de `headroom perf` bate com `atribuído + __unattributed__`. Uma
fatia órfã grande sugere agentes que não chamaram `track`, ou `duration_ms`
subestimado — nesse caso a falha é para o lado seguro (órfão, não atribuição errada).

## 8 · Suíte completa

```powershell
python -m pytest tests/ -q
```

**Esperado**: `83 passed, 6 skipped`.

---

## Rollback

| Nível | Ação | Efeito |
|---|---|---|
| 1 | `headroom: {enabled: false}` no `project-config.yaml` | O hook para de gravar; `track` intacto |
| 2 | Remover a chamada a `_write_headroom_metric` em `cmd_track` | Volta ao comportamento de specs/031 |
| 3 | `AGENT_CATALOG = _STATIC_AGENT_CATALOG` nos dois consumidores | Volta aos catálogos literais (com o drift de volta) |

As correções de drift (Category 3) **não** devem ser revertidas: são defeitos reais,
independentes do Headroom.
