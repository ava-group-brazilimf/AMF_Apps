/**
 * ═══════════════════════════════════════════════════════════════════════════
 * FastQA — Comando: Sincronizar Resultados de Pipeline
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Obtém resultados de execução de um build/pipeline do Azure DevOps e
 * sincroniza com Test Cases de um Test Plan/Suite, criando Test Runs,
 * atualizando outcomes e opcionalmente gerando bugs para falhas.
 *
 * Uso:
 *   npx tsx fastqa/scripts/azure-devops/commands/sync-pipeline-results.command.ts \
 *     --build-id <id> \
 *     --test-plan-id <id> \
 *     --test-suite-id <id> \
 *     [--map-by-name] \
 *     [--comment <texto>] \
 *     [--auto-bug] \
 *     [--bug-severity <severidade>] \
 *     [--update-existing] \
 *     [--dry-run]
 *
 * @module sync-pipeline-results
 */

import * as fs from 'fs';
import * as path from 'path';

import AzureDevOpsClient from '../azure-devops.client';
import { config } from '../azure-devops.config';
import { Logger } from '../utils/logger.util';

import type {
  SyncPipelineResultsParams,
  SyncPipelineResult,
  Build,
  BuildTestRun,
  TestPoint,
  TestOutcome,
  JsonPatchOperation,
  TestResult,
  PaginatedResponse,
} from '../types/azure-devops.types';

// ─────────────────────────────────────────────────────────────────────
// Interfaces internas
// ─────────────────────────────────────────────────────────────────────

/** Resultado individual de teste do pipeline (parseado do Test Run do build) */
interface PipelineTestResult {
  testCaseName: string;
  outcome: TestOutcome;
  durationMs?: number;
  errorMessage?: string;
  stackTrace?: string;
  testRunId: number;
  testResultId: number;
}

/** Mapeamento entre resultado do pipeline e Test Point no Test Plan */
interface MappedTestResult {
  pipelineResult: PipelineTestResult;
  testPoint?: TestPoint;
  testCaseId?: number;
  matched: boolean;
  matchMethod?: 'id' | 'name-exact' | 'name-partial' | 'name-normalized';
}

// ─────────────────────────────────────────────────────────────────────
// Constantes
// ─────────────────────────────────────────────────────────────────────

const COMMAND_NAME = 'sync-pipeline-results';

// ─────────────────────────────────────────────────────────────────────
// Função Principal
// ─────────────────────────────────────────────────────────────────────

