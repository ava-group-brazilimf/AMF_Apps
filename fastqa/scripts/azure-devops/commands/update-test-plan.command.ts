#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando #20: Atualizar Test Plan no Azure DevOps
// ==========================================================================
//
// Atualiza propriedades de um Test Plan existente.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/update-test-plan.command.ts \
//     --plan-id 29 \
//     [--name "Novo Nome"] \
//     [--area-path "Project\\Area"] \
//     [--iteration "Project\\Sprint 2"] \
//     [--start-date 2026-04-01] \
//     [--end-date 2026-04-30] \
//     [--state Active|Inactive] \
//     [--description "Nova descrição"]
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';
import type { UpdateTestPlanParams } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface UpdateTestPlanArgs {
  planId: number;
  name?: string;
  areaPath?: string;
  iteration?: string;
  startDate?: string;
  endDate?: string;
  state?: 'Active' | 'Inactive';
  description?: string;
}

function parseArgs(): UpdateTestPlanArgs {
  const args = process.argv.slice(2);
  const parsed: UpdateTestPlanArgs = { planId: 0 };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--plan-id': parsed.planId = parseInt(args[++i], 10); break;
      case '--name': parsed.name = args[++i]; break;
      case '--area-path': parsed.areaPath = args[++i]; break;
      case '--iteration': parsed.iteration = args[++i]; break;
      case '--start-date': parsed.startDate = args[++i]; break;
      case '--end-date': parsed.endDate = args[++i]; break;
      case '--state': parsed.state = args[++i] as 'Active' | 'Inactive'; break;
      case '--description': parsed.description = args[++i]; break;
    }
  }

  if (!parsed.planId) {
    console.error('❌ Parâmetro --plan-id é obrigatório');
    process.exit(1);
  }

  const hasUpdates = parsed.name || parsed.areaPath || parsed.iteration ||
    parsed.startDate || parsed.endDate || parsed.state || parsed.description;
  if (!hasUpdates) {
    console.error('❌ Informe pelo menos um campo para atualizar (--name, --area-path, --iteration, --start-date, --end-date, --state, --description)');
    process.exit(1);
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('update-test-plan');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Atualizar Test Plan no Azure DevOps');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Plan ID: ${args.planId}`);

  await withClient(async (client) => {
    // Step 1: Obter estado atual
    logger.info('\n🔍 Step 1: Obtendo estado atual do Test Plan...');
    const currentPlan = await client.getTestPlan(args.planId);
    logger.info(`  Nome atual:      ${currentPlan.name}`);
    logger.info(`  Estado atual:    ${currentPlan.state || 'N/A'}`);
    if (currentPlan.areaPath) logger.info(`  Area Path:       ${currentPlan.areaPath}`);
    if (currentPlan.iteration) logger.info(`  Iteration:       ${currentPlan.iteration}`);

    // Step 2: Aplicar atualizações
    logger.info('\n📝 Step 2: Aplicando atualizações...');
    const updateParams: UpdateTestPlanParams = {};
    if (args.name) { updateParams.name = args.name; logger.info(`  Nome: "${currentPlan.name}" → "${args.name}"`); }
    if (args.areaPath) { updateParams.areaPath = args.areaPath; logger.info(`  Area Path → "${args.areaPath}"`); }
    if (args.iteration) { updateParams.iteration = args.iteration; logger.info(`  Iteration → "${args.iteration}"`); }
    if (args.startDate) { updateParams.startDate = args.startDate; logger.info(`  Data Início → ${args.startDate}`); }
    if (args.endDate) { updateParams.endDate = args.endDate; logger.info(`  Data Fim → ${args.endDate}`); }
    if (args.state) { updateParams.state = args.state; logger.info(`  Estado → ${args.state}`); }
    if (args.description) { updateParams.description = args.description; logger.info(`  Descrição atualizada`); }

    const updatedPlan = await client.updateTestPlan(args.planId, updateParams);

    // Step 3: Relatório final
    logger.info('\n═══════════════════════════════════════════════════════════');
    logger.success('📊 RELATÓRIO FINAL');
    logger.info('═══════════════════════════════════════════════════════════');
    logger.info(`Test Plan ID:    ${updatedPlan.id}`);
    logger.info(`Nome:            ${updatedPlan.name}`);
    logger.info(`Estado:          ${updatedPlan.state || 'Active'}`);
    if (updatedPlan.areaPath) logger.info(`Area Path:       ${updatedPlan.areaPath}`);
    if (updatedPlan.iteration) logger.info(`Iteration:       ${updatedPlan.iteration}`);
    logger.success('✅ Test Plan atualizado com sucesso');
    logger.info('═══════════════════════════════════════════════════════════');
  }, 'update-test-plan');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
