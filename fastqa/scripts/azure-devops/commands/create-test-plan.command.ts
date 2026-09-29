#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando #19: Criar Test Plan no Azure DevOps
// ==========================================================================
//
// Cria um novo Test Plan com suites opcionais.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/create-test-plan.command.ts \
//     --name "Plano de Teste Sprint 1" \
//     [--area-path "Project\\Area"] \
//     [--iteration "Project\\Sprint 1"] \
//     [--start-date 2026-04-01] \
//     [--end-date 2026-04-30] \
//     [--description "Descrição do plano"] \
//     [--suites "Smoke Tests,Regression Tests,API Tests"] \
//     [--dry-run]
//
// ==========================================================================

import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';
import type { TestPlan, TestSuite, CreateTestPlanParams } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface CreateTestPlanArgs {
  name: string;
  areaPath?: string;
  iteration?: string;
  startDate?: string;
  endDate?: string;
  description?: string;
  suites: string[];
  dryRun: boolean;
}

function parseArgs(): CreateTestPlanArgs {
  const args = process.argv.slice(2);
  const parsed: CreateTestPlanArgs = {
    name: '',
    suites: [],
    dryRun: false,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--name': parsed.name = args[++i]; break;
      case '--area-path': parsed.areaPath = args[++i]; break;
      case '--iteration': parsed.iteration = args[++i]; break;
      case '--start-date': parsed.startDate = args[++i]; break;
      case '--end-date': parsed.endDate = args[++i]; break;
      case '--description': parsed.description = args[++i]; break;
      case '--suites': parsed.suites = args[++i].split(',').map(s => s.trim()).filter(Boolean); break;
      case '--dry-run': parsed.dryRun = true; break;
    }
  }

  if (!parsed.name) {
    console.error('❌ Parâmetro --name é obrigatório');
    console.error('Uso: npx tsx create-test-plan.command.ts --name "Nome do Plano" [--suites "Suite1,Suite2"]');
    process.exit(1);
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('create-test-plan');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Criar Test Plan no Azure DevOps');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Nome: ${args.name}`);
  if (args.areaPath) logger.info(`Area Path: ${args.areaPath}`);
  if (args.iteration) logger.info(`Iteration: ${args.iteration}`);
  if (args.startDate) logger.info(`Data Início: ${args.startDate}`);
  if (args.endDate) logger.info(`Data Fim: ${args.endDate}`);
  if (args.suites.length) logger.info(`Suites a criar: ${args.suites.join(', ')}`);
  if (args.dryRun) logger.warn('🔍 Modo DRY-RUN — nenhuma alteração será feita');

  if (args.dryRun) {
    logger.info('\n📋 Resumo do que seria criado:');
    logger.info(`  Test Plan: "${args.name}"`);
    for (const suite of args.suites) {
      logger.info(`  └── Suite: "${suite}"`);
    }
    logger.success('✅ Dry-run concluído');
    return;
  }

  await withClient(async (client) => {
    // Step 1: Criar Test Plan
    logger.info('\n📝 Step 1: Criando Test Plan...');
    const planParams: CreateTestPlanParams = {
      name: args.name,
      areaPath: args.areaPath,
      iteration: args.iteration,
      startDate: args.startDate,
      endDate: args.endDate,
      description: args.description,
    };

    const plan: TestPlan = await client.createTestPlan(planParams);
    logger.success(`✅ Test Plan criado: #${plan.id} — "${plan.name}"`);

    const rootSuiteId = plan.rootSuite?.id;
    if (!rootSuiteId) {
      logger.warn('⚠️ Root Suite não retornada pela API. Suites filhas não serão criadas.');
    }

    // Step 2: Criar Suites (se informadas)
    const createdSuites: TestSuite[] = [];
    if (args.suites.length && rootSuiteId) {
      logger.info(`\n📂 Step 2: Criando ${args.suites.length} suite(s)...`);
      for (const suiteName of args.suites) {
        const suite = await client.createTestSuite(plan.id, {
          name: suiteName,
          parentSuiteId: rootSuiteId,
          suiteType: 'StaticTestSuite',
        });
        createdSuites.push(suite);
        logger.success(`  ✅ Suite criada: #${suite.id} — "${suite.name}"`);
      }
    }

    // Step 3: Relatório final
    logger.info('\n═══════════════════════════════════════════════════════════');
    logger.success('📊 RELATÓRIO FINAL');
    logger.info('═══════════════════════════════════════════════════════════');
    logger.info(`Test Plan ID:    ${plan.id}`);
    logger.info(`Test Plan Nome:  ${plan.name}`);
    logger.info(`Estado:          ${plan.state || 'Active'}`);
    if (rootSuiteId) logger.info(`Root Suite ID:   ${rootSuiteId}`);
    if (plan.areaPath) logger.info(`Area Path:       ${plan.areaPath}`);
    if (plan.iteration) logger.info(`Iteration:       ${plan.iteration}`);
    if (createdSuites.length) {
      logger.info(`\nSuites criadas (${createdSuites.length}):`);
      for (const s of createdSuites) {
        logger.info(`  • #${s.id} — ${s.name}`);
      }
    }
    logger.info('═══════════════════════════════════════════════════════════');
  }, 'create-test-plan');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
