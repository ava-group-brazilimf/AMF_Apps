# Guia de Execução — `ava-pipeline-runner-cli.py`

> **Escopo**: documentação completa para executar o script `ava-pipeline-runner-cli.py`, cobrindo
> seus parâmetros, configurações, fluxos de execução, dependências e capacidades.
>
> **Público-alvo**: desenvolvedores, arquitetos e operadores que precisam rodar a esteira AVA Fabric
> — desde a extração AST até o summary executivo.
>
> **Fontes**: `ava-pipeline-runner-cli.py`, `docs/guia-comandos-pipeline-runner.md`,
> `docs/guia-ava-pipeline-cli.md`, `AGENTS.md`, `README.md`.

---

## 1. O que é o `ava-pipeline-runner-cli.py`

O `ava-pipeline-runner-cli.py` é o **executor principal da esteira AVA Fabric**. Ele orquestra as
fases de modernização de um sistema legado (Delphi, COBOL, VB6, VB.NET, PowerBuilder) para uma
stack moderna (.NET, Java/Spring Boot, Python/FastAPI, Go/Gin + Angular, React, Vue, Blazor).

O runner oferece **três modos de uso**:

| Modo | Descrição |
|------|-----------|
| **Interativo** | Sem argumentos: menu para escolher projeto, modelo, fases e confirmação passo a passo. |
| **Por etapa** | `--phase <ETAPA>` executa uma única etapa da esteira sem menu. |
| **Por agente** | `--agent <ID>` executa um agente específico, da esteira ou avulso do registry. |

Cada passo roda em **contexto isolado**: o script monta o prompt, carrega a skill do agente,
invoca o modelo via Foundry IMF, extrai os artefatos da resposta, grava em disco e valida o
contrato de saída.

> **Nota importante**: este guia trata do runner **clássico/legado** (`ava-pipeline-runner-cli.py`).
> Existe também um CLI mais novo (`ava-pipeline`, em `src/shared/tools/ava_pipeline.py`), documentado
> em [`docs/guia-ava-pipeline-cli.md`](guia-ava-pipeline-cli.md). Ambos coexistem; este runner é o
> mais completo em número de fases e comportamentos (F0, F1S, F2d, F4S, FC, FP, retomada, etc.).

---

## 2. Pré-requisitos de execução

### 2.1 Ambiente

| Item | Versão / Requisito | Como verificar |
|------|-------------------|----------------|
| Python | **3.11+** | `python --version` |
| Sistema operacional | Windows (usa `msvcrt` para leitura de teclado) | — |
| VPN | `vnet-core-eus2-001` conectada | Teste de TCP no endpoint Foundry |
| Terminal | PowerShell, CMD ou VS Code terminal | — |

### 2.2 Pacotes Python obrigatórios

Instale antes da primeira execução:

```bash
pip install anthropic requests pyyaml
```

| Pacote | Uso |
|--------|-----|
| `anthropic` | SDK para chamadas ao Claude via Foundry IMF. |
| `requests` | Cliente HTTP — healthcheck do proxy Headroom. |
| `pyyaml` | Leitura de `project-config.yaml` e artefatos YAML. |

O próprio script faz uma validação de requisitos no início (`check_and_install_requirements`).
Se faltar algum pacote, ele pergunta se deseja continuar (modo interativo) ou aborta
(modo não-interativo).

### 2.3 Ferramentas externas opcionais

Ferramentas necessárias apenas para fases específicas:

| Ferramenta | Fase que usa | Comando de verificação |
|------------|--------------|------------------------|
| `dotnet` | `ava-stack-build-validator` | `dotnet --version` |
| `node` | Testes frontend Angular | `node --version` |
| `docker` | `ava-devops-containerize` | `docker --version` |
| `terraform` | `ava-devops-iac` | `terraform --version` |
| `az` | `ava-devops-cd` | `az --version` |

### 2.4 Credenciais

Crie um arquivo chamado **`.copilot-key`** na **raiz do repositório** com a API Key do Foundry,
**sem newline no final**.

```text
.copilot-key
```

