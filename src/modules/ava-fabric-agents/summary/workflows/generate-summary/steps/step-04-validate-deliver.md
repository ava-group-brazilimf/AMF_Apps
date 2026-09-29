# Step 04 — Validação & Entrega

## Objetivo

Validar o HTML gerado, confirmar o estado padrão em inglês, salvar todos os
arquivos de saída e notificar o usuário. A validação do idioma padrão não deve
avaliar a visão em português alcançada somente por troca manual no seletor PT/EN.

## Ações

### 4.1 — Validar placeholders residuais

```
Grep "{{" em HTML_CONTENT
→ Listar todos os placeholders não substituídos
→ Registrar todos os placeholders não resolvidos
→ NÃO removê-los silenciosamente
→ Se placeholders críticos (layout / headers):
     considerar geração inválida
→ Registrar lista de campos não resolvidos no summary-data.json
```

### 4.2 — Verificar seções vazias

```
Para cada seção major (s-kpis, s-risks, s-phases, s-asis-arch, ...):
  Verificar se tem pelo menos 1 dado real (não "N/D" ou "Pendente")
→ Gerar lista de seções sem dados para o index.md
```

### 4.3 — Garantir autocontenção

```
Verificar que o HTML não contém referências externas:
  - Nenhum <link href="http...">
  - Nenhum <script src="http...">
  - Nenhuma @import de CDN
O template já é autocontido — esta verificação é uma salvaguarda.
```

### 4.3b — Garantir uso do template oficial

```
Validar que o HTML final contém a assinatura:
  "AVA Fabric Summary Template v1.0"
Se não contiver:
  - considerar saída inválida
  - voltar ao Step 03 e regenerar **apenas uma vez** a partir de:
    src/modules/ava-fabric-agents/summary/templates/html/
summary-template.html


Regra adicional:
  - NUNCA copiar/reutilizar HTML de summary de outro projeto.
  - Sempre gerar novo arquivo para o project_name atual.
```

### 4.4 — Criar diretório de saída

```
Bash: mkdir -p projects/{project_name}/outputs/summary/
```

### 4.5 — Salvar HTML

```
Write: projects/{project_name}/outputs/summary/{filename}.html
Conteúdo: HTML_CONTENT (string final com todos os dados injetados)
```

### 4.6 — Salvar summary-data.json

```
Write: projects/{project_name}/outputs/summary/summary-data.json
Conteúdo: objeto JSON com todos os dados extraídos + metadados:
{
  "generated_at": "...",
  "trace_id": "...",
  "html_filename": "...",
  "agents_ok": N,
  "agents_err": N,
  "total_artifacts": N,
  "sections_with_data": N,
  "sections_pending": N,
  "unresolved_placeholders": [...],
  "data": { ... }   // dados completos do Step 02
}
```

### 4.7 — Gerar index.md

```
Write: projects/{project_name}/outputs/summary/index.md
Conteúdo:
---
summary_html: "{filename}.html"
generated_at: "..."
project: "..."
agents_ok: N/{effective_total}
artifacts: N
---

# AVA Fabric Summary — {PROJECT_NAME}

Gerado em: {TIMESTAMP}
HTML: [{filename}](./{filename})

## Cobertura por Fase
| Fase | Agentes Executados | Artefatos |
|------|--------------------|-----------|
| F1 AS-IS        | X/14 | Y |
| F2 TO-BE        | X/18 | Y |
| F3 Protótipo    | X/1  | Y |
| F4 Stack        | X/11 | Y |
| F5 QA           | X/12 | Y |
| F6 DevOps       | X/9  | Y |
| F7 Entregáveis  | X/7  | Y |

## Campos sem dados ({{placeholders}} não resolvidos)
{lista de campos}

## Próximos passos
{lista de fases pendentes com trigger codes}
```

### 4.8 — Atualizar shared-context.md

```
Edit: projects/{project_name}/context/shared-context.md
Adicionar ao final (ou atualizar seção existente):

## Summary Report
- **HTML**: projects/{project_name}/outputs/summary/{filename}.html
- **Gerado em**: {TIMESTAMP}
- **Agentes com dados**: {agents_ok}/{effective_total}
- **Artefatos linkados**: {total_artifacts}
```

### 4.9 — Relatório final ao usuário

```
✅ AVA Fabric Summary gerado com sucesso!

📄 Arquivo:     projects/{project_name}/outputs/summary/{filename}.html
📊 Dados:       projects/{project_name}/outputs/summary/summary-data.json
📋 Índice:      projects/{project_name}/outputs/summary/index.md

📈 Estatísticas:
   Agentes com dados:     {agents_ok}/{effective_total} ({exec_pct}%)
   Artefatos linkados:    {total_artifacts}
   Seções com dados:      {sections_with_data}
   Seções pendentes:      {sections_pending}
   Tamanho do HTML:       {html_size} KB

{se sections_pending > 0:}
⚠️  Seções pendentes ({sections_pending}):
   {lista das fases não executadas com seus trigger codes}
   → Execute os workflows correspondentes e rode `GS` novamente para atualizar.

Para visualizar: abra o arquivo HTML no browser.
```

## Critério de Conclusão

- AVA-FABRIC-SUMMARY-\*.html salvo
- HTML válido e assinado
- HTML contém pelo menos:
  - 1 seção major com dados reais
  - 1 grid ou tabela populada
  - 1 bloco de navegação ativo
- Tamanho do HTML:
  - heurístico (> 30KB recomendado)
  - não bloqueante isoladamente

## Em caso de erro na escrita

```
Se Write falhar por permissão:
  → Tentar Bash: cp /tmp/summary.html projects/{project_name}/
outputs/summary/
→ Se ainda falhar:
   Exibir detalhes SOMENTE para fins de diagnóstico, desde que:
     - esteja explicitamente marcado como ERRO
     - esteja claramente rotulado como SAÍDA NÃO VÁLIDA
     - não seja considerado entrega final
     - não marque a execução como concluída
```
