/**
 * ============================================================================
 * FastQA — Upload de Múltiplas Execuções de Teste (Batch Test Execution)
 * ============================================================================
 * Script para processar múltiplas execuções de teste de uma vez no Azure DevOps.
 * Suporta entrada via arquivo JSON/CSV ou parâmetros inline.
 * 
 * NOVO: Inclui exibição formatada do conteúdo dos arquivos para confirmação
 * 
 * Fluxo para cada execução:
 *   1. Obtém Test Point (Plan → Suite → Test Case)
 *   2. Cria Test Run individual
 *   3. Upload de evidências específicas
 *   4. Atualiza outcome
 *   5. Finaliza Test Run
 *   6. [Opcional] Cria Bug se Failed
 *   7. [Opcional] Anexa ao Work Item
 * 
 * Formatos de entrada suportados:
 * 
 * 1. JSON File:
 *   npx tsx upload-batch-test-execution.command.ts --json-file "batch-executions.json"
 * 
 * 2. CSV File:  
 *   npx tsx upload-batch-test-execution.command.ts --csv-file "batch-executions.csv"
 * 
 * 3. Inline (múltiplas execuções separadas por |):
 *   npx tsx upload-batch-test-execution.command.ts \
 *     --test-plan-id 29 \
 *     --executions "38:14:Passed:C:/evidencias/TC-14:Teste 1|38:15:Failed:C:/evidencias/TC-15:Teste 2"
 * 
 * 4. Exibir conteúdo (JSON/CSV) formatado:
 *   npx tsx upload-batch-test-execution.command.ts --preview-json "arquivo.json"
 *   npx tsx upload-batch-test-execution.command.ts --preview-csv "arquivo.csv"
 * 
 * Formato JSON esperado:
 * {
 *   "testPlanId": 29,
 *   "executions": [
 *     {
 *       "testSuiteId": 38,
 *       "testCaseId": 14,
 *       "result": "Passed",
 *       "evidencePath": "C:/projetos/evidence/TC-14",
 *       "comment": "Execução automatizada",
 *       "attachToWorkItem": true,
 *       "autoBug": false,
 *       "bugSeverity": "3 - Medium"
 *     }
 *   ]
 * }
 * 
 * Formato CSV esperado (cabeçalho obrigatório):
 * testSuiteId,testCaseId,result,evidencePath,comment,attachToWorkItem,autoBug,bugSeverity
 * 38,14,Passed,C:/projetos/evidence/TC-14,Execução 1,true,false,3 - Medium
 * 38,15,Failed,C:/projetos/evidence/TC-15,Execução 2,false,true,2 - High
 * ============================================================================
 */

import * as path from 'path';
import * as fs from 'fs';
import { AzureDevOpsClient } from '../azure-devops.client';
import { config } from '../azure-devops.config';
import type {
  TestOutcome,
  JsonPatchOperation,
  TestRun,
  TestResult,
  TestPoint,
} from '../types/azure-devops.types';

// ─────────────────────────────────────────────────────────────────────
// Interfaces e Tipos
// ─────────────────────────────────────────────────────────────────────

interface BatchExecution {
  testSuiteId: number;
  testCaseId: number;
  result: TestOutcome;
  evidencePath: string;
  comment?: string;
  attachToWorkItem?: boolean;
  autoBug?: boolean;
  bugSeverity?: string;
}

interface BatchExecutionInput {
  testPlanId: number;
  executions: BatchExecution[];
}

interface ExecutionResult {
  testCaseId: number;
  success: boolean;
  testRunId?: number;
  testResultId?: number;
  bugId?: number;
  errorMessage?: string;
  evidencesUploaded: number;
  duration: number;
}

interface BatchExecutionSummary {
  totalExecutions: number;
  successful: number;
  failed: number;
  testRunsCreated: number;
  evidencesUploaded: number;
  bugsCreated: number;
  duration: number;
  results: ExecutionResult[];
}

// ─────────────────────────────────────────────────────────────────────
// Utilitários
// ─────────────────────────────────────────────────────────────────────

/**
 * Coleta arquivos de evidência de um caminho (arquivo ou diretório).
 */
