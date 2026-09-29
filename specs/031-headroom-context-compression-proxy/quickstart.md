# Quickstart — Headroom Context Compression

Verificação manual, do mais barato ao mais caro. Passos **1, 2, 4, 5, 8** rodam
sem rede e sem o venv da tool. Passos **3, 6, 7** exigem download de dependências
e a chave do Foundry.

Rode tudo da raiz do repositório.

---

## 1 · Isolamento — a esteira roda sem a tool *(IV3)*

```powershell
python src/modules/ava-fabric-agents/asis-diagnostic/utils/context_budget.py --project Meu-ERP --json
python -m pytest tests/utils/ -q
```

**Esperado**: `context_budget.py` funciona normalmente (exit 3 se não houver
`manifest.json` — é a degradação prevista); `28 passed`.
Nenhum dos dois pode falhar por causa do Headroom.

## 2 · Fonte única — nenhuma duplicação

```powershell
# IV2 — só o decodificador da tool conhece o formato (vendor é código de terceiros)
Get-ChildItem -Recurse -Include *.py src | Where-Object { $_.FullName -notmatch 'headroom\\vendor' } |
  Select-String -Pattern '__headroom__' | Select-Object Path, LineNumber

# IV1 — o segundo mapa de fatias não existe
Get-ChildItem -Recurse -Include *.py src | Select-String -Pattern 'AGENT_ARTIFACT_MAP'
```

**Esperado**: a primeira busca casa **apenas** em
`src/shared/tools/headroom/headroom_context.py`; a segunda não retorna nada.

## 3 · Instalação *(exige rede)*

```powershell
.\src\shared\tools\headroom\setup.ps1          # completo (torch ≈ 3 GB)
.\src\shared\tools\headroom\setup.ps1 -SkipML  # sem Kompress ML, muito mais rápido
```

**Esperado**: venv em `src/shared/tools/headroom/.venv`, `import headroom` OK e a
versão da CLI impressa. Sem `cargo` no PATH o script avisa que está usando o wheel
PyPI 0.33.0 em vez de buildar o fork — é o comportamento previsto.

## 4 · Diagnóstico

```powershell
python src/shared/tools/headroom/headroom_tool.py doctor
python src/shared/tools/headroom/headroom_config.py -p Meu-ERP
```

**Esperado**: `doctor` lista fork, venv, CLI, motor, fatias (19 agentes), proxy e
upstream. Exit `0` tudo verde · `1` degradado · `2` fork ausente.
`headroom_config.py` imprime a config efetiva já resolvida.

## 5 · Fatia por agente — sem custo de LLM

```powershell
python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP slice --agent ava-asis-db-analyzer
python src/modules/ava-fabric-agents/asis-diagnostic/utils/context_budget.py --project Meu-ERP --agent ava-asis-db-analyzer --json
```

**Esperado**: as duas saídas listam os **mesmos** artefatos
(`03_database_rules`, `04_database_schemas`, `05_procedures`) — porque leem o
mesmo dict. Num projeto com AST real (ex.: `processaERP-008`) os tokens devem
bater com a spec 030: `db-analyzer` = 559.144 tokens, 73,4% do payload.

## 6 · Proxy standalone *(I1 — exige rede)*

```powershell
.\src\shared\tools\headroom\run_standalone.ps1
```

Noutra aba:

```powershell
python src/shared/tools/headroom/headroom_tool.py proxy status
src\shared\tools\headroom\.venv\Scripts\headroom.exe doctor
src\shared\tools\headroom\.venv\Scripts\headroom.exe perf
```

**Esperado**: o proxy sobe **sem nenhum projeto ou agente**; `proxy status`
retorna `🟢 no ar` e exit 0.

## 7 · Interceptação end-to-end *(I3 — exige `.copilot-key`)*

Com o proxy do passo 6 no ar:

```powershell
.\copilot-cli-headroom.bat
```

**Esperado**: o cabeçalho mostra `COPILOT_PROVIDER_BASE_URL=http://127.0.0.1:8787`
e `headroom compression=yes`. Faça uma pergunta qualquer e confira:

```powershell
src\shared\tools\headroom\.venv\Scripts\headroom.exe perf
Get-Content .headroom\proxy-requests.jsonl -Tail 3
```

**Teste de degradação (I5)** — derrube o proxy (Ctrl+C na aba do passo 6) e rode
o `.bat` de novo:

**Esperado**: `WARNING: Headroom proxy não respondeu`, `headroom compression=no`,
e **a sessão inicia mesmo assim**, contra o endpoint direto.

## 8 · Métricas por agente

```powershell
python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP metrics `
  --agent ava-asis-inventory --phase F1 `
  --original 12400 --compressed 1860 --latency-ms 320 --proxy-used

python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP stats
Get-Content projects\Meu-ERP\outputs\observability\headroom-metrics.jsonl -Tail 1
```

**Esperado**: `-85.0%`, uma linha JSONL válida com timestamp BRZ (`-03:00`), e o
`stats` agregando por `agent_id`. O relatório existente continua funcionando:

```powershell
python src/shared/tools/pipeline_observer.py -p Meu-ERP dashboard
```

## 9 · MCP no VSCode

Recarregue a janela e rode **MCP: List Servers**.

**Esperado**: `ava-headroom` e `ava-headroom-cli` listados. As ferramentas
`headroom_slice`, `headroom_retrieve`, `headroom_decode`, `headroom_compress` e
`headroom_stats` respondem.

## 10 · Manutenção do fork

Num branch descartável:

```powershell
git subtree pull --prefix src/shared/tools/headroom/vendor `
  https://github.com/headroomlabs-ai/headroom.git main --squash

.\src\shared\tools\headroom\setup.ps1 -Force -SkipML
python -m pytest tests/tools/ -q
```

**Esperado**: `22 passed`.

> ⚠️ **Obrigatório após todo `git subtree pull`**: revalidar o roundtrip do
> formato tabular. O encoding `[N]{k:t}\n<csv>` **não é documentado
> publicamente** — se o upstream mudar, os testes de unidade continuam passando
> (usam fixtures) mas a leitura de artefatos reais quebra silenciosamente.
> Use a sonda de `research.md` §3: comprima um artefato com `compress()`, passe
> por `decode_headroom()` e compare com o original.

---

## Rollback — 3 níveis independentes

| Nível | Ação | Efeito |
|---|---|---|
| 1 | `headroom: {enabled: false}` no `project-config.yaml` | Desliga a tool naquele projeto |
| 2 | Usar `copilot-cli-v1.bat` (intacto) | Volta ao endpoint direto, sem proxy |
| 3 | `git rm -r src/shared/tools/headroom` | Remove a tool. `context_budget.py` não é afetado; os dois consumidores caem no `decode_headroom` no-op |
