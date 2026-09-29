#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Criar Test Case (fallback TS para MCP)
// ==========================================================================
//
// Cria um Test Case com steps estruturados a partir de um arquivo .feature
// ou de steps inline.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/create-test-case.command.ts \
//     --title "Validar login com credenciais válidas" \
//     [--steps-file path/to/scenario.feature] \
//     [--steps "Given I open login page;When I enter credentials;Then I see dashboard"] \
//     [--area-path "Project\\Area"] \
//     [--iteration "Project\\Sprint 1"] \
//     [--parent-id 123] \
//     [--plan-id 29 --suite-id 38]
//
// ==========================================================================

import * as fs from 'fs';
import { AzureDevOpsClient, withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';
import type { JsonPatchOperation, TestCaseStep } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface CreateTestCaseArgs {
  title: string;
  stepsFile?: string;
  stepsInline?: string[];
  areaPath?: string;
  iteration?: string;
  parentId?: number;
  planId?: number;
  suiteId?: number;
}

function parseArgs(): CreateTestCaseArgs {
  const args = process.argv.slice(2);
  const parsed: CreateTestCaseArgs = { title: '' };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--title': parsed.title = args[++i]; break;
      case '--steps-file': parsed.stepsFile = args[++i]; break;
      case '--steps': parsed.stepsInline = args[++i].split(';').map(s => s.trim()).filter(Boolean); break;
      case '--area-path': parsed.areaPath = args[++i]; break;
      case '--iteration': parsed.iteration = args[++i]; break;
      case '--parent-id': parsed.parentId = parseInt(args[++i], 10); break;
      case '--plan-id': parsed.planId = parseInt(args[++i], 10); break;
      case '--suite-id': parsed.suiteId = parseInt(args[++i], 10); break;
    }
  }

  if (!parsed.title) { console.error('❌ Parâmetro --title é obrigatório'); process.exit(1); }

  return parsed;
}

// ---------------------------------------------------------------------------
// Steps Parsing
// ---------------------------------------------------------------------------

function parseFeatureSteps(filePath: string): string[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const steps: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (/^(Given|When|Then|And|But)\s/i.test(trimmed)) {
      steps.push(trimmed);
    }
  }
  return steps;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('create-test-case');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Criar Test Case no Azure DevOps');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Título: ${args.title}`);

  // Resolve steps
  let stepLines: string[] = [];
  if (args.stepsFile) {
    logger.info(`Steps de: ${args.stepsFile}`);
    stepLines = parseFeatureSteps(args.stepsFile);
  } else if (args.stepsInline) {
    stepLines = args.stepsInline;
  }

  if (stepLines.length) {
    logger.info(`Steps (${stepLines.length}):`);
    for (const s of stepLines) logger.info(`  • ${s}`);
  }

  await withClient(async (client) => {
    // Build operations
    const operations: JsonPatchOperation[] = [
      { op: 'add', path: '/fields/System.Title', value: args.title },
    ];
    if (args.areaPath) operations.push({ op: 'add', path: '/fields/System.AreaPath', value: args.areaPath });
    if (args.iteration) operations.push({ op: 'add', path: '/fields/System.IterationPath', value: args.iteration });

    // Add steps XML if provided
    if (stepLines.length) {
      const stepsXml = AzureDevOpsClient.buildTestCaseStepsXmlFromFeatureLines(stepLines);
      operations.push({ op: 'add', path: '/fields/Microsoft.VSTS.TCM.Steps', value: stepsXml });
    }

    const wi = await client.createWorkItem('Test Case', operations);
    logger.success(`✅ Test Case criado: #${wi.id}`);

    // Link to parent
    if (args.parentId) {
      logger.info(`🔗 Vinculando ao parent #${args.parentId}...`);
      await client.linkWorkItems(wi.id, args.parentId, 'Parent');
      logger.success(`  ✅ Vinculado como child de #${args.parentId}`);
    }

    // Add to suite
    if (args.planId && args.suiteId) {
      logger.info(`📋 Adicionando à Suite #${args.suiteId} do Plan #${args.planId}...`);
      await client.addTestCaseToSuite(args.planId, args.suiteId, [wi.id]);
      logger.success(`  ✅ Adicionado à suite`);
    }

    // Report
    logger.info('\n═══════════════════════════════════════════════════════════');
    logger.info(`Test Case ID:  ${wi.id}`);
    logger.info(`Título:        ${args.title}`);
    logger.info(`Steps:         ${stepLines.length}`);
    if (args.planId) logger.info(`Test Plan:     #${args.planId}`);
    if (args.suiteId) logger.info(`Test Suite:    #${args.suiteId}`);
    logger.info(`URL:           ${wi.url}`);
    logger.success('✅ Concluído');
    logger.info('═══════════════════════════════════════════════════════════');
  }, 'create-test-case');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
