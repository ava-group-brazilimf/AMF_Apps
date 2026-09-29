# Requirements Checklist: Isolamento de Janela por Agente + Context Engineering

**Purpose**: Verificar que a spec 033 entrega isolamento real de contexto, cobertura completa de
wrappers, guardrails herdados de fonte única e enforcement executável — **sem** alterar o modo de
execução via GitHub CLI.
**Created**: 2026-08-02
**Feature**: `specs/033-agent-isolation-context-engineering/spec.md`

---

## IMFAI Constitution Compliance *(mandatory — always first)*

> These items apply to every IMFAI agent development checklist regardless of change type.

- [ ] CHK-C01 `[Article II]` Agent frontmatter contains ONLY `name`, `version`, `description` (Portuguese + activation phrases), `allowed-tools` — no `phase`, `module`, `inputs`, `outputs`, or `dependencies`
- [ ] CHK-C02 `[Article I]` No technology versions hardcoded in agent body — all values resolved from `reference-architecture.yaml` or `project-config.yaml`
- [ ] CHK-C03 `[Article II]` All output paths use lowercase `{project_name}` and the correct phase folder (`asis/`, `tobe/docs/`, `qa/`, etc.)
- [ ] CHK-C04 `[Article V]` Agent instruction body is written in Brazilian Portuguese
- [ ] CHK-C05 `[Article IV]` Module-level `module.yaml` registration reviewed — new entry added (new-agent) or existing entry version-bumped (modify-existing)
- [ ] CHK-C06 `[Article XI]` SKILL.md status confirmed — new SKILL.md created (new-agent) or existing verified still routes correctly after changes (modify-existing)
- [ ] CHK-C07 `[Article VI]` BDD acceptance scenarios cover nominal path, edge case (empty/missing input), and quality gate path (human_gate_required trigger)

> **Nota de aplicação nesta spec** — CHK-C01 vale para as **specs canônicas** em
> `src/modules/**/agents/*.md`, que permanecem inalteradas (exceto `orchestrator-asis.md`).
> Os `.github/agents/*.agent.md` são artefatos **gerados** sob o schema do Copilot CLI, que
> **descarta** `version`/`allowed-tools` e **enforça** `tools` — divergência registrada em
> `plan.md` § 9 Complexity Tracking, com proposta de emenda de escopo do Artigo II.
> CHK-C05 e CHK-C06 são **N/A**: nenhum agente novo, nenhum `SKILL.md` novo.

---

## `AGENTS.md` — fonte única e language-agnostic

- [ ] CHK001 `AGENTS.md` existe na raiz do repo e tem **≤ 8 KB**
- [ ] CHK002 Contém exatamente um par de delimitadores `<!-- AGENTS-CORE:START -->` /
      `<!-- AGENTS-CORE:END -->`
- [ ] CHK003 **Nenhuma** menção a `delphi`, `vb6`, `vbnet`, `cobol`, `powerbuilder`, `dotnet`,
      `.NET`, `java`, `angular`, `.pas` ou versão de framework —
      `validate_language_agnostic.py --strict --paths AGENTS.md` com exit 0
- [ ] CHK004 A resolução de linguagem é feita por referência a `legacy_technology` do
      `project-config.yaml`, nunca por valor literal
- [ ] CHK005 Cobre as 10 seções obrigatórias: identidade/escopo · Output Integrity Rules ·
      protocolo de retrieval · orçamento de contexto · handoff por extract · protocolo do
      `shared-context.md` · batch write · guardrails comuns · convenções de path · resolução de
      linguagem
- [ ] CHK006 As 4 Output Integrity Rules de `.github/copilot-instructions.md` L255–310 estão
      preservadas (nenhuma sumiu na destilação); a Regra 3 (PRE-FLIGHT) é declaradamente substituída
      por `artifact_gate.py`, que faz o mesmo antes do processo existir
- [ ] CHK007 Escrito em pt-BR (Artigo V)

## Wrappers `.agent.md` — cobertura e formato

- [ ] CHK008 **102 de 102** agentes despacháveis têm wrapper em `.github/agents/` (era 1) —
      107 arquivos de spec menos 4 sub-skills e 1 depreciado
- [ ] CHK009 Os 32 agentes que não tinham `SKILL.md` deixaram de depender de dispatch textual
- [ ] CHK010 Todo wrapper é **gerado**; nenhum foi editado à mão —
      `generate_agent_wrappers.py --check` retorna exit 0
- [ ] CHK011 O gerador é alimentado por `agent_registry.catalog()`, nunca por lista manual
- [ ] CHK012 Todo `name` casa `^ava-[a-z0-9-]+$`
- [ ] CHK013 Todo wrapper emite `tools:` com nomes reais do CLI
      (`view`/`create`/`edit`/`glob`/`grep`/`powershell`) — **`Bash` mapeado para `powershell`**
