# Retry Protocol — AVA AS-IS Orchestrator

Referenciado por `orchestrator-asis.md`.
Acionado quando qualquer agente reportar `status: failed` durante COLLECT ou ADVANCE.

---

## Regras

- **Máximo 4 retentativas** por agente. Incrementar `retries` a cada tentativa.
- **NUNCA acionar Wave 3** enquanto este protocolo estiver em execução.
- Ordem obrigatória: predecessor → successor (Wave 1 antes de Wave 2) — esta ordem agora vale
  também para o **dispatch inicial**, não só para retry (ver `orchestrator-asis.md` §
  Solution Agent Gate).

## Sequência de Retry

```
SE algum agente com status: failed antes do ADVANCE para Wave 3:

  PASSO 1 — Wave 1 (dispatch imediato, sem dependência entre si):
    1. solution-{tech}        (predecessor de toda a Wave 2 — ver Solution Agent Gate)
    2. security-orchestrator  (independente — nunca espera o gate; somente se security_enabled_asis: true)

    ⛔ solution-{tech} com retries=4 sem sucesso (OU implementation_status=STUB) NÃO aciona HG —
       aciona halt_pipeline() e interrompe TODA a esteira imediatamente (ver orchestrator-asis.md
       § Solution Agent Gate). Este é o único agente com esse comportamento; todos os demais
       seguem o PASSO 3 normal (HG).

  PASSO 2 — Wave 2 (somente após solution-{tech} completed + artifacts_confirmed=true — Solution Agent Gate OPEN):
    3. test-qa
    4. inventory
    5. db-analyzer
    6. events-pubsub
    7. doc:FT
    8. doc:VC

  PASSO 3 — Verificar ADVANCE:
    TODOS os agentes ativos (Wave 1 + Wave 2) completed + artifacts_confirmed → acionar gap-migration-analyzer / gaps-risks ✅
    Qualquer agente da Wave 2 com retries=4 sem sucesso → acionar HG ❌ (pipeline continua com dados parciais)
    solution-{tech} com retries=4 sem sucesso → halt_pipeline(), NÃO HG (ver acima)
```

## Persistência no retry (ISSUE-002 · RC-4)

Um retry NÃO pode trocar o modo de persistência. Vale o mesmo contrato do dispatch original
(`orchestrator-asis.md` § Regras Fundamentais, regras 12 e 13):

- **NUNCA** retentar um agente produtor de artefatos como background agent `general-purpose`.
  Sempre `task` agent `mode: sync` (ou `inline`, se o Context Budget assim determinar).
- O retry usa o batch PowerShell do [BatchWriteProtocol](batch-write-protocol.md) em **uma única
  chamada `Bash`**, exatamente como o dispatch original.
- O retry regenera **apenas** `artifacts_missing[]` vindo do `artifact_gate.py` — nunca o contrato
  de saída completo.
- Sucesso de um retry é confirmado por `artifact_gate.py` (bytes em disco), nunca pela mensagem de
  conclusão do agente. Um retry que "reporta sucesso" mas não muda o gate continua `failed` e
  consome uma tentativa.

## Invariantes

- NUNCA pular a ordem predecessor→successor
- NUNCA acionar Wave 3 com qualquer agente em failed/running/pending
- NUNCA ultrapassar 4 retentativas sem acionar HG (exceto `solution-{tech}`, que aciona `halt_pipeline()` em vez de HG)
- Agentes paralelos da Wave 1 sem dependência entre si podem ser retentados em conjunto — exceto `solution-{tech}` (predecessor de toda a Wave 2)
- Wave 2 NUNCA é despachada (nem para retry) antes do Solution Agent Gate abrir
- NUNCA retentar em background agent nem fora do batch write — ver § Persistência no retry
