# Step 06 — Human Approval Gate

## Objetivo
Apresentar o diagnóstico consolidado ao responsável técnico do cliente para aprovação.

## Responsável pela Aprovação
- Tech Lead ou CTO do cliente
- PM da fábrica

## O que é Apresentado
1. AS-IS Architecture Blueprint
2. Risk Register com score global
3. Gaps identificados
4. Recomendação de arquitetura TO-BE (preview)

## SLA
- Prazo para resposta: 24h
- Se sem resposta: escalar para PM → sponsor do cliente
- Se recusa: revisar com SME → re-submeter

## Critérios de Aprovação
- Stakeholder confirma que o diagnóstico reflete a realidade do sistema
- Risk register revisado e aceito
- Próxima fase (TO-BE) autorizada

## Outputs
```yaml
gate_result:
  status: "approved" | "rejected" | "revision_requested"
  reviewer: string
  comments: string
  approved_at: timestamp
```
