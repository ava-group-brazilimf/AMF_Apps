# AVA Fabric — Governance: Artifact-Only Consumption & Missing-Artifact Escalation

> **Version:** 1.0.0 — 2026-07-12
> **Applies to:** `ava-tobe-orchestrator` e todos os agentes despachados por ele em
> `src/modules/ava-fabric-agents/tobe-architecture/agents/`.
> **Reference this file as:** `@artifact-only-consumption-protocol`

---

## ABSOLUTE INVARIANT

> ⚠️ **TODO agente que consome este protocolo DEVE seguir as duas seções abaixo. Sem exceções.**
> Esta regra tem **prioridade sobre conhecimento genérico de domínio** e sobre qualquer
> instinto de "buscar mais contexto lendo o código-fonte" quando um artefato declarado como
> entrada estiver ausente. Uma vez encontrada em qualquer ponto da sessão, governa
> retroativamente todo o restante da execução daquele agente.

Contexto: a esteira AS-IS (F1) já foi otimizada (`specs/010-asis-agents-ast-artifact-consumption`)
para ser determinística e produzir artefatos (`outputs/asis/**`) prontos para consumo por LLM —
exatamente para que a esteira TO-BE (F2) nunca precise reler o código legado completo. Este
protocolo torna essa premissa um invariante explícito e adiciona o procedimento a seguir quando
um artefato esperado não existe.

---

## 1. Proibição de Releitura de Código Legado / Fonte Completo

**Proibido, sem exceção:**
- `Read`, `Glob` ou `Grep` em qualquer arquivo sob `repository_path` (valor lido de
  `project-config.yaml`) — inclui qualquer extensão de código legado (`.pas`, `.dfm`, `.dpr`,
  `.pas.bak`, e equivalentes de outras tecnologias legadas suportadas).
- `Read`/`Glob` em massa (varredura arquivo-a-arquivo) da árvore
  `outputs/tobe/source-code/**` já gerada por fases anteriores.

**Exceções legítimas, já em uso e mantidas** (não são "releitura de contexto", são operações
pontuais e determinísticas):
- Escrever (não ler) `outputs/tobe/source-code/Directory.Packages.props`.
- Escrever (não ler) `README.md` por módulo dentro de `outputs/tobe/source-code/`.
- Checagem pontual de **existência** de um único arquivo (ex.: `docker-compose.yml`) para
  decidir uma ramificação de conteúdo — nunca leitura do conteúdo de código gerado.
- Gates de build/CVE via CLI (`dotnet build`, `dotnet list package --vulnerable` e
  equivalentes) — validação determinística por compilador, não ingestão do código-fonte pelo
  LLM.

**Regra positiva:** todo o contexto necessário para qualquer agente TO-BE vem de artefatos já
gerados em `outputs/asis/**` e `outputs/tobe/**`, exatamente conforme declarado no próprio
`## Input Contract` / `## Input Sources` do agente. Se uma informação parece exigir reler o
legado, isso é sinal de que o artefato correto está ausente ou incompleto — tratar pela Seção 2
abaixo, nunca compensar lendo o código-fonte.

---

## 2. Procedimento de Escalonamento — Artefato Obrigatório Ausente

Ao encontrar um artefato de entrada ausente, classificar pelo próprio `## Input Contract` do
agente (coluna Obrigatório/Bloqueante) e seguir um dos dois caminhos abaixo. Não inventar
vocabulário novo — reutilizar as tags já em uso no repositório.

### 2.1 Input não-bloqueante ausente (⬜ / opcional / enriquecimento)

Registrar no log de execução, de forma visível (nunca omitir do output da sessão):

```
[FONTE AUSENTE] {nome do artefato} — CONFIDENCE: LOW
```

A esteira **continua** normalmente, usando o comportamento de fallback já documentado no agente
(valor estimado, seção omitida, threshold padrão, etc.).

### 2.2 Input bloqueante ausente (✅ / obrigatório)

**Nunca** prosseguir automaticamente, estimar o conteúdo ausente, ou cair para releitura de
código legado como compensação. Emitir o relatório estruturado abaixo e **parar**:

```
⛔ [ARTIFACT GATE FAILED] {agent_id} — Artefato obrigatório ausente
  trace_id        : {trace_id}
  projeto         : {project_name}
  fase            : {fase atual da esteira TO-BE}
  agente afetado  : {agent_id}
  artefato ausente: {nome do arquivo}
  path esperado   : {path completo, projects/{project_name}/...}
  produzido por   : {fase/agente que deveria ter gerado este artefato}

  ⚠️  Esta fase NÃO pode prosseguir sem este artefato.

  Sugestões de resolução (escolha uma):
    Opção A — Fornecer o artefato manualmente e reexecutar esta fase.
    Opção B — Pular esta fase com confiança degradada (CONFIDENCE: LOW) — apenas se o artefato
              for classificado como enriquecimento, não estruturalmente fundamental. NÃO
              disponível para inputs estruturalmente obrigatórios (ex.: `project-config.yaml`,
              `bounded-context-map.md` TO-BE, ADRs, `master-report.md` AS-IS).
    Opção C — Abortar a esteira e reportar ao PM/tech lead.

  → Aguardando decisão do usuário. NUNCA prosseguir automaticamente nem inventar/estimar o
    conteúdo do artefato ausente.
```

**Relação com gates já existentes:** este procedimento generaliza — não substitui — mecanismos
já corretos no repositório: o "Gate 0→1 — Validação de Consistência ADR × project-config.yaml"
de `orchestrator-tobe.md` e a guardrail `G-9` de `coder-dotnet.md` ("Se `bounded-context-map.md`
TO-BE estiver ausente → alertar e interromper... nunca inventar bounded contexts") já seguem
este espírito e permanecem como estão — este protocolo apenas estende o mesmo padrão a todos os
demais agentes da esteira TO-BE que hoje degradam silenciosamente ou dão HARD STOP sem relatório
estruturado nem opções de resolução.

---

*AVA Fabric — `@artifact-only-consumption-protocol` v1.0.0 — 2026-07-12*
