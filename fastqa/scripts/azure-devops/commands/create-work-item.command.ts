#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Criar Work Item (fallback TS para MCP)
// ==========================================================================
//
// Cria um work item de qualquer tipo no Azure DevOps.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/create-work-item.command.ts \
//     --type "Test Case" \
//     --title "Título do work item" \
//     [--area-path "Project\\Area"] \
//     [--iteration "Project\\Sprint 1"] \
//     [--assigned-to "user@email.com"] \
//     [--fields "System.Description=Texto,Microsoft.VSTS.Common.Priority=2"] \
//     [--parent-id 123] \
//     [--tags "tag1,tag2"]
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';
import type { JsonPatchOperation, WorkItemType } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface CreateWorkItemArgs {
  type: string;
  title: string;
  areaPath?: string;
  iteration?: string;
  assignedTo?: string;
  fields: Record<string, string>;
  parentId?: number;
  tags?: string;
}

function parseArgs(): CreateWorkItemArgs {
  const args = process.argv.slice(2);
  const parsed: CreateWorkItemArgs = { type: '', title: '', fields: {} };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--type': parsed.type = args[++i]; break;
      case '--title': parsed.title = args[++i]; break;
      case '--area-path': parsed.areaPath = args[++i]; break;
      case '--iteration': parsed.iteration = args[++i]; break;
      case '--assigned-to': parsed.assignedTo = args[++i]; break;
      case '--parent-id': parsed.parentId = parseInt(args[++i], 10); break;
      case '--tags': parsed.tags = args[++i]; break;
      case '--fields': {
        const pairs = args[++i].split(',');
        for (const pair of pairs) {
          const eqIdx = pair.indexOf('=');
          if (eqIdx > 0) {
            const key = pair.substring(0, eqIdx).trim();
            const value = pair.substring(eqIdx + 1).trim();
            parsed.fields[key] = value;
          }
        }
        break;
      }
    }
  }

  if (!parsed.type) { console.error('❌ Parâmetro --type é obrigatório'); process.exit(1); }
  if (!parsed.title) { console.error('❌ Parâmetro --title é obrigatório'); process.exit(1); }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('create-work-item');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Criar Work Item no Azure DevOps');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Tipo:    ${args.type}`);
  logger.info(`Título:  ${args.title}`);

  await withClient(async (client) => {
    // Build operations
    const operations: JsonPatchOperation[] = [
      { op: 'add', path: '/fields/System.Title', value: args.title },
    ];
    if (args.areaPath) operations.push({ op: 'add', path: '/fields/System.AreaPath', value: args.areaPath });
    if (args.iteration) operations.push({ op: 'add', path: '/fields/System.IterationPath', value: args.iteration });
    if (args.assignedTo) operations.push({ op: 'add', path: '/fields/System.AssignedTo', value: args.assignedTo });
    if (args.tags) operations.push({ op: 'add', path: '/fields/System.Tags', value: args.tags });

    for (const [field, value] of Object.entries(args.fields)) {
      operations.push({ op: 'add', path: `/fields/${field}`, value });
    }

    const wi = await client.createWorkItem(args.type as WorkItemType, operations);
    logger.success(`✅ Work Item criado: #${wi.id}`);

    // Link to parent if specified
    if (args.parentId) {
      logger.info(`🔗 Vinculando ao parent #${args.parentId}...`);
      await client.linkWorkItems(wi.id, args.parentId, 'Child');
      logger.success(`  ✅ Vinculado como child de #${args.parentId}`);
    }

    // Report
    logger.info('\n═══════════════════════════════════════════════════════════');
    logger.info(`Work Item ID:  ${wi.id}`);
    logger.info(`Tipo:          ${args.type}`);
    logger.info(`Título:        ${args.title}`);
    logger.info(`URL:           ${wi.url}`);
    logger.success('✅ Concluído');
    logger.info('═══════════════════════════════════════════════════════════');
  }, 'create-work-item');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