> ⚠️ O arquivo `.copilot-key` está no `.gitignore` por padrão. Nunca commite essa chave.

### 2.5 Configuração do projeto

Antes de rodar, é necessário ter um projeto criado em `projects/{NOME_DO_PROJETO}/` com pelo
menos:

```text
projects/{NOME_DO_PROJETO}/
├── context/
│   ├── project-config.yaml       # configuração obrigatória
│   └── shared-context.md         # índice de estado (atualizado pelos orquestradores)
└── outputs/                      # artefatos gerados pelos agentes
```

Exemplo mínimo de `project-config.yaml`:

```yaml
project_name: "Meu-ERP"
repository_path: "/path/to/legacy"
legacy_technology: "delphi"        # delphi | cobol | vb6 | vbnet | powerbuilder
scope_modules: "all"               # "all" ou lista: ["finance", "register"]
client_name: "Cliente"
```

Para copiar o template de projeto:

```bash
cp -r projects/_template projects/Meu-ERP
```

---

## 3. Como executar

Todos os comandos assumem que você está na **raiz do repositório**.

### 3.1 Modo interativo (recomendado para primeira execução)

```bash
python "ava-pipeline-runner-cli.py"
```

O runner apresentará menus sequenciais:

1. **Seleção do modelo Foundry** (se `.copilot-key` existir).
2. **Seleção do projeto** (lista diretórios em `projects/`, exceto `_template`).
3. **Retomada de execução anterior** (se houver `runner-state.json`).
4. **Validação de pré-requisitos do F0/AST**.
5. **Modo de execução**: `1` Full Pipeline ou `2` Por Fase.
6. **Modo de confirmação**: `1` Manual ou `2` Automático.
7. **Seleção de fases** (se modo Por Fase).
8. **Confirmação passo a passo**: `S` executar, `P` pular, `A` abortar, `V` ver skill/prompt.

### 3.2 Modo não-interativo — uma etapa

```bash
python "ava-pipeline-runner-cli.py" -p Meu-ERP --phase F1
```

A flag `--phase` aceita **uma etapa** da tabela `PIPELINE`, não um grupo.
Se você passar um grupo (ex: `--phase F2`), o script lista as etapas do grupo e sai com
exit code `2`.

### 3.3 Modo não-interativo — um agente

```bash
python "ava-pipeline-runner-cli.py" -p Meu-ERP --agent ava-tobe-migration-plan
```

Para agentes que aparecem em mais de uma etapa, use `--phase` para desempatar:

```bash
# ava-devops-orchestrator aparece em F2b (plano) e F5 (execução)
python "ava-pipeline-runner-cli.py" -p Meu-ERP --agent ava-devops-orchestrator --phase F2b
python "ava-pipeline-runner-cli.py" -p Meu-ERP --agent ava-devops-orchestrator --phase F5
```

### 3.4 Listar agentes disponíveis

```bash
python "ava-pipeline-runner-cli.py" --list-agents
```

---

## 4. Parâmetros de linha de comando

| Parâmetro | Abreviação | Descrição |
|-----------|------------|-----------|
| `--agent ID` | — | Executa apenas o agente informado. Requer `-p/--project`. |
| `-p NOME` | `--project` | Projeto em `projects/`. Obrigatório com `--agent`. |
| `--phase ID` | — | Etapa da esteira a executar. Usada para desempatar `--agent`. |
| `--trigger T` | — | Trigger do prompt. Sem ele, o prompt padrão é `@agente project: X`. |
| `--feature F` | — | Feature do SpecKit (usada para fases com fan-out, como F3S). |
| `--model ID` | — | Deployment do Foundry. Padrão: `claude-sonnet-4-6`. |
| `--headroom` | — | Sobe o proxy Headroom antes do despacho. |
| `--force-single` | — | Despacha agente com fan-out como passo único (não recomendado). |
| `--dry-run` | — | Resolve o passo e mostra o prompt, sem gastar inferência. |
| `--list-agents` | — | Lista agentes despacháveis e sai. |
| `--json` | — | Emite o resultado do despacho em JSON. |

