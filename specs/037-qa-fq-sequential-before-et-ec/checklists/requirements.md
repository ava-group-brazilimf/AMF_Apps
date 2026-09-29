# Requirements Checklist — Spec 037

## Requisitos Funcionais
- [ ] RF-001: O step 9 do trigger `QE` despacha **apenas** `ava-qa-bridge-fastqa-tobe` (FQ).
- [ ] RF-002: O step 9a (FQ COMPLETION GATE) executa imediatamente após o step 9, com o mesmo
      conteúdo de verificação do atual 9c.
- [ ] RF-003: O step 9b despacha `ava-qa-exploratory` e `ava-qa-evidence-capture` em paralelo,
      independentemente do resultado do step 9a.
- [ ] RF-004: O step 9c (ET VERIFICATION GATE) executa após o step 9b, com o mesmo conteúdo do
      atual 9b.
- [ ] RF-005: Os passos 10 (PT) e 11 (RS) permanecem inalterados e continuam corretos, pois EC
      ainda é despachado (em 9b) antes deles.

## Requisitos Não-Funcionais
- [ ] RNF-001: Nenhum texto de instrução crítica (`⛔ CRITICAL` do FQ, os 4 artefatos obrigatórios
      do ET) é reescrito — apenas reordenado.
- [ ] RNF-002: `## Output Contract` permanece inalterado.
- [ ] RNF-003: Version bump PATCH (2.1.0 → 2.1.1) conforme Article X da constituição.
- [ ] RNF-004: Wrapper `.github/agents/ava-qa-orchestrator.agent.md` regenerado e sincronizado
      (`metadata.version = 2.1.1`).

## Integridade
- [ ] INT-001: Todas as 5 ocorrências textuais da ordem `ET→EC→FQ` (fora do bloco do step 9) são
      atualizadas para `FQ→ET→EC` (ou `FQ→ET+EC` quando aplicável).
- [ ] INT-002: A referência cruzada no 4b TS COMPLETION GATE aponta para "(passo 9b)".
- [ ] INT-003: `CHANGELOG.md` contém a entrada PATCH da spec 037.
- [ ] INT-004: `tests/tools/test_pipeline_plan.py` continua passando (não depende da ordem
      interna do DAG).
- [ ] INT-005: `tests/tools/test_agent_wrappers.py` continua passando após regenerar o wrapper.

## Riscos Aceitos
- [ ] RA-001: Latência total do trigger `QE` aumenta (FQ deixa de rodar em paralelo com ET+EC) —
      aceito explicitamente pelo usuário como objetivo da mudança.
