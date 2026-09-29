---
template_id: integration-coupling-matrix
agent: ava-tobe-migration-plan
version: "1.0.0"
description: "Template de saída da Matriz de Acoplamento de Integrações — schema obrigatório para integration-matrix.md"
---

# Integration Coupling Matrix — Template de Saída

> **Load when**: executing Step 2 of the Execution Protocol.

```markdown
### Matriz de Acoplamento de Integrações

| Módulo | Dependências de entrada | Dependências de saída | Coupling Score | Wave sugerida |
|---|---|---|---|---|
| Módulo A | — | Módulo B, Módulo C | 2 | Wave 1 |
| Módulo B | Módulo A | Módulo D | 2 | Wave 2 |
| Módulo C | Módulo A | — | 1 | Wave 1 |
| Módulo D | Módulo B, Módulo C | Módulo E | 3 | Wave 3 |
| Módulo E | Módulo D | — | 1 | Wave 3 |

> **Coupling Score** = n.º de dependências de entrada + n.º de dependências de saída.
> Sequência de waves: determinada pelo algoritmo determinístico do Step 4 (Priority Score → Risco Transacional → Complexidade Funcional → Coupling Score → ordem alfabética).
> O Coupling Score é usado como **critério de desempate técnico** (4º nível), não como critério primário de ordenação.
>
> **Enforcement obrigatório**:
> - Colunas `Dependências de entrada` e `Dependências de saída` são **DISTINTAS** — proibido usar coluna única "# Dependências".
> - `Wave sugerida` deve ser preenchida por linha, após execução do Step 4.
> - Score = 0 indica módulo isolado (candidato à Wave 1).
```
