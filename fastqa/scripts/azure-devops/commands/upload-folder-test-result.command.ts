/**
 * ============================================================================
 * FastQA — Upload de Pasta de Evidências para Test Result
 * ============================================================================
 * Script para upload de todos os arquivos de uma pasta de evidências
 * para um Test Result no Azure DevOps.
 *
 * Fluxo:
 *   1. Lista arquivos da pasta (filtro por extensões permitidas)
 *   2. Obtém Test Point → Cria Test Run → Obtém Test Result
 *   3. Upload de cada arquivo como attachment do Test Result
 *   4. Atualiza outcome e finaliza Test Run
 *
 * Uso:
 *   npx tsx upload-folder-test-result.command.ts \
 *     --test-plan-id 29 \
 *     --test-suite-id 38 \
 *     --test-case-id 15 \
 *     --folder-path "fastqa/manual_test/evidence/TC-15" \
 *     --result Passed \
 *     --comment "Evidências da execução manual" \
 *     --attach-to-work-item false
 * ============================================================================
 */

import * as path from 'path';
import * as fs from 'fs';
import { AzureDevOpsClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';
import type { TestOutcome } from '../types/azure-devops.types';

function collectFolderFiles(
  folderPath: string,
  recursive: boolean = true,
  extensionsFilter?: string[]
): string[] {
  const resolved = path.resolve(folderPath);

  if (!fs.existsSync(resolved)) {
    throw new Error(`Pasta não encontrada: ${resolved}`);
  }

  if (!fs.statSync(resolved).isDirectory()) {
    throw new Error(`Caminho não é um diretório: ${resolved}`);
  }

  const allowedExts = extensionsFilter || config.allowedExtensions;
  const results: string[] = [];

  function walk(dir: string) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isFile()) {
        const ext = path.extname(entry.name).toLowerCase();
        if (allowedExts.includes(ext)) {
          results.push(fullPath);
        }
      } else if (entry.isDirectory() && recursive) {
        walk(fullPath);
      }
    }
  }

  walk(resolved);
  return results.sort();
}

function validateOutcome(value: string): TestOutcome {
  const valid: TestOutcome[] = [
    'Passed', 'Failed', 'Blocked', 'NotApplicable',
    'NotExecuted', 'Inconclusive', 'Timeout', 'Aborted', 'None',
  ];
  if (!valid.includes(value as TestOutcome)) {
    throw new Error(`Resultado inválido: "${value}". Aceitos: ${valid.join(', ')}`);
  }
  return value as TestOutcome;
}

