/**
 * ============================================================================
 * FastQA — Upload de Execução de Teste (Test Run Completo)
 * ============================================================================
 * Script para criar um Test Run no Azure DevOps, anexar evidências ao
 * Test Result, atualizar o outcome (Passed/Failed) e finalizar o Run.
 *
 * Fluxo completo:
 *   1. Obtém Test Point (Plan → Suite → Test Case)
 *   2. Cria Test Run
 *   3. Obtém Test Result do Run
 *   4. Upload de todas as evidências como attachments do Test Result
 *   5. Atualiza outcome (Passed/Failed/Blocked)
 *   6. Finaliza Test Run com status Completed
 *   7. [Opcional] Cria Bug automaticamente se resultado = Failed
 *
 * Uso:
 *   npx tsx upload-test-execution.command.ts \
 *     --test-plan-id 29 \
 *     --test-suite-id 38 \
 *     --test-case-id 15 \
 *     --evidence-path "fastqa/manual_test/evidence/TC-15" \
 *     --result Passed \
 *     --comment "Execução manual via Playwright MCP" \
 *     --auto-bug false \
 *     --bug-severity "3 - Medium"
 * ============================================================================
 */

import * as path from 'path';
import * as fs from 'fs';
import { AzureDevOpsClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';
import type {
  TestOutcome,
  JsonPatchOperation,
} from '../types/azure-devops.types';

// ─────────────────────────────────────────────────────────────────────
// Utilitários
// ─────────────────────────────────────────────────────────────────────

/**
 * Coleta arquivos de evidência de um caminho (arquivo ou diretório).
 * Filtra por extensões permitidas na configuração.
 */
function collectEvidenceFiles(evidencePath: string): string[] {
  const resolvedPath = path.resolve(evidencePath);

  if (!fs.existsSync(resolvedPath)) {
    console.warn(`⚠️  Caminho não encontrado: ${resolvedPath}`);
    return [];
  }

  const stat = fs.statSync(resolvedPath);

  if (stat.isFile()) {
    return [resolvedPath];
  }

  if (stat.isDirectory()) {
    const files = fs.readdirSync(resolvedPath);
    const allowedExts = config.allowedExtensions;
    const evidenceFiles = files
      .filter((f) => {
        const ext = path.extname(f).toLowerCase();
        return allowedExts.includes(ext);
      })
      .sort() // Ordenar para manter consistência (step-01, step-02, etc.)
      .map((f) => path.join(resolvedPath, f));
    return evidenceFiles;
  }

  return [];
}

/**
 * Valida o valor do resultado da execução.
 */
function validateOutcome(value: string): TestOutcome {
  const valid: TestOutcome[] = [
    'Passed',
    'Failed',
    'Blocked',
    'NotApplicable',
    'NotExecuted',
    'Inconclusive',
    'Timeout',
    'Aborted',
    'None',
  ];
  if (!valid.includes(value as TestOutcome)) {
    throw new Error(
      `❌ Resultado inválido: "${value}". Valores aceitos: ${valid.join(', ')}`
    );
  }
  return value as TestOutcome;
}

// ─────────────────────────────────────────────────────────────────────
// Função Principal
// ─────────────────────────────────────────────────────────────────────

async function uploadTestExecution(params: {
  testPlanId: number;
  testSuiteId: number;
  testCaseId: number;
  evidencePath: string;
  result: TestOutcome;
  comment?: string;
  autoBug?: boolean;
  bugSeverity?: string;
  attachToWorkItem?: boolean;
}) {
  const client = new AzureDevOpsClient('UploadTestExecution');

  console.log('\n🚀 ═══════════════════════════════════════════════════════════════');
  console.log('   FastQA — Upload de Execução de Teste (Test Run Completo)');
  console.log('═══════════════════════════════════════════════════════════════\n');

  console.log(`   Test Plan ID:  ${params.testPlanId}`);
  console.log(`   Test Suite ID: ${params.testSuiteId}`);
  console.log(`   Test Case ID:  ${params.testCaseId}`);
  console.log(`   Resultado:     ${params.result}`);
  console.log(`   Evidências:    ${params.evidencePath}`);
  if (params.comment) {
    console.log(`   Comentário:    ${params.comment}`);
  }
  if (params.autoBug) {
    console.log(`   Auto Bug:      Sim (Severidade: ${params.bugSeverity || '3 - Medium'})`);
  }
  console.log('');

  // ── 1. Coletar arquivos de evidência ──────────────────────────────

  const evidenceFiles = collectEvidenceFiles(params.evidencePath);

  if (evidenceFiles.length === 0) {
    console.warn(`⚠️  Nenhum arquivo de evidência encontrado em: ${params.evidencePath}`);
    console.warn('   Continuando sem evidências...\n');
  } else {
    console.log(`📂 Encontrados ${evidenceFiles.length} arquivo(s) de evidência:`);
    for (const f of evidenceFiles) {
      const size = fs.statSync(f).size;
      const sizeMB = (size / (1024 * 1024)).toFixed(2);
      console.log(`   📄 ${path.basename(f)} (${sizeMB} MB)`);
    }
    console.log('');
  }

  // ── 2. Executar fluxo completo de Test Run ────────────────────────

  console.log('🔄 Executando fluxo completo de Test Run...\n');

  const comment =
    params.comment ||
    `FastQA — Execução manual via Playwright MCP — ${new Date().toISOString()}`;

  const flowResult = await client.executeTestUploadFlow({
    testPlanId: params.testPlanId,
    testSuiteId: params.testSuiteId,
    testCaseId: params.testCaseId,
    evidencePaths: evidenceFiles,
    outcome: params.result,
    comment,
  });

  const { testRun, testResult, attachments } = flowResult;

  // ── 3. Exibir resultados do Test Run ──────────────────────────────

  const testRunUrl = testRun.webAccessUrl ||
    `${config.orgUrl}/${encodeURIComponent(config.project)}/_testManagement/runs?runId=${testRun.id}&_a=runCharts`;

  console.log('═══════════════════════════════════════════════════════════════');
  console.log('✅ Test Run criado e finalizado com sucesso!');
  console.log('═══════════════════════════════════════════════════════════════\n');
  console.log(`   Test Run ID:      #${testRun.id}`);
  console.log(`   Test Run Name:    ${testRun.name}`);
  console.log(`   Test Run State:   ${testRun.state}`);
  console.log(`   Test Result ID:   #${testResult.id}`);
  console.log(`   Outcome:          ${params.result}`);
  console.log(`   Evidências:       ${attachments.length} arquivo(s) anexados`);
  console.log(`\n   🔗 ${testRunUrl}`);

  // ── 4. Anexar ao Work Item (opcional) ─────────────────────────────

  if (params.attachToWorkItem && evidenceFiles.length > 0) {
    console.log(`\n📎 Anexando evidências ao Work Item #${params.testCaseId}...`);
    for (const filePath of evidenceFiles) {
      try {
        const fileName = path.basename(filePath);
        const attachment = await client.uploadAttachment(filePath, fileName);
        await client.attachToWorkItem(
          params.testCaseId,
          attachment.url,
          `Evidência Test Run #${testRun.id}: ${fileName}`
        );
        console.log(`   ✅ ${fileName}`);
      } catch (error) {
        console.error(`   ❌ ${path.basename(filePath)}: ${error}`);
      }
    }
  }

  // ── 5. Criar Bug automaticamente (opcional) ───────────────────────

  let bugId: number | undefined;
  let bugUrl: string | undefined;

  if (params.autoBug && params.result === 'Failed') {
    console.log('\n🐛 Criando Bug automaticamente (resultado = Failed)...\n');

    const severity = params.bugSeverity || '3 - Medium';

    // Obter título do Test Case
    let testCaseTitle = `TC-${params.testCaseId}`;
    try {
      const workItem = await client.getWorkItem(params.testCaseId, 'fields');
      testCaseTitle =
        workItem.fields?.['System.Title'] || testCaseTitle;
    } catch {
      // Ignorar — usar título genérico
    }

    const bugTitle = `[AUTO-BUG] Falha no TC-${params.testCaseId}: ${testCaseTitle}`;

    const reproSteps = AzureDevOpsClient.buildBugReproStepsHtml({
      reproSteps: `<p>Bug criado automaticamente pelo FastQA após falha no Test Case #${params.testCaseId}.</p>
<p>Test Run: #${testRun.id}</p>
<p>Test Result: #${testResult.id}</p>
<p>Comentário: ${comment}</p>`,
      expectedResult: 'Teste deveria ter passado conforme cenário Gherkin.',
      actualResult: `Teste falhou. Veja evidências anexadas ao Test Run #${testRun.id}.`,
      environment: `Data: ${new Date().toISOString()}`,
    });

    const bugOperations: JsonPatchOperation[] = [
      { op: 'add', path: '/fields/System.Title', value: bugTitle },
      { op: 'add', path: '/fields/Microsoft.VSTS.TCM.ReproSteps', value: reproSteps },
      { op: 'add', path: '/fields/Microsoft.VSTS.Common.Severity', value: severity },
      { op: 'add', path: '/fields/Microsoft.VSTS.Common.Priority', value: mapSeverityToPriority(severity) },
      { op: 'add', path: '/fields/System.Tags', value: 'auto-bug; fastqa; test-execution' },
    ];

    try {
      const bug = await client.createWorkItem('Bug', bugOperations);
      bugId = bug.id;
      bugUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_workitems/edit/${bug.id}`;

      console.log(`   ✅ Bug #${bugId} criado: "${bugTitle}"`);
      console.log(`   🔗 ${bugUrl}`);

      // Vincular Bug ao Test Case como "Tests"
      try {
        await client.linkWorkItems(bug.id, params.testCaseId, 'related', `Bug criado por falha no Test Run #${testRun.id}`);
        console.log(`   🔗 Bug #${bugId} vinculado ao TC #${params.testCaseId} (related)`);
      } catch (linkError) {
        console.warn(`   ⚠️  Falha ao vincular Bug ao TC: ${linkError}`);
      }

      // Anexar evidências ao Bug
      if (evidenceFiles.length > 0) {
        console.log(`\n   📎 Anexando evidências ao Bug #${bugId}...`);
        for (const filePath of evidenceFiles) {
          try {
            const fileName = path.basename(filePath);
            const attachment = await client.uploadAttachment(filePath, fileName);
            await client.attachToWorkItem(
              bugId,
              attachment.url,
              `Evidência de falha — Test Run #${testRun.id}: ${fileName}`
            );
            console.log(`      ✅ ${fileName}`);
          } catch (error) {
            console.error(`      ❌ ${path.basename(filePath)}: ${error}`);
          }
        }
      }
    } catch (bugError) {
      console.error(`\n   ❌ Falha ao criar Bug: ${bugError}`);
    }
  }

  // ── 6. Resumo Final ───────────────────────────────────────────────

  console.log('\n═══════════════════════════════════════════════════════════════');
  console.log('📊 RESUMO DA EXECUÇÃO');
  console.log('═══════════════════════════════════════════════════════════════\n');
  console.log(`   Test Plan:        #${params.testPlanId}`);
  console.log(`   Test Suite:       #${params.testSuiteId}`);
  console.log(`   Test Case:        #${params.testCaseId}`);
  console.log(`   Test Run:         #${testRun.id}`);
  console.log(`   Test Result:      #${testResult.id}`);
  console.log(`   Outcome:          ${params.result}`);
  console.log(`   Evidências:       ${attachments.length}/${evidenceFiles.length} anexadas`);
  if (bugId) {
    console.log(`   Bug Criado:       #${bugId}`);
  }
  console.log(`\n   🔗 Test Run: ${testRunUrl}`);
  if (bugUrl) {
    console.log(`   🔗 Bug:      ${bugUrl}`);
  }
  console.log('');

  // ── 7. Salvar log da execução ─────────────────────────────────────

  const logData = {
    timestamp: new Date().toISOString(),
    command: 'upload-test-execution',
    params: {
      testPlanId: params.testPlanId,
      testSuiteId: params.testSuiteId,
      testCaseId: params.testCaseId,
      result: params.result,
      comment,
    },
    results: {
      testRunId: testRun.id,
      testRunUrl,
      testResultId: testResult.id,
      outcome: params.result,
      attachmentsCount: attachments.length,
      evidenceFiles: evidenceFiles.map((f) => path.basename(f)),
      bugId,
      bugUrl,
    },
  };

  const logsDir = config.logsDir;
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }

  const logFileName = `execution-${params.testCaseId}-${Date.now()}.json`;
  const logFilePath = path.join(logsDir, logFileName);
  fs.writeFileSync(logFilePath, JSON.stringify(logData, null, 2), 'utf-8');
  console.log(`   📝 Log salvo em: ${logFilePath}\n`);
}

