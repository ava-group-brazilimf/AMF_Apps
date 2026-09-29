#!/usr/bin/env npx tsx
// ==========================================================================
// FastQA — Comando #24: Verificar Resultados de Pipeline + Diagnóstico
// ==========================================================================
//
// Verifica resultados de uma pipeline executada, sincroniza com o Test Plan,
// extrai logs de falhas e gera relatório de diagnóstico para uso com
// @fastqa:verify_and_fix (auto-healing).
//
// Uso:
//   npx tsx fastqa/scripts/azure-devops/commands/verify-pipeline-results.command.ts \
//     --build-id 123 \
//     --test-plan-id 29 \
//     --test-suite-id 38 \
//     [--auto-bug] \
//     [--bug-severity "3 - Medium"] \
//     [--wait] \
//     [--timeout 600000] \
//     [--poll-interval 15000] \
//     [--output-report]
//
// ==========================================================================

import * as fs from 'fs';
import * as path from 'path';
import { withClient } from '../azure-devops.client';
import { Logger } from '../utils/logger.util';
import type { Build, BuildTestRun, TestResult } from '../types/azure-devops.types';

// ---------------------------------------------------------------------------
// CLI Parsing
// ---------------------------------------------------------------------------

interface VerifyPipelineArgs {
  buildId: number;
  testPlanId: number;
  testSuiteId: number;
  autoBug: boolean;
  bugSeverity: string;
  wait: boolean;
  timeoutMs: number;
  pollIntervalMs: number;
  outputReport: boolean;
}

function parseArgs(): VerifyPipelineArgs {
  const args = process.argv.slice(2);
  const parsed: VerifyPipelineArgs = {
    buildId: 0,
    testPlanId: 0,
    testSuiteId: 0,
    autoBug: false,
    bugSeverity: '3 - Medium',
    wait: false,
    timeoutMs: 600_000,
    pollIntervalMs: 15_000,
    outputReport: true,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--build-id': parsed.buildId = parseInt(args[++i], 10); break;
      case '--test-plan-id': parsed.testPlanId = parseInt(args[++i], 10); break;
      case '--test-suite-id': parsed.testSuiteId = parseInt(args[++i], 10); break;
      case '--auto-bug': parsed.autoBug = true; break;
      case '--bug-severity': parsed.bugSeverity = args[++i]; break;
      case '--wait': parsed.wait = true; break;
      case '--timeout': parsed.timeoutMs = parseInt(args[++i], 10); break;
      case '--poll-interval': parsed.pollIntervalMs = parseInt(args[++i], 10); break;
      case '--output-report': parsed.outputReport = true; break;
      case '--no-report': parsed.outputReport = false; break;
    }
  }

  if (!parsed.buildId) { console.error('❌ Parâmetro --build-id é obrigatório'); process.exit(1); }
  if (!parsed.testPlanId) { console.error('❌ Parâmetro --test-plan-id é obrigatório'); process.exit(1); }
  if (!parsed.testSuiteId) { console.error('❌ Parâmetro --test-suite-id é obrigatório'); process.exit(1); }

  return parsed;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSecs = seconds % 60;
  if (minutes > 0) return `${minutes}m ${remainingSecs}s`;
  return `${seconds}s`;
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

interface FailedTestDiagnosis {
  testName: string;
  outcome: string;
  errorMessage?: string;
  stackTrace?: string;
  logExcerpt?: string;
  duration?: number;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const logger = new Logger('verify-pipeline-results');

  logger.info('═══════════════════════════════════════════════════════════');
  logger.info('FastQA — Verificar Resultados de Pipeline');
  logger.info('═══════════════════════════════════════════════════════════');
  logger.info(`Build ID:       ${args.buildId}`);
  logger.info(`Test Plan ID:   ${args.testPlanId}`);
  logger.info(`Test Suite ID:  ${args.testSuiteId}`);
  if (args.autoBug) logger.info(`Auto-Bug:       ${args.bugSeverity}`);
  if (args.wait) logger.info(`Aguardar:       Sim (timeout: ${formatDuration(args.timeoutMs)})`);