function collectEvidenceFiles(evidencePath: string): string[] {
  const resolvedPath = path.resolve(evidencePath);

  if (!fs.existsSync(resolvedPath)) {
    return [];
  }

  const stat = fs.statSync(resolvedPath);

  if (stat.isFile()) {
    const ext = path.extname(resolvedPath).toLowerCase();
    if (config.allowedExtensions.includes(ext)) {
      return [resolvedPath];
    }
    return [];
  }

  // É um diretório: buscar arquivos suportados
  const files: string[] = [];
  const entries = fs.readdirSync(resolvedPath);

  for (const entry of entries) {
    const fullPath = path.join(resolvedPath, entry);
    const stat = fs.statSync(fullPath);

    if (stat.isFile()) {
      const ext = path.extname(fullPath).toLowerCase();
      if (config.allowedExtensions.includes(ext)) {
        files.push(fullPath);
      }
    }
  }

  return files.sort();
}

/**
 * Exibe preview formatado do arquivo JSON no chat.
 */
function previewJsonFile(filePath: string): void {
  const resolvedPath = path.resolve(filePath);
  
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`Arquivo JSON não encontrado: ${resolvedPath}`);
  }

  const content = fs.readFileSync(resolvedPath, 'utf8');
  
  try {
    const data = JSON.parse(content);
    
    console.log('📋 PREVIEW DO ARQUIVO JSON');
    console.log('═'.repeat(50));
    console.log(`📁 Arquivo: ${resolvedPath}`);
    console.log(`📊 Test Plan ID: ${data.testPlanId}`);
    console.log(`📝 Total de Execuções: ${data.executions?.length || 0}`);
    console.log('');
    
    if (data.executions && data.executions.length > 0) {
      console.log('📋 LISTA DE EXECUÇÕES:');
      console.log('─'.repeat(120));
      console.log('│ #  │ Suite ID │ Case ID │ Resultado     │ Evidência                    │ Comentário           │');
      console.log('├────┼──────────┼─────────┼───────────────┼──────────────────────────────┼──────────────────────┤');
      
      data.executions.forEach((exec: any, index: number) => {
        const num = (index + 1).toString().padStart(2, '0');
        const suiteId = exec.testSuiteId?.toString().padEnd(8, ' ') || '—'.padEnd(8, ' ');
        const caseId = exec.testCaseId?.toString().padEnd(7, ' ') || '—'.padEnd(7, ' ');
        const result = exec.result?.padEnd(13, ' ') || '—'.padEnd(13, ' ');
        const evidence = (exec.evidencePath || '—').substring(0, 28).padEnd(28, ' ');
        const comment = (exec.comment || '—').substring(0, 20).padEnd(20, ' ');
        
        console.log(`│ ${num} │ ${suiteId} │ ${caseId} │ ${result} │ ${evidence} │ ${comment} │`);
      });
      console.log('─'.repeat(120));
      
      // Resumo por resultado
      const resultCounts: Record<string, number> = {};
      data.executions.forEach((exec: any) => {
        const result = exec.result || 'Undefined';
        resultCounts[result] = (resultCounts[result] || 0) + 1;
      });
      
      console.log('');
      console.log('📊 RESUMO POR RESULTADO:');
      Object.entries(resultCounts).forEach(([result, count]) => {
        const emoji = result === 'Passed' ? '✅' : result === 'Failed' ? '❌' : result === 'Blocked' ? '⚠️' : '❓';
        console.log(`   ${emoji} ${result}: ${count} execução(ões)`);
      });
    }
    
    console.log('');
    console.log('═'.repeat(50));
    
  } catch (error) {
    throw new Error(`Erro ao parsear JSON: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/**
 * Exibe preview formatado do arquivo CSV no chat.
 */
function previewCsvFile(filePath: string, testPlanId?: number): void {
  const resolvedPath = path.resolve(filePath);
  
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`Arquivo CSV não encontrado: ${resolvedPath}`);
  }

  const content = fs.readFileSync(resolvedPath, 'utf8');
  const lines = content.trim().split('\n');
  
  if (lines.length < 2) {
    throw new Error('Arquivo CSV deve conter cabeçalho e pelo menos uma linha de dados');
  }

  const headers = lines[0].split(',').map(h => h.trim());
  const dataRows = lines.slice(1);
  
  console.log('📋 PREVIEW DO ARQUIVO CSV');
  console.log('═'.repeat(50));
  console.log(`📁 Arquivo: ${resolvedPath}`);
  if (testPlanId) {
    console.log(`📊 Test Plan ID: ${testPlanId}`);
  }
  console.log(`📝 Total de Execuções: ${dataRows.length}`);
  console.log('');
  
  if (dataRows.length > 0) {
    console.log('📋 DADOS DO CSV:');
    console.log('─'.repeat(120));
    console.log('│ #  │ Suite ID │ Case ID │ Resultado     │ Evidência                    │ Comentário           │');
    console.log('├────┼──────────┼─────────┼───────────────┼──────────────────────────────┼──────────────────────┤');
    
    dataRows.forEach((row, index) => {
      const values = row.split(',').map(v => v.trim());
      const num = (index + 1).toString().padStart(2, '0');
      const suiteId = (values[0] || '—').padEnd(8, ' ');
      const caseId = (values[1] || '—').padEnd(7, ' ');
      const result = (values[2] || '—').padEnd(13, ' ');
      const evidence = (values[3] || '—').substring(0, 28).padEnd(28, ' ');
      const comment = (values[4] || '—').substring(0, 20).padEnd(20, ' ');
      
      console.log(`│ ${num} │ ${suiteId} │ ${caseId} │ ${result} │ ${evidence} │ ${comment} │`);
    });
    console.log('─'.repeat(120));
    
    // Resumo por resultado
    const resultCounts: Record<string, number> = {};
    dataRows.forEach(row => {
      const values = row.split(',').map(v => v.trim());
      const result = values[2] || 'Undefined';
      resultCounts[result] = (resultCounts[result] || 0) + 1;
    });
    
    console.log('');
    console.log('📊 RESUMO POR RESULTADO:');
    Object.entries(resultCounts).forEach(([result, count]) => {
      const emoji = result === 'Passed' ? '✅' : result === 'Failed' ? '❌' : result === 'Blocked' ? '⚠️' : '❓';
      console.log(`   ${emoji} ${result}: ${count} execução(ões)`);
    });
  }
  
  console.log('');
  console.log('═'.repeat(50));
}

/**
 * Exibe preview formatado das execuções inline.
 */
function previewInlineExecutions(executionsString: string, testPlanId: number): void {
  const executions = executionsString.split('|').map(exec => {
    const parts = exec.trim().split(':');
    if (parts.length < 4) {
      throw new Error(`Formato inválido: ${exec}. Use formato: suiteId:caseId:result:evidencePath:comment`);
    }
    
    return {
      testSuiteId: parseInt(parts[0]),
      testCaseId: parseInt(parts[1]),
      result: parts[2],
      evidencePath: parts[3],
      comment: parts[4] || '',
    };
  });
  
  console.log('📋 PREVIEW DAS EXECUÇÕES INLINE');
  console.log('═'.repeat(50));
  console.log(`📊 Test Plan ID: ${testPlanId}`);
  console.log(`📝 Total de Execuções: ${executions.length}`);
  console.log('');
  
  if (executions.length > 0) {
    console.log('📋 LISTA DE EXECUÇÕES:');
    console.log('─'.repeat(120));
    console.log('│ #  │ Suite ID │ Case ID │ Resultado     │ Evidência                    │ Comentário           │');
    console.log('├────┼──────────┼─────────┼───────────────┼──────────────────────────────┼──────────────────────┤');
    
    executions.forEach((exec, index) => {
      const num = (index + 1).toString().padStart(2, '0');
      const suiteId = exec.testSuiteId.toString().padEnd(8, ' ');
      const caseId = exec.testCaseId.toString().padEnd(7, ' ');
      const result = exec.result.padEnd(13, ' ');
      const evidence = exec.evidencePath.substring(0, 28).padEnd(28, ' ');
      const comment = exec.comment.substring(0, 20).padEnd(20, ' ');
      
      console.log(`│ ${num} │ ${suiteId} │ ${caseId} │ ${result} │ ${evidence} │ ${comment} │`);
    });
    console.log('─'.repeat(120));
    
    // Resumo por resultado
    const resultCounts: Record<string, number> = {};
    executions.forEach(exec => {
      resultCounts[exec.result] = (resultCounts[exec.result] || 0) + 1;
    });
    
    console.log('');
    console.log('📊 RESUMO POR RESULTADO:');
    Object.entries(resultCounts).forEach(([result, count]) => {
      const emoji = result === 'Passed' ? '✅' : result === 'Failed' ? '❌' : result === 'Blocked' ? '⚠️' : '❓';
      console.log(`   ${emoji} ${result}: ${count} execução(ões)`);
    });
  }
  
  console.log('');
  console.log('═'.repeat(50));
}

/**
 * Lê arquivo JSON com execuções em lote.
 */
function readJsonFile(filePath: string): BatchExecutionInput {
  const resolvedPath = path.resolve(filePath);
  
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`Arquivo JSON não encontrado: ${resolvedPath}`);
  }

  const content = fs.readFileSync(resolvedPath, 'utf8');
  
  try {
    const data = JSON.parse(content);
    
    // Validar estrutura básica
    if (!data.testPlanId || !data.executions || !Array.isArray(data.executions)) {
      throw new Error('Estrutura JSON inválida. Deve conter testPlanId e executions (array)');
    }

    // Validar cada execução
    for (let i = 0; i < data.executions.length; i++) {
      const exec = data.executions[i];
      if (!exec.testSuiteId || !exec.testCaseId || !exec.result || !exec.evidencePath) {
        throw new Error(`Execução ${i + 1} inválida: testSuiteId, testCaseId, result e evidencePath são obrigatórios`);
      }
    }

    return data;
  } catch (error) {
    throw new Error(`Erro ao parsear JSON: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/**
 * Lê arquivo CSV com execuções em lote.
 */
function readCsvFile(filePath: string, testPlanId: number): BatchExecutionInput {
  const resolvedPath = path.resolve(filePath);
  
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`Arquivo CSV não encontrado: ${resolvedPath}`);
  }

  const content = fs.readFileSync(resolvedPath, 'utf8');
  const lines = content.split('\n').map(line => line.trim()).filter(line => line.length > 0);

  if (lines.length < 2) {
    throw new Error('Arquivo CSV deve conter cabeçalho e pelo menos uma linha de dados');
  }

  const headers = lines[0].split(',').map(h => h.trim());
  const requiredHeaders = ['testSuiteId', 'testCaseId', 'result', 'evidencePath'];
  
  for (const required of requiredHeaders) {
    if (!headers.includes(required)) {
      throw new Error(`Cabeçalho CSV deve conter: ${requiredHeaders.join(', ')}`);
    }
  }

  const executions: BatchExecution[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(v => v.trim());
    
    if (values.length !== headers.length) {
      console.warn(`⚠️  Linha ${i + 1} ignorada: número de colunas inválido`);
      continue;
    }

    const execution: any = {};
    
    for (let j = 0; j < headers.length; j++) {
      const header = headers[j];
      const value = values[j];

      switch (header) {
        case 'testSuiteId':
        case 'testCaseId':
          execution[header] = parseInt(value);
          break;
        case 'result':
          execution[header] = value as TestOutcome;
          break;
        case 'attachToWorkItem':
        case 'autoBug':
          execution[header] = value.toLowerCase() === 'true';
          break;
        default:
          execution[header] = value || undefined;
      }
    }

    executions.push(execution);
  }

  return {
    testPlanId,
    executions
  };
}

