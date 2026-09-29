# Agent Development Tasks: Remoção de Geração de Arquivos .drawio nos Agentes TO-BE

**Plan**: `specs/014-remover-geracao-drawio-tobe/plan.md`
**Status**: Implementation complete; verification in progress.

## Category 1 — Version & Contract Verification

- [x] **1.1** Confirm `security-design-tobe.md` frontmatter gained `version: "1.1.0"` /
  `date: 2026-07-09` (não existia antes — adicionado per Guardrail #3).
- [x] **1.2** Confirm `architecture-design-tobe.md` frontmatter `version` bumped `1.0.0`→`1.1.0`.
- [x] **1.3** Confirm `migration-plan-tobe.md` frontmatter `version` bumped `1.2.1`→`1.3.0`.
- [x] **1.4** Confirm `coexistence-strategy-tobe.md` frontmatter `version` bumped `1.0.0`→`1.1.0`.
- [x] **1.5** Confirm `orchestrator-tobe.md` frontmatter `version` bumped `2.3.0`→`2.4.0`.
- [x] **1.6** Confirm each agent's own `pipeline_observer.py --version` self-report line matches
  its new frontmatter version (checked in `security-design-tobe.md`,
  `architecture-design-tobe.md`, `migration-plan-tobe.md`, `coexistence-strategy-tobe.md`).

## Category 2 — Implementation

- [x] **2.1** `security-design-tobe.md`: `.drawio` removido do bloco PRE-WRITE VALIDATION GATE,
  da linha de sanitização Draw.io, do Output Contract (`security_diagram_drawio`), e do
  Validation Gate checklist — DONE
- [x] **2.2** `architecture-design-tobe.md`: `.drawio` removido do bloco PRE-WRITE VALIDATION
  GATE; bullet "Draw.io" do C4 removido; `context-map.drawio` removido de "Regras do Context Map"
  e do Output Path; ER diagram drawio removido; 9 chaves `*_drawio` removidas do Output Contract
  YAML; tabela AS-IS Parity Check simplificada para `.mmd`-only; bullets "Diagrams Creation
  Mandate" simplificados; 3 seções drawio-only removidas inteiras (`Pre-Output Checklist
  Draw.io`, `Canonical Draw.io XML Templates`, `Template canônico — Value Chain Draw.io`); 2
  guardrails reescritos (Component Diagram BC Coverage, Context Map) — DONE
- [x] **2.3** `migration-plan-tobe.md`: `.drawio` removido do bloco PRE-WRITE VALIDATION GATE, da
  descrição do skill "Gantt Generator", da tabela "Artefatos Derivados do Wave Model"; subsection
  `#### 6.5.5 — Gerar migration-gantt.drawio` removida inteira (`6.5.6`→`6.5.5`); Output Contract
  YAML (`gantt_chart_drawio` removido) e 5 pontos de contagem "14→13 arquivos" corrigidos (tabela
  de triggers, nota SSoT, G-6, G-10, G-21, Validation Gate, Diagram Governance table) — DONE
- [x] **2.4** `coexistence-strategy-tobe.md`: `.drawio` removido do bloco PRE-WRITE VALIDATION
  GATE, do skill "Coexistence Diagram Generator", do Output Contract (`coexistence_drawio`,
  4→3 artefatos), da descrição do artefato, do Step 8 (item 4 removido), e do Diagram Governance
  — DONE
- [x] **2.5** `orchestrator-tobe.md`: Fase 1 (output/checklist `context-map.drawio` + linha
  genérica "Todos os .drawio correspondentes"), Fase 1.6 (`security-architecture.drawio`), Fase 4
  (`migration-gantt.drawio`, 14→13), Fase 4.3 (`coexistence-architecture.drawio`, 4→3) — DONE
- [x] **2.6** `orchestrator-tobe.md` Fase 4.5 (gate bloqueante — ponto crítico): tabela de 14
  arquivos do migration-plan reduzida a 13 (removida linha `migration-gantt.drawio`, renumerado);
  tabela de 4 arquivos da coexistence-strategy reduzida a 3 (removida
  `coexistence-architecture.drawio`); total 18→16 arquivos — DONE

## Category 3 — Schema Updates — SKIP

Nenhum schema JSON novo; este PBI só altera prosa de instrução de agentes e tabelas de gate em
Markdown.

## Category 4 — Module Registration — SKIP

Nenhum agente novo criado ou removido; nenhuma mudança em `module.yaml`.

## Category 5 — Quality Gate Checklists

- [x] **5.1** `tobe-architecture/checklists/migration-validation-gate.md`: checks 3.12/3.13/3.16
  removidos (comparação cross-formato e detecção de stub `.drawio`); Etapa 4 (nota de origem +
  tabela de completude) 14→13; Etapa 7.1 sem `migration-gantt.drawio`; Relatório de Completude e
  Output Invariant 14→13 em todos os pontos; `version` bumped `1.2.0`→`1.3.0` — DONE
- [x] **5.2** `tobe-architecture/checklists/coexistence-validation-gate.md`: check 3.2 removido
  (`.drawio` é XML válido); Etapa 4 e Relatório de Completude 4→3; `version` bumped
  `1.0.0`→`1.1.0` — DONE
- [x] **5.3** `shared/checklists/migration-design-checklist.md`: linha `B5` (Context Map Draw.io)
  removida da Seção B (5→4 artefatos, B.V5 removida, critério de aprovação atualizado); linha
  `D3` (Security Diagram Draw.io) removida da Seção D (3→2 artefatos, critério atualizado); linha
  de troubleshooting "Diagrama não renderiza" sem mais mencionar Draw.io; `version` bumped
  `1.0.0`→`1.1.0` — DONE
- [x] **5.4** `tobe-architecture/workflows/design-dotnet/steps/step-01c-security-design.md`:
  linha de output `security-architecture.drawio` e critério `AC-3` removidos; "3 arquivos"→"2
  arquivos" no Critério de Conclusão — DONE
- [x] **5.5** Órfão removido: `tobe-architecture/templates/migration-gantt-drawio.md` apagado
  (confirmado via `grep -r migration-gantt-drawio` = 0 matches restantes antes da exclusão) —
  DONE

## Category 6 — Acceptance Validation

- [x] **6.1** CA01 — os 4 agentes TO-BE não geram mais `.drawio`: `grep -ri drawio` em cada um
  dos 4 arquivos de agente → 0 matches — PASS (structural)
- [x] **6.2** CA02 — gates downstream não bloqueiam mais o pipeline: `orchestrator-tobe.md` Fase
  4.5 valida 13+3=16 arquivos (não mais 14+4=18); `migration-validation-gate.md` e
  `coexistence-validation-gate.md` reportam 13/13 e 3/3 respectivamente — PASS (structural; sem
  execução de pipeline ao vivo nesta sessão, consistente com precedente de `specs/013`)
- [x] **6.3** CA03 — geração Mermaid permanece intacta: diff de cada um dos 4 agentes revisado
  manualmente, nenhuma linha de instrução `.mmd`/Mermaid alterada além das remoções `.drawio` —
  PASS
- [x] **6.4** CA04 — escopo AS-IS preservado: `shared/drawio-governance.md` e os 4 agentes
  AS-IS de solução legada (`solution-vb.md`, `solution-cobol.md`, `solution-vbnet.md`,
  `solution-powerbuilder.md`) sem diff — PASS

## Category 7 — Documentation

- [x] **7.1** Esta documentação spec-kit (`spec.md`, `plan.md`, `tasks.md`) — DONE
- [ ] **7.2** `CHANGELOG.md` na raiz do repositório — pendente de confirmação do PBI/work item
  number com o usuário antes de commitar (Guardrail #10 do projeto).

## Completion Checklist

- [x] Confirmado, via 3 investigações diretas em paralelo, que nenhum consumidor real (Summary
  HTML) lê os `.drawio` do TO-BE antes de remover a geração
- [x] Escopo de gates downstream confirmado explicitamente com o usuário via `AskUserQuestion`
  antes de tocar em arquivos além dos 4 nomeados originalmente
- [x] Escopo de remoção de conteúdo órfão confirmado explicitamente com o usuário via
  `AskUserQuestion`
- [x] Todos os 9 arquivos afetados (4 agentes + orquestrador + 4 checklists/steps) verificados
  individualmente com `grep -ri drawio` → 0 matches após as edições
- [x] Nenhuma instrução de geração Mermaid (`.mmd`) foi alterada em nenhum dos 4 agentes
- [x] `shared/drawio-governance.md` e os agentes AS-IS de solução legada permanecem intocados
- [x] Arquivo de template órfão (`migration-gantt-drawio.md`) confirmado sem outras referências
  antes de ser apagado
- [ ] Commit ainda não realizado — aguardando confirmação do usuário (branch/PBI number) antes de
  `git add`/`git commit`, conforme Guardrail #11 do projeto
