---
name: "fastqa_2.5_ac_scope_analyzer"
description: "Analisador de Escopo de Critérios de Aceite — Triagem rápida de ACs para geração de testes"
version: "1.0"

tools:
  - memory
  - sequential-thinking
---

# Template: Analisador de Escopo de Critérios de Aceite (AC Scope Analyzer)

## 🎯 Objetivo
Analisar uma User Story e seus Critérios de Aceite (ACs) para **classificar rapidamente** quais ACs devem ser cobertos na geração de casos de teste e quais podem ser excluídos ou adiados — otimizando o esforço de QA sem perder cobertura crítica.

**Contexto:** Este template é executado **antes** da geração de cenários Gherkin (fastqa_2.1) para definir o escopo de teste efetivo. Prioriza velocidade de análise e clareza na saída.

**Foco principal:**
- ✅ Identificação imediata de ACs explicitamente excluídos pela US
- ✅ **Sugestão de itens ou sub-itens dentro de ACs** que não são críticos para geração de testes (análise granular)
- ✅ Classificação de criticidade de cada AC (Crítico / Importante / Baixa Prioridade)
- ✅ Recomendação clara de escopo para geração de testes
- ✅ Formato de saída consumível por agentes de IA e humanos
- ❌ Não realiza análise de gaps (use `fastqa_1.1_gap_identifier` para isso)
- ❌ Não gera cenários de teste (use `fastqa_2.1_gherkin_writer` após esta análise)

---

## 📥 Entrada

### Fonte de Dados
A User Story pode ser fornecida de 3 formas:

1. **Arquivo local:** Caminho para arquivo `.md` na pasta `fastqa/manual_test/US/`
2. **Conteúdo colado no chat:** Texto da US diretamente na conversa
3. **Referência por ID:** Ex: `US10.3.4` → busca automática em `fastqa/manual_test/US/`

```typescript
{
  source: "file" | "chat" | "id";
  filePath?: string;        // se source = "file"
  content?: string;         // se source = "chat"
  usId?: string;            // se source = "id" → busca em fastqa/manual_test/US/
  behaviorsFile?: string;   // (opcional) caminho para [US-ID]_behaviors.md do fastqa_1.4
}
```

### Enriquecimento com Behaviors (quando behaviorsFile fornecido)
Se `behaviorsFile` for fornecido, o analyzer enriquece a classificação de criticidade:
- **AC mapeia para BHV de Fluxo Principal** → automaticamente 🔴 Crítico
- **AC mapeia apenas para BHVs de Fluxo Alternativo** → mínimo 🟡 Importante
- **AC mapeia apenas para BHVs de Fluxo de Exceção** → avaliar entre 🟡 Importante e 🔵 Baixa Prioridade
- Incluir coluna `BHV-IDs` na Matriz de Classificação Completa

---

## 📤 Saída (Contrato)

O relatório deve seguir **exatamente** este formato para garantir consumo por agentes de IA:

