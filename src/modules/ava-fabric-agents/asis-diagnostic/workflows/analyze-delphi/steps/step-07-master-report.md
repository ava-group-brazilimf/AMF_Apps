# Step 07 — AS-IS Master Report

## Objetivo
Gerar o relatório executivo consolidado do diagnóstico AS-IS.

## Agente Responsável
`ava-asis-orchestrator` (consolidação final)

## Estrutura do Master Report
```markdown
# AS-IS Master Report — {Project Name}

## 1. Sumário Executivo
## 2. Arquitetura AS-IS
   - Blueprint C4 (3 níveis)
   - Padrões identificados
   - Bounded contexts
## 3. Análise Funcional
   - Cadeia de valor
   - Requisitos funcionais (total e por módulo)
   - Regras de negócio
## 4. Análise de Dados
   - Schema do banco
   - Stored procedures
   - Business logic no banco
## 5. Inventário Quantitativo
   - LOC, classes, métodos, complexidade
## 6. Segurança
   - Findings OWASP
   - PII identificado
## 7. Riscos e Gaps
   - Risk register completo
   - Score global
   -  riscos críticos
## 8. Recomendações
   - Arquitetura TO-BE sugerida
   - Próximos passos
## 9. Artefatos Entregues
   - Índice de todos os arquivos gerados
```

## Output
`projects/{project_name}/outputs/asis/AS-IS-MASTER-REPORT.md`

## Sinalização
Ao concluir → notificar Orchestrator TO-BE Agent para iniciar próxima fase.
