# Copilot CLI — fatos de runtime medidos (M0)

> Spike de medição do milestone **M0** do plano de escala da esteira.
> Tudo aqui foi **medido nesta máquina**, não estimado. Nenhum arquivo do repo foi alterado
> (a sonda `.github/agents/zz-m0-probe.agent.md` foi criada e removida).
>
> | | |
> |---|---|
> | Data | 2026-08-02 |
> | Versão | `GitHub Copilot CLI 1.0.77` |
> | Provider | BYOK Anthropic → Azure AI Foundry (`.../anthropic`), wire model `claude-sonnet-4-6` |
> | Rota | **direta** (proxy Headroom fora do ar — venv ausente). Ver § Proxy. |
> | Fonte primária | `~/.copilot/session-state/<sessionId>/events.jsonl` |

---

## 1. Janela de contexto — **128.000**, não 200.000

`grep '"tokenLimit"' ~/.copilot/session-state/*/events.jsonl` → **75 ocorrências, todas `128000`**.
Emitido em `session.compaction_start` e `session.truncation`.

**Impacto direto:** os limiares de
[context_budget.py](../src/modules/ava-fabric-agents/asis-diagnostic/utils/context_budget.py)
(`inline > 400.000`, `bc_scoped > 700.000`) e a documentação do Headroom
(`docs/02-esteira-github-cli.md`: *"janela 200.000 tokens"*) foram calibrados contra uma janela que
não existe. Ver § 3 para o orçamento real.

### `--context long_context` — **NÃO verificado**

A flag é aceita e `session.start` passa a registrar `"contextTier":"long_context"` (baseline registra
`null`). Mas **nenhuma sessão long_context chegou a compactar**, então nenhum `tokenLimit` foi emitido
para esse tier. **O limite do `long_context` continua desconhecido.** Não assumir que é maior sem medir.

---

## 2. Overhead estático por processo — e como reduzi-lo em 55%

5 sondas idênticas (`-p "reply with exactly: OK"`, `-C <repo root>`, `--model claude-sonnet-4`),
variando só as flags. Números de `session.shutdown`:

| Sonda | Flags adicionais | `systemTokens` | `toolDefinitionsTokens` | **Total estático** | Δ vs baseline |
|---|---|---:|---:|---:|---:|
| **P1** | — (baseline) | 21.719 | 8.074 | **29.871** | — |
| **P2** | `--no-custom-instructions` | 10.347 | 8.074 | **18.499** | **−11.372** |
| **P3** | `--disable-builtin-mcps` | 21.517 | 7.657 | **29.252** | −619 |
| **P4** | P2 + P3 + `--excluded-tools=skill` | 6.042 | 7.329 | **13.449** | **−16.422 (−55%)** |
| **P5** | `--context long_context` | 21.727 | 8.074 | 29.879 | +8 (ruído) |

P1 rodou duas vezes: 29.871 e 29.873 → **repetibilidade ±2 tokens**.

### Leitura

- **`--no-custom-instructions` é a maior alavanca isolada: −11.372 tokens.** É *mais* do que
  `.github/copilot-instructions.md` sozinho (28,9 KB ≈ 7,2K tokens), logo o flag também remove outras
  fontes de custom instructions. Não foi isolado quais.
- **`--disable-builtin-mcps` rende pouco: −619.** O `github-mcp-server` responde por só 417 dos 8.074
  tokens de definição de tool. Vale ligar, mas não é onde está o ganho.
- **`--excluded-tools=skill` rende ~−4.400** (derivado: P4 vs P2+P3). As 75 skills de `.github/skills/`
  entram no prompt de sistema. No modelo de runner o agente recebe a spec por `Read`, então não precisa
  da tool `skill` — é ganho limpo.
- **Piso prático: 13.449 tokens (10,5% da janela).** Baseline hoje: 29.871 (23,3%).

---

## 3. Orçamento real por processo

```
128.000  janela
−13.449  estático com as flags do runner (P4)
−  ~8000  reserva de saída
─────────
 ~106.000 tokens úteis para context pack + spec + trabalho
```

Contra o baseline atual (29.871 estáticos) sobrariam ~90.000. **As flags do runner recuperam ~16K
tokens por processo** — em F1 com ~19 agentes, ~312K tokens de overhead evitado por execução.

O CLI já avisou explicitamente em 2 sessões reais:
`session.warning` → `"warningType":"compaction_static_context_budget"` →
*"Static context is using 76% of available input tokens... system messages and tool definitions cannot
be reclaimed."*

