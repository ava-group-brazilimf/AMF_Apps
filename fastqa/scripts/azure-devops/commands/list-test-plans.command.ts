#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Listar Test Plans (fallback TS para MCP)
// ==========================================================================
//
// Lista Test Plans, Suites e Test Cases em formato hierárquico.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/list-test-plans.command.ts \
//     [--plan-id 29] \
//     [--suite-id 38] \
//     [--show-test-cases]
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface ListTestPlansArgs {
  planId?: number;
  suiteId?: number;
  showTestCases: boolean;
}

function parseArgs(): ListTestPlansArgs {
  const args = process.argv.slice(2);
  const parsed: ListTestPlansArgs = { showTestCases: false };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--plan-id': parsed.planId = parseInt(args[++i], 10); break;
      case '--suite-id': parsed.suiteId = parseInt(args[++i], 10); break;
      case '--show-test-cases': parsed.showTestCases = true; break;
    }
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('list-test-plans');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Listar Test Plans');
  logger.info('═══════════════════════════════════════════════════════════');

  await withClient(async (client) => {
    const plansResponse = await client.getTestPlans();
    const plans = plansResponse.value || [];

    if (!plans.length) {
      logger.warn('Nenhum Test Plan encontrado.');
      return;
    }

    // Filtrar por plan ID se especificado
    const filteredPlans = args.planId ? plans.filter(p => p.id === args.planId) : plans;

    if (!filteredPlans.length) {
      logger.warn(`Test Plan #${args.planId} não encontrado.`);
      return;
    }

    logger.info(`\n📋 Encontrados ${filteredPlans.length} Test Plan(s):\n`);

    for (const plan of filteredPlans) {
      logger.info(`📁 Test Plan #${plan.id}: ${plan.name} [${plan.state || 'Active'}]`);
      if (plan.areaPath) logger.info(`   Area: ${plan.areaPath}`);
      if (plan.iteration) logger.info(`   Iteration: ${plan.iteration}`);

      // Listar suites
      const suitesResponse = await client.getTestSuites(plan.id);
      const suites = suitesResponse.value || [];

      // Filtrar por suite ID se especificado
      const filteredSuites = args.suiteId ? suites.filter(s => s.id === args.suiteId) : suites;

      for (const suite of filteredSuites) {
        const indent = suite.parentSuite ? '   ' : '';
        logger.info(`${indent}├── Suite #${suite.id}: ${suite.name} [${suite.suiteType}] (${suite.testCaseCount || 0} TCs)`);

        // Listar test cases se solicitado
        if (args.showTestCases && suite.testCaseCount) {
          try {
            const tcsResponse = await client.getTestCases(plan.id, suite.id);
            const tcs = tcsResponse.value || [];
            for (const tc of tcs) {
              const tcId = tc.workItem?.id || tc.testCase?.id || 'N/A';
              const tcName = (tc.workItem?.fields?.['System.Title'] as string | undefined) || tc.testCase?.name || 'N/A';
              logger.info(`${indent}│   ├── TC #${tcId}: ${tcName}`);
            }
          } catch {
            logger.warn(`${indent}│   ⚠️ Erro ao listar test cases da suite`);
          }
        }
      }
      logger.info('');
    }

    logger.info('═══════════════════════════════════════════════════════════');
  }, 'list-test-plans');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