async function syncPipelineResults(params: {
  buildId: number;
  testPlanId: number;
  testSuiteId: number;
  mapByName: boolean;
  comment?: string;
  autoBug: boolean;
  bugSeverity: string;
  updateExisting: boolean;
  dryRun: boolean;
}): Promise<SyncPipelineResult> {
  const client = new AzureDevOpsClient('SyncPipelineResults');
  const logger = new Logger(COMMAND_NAME);

  console.log('\n🔄 ═══════════════════════════════════════════════════════════════');
  console.log('   FastQA — Sincronização de Resultados de Pipeline');
  console.log('═══════════════════════════════════════════════════════════════\n');

  console.log(`   Build ID:       #${params.buildId}`);
  console.log(`   Test Plan ID:   #${params.testPlanId}`);
  console.log(`   Test Suite ID:  #${params.testSuiteId}`);
  console.log(`   Map by Name:    ${params.mapByName ? 'Sim' : 'Não (apenas por ID)'}`);
  console.log(`   Auto Bug:       ${params.autoBug ? 'Sim' : 'Não'}`);
  console.log(`   Update Existing:${params.updateExisting ? ' Sim' : ' Não'}`);
  if (params.dryRun) {
    console.log(`   ⚠️  DRY-RUN:     Sim (nenhuma alteração será feita)`);
  }
  console.log('');

  // ── 1. Obter informações do Build ──────────────────────────────────

  console.log('📦 Etapa 1: Obtendo informações do Build...\n');

  let build: Build;
  try {
    build = await client.getBuild(params.buildId);
  } catch (error) {
    throw new Error(
      `Falha ao obter Build #${params.buildId}: ${error}\n` +
      `Verifique se o Build ID está correto e se o PAT tem permissão de leitura.`
    );
  }

  const buildUrl = build._links?.web?.href ||
    `${config.orgUrl}/${encodeURIComponent(config.project)}/_build/results?buildId=${build.id}`;

  console.log(`   Build:          #${build.id} — ${build.buildNumber}`);
  console.log(`   Status:         ${build.status}`);
  console.log(`   Resultado:      ${build.result || 'em andamento'}`);
  console.log(`   Branch:         ${build.sourceBranch}`);
  console.log(`   Pipeline:       ${build.definition.name}`);
  if (build.startTime) {
    console.log(`   Início:         ${new Date(build.startTime).toLocaleString('pt-BR')}`);
  }
  if (build.finishTime) {
    console.log(`   Fim:            ${new Date(build.finishTime).toLocaleString('pt-BR')}`);
  }
  console.log(`   🔗 ${buildUrl}`);
  console.log('');

  // Validar se o build está completo
  if (build.status !== 'completed') {
    console.warn(`⚠️  Build #${build.id} ainda não está completo (status: ${build.status}).`);
    console.warn('   Os resultados podem estar incompletos.\n');
  }

  // ── 2. Obter Test Runs do Build ────────────────────────────────────

  console.log('🧪 Etapa 2: Obtendo Test Runs associados ao Build...\n');

  const buildUri = `vstfs:///Build/Build/${build.id}`;
  let buildTestRuns: BuildTestRun[];

  try {
    const testRunsResponse = await client.getTestRunsByBuild(buildUri);
    buildTestRuns = testRunsResponse.value || [];
  } catch (error) {
    throw new Error(
      `Falha ao obter Test Runs do Build #${build.id}: ${error}\n` +
      `Verifique se a pipeline publica resultados de teste (PublishTestResults@2 task).`
    );
  }

  if (buildTestRuns.length === 0) {
    console.warn('⚠️  Nenhum Test Run encontrado para este Build.');
    console.warn('   Certifique-se de que a pipeline inclui a task PublishTestResults@2.');
    console.warn('   Use @fastqa:azdo_create_pipeline para gerar YAML com publicação de testes.\n');

    return {
      buildId: build.id,
      buildStatus: build.status,
      buildResult: build.result || 'unknown',
      totalTests: 0,
      passedTests: 0,
      failedTests: 0,
      otherTests: 0,
      testRunsUpdated: 0,
      testRunsCreated: 0,
      bugsCreated: 0,
      details: [],
    };
  }

  console.log(`   📊 ${buildTestRuns.length} Test Run(s) encontrado(s) no Build:`);
  let totalBuildTests = 0;
  let totalBuildPassed = 0;
  let totalBuildFailed = 0;

  for (const tr of buildTestRuns) {
    const failed = tr.totalTests - tr.passedTests - tr.incompleteTests - (tr.notApplicableTests || 0);
    totalBuildTests += tr.totalTests;
    totalBuildPassed += tr.passedTests;
    totalBuildFailed += failed;

    console.log(`   • Run #${tr.id}: "${tr.name}" — Total: ${tr.totalTests}, ✅ ${tr.passedTests}, ❌ ${failed}`);
  }
  console.log('');

  // ── 3. Coletar resultados individuais dos Test Runs ────────────────

  console.log('📋 Etapa 3: Coletando resultados individuais dos testes...\n');

  const pipelineResults: PipelineTestResult[] = [];

  for (const buildTR of buildTestRuns) {
    try {
      const resultsResponse = await client.getTestResults(buildTR.id);
      const results = resultsResponse.value || [];

      for (const result of results) {
        pipelineResults.push({
          testCaseName: result.testCase?.name || `Test_${result.id}`,
          outcome: mapPipelineOutcome(result.outcome),
          durationMs: result.durationInMs,
          errorMessage: result.errorMessage,
          testRunId: buildTR.id,
          testResultId: result.id,
        });
      }
    } catch (error) {
      logger.error(`Falha ao obter resultados do Test Run #${buildTR.id}: ${error}`);
    }
  }

  console.log(`   📊 ${pipelineResults.length} resultado(s) individual(is) coletado(s)`);
  console.log(`   ✅ Passed:     ${pipelineResults.filter(r => r.outcome === 'Passed').length}`);
  console.log(`   ❌ Failed:     ${pipelineResults.filter(r => r.outcome === 'Failed').length}`);
  console.log(`   ⏭  Outros:     ${pipelineResults.filter(r => r.outcome !== 'Passed' && r.outcome !== 'Failed').length}`);
  console.log('');

  // ── 4. Obter Test Points do Test Plan/Suite ────────────────────────

  console.log('📌 Etapa 4: Obtendo Test Cases do Test Plan/Suite...\n');

  let testPoints: TestPoint[];

  try {
    const pointsResponse = await client.getTestPoints(
      params.testPlanId,
      params.testSuiteId
    );
    testPoints = pointsResponse.value || [];
  } catch (error) {
    throw new Error(
      `Falha ao obter Test Points do Plan #${params.testPlanId}, Suite #${params.testSuiteId}: ${error}\n` +
      `Verifique se os IDs estão corretos e se existem Test Cases associados à Suite.`
    );
  }

  console.log(`   📊 ${testPoints.length} Test Case(s) no Test Plan/Suite:`);
  for (const tp of testPoints) {
    console.log(`   • TC-${tp.testCaseReference.id}: "${tp.testCaseReference.name}" (Estado: ${tp.testCaseReference.state})`);
  }
  console.log('');

  // ── 5. Mapear resultados do pipeline com Test Cases ────────────────

  console.log('🔗 Etapa 5: Mapeando resultados do pipeline com Test Cases...\n');

  const mappedResults: MappedTestResult[] = [];

  for (const pResult of pipelineResults) {
    const mapped = matchPipelineResultToTestPoint(
      pResult,
      testPoints,
      params.mapByName
    );
    mappedResults.push(mapped);
  }

  const matchedCount = mappedResults.filter(m => m.matched).length;
  const unmatchedCount = mappedResults.filter(m => !m.matched).length;

  console.log(`   ✅ Mapeados:    ${matchedCount}/${pipelineResults.length}`);
  console.log(`   ❌ Sem match:   ${unmatchedCount}/${pipelineResults.length}`);

  if (unmatchedCount > 0) {
    console.log('\n   ⚠️  Resultados sem correspondência no Test Plan:');
    for (const m of mappedResults.filter(mr => !mr.matched)) {
      console.log(`      • "${m.pipelineResult.testCaseName}" (${m.pipelineResult.outcome})`);
    }
  }
  console.log('');

  // Se é DRY-RUN, apenas exibir resumo e parar
  if (params.dryRun) {
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('⚠️  DRY-RUN — Nenhuma alteração foi feita no Azure DevOps');
    console.log('═══════════════════════════════════════════════════════════════\n');

    printMappingTable(mappedResults);

    return buildSyncResult(build, mappedResults, 0, 0, 0);
  }

  // ── 6. Criar/Atualizar Test Runs no Test Plan ─────────────────────

  console.log('🚀 Etapa 6: Criando Test Runs no Test Plan...\n');

  const matchedResults = mappedResults.filter(m => m.matched && m.testPoint);
  let testRunsCreated = 0;
  let testRunsUpdated = 0;
  let bugsCreated = 0;
  const syncDetails: SyncPipelineResult['details'] = [];

  if (matchedResults.length === 0) {
    console.warn('   ⚠️  Nenhum resultado mapeado — nada a sincronizar.\n');
  } else {
    // Agrupar resultados por outcome para batch de Test Runs
    // Criar um Test Run com todos os Test Points mapeados
    const pointIds = matchedResults.map(m => m.testPoint!.id);
    const runName = `FastQA Pipeline Sync — Build #${build.id} — ${build.definition.name} — ${new Date().toISOString()}`;

    let testRun;
    try {
      testRun = await client.createTestRun(params.testPlanId, pointIds, runName);
      testRunsCreated++;
      console.log(`   ✅ Test Run #${testRun.id} criado com ${pointIds.length} Test Point(s)`);
    } catch (error) {
      throw new Error(`Falha ao criar Test Run: ${error}`);
    }

    // Obter Test Results do Run criado
    let testResults: TestResult[];
    try {
      const resultsResponse = await client.getTestResults(testRun.id);
      testResults = resultsResponse.value || [];
    } catch (error) {
      throw new Error(`Falha ao obter Test Results do Run #${testRun.id}: ${error}`);
    }

    // Mapear Test Results do Run com os resultados do pipeline
    const updates: Array<{
      id: number;
      outcome: TestOutcome;
      state: 'Completed';
      comment: string;
      errorMessage?: string;
      durationInMs?: number;
    }> = [];

    for (const matched of matchedResults) {
      const pResult = matched.pipelineResult;
      const testCaseId = matched.testCaseId!;

      // Encontrar o Test Result correspondente no Run criado
      const targetResult = testResults.find(
        tr => tr.testCase?.id === testCaseId
      );

      if (!targetResult) {
        logger.warn(`Test Result não encontrado para TC-${testCaseId} no Run #${testRun.id}`);
        syncDetails.push({
          testCaseId,
          testCaseName: pResult.testCaseName,
          outcome: pResult.outcome,
          duration: pResult.durationMs,
          errorMessage: `Test Result não encontrado no Run #${testRun.id}`,
        });
        continue;
      }

      const comment = params.comment ||
        `Sincronizado do Build #${build.id} (${build.definition.name}) — Pipeline: ${build.buildNumber} — Branch: ${build.sourceBranch}`;

      updates.push({
        id: targetResult.id,
        outcome: pResult.outcome,
        state: 'Completed',
        comment,
        errorMessage: pResult.errorMessage,
        durationInMs: pResult.durationMs,
      });

      syncDetails.push({
        testCaseId,
        testCaseName: pResult.testCaseName,
        outcome: pResult.outcome,
        duration: pResult.durationMs,
        errorMessage: pResult.errorMessage,
        testRunId: testRun.id,
      });
    }

    // Atualizar todos os Test Results de uma vez (batch)
    if (updates.length > 0) {
      try {
        await client.updateTestResults(testRun.id, updates);
        testRunsUpdated += updates.length;
        console.log(`   ✅ ${updates.length} Test Result(s) atualizados no Run #${testRun.id}`);
      } catch (error) {
        logger.error(`Falha ao atualizar Test Results: ${error}`);
      }
    }

    // Finalizar Test Run
    try {
      const runComment = `FastQA Pipeline Sync — Build #${build.id} — ${build.definition.name} — ` +
        `${matchedResults.filter(m => m.pipelineResult.outcome === 'Passed').length} passed, ` +
        `${matchedResults.filter(m => m.pipelineResult.outcome === 'Failed').length} failed`;

      await client.completeTestRun(testRun.id, runComment);
      console.log(`   ✅ Test Run #${testRun.id} finalizado\n`);
    } catch (error) {
      logger.error(`Falha ao finalizar Test Run #${testRun.id}: ${error}`);
    }

    // ── 7. Criar bugs para falhas (opcional) ──────────────────────────

    if (params.autoBug) {
      const failedResults = matchedResults.filter(
        m => m.pipelineResult.outcome === 'Failed'
      );

      if (failedResults.length > 0) {
        console.log(`🐛 Etapa 7: Criando bugs para ${failedResults.length} falha(s)...\n`);

        for (const failed of failedResults) {
          const pResult = failed.pipelineResult;
          const testCaseId = failed.testCaseId!;

          try {
            const bugTitle = `[PIPELINE-BUG] Build #${build.id} — Falha: ${pResult.testCaseName}`;

            const reproSteps = AzureDevOpsClient.buildBugReproStepsHtml({
              reproSteps: [
                `<p>Bug criado automaticamente pelo FastQA após falha na pipeline.</p>`,
                `<p><b>Pipeline:</b> ${build.definition.name}</p>`,
                `<p><b>Build:</b> #${build.id} — ${build.buildNumber}</p>`,
                `<p><b>Branch:</b> ${build.sourceBranch}</p>`,
                `<p><b>Test Case:</b> ${pResult.testCaseName}</p>`,
                `<p><b>Test Run (Pipeline):</b> #${pResult.testRunId}</p>`,
              ].join('\n'),
              expectedResult: 'Teste deveria ter passado conforme cenário automatizado.',
              actualResult: pResult.errorMessage || 'Teste falhou durante execução na pipeline.',
              environment: [
                `Pipeline: ${build.definition.name}`,
                `Build: #${build.id} — ${build.buildNumber}`,
                `Branch: ${build.sourceBranch}`,
                `Data: ${new Date().toISOString()}`,
              ].join(' · '),
            });

            const bugOperations: JsonPatchOperation[] = [
              { op: 'add', path: '/fields/System.Title', value: bugTitle },
              { op: 'add', path: '/fields/Microsoft.VSTS.TCM.ReproSteps', value: reproSteps },
              { op: 'add', path: '/fields/Microsoft.VSTS.Common.Severity', value: params.bugSeverity },
              { op: 'add', path: '/fields/Microsoft.VSTS.Common.Priority', value: mapSeverityToPriority(params.bugSeverity) },
              { op: 'add', path: '/fields/System.Tags', value: 'pipeline-bug; fastqa; automation; ci-cd' },
            ];

            const bug = await client.createWorkItem('Bug', bugOperations);
            bugsCreated++;

            const bugUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_workitems/edit/${bug.id}`;
            console.log(`   ✅ Bug #${bug.id}: "${bugTitle}"`);
            console.log(`      🔗 ${bugUrl}`);

            // Vincular Bug ao Test Case
            try {
              await client.linkWorkItems(
                bug.id,
                testCaseId,
                'related',
                `Bug criado por falha na pipeline — Build #${build.id}`
              );
              console.log(`      🔗 Bug #${bug.id} vinculado ao TC-${testCaseId}`);
            } catch (linkError) {
              logger.warn(`Falha ao vincular Bug #${bug.id} ao TC-${testCaseId}: ${linkError}`);
            }

            // Atualizar detalhes com bug info
            const detail = syncDetails.find(d => d.testCaseId === testCaseId);
            if (detail) {
              detail.bugId = bug.id;
            }
          } catch (bugError) {
            logger.error(`Falha ao criar Bug para TC-${testCaseId}: ${bugError}`);
          }
        }
        console.log('');
      }
    }
  }

  // Adicionar resultados não mapeados ao syncDetails
  for (const unmatched of mappedResults.filter(m => !m.matched)) {
    syncDetails.push({
      testCaseName: unmatched.pipelineResult.testCaseName,
      outcome: unmatched.pipelineResult.outcome,
      duration: unmatched.pipelineResult.durationMs,
      errorMessage: 'Sem correspondência no Test Plan/Suite',
    });
  }

  // ── Resumo Final ──────────────────────────────────────────────────

  const result = buildSyncResult(
    build,
    mappedResults,
    testRunsCreated,
    testRunsUpdated,
    bugsCreated
  );

  printFinalSummary(result, params, buildUrl);

  // ── Salvar log ────────────────────────────────────────────────────

  const logData = {
    timestamp: new Date().toISOString(),
    command: COMMAND_NAME,
    params: {
      buildId: params.buildId,
      testPlanId: params.testPlanId,
      testSuiteId: params.testSuiteId,
      mapByName: params.mapByName,
      autoBug: params.autoBug,
      dryRun: params.dryRun,
    },
    build: {
      id: build.id,
      buildNumber: build.buildNumber,
      status: build.status,
      result: build.result,
      pipeline: build.definition.name,
      branch: build.sourceBranch,
      url: buildUrl,
    },
    results: result,
  };

  const logsDir = config.logsDir;
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }

  const logFileName = `pipeline-sync-${build.id}-${Date.now()}.json`;
  const logFilePath = path.join(logsDir, logFileName);
  fs.writeFileSync(logFilePath, JSON.stringify(logData, null, 2), 'utf-8');
  console.log(`   📝 Log salvo em: ${logFilePath}\n`);

  return result;
}

