/**
 * ═══════════════════════════════════════════════════════════════════════════
 * FastQA — Comando: Executar Plano de Regressão
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Recebe um plano de regressão JSON (gerado por analyze-pr-regression),
 * executa os testes localmente agrupados por layer, parseia resultados
 * do JSON reporter do framework e gera relatório de execução cruzando
 * com o plano original.
 *
 * Uso:
 *   npx tsx fastqa/scripts/regression/commands/execute-regression-plan.command.ts \
 *     --plan <path-to-plan.json> \
 *     [--mode local|pipeline] \
 *     [--layer e2e|api|unit|all] \
 *     [--risk-level critical|high|medium|low|all] \
 *     [--output <path>] \
 *     [--timeout <ms>] \
 *     [--dry-run]
 *
 * @module execute-regression-plan
 */

import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

import type {
  RegressionAnalysisJson,
  RegressionTestEntry,
  RiskLevel,
  ExecutionReport,
  ExecuteRegressionPlanParams,
  TestExecutionResult,
  TestExecutionOutcome,
  AreaExecutionSummary,
  PrData,
} from '../types/regression.types';

// ─────────────────────────────────────────────────────────────────────
// Constantes
// ─────────────────────────────────────────────────────────────────────

const COMMAND_NAME = 'execute-regression-plan';
const CONFIG_PATH = 'fastqa/scripts/project_config.json';
const DEFAULT_OUTPUT_DIR = 'fastqa/manual_test/regression_analysis';
const DEFAULT_TIMEOUT = 600_000; // 10 minutos por layer
const RISK_ORDER: RiskLevel[] = ['critical', 'high', 'medium', 'low', 'gap'];

// ─────────────────────────────────────────────────────────────────────
// Tipos internos
// ─────────────────────────────────────────────────────────────────────

interface ProjectConfig {
  platform?: { type?: string };
  connectors?: { output?: { automation_framework?: string; language?: string } };
  folder_structure?: {
    root?: string;
    custom_paths?: {
      tests?: string;
      automation_root?: string;
      results?: string;
      additional_test_layers?: Array<{ name: string; path: string }>;
    };
  };
}

interface FrameworkRunner {
  buildCommand(specs: string[], layer: string, reportDir: string): string;
  parseResults(reportDir: string, layer: string): ParsedTestResult[];
}

interface ParsedTestResult {
  name: string;
  file: string;
  outcome: TestExecutionOutcome;
  durationMs: number;
  errorMessage?: string;
  stackTrace?: string;
}

// ─────────────────────────────────────────────────────────────────────
// Utilitários
// ─────────────────────────────────────────────────────────────────────

function truncate(text: string, maxLength: number): string {
  return text.length > maxLength ? text.substring(0, maxLength - 2) + '..' : text;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainSec = seconds % 60;
  return `${minutes}m ${remainSec}s`;
}

function normalizeTestName(name: string): string {
  return name
    .replace(/\\/g, '/')
    .replace(/^.*[\\/]/, '')            // remove diretório
    .replace(/\.(spec|test)\.(ts|js|py|java|cs)$/i, '')
    .replace(/Spec$/i, '')
    .replace(/Test$/i, '')
    .toLowerCase();
}

function riskPassesFilter(risk: RiskLevel, minLevel: RiskLevel | 'all'): boolean {
  if (minLevel === 'all') return true;
  return RISK_ORDER.indexOf(risk) <= RISK_ORDER.indexOf(minLevel);
}

// ─────────────────────────────────────────────────────────────────────
// Framework Runners
// ─────────────────────────────────────────────────────────────────────

