# Constituição do Projeto — {PROJECT_NAME}

> **trace_id**: {trace_id} · **Gerado por**: ava-speckit-constitution v1.0.0 · **Data**: {data}
> Documento governante. Entra no contexto de todo agente a jusante, inclusive de cada chamada
> de geração de código do fan-out da F4. Manter abaixo de 1.500 linhas.

## 1. Identidade do Projeto
| Campo | Valor |
|---|---|
| Projeto | {project_name} |
| Tecnologia legada | {legacy_technology} |
| Stack alvo | {backend} / {frontend} / {database} |

## 2. Princípios Arquiteturais
| # | Princípio | Justificativa | Origem |
|---|---|---|---|

## 3. Padrões de Tecnologia
| Componente | Escolha | Versão | Origem da versão |
|---|---|---|---|

> Nenhuma versão inventada. Toda linha cita a chave de `reference-architecture.yaml` ou o
> override de `project-config.yaml`.

## 4. Pacotes e Bibliotecas
| Pacote | Permitido | Motivo |
|---|---|---|

## 5. Padrões de Código
{Nomenclatura, estrutura de pastas, tratamento de erro, logging, comentários.}

## 6. Regras de Camada
| Camada | Pode importar | Não pode importar |
|---|---|---|

## 7. Requisitos Não-Funcionais
| ID | Requisito | Métrica | Valor alvo | Como medir |
|---|---|---|---|---|

> "Deve ser performático" é proibido. "p95 < 400 ms sob 200 req/s" é o formato aceito.

## 8. Requisitos de Segurança e Compliance
| ID | Requisito | Origem | Verificação |
|---|---|---|---|

## 9. Restrições de Arquitetura
| Proibição | O que fazer em vez disso |
|---|---|

## 10. Decisões Obrigatórias
| ID | Decisão | ADR | Impacto na geração de código |
|---|---|---|---|

> A última coluna tem de ser acionável sem contexto adicional.

## 11. Decisões Superadas
| ADR | Status | Não reintroduzir |
|---|---|---|

## 12. Conflitos Detectados
| Conceito | Artefatos em conflito | Divergência | Desempate |
|---|---|---|---|

## 13. Quality Gates
| Gate | Limiar | Comando |
|---|---|---|

## 14. Definition of Done Global
- [ ] {aplicável a toda task da F3S e da F4}