---

## 4. `.github/agents/*.agent.md` — formato

### `tools:` é **enforçado** (verificado)

Sonda com `tools: ["glob"]`, instruída a usar `view`. Resposta do modelo:

> *"I found `README.md` via glob, but I don't have a `view` tool available in this environment."*
> **TOOL_UNAVAILABLE**

Nenhum `tool.execution_start` de `view` no `events.jsonl`. **A restrição é real, não sugestão.**

### `version:` e `allowed-tools:` são **descartados** (verificado)

Com `--log-level warning`:

```
[WARNING] .github\agents\zz-m0-probe.agent.md: unknown fields ignored: version, allowed-tools
```

O frontmatter atual dos 107 agentes usa exatamente essas duas chaves. **O gerador de wrappers tem que
emitir `tools:`**, senão o agente nasce com todas as tools liberadas e sem versão.

Campos aceitos: `description` (obrigatório), `name`, `tools`, `model`, `target`,
`disable-model-invocation`, `user-invocable`, `mcp-servers`, `metadata`.

### `~/.copilot/agents/` não existe nesta máquina

O risco R7 (shadowing do diretório de usuário sobre `.github/agents/`) é **nulo hoje**. O preflight do
runner deve mesmo assim falhar em colisão — o diretório pode ser criado a qualquer momento.

---

## 5. Nomes reais das tools

De `"toolName"` em todas as sessões:

| Tool | Invocações | Tool | Invocações |
|---|---:|---|---:|
| `task` | 1.251 | `skill` | 35 |
| `powershell` | 918 | `read_powershell` | 24 |
| `view` | 674 | `sql` | 11 |
| `grep` | 577 | `task_complete` | 8 |
| `glob` | 455 | `read_agent` | 8 |
| `create` | 148 | `ask_user` | 7 |
| `edit` | 124 | `web_fetch`, `web_search`, `write_agent`, `stop_powershell`, `local_shell` | 1–2 |

Dois pontos que afetam as specs:

1. **A tool de shell chama-se `powershell`, não `bash`.** Os agentes escrevem `Bash:` nos Execution
   Steps (`batch-write-protocol.md` inclusive). Funciona hoje porque o modelo mapeia a intenção, mas
   qualquer `tools:` gerado precisa listar `powershell`.
2. **`task` é a tool mais usada (1.251).** É o dispatch in-prompt de sub-agente que o runner substitui.

---

## 6. Detecção de conclusão

### Exit code
`0` em todas as 6 sondas bem-sucedidas. `1` em erro de argumento
(*"Invalid command format"* — o prompt precisa vir entre aspas).

### stdout com `--output-format json`
O último evento é um registro terminal utilizável:

```json
{"type":"result","sessionId":"e008ec66-…","exitCode":0,
 "usage":{"premiumRequests":0,"totalApiDurationMs":5639,"sessionDurationMs":14643,
          "codeChanges":{"linesAdded":0,"linesRemoved":0,"filesModified":[]}}}
```

### `events.jsonl` (mais rico — usar como fonte de verdade)
`session.start` (`contextTier`, `model`) · `session.shutdown` (`systemTokens`,
`toolDefinitionsTokens`, `currentTokens`, `modelMetrics.*.usage`, `totalApiDurationMs`) ·
`session.compaction_start` / `session.truncation` (**sinal de `context_overflow`**) ·
`session.warning` · `session.error` · `tool.execution_complete` (`success`, `error`).

Taxonomia de erro observada: `errorType` ∈ {`query` (87), `authentication` (2), `quota` (1)};
`statusCode` ∈ {404 (87), 401 (1), 402 (1)}.

---

## 7. Proxy Headroom — bloqueador para o runner

**87 erros 404 em 25 sessões distintas**, todos "Model not found":

| Endpoint | Ocorrências |
|---|---:|
| `http://127.0.0.1:8787` (**proxy Headroom**) | **71** |
| `https://…services.ai.azure.com/anthropic` (direto) | 6 |
| `…openai.azure.com/openai/deployments/claude-sonnet-4-6` | 5 |
| outras variantes de URL | 5 |

**As 6 sondas deste M0 foram direto ao Foundry e todas retornaram `exit 0` com
`model: claude-sonnet-4-6`.** Ou seja: o caminho direto funciona; o caminho pelo proxy é a origem
dominante dos 404.

