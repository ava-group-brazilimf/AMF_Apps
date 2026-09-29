#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Vincular Work Items (fallback TS para MCP)
// ==========================================================================
//
// Cria vínculo entre dois work items no Azure DevOps.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/link-work-items.command.ts \
//     --source-id 123 \
//     --target-id 456 \
//     --link-type "Tests" \
//     [--comment "Vínculo de rastreabilidade"]
//
// Link types: Parent, Child, Related, Duplicate, Tests, Tested By, Affects
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface LinkWorkItemsArgs {
  sourceId: number;
  targetId: number;
  linkType: string;
  comment?: string;
}

function parseArgs(): LinkWorkItemsArgs {
  const args = process.argv.slice(2);
  const parsed: LinkWorkItemsArgs = { sourceId: 0, targetId: 0, linkType: '' };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--source-id': parsed.sourceId = parseInt(args[++i], 10); break;
      case '--target-id': parsed.targetId = parseInt(args[++i], 10); break;
      case '--link-type': parsed.linkType = args[++i]; break;
      case '--comment': parsed.comment = args[++i]; break;
    }
  }

  if (!parsed.sourceId) { console.error('❌ Parâmetro --source-id é obrigatório'); process.exit(1); }
  if (!parsed.targetId) { console.error('❌ Parâmetro --target-id é obrigatório'); process.exit(1); }
  if (!parsed.linkType) { console.error('❌ Parâmetro --link-type é obrigatório (Parent, Child, Related, Tests, etc.)'); process.exit(1); }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('link-work-items');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Vincular Work Items');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Source:    #${args.sourceId}`);
  logger.info(`Target:    #${args.targetId}`);
  logger.info(`Link Type: ${args.linkType}`);

  await withClient(async (client) => {
    await client.linkWorkItems(args.sourceId, args.targetId, args.linkType, args.comment);
    logger.success(`✅ Work Items vinculados: #${args.sourceId} —[${args.linkType}]→ #${args.targetId}`);
  }, 'link-work-items');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