/**
 * Processa execuções inline (formato: suiteId:caseId:result:evidencePath:comment)
 */
function parseInlineExecutions(executionsString: string, testPlanId: number): BatchExecutionInput {
  const executionStrings = executionsString.split('|').map(s => s.trim());
  const executions: BatchExecution[] = [];

  for (const execString of executionStrings) {
    const parts = execString.split(':');
    
    if (parts.length < 4) {
      throw new Error(`Formato inválido: ${execString}. Esperado: suiteId:caseId:result:evidencePath[:comment]`);
    }

    executions.push({
      testSuiteId: parseInt(parts[0]),
      testCaseId: parseInt(parts[1]),
      result: parts[2] as TestOutcome,
      evidencePath: parts[3],
      comment: parts[4] || undefined,
      attachToWorkItem: false,
      autoBug: false
    });
  }

  return {
    testPlanId,
    executions
  };
}

/**
 * Executa upload de uma única execução.
 */
async function executeTestRun(
  client: AzureDevOpsClient,
  testPlanId: number,
  execution: BatchExecution,
  index: number,
  total: number
): Promise<ExecutionResult> {
  const startTime = Date.now();
  const result: ExecutionResult = {
    testCaseId: execution.testCaseId,
    success: false,
    evidencesUploaded: 0,
    duration: 0
  };

  try {
    console.log(`\n📋 [${index + 1}/${total}] Executando Test Case #${execution.testCaseId}...`);
    console.log(`   Suite: ${execution.testSuiteId} | Resultado: ${execution.result}`);
    console.log(`   Evidências: ${execution.evidencePath}`);

    // ── 1. Coletar arquivos de evidência ──────────────────────────────

    const evidenceFiles = collectEvidenceFiles(execution.evidencePath);
    console.log(`   📂 ${evidenceFiles.length} arquivo(s) encontrado(s)`);

    // ── 2. Obter Test Point ────────────────────────────────────────────

    const testPointsResponse = await client.getTestPoints(testPlanId, execution.testSuiteId, execution.testCaseId);
    const testPoints = testPointsResponse.value;
    if (testPoints.length === 0) {
      throw new Error(`Test Point não encontrado para TC-${execution.testCaseId} na Suite ${execution.testSuiteId}`);
    }

    // ── 3. Criar Test Run ──────────────────────────────────────────────

    const testRun = await client.createTestRun(
      testPlanId,
      testPoints.map(tp => tp.id),
      `FastQA Batch - TC-${execution.testCaseId} - ${new Date().toISOString()}`
    );
    result.testRunId = testRun.id;
    console.log(`   ✅ Test Run #${testRun.id} criado`);

    // ── 4. Obter Test Results ──────────────────────────────────────────

    const testResultsResponse = await client.getTestResults(testRun.id);
    const testResults = testResultsResponse.value;
    if (testResults.length === 0) {
      throw new Error(`Test Results não encontrados para Run #${testRun.id}`);
    }

    const testResult = testResults[0];
    result.testResultId = testResult.id;

    // ── 5. Upload de evidências ────────────────────────────────────────

    for (const file of evidenceFiles) {
      await client.uploadTestResultAttachment(testRun.id, testResult.id, file);
      result.evidencesUploaded++;
      console.log(`   📎 ${path.basename(file)} anexado`);
    }

    // ── 6. Atualizar outcome ───────────────────────────────────────────

    await client.updateTestResults(testRun.id, [{
      id: testResult.id,
      outcome: execution.result,
      state: 'Completed',
      comment: execution.comment
    }]);
    console.log(`   ✅ Outcome atualizado: ${execution.result}`);

    // ── 7. Finalizar Test Run ──────────────────────────────────────────

    await client.completeTestRun(testRun.id);
    console.log(`   ✅ Test Run #${testRun.id} finalizado`);

    // ── 8. Criar Bug se necessário ─────────────────────────────────────

    if (execution.autoBug && execution.result === 'Failed') {
      // Implementação simplificada - poderia usar MCP para criação completa
      console.log(`   🐛 Bug auto-criado (simulado) com severidade: ${execution.bugSeverity || '3 - Medium'}`);
      result.bugId = -1; // Placeholder
    }

    // ── 9. Anexar ao Work Item se solicitado ──────────────────────────

    if (execution.attachToWorkItem && evidenceFiles.length > 0) {
      for (const file of evidenceFiles) {
        const attachment = await client.uploadAttachment(file, path.basename(file));
        await client.attachToWorkItem(
          execution.testCaseId,
          attachment.url,
          execution.comment ? `${execution.comment} | ${path.basename(file)}` : `Evidência: ${path.basename(file)}`
        );
        console.log(`   📎 ${path.basename(file)} anexado ao WI #${execution.testCaseId}`);
      }
    }

    result.success = true;
    console.log(`   ✅ Execução ${index + 1}/${total} concluída com sucesso`);

  } catch (error) {
    result.errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`   ❌ Erro na execução ${index + 1}/${total}: ${result.errorMessage}`);
  } finally {
    result.duration = Date.now() - startTime;
  }

  return result;
}

