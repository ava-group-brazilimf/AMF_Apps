/**
 * ============================================================================
 * FastQA — Report Generator Utility
 * ============================================================================
 * Gera relatórios de execução de testes em formato Markdown.
 * Usado pelo comando @fastqa:azdo_generate_report.
 * ============================================================================
 */

import * as fs from 'fs';
import * as path from 'path';
import type { TestRun, TestResult, TestOutcome } from '../types/azure-devops.types';

export interface ReportData {
  title: string;
  testPlanId?: number;
  testPlanName?: string;
  testRunId?: number;
  testSuiteId?: number;
  executionDate: string;
  executedBy?: string;
  results: ReportTestResult[];
  bugs?: ReportBug[];
}

export interface ReportTestResult {
  testCaseId: number;
  testCaseTitle: string;
  outcome: TestOutcome;
  evidenceFiles: string[];
  bugId?: number;
  duration?: number;
  comment?: string;
}

export interface ReportBug {
  id: number;
  title: string;
  severity: string;
  testCaseId: number;
  url?: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Geração de Relatório Markdown
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Gera relatório completo em formato Markdown.
 */
export function generateMarkdownReport(data: ReportData): string {
  const lines: string[] = [];

  // Cabeçalho
  lines.push(`# 📊 Relatório de Execução de Testes`);
  lines.push('');
  if (data.testPlanName) {
    lines.push(`**Test Plan:** ${data.testPlanName}${data.testPlanId ? ` (ID: ${data.testPlanId})` : ''}`);
  }
  if (data.testRunId) {
    lines.push(`**Test Run ID:** ${data.testRunId}`);
  }
  if (data.testSuiteId) {
    lines.push(`**Test Suite ID:** ${data.testSuiteId}`);
  }
  lines.push(`**Data:** ${data.executionDate}`);
  if (data.executedBy) {
    lines.push(`**Executado por:** ${data.executedBy}`);
  }
  lines.push('');
  lines.push('---');
  lines.push('');

  // Resumo Executivo
  const summary = calculateSummary(data.results);
  lines.push('## Resumo Executivo');
  lines.push('');
  lines.push('| Métrica | Valor |');
  lines.push('|---------|-------|');
  lines.push(`| Total de Test Cases | ${summary.total} |`);
  lines.push(`| ✅ Passed | ${summary.passed} (${summary.passedPct}%) |`);
  lines.push(`| ❌ Failed | ${summary.failed} (${summary.failedPct}%) |`);
  lines.push(`| ⚠️ Blocked | ${summary.blocked} (${summary.blockedPct}%) |`);
  lines.push(`| ⏳ Not Executed | ${summary.notExecuted} (${summary.notExecutedPct}%) |`);
  lines.push(`| 📎 Evidências | ${summary.totalEvidence} |`);
  if (data.bugs && data.bugs.length > 0) {
    lines.push(`| 🐛 Bugs Criados | ${data.bugs.length} |`);
  }
  lines.push('');

  // Taxa de aprovação visual
  lines.push(`**Taxa de Aprovação:** ${summary.passedPct}%`);
  lines.push(`${'█'.repeat(Math.round(summary.passedPct / 5))}${'░'.repeat(20 - Math.round(summary.passedPct / 5))} ${summary.passedPct}%`);
  lines.push('');
  lines.push('---');
  lines.push('');

  // Detalhamento por Test Case
  lines.push('## Detalhamento por Test Case');
  lines.push('');
  lines.push('| TC ID | Título | Resultado | Evidência | Bug |');
  lines.push('|-------|--------|-----------|-----------|-----|');

  for (const result of data.results) {
    const outcomeIcon = getOutcomeIcon(result.outcome);
    const evidence = result.evidenceFiles.length > 0
      ? result.evidenceFiles.map(f => path.basename(f)).join(', ')
      : '—';
    const bug = result.bugId ? `BUG-${result.bugId}` : '—';
    lines.push(
      `| TC-${result.testCaseId} | ${result.testCaseTitle} | ${outcomeIcon} ${result.outcome} | ${evidence} | ${bug} |`
    );
  }
  lines.push('');

  // Bugs vinculados
  if (data.bugs && data.bugs.length > 0) {
    lines.push('---');
    lines.push('');
    lines.push('## 🐛 Bugs Vinculados');
    lines.push('');
    lines.push('| Bug ID | Título | Severidade | Test Case |');
    lines.push('|--------|--------|------------|-----------|');

    for (const bug of data.bugs) {
      lines.push(`| BUG-${bug.id} | ${bug.title} | ${bug.severity} | TC-${bug.testCaseId} |`);
    }
    lines.push('');
  }

  // Rodapé
  lines.push('---');
  lines.push('');
  lines.push(`*Relatório gerado automaticamente pelo FastQA em ${new Date().toISOString()}*`);
  lines.push('');

  return lines.join('\n');
}

/**
 * Gera relatório em formato JSON.
 */
export function generateJsonReport(data: ReportData): string {
  const summary = calculateSummary(data.results);
  return JSON.stringify(
    {
      ...data,
      summary,
      generatedAt: new Date().toISOString(),
    },
    null,
    2
  );
}

/**
 * Salva relatório em arquivo.
 */
export function saveReport(
  content: string,
  outputPath: string
): string {
  const resolvedPath = path.resolve(outputPath);
  const dir = path.dirname(resolvedPath);

  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  fs.writeFileSync(resolvedPath, content, 'utf-8');
  return resolvedPath;
}

// ═══════════════════════════════════════════════════════════════════════════
// Utilitários internos
// ═══════════════════════════════════════════════════════════════════════════

interface Summary {
  total: number;
  passed: number;
  failed: number;
  blocked: number;
  notExecuted: number;
  passedPct: number;
  failedPct: number;
  blockedPct: number;
  notExecutedPct: number;
  totalEvidence: number;
}

function calculateSummary(results: ReportTestResult[]): Summary {
  const total = results.length;
  const passed = results.filter(r => r.outcome === 'Passed').length;
  const failed = results.filter(r => r.outcome === 'Failed').length;
  const blocked = results.filter(r => r.outcome === 'Blocked').length;
  const notExecuted = results.filter(r =>
    r.outcome === 'NotExecuted' || r.outcome === 'None'
  ).length;
  const totalEvidence = results.reduce(
    (acc, r) => acc + r.evidenceFiles.length, 0
  );

  const pct = (count: number) => total > 0 ? Math.round((count / total) * 100) : 0;

  return {
    total,
    passed,
    failed,
    blocked,
    notExecuted,
    passedPct: pct(passed),
    failedPct: pct(failed),
    blockedPct: pct(blocked),
    notExecutedPct: pct(notExecuted),
    totalEvidence,
  };
}

function getOutcomeIcon(outcome: TestOutcome): string {
  switch (outcome) {
    case 'Passed': return '✅';
    case 'Failed': return '❌';
    case 'Blocked': return '⚠️';
    case 'NotApplicable': return '🚫';
    case 'NotExecuted':
    case 'None': return '⏳';
    case 'Inconclusive': return '❓';
    case 'Timeout': return '⏱️';
    case 'Aborted': return '🛑';
    default: return '❓';
  }
}

export default { generateMarkdownReport, generateJsonReport, saveReport };
