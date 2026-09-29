---
template_id: migration-wave
agent: ava-tobe-migration-plan
version: "1.0.0"
description: "Template canônico de wave individual — schema obrigatório para cada wave em wave-plan.md"
---

# Migration Wave Template (Enhanced)

> **Load when**: executing Steps 4–7 of the Execution Protocol, when generating `wave-plan.md`.

```markdown
## Wave {{N}}: {{Nome da Wave}}

| Campo | Valor |
|---|---|
| **Módulos incluídos** | [lista de bounded contexts] |
| **T-Shirt Size** | XS / S / M / L / XL |
| **Justificativa do T-Shirt** | Dimensão determinante: [qual foi e por quê] |
| **Coupling Score acumulado** | N (soma dos scores dos módulos da wave) |
| **Integrações externas** | [lista] |
| **Dependências de waves anteriores** | Wave N-1, Wave N-2 |
| **Tempo IA estimado** ⚠️ OBRIGATÓRIO | X horas — derivado da tabela de benchmarks pelo T-shirt da wave |
| **Tempo manual estimado** ⚠️ OBRIGATÓRIO | Y horas — derivado da tabela de benchmarks pelo T-shirt da wave |
| **Tempo total estimado** ⚠️ OBRIGATÓRIO | Z horas (= IA + Manual) |
| **Feature Flag** | {{NomeDaFlag}} |

### Gap-List de Remediação Manual

> Itens que a IA **não** executa automaticamente nesta wave. Todos devem ser concluídos antes dos Critérios de Aceite.
> **Colunas obrigatórias**: `Motivo técnico`, `Responsável sugerido` e `Impacto se omitido` devem estar preenchidas.
> **Valores aceitos para `Responsável sugerido`**: `Dev` · `DevOps` · `QA` · `BA` · `Legal` · `Security` · `A definir até {data}`.
> Campo em branco **não é aceito**. `A definir` sem data **não é aceito**.

| # | Item | Motivo técnico | Responsável sugerido | Impacto se omitido |
|---|---|---|---|---|
| 1 | [item] | [motivo] | Dev \| DevOps \| QA \| BA \| Legal \| Security \| A definir até {data} | Crítico / Alto / Médio |

### Critérios de Aceite (obrigatório antes de avançar para próxima wave)

- [ ] Cobertura de testes ≥ 80 %
- [ ] Zero findings Critical/High no SonarQube
- [ ] Paridade funcional validada pelo cliente
- [ ] Performance igual ou melhor que AS-IS (p95 latência)
- [ ] Security scan OWASP sem Critical
- [ ] Todos os itens da Gap-List desta wave concluídos e evidenciados

### Rollback Strategy

[Descrição detalhada de como reverter esta wave; inclui feature flag de desativação e janela de rollback]
```