### Exit codes

| Código | Significado |
|--------|-------------|
| `0` | OK |
| `1` | Etapa falhou (`val_ok=False`) |
| `2` | Erro de configuração |
| `130` | Abortado (Ctrl+C) |

---

## 5. Fases e grupos da esteira

A esteira completa segue a ordem abaixo. O runner expande fases com fan-out
(`F3S`, `F4`) em múltiplos passos.

| Grupo | Etapas | Descrição |
|-------|--------|-----------|
| `F0` | `F0` | Extração AST determinística (pré-requisito opcional da F1). |
| `F1` | `F1` | AS-IS Diagnostic — orquestrador. |
| `F1S` | `F1a`–`F1f` | Agentes especializados AS-IS. |
| `F2` | `F2a`–`F2d` | TO-BE Architecture. |
| `F3` | `F3` | Prototype HTML navegável. |
| `F3S` | `F3S:*` | SpecKit: constitution → specs → plans → tasks (fan-out por wave). |
| `F4S` | `F4S` | Scaffold determinístico (frontend → backend → baseline → aprovação). |
| `F4` | `F4:*` | Tech Stack Generation (fan-out por task do razão). |
| `F5` | `F5` | DevOps Execute. |
| `F6` | `F6` | QA Execution. |
| `SU` | `S1`–`S4` | Summary: generate → remediate → validate → final. |
| `FC` | `FC` | Containerize (Dockerfiles + docker-compose). |
| `FP` | `FP` | Podman Run — executa a solução containerizada localmente. |

### Tabela detalhada de etapas

| Etapa | Agente | Trigger | Tipo | Observação |
|-------|--------|---------|------|------------|
| `F0` | `_ast_extractor` | — | determinístico | Extração AST via `run_ast_analysis.py`. |
| `F1` | `ava-asis-orchestrator` | `FP` | LLM | Orquestrador AS-IS. |
| `F1a` | `ava-asis-inventory` | — | LLM | Inventário quantitativo. |
| `F1b` | `ava-asis-solution-delphi`¹ | — | LLM | Arquitetura legada por tecnologia. |
| `F1c` | `ava-asis-db-analyzer` | — | LLM | Análise de banco de dados. |
| `F1d` | `ava-asis-documentation` | — | LLM | Documentação funcional. |
| `F1e` | `ava-asis-security-review` | — | LLM | Revisão de segurança. |
| `F1f` | `ava-asis-gaps-risks` | — | LLM | Gaps e riscos. |
| `F2a` | `ava-tobe-orchestrator` | `SD` | LLM | Solution Design TO-BE. |
| `F2b` | `ava-devops-orchestrator` | `DP` | LLM | DevOps Plan. |
| `F2c` | `ava-qa-orchestrator` | `TPT` | LLM | QA Test Plan & Strategy. |
| `F2d` | `wave-model-consistency` | — | determinístico | Valida coerência do wave model. |
| `F3` | `ava-prototype` | — | LLM | Protótipo HTML navegável. |
| `F3S` | `ava-speckit-orchestrator` | `SK` | LLM + fan-out | Um despacho por migration wave. |
| `F4S` | `scaffold-runner` | — | determinístico | Scaffold determinístico. |
| `F4` | `ava-stack-orchestrator` | `SG` | LLM + fan-out | Um despacho por task do razão. |
| `F5` | `ava-devops-orchestrator` | `DE` | LLM + fan-out | DevOps Execute por tarefa. |
| `F6` | `ava-qa-orchestrator` | `QE` | LLM + fan-out | QA Execute por tarefa. |
| `S1` | `ava-summary` | `SAS` | determinístico | Geração do summary. |
| `S2` | `ava-summary-remediation` | — | determinístico | Remediação do summary. |
| `S3` | `ava-summary-validate` | — | determinístico | Validação do summary. |
| `S4` | `ava-summary` | `SAS` | determinístico | Regeneração final limpa. |
| `FC` | `ava-devops-containerize` | — | LLM | Containerização. |
| `FP` | `ava-devops-podman-run` | — | LLM | Execução local via Podman. |