function createPlaywrightRunner(cwd: string): FrameworkRunner {
  return {
    buildCommand(specs: string[], layer: string, reportDir: string): string {
      const reportFile = path.join(reportDir, `${layer}-results.json`);
      const specList = specs.join(' ');
      return `npx playwright test ${specList} --reporter=json 2>nul > "${reportFile}"`;
    },
    parseResults(reportDir: string, layer: string): ParsedTestResult[] {
      const reportFile = path.join(reportDir, `${layer}-results.json`);
      if (!fs.existsSync(reportFile)) return [];

      const raw = fs.readFileSync(reportFile, 'utf-8').trim();
      if (!raw) return [];

      let report: any;
      try { report = JSON.parse(raw); } catch { return []; }

      const results: ParsedTestResult[] = [];
      const suites = report.suites || [];

      function walkSuites(suiteList: any[]) {
        for (const suite of suiteList) {
          for (const spec of suite.specs || []) {
            for (const test of spec.tests || []) {
              for (const result of test.results || []) {
                const outcome = mapPlaywrightStatus(result.status);
                results.push({
                  name: spec.title || spec.file || '',
                  file: suite.file || spec.file || '',
                  outcome,
                  durationMs: result.duration || 0,
                  errorMessage: result.error?.message,
                  stackTrace: result.error?.stack,
                });
              }
            }
          }
          if (suite.suites) walkSuites(suite.suites);
        }
      }

      walkSuites(suites);
      return results;
    },
  };
}

function mapPlaywrightStatus(status: string): TestExecutionOutcome {
  switch (status) {
    case 'passed': case 'expected': return 'passed';
    case 'failed': case 'unexpected': return 'failed';
    case 'skipped': case 'flaky': return 'skipped';
    default: return 'error';
  }
}

function createCypressRunner(cwd: string): FrameworkRunner {
  return {
    buildCommand(specs: string[], layer: string, reportDir: string): string {
      const reportFile = path.join(reportDir, `${layer}-results.json`);
      const specList = specs.join(',');
      return `npx cypress run --spec "${specList}" --reporter json > "${reportFile}" 2>&1`;
    },
    parseResults(reportDir: string, layer: string): ParsedTestResult[] {
      const reportFile = path.join(reportDir, `${layer}-results.json`);
      if (!fs.existsSync(reportFile)) return [];

      const raw = fs.readFileSync(reportFile, 'utf-8').trim();
      if (!raw) return [];

      // Cypress JSON output pode ter prefixo não-JSON — encontrar o JSON
      const jsonStart = raw.indexOf('{');
      if (jsonStart < 0) return [];

      let report: any;
      try { report = JSON.parse(raw.substring(jsonStart)); } catch { return []; }

      const results: ParsedTestResult[] = [];
      for (const run of report.runs || []) {
        for (const test of run.tests || []) {
          results.push({
            name: Array.isArray(test.title) ? test.title.join(' > ') : test.title || '',
            file: run.spec?.relative || run.spec?.name || '',
            outcome: test.state === 'passed' ? 'passed' : test.state === 'failed' ? 'failed' : 'skipped',
            durationMs: test.duration || 0,
            errorMessage: test.displayError || test.err?.message,
            stackTrace: test.err?.estack || test.err?.stack,
          });
        }
      }
      return results;
    },
  };
}

function createRobotRunner(cwd: string): FrameworkRunner {
  return {
    buildCommand(specs: string[], layer: string, reportDir: string): string {
      const specList = specs.join(' ');
      return `robot --outputdir "${reportDir}" --output ${layer}-output.xml ${specList}`;
    },
    parseResults(reportDir: string, layer: string): ParsedTestResult[] {
      const outputFile = path.join(reportDir, `${layer}-output.xml`);
      if (!fs.existsSync(outputFile)) return [];

      // Parse simplificado do output.xml do Robot Framework
      const xml = fs.readFileSync(outputFile, 'utf-8');
      const results: ParsedTestResult[] = [];
      const testRegex = /<test\s+[^>]*name="([^"]*)"[^>]*>[\s\S]*?<status\s+[^>]*status="(PASS|FAIL|SKIP)"[^>]*(?:starttime="([^"]*)")?[^>]*(?:endtime="([^"]*)")?[^>]*\/?>/gi;

      let match;
      while ((match = testRegex.exec(xml)) !== null) {
        const [, name, status, start, end] = match;
        let duration = 0;
        if (start && end) {
          duration = new Date(end).getTime() - new Date(start).getTime();
          if (isNaN(duration) || duration < 0) duration = 0;
        }
        results.push({
          name,
          file: '',
          outcome: status === 'PASS' ? 'passed' : status === 'FAIL' ? 'failed' : 'skipped',
          durationMs: duration,
        });
      }
      return results;
    },
  };
}