// ─────────────────────────────────────────────────────────────────────
// Funções Auxiliares
// ─────────────────────────────────────────────────────────────────────

/**
 * Mapeia o outcome de um resultado do pipeline para o formato TestOutcome.
 * Os outcomes da API de Test Results do Build podem variar.
 */
function mapPipelineOutcome(outcome: string | TestOutcome): TestOutcome {
  const normalized = (outcome || '').toLowerCase().trim();

  const outcomeMap: Record<string, TestOutcome> = {
    passed: 'Passed',
    failed: 'Failed',
    blocked: 'Blocked',
    notapplicable: 'NotApplicable',
    notexecuted: 'NotExecuted',
    inconclusive: 'Inconclusive',
    timeout: 'Timeout',
    aborted: 'Aborted',
    none: 'None',
    // Variantes comuns
    success: 'Passed',
    failure: 'Failed',
    error: 'Failed',
    skipped: 'NotApplicable',
    ignored: 'NotApplicable',
    warning: 'Inconclusive',
  };

  return outcomeMap[normalized] || 'None';
}

/**
 * Tenta mapear um resultado do pipeline para um Test Point no Test Plan/Suite.
 * Estratégias de matching (em ordem de prioridade):
 * 1. Match por Test Case ID (se presente no nome do teste)
 * 2. Match por nome exato
 * 3. Match por nome normalizado (sem espaços extras, case-insensitive)
 * 4. Match parcial por nome (contém)
 */