> ¹ O agente da F1b é resolvido pela `legacy_technology` do projeto. Para outras tecnologias,
> use os agentes avulsos do registry (`ava-asis-solution-java`, `-cobol`, `-dotnet`, `-vbnet`, etc.).

### Fases determinísticas (sem LLM)

Algumas fases não usam modelo de linguagem — rodam scripts Python ou subprocess:

| Fase | Script / Mecanismo | Saída típica |
|------|-------------------|--------------|
| `F0` | `run_ast_analysis.py` | JSONs em `outputs/asis/ast-raw/{tech}/` |
| `F2d` | `wave-model-consistency` tool | `wave-model-consistency.json` |
| `F4S` | `scaffold-runner` tool | código-base em `outputs/tobe/source-code/` |
| `S1`, `S2`, `S3`, `S4` | `build_summary_comprehensive.py`, `remediate_summary.py`, `validate_summary.py` | HTMLs em `outputs/summary/` |

Se todas as fases selecionadas forem determinísticas, o runner **pula autenticação,
headroom e ping ao Foundry**.

---

## 6. Fluxos de execução

### 6.1 Full Pipeline

```bash
python "ava-pipeline-runner-cli.py"
# Escolha: projeto → 1 (Full Pipeline) → 1 (Manual) ou 2 (Automático)
```

Ordem executada:

```text
F0 → F1 → F1a → F1b → F1c → F1d → F1e → F1f → F2a → F2b → F2c → F2d
→ F3 → F3S (expandido por wave) → F4S → F4 (expandido por task)
→ F5 → F6 → S1 → S2 → S3 → S4
```

`FC` e `FP` **não** fazem parte do Full Pipeline — são executados manualmente após a entrega.

### 6.2 Por grupo de fases (menu interativo)

```bash
python "ava-pipeline-runner-cli.py"
# Escolha: projeto → 2 (Por Fase) → selecione os números dos grupos
```

Exemplo: digitar `1 6 7` executa `F0`, `F3S` e `F4S`.

> Grupos **não** são aceitos por `--phase`. Para rodar um grupo sem menu, encadeie as etapas:
>
> ```bash
> for fase in F2a F2b F2c F2d; do
>   python "ava-pipeline-runner-cli.py" -p Meu-ERP --phase $fase || break
> done
> ```

### 6.3 Por etapa

```bash
python "ava-pipeline-runner-cli.py" -p Meu-ERP --phase F1
python "ava-pipeline-runner-cli.py" -p Meu-ERP --phase F2a
python "ava-pipeline-runner-cli.py" -p Meu-ERP --phase FC
```

### 6.4 Por agente

```bash
python "ava-pipeline-runner-cli.py" -p Meu-ERP --agent ava-tobe-migration-plan
python "ava-pipeline-runner-cli.py" -p Meu-ERP --agent ava-prototype
```

### 6.5 Retomada de execução interrompida

Se uma execução anterior foi interrompida (Ctrl+C, erro, etc.), o runner detecta
`runner-state.json` no diretório `outputs/pipeline_runner/` e pergunta:

```text
⚠️  Execução anterior detectada
    Projeto: Meu-ERP
    Último passo: 7/24 · Executados: 6 · Pulados: 1 · Abortados: 0
Deseja retomar de onde parou? [S]im / [N]ão (recomeçar):
```

> **Não existe flag `--resume`**. A retomada é feita pelo menu interativo. O runner preserva
> `executed`, `skipped`, `aborted`, `val_failed` e `exec_metrics` do estado anterior.

### 6.6 Dry-run

Útil para validar resolução de agente, trigger e prompt sem gastar tokens:

```bash
python "ava-pipeline-runner-cli.py" -p Meu-ERP --agent ava-tobe-migration-plan --dry-run
python "ava-pipeline-runner-cli.py" -p Meu-ERP --phase F1 --dry-run
```

---

## 7. Fan-out: F3S e F4

Duas fases têm **fan-out** — expandem em múltiplos despachos — e **não podem ser invocadas
como passo único** por `--phase`:

