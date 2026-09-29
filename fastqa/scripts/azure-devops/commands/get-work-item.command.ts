#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Obter Work Item (fallback TS para MCP)
// ==========================================================================
//
// Obtém informações de um work item por ID ou busca por título via WIQL.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/get-work-item.command.ts \
//     --id 123
//   npx tsx fastqa/scripts/azure-devops/commands/get-work-item.command.ts \
//     --search "texto do título" [--type "Test Case"]
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';
import { Logger } from '../utils/logger.util';
import type { WorkItem } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface GetWorkItemArgs {
  id?: number;
  search?: string;
  type?: string;
}

function parseArgs(): GetWorkItemArgs {
  const args = process.argv.slice(2);
  const parsed: GetWorkItemArgs = {};

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--id': parsed.id = parseInt(args[++i], 10); break;
      case '--search': parsed.search = args[++i]; break;
      case '--type': parsed.type = args[++i]; break;
    }
  }

  if (!parsed.id && !parsed.search) {
    console.error('❌ Informe --id <number> ou --search "texto"');
    process.exit(1);
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('get-work-item');

  await withClient(async (client) => {
    if (args.id) {
      logger.info(`🔍 Buscando Work Item #${args.id}...`);
      const wi: WorkItem = await client.getWorkItem(args.id, 'all');
      printWorkItem(logger, wi);
    } else if (args.search) {
      logger.info(`🔍 Buscando por título: "${args.search}"...`);
      let wiql = `SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType] FROM workitems WHERE [System.Title] CONTAINS '${args.search.replace(/'/g, "''")}'`;
      if (args.type) {
        wiql += ` AND [System.WorkItemType] = '${args.type.replace(/'/g, "''")}'`;
      }
      wiql += ` AND [System.TeamProject] = '${config.project.replace(/'/g, "''")}'`;
      wiql += ' ORDER BY [System.ChangedDate] DESC';

      const result = await client.searchWorkItems(wiql);
      const ids = result.workItems?.map(w => w.id) || [];

      if (!ids.length) {
        logger.warn('Nenhum work item encontrado.');
        return;
      }

      logger.info(`Encontrados ${ids.length} work item(s):\n`);
      const items = await client.getWorkItemsBatch(ids.slice(0, 20));
      for (const wi of items) {
        printWorkItemSummary(logger, wi);
      }
    }
  }, 'get-work-item');
}

function printWorkItem(logger: Logger, wi: WorkItem): void {
  const f = wi.fields || {};
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Work Item #${wi.id}`);
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Tipo:            ${f['System.WorkItemType'] || 'N/A'}`);
  logger.info(`Título:          ${f['System.Title'] || 'N/A'}`);
  logger.info(`Estado:          ${f['System.State'] || 'N/A'}`);
  logger.info(`Atribuído a:     ${f['System.AssignedTo']?.displayName || 'N/A'}`);
  logger.info(`Area Path:       ${f['System.AreaPath'] || 'N/A'}`);
  logger.info(`Iteration:       ${f['System.IterationPath'] || 'N/A'}`);
  logger.info(`Criado em:       ${f['System.CreatedDate'] || 'N/A'}`);
  logger.info(`Atualizado em:   ${f['System.ChangedDate'] || 'N/A'}`);
  if (f['System.Description']) logger.info(`\nDescrição:\n${f['System.Description']}`);
  if (f['Microsoft.VSTS.TCM.Steps']) logger.info(`\nSteps:\n${f['Microsoft.VSTS.TCM.Steps']}`);
  logger.info('═══════════════════════════════════════════════════════════');
}

function printWorkItemSummary(logger: Logger, wi: WorkItem): void {
  const f = wi.fields || {};
  logger.info(`  #${wi.id} [${f['System.WorkItemType']}] ${f['System.Title']} — ${f['System.State']}`);
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