  await withClient(async (client) => {
    // Step 1: Obter/aguardar build
    logger.info('\n🔍 Step 1: Verificando status da build...');
    let build: Build = await client.getBuild(args.buildId);

    if (build.status !== 'completed' && args.wait) {
      logger.info(`  Build #${args.buildId} em andamento (${build.status}). Aguardando...`);
      const startTime = Date.now();
      while (build.status !== 'completed') {
        const elapsed = Date.now() - startTime;
        if (elapsed > args.timeoutMs) {
          logger.error(`⏱️ Timeout atingido (${formatDuration(args.timeoutMs)})`);
          process.exit(2);
        }
        await sleep(args.pollIntervalMs);
        build = await client.getBuild(args.buildId);
        logger.info(`  ⏳ Status: ${build.status} (${formatDuration(elapsed)})`);
      }
    } else if (build.status !== 'completed') {
      logger.error(`❌ Build #${args.buildId} não está completa (status: ${build.status}). Use --wait para aguardar.`);
      process.exit(1);
    }

    logger.success(`  ✅ Build #${args.buildId} — resultado: ${build.result}`);

    // Step 2: Obter test runs da build
    logger.info('\n📋 Step 2: Obtendo test runs da build...');
    const buildUri = `vstfs:///Build/Build/${args.buildId}`;
    const testRuns = await client.getTestRunsByBuild(buildUri);
    const runs: BuildTestRun[] = testRuns.value || [];
    logger.info(`  Encontradas ${runs.length} test run(s)`);

    // Step 3: Coletar resultados detalhados
    logger.info('\n📊 Step 3: Coletando resultados dos testes...');
    const allResults: TestResult[] = [];
    for (const run of runs) {
      const results = await client.getTestResults(run.id);
      const resultList = Array.isArray(results) ? results : (results as any).value || [];
      allResults.push(...resultList);
    }

    const passed = allResults.filter(r => r.outcome === 'Passed');
    const failed = allResults.filter(r => r.outcome === 'Failed');
    const others = allResults.filter(r => r.outcome !== 'Passed' && r.outcome !== 'Failed');

    logger.info(`  Total:   ${allResults.length}`);
    logger.success(`  Passed:  ${passed.length}`);
    if (failed.length) logger.error(`  Failed:  ${failed.length}`);
    if (others.length) logger.warn(`  Others:  ${others.length}`);

    // Step 4: Extrair diagnóstico de falhas
    const diagnoses: FailedTestDiagnosis[] = [];
    if (failed.length) {
      logger.info('\n🔬 Step 4: Extraindo diagnóstico de falhas...');

      // Obter logs da build para contexto
      let buildLogContent = '';
      try {
        const logs = await client.getBuildLogs(args.buildId);
        const logEntries = logs.value || [];
        // Pegar os últimos logs (normalmente contêm os erros)
        const lastLogs = logEntries.slice(-3);
        for (const logEntry of lastLogs) {
          try {
            const content = await client.getBuildLogContent(args.buildId, logEntry.id);
            buildLogContent += content + '\n';
          } catch {
            // Log individual pode falhar, continuar
          }
        }
      } catch {
        logger.warn('  ⚠️ Não foi possível obter logs da build');
      }

      for (const result of failed) {
        const testName = result.testCase?.name || `TestCase#${result.testCase?.id ?? 'Unknown'}`;
        const diagnosis: FailedTestDiagnosis = {
          testName,
          outcome: result.outcome,
          errorMessage: result.errorMessage,
          duration: result.durationInMs,
        };

        // Extrair stack trace do errorMessage se presente
        if (result.errorMessage) {
          const stackIdx = result.errorMessage.indexOf('\n   at ');
          if (stackIdx > -1) {
            diagnosis.errorMessage = result.errorMessage.substring(0, stackIdx);
            diagnosis.stackTrace = result.errorMessage.substring(stackIdx);
          }
        }

        // Buscar trecho relevante nos logs da build
        if (buildLogContent && testName) {
          const logLines = buildLogContent.split('\n');
          const matchIdx = logLines.findIndex(l => l.includes(testName) || l.toLowerCase().includes('failed'));
          if (matchIdx > -1) {
            const start = Math.max(0, matchIdx - 5);
            const end = Math.min(logLines.length, matchIdx + 20);
            diagnosis.logExcerpt = logLines.slice(start, end).join('\n');
          }
        }

        diagnoses.push(diagnosis);
        logger.error(`  ❌ ${testName}: ${diagnosis.errorMessage || 'Sem mensagem de erro'}`);
      }
    }

    // Step 5: Gerar relatório de diagnóstico
    if (args.outputReport && diagnoses.length) {
      logger.info('\n📝 Step 5: Gerando relatório de diagnóstico...');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const reportDir = path.resolve(process.cwd(), 'fastqa', 'manual_test', 'evidence', 'reports');
      if (!fs.existsSync(reportDir)) fs.mkdirSync(reportDir, { recursive: true });
      const reportPath = path.join(reportDir, `pipeline-verify-${args.buildId}-${timestamp}.md`);

      const reportContent = generateDiagnosticReport(args, build, allResults, diagnoses);
      fs.writeFileSync(reportPath, reportContent, 'utf-8');
      logger.success(`  ✅ Relatório salvo: ${reportPath}`);
    }

    // Step 6: Executar sync com Test Plan
    logger.info('\n🔄 Step 6: Dica de sincronização com Test Plan...');
    const syncCmd = [
      'npx tsx fastqa/scripts/azure-devops/commands/sync-pipeline-results.command.ts',
      `--build-id ${args.buildId}`,
      `--test-plan-id ${args.testPlanId}`,
      `--test-suite-id ${args.testSuiteId}`,
      '--map-by-name',
    ];
    if (args.autoBug) {
      syncCmd.push('--auto-bug');
      syncCmd.push(`--bug-severity "${args.bugSeverity}"`);
    }
    logger.info(`  Execute: ${syncCmd.join(' \\\n    ')}`);

    // Step 7: Relatório final
    logger.info('\n═══════════════════════════════════════════════════════════');
    logger.success('📊 RELATÓRIO FINAL');
    logger.info('═══════════════════════════════════════════════════════════');
    logger.info(`Build:           #${build.id} (${build.buildNumber})`);
    logger.info(`Resultado:       ${build.result}`);
    logger.info(`Total testes:    ${allResults.length}`);
    logger.info(`Passed:          ${passed.length}`);
    logger.info(`Failed:          ${failed.length}`);
    logger.info(`Outros:          ${others.length}`);
    const passRate = allResults.length > 0 ? ((passed.length / allResults.length) * 100).toFixed(1) : '0';
    logger.info(`Taxa de sucesso: ${passRate}%`);

    if (diagnoses.length) {
      logger.info('\n🔧 Testes falhados (para @fastqa:verify_and_fix):');
      for (const d of diagnoses) {
        logger.error(`  • ${d.testName}`);
        if (d.errorMessage) logger.error(`    Erro: ${d.errorMessage.substring(0, 200)}`);
      }
      logger.info('\n💡 Execute @fastqa:verify_and_fix para corrigir automaticamente os testes falhados.');
    } else {
      logger.success('🎉 Todos os testes passaram!');
    }
    logger.info('═══════════════════════════════════════════════════════════');

    if (failed.length) process.exit(2);
  }, 'verify-pipeline-results');
}