function matchPipelineResultToTestPoint(
  pipelineResult: PipelineTestResult,
  testPoints: TestPoint[],
  mapByName: boolean
): MappedTestResult {
  const testName = pipelineResult.testCaseName;

  // Estratégia 1: Tentar extrair TC ID do nome do teste
  // Formatos reconhecidos: TC-123, TC_123, testcase_123, [123]
  const idPatterns = [
    /TC[-_](\d+)/i,
    /testcase[-_]?(\d+)/i,
    /\[(\d+)\]/,
    /test_case_(\d+)/i,
    /#(\d+)/,
  ];

  for (const pattern of idPatterns) {
    const match = testName.match(pattern);
    if (match) {
      const extractedId = parseInt(match[1]);
      const tp = testPoints.find(p => p.testCaseReference.id === extractedId);
      if (tp) {
        return {
          pipelineResult,
          testPoint: tp,
          testCaseId: tp.testCaseReference.id,
          matched: true,
          matchMethod: 'id',
        };
      }
    }
  }

  // Se mapByName está desabilitado, parar aqui
  if (!mapByName) {
    return {
      pipelineResult,
      matched: false,
    };
  }

  // Estratégia 2: Match por nome exato
  const exactMatch = testPoints.find(
    tp => tp.testCaseReference.name === testName
  );
  if (exactMatch) {
    return {
      pipelineResult,
      testPoint: exactMatch,
      testCaseId: exactMatch.testCaseReference.id,
      matched: true,
      matchMethod: 'name-exact',
    };
  }

  // Estratégia 3: Match por nome normalizado
  const normalizedTestName = normalizeName(testName);
  const normalizedMatch = testPoints.find(
    tp => normalizeName(tp.testCaseReference.name) === normalizedTestName
  );
  if (normalizedMatch) {
    return {
      pipelineResult,
      testPoint: normalizedMatch,
      testCaseId: normalizedMatch.testCaseReference.id,
      matched: true,
      matchMethod: 'name-normalized',
    };
  }

  // Estratégia 4: Match parcial (nome do teste contém o nome do TC ou vice-versa)
  const partialMatch = testPoints.find(tp => {
    const normalizedTpName = normalizeName(tp.testCaseReference.name);
    return (
      normalizedTestName.includes(normalizedTpName) ||
      normalizedTpName.includes(normalizedTestName)
    );
  });

  if (partialMatch) {
    return {
      pipelineResult,
      testPoint: partialMatch,
      testCaseId: partialMatch.testCaseReference.id,
      matched: true,
      matchMethod: 'name-partial',
    };
  }

  // Nenhuma correspondência
  return {
    pipelineResult,
    matched: false,
  };
}

