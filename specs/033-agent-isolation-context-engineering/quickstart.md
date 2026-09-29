# Quickstart — Verificação end-to-end (spec 033)

**Spec**: `specs/033-agent-isolation-context-engineering/spec.md`
**Plataforma**: Windows / PowerShell. Executar da **raiz do repo**.
**Pré-requisitos**: GitHub Copilot CLI ≥ 1.0.77 · `.copilot-key` presente na raiz · Python 3 no PATH.

> Ordem intencional: os passos 0–3 não gastam inferência. Só a partir do passo 4 há custo.

---

## 0. Preflight — formato dos wrappers

O M0 provou que `version:` e `allowed-tools:` são descartados em silêncio. Este passo é o que
impede um wrapper malformado de nascer com todas as tools liberadas.

```powershell
python src/shared/tools/generate_agent_wrappers.py --check
#  exit 0 = os 102 wrappers em disco == o que o agent_registry produziria
#  exit 1 = drift; rode sem --check para regenerar

python -m pytest tests/test_agent_wrappers.py tests/test_agent_body_size.py -q

(Get-ChildItem .github/agents -Filter 'ava-*.agent.md').Count      # esperado: 102
```

Zero `unknown fields ignored` — a prova de que o frontmatter está no schema do CLI:

```powershell
copilot --log-level warning -p '"reply with exactly: OK"' --no-ask-user `
        --allow-all-tools --no-custom-instructions 2>&1 |
  Select-String 'unknown fields ignored'          # sem saída = OK
```

## 0.1 A sessão carregou tudo? (custo zero de inferência)

Passar um nome de agente inválido faz o CLI listar o que carregou e sair:

```powershell
copilot --agent zz-probe -p '"x"' --allow-all-tools --no-ask-user --log-level error
#  -> No such agent: zz-probe, available: ava-asis-bridge-fastqa, ava-asis-db-analyzer, ...
```

Conferência automática contra o disco:

```powershell
copilot --agent zz-probe -p '"x"' --allow-all-tools --no-ask-user --log-level error 2>&1 |
  ForEach-Object { ($_ -replace '^No such agent: [^,]*, available: ','') -split ',\s*' } |
  Where-Object { $_ -like 'ava-*' } | Sort-Object > $env:TEMP\load.txt
Get-ChildItem .github/agents/ava-*.agent.md |
  ForEach-Object { $_.BaseName -replace '\.agent$','' } | Sort-Object > $env:TEMP\disk.txt
Compare-Object (Get-Content $env:TEMP\disk.txt) (Get-Content $env:TEMP\load.txt)   # sem saída = OK
```

Esperado: **102 `ava-*` + 10 `speckit.*` = 112**, e `Compare-Object` sem saída.

O `AGENTS.md` não aparece nessa lista porque não é agente — a prova de que carregou é o
`systemTokens` (~23.7K com ele, ~21.7K sem; `docs/copilot-cli-runtime-facts.md` § 10.1).

## 0.2 O ponto de entrada

`copilot-cli-headroom.bat` faz o preflight e abre a sessão já com tudo descoberto:

```powershell
.\copilot-cli-headroom.bat        # abre a sessão; escolha a fase com /agent
.\copilot-cli-headroom.bat F1     # abre já no ava-asis-orchestrator
.\copilot-cli-headroom.bat F5     # ava-qa-orchestrator
```

O `.bat` imprime, antes de abrir:

```
  agentes customizados=102 (em dia com o agent_registry)
  AGENTS.md=carregado automaticamente pela sessao
```

Se disser `DIVERGENTE`, **pare** — a fase rodaria com guardrails desatualizados; rode
`python src/shared/tools/generate_agent_wrappers.py` antes.

A fase é resolvida por `agent_registry.py --orchestrator F1`, nunca por um mapa dentro do
`.bat`. F3, F7 e F8 não têm orquestrador registrado: o `.bat` avisa e abre a sessão sem agente
inicial.

## 1. `AGENTS.md` — language-agnostic e herdado

```powershell
(Get-Item AGENTS.md).Length                        # esperado: <= 8192 bytes
Select-String -Path AGENTS.md -Pattern 'AGENTS-CORE:(START|END)'   # 2 ocorrências

# Gate duro — AGENTS.md não pode nomear nenhuma tecnologia
python src/shared/utils/validate_language_agnostic.py --strict --paths AGENTS.md   # exit 0

# Medição da dívida — os wrappers herdam a `description` da spec canônica, e
# 9 delas nomeiam tecnologia. É follow-on (spec.md § 7), não regressão desta spec.
python src/shared/utils/validate_language_agnostic.py --report --paths .github/agents
```

O teste `test_agent_wrappers.py` já afirma que o bloco `AGENTS-CORE` de cada um dos 102 wrappers é
**byte-idêntico** ao de `AGENTS.md`. Para confirmar a herança na prática: edite uma linha do bloco,
rode `generate_agent_wrappers.py`, e confira que a mudança apareceu nos 102.

## 2. O DAG não virou a quarta fonte divergente

```powershell
python -m pytest tests/test_pipeline_dag.py -q
#  Reprova se F1.yaml divergir de ARTIFACT_CONTRACTS, AGENT_ARTIFACT_SLICE
#  ou agent_registry.catalog() — a mitigação do risco R1.
```

## 3. Context pack — orçamento e determinismo

```powershell
python src/shared/tools/context_pack.py --project MeuERP-002 --phase F1 --json
#  Nenhum pack acima do orçamento. Pack degradado traz a decisão registrada
#  dentro do próprio arquivo — nunca truncamento silencioso.

