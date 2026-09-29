# Especificação: {TÍTULO}

> **Spec ID**: SPEC-{WAVE}-001 · **Wave**: {wave_id} · **Feature**: {feature}
> **Fontes**: `outputs/tobe/speckit/wave-spec-manifest.json#{feature}`
> **Constituição**: outputs/tobe/speckit/constitution.md · **trace_id**: {trace_id}
> **Gerado por**: ava-speckit-specification v2.0.0 · **Data**: {data}

> Preencher TODAS as 16 seções. As seis últimas têm heading literal em inglês porque
> `readiness-gate.md` C2 as confere por glob — traduzi-las reprova o gate.

---

## 1. Objetivos Funcionais

{O que o sistema passa a fazer, em termos de negócio.}

## 2. Regras de Negócio

| ID | Descrição | Referências verificáveis | Critério de aceite |
|---|---|---|---|
| {CAP-WX-000} | {descrição} | `{arquivo-1}#{âncora}`; `{arquivo-2}#{âncora}` | {verificável} |

> A âncora é reaberta e procurada no arquivo-fonte por CHK-SK-006. Âncora inventada reprova.

## 3. Modelo de Domínio

{Entidades, agregados, value objects, invariantes.}

## 4. Fluxos de Aplicação

{Passo a passo, incluindo o caminho de erro.}

## 5. Critérios de Aceite

{Um por objetivo. Cada um vira teste.}

## 6. Tratamento de Erros

| Condição | Resposta | Código | Mensagem | Log |
|---|---|---|---|---|

## 7. Requisitos de Segurança

{Autorização, dados sensíveis, auditoria.}

## 8. Dependências

{Waves predecessoras, contratos de API e decisões da constituição. Conflitos declarados aqui.}

## 9. Casos de Borda

{O que a fonte não diz e precisa de decisão explícita, com quem decide.}

## 10. Cenários de Teste

| ID | Cenário | Dado / Quando / Então | Tipo |
|---|---|---|---|

---

## Context

{Por que esta especificação existe e onde ela se encaixa na esteira.}

## Input

{Artefatos consumidos, com caminho.}

## Processing

{Como a fonte foi interpretada; regras de desempate aplicadas.}

## Output

{Artefatos produzidos e quem os consome.}

## Examples

{Ao menos um exemplo concreto de entrada e saída esperada.}

## Failure Modes

{O que acontece quando um insumo falta, quando a fonte é ambígua, quando há conflito.}
