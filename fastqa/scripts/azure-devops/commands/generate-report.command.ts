#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando: Gerar Relatório (fallback TS para MCP)
// ==========================================================================
//
// Gera relatório consolidado de execução de testes a partir de Test Plans.
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/generate-report.command.ts \
//     --plan-id 29 \
//     [--suite-id 38] \
//     [--format markdown|json] \
//     [--output-path "./reports/"]
//
// ==========================================================================

import * as fs from 'fs';
import * as path from 'path';
import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';
import { generateMarkdownReport, generateJsonReport } from '../utils/report-generator.util';
import type { ReportData, ReportTestResult } from '../utils/report-generator.util';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface GenerateReportArgs {
  planId: number;
  suiteId?: number;
  format: 'markdown' | 'json';
  outputPath?: string;
}

function parseArgs(): GenerateReportArgs {
  const args = process.argv.slice(2);
  const parsed: GenerateReportArgs = { planId: 0, format: 'markdown' };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--plan-id': parsed.planId = parseInt(args[++i], 10); break;
      case '--suite-id': parsed.suiteId = parseInt(args[++i], 10); break;
      case '--format': parsed.format = args[++i] as 'markdown' | 'json'; break;
      case '--output-path': parsed.outputPath = args[++i]; break;
    }
  }

  if (!parsed.planId) { console.error('❌ Parâmetro --plan-id é obrigatório'); process.exit(1); }

  return parsed;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('generate-report');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Gerar Relatório de Execução');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Plan ID: ${args.planId}`);
  if (args.suiteId) logger.info(`Suite ID: ${args.suiteId}`);
  logger.info(`Formato: ${args.format}`);

  await withClient(async (client) => {
    // Step 1: Obter plano
    logger.info('\n🔍 Step 1: Obtendo dados do Test Plan...');
    const plan = await client.getTestPlan(args.planId);
    logger.info(`  Plan: "${plan.name}" [${plan.state || 'Active'}]`);

    // Step 2: Obter suites
    logger.info('\n📂 Step 2: Obtendo suites...');
    const suitesResponse = await client.getTestSuites(args.planId);
    let suites = suitesResponse.value || [];
    if (args.suiteId) suites = suites.filter(s => s.id === args.suiteId);
    logger.info(`  Encontradas ${suites.length} suite(s)`);

    // Step 3: Coletar test cases
    logger.info('\n📋 Step 3: Coletando test cases...');
    const testResults: ReportTestResult[] = [];

    for (const suite of suites) {
      try {
        const tcsResponse = await client.getTestCases(args.planId, suite.id);
        const tcs = tcsResponse.value || [];
        for (const tc of tcs) {
          testResults.push({
            testCaseId: tc.workItem?.id || tc.testCase?.id || 0,
            testCaseTitle: (tc.workItem?.fields?.['System.Title'] as string | undefined) || tc.testCase?.name || 'N/A',
            outcome: (tc.pointAssignments?.[0] as any)?.outcome || 'NotExecuted',
            evidenceFiles: [],
          });
        }
      } catch {
        logger.warn(`  ⚠️ Erro ao obter test cases da suite #${suite.id}`);
      }
    }

    logger.info(`  Total test cases: ${testResults.length}`);

    // Step 4: Gerar relatório
    logger.info('\n📊 Step 4: Gerando relatório...');
    const reportData: ReportData = {
      title: `Relatório - ${plan.name}`,
      testPlanId: plan.id,
      testPlanName: plan.name,
      executionDate: new Date().toISOString(),
      results: testResults,
    };

    const reportContent = args.format === 'json'
      ? generateJsonReport(reportData)
      : generateMarkdownReport(reportData);

    // Step 5: Salvar
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const ext = args.format === 'json' ? 'json' : 'md';
    const outputDir = args.outputPath || path.resolve(process.cwd(), 'fastqa', 'manual_test', 'evidence', 'reports');
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
    const outputFile = path.join(outputDir, `report-plan-${args.planId}-${timestamp}.${ext}`);
    fs.writeFileSync(outputFile, reportContent, 'utf-8');

    logger.success(`\n✅ Relatório salvo: ${outputFile}`);
    logger.info('═══════════════════════════════════════════════════════════');
  }, 'generate-report');
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