// ---------------------------------------------------------------------------
// Report Generator
// ---------------------------------------------------------------------------

function generateDiagnosticReport(
  args: VerifyPipelineArgs,
  build: Build,
  allResults: TestResult[],
  diagnoses: FailedTestDiagnosis[]
): string {
  const passed = allResults.filter(r => r.outcome === 'Passed').length;
  const failed = allResults.filter(r => r.outcome === 'Failed').length;
  const passRate = allResults.length > 0 ? ((passed / allResults.length) * 100).toFixed(1) : '0';

  let report = `# 📊 Pipeline Verification Report — Build #${build.id}

**Gerado:** ${new Date().toISOString()}
**Build:** #${build.id} (${build.buildNumber})
**Resultado:** ${build.result}
**Branch:** ${build.sourceBranch}
**Test Plan:** #${args.testPlanId} | **Test Suite:** #${args.testSuiteId}

## 📈 Resumo

| Métrica | Valor |
|---------|-------|
| Total de testes | ${allResults.length} |
| ✅ Passed | ${passed} |
| ❌ Failed | ${failed} |
| Outros | ${allResults.length - passed - failed} |
| Taxa de sucesso | ${passRate}% |

`;

  if (diagnoses.length) {
    report += `## ❌ Testes Falhados — Diagnóstico para Auto-Healing

`;
    for (let i = 0; i < diagnoses.length; i++) {
      const d = diagnoses[i];
      report += `### ${i + 1}. ${d.testName}

**Outcome:** ${d.outcome}
`;
      if (d.duration) report += `**Duração:** ${d.duration}ms\n`;
      if (d.errorMessage) report += `\n**Erro:**\n\`\`\`\n${d.errorMessage}\n\`\`\`\n`;
      if (d.stackTrace) report += `\n**Stack Trace:**\n\`\`\`\n${d.stackTrace}\n\`\`\`\n`;
      if (d.logExcerpt) report += `\n**Log da Build (trecho relevante):**\n\`\`\`\n${d.logExcerpt}\n\`\`\`\n`;
      report += '\n---\n\n';
    }

    report += `## 🔧 Próximos Passos

1. Execute \`@fastqa:verify_and_fix\` passando os arquivos de teste falhados com o contexto de erro acima
2. Após correção, execute \`@fastqa:azdo_push_automation\` para enviar código corrigido
3. Execute \`@fastqa:azdo_run_pipeline\` para re-executar a pipeline
4. Execute \`@fastqa:azdo_verify_pipeline_results\` novamente para verificar o resultado

### Comando sugerido para auto-healing:
\`\`\`
@fastqa:verify_and_fix
\`\`\`
`;
  }

  return report;
}

main().catch((err) => {
  console.error('❌ Erro fatal:', err.message || err);
  process.exit(1);
});
