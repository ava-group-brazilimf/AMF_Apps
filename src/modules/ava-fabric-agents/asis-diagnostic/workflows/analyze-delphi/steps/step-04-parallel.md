# Step 04 — Análises Paralelas (DB + Security + Inventory)

## Objetivo
Executar análises paralelas independentes para maximizar eficiência.

## Agentes em Paralelo

### 4A — DB Analyzer
Agente: `ava-asis-db-analyzer`
- Detectar SGBD → delegar para skill específica
- Extrair schema, SPs, triggers, índices
- Gerar ER diagram
- Identificar business logic no banco

### 4B — Security Review
Agente: `ava-asis-security-review`
- OWASP scan no código
- Detectar credenciais hardcoded
- Mapear PII e dados sensíveis
- Gerar security map

### 4C — Inventory
Agente: `ava-asis-inventory`
- Contar LOC, classes, métodos
- Calcular complexidade ciclomática
- Mapear camadas e módulos
- Gerar matriz de acoplamento

## Sincronização
Todos os 4 devem completar antes do Step 05.
Se qualquer um falhar → retentativa (max 3) → escalação se persistir.