```markdown
# 🔍 Análise de Escopo de ACs — [US-ID]: [Nome da US]

**Data:** [YYYY-MM-DD]
**Analista:** FastQA AC Scope Analyzer v1.0

---

## 📊 Resumo Executivo

| Métrica | Valor |
|---------|-------|
| Total de ACs | [número] |
| ACs no escopo de testes | [número] |
| ACs excluídos (pela US) | [número] |
| ACs baixa prioridade | [número] |
| Cobertura recomendada | [percentual]% |

---

## 🚫 ACs Excluídos (Explícito pela US)

Critérios que a própria US declara como fora do escopo de validação QA.

| AC | Item | Motivo de Exclusão (citação da US) |
|----|------|------------------------------------|
| [AC-ID] | [descrição do item] | "[trecho exato da US que exclui]" |

---

## ✅ ACs no Escopo de Testes (Recomendados)

### 🔴 Críticos — Devem ser testados obrigatoriamente

| AC | Descrição | Justificativa |
|----|-----------|---------------|
| [AC-ID] | [resumo] | [por que é crítico] |

### 🟡 Importantes — Recomendados para cobertura completa

| AC | Descrição | Justificativa |
|----|-----------|---------------|
| [AC-ID] | [resumo] | [por que é importante] |

---

## 🔵 ACs de Baixa Prioridade (Podem ser adiados)

Critérios que não afetam a funcionalidade principal e podem ser validados em ciclo posterior.

| AC | Descrição | Motivo para Baixa Prioridade |
|----|-----------|------------------------------|
| [AC-ID] | [resumo] | [justificativa] |

---

## 📋 Matriz de Classificação Completa

| AC | Classificação | No Escopo? | BHV-IDs | Observações |
|----|---------------|------------|---------|-------------|
| [AC-ID] | 🔴 Crítico / 🟡 Importante / 🔵 Baixa / 🚫 Excluído | ✅/❌ | [BHV-001, BHV-002] | [notas] |

---

## 💡 Sugestões de Exclusão Parcial (Sub-itens de ACs)

> Critérios que **não são excluídos por inteiro**, mas contêm itens ou sub-itens específicos que **não são críticos o suficiente** para justificar geração de cenários de teste dedicados. O analista de QA pode optar por não cobri-los sem impacto significativo na qualidade.

| AC | Sub-item | Descrição | Motivo da Sugestão | Risco de Não Testar |
|----|----------|-----------|--------------------|-----------------------|
| [AC-ID] | [item/sub-item específico] | [o que faz] | [por que pode ser dispensado] | 🟢 Baixo / 🟡 Mínimo |

---

## 💡 Recomendações para Geração de Testes

1. [Recomendação específica para o gherkin_writer]
2. [ACs que devem ser consolidados em Scenario Outline]
3. [Sugestão de priorização na automação]
4. [Sub-itens sugeridos para exclusão e impacto na cobertura]
```

---

## 🧠 Regras de Classificação

### 🚫 EXCLUÍDO — Detecção Automática
Marcadores que indicam exclusão explícita na US:
- `"Não será validado em QA"`
- `"Não será revalidado por testes de QA"`
- `"não será validado endpoint por QA"`
- `"Não será relavidado por testes de QA"` (variantes ortográficas)
- `"fora de escopo de QA"`
- `"não precisa ser testado"`

**Matching Semântico Complementar:** Além dos marcadores literáis acima, aplicar matching semântico para detectar variações linguísticas equivalentes:
- Sinonímias: "dispensar validação", "sem necessidade de teste", "excluído do escopo de testes"
- Negações compostas: "este critério não requer verificação de QA"
- Variações de conjugação: "não serão validados", "não deverá ser testado"
- Se houver dúvida semântica, classificar como 🟡 Importante (não excluir)

**Ação:** Extrair o trecho exato da US como evidência de exclusão.

### 🔴 CRÍTICO — Impacto direto no usuário
- Fluxos principais (happy path) da funcionalidade
- Validações de campos obrigatórios
- Integrações essenciais (ex: busca de CEP, salvamento de dados)
- Confirmação/feedback de ações (sucesso/erro)
- Regras de negócio core (ex: máximo de convênios, convênio principal obrigatório)
- Controle de acesso e autenticação

### 🟡 IMPORTANTE — Complementa a experiência
- Validações de formato e limites de caracteres
- Fluxos alternativos (cancelar, descartar)
- Componentes interativos específicos (modal de confirmação, tooltips)
- Upload de arquivos com validação de tipo/tamanho
- Casos de borda (edge cases)

### 🔵 BAIXA PRIORIDADE — Não afeta funcionalidade core
- Responsividade e layout (breakpoints mobile/tablet/desktop)
- Comportamentos visuais puros (cores, estilos, posicionamento de badges)
- Funcionalidades de leitura já cobertas por outra US
- Reordenação de elementos visuais entre breakpoints

### 💡 SUGESTÃO DE EXCLUSÃO PARCIAL — Sub-itens dentro de ACs

Além de ACs inteiros, o analyzer deve identificar **partes específicas** de ACs que podem ser dispensadas. Aplicar quando:

- 🟢 O sub-item é **redundância funcional** já coberta em outro AC (ex: validação de obrigatoriedade já testada no AC de validações)
- 🟢 O sub-item é **comportamento implícito do framework/componente** (ex: máscara de input que é comportamento nativo do componente UI)
- 🟢 O sub-item descreve **detalhamento visual/estético** dentro de um AC funcional (ex: "fundo cinza" em campos readonly)
- 🟢 O sub-item é **configuração de infraestrutura/backend** que não é observável pelo usuário final (ex: "enviar via endpoint PATCH separado")
- 🟢 O sub-item é **observação/nota informativa** ("Obs:", "OBS:") que altera escopo de **outra** US, não desta
- 🟡 O sub-item é **tooltips ou microcopy** que não impactam a jornada funcional

