# Step 03 — Documentação Funcional

## Objetivo
Executar Documentation AS-IS Agent para extrair requisitos, regras de negócio e fluxos.

## Agente Responsável
`ava-asis-documentation`

## Inputs
- `projects/{project_name}/outputs/asis/pattern-classifications.json` (do Step 02)
- `projects/{project_name}/outputs/asis/bounded-context-map.md` (do Step 02)

## Sequência de Execução
1. Extrair Cadeia de Valor
2. Mapear Requisitos Funcionais com critérios de aceite
3. Identificar Regras de Negócio por módulo
4. Gerar Fluxo de Telas (mapa de navegação)
5. Documentar Regras de Tela por form
6. Criar Protótipos AS-IS

## Critério de Conclusão
- business-rules.md gerado
- screen-navigation-map.md gerado
- Todos os forms principais documentados
