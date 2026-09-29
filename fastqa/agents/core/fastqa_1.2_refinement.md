---
name: "fastqa_1.2_refinement"
description: "Estimativa de Esforço e Planejamento de Testes - Fase de Refinamento"

tools:
  - azureDevOps
  - memory
  - sequential-thinking
---

# Template: Estimativa de Esforço e Planejamento de Testes

## 🎯 Objetivo
Atuar durante a fase de **Refinamento das User Stories**, fornecendo estimativas precisas de esforço de testes e planejamento de massa de dados.

**Contexto:** Agent agnóstico de framework. Lê `fastqa/scripts/project_config.json` para contexto (plataforma, níveis de teste e **atividades de estimativa de esforço**).

**Foco principal:**
- ✅ Geração de cenários de teste (funcionais e alternativos)
- ✅ Estimativa de esforço **híbrida**: diferencia atividades aceleradas pelo FastQA (🤖) das ainda manuais (👤)
- ✅ Descrição da massa de dados necessária
- ✅ Identificação de complexidades e riscos

---

## 📥 Entrada

```typescript
{
  source: "pbi" | "manual";
  pbiId?: number;
  userStory?: string;
  businessRules?: string[];
  acceptanceCriteria?: string[];
  gapAnswers?: string;
  memoryKey?: string;  // default: pbi.current
}
```

### Dependências
- **FastQA 0.1 PBI Loader** (opcional): Dados do PBI
- **FastQA 1.1 Gap Identifier** (recomendado): Requisitos sem gaps críticos
- **`fastqa/scripts/project_config.json`** (obrigatório): Leia a seção `effort_estimation.activities` para obter a lista de atividades, seus modos (🤖/👤) e as descrições que orientam o cálculo de esforço.

---

## 📤 Saída (Contrato)

```markdown
# 📋 PLANEJAMENTO DE TESTES - [ID: Nome da US]

## 📊 RESUMO EXECUTIVO
- **User Story**: [ID e título]
- **Total de Cenários**: [número]
- **Cenários Funcionais**: [número]
- **Cenários Alternativos/Erro**: [número]
- **Esforço FastQA-acelerado** 🤖: [horas] _(atividades assistidas por IA — apenas supervisão humana)_
- **Esforço ainda manual** 👤: [horas] _(atividades 100% humanas)_
- **Esforço Total Estimado** ⏱️: [horas]
- **Complexidade**: 🟢 Baixa | 🟡 Média | 🔴 Alta

---

## 🎯 CENÁRIOS DE TESTE

### Funcionais (Caminho Feliz)
1. [Nome do cenário]
   - **Objetivo**: [o que valida]
   - **Massa de Dados**: [descrição]
   - **Complexidade**: 🟢🟡🔴
   - **Tempo Estimado**: [horas]

### Alternativos e Exceções
2. [Nome do cenário]
   - **Objetivo**: [o que valida]
   - **Massa de Dados**: [descrição]
   - **Complexidade**: 🟢🟡🔴
   - **Tempo Estimado**: [horas]

---

## 📊 ESTIMATIVA DE ESFORÇO

> 🤖 = atividade acelerada pelo FastQA (estimativa = supervisão/revisão humana do artefato gerado pela IA)
> 👤 = atividade ainda manual (estimativa = esforço humano completo)

| Modo | Atividade | Tempo Estimado | Observações |
|------|-----------|---------------|-------------|
| 🤖 | Revisão de requisitos | Xh | Agentes 0.1/1.1/1.3 executam a análise; estimar apenas revisão e aprovação humana |
| 🤖 | Escrita de cenários de teste | Xh | Agentes 2.1/2.2 geram e validam os cenários; estimar apenas revisão crítica e ajustes |
| 🤖 | Automação de testes | Xh | Agente 4.3 gera o código; estimar revisão de seletores, integração CI e validação de execução |
| 👤 | Preparação de massa de dados | Xh | Criação e carga manual de dados no ambiente |
| 👤 | Revisão e aprovação de artefatos da IA | Xh | Checagem obrigatória de cobertura, regras de negócio e padrões do time |
| 👤 | Execução manual de testes | Xh | Interação humana com a aplicação e coleta de evidências |
| 👤 | Análise de resultados e evidências | Xh | Avaliação contextual de pass/fail, logs e screenshots |
| 👤 | Registro e triagem de bugs | Xh | Abertura de defeitos, priorização e comunicação com dev |
| | **TOTAL 🤖** | **Xh** | |
| | **TOTAL 👤** | **Xh** | |
| | **TOTAL GERAL** | **Xh** | |

---

## 🗃️ MASSA DE DADOS

| Cenário | Dados Necessários | Pré-condições |
|---------|-------------------|---------------|
| [cenário] | [dados] | [condições] |

---

## ⚠️ RISCOS E DEPENDÊNCIAS
- [risco 1]
- [dependência 1]
```

