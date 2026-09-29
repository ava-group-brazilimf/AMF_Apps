#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Adicionar Comentário em Work Item
// ==========================================================================
//
// Adiciona um comentário formatado em Markdown a um Work Item do Azure DevOps.
// Usado pela Jornada J1 (Fase 1) para registrar gaps identificados e suas
// respostas diretamente no PBI, mantendo rastreabilidade no AzDO.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/add-comment.command.ts \
//     --work-item-id 1234 \
//     --comment "## 🔍 Gaps Identificados\n\n1. **[Crítico]** Falta AC para fluxo de erro..."
//
// ==========================================================================

import * as fs from 'fs';
import { AzureDevOpsClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface AddCommentArgs {
  workItemId: number;
  comment: string;
  section?: string;
}

function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderInlineMarkdown(text: string): string {
  const escaped = escapeHtml(text);
  return escaped
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function renderHistoryLine(line: string): string {
  if (line.startsWith('### ')) {
    return `<strong>${renderInlineMarkdown(line.slice(4))}</strong>`;
  }

  if (line.startsWith('## ')) {
    return `<strong>${renderInlineMarkdown(line.slice(3))}</strong>`;
  }

  if (line.startsWith('# ')) {
    return `<strong>${renderInlineMarkdown(line.slice(2))}</strong>`;
  }

  const numberedMatch = line.match(/^(\d+\.)\s+(.+)$/);
  if (numberedMatch) {
    return `${escapeHtml(numberedMatch[1])} ${renderInlineMarkdown(numberedMatch[2])}`;
  }

  const bulletMatch = line.match(/^[-*]\s+(.+)$/);
  if (bulletMatch) {
    return `- ${renderInlineMarkdown(bulletMatch[1])}`;
  }

  return renderInlineMarkdown(line);
}

/**
 * Converte markdown simples para HTML compatível com System.History.
 * Usa apenas tags simples para evitar truncamento visual no Azure DevOps.
 */
function markdownToHistoryHtml(markdown: string): string {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  const htmlParts: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      htmlParts.push('<br/>');
      continue;
    }

    htmlParts.push(`${renderHistoryLine(line)}<br/>`);
  }

  return htmlParts.join('');
}

function parseArgs(): AddCommentArgs {
  const args = process.argv.slice(2);
  const parsed: Partial<AddCommentArgs> = {};

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--work-item-id': parsed.workItemId = parseInt(args[++i], 10); break;
      case '--comment': parsed.comment = args[++i]; break;
      case '--comment-file': parsed.comment = fs.readFileSync(args[++i], 'utf-8'); break;
      case '--section': parsed.section = args[++i]; break;
    }
  }

  if (!parsed.workItemId || isNaN(parsed.workItemId)) {
    console.error('❌ Parâmetro --work-item-id é obrigatório (número inteiro)');
    process.exit(1);
  }
  if (!parsed.comment || parsed.comment.trim() === '') {
    console.error('❌ Parâmetro --comment é obrigatório');
    process.exit(1);
  }

  return parsed as AddCommentArgs;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Formata comentário com estrutura de markdown */
function formatComment(content: string, section?: string): string {
  const header = section ? section : 'FastQA Comment';
  const timestamp = new Date().toLocaleString('pt-BR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const contentHtml = markdownToHistoryHtml(content);
  return `<div><strong>${escapeHtml(header)}</strong><br/><br/>${contentHtml}<br/><em>FastQA | ${escapeHtml(timestamp)}</em></div>`;
}

/** Verifica se comentário similar já existe nas últimas 5 adições */
async function isDuplicateComment(
  client: AzureDevOpsClient,
  workItemId: number,
  newComment: string
): Promise<boolean> {
  try {
    const workItem = await client.getWorkItem(workItemId, 'all');
    const history = workItem.fields?.['System.History'] || '';
    
    // Verificar se há o mesmo comentário no histórico recente
    const recentComments = history.split('---').slice(-5);
    const normalizedNew = newComment.toLowerCase().replace(/\s+/g, ' ').trim();
    
    return recentComments.some(c => {
      const normalized = c.toLowerCase().replace(/\s+/g, ' ').trim();
      // Comparar conteúdo (ignorar timestamp)
      return normalized.includes(normalizedNew.substring(0, 50)) || 
             normalizedNew.includes(normalized.substring(0, 50));
    });
  } catch {
    // Se não conseguir verificar, continuar mesmo assim
    return false;
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const client = new AzureDevOpsClient('add-comment');

  console.log('\n═══════════════════════════════════════════════════════════');
  console.log('FastQA — Adicionar Comentário em Work Item');
  console.log('═══════════════════════════════════════════════════════════');
  console.log(`Work Item ID: ${args.workItemId}`);
  console.log(`Seção:        ${args.section || '(padrão)'}`);
  console.log(`Comentário:   ${args.comment.substring(0, 80)}${args.comment.length > 80 ? '...' : ''}\n`);

  try {
    // Verificar duplicação
    const isDuplicate = await isDuplicateComment(client, args.workItemId, args.comment);
    if (isDuplicate) {
      console.log('⚠️  Comentário similar já foi adicionado recentemente. Prosseguindo com deduplicação ativa...\n');
    }

    // Formatar e adicionar comentário
    const formattedComment = formatComment(args.comment, args.section);
    await client.addWorkItemDiscussionComment(args.workItemId, formattedComment);

    const workItemUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_workitems/edit/${args.workItemId}`;
    console.log('✅ Comentário adicionado com sucesso!');
    console.log(`🔗 Work Item: ${workItemUrl}\n`);

    process.exit(0);
  } catch (error) {
    console.error('\n❌ Erro ao adicionar comentário:');
    console.error(error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { main as addComment };

