# Requirements Checklist — Spec 035

## Requisitos Funcionais
- [x] RF-001: O trigger `QE` existe no `## Triggers / Menu` e executa todos os triggers fora do escopo do `TPT`.
- [x] RF-002: `## Pre-condition Gate (QE)` bloqueia quando a esteira de código F4 não está concluída.
- [x] RF-003: `## Pre-condition Gate (QE)` bloqueia quando o DevOps Momento 2 (`DE`) não está concluído.
- [x] RF-004: `## Pre-condition Gate (QE)` bloqueia quando o planejamento `TPT` não produziu `test-plan.md` e `test-cases.md`.
- [x] RF-005: Ao bloquear, o gate emite o sinal `↳ ✅ [ava-qa-orchestrator] QE DEFERRED — {motivo}`.
- [x] RF-006: `TPT` está reclassificado como Momento 1 — Planejamento, sem alteração de comportamento.
- [x] RF-007: `QS` é um alias deprecado que emite aviso e delega ao `§Routing — Trigger QE`.
- [x] RF-008: `## Routing — Trigger PT` documenta que o executor real é o `ava-devops-compare-version`.
- [x] RF-009: `## Routing — Trigger RS` despacha `ava-qa-script-generator` em `mode: regression`.
- [x] RF-010: `FTM` é executado dentro do `QE`, após o `BM`, condicional ao `behavior-catalog.json`.

## Requisitos Não-Funcionais
- [x] RNF-001: O corpo do Routing `QS` é **movido** para o `QE`, não reescrito — ET VERIFICATION GATE, FQ COMPLETION GATE, `qa_test_runner.py` e `qa-master-report.md` preservados literalmente.
- [x] RNF-002: Os paths verificados pelo gate correspondem aos produtores reais, não aos paths do gate F6 do master (que estão errados).
- [x] RNF-003: O `## Output Contract` permanece inalterado — nenhum parser downstream é afetado.
- [x] RNF-004: Nenhuma fase nova é inventada na taxonomia do `pipeline_observer.py` (`--phase F5` mantido).
- [x] RNF-005: Version bump MAJOR (1.3.0 → 2.0.0) conforme Article X da constituição.

## Integridade
- [x] INT-001: Zero referências `§Routing — Trigger X` sem seção correspondente no arquivo.
- [x] INT-002: Todo código do `## Triggers / Menu` aparece na tabela "Resumo de cobertura por trigger".
- [x] INT-003: `FQ` consta da lista do invariante em `## Terminal Mandatory Steps`.
- [x] INT-004: Versão do frontmatter idêntica à do bloco `pipeline_observer.py`.
- [x] INT-005: `CHANGELOG.md` contém a entrada MAJOR da spec 035.
- [x] INT-006: `module.yaml` e `SKILL.md` não requerem alteração (verificado, não presumido).

## Riscos Aceitos
- [x] RA-001: O `master-orchestrator.md` Step 5.1 continua despachando `QS` em F5 (antes do `DE`); o gate deferirá e o master seguirá para F6 com WARN. Documentado em `spec.md` §Exclusions.
- [x] RA-002: Na esteira automática (`FP`), a execução QA passa a exigir invocação manual de `QE` após F6 até o follow-up no master ser implementado.