**Classificação de risco ao não testar o sub-item:**
| Risco | Descrição |
|-------|----------|
| 🟢 Baixo | Sem impacto funcional; puramente visual ou redundante |
| 🟡 Mínimo | Impacto perceptual pequeno; não bloqueia o usuário |

---

## ⚡ Fluxo de Execução (Otimizado para Velocidade)

O template é projetado para análise rápida em **3 passos**:

### Passo 1 — Scan de Exclusões (< 10 segundos)
Buscar marcadores de exclusão no texto da US usando as expressões da seção "Detecção Automática".
Extrair e catalogar imediatamente.

### Passo 2 — Classificação por Impacto (< 30 segundos)
Para cada AC restante, aplicar as regras de classificação:
1. É fluxo principal ou regra de negócio core? → 🔴 Crítico
2. Complementa experiência ou é validação de campo? → 🟡 Importante
3. É puramente visual/layout ou redundante com outra US? → 🔵 Baixa Prioridade

### Passo 2.1 — Varredura de Sub-itens Dispensáveis (< 20 segundos)
Para cada AC classificado como 🔴 Crítico ou 🟡 Importante, verificar se há **sub-itens internos** que podem ser dispensados:
- Ler cada item numerado/bullet dentro do AC
- Aplicar as regras de "Sugestão de Exclusão Parcial"
- Catalogar sub-itens dispensáveis com risco e justificativa

### Passo 3 — Geração do Relatório (< 15 segundos)
Montar saída no formato do contrato, incluindo a matriz completa, sugestões de exclusão parcial e recomendações.

---

## 💾 Saída de Arquivo

Salvar em: `fastqa/manual_test/requirements_analysis/[US-ID]_ac_scope.md`

**Exemplo:** `fastqa/manual_test/requirements_analysis/10-3-4_ac_scope.md`

---

## � Contrato Inter-Agent

| Campo | Valor |
|-------|-------|
| **upstream_artifact** | `fastqa/manual_test/US/[US-ID].md` + (opcional) `fastqa/manual_test/behavior_analysis/[US-ID]_behaviors.md` |
| **downstream_artifact** | `fastqa/manual_test/requirements_analysis/[US-ID]_ac_scope.md` |
| **required_fields** | Matriz de Classificação Completa com `Classificação` e `No Escopo?` preenchidos |
| **readiness_gate** | Sempre `ready` (este step é não-obrigatório; a ausência do artefato aciona fallback no 2.1) |

### 🔄 Fallback quando este step é pulado
O `fastqa_2.1_gherkin_writer` tem regra de fallback: se `[US-ID]_ac_scope.md` **não existe**, o writer assume todos os ACs como 🟡 Importante (sem exclusões, sem tags `@low-priority`). O pipeline não quebra.

---

## �🔗 Integração com Outros Templates

```
[User Story]
     ↓
fastqa_2.5_ac_scope_analyzer  ← ESTE TEMPLATE
     ↓ (escopo definido)
fastqa_2.1_gherkin_writer      → gera cenários apenas dos ACs no escopo
     ↓
fastqa_2.2_validator           → valida cobertura considerando escopo
```

**Uso no gherkin_writer:** Ao gerar cenários, o writer deve consultar o arquivo `[US-ID]_ac_scope.md` para:
- Ignorar ACs marcados como 🚫 Excluído
- Priorizar cenários de ACs 🔴 Críticos
- Incluir ACs 🟡 Importantes na cobertura padrão
- Marcar ACs 🔵 Baixa Prioridade como opcionais (tag `@low-priority`)

---

## 🔄 Continuidade da Jornada

Após concluir este comando, siga as regras de continuidade:

1. **Leia** `fastqa/scripts/journey_state.json`
2. **Se `active_journey` não é null** (jornada ativa):
   - Marque o step atual como `"completed"` no array `steps`
   - Adicione artefatos produzidos ao `artifacts_produced` (ex: `manual_test/test_cases/[US-ID]_ac_scope.md`)
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
