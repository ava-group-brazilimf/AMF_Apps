# Plano de Implementação: {TÍTULO}

> **Plan ID**: PLAN-{SPEC}-001 · **Spec**: outputs/tobe/speckit/specs/{feature}/spec.md
> **Migration Wave**: {wave_id} · **Ordem**: {migration_wave_order}
> **Constituição**: outputs/tobe/speckit/constitution.md · **trace_id**: {trace_id}
> **Gerado por**: ava-speckit-planning v4.0.0 · **Data**: {data}
> Derivado de `plan-graph.json` — grupos, arquivos e dependências não são editados à mão.

## 1. Estratégia de Implementação
{Ordem de construção e por quê.}

## 2. Mapeamento Arquitetural
| Elemento da spec | Camada | Módulo |
|---|---|---|

## 3. Quebra em Módulos
| Grupo | Stack alvo | Escopo | Depende de | Verificação |
|---|---|---|---|---|

> Base do fan-out da F4. Cada grupo implementável e verificável isoladamente, com no máximo
> ~25 arquivos — o teto de saída de 128k tokens é real e já custou uma esteira inteira.

## 4. Impacto Arquivo a Arquivo
| Caminho | Ação | Grupo | Tipo | Responsabilidade | Origem na spec | Produz | Consome |
|---|---|---|---|---|---|---|---|

> Cada origem vira `{artifact, anchor}` em `source_refs[]` do `plan-graph.json` v3.

## 5. Pontos de Integração
{O que este plano consome de outros e o que expõe.}

## 6. Dependências de API
| Operação | Consome ou implementa | Contrato de origem |
|---|---|---|

## 7. Mudanças de Banco
| Objeto | Mudança | Migração | Ordem |
|---|---|---|---|

## 8. Estratégia de Teste
| Cenário da spec | Tipo | Onde |
|---|---|---|

## 9. Ordem e Dependências
Formato obrigatório e compacto (sem ASCII-art):

### 9.1 Tabela de Dependências Exatas
| Grupo | Depende de |
|---|---|

### 9.2 Ordem Topológica por Wave
| Wave | Grupos | Paralelizável |
|---|---|---|

> Regras da seção 9:
> - Usar somente as duas tabelas acima (9.1 e 9.2).
> - Não usar diagramas textuais com box-drawing (`─│├└┌┐┬┴┼►`) ou árvores ASCII.
> - Os IDs de grupo e dependências devem ser idênticos ao `plan-graph.json`.

## 10. Riscos de Implementação
| Risco | Sinal que denuncia | Mitigação |
|---|---|---|