// ─────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────

/** Mapeia severidade para prioridade numérica */
function mapSeverityToPriority(severity: string): number {
  if (severity.startsWith('1')) return 1;
  if (severity.startsWith('2')) return 2;
  if (severity.startsWith('3')) return 3;
  return 4;
}

// ─────────────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  const getArg = (flag: string): string | undefined => {
    const index = args.indexOf(flag);
    return index >= 0 && index + 1 < args.length ? args[index + 1] : undefined;
  };

  const testPlanId = getArg('--test-plan-id');
  const testSuiteId = getArg('--test-suite-id');
  const testCaseId = getArg('--test-case-id');
  const evidencePath = getArg('--evidence-path');
  const result = getArg('--result');
  const comment = getArg('--comment');
  const autoBug = getArg('--auto-bug');
  const bugSeverity = getArg('--bug-severity');
  const attachToWorkItem = getArg('--attach-to-work-item');

  // Validação de parâmetros obrigatórios
  if (!testPlanId || !testSuiteId || !testCaseId || !evidencePath || !result) {
    console.error('');
    console.error('❌ Parâmetros obrigatórios faltando.');
    console.error('');
    console.error('Uso:');
    console.error('  npx tsx upload-test-execution.command.ts \\');
    console.error('    --test-plan-id <id> \\');
    console.error('    --test-suite-id <id> \\');
    console.error('    --test-case-id <id> \\');
    console.error('    --evidence-path <path> \\');
    console.error('    --result <Passed|Failed|Blocked|NotApplicable>');
    console.error('');
    console.error('Parâmetros opcionais:');
    console.error('    --comment <texto>');
    console.error('    --auto-bug <true|false>');
    console.error('    --bug-severity <"1 - Critical"|"2 - High"|"3 - Medium"|"4 - Low">');
    console.error('    --attach-to-work-item <true|false>');
    console.error('');
    process.exit(1);
  }

  try {
    const outcome = validateOutcome(result);

    await uploadTestExecution({
      testPlanId: parseInt(testPlanId),
      testSuiteId: parseInt(testSuiteId),
      testCaseId: parseInt(testCaseId),
      evidencePath,
      result: outcome,
      comment,
      autoBug: autoBug === 'true',
      bugSeverity: bugSeverity || '3 - Medium',
      attachToWorkItem: attachToWorkItem === 'true',
    });

    process.exit(0);
  } catch (error) {
    console.error('\n❌ Erro na execução do teste:');
    console.error(error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { uploadTestExecution, collectEvidenceFiles };