### F3S — SpecKit

Expande uma vez por migration wave. Para rodar sem menu, use `--feature`:

```bash
python "ava-pipeline-runner-cli.py" -p Meu-ERP \
  --agent ava-speckit-orchestrator --feature 001-w0-foundation
```

Se tentar `--phase F3S`, o runner recusa:

```text
AGENTE COM FAN-OUT — INFORME O ESCOPO
```

### F4 — Tech Stack Generation

Expande uma vez por task do razão SpecKit. Rode pelo menu interativo ou garanta que o
ledger de tasks esteja populado. Sem tasks, o runner informa que a F3S precisa rodar antes.

> `--force-single` permite despachar fan-out como passo único, mas **reproduz um modo de
> falha medido** (resposta enorme, artefatos fora do contrato). Use apenas para depuração.

---

## 8. Configuração do AST (F0)

A fase `F0` é opcional. Para ativá-la, adicione ao `project-config.yaml`:

```yaml
legacy_technology: "delphi"
ava_ast_analyzers:
  delphi: "/path/to/ava-fabric-delphi-analyzer"
```

Ou, para compatibilidade legada:

```yaml
ava_ast_analyzer_path: "/path/to/ava-fabric-delphi-analyzer"
```

Precedência:

```text
ava_ast_analyzers[legacy_technology] → ava_ast_analyzer_path
```

Se o campo estiver vazio/ausente, o F0 é **pulado silenciosamente** e os agentes F1 usam
análise pattern-based. Se o campo estiver preenchido mas o path não existir, o runner emite
alerta e pergunta se continua.

---

## 9. Modelo e endpoint Foundry

### Padrões

| Configuração | Valor padrão |
|--------------|--------------|
| Endpoint Anthropic | `https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic` |
| Endpoint OpenAI | `https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/openai` |
| Deployment padrão | `claude-sonnet-4-6` |
| Janela de contexto | 1.000.000 tokens |
| Máximo de saída | 128.000 tokens |

### Seleção de modelo

No modo interativo, o runner lista os deployments disponíveis no Foundry e permite escolher.
No modo não-interativo, use `--model`:

```bash
python "ava-pipeline-runner-cli.py" -p Meu-ERP --agent ava-tobe-migration-plan --model gpt-5.6-luna
```

O provider (`anthropic` ou `openai`) é detectado automaticamente a partir do nome do deployment.

---

## 10. Proxy Headroom

O Headroom é um compressor de contexto opcional que roda em `127.0.0.1:8787`. Ele reduz o
tamanho do prompt antes de enviar ao Foundry, economizando tokens.

### Comportamentos

| Situação | Ação do runner |
|----------|----------------|
| Headroom já no ar | Usa automaticamente. |
| `--headroom` passado | Sobe o proxy antes do despacho. |
| Headroom falha | Degrada para endpoint direto, avisando no console. |
| Fases determinísticas | Ignora Headroom. |

Instalação manual (se necessário):

```powershell
.\src\shared\tools\headroom\setup.ps1
.\src\shared\tools\headroom\run_standalone.ps1
```

---

## 11. Saídas e artefatos

O runner grava vários artefatos de controle e logs além dos artefatos dos agentes:

### Diretórios principais

```text
projects/{projeto}/
├── context/
│   ├── project-config.yaml
│   └── shared-context.md
└── outputs/
    ├── asis/                  # F1
    ├── tobe/
    │   ├── docs/              # F2
    │   ├── prototype/         # F3
    │   ├── source-code/       # F4
    │   └── devops/            # F5
    ├── qa/                    # F6
    ├── deliverables/          # F7 (não executado pelo runner)
    ├── summary/               # S1–S4
    └── pipeline_runner/       # logs, estado e métricas do runner
```

### Arquivos de controle do runner