function createGenericRunner(cwd: string): FrameworkRunner {
  return {
    buildCommand(specs: string[], layer: string, reportDir: string): string {
      const reportFile = path.join(reportDir, `${layer}-results.json`);
      const specList = specs.join(' ');
      return `npm test -- ${specList} --json > "${reportFile}" 2>&1`;
    },
    parseResults(reportDir: string, layer: string): ParsedTestResult[] {
      const reportFile = path.join(reportDir, `${layer}-results.json`);
      if (!fs.existsSync(reportFile)) return [];

      const raw = fs.readFileSync(reportFile, 'utf-8').trim();
      if (!raw) return [];

      // Tenta parsear como Jest JSON
      const jsonStart = raw.indexOf('{');
      if (jsonStart < 0) return [];

      let report: any;
      try { report = JSON.parse(raw.substring(jsonStart)); } catch { return []; }

      const results: ParsedTestResult[] = [];
      for (const suite of report.testResults || []) {
        for (const test of suite.testResults || suite.assertionResults || []) {
          results.push({
            name: test.fullName || test.title || test.ancestorTitles?.join(' > ') || '',
            file: suite.testFilePath || suite.name || '',
            outcome: test.status === 'passed' ? 'passed' : test.status === 'failed' ? 'failed' : 'skipped',
            durationMs: test.duration || 0,
            errorMessage: test.failureMessages?.join('\n'),
          });
        }
      }
      return results;
    },
  };
}

function resolveRunner(framework: string, cwd: string): FrameworkRunner {
  const fw = (framework || '').toLowerCase();
  if (fw.includes('playwright')) return createPlaywrightRunner(cwd);
  if (fw.includes('cypress')) return createCypressRunner(cwd);
  if (fw.includes('robot')) return createRobotRunner(cwd);
  return createGenericRunner(cwd);
}

// ─────────────────────────────────────────────────────────────────────
// Matching: cruzar resultado do reporter com teste do plano
// ─────────────────────────────────────────────────────────────────────

function matchResultToPlannedTest(
  result: ParsedTestResult,
  plannedTests: RegressionTestEntry[],
): RegressionTestEntry | undefined {
  const normResult = normalizeTestName(result.file || result.name);

  // 1. Match exato por nome normalizado
  let match = plannedTests.find(t => normalizeTestName(t.test) === normResult);
  if (match) return match;

  // 2. Match parcial — resultado contém o nome do teste ou vice-versa
  match = plannedTests.find(t => {
    const normTest = normalizeTestName(t.test);
    return normResult.includes(normTest) || normTest.includes(normResult);
  });
  return match;
}

// ─────────────────────────────────────────────────────────────────────
// Gerador de Relatório Markdown
// ─────────────────────────────────────────────────────────────────────