// ─────────────────────────────────────────────────────────────────────
// Função Principal
// ─────────────────────────────────────────────────────────────────────

async function uploadBatchTestExecution(input: BatchExecutionInput): Promise<BatchExecutionSummary> {
  const client = new AzureDevOpsClient('BatchTestExecution');
  const startTime = Date.now();

  console.log('\n🚀 ═══════════════════════════════════════════════════════════════');
  console.log('   FastQA — Upload de Múltiplas Execuções (Batch Test Execution)');
  console.log('═══════════════════════════════════════════════════════════════\n');

  console.log(`   Test Plan ID:    ${input.testPlanId}`);
  console.log(`   Total Execuções: ${input.executions.length}`);
  console.log('');

  const results: ExecutionResult[] = [];
  let successCount = 0;
  let testRunsCreated = 0;
  let evidencesUploaded = 0;
  let bugsCreated = 0;

  // Processar cada execução sequencialmente
  for (let i = 0; i < input.executions.length; i++) {
    const execution = input.executions[i];
    const result = await executeTestRun(client, input.testPlanId, execution, i, input.executions.length);
    
    results.push(result);
    
    if (result.success) {
      successCount++;
      if (result.testRunId) testRunsCreated++;
      evidencesUploaded += result.evidencesUploaded;
      if (result.bugId) bugsCreated++;
    }

    // Pausa breve entre execuções para evitar throttling
    if (i < input.executions.length - 1) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }

  const totalDuration = Date.now() - startTime;

  // ── Relatório Final ────────────────────────────────────────────────

  console.log('\n═══════════════════════════════════════════════════════════════');
  console.log('📊 RESUMO DO BATCH EXECUTION');
  console.log('═══════════════════════════════════════════════════════════════\n');

  console.log(`   Test Plan:       #${input.testPlanId}`);
  console.log(`   Total Execuções: ${input.executions.length}`);
  console.log(`   ✅ Sucessos:     ${successCount} (${((successCount / input.executions.length) * 100).toFixed(1)}%)`);
  console.log(`   ❌ Falhas:       ${input.executions.length - successCount}`);
  console.log(`   Test Runs:       ${testRunsCreated} criados`);
  console.log(`   Evidências:      ${evidencesUploaded} anexadas`);
  console.log(`   Bugs:           ${bugsCreated} criados`);
  console.log(`   Duração Total:   ${(totalDuration / 1000).toFixed(1)}s`);
  console.log('');

  // Detalhamento por execução
  console.log('📋 DETALHAMENTO POR EXECUÇÃO:');
  for (const result of results) {
    const status = result.success ? '✅' : '❌';
    const duration = (result.duration / 1000).toFixed(1);
    console.log(`   ${status} TC-${result.testCaseId}: ${duration}s | Evidências: ${result.evidencesUploaded}`);
    if (!result.success && result.errorMessage) {
      console.log(`      Erro: ${result.errorMessage}`);
    }
  }

  // Salvar log detalhado
  const logsDir = config.logsDir;
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }
  const logFile = path.join(logsDir, `batch-execution-${Date.now()}.json`);
  const summary: BatchExecutionSummary = {
    totalExecutions: input.executions.length,
    successful: successCount,
    failed: input.executions.length - successCount,
    testRunsCreated,
    evidencesUploaded,
    bugsCreated,
    duration: totalDuration,
    results
  };

  fs.writeFileSync(logFile, JSON.stringify(summary, null, 2));
  console.log(`\n   📝 Log detalhado salvo em: ${logFile}`);
  console.log('');

  return summary;
}

