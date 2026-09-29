# Step 02 — Análise de Código

## Objetivo
Executar AS-IS Solution Agent (Delphi) para mapear arquitetura, padrões e bounded contexts.

## Agente Responsável
`ava-asis-solution-delphi`

## Sequência de Execução
1. Glob all `.pas`, `.dfm`, `.dpr`, `.dpk` files
2. Classificar por tipo (Form, DataModule, Unit, Package)
3. Aplicar Pattern Classifier por arquivo
4. Construir grafo de dependências
5. Gerar diagramas C4 (contexto → container → componente)
6. Inferir bounded contexts
7. Mapear APIs e estrutura de dados

## Critério de Conclusão
- Todos os arquivos do escopo classificados
- C4 Blueprint gerado nos 3 níveis
- Bounded Context Map produzido
- AnalysisReport.json salvo em `projects/{project_name}/outputs/asis/`

## Human Gate
Não requerido neste step. Prosseguir automaticamente para Step 03.