python src/shared/tools/context_pack.py --project MeuERP-002 --agent ava-asis-inventory > a.md
python src/shared/tools/context_pack.py --project MeuERP-002 --agent ava-asis-inventory > b.md
Compare-Object (Get-Content a.md) (Get-Content b.md)     # sem saída = determinístico
Remove-Item a.md, b.md
```

## 4. Runner — dry-run antes do real

```powershell
# Imprime os comandos exatos sem gastar inferência. Revisar à mão na primeira vez.
python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --dry-run

# Execução real
python src/shared/tools/agent_runner.py --project MeuERP-002 --phase F1 --json
```

## 5. A prova central — isolamento de janela (CA01)

Cada nó tem que nascer numa janela limpa. Se este passo falhar, a spec não entregou o que promete.

```powershell
$runDir = Get-ChildItem projects/MeuERP-002/outputs/.runs |
          Sort-Object Name -Descending | Select-Object -First 1

# 5a. Zero compactação / truncamento em qualquer nó — a assinatura da ISSUE-002
Get-ChildItem "$env:USERPROFILE\.copilot\session-state" -Recurse -Filter events.jsonl |
  Get-Content | Select-String 'compaction_start|truncation'     # vazio = OK

# 5b. Overhead estático e pico de contexto por nó
Get-ChildItem "$env:USERPROFILE\.copilot\session-state" -Recurse -Filter events.jsonl |
  ForEach-Object { Get-Content $_ | ConvertFrom-Json } |
  Where-Object type -eq 'session.shutdown' |
  Select-Object -ExpandProperty data |
  Select-Object systemTokens, toolDefinitionsTokens, currentTokens
#  esperado por nó: systemTokens ~ 6.042 · toolDefinitions ~ 7.329
#                   (estático ~ 13.449) · currentTokens muito abaixo de 128.000
```

## 6. Enforcement — o hook nega, não desencoraja (CA07)

```powershell
copilot -p '"view projects/MeuERP-002/outputs/asis/ast-raw/delphi/compressed/04_database_schemas.json"' `
        --agent ava-asis-inventory --no-ask-user --allow-all-tools `
        --no-custom-instructions --session-id ([guid]::NewGuid())
#  A leitura deve ser NEGADA, com permissionDecisionReason apontando para
#  headroom_tool.py slice. Confirmar hook.start / hook.end no events.jsonl da sessão.
```

## 7. Gate e paridade de artefatos

```powershell
python src/modules/ava-fabric-agents/asis-diagnostic/utils/artifact_gate.py `
       --project MeuERP-002 --json
#  F1_OUTPUT_CONTRACT: 12/12 paths obrigatórios · 19/19 artefatos (era 11/19)

# Comparar a estrutura com a referência de um F1 completo
Get-ChildItem 'C:\Desenv\factory_apps\ava-fabric-apps-agents\projects\Meu-ERP\outputs\asis' -Name
Get-ChildItem 'projects/MeuERP-002/outputs/asis' -Name
```

## 8. O modo de execução do usuário não mudou (CA02) — restrição inviolável

```powershell
git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat   # sem saída = OK

.\copilot-cli-headroom.bat
#  O operador abre o CLI igual e chama o orquestrador da F1 igual.
#  A única diferença observável: o orquestrador emite UMA chamada ao runner
#  em vez de N dispatches in-prompt.
```

## 9. Caminho nativo (híbrido) continua funcionando (CA03)

```powershell
copilot
#  /agent  -> escolher qualquer um dos 102 -> roda em janela própria
#  ou:  "use the ava-asis-inventory agent on MeuERP-002"
```

## 10. Regressão e CI

```powershell
python -m pytest tests/ -q
python src/shared/utils/verify_agent_observability.py
#  Cobertura de agentes idêntica antes/depois. Agente migrado pode omitir o
#  bloco `track` — o runner registra por ele, com números reais.
```

---

## Rollback

```powershell
# 1. Voltar ao caminho in-prompt, bit a bit:
#    projects/{p}/context/project-config.yaml  ->  execution_backend: inprompt
#    (o runner recusa rodar; o orquestrador segue o caminho atual)

# 2. Ou simplesmente parar de invocar o runner no orchestrator-asis.md.
```

Nada em M1–M3 altera arquivo existente: `AGENTS.md`, os wrappers, `context_pack.py`, os hooks e os
testes são todos **novos**. O caminho interativo é preservado por construção.

---

## Solução de problemas

| Sintoma | Causa provável | Ação |
|---|---|---|
| `session.error` 404 *"Model not found on provider"* | BYOK não propagado ou apontando para o proxy | O runner classifica como `config_error` e **aborta a fase** — não é para retentar. Conferir o bloco BYOK e usar a rota **direta** (M0 § 1.8) |
| Nó "passou" com `exit 0` mas sem artefato | prompt, não transporte | É classificado `failed` por design. O gate é a autoridade; retentar sem mudar o prompt é retry-storm |
| `unknown fields ignored: version, allowed-tools` | wrapper escrito à mão ou gerador desatualizado | `generate_agent_wrappers.py` (sem `--check`) para regenerar |
| Agente reclama que não tem a tool `view` | `tools:` do wrapper incompleto | `tools:` é enforçado de verdade (M0 § 1.5); conferir o `TOOL_NAME_MAP` |
| `context_overflow` sinalizado mesmo com o nó completo | pack grande demais para aquele agente | É o sinal para apertar o pack daquele nó — a assinatura exata da ISSUE-002 |
| Processo `node` órfão após timeout | `Popen.terminate()` no Windows | O runner usa `taskkill /PID <pid> /T /F`; conferir que a árvore inteira morreu |
| `[ERROR] Copilot Task API failed … 404` no log | ruído conhecido | Benigno, ocorre mesmo com `--no-remote`. Filtrado por `BENIGN_LOG_PATTERNS` |