- [ ] CHK014 **Nenhum** wrapper emite `version:` ou `allowed-tools:` no topo do frontmatter
- [ ] CHK015 `metadata.version` de cada wrapper é igual ao `version:` do frontmatter canônico
- [ ] CHK016 `model: claude-sonnet-4` pinado em todos — nunca `auto`
- [ ] CHK017 Todo corpo tem **< 30.000 caracteres**
- [ ] CHK018 `copilot --log-level warning` produz **zero** `unknown fields ignored`
- [ ] CHK019 O bloco `AGENTS-CORE` é **byte-idêntico** ao de `AGENTS.md` nos 102 wrappers
- [ ] CHK020 O preflight falha se `~/.copilot/agents/` contiver nome colidente
- [ ] CHK021 As 4 sub-skills de `db-analyzer/skills/*.md` **não** receberam wrapper (excluídas por
      `_is_dispatchable` — não têm identidade de execução)

## Isolamento de janela

- [ ] CHK022 Cada nó da F1 roda como processo próprio (`copilot -p --agent <id>`)
- [ ] CHK023 Por nó: `session.shutdown.systemTokens ≈ 13.449` (estático com as flags do runner)
- [ ] CHK024 Por nó: `currentTokens` muito abaixo de 128.000
- [ ] CHK025 **Zero** `session.compaction_start` e **zero** `session.truncation` num run F1 completo
- [ ] CHK026 Cada processo recebe `--session-id` gerado pelo runner, e os fatos vêm de
      `events.jsonl` num caminho determinístico — **não** de parsing de stdout
- [ ] CHK027 As flags do M0 estão todas presentes: `--no-custom-instructions`,
      `--disable-builtin-mcps`, `--excluded-tools=skill`, `--no-remote`, `--no-remote-export`,
      `--secret-env-vars`
- [ ] CHK028 `--allow-all` / `--yolo` / `--autopilot` / `--resume` / `--continue` **não** são usados
      pelo runner
- [ ] CHK029 `-C <REPO_ROOT>` (não o diretório do projeto) — as specs usam paths repo-relativos

## Context pack (shared context com memória)

- [ ] CHK030 O pack é materializado em
      `projects/{project_name}/outputs/.context/{agent_id}/context-pack.md` **antes** do spawn
- [ ] CHK031 Traz as 5 seções do contrato (fatia · índice upstream · como consultar · output
      contract · estado da fase)
- [ ] CHK032 A seção 2 carrega **paths e seções, nunca conteúdo**
- [ ] CHK033 **Nenhum** pack excede o orçamento do agente
- [ ] CHK034 Pack acima do orçamento degrada para query-only e **registra a decisão dentro do
      próprio pack** — nunca truncamento silencioso
- [ ] CHK035 Dois builds consecutivos com o mesmo input produzem **bytes idênticos**
- [ ] CHK036 Agente desconhecido (fatia `None`) → pack vazio com `known_agent: false`, sem exceção
- [ ] CHK037 Reusa `headroom_context.build_agent_context()` — nenhum decoder SmartCrusher novo
- [ ] CHK038 `shared-context.md` é índice curado, não depósito; o pack traz só o extrato
- [ ] CHK039 `context-pack-protocol.md` define a precedência: pack presente → autoridade; ausente →
      `## Input Contract` clássico

## Enforcement executável

- [ ] CHK040 `.github/hooks/ava-guardrails.json` registra o `preToolUse`
- [ ] CHK041 Leitura sob `outputs/asis/ast-raw/` é **negada**
- [ ] CHK042 Leitura de arquivo ≥ 200 KB é **negada**
- [ ] CHK043 O `permissionDecisionReason` é **acionável** — aponta para `headroom_tool.py slice`
- [ ] CHK044 A negativa aparece como `hook.start` / `hook.end` no `events.jsonl`
- [ ] CHK045 `--add-dir` é usado **apenas** para árvores de código legado fora do repo

## DAG e anti-divergência (risco R1)

- [ ] CHK046 `F1.yaml` cobre o DAG F1 completo, não só `wave2`
- [ ] CHK047 `tests/test_pipeline_dag.py` compara **conteúdo**:
      `dag.slice ≡ AGENT_ARTIFACT_SLICE` (não só presença, como o `validate_dag` atual)
- [ ] CHK048 `dag.nodes ≡ ARTIFACT_CONTRACTS.keys() ≡ agent_registry.catalog()`
- [ ] CHK049 Grafo de waves acíclico; todo nó com `slice`, `timeout_s` e artefatos
- [ ] CHK050 **Nenhum** nó usa `context: long_context` (tier não medido)
- [ ] CHK051 O CI coleta `tests/` da raiz — hoje `CHK-04` do
      `validate-agent-observability.yml` só coleta `tests/tools` e `tests/utils`

## Runner — classificação, retry e falha segura