Isso confirma o diagnóstico do próprio repo em
[docs/02-esteira-github-cli.md § Anexo A](../src/shared/tools/headroom/docs/02-esteira-github-cli.md):
o Copilot valida o wire model via `GET /v1/models/{modelo}`, rota que o headroom encaminha em vez de
responder localmente, e a superfície Anthropic do Foundry devolve 404.

**Consequência para o plano:** o runner roda **hoje** apenas na rota direta. Para rodar comprimido é
preciso antes o shim local de `/v1/models/{id}` no proxy (contorno 3 do Anexo A, ainda não
implementado). O runner deve registrar `compression=on|off` por nó e **não** degradar em silêncio.

---

## 8. Ruído sem impacto funcional

Presente em todas as execuções, sem afetar `exit 0`:

- `[ERROR] Request to Copilot Task API failed … /agents/tasks/<sid> … 404` — ocorre **mesmo com**
  `--no-remote --no-remote-export`.
- `[ERROR] GitHub MCP server configured after authentication`.
- `[WARNING] could not load remote agents, no GitHub remote found`.

Filtrar essas três no parser de log do runner para não gerar falso positivo de falha.

---

## 9. Ajustes que estes números impõem ao plano

| Item do plano | Ajuste |
|---|---|
| Limiares de `context_budget.py` (400K/700K) | Recalibrar para **~106K úteis por processo** (§3). Manter os valores atuais só como heurística de total de pipeline. |
| `--disable-builtin-mcps` como ganho relevante | Rende só −619. Manter (é grátis), mas o ganho está em `--no-custom-instructions` (−11.372) e `--excluded-tools=skill` (−4.400). |
| `--excluded-tools=skill` | **Promover a flag padrão do runner** — não era certo no plano, agora é: −4.400 tokens e o agente não precisa de skill. |
| Gerador de wrappers | Emitir `tools:` (não `allowed-tools:`) e não emitir `version:`. Mapear `Bash` → `powershell`. |
| `--context long_context` para os `solution-*` | **Não usar até medir.** O tier é aceito mas o limite é desconhecido. |
| Rota do runner | Direta por ora. Proxy só depois do shim `/v1/models/{id}` (§7). |
| Risco R7 (colisão `~/.copilot/agents/`) | Diretório não existe hoje; manter o preflight mesmo assim. |

---

## Como reproduzir

O script da sonda está em `m0-probe.ps1` (scratchpad da sessão). Essência:

```powershell
$sid = [guid]::NewGuid().ToString()
copilot -p '"reply with exactly: OK"' --allow-all-tools --no-ask-user `
        --model claude-sonnet-4 --output-format json -C <REPO_ROOT> `
        --session-id $sid --log-level error
Get-Content "$env:USERPROFILE\.copilot\session-state\$sid\events.jsonl" |
  ConvertFrom-Json | Where-Object type -eq 'session.shutdown' |
  Select-Object -ExpandProperty data |
  Select-Object systemTokens, toolDefinitionsTokens, currentTokens
```

> `Start-Process -ArgumentList` **não re-quota** os argumentos: o prompt precisa carregar aspas
> embutidas, senão o CLI responde *"Invalid command format"* e sai com 1.

---

## 10. Re-medição de 2026-08-03 — o efeito dos 102 agentes customizados

> As medições do M0 (§§ 1–9) foram feitas quando havia **1** agente em
> `.github/agents/`. Depois que a spec 033 gerou os **102 wrappers** e criou o
> `AGENTS.md`, o estático mudou o suficiente para invalidar o orçamento anterior.
> Mesmo método: `session.shutdown` do `events.jsonl`, `-C <repo root>`,
> `--model claude-sonnet-4`. Nenhum servidor MCP configurado (`copilot mcp list` → vazio).

| Sonda | `systemTokens` | `toolDefinitionsTokens` | **Total estático** |
|---|---:|---:|---:|
| M0 baseline (1 agente, sem `AGENTS.md`) | 21.719 | 8.074 | 29.793 |
| **`.bat` interativo hoje** (102 agentes + `AGENTS.md`) | 23.709 | 18.920 | **42.629** |
| + `--excluded-tools=task` | 22.820 | 6.526 | 29.346 |
| Flags do runner do M0 (`skill` só) | 6.042 | 18.175 | 24.217 |
| **Flags do runner + `--excluded-tools=skill,task`** | 5.157 | 5.781 | **10.938** |