| Arquivo | Descrição |
|---------|-----------|
| `outputs/pipeline_runner/runner-state.json` | Estado para retomada. |
| `outputs/pipeline_runner/runner-state-done.json` | Estado finalizado. |
| `outputs/pipeline_runner/execution-metrics.json` | Métricas de execução (tokens, tempo, artefatos). |
| `outputs/pipeline_runner/status.html` | Dashboard visual com auto-refresh de 3s. |
| `outputs/pipeline_runner/remediation-report.json` | Degradações e caminhos de correção. |
| `outputs/pipeline_runner/F{FASE}_{agente}_{timestamp}.md` | Log de cada passo. |

### Dashboard visual

Ao iniciar uma execução, o runner imprime:

```text
📊 Dashboard visual (auto-refresh 3s — Opção 2):
  file:///C:/.../projects/Meu-ERP/outputs/pipeline_runner/status.html
  VS Code: Ctrl+Shift+P → 'Simple Browser: Show' → cole a URL acima
```

O HTML mostra progresso, fases executadas/puladas/abortadas, métricas de tokens e tempo.

---

## 12. Política de erros e degradação

O runner segue a política do `AGENTS.md`: **erro não trava a fase**.

| Situação | Comportamento |
|----------|---------------|
| Insumo obrigatório ausente | Fase é pulada, registrada como degradada, e o caminho de correção vai para `remediation-report.json`. |
| Resposta truncada (`max_tokens`) | Reprova o passo (`val_ok=False`). |
| Verificação de build reprovada (F4) | Task fica como executada-com-aviso, não aborta a fase. |
| F3S com wave model incoerente | Tenta remediação determinística; se falhar, degrada sem bloquear. |
| Ctrl+C | Aborta o passo atual, salva estado para retomada. |

---

## 13. Dicas e boas práticas

1. **Sempre comece com `--dry-run`** ao testar um novo comando.
2. **Use o modo interativo** para execuções longas — ele permite pular/abortar passos.
3. **Não rode `F3S` ou `F4` como passo único** sem `--feature` ou tasks; use o menu.
4. **Mantenha o `.copilot-key` atualizado** e fora do controle de versão.
5. **Verifique o dashboard** `status.html` para acompanhar execuções longas.
6. **Retome execuções interrompidas** pelo menu interativo, não recriando estado manualmente.
7. **Confira `remediation-report.json`** após qualquer run para identificar degradações.
8. **Use `--json`** em automações/CI para parsear o resultado do despacho avulso.

---

## 14. Solução de problemas

| Problema | Causa provável | Solução |
|----------|----------------|---------|
| `.copilot-key não encontrado` | Arquivo ausente ou fora da raiz | Crie `/.copilot-key` na raiz do repo. |
| `Endpoint do Foundry inalcançável` | VPN desconectada ou Private Endpoint bloqueado | Conecte `vnet-core-eus2-001`. |
| `AGENTE COM FAN-OUT` | `--phase F3S` ou `--phase F4` sem escopo | Use menu interativo ou `--feature`/`--agent` com escopo. |
| `--phase F2 é um GRUPO` | `--phase` aceita etapa, não grupo | Use `--phase F2a`, `--phase F2b`, etc. |
| `task não pronta` (F4/F5/F6) | Dependências do ledger não satisfeitas | Rode a F3S antes e verifique `tasks-progress.json`. |
| `resposta cortada por max_tokens` | Saída da fase excedeu o teto | A fase é reprovada; reduza escopo ou reexecute. |
| Prompt muito longo / `prompt is too long` | Contexto expandido demais | Ative o Headroom ou use o runner novo `ava-pipeline`. |

---

## 15. Referências cruzadas

- [`docs/guia-comandos-pipeline-runner.md`](guia-comandos-pipeline-runner.md) — tabela de comandos
  copiar-e-colar por etapa e agente.
- [`docs/guia-ava-pipeline-cli.md`](guia-ava-pipeline-cli.md) — guia do CLI novo (`ava-pipeline`).
- [`AGENTS.md`](../AGENTS.md) — guardrails gerais da esteira.
- [`README.md`](../README.md) — visão geral do projeto e catálogo de agentes.

---

*Documento gerado para auxiliar na execução do `ava-pipeline-runner-cli.py`. Atualize-o sempre
que o script ganhar novas flags ou fases.*
