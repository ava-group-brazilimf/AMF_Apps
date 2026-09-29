# Step 01c-security-design — Security Architecture Design TO-BE

## Objetivo
Executar a Fase 1.6 da esteira TO-BE: gerar a Security Architecture completa da solução alvo,
traduzindo os achados de segurança AS-IS em controles TO-BE mapeados e documentados.
Implementa o protocolo de remediação Z-curve controlado por `skip_z-curve-remediation`.

## Placeholder Guard
1. Ler `projects/{project_name}/context/project-config.yaml` → `security_enabled_tobe` (default: `false` se ausente).
2. SE `security_enabled_tobe == false`:
   - Emitir: `⚠️ [SECURITY PLACEHOLDER] Step 01c-security-design SKIPPED — security_enabled_tobe=false. Segurança TO-BE permanece como placeholder; pipeline continua sem bloqueio.`
   - NÃO verificar os gates de entrada abaixo, NÃO ler inputs de segurança, NÃO invocar `agents/security-design-tobe.md`.
   - Criar arquivo placeholder em `projects/{project_name}/outputs/tobe/docs/security-architecture.md` (se ainda não existir) com conteúdo mínimo:
     ```markdown
     # Security Architecture TO-BE — PLACEHOLDER

     > ⚠️ Este artefato foi gerado como **placeholder** porque `security_enabled_tobe: false` no `project-config.yaml`.
     > A fase de Security Architecture Design (Fase 1.6) foi intencionalmente desabilitada; o pipeline continua sem bloqueio.
     > Para executar a análise completa de segurança, defina `security_enabled_tobe: true` e reexecute a fase.
     ```
   - Registrar conclusão do step com status `SKIPPED` e prosseguir para Fase 2.
3. SENÃO (`security_enabled_tobe == true`): prosseguir com o fluxo abaixo.

## Posição na Esteira
```
Fase 0    — ADR Generation          (adr-tobe)
Fase 1    — Blueprint + BCs         (architecture-design-tobe: CB → BC → TD)
Fase 1.5  — DB Design TO-BE         (database-design-tobe)
Fase 1.6  — Security Architecture   ← ESTE STEP
Fase 2    — Tech Framework          (architecture-technical-tobe: SS → NP → CS → QG → TF)
```

## Gate de Entrada (verificar antes de iniciar)
- [ ] `projects/{project_name}/outputs/tobe/docs/decisions/ADR-003-security.md` existe
- [ ] `projects/{project_name}/outputs/asis/security-map.md` existe
- [ ] `projects/{project_name}/outputs/asis/vulnerabilities.md` existe
- Se ADR-003 ausente → **interromper** e alertar: "Execute a Fase 0 (adr-tobe) antes de prosseguir"

## Parâmetro de Controle
`skip_z-curve-remediation`:
1. Verificar se foi passado explicitamente pelo Orchestrator
2. Fallback: `project-config.yaml → tobe_pipeline.skip_z_curve_remediation` (default: `false`)
3. Se `true` → logar: `⚠️ Z-curve remediation SKIPPED (skip_z-curve-remediation: true)`

## Agente Responsável
`agents/security-design-tobe.md`

## Inputs
| Prioridade | Fonte | Path |
|---|---|---|
| 1 | ADR-003 Security (Gate) | `projects/{project_name}/outputs/tobe/docs/decisions/ADR-003-security.md` |
| 2 | `project-config.yaml` | `projects/{project_name}/context/project-config.yaml` |
| 3 | AS-IS Security Map | `projects/{project_name}/outputs/asis/security-map.md` |
| 4 | AS-IS Vulnerabilities | `projects/{project_name}/outputs/asis/vulnerabilities.md` |
| 5 | AS-IS Compliance Gaps | `projects/{project_name}/outputs/asis/compliance-gaps.md` |
| 6 | AS-IS Gap Register | `projects/{project_name}/outputs/asis/gap-register.json` |
| 7 | Architecture Blueprint | `projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md` |
| 8 | ADR-008 Audit Log | `projects/{project_name}/outputs/tobe/docs/decisions/ADR-008-audit-log.md` |
| 9 | ADR-004 Backend | `projects/{project_name}/outputs/tobe/docs/decisions/ADR-004-backend.md` |

## Output Files (checklist)

| # | Arquivo | Descrição |
|---|---|---|
| 1 | `projects/{project_name}/outputs/tobe/docs/security-architecture.md` | Documento completo (15 seções obrigatórias) |
| 2 | `projects/{project_name}/outputs/tobe/diagrams/security-architecture.mmd` | Diagrama Mermaid `flowchart TB` |

## Acceptance Criteria

### AC-1: `security-architecture.md`
- [ ] Arquivo criado em `projects/{project_name}/outputs/tobe/docs/`
- [ ] TODAS as 15 seções presentes com conteúdo substantivo (sem placeholders)
- [ ] Seção 1: `trace_id` presente, ADR-003 e ADR-008 referenciados, Security Lead identificado
- [ ] Seção 12: mapeamento de TODOS os V-01..V-13 (linha para cada ID)
- [ ] Seção 12: cada linha tem Vuln ID, OWASP Category, AS-IS Finding, TO-BE Control, Implementation Layer, ADR Reference, Status
- [ ] Seção 15: comportamento documentado para `skip_z-curve-remediation: true` E `false`
- [ ] Nenhum valor hardcoded (auth provider, framework version, security tool)
- [ ] ADR-003 não contradito em nenhuma seção

### AC-2: `security-architecture.mmd`
- [ ] Arquivo criado em `projects/{project_name}/outputs/tobe/diagrams/`
- [ ] Começa com `flowchart TB`
- [ ] IDs de nós: apenas `[A-Za-z0-9_]`
- [ ] Máximo 2 níveis de subgraph
- [ ] Todos os 8 nós obrigatórios presentes (Client, Gateway, Auth, Authz, App, Data, Secrets, Observability)
- [ ] Sintaxe Mermaid v11.14.0 válida

### AC-3: Z-Curve Behavior
- [ ] Se `skip_z-curve-remediation: false` e UNRESOLVED CRITICAL/HIGH → loop ativado (SecurityAgent → DeveloperAgent)
- [ ] Se `skip_z-curve-remediation: true` → log `⚠️ Z-curve remediation SKIPPED` na saída; todos os achados reportados
- [ ] Máximo de 3 iterações antes de escalar ao usuário

## Anti-Regressão
- [ ] Nenhum arquivo em `outputs/asis/` foi modificado
- [ ] ADR-003 não foi modificado

## Critério de Conclusão
- Todos os 2 arquivos gerados e salvos nos paths corretos
- Validation Gate do agente `security-design-tobe.md` executado e aprovado
- Agente reportou conclusão ao Orchestrator TO-BE com status `FASE_1.6: COMPLETE` (ou `BLOCKED` se Z-curve ativo)