- [ ] CHK052 Nó com `exit 0` mas sem artefato é classificado **`failed`** — o gate é a autoridade
- [ ] CHK053 404 *"Model not found on provider"* → `config_error`, **aborta a fase**, **sem** retry
- [ ] CHK054 Backoff só para `statusCode` ∈ {429, 5xx}; **nunca** para 404 nem para
      artefato-ausente
- [ ] CHK055 `artifact_gate` roda antes de cada tentativa (anti-retry-storm)
- [ ] CHK056 Timeout mata a árvore com `taskkill /PID <pid> /T /F`, não `terminate()`
- [ ] CHK057 `context_overflow` é sinalizado mesmo quando o nó "passou"
- [ ] CHK058 `max_parallel` do DAG é honrado (hoje é lido e ignorado)
- [ ] CHK059 `compression=on|off` é registrado por nó — sem degradação silenciosa, ao contrário do
      `.bat`
- [ ] CHK060 Os 3 ruídos benignos do M0 são filtrados e não geram falso positivo de falha

## Orquestrador de fase

- [ ] CHK061 `orchestrator-asis.md` cai de 193.848 para ~15 KB
- [ ] CHK062 Bump **MAJOR** aplicado (o contrato de dispatch muda) — Artigo X
- [ ] CHK063 As regras 10/11/13/14 do DAG Event Protocol têm substituto **executável** no runner
      antes de saírem do prompt — nenhuma regra desaparece sem cobertura
- [ ] CHK064 O Solution Agent Gate (regra 9 — HALT em falha ou `implementation_status == STUB`)
      permanece no orquestrador
- [ ] CHK065 A tabela `SOLUTION_AGENTS` deixa de ser comentário YAML duplicado e passa a vir do
      `agent_registry`
- [ ] CHK066 `ava-asis-security-orchestrator` continua sendo nó do DAG — o sub-pipeline de segurança
      não é contornado (Artigo VII)

## Observabilidade

- [ ] CHK067 `pipeline_observer track` é idempotente por `(run_id, agent_id, attempt)`
- [ ] CHK068 O runner emite `track` com tokens e duração **reais** de `session.shutdown.modelMetrics`
- [ ] CHK069 `verify_agent_observability.py` foi atualizado **no mesmo commit** — CI não fica
      vermelho nem a fase fica cega
- [ ] CHK070 `trace_id` propagado sem mutação: `project-config.yaml` → envelope → pack → artefato
- [ ] CHK071 `headroom_tool.py attribute` continua funcionando, com janelas mais precisas

## Bugs corrigidos no caminho tocado

- [ ] CHK072 `projects/MeuERP-002/context/project-config.yaml:9` — `scope_modules` deixa de ser
      engolido pelo comentário de `trace_id`
- [ ] CHK073 `quality_gates:` declarado uma única vez em `MeuERP-002` e em `_template`
- [ ] CHK074 `run_ast_analysis._ensure_manifest_metrics` — `tokens_out` passa a ser lido pelo
      `context_budget`, e o budget gate deixa de ler 0 e liberar tudo

## Restrição do usuário — modo de execução preservado

- [ ] CHK075 `git diff --exit-code copilot-cli-headroom.bat copilot-cli-v1.bat` **sem saída**
- [ ] CHK076 O operador abre o CLI e chama o orquestrador da fase exatamente como antes
- [ ] CHK077 Os 75 `.github/skills/*/SKILL.md` continuam funcionando como entrada humana
- [ ] CHK078 `.github/copilot-instructions.md` permanece, com o bloco `SPECKIT` intacto
- [ ] CHK079 `/agent` e `--agent` invocam qualquer um dos 102 em janela própria (modo híbrido)
- [ ] CHK080 `execution_backend: inprompt` (default) restaura o caminho atual **bit a bit**

## Escopo — o que NÃO entra

- [ ] CHK081 F2–F8 não foram migradas; só `F1.yaml` existe
- [ ] CHK082 Knowledge graph / `ast_index.py` / FTS5 / write-back F2 ficaram para a **spec 034**
- [ ] CHK083 `master-orchestrator.md` está intacto
- [ ] CHK084 A limpeza language-agnostic do repo está **mapeada** em `spec.md` § 7, não executada —
      inclusive as 9 `description:` de wrapper que herdam tecnologia da spec canônica (o corpo
      gerado é neutro; a linha herdada não)
- [ ] CHK085 A remoção em massa dos ~206 blocos `track` não foi feita — só a idempotência e a regra
      "agente migrado pode omitir"

---

## Notes

- Check items off as completed: `[x]`
- CHK-C items são da Constituição IMFAI; os demais são específicos desta feature
- Roteiro executável de verificação: `specs/033-agent-isolation-context-engineering/quickstart.md`
- Números de runtime (janela, overhead, flags): `docs/copilot-cli-runtime-facts.md` — **medidos**,
  não estimados