/**
 * Normaliza nome para comparação:
 * - Converte para lowercase
 * - Remove caracteres especiais (exceto letras, números e espaços)
 * - Remove espaços extras
 * - Trim
 */
function normalizeName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9\sàáâãéêíóôõúüç]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Mapeia severidade para prioridade numérica */
function mapSeverityToPriority(severity: string): number {
  if (severity.startsWith('1')) return 1;
  if (severity.startsWith('2')) return 2;
  if (severity.startsWith('3')) return 3;
  return 4;
}

/** Exibe tabela de mapeamento */
function printMappingTable(mappedResults: MappedTestResult[]): void {
  console.log('\n📋 Tabela de Mapeamento:');
  console.log('─'.repeat(100));
  console.log(
    padRight('Teste Pipeline', 40) +
    padRight('Outcome', 12) +
    padRight('TC ID', 8) +
    padRight('Match', 18) +
    padRight('TC Name (Plan)', 30)
  );
  console.log('─'.repeat(100));

  for (const m of mappedResults) {
    const pName = truncate(m.pipelineResult.testCaseName, 38);
    const outcome = m.pipelineResult.outcome;
    const tcId = m.matched ? `#${m.testCaseId}` : '—';
    const method = m.matched ? `✅ ${m.matchMethod}` : '❌ sem match';
    const tcName = m.testPoint
      ? truncate(m.testPoint.testCaseReference.name, 28)
      : '—';

    console.log(
      padRight(pName, 40) +
      padRight(outcome, 12) +
      padRight(tcId, 8) +
      padRight(method, 18) +
      padRight(tcName, 30)
    );
  }

  console.log('─'.repeat(100));
  console.log('');
}

