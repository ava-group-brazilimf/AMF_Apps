#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Adicionar Test Case à Suite (fallback TS para MCP)
// ==========================================================================
//
// Adiciona um ou mais Test Cases a uma Test Suite.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/add-testcase-to-suite.command.ts \
//     --plan-id 29 \
//     --suite-id 38 \
//     --test-case-ids "45,46,47"
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface AddTestCaseArgs {
  planId: number;
  suiteId: number;
  testCaseIds: number[];
}

function parseArgs(): AddTestCaseArgs {
  const args = process.argv.slice(2);
  const parsed: AddTestCaseArgs = { planId: 0, suiteId: 0, testCaseIds: [] };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--plan-id': parsed.planId = parseInt(args[++i], 10); break;
      case '--suite-id': parsed.suiteId = parseInt(args[++i], 10); break;
      case '--test-case-ids': parsed.testCaseIds = args[++i].split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n)); break;
    }
  }

  if (!parsed.planId) { console.error('❌ Parâmetro --plan-id é obrigatório'); process.exit(1); }
  if (!parsed.suiteId) { console.error('❌ Parâmetro --suite-id é obrigatório'); process.exit(1); }
  if (!parsed.testCaseIds.length) { console.error('❌ Parâmetro --test-case-ids é obrigatório (ex: "45,46,47")'); process.exit(1); }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('add-testcase-to-suite');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Adicionar Test Cases à Suite');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Plan ID:       ${args.planId}`);
  logger.info(`Suite ID:      ${args.suiteId}`);
  logger.info(`Test Case IDs: ${args.testCaseIds.join(', ')}`);

  await withClient(async (client) => {
    await client.addTestCaseToSuite(args.planId, args.suiteId, args.testCaseIds);
    logger.success(`✅ ${args.testCaseIds.length} Test Case(s) adicionados à Suite #${args.suiteId} do Plan #${args.planId}`);
    for (const id of args.testCaseIds) {
      logger.info(`  • TC #${id} ✅`);
    }
  }, 'add-testcase-to-suite');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