async function uploadFolderEvidenceToTestResult(params: {
  testPlanId: number;
  testSuiteId: number;
  testCaseId: number;
  folderPath: string;
  result: TestOutcome;
  comment?: string;
  attachToWorkItem?: boolean;
  recursive?: boolean;
  extensions?: string[];
}) {
  const client = new AzureDevOpsClient('UploadFolderTestResult');

  console.log('\n📁 ═══════════════════════════════════════════════════════════════');
  console.log('   FastQA — Upload de Pasta para Test Result');
  console.log('═══════════════════════════════════════════════════════════════\n');

  console.log(`   Test Plan ID:  ${params.testPlanId}`);
  console.log(`   Test Suite ID: ${params.testSuiteId}`);
  console.log(`   Test Case ID:  ${params.testCaseId}`);
  console.log(`   Pasta:         ${params.folderPath}`);
  console.log(`   Resultado:     ${params.result}`);
  console.log(`   Recursivo:     ${params.recursive !== false ? 'Sim' : 'Não'}`);
  console.log('');

  const files = collectFolderFiles(
    params.folderPath,
    params.recursive !== false,
    params.extensions
  );

  if (files.length === 0) {
    console.error('❌ Nenhum arquivo válido encontrado na pasta.');
    console.error(`   Extensões permitidas: ${config.allowedExtensions.join(', ')}`);
    process.exit(1);
  }

  let totalSize = 0;
  console.log(`📂 ${files.length} arquivo(s) encontrados:\n`);
  for (const filePath of files) {
    const size = fs.statSync(filePath).size;
    totalSize += size;
    const sizeMB = (size / (1024 * 1024)).toFixed(2);
    console.log(`   📄 ${path.basename(filePath)} (${sizeMB} MB)`);
  }
  const totalMB = (totalSize / (1024 * 1024)).toFixed(2);
  console.log(`\n   Total: ${totalMB} MB\n`);

  console.log('🔄 Criando Test Run e enviando evidências...\n');

  const comment =
    params.comment || `FastQA — Upload de pasta para test result — ${new Date().toISOString()}`;

  const flowResult = await client.executeTestUploadFlow({
    testPlanId: params.testPlanId,
    testSuiteId: params.testSuiteId,
    testCaseId: params.testCaseId,
    evidencePaths: files,
    outcome: params.result,
    comment,
  });

  const { testRun, testResult, attachments } = flowResult;

  if (params.attachToWorkItem && files.length > 0) {
    console.log(`\n📎 Anexando ao Work Item #${params.testCaseId}...`);
    for (const filePath of files) {
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

  const testRunUrl = testRun.webAccessUrl ||
    `${config.orgUrl}/${encodeURIComponent(config.project)}/_testManagement/runs?runId=${testRun.id}&_a=runCharts`;

  console.log('\n═══════════════════════════════════════════════════════════════');
  console.log('✅ Upload de pasta para Test Result concluído!');
  console.log('═══════════════════════════════════════════════════════════════\n');
  console.log(`   Test Run:     #${testRun.id}`);
  console.log(`   Test Result:  #${testResult.id}`);
  console.log(`   Outcome:      ${params.result}`);
  console.log(`   Arquivos:     ${attachments.length}/${files.length} enviados`);
  console.log(`   Tamanho:      ${totalMB} MB`);
  console.log(`\n   🔗 ${testRunUrl}\n`);

  const logsDir = config.logsDir;
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }
  const logPath = path.join(logsDir, `folder-test-result-${params.testCaseId}-${Date.now()}.json`);
  fs.writeFileSync(logPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    command: 'upload-folder-test-result',
    testRunId: testRun.id,
    testResultId: testResult.id,
    outcome: params.result,
    totalFiles: files.length,
    uploadedFiles: attachments.length,
    totalSizeMB: totalMB,
    files: files.map(filePath => path.basename(filePath)),
  }, null, 2), 'utf-8');
  console.log(`   📝 Log: ${logPath}\n`);
}

async function main() {
  const args = process.argv.slice(2);
  const getArg = (flag: string): string | undefined => {
    const index = args.indexOf(flag);
    return index >= 0 && index + 1 < args.length ? args[index + 1] : undefined;
  };

  const testPlanId = getArg('--test-plan-id');
  const testSuiteId = getArg('--test-suite-id');
  const testCaseId = getArg('--test-case-id');
  const folderPath = getArg('--folder-path');
  const result = getArg('--result');
  const comment = getArg('--comment');
  const attachToWorkItem = getArg('--attach-to-work-item');
  const recursive = getArg('--recursive');
  const extensions = getArg('--extensions');

  if (!testPlanId || !testSuiteId || !testCaseId || !folderPath || !result) {
    console.error('\n❌ Parâmetros obrigatórios faltando.\n');
    console.error('Uso:');
    console.error('  npx tsx upload-folder-test-result.command.ts \\');
    console.error('    --test-plan-id <id> \\');
    console.error('    --test-suite-id <id> \\');
    console.error('    --test-case-id <id> \\');
    console.error('    --folder-path <caminho> \\');
    console.error('    --result <Passed|Failed|Blocked|NotApplicable>\n');
    console.error('Opcionais:');
    console.error('    --comment <texto>');
    console.error('    --attach-to-work-item <true|false>');
    console.error('    --recursive <true|false>');
    console.error('    --extensions ".png,.mp4,.pdf"\n');
    process.exit(1);
  }

  try {
    await uploadFolderEvidenceToTestResult({
      testPlanId: parseInt(testPlanId, 10),
      testSuiteId: parseInt(testSuiteId, 10),
      testCaseId: parseInt(testCaseId, 10),
      folderPath,
      result: validateOutcome(result),
      comment,
      attachToWorkItem: attachToWorkItem === 'true',
      recursive: recursive !== 'false',
      extensions: extensions ? extensions.split(',').map(ext => ext.trim()) : undefined,
    });

    process.exit(0);
  } catch (error) {
    console.error('\n❌ Erro:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { uploadFolderEvidenceToTestResult, collectFolderFiles };