/** Constrói o objeto SyncPipelineResult */
function buildSyncResult(
  build: Build,
  mappedResults: MappedTestResult[],
  testRunsCreated: number,
  testRunsUpdated: number,
  bugsCreated: number
): SyncPipelineResult {
  const passedTests = mappedResults.filter(
    m => m.pipelineResult.outcome === 'Passed'
  ).length;
  const failedTests = mappedResults.filter(
    m => m.pipelineResult.outcome === 'Failed'
  ).length;
  const otherTests =
    mappedResults.length - passedTests - failedTests;

  return {
    buildId: build.id,
    buildStatus: build.status,
    buildResult: build.result || 'unknown',
    totalTests: mappedResults.length,
    passedTests,
    failedTests,
    otherTests,
    testRunsUpdated,
    testRunsCreated,
    bugsCreated,
    details: mappedResults.map(m => ({
      testCaseId: m.testCaseId,
      testCaseName: m.pipelineResult.testCaseName,
      outcome: m.pipelineResult.outcome,
      duration: m.pipelineResult.durationMs,
      errorMessage: m.pipelineResult.errorMessage,
      testRunId: m.pipelineResult.testRunId,
    })),
  };
}

/** Imprime resumo final */
function printFinalSummary(
  result: SyncPipelineResult,
  params: { buildId: number; testPlanId: number; testSuiteId: number },
  buildUrl: string
): void {
  const passRate =
    result.totalTests > 0
      ? ((result.passedTests / result.totalTests) * 100).toFixed(1)
      : '0.0';

  console.log('═══════════════════════════════════════════════════════════════');
  console.log('📊 RESUMO DA SINCRONIZAÇÃO');
  console.log('═══════════════════════════════════════════════════════════════\n');
  console.log(`   Build:             #${result.buildId}`);
  console.log(`   Build Status:      ${result.buildStatus}`);
  console.log(`   Build Result:      ${result.buildResult}`);
  console.log(`   Test Plan:         #${params.testPlanId}`);
  console.log(`   Test Suite:        #${params.testSuiteId}`);
  console.log('');
  console.log(`   Total Testes:      ${result.totalTests}`);
  console.log(`   ✅ Passed:         ${result.passedTests} (${passRate}%)`);
  console.log(`   ❌ Failed:         ${result.failedTests}`);
  console.log(`   ⏭  Outros:         ${result.otherTests}`);
  console.log('');
  console.log(`   Test Runs Criados: ${result.testRunsCreated}`);
  console.log(`   Results Updated:   ${result.testRunsUpdated}`);
  if (result.bugsCreated > 0) {
    console.log(`   🐛 Bugs Criados:   ${result.bugsCreated}`);
  }
  console.log(`\n   🔗 Build: ${buildUrl}`);
  console.log('');
}

