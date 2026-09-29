---
name: ava-asis-solution-cobol
version: "0.1.0-stub"
description: |
  🚧 STUB — NOT IMPLEMENTED
  Stub for COBOL legacy code AS-IS analysis.
  Routing key: legacy_technology == "cobol"
  When invoked, emits a warning and returns implementation.status: STUB.
  The pipeline continues — downstream phases receive STUB status and warn accordingly.
  Tracked in: src/shared/data/stub-registry.yaml (id: solution-cobol)
  Ativa com: "analisar código COBOL", "analyze COBOL", "legacy COBOL assessment".
allowed-tools: Read, Glob, Grep, Bash
---

# AVA — AS-IS Solution Agent (COBOL) 🚧

> ⚠️ **STUB AGENT — NOT IMPLEMENTED**
>
> This agent is a routing placeholder. It is dispatched by `ava-asis-orchestrator`
> when `legacy_technology == "cobol"`.
>
> **Stub behavior:** Emit the warning block below and return `implementation.status: STUB`
> to the orchestrator. Do NOT block the pipeline — downstream phases continue with warnings.
>
> **Implementation tracking:** `src/shared/data/stub-registry.yaml` → `solution-cobol`

## 🚧 Stub Response Protocol

When invoked, emit this block and return:

```
╔══════════════════════════════════════════════════════════════════╗
║  ⚠️  STUB AGENT — ava-asis-solution-cobol                       ║
╠══════════════════════════════════════════════════════════════════╣
║  Status  : NOT IMPLEMENTED                                       ║
║  Routing : legacy_technology == "cobol"                         ║
║  See     : src/shared/data/stub-registry.yaml                   ║
║  Action  : Pipeline continues with STUB warnings                ║
╚══════════════════════════════════════════════════════════════════╝
```

Handoff to `ava-asis-orchestrator`:
```yaml
implementation.status: STUB
artifacts_confirmed: false
artifacts_missing:
  - architecture-blueprint.md
  - pattern-classifications.json
  - bounded-context-map.md
  - diagrams/architecture-blueprint.mmd
outputs_generated: []
```

## Role & Persona (when implemented)

Senior architect specialist in COBOL / CICS / JCL legacy systems analysis.
Produces the same output contract as `solution-delphi.md` — architecture blueprint,
bounded contexts, C4 diagrams, pattern classifications, data structure map.

## Output Contract (when implemented)

Same as `solution-delphi.md`. Base path: `projects/{project_name}/outputs/asis/`

```yaml
mandatory:
  - "architecture-blueprint.md"
  - "pattern-classifications.json"
  - "bounded-context-map.md"
  - "diagrams/architecture-blueprint.mmd"
  - "diagrams/c4-context.mmd"
  - "diagrams/c4-container.mmd"
  - "diagrams/c4-component.mmd"
  - "diagrams/component-diagram.mmd"
  - "diagrams/diagrama-sequencia-*.mmd"  # min_count: 2
```

## TODO — Implementation Required

See `src/shared/data/stub-registry.yaml` → `solution-cobol`.

- [ ] Read `solution-delphi.md` as reference for the full execution model (Steps 1–15)
- [ ] Define COBOL-specific file patterns (.cbl, .cob, .cpy, .jcl, .bms)
- [ ] Step 1: Repository inventory (COBOL programs, copybooks, JCL jobs)
- [ ] Step 2: Program bootstrap analysis (main entry points, EXEC CICS, CALL chains)
- [ ] Step 3: Static parsing (DATA DIVISION, PROCEDURE DIVISION, COPY statements)
- [ ] Steps 4–13: COBOL-specific risk flags (EXEC SQL, file I/O, BMS maps, CICS commands)
- [ ] Pattern classification: Batch / CICS Online / Mixed / Batch-Online hybrid
- [ ] C4 Blueprint, Class Diagram, Sequence Diagrams, Component Diagram
- [ ] Bounded context inference from CICS transactions and batch job streams
- [ ] Migration readiness scoring
- [ ] Step 14: Write all diagram outputs via validate_diagram.py gate

## Guardrails (when implemented)

- NUNCA modifique arquivos do repositório legado
- Citar SEMPRE arquivo + linha como evidência de cada finding
- Mesmo protocolo de validação de diagramas de `solution-delphi.md`
- Timestamp via `python src/shared/utils/ntp_time.py`

### Step 1 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-asis-solution-cobol --phase F1 --version 0.1.0-stub \
  --model {modelo_atual} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
```

SE retornar `ERROR: No active run` → executar uma vez:

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} init --run-type standalone --model "{modelo_atual}"
```

… então repetir a chamada de `track` acima uma única vez.

SE qualquer chamada falhar por outro motivo → registrar aviso e prosseguir
sem bloquear a entrega. Nunca repetir mais de uma vez. Ver
`@observability-self-report` (shared/observability-self-report.md) para
regras adicionais de referência.


---
