# Task Dispatch Protocol — AVA AS-IS Agents

Referenciado por `orchestrator-asis.md`.

> **Motivação:** a tool `task` do GitHub Copilot CLI exige 3 campos obrigatórios —
> `description`, `prompt`, `agent_type`. Instruir o dispatch com pseudocódigo abstrato
> ("Dispatch: @agent", "Despachar como SubAgent com prompt: ...") deixa o LLM compor a
> tool call livremente, e ele ocasionalmente omite um campo, produzindo:
>
> `Multiple validation errors: "description" Required / "prompt" Required / "agent_type" Required`
>
> (3 ocorrências medidas em `docs/copilot-cli-runtime-facts.md` §12.2, de 345 falhas de
> `task`). Este protocolo elimina a composição livre: o orquestrador roda um script
> determinístico ANTES de todo dispatch e usa os 3 campos retornados **verbatim**.

---

## ⛔ Regra — TASK_CALL_FIELDS_MANDATORY

**NUNCA invocar a tool `task` sem antes rodar `build_task_call()`.** Os 3 campos da
tool call (`description`, `agent_type`, `prompt`) DEVEM vir, sem edição de conteúdo,
do JSON emitido por `build_dispatch_payload.py`. Compor esses campos "de cabeça" —
mesmo parcialmente — é violação de contrato e conta como dispatch failure.

`agent_type` é sempre o `agent_id` canônico do agente (== o campo `name:` do
`.github/agents/{agent_id}.agent.md`, == o mesmo valor usado como
`resolved_solution_agent` e demais `agent_id` do DAG). Nunca `"general-purpose"` nem
`"explore"` (proibido por AGENTS.md § D1).

## PROCEDURE build_task_call

```
PROCEDURE build_task_call(agent_id, project_name, missing?, ast_slice?, execution_mode?, extra?):
  result = Bash: python src/modules/ava-fabric-agents/asis-diagnostic/utils/build_dispatch_payload.py \
             --agent {agent_id} --project {project_name} \
             --missing "{','.join(missing or [])}" \
             --ast-slice "{','.join(ast_slice or [])}" \
             {"--execution-mode " + execution_mode if execution_mode else ""} \
             {"--extra \"" + extra + "\"" if extra else ""} \
             --json

  IF result.exit_code == 2:  # NOT_FOUND — agent_id não corresponde a nenhum wrapper
    Logar "TASK_DISPATCH_PAYLOAD_NOT_FOUND: agent_id={agent_id} — " + result.detail
    → PARAR este dispatch específico; NÃO adivinhar agent_type; reportar ao usuário
      com result.valid_agent_ids como referência
    RETURN { ok: false }

  IF result.exit_code not in [0, 2]:  # erro inesperado do script
    Logar "TASK_DISPATCH_PAYLOAD_ERROR: " + result.detail
    RETURN { ok: false }

  # Sucesso — usar os 3 campos SEM MODIFICAÇÃO na tool call task
  RETURN {
    ok: true,
    description: result.description,
    agent_type:  result.agent_type,
    prompt:      result.prompt,
  }
```

**Uso na tool call:**

```
call = build_task_call(agent_id, project_name, missing, ast_slice, execution_mode, extra)
IF call.ok == false:
  → NÃO chamar a tool task para este agente; tratar como dispatch failure
  (mesmo fluxo de `should_dispatch()` retornando dispatch:false por outro motivo)

ELSE:
  INVOKE tool `task` COM:
    description: call.description
    agent_type:  call.agent_type
    prompt:      call.prompt
```

## Exemplo concreto preenchido (Wave 1 — dispatch de `ava-asis-solution-java`)

```
Bash: python src/modules/ava-fabric-agents/asis-diagnostic/utils/build_dispatch_payload.py \
        --agent ava-asis-solution-java --project meu-erp --json
```

retorna:

```json
{
  "description": "Executar ava-asis-solution-java (Fase F1) para o projeto meu-erp",
  "agent_type": "ava-asis-solution-java",
  "prompt": "Leia por inteiro src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-java.md antes de qualquer outra ação e siga todos os Execution Steps literalmente.\nProjeto: meu-erp.\nFILE_PERSISTENCE_RULE: para toda escrita de arquivos, usar Bash + PowerShell batch (BatchWriteProtocol) — $files=[ordered]@{...} + loop Set-Content em UMA ÚNICA chamada Bash. NUNCA usar Write tool por arquivo individual.",
  "spec_path": "src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-java.md"
}
```

A tool call `task` correspondente usa `description`, `agent_type` e `prompt` exatamente
como retornados — nenhum campo é composto manualmente pelo orquestrador.

## Regras de aplicação

- `build_task_call()` é chamado em **todo** ponto de dispatch de agente LLM: Wave 1
  (Step 3.1), Wave 2 (Step 3.1b / `dispatch_wave()`), `dispatch_bridge_fastqa()`,
  `remediate_pending_agents()` e qualquer retry da `retry_queue`.
- `missing`/`ast_slice`/`execution_mode` são os mesmos valores já resolvidos por
  `should_dispatch()` / `evaluate_context_budget()` — apenas repassados ao script, nunca
  recompostos.
- `extra` é reservado para a instrução específica do dispatch (ex: o texto completo do
  Step C de `dispatch_bridge_fastqa()`) quando o skeleton padrão não é suficiente.
- Falha de `build_task_call()` (`ok: false`) **não** é tratada como falha do agente —
  é uma falha de **preparação do dispatch**; não conta contra `dispatch_attempts` do
  agente e não deve ser re-tentada sem antes corrigir `agent_id`/script.
