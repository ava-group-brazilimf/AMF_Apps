# Step 01 — Validação de Inputs

## Objetivo
Verificar que todos os pré-requisitos estão disponíveis antes de iniciar a análise.

## Checklist de Validação
- [ ] Repositório Delphi acessível (read-only)
- [ ] Schema do banco de dados disponível (DDL scripts ou conexão)
- [ ] cliente designado e disponível
- [ ] trace_id gerado e propagado
- [ ] Escopo definido (todos os módulos ou lista específica)

## Inputs Esperados
```yaml
repository_path: string
legacy_technology: "delphi"
project_name: string
trace_id: string
scope_modules: string[] | "all"
```

## Ação se Falhar
Pausar workflow → notificar PM → aguardar resolução → retomar

## Output
```yaml
validation_result:
  status: "pass" | "fail"
  missing_items: string[]
  warnings: string[]
```