function generateExecutionReport(report: ExecutionReport): string {
  const lines: string[] = [];
  const s = report.summary;
  const pr = report.pr;

  lines.push(`# 📊 Relatório de Execução — PR #${pr.id}`);
  lines.push('');
  lines.push('> Gerado automaticamente por **FastQA Regression Execution**');
  lines.push(`> Data: ${new Date().toLocaleString('pt-BR')}`);
  lines.push(`> Modo: ${report.mode === 'local' ? '🖥️ Execução Local' : '☁️ Pipeline'}`);
  lines.push('');

  // ── Resumo ──────────────────────────────────────────────────────
  lines.push('## 📋 Resumo');
  lines.push('');
  lines.push('| Métrica | Valor |');
  lines.push('|---------|-------|');
  lines.push(`| Total planejado | ${s.totalPlanned} |`);
  lines.push(`| Total executado | ${s.totalExecuted} |`);
  lines.push(`| ✅ Passou | ${s.passed} |`);
  lines.push(`| ❌ Falhou | ${s.failed} |`);
  lines.push(`| ⏭️ Skipped | ${s.skipped} |`);
  lines.push(`| ⚠️ Erros | ${s.errors} |`);
  lines.push(`| 🔍 Não encontrado | ${s.notFound} |`);
  lines.push(`| Taxa de sucesso | **${s.passRate}** |`);
  lines.push(`| Duração total | ${formatDuration(s.durationMs)} |`);
  lines.push('');

  // ── Barra visual ────────────────────────────────────────────────
  if (s.totalExecuted > 0) {
    const passPct = Math.round((s.passed / s.totalExecuted) * 100);
    const failPct = Math.round((s.failed / s.totalExecuted) * 100);
    lines.push(`> ${'🟩'.repeat(Math.round(passPct / 5))}${'🟥'.repeat(Math.round(failPct / 5))}${'⬜'.repeat(Math.max(0, 20 - Math.round(passPct / 5) - Math.round(failPct / 5)))} ${passPct}% sucesso`);
    lines.push('');
  }

  // ── Validação de Risco ──────────────────────────────────────────
  const rv = report.riskValidation;
  if (rv.highRiskFailures.length > 0) {
    lines.push('## 🔴 Validação de Risco — Falhas em Testes de Alta Prioridade');
    lines.push('');
    lines.push('> Testes classificados como `critical` ou `high` que falharam na execução.');
    lines.push('');
    lines.push('| Teste | Área | Risco | Layer | Erro |');
    lines.push('|-------|------|-------|-------|------|');
    for (const r of rv.highRiskFailures) {
      const area = r.sourceFile.split('/').filter(Boolean)[0] || '—';
      const error = truncate(r.errorMessage || '—', 60);
      lines.push(`| ${r.test} | ${area} | 🔴 ${r.riskPlanned} | ${r.layer} | ${error} |`);
    }
    lines.push('');
  }

  if (rv.unexpectedFailures.length > 0) {
    lines.push('## 🟡 Falhas Inesperadas — Risco Baixo/Médio');
    lines.push('');
    lines.push('| Teste | Layer | Risco | Erro |');
    lines.push('|-------|-------|-------|------|');
    for (const r of rv.unexpectedFailures) {
      const error = truncate(r.errorMessage || '—', 60);
      lines.push(`| ${r.test} | ${r.layer} | ${r.riskPlanned} | ${error} |`);
    }
    lines.push('');
  }

  // ── Resultados por Área ─────────────────────────────────────────
  lines.push('## 📋 Resultados por Área');
  lines.push('');
  for (const area of report.areaResults) {
    const icon = area.failed === 0 ? '✅' : '❌';
    lines.push(`### ${icon} ${area.area} (${area.passed}/${area.total} passou)`);
    lines.push('');

    const areaResults = report.results.filter(r => {
      const rArea = r.sourceFile.split('/').filter(Boolean)[0] || '—';
      return rArea === area.area;
    });

    if (areaResults.length > 0) {
      lines.push('| Teste | Layer | Resultado | Duração | Erro |');
      lines.push('|-------|-------|-----------|---------|------|');
      for (const r of areaResults) {
        const icon = r.outcome === 'passed' ? '✅' : r.outcome === 'failed' ? '❌' : r.outcome === 'skipped' ? '⏭️' : '⚠️';
        const error = r.errorMessage ? truncate(r.errorMessage, 50) : '—';
        lines.push(`| ${r.test} | ${r.layer} | ${icon} ${r.outcome} | ${formatDuration(r.durationMs)} | ${error} |`);
      }
      lines.push('');
    }
  }

  // ── Não Encontrados ─────────────────────────────────────────────
  if (report.notFound.length > 0) {
    lines.push('## ⚠️ Testes Não Encontrados');
    lines.push('');
    lines.push('> Testes do plano de regressão que não foram localizados ou não produziram resultados.');
    lines.push('');
    for (const t of report.notFound) {
      lines.push(`- \`${t}\``);
    }
    lines.push('');
  }

  // ── Próximos Passos ─────────────────────────────────────────────
  lines.push('## 🏷️ Próximos Passos');
  lines.push('');
  if (s.failed > 0) {
    lines.push('- 🔧 Use `@fastqa:verify_and_fix` para corrigir automaticamente as falhas de teste');
  }
  lines.push('- 📊 Use `@fastqa:azdo_sync_pipeline_results` para sincronizar resultados com o Test Plan');
  lines.push('- 📋 Use `@fastqa:azdo_generate_report` para gerar relatório formal');
  if (report.notFound.length > 0) {
    lines.push('- 💡 Use `@fastqa:test_case_with_fastqa` para gerar testes para os itens não encontrados');
  }
  lines.push('');

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────
// Função principal
// ─────────────────────────────────────────────────────────────────────

async function executeRegressionPlan(params: ExecuteRegressionPlanParams): Promise<ExecutionReport> {
  const {
    plan: planPath,
    mode = 'local',
    layer: layerFilter = 'all',
    riskLevel = 'all',
    output,
    dryRun = false,
    timeout = DEFAULT_TIMEOUT,
  } = params;

  console.log('');
  console.log('═══════════════════════════════════════════════════════════════');
  console.log('  FastQA — Execução de Plano de Regressão');
  console.log('═══════════════════════════════════════════════════════════════');
  console.log('');

  // ── 1. Carregar plano ───────────────────────────────────────────
  console.log('📂 [1/5] Carregando plano de regressão...');

  const resolvedPlanPath = path.resolve(planPath);
  if (!fs.existsSync(resolvedPlanPath)) {
    throw new Error(`Plano não encontrado: ${resolvedPlanPath}`);
  }

  const planJson: RegressionAnalysisJson = JSON.parse(fs.readFileSync(resolvedPlanPath, 'utf-8'));
  console.log(`   PR #${planJson.pr.id}: ${truncate(planJson.pr.title, 60)}`);
  console.log(`   Testes no plano: ${planJson.tests.length}`);

  // ── 2. Carregar configuração do projeto ─────────────────────────
  console.log('');
  console.log('⚙️  [2/5] Carregando configuração do projeto...');

  let config: ProjectConfig = {};
  const configPath = path.resolve(CONFIG_PATH);
  if (fs.existsSync(configPath)) {
    config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  }

  const framework = config.connectors?.output?.automation_framework || 'playwright';
  const automationRoot = config.folder_structure?.custom_paths?.automation_root || 'fastqa/automated_test';
  const cwd = path.resolve(automationRoot);

  console.log(`   Framework: ${framework}`);
  console.log(`   Automation root: ${automationRoot}`);
  console.log(`   Modo: ${mode}`);

  // ── 3. Filtrar e agrupar testes ─────────────────────────────────
  console.log('');
  console.log('🎯 [3/5] Filtrando e agrupando testes...');

  let testsToRun = planJson.tests.filter(t => !t.test.startsWith('('));

  // Filtrar por risk level
  if (riskLevel !== 'all') {
    testsToRun = testsToRun.filter(t => riskPassesFilter(t.risk, riskLevel));
    console.log(`   Filtro de risco: >= ${riskLevel} → ${testsToRun.length} teste(s)`);
  }

  // Filtrar por layer
  if (layerFilter !== 'all') {
    testsToRun = testsToRun.filter(t => (t.layer || 'e2e') === layerFilter);
    console.log(`   Filtro de layer: ${layerFilter} → ${testsToRun.length} teste(s)`);
  }

  // Agrupar por layer
  const testsByLayer = new Map<string, RegressionTestEntry[]>();
  for (const t of testsToRun) {
    const layer = t.layer || 'e2e';
    if (!testsByLayer.has(layer)) testsByLayer.set(layer, []);
    testsByLayer.get(layer)!.push(t);
  }

  for (const [layer, tests] of testsByLayer) {
    console.log(`   📦 ${layer}: ${tests.length} teste(s)`);
  }

  // ── 4. Executar testes ──────────────────────────────────────────
  console.log('');
  if (dryRun) {
    console.log('📄 [4/5] Dry-run: comandos que seriam executados:');
  } else {
    console.log('🚀 [4/5] Executando testes...');
  }

  const runner = resolveRunner(framework, cwd);
  const reportDir = path.resolve(DEFAULT_OUTPUT_DIR, '.execution-reports');
  if (!dryRun && !fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  const allResults: TestExecutionResult[] = [];
  const notFound: string[] = [];
  let totalDurationMs = 0;

  for (const [layer, tests] of testsByLayer) {
    const specs = [...new Set(tests.map(t => t.test))];
    const command = runner.buildCommand(specs, layer, reportDir);

    console.log('');
    console.log(`   ── ${layer.toUpperCase()} (${specs.length} specs) ──`);
    console.log(`   $ ${command}`);

    if (dryRun) continue;

    // Executar comando
    const startTime = Date.now();
    try {
      execSync(command, {
        cwd,
        timeout,
        stdio: ['inherit', 'pipe', 'pipe'],
        encoding: 'utf-8',
        windowsHide: true,
      });
    } catch (err: any) {
      // Exit code != 0 é esperado quando testes falham
      if (err.killed) {
        console.log(`   ⏰ Timeout: execução de ${layer} excedeu ${formatDuration(timeout)}`);
      }
    }
    const layerDuration = Date.now() - startTime;
    totalDurationMs += layerDuration;
    console.log(`   ⏱️  Duração: ${formatDuration(layerDuration)}`);

    // Parsear resultados
    const parsed = runner.parseResults(reportDir, layer);
    console.log(`   📊 ${parsed.length} resultado(s) parseado(s)`);

    // Cross-referência com plano
    const matchedTests = new Set<string>();
    for (const result of parsed) {
      const planned = matchResultToPlannedTest(result, tests);
      if (planned) {
        matchedTests.add(planned.test);
        allResults.push({
          test: planned.test,
          layer,
          outcome: result.outcome,
          durationMs: result.durationMs,
          errorMessage: result.errorMessage,
          stackTrace: result.stackTrace,
          sourceFile: planned.sourceFile,
          riskPlanned: planned.risk,
        });
      } else {
        // Resultado existe mas não estava no plano — incluir como extra
        allResults.push({
          test: result.file || result.name,
          layer,
          outcome: result.outcome,
          durationMs: result.durationMs,
          errorMessage: result.errorMessage,
          stackTrace: result.stackTrace,
          sourceFile: '—',
          riskPlanned: 'low',
        });
      }
    }

    // Detectar testes do plano que não foram encontrados
    for (const t of tests) {
      if (!matchedTests.has(t.test)) {
        notFound.push(t.test);
      }
    }
  }

  // ── 5. Gerar relatório ──────────────────────────────────────────
  console.log('');
  console.log('📊 [5/5] Gerando relatório...');

  // Resumo por área
  const areaMap = new Map<string, AreaExecutionSummary>();
  for (const r of allResults) {
    const area = r.sourceFile.split('/').filter(Boolean)[0] || '—';
    if (!areaMap.has(area)) {
      areaMap.set(area, { area, total: 0, passed: 0, failed: 0, skipped: 0, errors: 0 });
    }
    const a = areaMap.get(area)!;
    a.total++;
    if (r.outcome === 'passed') a.passed++;
    else if (r.outcome === 'failed') a.failed++;
    else if (r.outcome === 'skipped') a.skipped++;
    else a.errors++;
  }

  const passed = allResults.filter(r => r.outcome === 'passed').length;
  const failed = allResults.filter(r => r.outcome === 'failed').length;
  const skipped = allResults.filter(r => r.outcome === 'skipped').length;
  const errors = allResults.filter(r => r.outcome === 'error').length;
  const passRate = allResults.length > 0
    ? `${Math.round((passed / allResults.length) * 100)}%`
    : '—';

  // Validação de risco
  const highRiskFailures = allResults.filter(r =>
    r.outcome === 'failed' && (r.riskPlanned === 'critical' || r.riskPlanned === 'high')
  );
  const unexpectedFailures = allResults.filter(r =>
    r.outcome === 'failed' && r.riskPlanned !== 'critical' && r.riskPlanned !== 'high'
  );

  const report: ExecutionReport = {
    planFile: planPath,
    pr: planJson.pr,
    mode,
    results: allResults,
    notFound,
    areaResults: [...areaMap.values()].sort((a, b) => b.failed - a.failed || b.total - a.total),
    riskValidation: { highRiskFailures, unexpectedFailures },
    summary: {
      totalPlanned: testsToRun.length,
      totalExecuted: allResults.length,
      passed,
      failed,
      skipped,
      errors,
      notFound: notFound.length,
      durationMs: totalDurationMs,
      passRate,
    },
  };

  // Salvar relatórios
  if (!dryRun) {
    const prId = planJson.pr.id;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
    const outputDir = output ? path.dirname(path.resolve(output)) : path.resolve(DEFAULT_OUTPUT_DIR);

    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    const mdFileName = output
      ? path.resolve(output)
      : path.join(outputDir, `PR-${prId}_execution_report_${timestamp}.md`);
    const jsonFileName = mdFileName.replace(/\.md$/, '.json');

    const markdown = generateExecutionReport(report);
    fs.writeFileSync(mdFileName, markdown, 'utf-8');
    fs.writeFileSync(jsonFileName, JSON.stringify(report, null, 2), 'utf-8');

    console.log(`   📄 Relatório Markdown: ${mdFileName}`);
    console.log(`   📊 Relatório JSON: ${jsonFileName}`);
  } else {
    console.log('   📄 Dry-run: relatórios não salvos.');
  }

  // ── Resumo no terminal ──────────────────────────────────────────
  console.log('');
  console.log('═══════════════════════════════════════════════════════════════');
  console.log('   Execução de Regressão Concluída');
  console.log('═══════════════════════════════════════════════════════════════');
  console.log('');
  console.log(`   PR:              #${planJson.pr.id} — ${truncate(planJson.pr.title, 50)}`);
  console.log(`   Planejados:      ${report.summary.totalPlanned}`);
  console.log(`   Executados:      ${report.summary.totalExecuted}`);
  console.log(`   ✅ Passou:       ${report.summary.passed}`);
  console.log(`   ❌ Falhou:       ${report.summary.failed}`);
  console.log(`   ⏭️  Skipped:     ${report.summary.skipped}`);
  console.log(`   ⚠️  Não encontr.: ${report.summary.notFound}`);
  console.log(`   Taxa:            ${report.summary.passRate}`);
  console.log(`   Duração:         ${formatDuration(report.summary.durationMs)}`);
  console.log('');

  if (highRiskFailures.length > 0) {
    console.log('🔴 ATENÇÃO: Falhas em testes de alta prioridade:');
    for (const r of highRiskFailures) {
      console.log(`   ❌ [${r.riskPlanned}] ${r.test}: ${truncate(r.errorMessage || '—', 60)}`);
    }
    console.log('');
  }

  return report;
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

  const plan = getArg('--plan');
  const mode = (getArg('--mode') || 'local') as 'local' | 'pipeline';
  const layer = getArg('--layer') || 'all';
  const riskLevel = (getArg('--risk-level') || 'all') as RiskLevel | 'all';
  const output = getArg('--output');
  const timeoutStr = getArg('--timeout');
  const dryRun = hasFlag('--dry-run');

  if (hasFlag('--help') || !plan) {
    console.log('');
    console.log('Uso:');
    console.log('  npx tsx fastqa/scripts/regression/commands/execute-regression-plan.command.ts [opções]');
    console.log('');
    console.log('Opções obrigatórias:');
    console.log('  --plan <path>             Caminho do JSON do plano de regressão');
    console.log('');
    console.log('Opções adicionais:');
    console.log('  --mode <local|pipeline>   Modo de execução (padrão: local)');
    console.log('  --layer <e2e|api|unit|all> Filtrar por layer (padrão: all)');
    console.log('  --risk-level <level|all>  Filtrar por nível de risco mínimo (padrão: all)');
    console.log('  --output <path>           Caminho de saída do relatório');
    console.log('  --timeout <ms>            Timeout por layer em ms (padrão: 600000)');
    console.log('  --dry-run                 Simular sem executar');
    console.log('  --help                    Exibe esta ajuda');
    console.log('');
    console.log('Exemplos:');
    console.log('  # Executar tudo localmente');
    console.log('  npx tsx execute-regression-plan.command.ts \\');
    console.log('    --plan fastqa/manual_test/regression_analysis/PR-123_regression_plan.json');
    console.log('');
    console.log('  # Só testes de alta prioridade, layer e2e');
    console.log('  npx tsx execute-regression-plan.command.ts \\');
    console.log('    --plan PR-123_regression_plan.json --layer e2e --risk-level high');
    console.log('');
    console.log('  # Dry-run: ver o que seria executado');
    console.log('  npx tsx execute-regression-plan.command.ts \\');
    console.log('    --plan PR-123_regression_plan.json --dry-run');
    console.log('');
    process.exit(hasFlag('--help') ? 0 : 1);
  }

  try {
    const report = await executeRegressionPlan({
      plan,
      mode,
      layer,
      riskLevel,
      output,
      dryRun,
      timeout: timeoutStr ? parseInt(timeoutStr, 10) : undefined,
    });
    process.exit(report.summary.failed > 0 ? 2 : 0);
  } catch (error) {
    console.error('\n❌ Erro na execução do plano de regressão:');
    console.error(error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

export { executeRegressionPlan };
