# Tasks — Spec 042: Gate de aprovação humana da conformidade F3S

Status: **todas concluídas** em 2026-08-21. Verificação executada contra
`projects/nopcommerce-04`, que estava no estado exato do incidente (3 achados
`critical`/`high` e `_verdict_rule_check.consistent == false`).

## 1. Governança

- [x] Registrar a exceção à política "erro nunca trava fase" no cabeçalho de
      `src/shared/data/pipeline-dag/F3S.yaml`, nomeando os dois modos.
- [x] Registrar a mesma exceção no comentário de `_abort_pipeline`
      (`pipeline_runner 19.py`), com ponteiro para o cabeçalho do DAG.
- [x] Documentar em `docs/plan/speckit-compliance-approval-gate.md` o limite
      honesto: em modo automático o gate é aviso, não barreira.

## 2. Tool de gate — `src/shared/tools/speckit_compliance_gate.py`

- [x] `triggers()` — os três gatilhos de R1, independentes.
- [x] `fingerprint()` — `sha256` sobre veredito + achados + `graph_checksum`.
- [x] `gate_status()` — leitura pura, fonte única para o exit gate.
- [x] `evaluate()` — grava `compliance-gate.json`; **sempre exit 0**.
- [x] `record()` — `approved` / `auto_acknowledged` / `rejected`, com
      `--fingerprint` opcional para recusar decisão sobre conteúdo que mudou
      entre a exibição e a resposta.
- [x] Nome e Papel obrigatórios em `approved` e `rejected`.
- [x] Timestamp por `ntp_time.resolve()`, com `approved_at_source` e
      `ntp_fallback`. Chamado **só** nos modos de gravação — `--evaluate` roda
      em todo run e não pode pagar até 24s de timeout de rede.
- [x] Append em `approval-log.jsonl`; falha de escrita do log não invalida a
      decisão já gravada.
- [x] `render_panel()` — painel legível dos achados.

## 3. Preservação da assinatura

- [x] `_carry_approval()` em `speckit_compliance_normalize.py`.
- [x] Aplicado nos três caminhos de escrita (canônico válido, reconstruído,
      fallback).
- [x] Rebaixamento para `expired` preservando `reviewer` e `previous_status`.
- [x] Caminho no-op passa a reportar `action: "approval_expired"` quando de fato
      reescreve — o retorno não pode dizer "none" tendo escrito.

## 4. DAG e propagação

- [x] `wave6c` em `F3S.yaml`, entre wave6b e wave7, com `requires_approval: true`.
- [x] `wave7.depends_on` apontado para `wave6c`.
- [x] Item `kind: human_approval` em `exit_gate.items`.
- [x] `requires_approval` propagado em `pipeline_plan.dag_steps()` — a lista de
      chaves é fixa, então chave nova no YAML não chega ao runner sozinha.

## 5. Runner e entrada com prazo

- [x] `_consumir_linha()` extraída de `safe_input` e compartilhada.
- [x] `safe_input_timeout()` — prazo até a primeira tecla; `None` no estouro e
      quando não há console (`OSError`).
- [x] `_ler_gate_aprovacao()`, `_registrar_decisao()`, `_painel_aprovacao()`,
      `_coletar_identidade()`, `_solicitar_aprovacao()`.
- [x] Hook após passo de tool com `requires_approval`.
- [x] Manual: "S" coleta identidade obrigatória; "N" para a esteira e grava
      `rejected`.
- [x] Automático: prompt opcional com prazo; silêncio → `auto_acknowledged` e
      segue.
- [x] `_record_degradation` nos dois desfechos, para o relatório de remediação e
      o banner de retomada.

## 6. Exit gate

- [x] `kind: "human_approval"` em `check_item()`, importando
      `gate_status()` em vez de recalcular o fingerprint.
- [x] `kind` propagado no resultado de `check_item` — a orientação de correção
      depende dele.
- [x] `_print()` separa decisão pendente de artefato ausente: dizer "gere-o"
      manda procurar arquivo quando o que falta é decidir.
- [x] Corrigido o caminho de import: `REPO_ROOT` (onde o código vive) para achar
      o módulo, `root` (raiz de dados) só para ler o projeto. Em produção
      coincidem, e usar `root` para os dois funcionava por coincidência.

## 7. Contrato do agente

- [x] `compliance-agent.md` — bloco `approval` documentado como **escrito
      exclusivamente pela ferramenta**, com instrução explícita de preservá-lo
      inalterado e de nunca produzi-lo.

## 8. Verificação

Executada contra `projects/nopcommerce-04`:

- [x] A1 — `--evaluate` acusa `requires_approval: true` com 3 blockers, exit 0.
- [x] A2 — exit gate sem decisão: FAIL, orientando a decidir.
- [x] A3 — `--approve --name "Rafael Almeida" --role "Tech Lead"`: exit gate PASS,
      `approved_at_source: a.st1.ntp.br`.
- [x] A4 — `--approve` sem Nome: recusado, exit 2, estado segue `pending`.
- [x] A5 — `--acknowledge --mode auto`: `auto_acknowledged` sem revisor, PASS.
- [x] A6 — `--reject`: exit gate FAIL.
- [x] A7 — achado novo: `expired`, exit gate volta a reprovar.
- [x] A8 — recompilação idêntica: assinatura preservada.
- [x] A9 — wave6b após a assinatura: `approval` intacto.
- [x] A10/A11 — cobertos por `tests/tools/test_runner_approval_gate.py` com o
      teclado substituído (o prompt real não é automatizável em CI).
- [x] A12 — `approval-log.jsonl` com as três decisões, na ordem.

Testes automatizados adicionados:

| Arquivo | Casos |
|---|---|
| `tests/ava-fabric-agents/speckit/test_speckit_compliance_gate.py` | 21 |
| `tests/tools/test_runner_approval_gate.py` | 22 |
| `test_speckit_compliance_normalize.py` (acrescidos) | 3 |
| `test_artifact_gate_speckit.py` (acrescidos) | 6 |
| `test_pipeline_plan.py` (estendido) | ordem da wave6c e propagação |

`python -m pytest tests/tools tests/ava-fabric-agents -q` → **391 passed**, 16
falhas pré-existentes e não relacionadas (agent registry/wrappers, gates da
tobe-architecture, `ava_pipeline_f4`, CHK-SK-008), o mesmo conjunto do baseline.

## 9. Pendências conhecidas

- Autenticação do aprovador (hoje é registro, não prova).
- `--redo <fase>` para repetir uma fase degradada sem recomeçar.
- O caso A10/A11 depende de teclado substituído; o prompt real só é exercitado
  manualmente.