### 10.1 O `AGENTS.md` **é** carregado automaticamente — confirmado

`systemTokens` foi de 21.719 (M0, sem o arquivo) para 23.709: **+1.990 tokens**, coerente
com os 8,1 KB do `AGENTS.md`. Não é preciso passar flag nenhuma; basta o CLI enxergar a raiz
do repo — daí o `-C "%~dp0."` no `.bat`.

Corolário já conhecido, agora quantificado: `--no-custom-instructions` **desliga** esse
carregamento (`systemTokens` cai para 5.157–6.042). É por isso que o bloco `AGENTS-CORE` é
injetado no corpo de cada wrapper — no caminho do runner, é a única entrega da regra.

### 10.2 Os 102 agentes custam ~12,4K tokens em `toolDefinitions`

`toolDefinitionsTokens` subiu de 8.074 para 18.920 (**+10.846**), e
`--excluded-tools=task` derruba para 6.526 (**−12.394**). Ou seja: **o catálogo dos agentes
customizados viaja dentro da definição da tool `task`** (o dispatch nativo de sub-agente),
a ~120 tokens por agente — compatível com as `description` de 260–470 chars que o gerador emite.

**Consequência para o runner:** sem excluir `task`, o estático por processo seria 24.217 em vez
dos 13.449 do M0 — os 102 wrappers teriam **anulado** a economia das flags. Com
`--excluded-tools=skill,task` o estático cai para **10.938**, melhor que o número original.
Um nó folha do DAG não delega para ninguém, então a tool é peso morto num processo isolado.

Orçamento por processo isolado, revisado:

```
128.000  janela
−10.938  estático (flags do runner + skill,task excluídas)
− ~8.000  reserva de saída
─────────
~109.062 úteis            (era ~106.551 com o número obsoleto do M0)
```

### 10.3 A sessão interativa paga 42.629 — 33% da janela

É o preço de ter os 102 agentes invocáveis **nativamente** (que é o que permite o orquestrador
delegar em janela própria) somado ao `.github/copilot-instructions.md` (28,9 KB ≈ 7,2K tokens)
e ao `AGENTS.md`. Aceitável para a janela do orquestrador, que não faz leitura pesada.

Maior alavanca disponível, **não aplicada**: `.github/copilot-instructions.md` tem uma seção
`## Available Skills (44 agents)` desatualizada em 63 entradas e hoje redundante com os wrappers.
Enxugá-la é a redução mais barata do caminho interativo — fica registrado como follow-on.

### 10.4 Como reproduzir

```powershell
$sid = [guid]::NewGuid().ToString()
copilot -p '"ok"' --allow-all-tools --no-ask-user --model claude-sonnet-4 `
        -C <REPO_ROOT> --session-id $sid --log-level error <FLAGS>
Get-Content "$env:USERPROFILE\.copilot\session-state\$sid\events.jsonl" |
  ConvertFrom-Json | Where-Object type -eq 'session.shutdown' |
  Select-Object -ExpandProperty data |
  Select-Object systemTokens, toolDefinitionsTokens