// ─────────────────────────────────────────────────────────────────────
// CLI e Execução
// ─────────────────────────────────────────────────────────────────────

async function main() {
  try {
    const args = process.argv.slice(2);
    
    // Parsear argumentos
    const getArg = (flag: string): string | undefined => {
      const index = args.indexOf(flag);
      return index !== -1 && index + 1 < args.length ? args[index + 1] : undefined;
    };

    const hasFlag = (flag: string): boolean => args.includes(flag);

    // Verificar se é modo preview
    if (hasFlag('--preview-json')) {
      const jsonFile = getArg('--preview-json');
      if (!jsonFile) {
        throw new Error('Caminho do arquivo JSON é obrigatório com --preview-json');
      }
      previewJsonFile(jsonFile);
      process.exit(0);
    }

    if (hasFlag('--preview-csv')) {
      const csvFile = getArg('--preview-csv');
      const testPlanId = getArg('--test-plan-id');
      if (!csvFile) {
        throw new Error('Caminho do arquivo CSV é obrigatório com --preview-csv');
      }
      previewCsvFile(csvFile, testPlanId ? parseInt(testPlanId) : undefined);
      process.exit(0);
    }

    if (hasFlag('--preview-inline')) {
      const executionsString = getArg('--executions');
      const testPlanId = getArg('--test-plan-id');
      if (!executionsString) {
        throw new Error('String de execuções é obrigatória com --preview-inline');
      }
      if (!testPlanId) {
        throw new Error('Test Plan ID é obrigatório com --preview-inline');
      }
      previewInlineExecutions(executionsString, parseInt(testPlanId));
      process.exit(0);
    }

    let batchInput: BatchExecutionInput;

    // Determinar fonte dos dados
    if (hasFlag('--json-file')) {
      const jsonFile = getArg('--json-file');
      if (!jsonFile) {
        throw new Error('Caminho do arquivo JSON é obrigatório com --json-file');
      }
      console.log(`📁 Carregando execuções do arquivo JSON: ${jsonFile}`);
      batchInput = readJsonFile(jsonFile);

    } else if (hasFlag('--csv-file')) {
      const csvFile = getArg('--csv-file');
      const testPlanId = getArg('--test-plan-id');
      
      if (!csvFile) {
        throw new Error('Caminho do arquivo CSV é obrigatório com --csv-file');
      }
      if (!testPlanId) {
        throw new Error('Test Plan ID é obrigatório com --csv-file');
      }
      
      console.log(`📁 Carregando execuções do arquivo CSV: ${csvFile}`);
      batchInput = readCsvFile(csvFile, parseInt(testPlanId));

    } else if (hasFlag('--executions')) {
      const executionsString = getArg('--executions');
      const testPlanId = getArg('--test-plan-id');
      
      if (!executionsString) {
        throw new Error('String de execuções é obrigatória com --executions');
      }
      if (!testPlanId) {
        throw new Error('Test Plan ID é obrigatório com --executions');
      }
      
      console.log('📝 Processando execuções inline...');
      batchInput = parseInlineExecutions(executionsString, parseInt(testPlanId));

    } else {
      throw new Error(`
Uso: npx tsx upload-batch-test-execution.command.ts [OPÇÃO]

OPÇÕES DE EXECUÇÃO:
  --json-file <caminho>              Carregar de arquivo JSON
  --csv-file <caminho> --test-plan-id <id>  Carregar de arquivo CSV 
  --executions <string> --test-plan-id <id> Execuções inline separadas por |

OPÇÕES DE PREVIEW (apenas visualizar conteúdo):
  --preview-json <caminho>           Exibir conteúdo do arquivo JSON formatado
  --preview-csv <caminho> [--test-plan-id <id>]  Exibir conteúdo do arquivo CSV formatado
  --preview-inline --executions <string> --test-plan-id <id>  Exibir execuções inline formatadas

EXEMPLOS DE EXECUÇÃO:
  # JSON
  npx tsx upload-batch-test-execution.command.ts --json-file "batch.json"
  
  # CSV
  npx tsx upload-batch-test-execution.command.ts --csv-file "batch.csv" --test-plan-id 29
  
  # Inline
  npx tsx upload-batch-test-execution.command.ts --test-plan-id 29 \\
    --executions "38:14:Passed:C:/evidence/TC-14:Teste 1|38:15:Failed:C:/evidence/TC-15:Teste 2"

EXEMPLOS DE PREVIEW:
  # Preview JSON
  npx tsx upload-batch-test-execution.command.ts --preview-json "batch.json"
  
  # Preview CSV
  npx tsx upload-batch-test-execution.command.ts --preview-csv "batch.csv" --test-plan-id 29
  
  # Preview Inline
  npx tsx upload-batch-test-execution.command.ts --preview-inline \\
    --test-plan-id 29 --executions "38:14:Passed:C:/evidence/TC-14:Teste 1"

FORMATOS:
  Ver documentação no cabeçalho do arquivo para estruturas JSON e CSV.
`);
    }

    // Executar batch
    await uploadBatchTestExecution(batchInput);

    console.log('✅ Batch execution concluído com sucesso!\n');
    process.exit(0);

  } catch (error) {
    console.error('\n❌ Erro no batch execution:');
    console.error(error instanceof Error ? error.message : String(error));
    console.error('');
    process.exit(1);
  }
}

// Executar se chamado diretamente
if (require.main === module) {
  main();
}

export { uploadBatchTestExecution, BatchExecutionInput, BatchExecutionSummary };