/** Utilidades de formatação */
function padRight(text: string, length: number): string {
  return text.length >= length ? text.substring(0, length) : text + ' '.repeat(length - text.length);
}

function truncate(text: string, maxLength: number): string {
  return text.length > maxLength ? text.substring(0, maxLength - 2) + '..' : text;
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
  const hasFlag = (flag: string): boolean => args.includes(flag);

  const buildId = getArg('--build-id');
  const testPlanId = getArg('--test-plan-id');
  const testSuiteId = getArg('--test-suite-id');
  const mapByName = hasFlag('--map-by-name');
  const comment = getArg('--comment');
  const autoBug = hasFlag('--auto-bug');
  const bugSeverity = getArg('--bug-severity') || '3 - Medium';
  const updateExisting = hasFlag('--update-existing');
  const dryRun = hasFlag('--dry-run');

  // Validação de parâmetros obrigatórios
  if (!buildId || !testPlanId || !testSuiteId) {
    console.error('');
    console.error('❌ Parâmetros obrigatórios faltando.');
    console.error('');
    console.error('Uso:');
    console.error('  npx tsx fastqa/scripts/azure-devops/commands/sync-pipeline-results.command.ts \\');
    console.error('    --build-id <id> \\');
    console.error('    --test-plan-id <id> \\');
    console.error('    --test-suite-id <id>');
    console.error('');
    console.error('Parâmetros opcionais:');
    console.error('    --map-by-name                  Mapeia resultados por nome do teste (além de ID)');
    console.error('    --comment <texto>               Comentário nos Test Results');
    console.error('    --auto-bug                     Cria bugs automaticamente para falhas');
    console.error('    --bug-severity <severidade>     Severidade de bugs (padrão: "3 - Medium")');
    console.error('    --update-existing               Atualiza Test Runs existentes');
    console.error('    --dry-run                       Simula sem fazer alterações');
    console.error('');
    console.error('Exemplos:');
    console.error('  # Sincronização básica');
    console.error('  npx tsx sync-pipeline-results.command.ts --build-id 42 --test-plan-id 29 --test-suite-id 38');
    console.error('');
    console.error('  # Com mapeamento por nome e auto-bug');
    console.error('  npx tsx sync-pipeline-results.command.ts --build-id 42 --test-plan-id 29 --test-suite-id 38 \\');
    console.error('    --map-by-name --auto-bug --bug-severity "2 - High"');
    console.error('');
    console.error('  # Dry-run para validar mapeamento');
    console.error('  npx tsx sync-pipeline-results.command.ts --build-id 42 --test-plan-id 29 --test-suite-id 38 \\');
    console.error('    --map-by-name --dry-run');
    console.error('');
    process.exit(1);
  }

  try {
    const result = await syncPipelineResults({
      buildId: parseInt(buildId),
      testPlanId: parseInt(testPlanId),
      testSuiteId: parseInt(testSuiteId),
      mapByName,
      comment,
      autoBug,
      bugSeverity,
      updateExisting,
      dryRun,
    });

    // Exit code baseado no resultado
    if (result.failedTests > 0) {
      process.exit(2); // Indica falhas nos testes (não é erro do script)
    }
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Erro na sincronização:');
    console.error(error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { syncPipelineResults };