```

> O `session.shutdown` reporta o estático **mesmo quando a chamada de API falha** — as sondas
> desta seção rodaram com o endpoint em timeout e ainda assim produziram números válidos.
> Útil: dá para medir estático sem gastar inferência.

---

## 11. Subagentes que não produzem nada (2026-08-03)

> Levantamento de **70 sessões** em `~/.copilot/session-state/*/events.jsonl`, 1.033
> `subagent.started`. Reproduzível a qualquer momento com
> `python src/shared/tools/check_session_health.py --all`.

| `agentName` | modelo atribuído | dispatches | com `totalToolCalls: 0` |
|---|---|---:|---|
| `task` | `claude-sonnet-4` | 950 | 10 (**1%**) |
| **`general-purpose`** | **`gpt-5.4`** | **54** | **53 (98%)** |
| **`explore`** | **`gpt-5.4-mini`** | **24** | **19 (79%)** |
| `task` | `claude-opus-4-5` | 3 | — |

**78 dispatches desperdiçados em 18 sessões; 77 terminam em erro.** Ativo até
2026-08-03 (sessões `ace165e4` 15:01 e `ef5de569` 17:16).

### 11.1 A sequência

```
subagent.started    agentName=general-purpose  model=gpt-5.4
session.error  404  "Model 'claude-sonnet-4-6' not found on provider at http://127.0.0.1:8787"
subagent.completed  agentName=general-purpose  totalToolCalls=0
```

Com BYOK, **todo** tráfego vai para o provider configurado. Os tipos embutidos do CLI trazem modelo
próprio — a descrição da tool `task` no prompt de sistema declara: `explore` *"fast, lightweight
model"*, `general-purpose` *"high-capability model"*. Quando o CLI troca o modelo do subagente, a
troca dispara uma validação do **wire model** (`claude-sonnet-4-6`) contra o provider, que responde
404. O subagente morre antes da primeira tool call e o orquestrador segue como se tivesse recebido
resultado.

`task` é a exceção: resolve para o modelo do pai e funciona em 99% dos casos — **na mesma sessão** em
que `general-purpose` falha.

### 11.2 Falha nas duas rotas

| Rota | dispatches falhos |
|---|---:|
| Proxy Headroom `127.0.0.1:8787` | 72 |
| Direto Foundry | 5 |
| Sem erro | 1 |

`copilot-cli-v1.bat` (rota direta) **não** é workaround — só falha menos.

### 11.3 O que corrige

| Camada | Estado |
|---|---|
| `agent_runner.py` | **já imune**: `--model` pinado, `Popen`+`communicate` síncrono, e `--excluded-tools=skill,task` remove fisicamente a tool de subagente do processo filho |
| `AGENTS.md` § 5 (D1/D2) | proíbe delegar a `general-purpose`/`explore`; injetado nos 102 wrappers → alcança F1–F8 (a `FILE_PERSISTENCE_RULE` só existia sob `asis-diagnostic/`) |
| `agent_runner._classify()` | subagente fora do modelo pinado **ou** com 0 tool calls → `config_error` (aborta a fase, não retenta) |
| `check_session_health.py` | detector para o caminho **interativo**, onde não há runner |
| `subagents.agents.<nome>.model = "inherit"` | correção de raiz do CLI — **caminho do settings não confirmado**, ver § 11.4 |

### 11.4 Onde ficam as settings — não confirmado

`copilot help config` documenta `subagents.agents.<agent-name>` com `model`/`effortLevel`/
`contextTier`, cada um aceitando `"inherit"`. O **caminho do arquivo**, porém, não foi determinado:

- `~/.copilot/config.json` diz *"User settings belong in settings.json. This file is managed automatically."*
- `copilot help config` cita *"in repo settings.json"* sem dar o path.
- `~/.copilot/settings.json` e `.copilot/` no repo **não existiam**.
- Criar `~/.copilot/settings.json` (válido **e** inválido) não produziu nenhuma reação observável:
  o grupo de log `--- Start of group: configured settings: ---` sai **vazio**, e só as settings de
  MDM (`C:\Program Files\GitHubCopilot\managed-settings.json`, `HKLM\SOFTWARE\Policies\GitHubCopilot`)
  aparecem no `--log-level debug`.
- O binário é empacotado; `strings` não revela o caminho.

**Como resolver:** rodar `/subagents` uma vez numa sessão interativa e configurar `inherit` pela UI —
o CLI grava onde quiser, e aí basta ler o arquivo de volta para aprender o path e versioná-lo.
Até lá, a correção de raiz é config de máquina e a detecção (§ 11.3) é a garantia.

### 11.5 Comandos úteis descobertos

| Comando | Para quê |
|---|---|
| `/instructions` | **Prova direta** de que o `AGENTS.md` foi carregado — lista os arquivos de custom instruction ativos |
| `/subagents` | Configura modelo/esforço/tier por subagente |
| `/fleet` | Liga execução paralela de subagentes |
| `/tasks` | Vê e gerencia tasks (subagentes e comandos de shell) |
| `/context` · `/usage` | Janela de contexto e métricas da sessão |
| `copilot --agent <inválido>` | Lista **todos** os agentes carregados e sai — custo zero de inferência |

---

## 12. Confiabilidade de ferramenta e peso das custom instructions (2026-08-04)

> Origem: 3 recomendações de uma sessão de diagnóstico. Apuradas contra 4.369
> `tool.execution_complete` de 56 sessões e contra sondas de `systemTokens`.
> Reproduzir: `python src/shared/tools/check_session_health.py --all` e § 12.4.

### 12.1 Taxa de falha por ferramenta — `glob` é a mais confiável, não a menos

Junção `tool.execution_start` → `tool.execution_complete` por `toolCallId` (o
`toolName` só existe no evento de início):

| Tool | execuções | falhas | taxa |
|---|---:|---:|---:|
| `task` | 1.380 | **345** | **25%** |
| `powershell` | 1.191 | 22 | 1% |
| `view` | 839 | 36 | 4% |
| `grep` | 745 | 3 | **0%** |
| **`glob`** | **545** | **4** | **0%** |
| `create` | 147 | 7 | 4% |
| `edit` | 132 | 29 | 21% |
| `read_powershell` | 24 | 16 | 66% |

**A recomendação "glob é não-confiável no Windows, use `Get-ChildItem`" é falsa e seria
prejudicial.** As 4 falhas de `glob` são todas `rg: <path>` de branches antigas que não existem
mais — path inexistente, não instabilidade. `powershell` falha **mais** (1%) e tem um modo de falha
que `glob` não tem: **colisão de `shellId`** (9 ocorrências de *"Shell ID 'X' is already in use"* /
*"already running, wait for output with read_powershell"*) e 4 de *"unknown attachedShellSession
handle"*. Trocar `glob` por `Get-ChildItem` migraria de 0% para 1% e adicionaria concorrência de shell.

Registrado como `AGENTS.md` § C8.

### 12.2 O que realmente falha: `task` a 25%, e 84% disso é profundidade

Das 345 falhas de `task`:

| Mensagem | Ocorrências |
|---|---:|
| **`Maximum sub-agent depth of 4 reached`** | **289 (84%)** |
| `Agent completed but produced no response` | 44 |
| `No response generated` | 9 |
| `Multiple validation errors: description/prompt/agent_type Required` | 3 |

O limite de profundidade 4 é guardrail fixo do CLI. As 289 falhas são `task` chamando `task` —
agente delegado que delega de novo. É a maior fonte de falha de ferramenta da esteira inteira e não
estava coberta por nenhuma regra. Registrado como `AGENTS.md` § D3 (e § D4: escrita simples não se
delega, porque delegar consome um nível de profundidade sem ganho).

### 12.3 `File too large to read at once` — 271 ocorrências

Não é falha (o `success` vem `true`), mas o conteúdo retornado é só o aviso:

| Tool | ocorrências |
|---|---:|
| `powershell` | 111 |
| `task` | 76 |
| `view` | 56 |
| `grep` | 25 |

Junto com as 27 de `view_range out of bounds`, é a assinatura de ingestão exaustiva — o que
`AGENTS.md` § C2–C4 e o context pack existem para evitar.

### 12.4 As custom instructions do FastQA custavam 6.815 tokens por sessão

`.github/instructions/00-fastqa-index.instructions.md` (24,2 KB) declarava `applyTo: '**'`, então
entrava no prompt de sistema de **toda** sessão — inclusive runs de F1 que nunca tocam QA.

Sondas controladas (mesma máquina, mesmo dia, arquivo restaurado por `git checkout` ao fim):

| Configuração | `systemTokens` |
|---|---:|
| `applyTo: '**'` (como estava) | 23.674 |
| arquivo removido | 16.671 |
| **`applyTo: 'fastqa/**'` (aplicado)** | **16.780** |

**O CLI honra `applyTo`**: escopar rende praticamente o mesmo que remover — **−6.815 tokens**, 5,3%
da janela de 128K.

O roteamento `@fastqa` foi preservado por uma linha em `.github/copilot-instructions.md` (sempre
carregado), que aponta para o índice: ~30 tokens no lugar de 6.815.

**Resultado líquido medido depois de todas as mudanças deste dia** (já incluindo o `AGENTS.md`
crescer com § D3/D4/D5 e § C8):

```
systemTokens   23.674 → 16.989   (−6.685)
estático total 42.594 → 35.909   (−6.685, 28% da janela em vez de 33%)
```

### 12.5 As tools BMAD não estão nas specs dos agentes

O diagnóstico atribuía `memory`, `sequential-thinking` e `browser` ao frontmatter dos agentes.
**Não procede**: `grep` em `src/modules/ava-fabric-agents/**/*.md` não encontra nenhuma. Elas existem
apenas nos **8 arquivos FastQA** de `.github/instructions/`, escritos para VS Code com MCP. Ou seja,
o "problema das tools inexistentes" e o "peso das custom instructions" são **o mesmo defeito**, e o
escopo do § 12.4 resolve os dois. A regra § D5 do `AGENTS.md` fica como prevenção de drift.
