#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Listar Work Items por Sprint (fallback TS para MCP)
// ==========================================================================
//
// Lista work items de uma sprint/iteração via WIQL.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/list-work-items-by-sprint.command.ts \
//     --iteration "Project\\Sprint 1" \
//     [--type "Bug,Test Case"] \
//     [--state "Active,New"]
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';
import { Logger } from '../utils/logger.util';
import type { WorkItem } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface ListWorkItemsArgs {
  iteration: string;
  types: string[];
  states: string[];
}

function parseArgs(): ListWorkItemsArgs {
  const args = process.argv.slice(2);
  const parsed: ListWorkItemsArgs = { iteration: '', types: [], states: [] };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--iteration': parsed.iteration = args[++i]; break;
      case '--type': parsed.types = args[++i].split(',').map(s => s.trim()); break;
      case '--state': parsed.states = args[++i].split(',').map(s => s.trim()); break;
    }
  }

  if (!parsed.iteration) {
    console.error('❌ Parâmetro --iteration é obrigatório (ex: "Project\\Sprint 1")');
    process.exit(1);
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('list-work-items-sprint');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Listar Work Items por Sprint');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Iteration: ${args.iteration}`);
  if (args.types.length) logger.info(`Tipos:     ${args.types.join(', ')}`);
  if (args.states.length) logger.info(`Estados:   ${args.states.join(', ')}`);

  await withClient(async (client) => {
    let wiql = `SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo] FROM workitems WHERE [System.IterationPath] UNDER '${args.iteration.replace(/'/g, "''")}'`;
    wiql += ` AND [System.TeamProject] = '${config.project.replace(/'/g, "''")}'`;

    if (args.types.length) {
      const typeFilter = args.types.map(t => `'${t.replace(/'/g, "''")}'`).join(', ');
      wiql += ` AND [System.WorkItemType] IN (${typeFilter})`;
    }
    if (args.states.length) {
      const stateFilter = args.states.map(s => `'${s.replace(/'/g, "''")}'`).join(', ');
      wiql += ` AND [System.State] IN (${stateFilter})`;
    }

    wiql += ' ORDER BY [System.WorkItemType], [System.State], [System.Id]';

    const result = await client.searchWorkItems(wiql);
    const ids = result.workItems?.map(w => w.id) || [];

    if (!ids.length) {
      logger.warn('Nenhum work item encontrado para esta sprint.');
      return;
    }

    const items = await client.getWorkItemsBatch(ids, [
      'System.Id', 'System.Title', 'System.State',
      'System.WorkItemType', 'System.AssignedTo',
    ]);

    // Agrupar por tipo
    const byType: Record<string, WorkItem[]> = {};
    for (const wi of items) {
      const type = wi.fields?.['System.WorkItemType'] || 'Outros';
      if (!byType[type]) byType[type] = [];
      byType[type].push(wi);
    }

    logger.info(`\n📋 Encontrados ${items.length} work item(s) em "${args.iteration}":\n`);
    for (const [type, wis] of Object.entries(byType)) {
      logger.info(`\n  📁 ${type} (${wis.length}):`);
      for (const wi of wis) {
        const f = wi.fields || {};
        const assignee = f['System.AssignedTo']?.displayName || 'Não atribuído';
        logger.info(`    #${wi.id} [${f['System.State']}] ${f['System.Title']} — ${assignee}`);
      }
    }

    logger.info('\n═══════════════════════════════════════════════════════════');
  }, 'list-work-items-sprint');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