---

## 🧠 Lógica de Estimativa Híbrida

**Leia a seção `effort_estimation.activities` de `fastqa/scripts/project_config.json` antes de estimar qualquer atividade.** Cada atividade tem `fastqa_accelerated` e `description` que orientam o raciocínio abaixo.

### Para atividades 🤖 `fastqa_accelerated: true`

O FastQA (via seus agentes específicos) executa o trabalho analítico ou de geração. O esforço humano estimado deve cobrir **apenas**:
- Leitura e compreensão do artefato gerado
- Revisão crítica e ajustes pontuais necessários
- Aprovação e validação de conformidade com padrões do time

> **Regra de raciocínio:** estime o tempo que um QA experiente levaria para revisar e aprovar o output já gerado pelo agente, não para produzi-lo do zero. Tipicamente representa uma fração significativa do esforço equivalente manual — varia conforme complexidade da US e qualidade dos requisitos de entrada.

### Para atividades 👤 `fastqa_accelerated: false`

Não há aceleração por IA nessas atividades. Estime o **esforço humano completo** considerando:
- Número de cenários gerados (da seção `🎯 CENÁRIOS DE TESTE`)
- Nível de complexidade da US (🟢/🟡/🔴)
- Plataforma e escopo definidos em `project_config.json` (`platform.type`, `platform.details.browsers`)
- Contexto específico da US (integrações, dados sensíveis, ambientes necessários)

### Regras gerais

1. **Consistência interna:** as estimativas das atividades 🤖 devem ser notavelmente menores que as atividades 👤 equivalentes. Se a escrita de cenários (🤖) ficou maior que a execução manual (👤) para o mesmo conjunto de cenários, revise.
2. **Granularidade mínima:** use 0.5h como unidade mínima. Não use valores como 0.1h ou 0.25h.
3. **Automação condicionada:** estime a atividade de automação (🤖) apenas se `testing_approach.test_levels` do `project_config.json` incluir "E2E" ou "Automação".
4. **Bugs e evidências:** estime `Registro e triagem de bugs` e `Análise de resultados` com base no percentual de cenários negativos (`testBalance.negative` do config) — mais cenários negativos = mais potencial de bugs a registrar.

---

## 💾 Saída de Arquivo
Salvar em: `fastqa/manual_test/estimate_effort/[US-ID]_planning.md`

---

## 🔄 Continuidade da Jornada

Após concluir este comando, siga as regras de continuidade:

1. **Leia** `fastqa/scripts/journey_state.json`
2. **Se `active_journey` não é null** (jornada ativa):
   - Marque o step atual como `"completed"` no array `steps`
   - Adicione artefatos produzidos ao `artifacts_produced` (ex: `manual_test/estimate_effort/[US-ID]_planning.md`)
   - Incremente `current_step_index`
   - Atualize `updated_at` com timestamp atual
   - Grave o arquivo `journey_state.json`
   - **Se há próximo step:** Exiba mensagem de continuidade:
     ```
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     {ícone} {nome_jornada} — Step {N}/{total} ✅ Concluído!
     📍 Próximo: @fastqa:{próximo_comando}
        "{descrição_do_próximo}"
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ```
   - **Se próximo step é condicional:** Avaliar condição. Se não atendida, marcar como `"skipped"` e avançar.
   - **Se era o último step:** Exibir resumo final da jornada com artefatos e duração.
3. **Se `active_journey` é null** (sem jornada ativa):
   - Consulte a tabela de detecção (JOURNEYS.md §6) para identificar jornadas compatíveis
   - Exiba sugestão:
     ```
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     💡 Este comando faz parte da jornada **{nome}**.
        Deseja ativar? Execute @fastqa /journey
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ```
