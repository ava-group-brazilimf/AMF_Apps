/**
 * ============================================================================
 * FastQA — Regression Analysis Types
 * ============================================================================
 * Interfaces e tipos para análise de regressão por PR da aplicação.
 * Cobre provedores de PR, mapeamento funcional, classificação de risco
 * e geração de plano de regressão.
 *
 * Referência:
 *   FastQA Phase 6 — Regression Analysis
 * ============================================================================
 */

// ═══════════════════════════════════════════════════════════════════════════
// Provedores de PR
// ═══════════════════════════════════════════════════════════════════════════

/** Provedores suportados para obtenção de dados de PR */
export type PrProvider = 'azure-devops' | 'git-local';

/** Input normalizado para obtenção de dados de PR */
export interface PrInput {
  provider: PrProvider;
  prId?: number;
  repoNameOrId?: string;
  appRepoPath?: string;
  targetBranch?: string;
}

/** Dados normalizados de um PR (contrato unificado entre provedores) */
export interface PrData {
  id: number;
  title: string;
  source: string;
  target: string;
  author: string;
  date: string;
  provider: PrProvider;
}

/** Alteração de arquivo em um PR */
export interface PrFileChange {
  changeType: 'add' | 'edit' | 'delete' | 'rename';
  path: string;
  /** Conteúdo do diff (patch) para este arquivo — disponível para top N arquivos */
  diff?: string;
  /** Estatísticas do diff (linhas adicionadas/removidas) */
  diffStats?: { additions: number; deletions: number };
}

/** Work Item associado a um PR */
export interface PrWorkItem {
  id: string;
  title?: string;
  priority?: number;
}

/** Resultado unificado da análise de PR (contrato entre provedores) */
export interface PrAnalysisResult {
  pr: PrData;
  files: PrFileChange[];
  workItems: PrWorkItem[];
}

// ═══════════════════════════════════════════════════════════════════════════
// Áreas Funcionais e Mapeamento
// ═══════════════════════════════════════════════════════════════════════════

/** Escopo de uma área funcional da aplicação */
export type FunctionalAreaScope = 'page' | 'api' | 'service' | 'component' | 'model' | 'global';

/** Área funcional identificada a partir dos arquivos do PR */
export interface FunctionalArea {
  name: string;
  scope: FunctionalAreaScope;
  sourceFiles: string[];
}

/** Mapeamento entre um teste e uma área funcional */
export interface TestMapping {
  test: string;
  area: string;
  confidence: 'high' | 'medium-high' | 'medium' | 'low';
  strategy: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Classificação de Risco
// ═══════════════════════════════════════════════════════════════════════════

/** Nível de risco de um teste na regressão */
export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'gap';

/** Entrada de teste no plano de regressão */
export interface RegressionTestEntry {
  test: string;
  tags: string[];
  risk: RiskLevel;
  reason: string;
  confidence: string;
  sourceFile: string;
  /** Camada de teste: e2e, api, unit, manual, etc. */
  layer?: string;
  /** Todas as áreas funcionais (do PR) que este teste cobre */
  coveredAreas?: string[];
}

// ═══════════════════════════════════════════════════════════════════════════
// Plano de Regressão
// ═══════════════════════════════════════════════════════════════════════════

/** Alerta de impacto global (advisory, não é um teste) */
export interface GlobalAlert {
  message: string;
  strategy: string;
  sourceFile: string;
}

/** Plano de regressão completo gerado pela análise */
export interface RegressionPlan {
  pr: PrData;
  areas: FunctionalArea[];
  tests: RegressionTestEntry[];
  gaps: Array<{ file: string; area: string; note: string }>;
  commands: Array<{ label: string; command: string }>;
  /** Alertas de impacto global (arquivos de config/infra alterados) */
  globalAlerts: GlobalAlert[];
  summary: {
    filesChanged: number;
    areasImpacted: number;
    testsImpacted: number;
    gapsFound: number;
    avgConfidence: string;
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// Regression Map (regression-map.yaml)
// ═══════════════════════════════════════════════════════════════════════════

/** Área no regression-map.yaml */
export interface RegressionMapArea {
  description?: string;
  app_patterns: string[];
  tests: string[];
  features: string[];
  tags: string[];
  /** Nível de cobertura de testes: none (gap), partial ou full */
  coverage?: 'none' | 'partial' | 'full';
  /** Áreas que esta área depende diretamente (via import graph) */
  dependencies?: string[];
  /** Áreas que dependem desta (via import graph) */
  dependents?: string[];
  /** Módulo compartilhado por 3+ áreas distintas (infra, não funcional) */
  shared?: boolean;
  /** Escopo de impacto: global real ou targeted a áreas específicas */
  impact_scope?: 'global' | 'targeted';
  /** Se targeted, lista de áreas realmente impactadas */
  impacted_areas?: string[];
}

/** Estrutura completa do regression-map.yaml */
export interface RegressionMapConfig {
  version: string;
  /** Camadas de teste usadas na geração do mapa (e2e, api, unit, etc.) */
  layers_used?: TestLayer[];
  areas: Record<string, RegressionMapArea>;
  global_triggers: string[];
}

// ═══════════════════════════════════════════════════════════════════════════
// Parâmetros de Comando CLI
// ═══════════════════════════════════════════════════════════════════════════

/** Parâmetros para o comando analyze-pr-regression */
export interface AnalyzePrRegressionParams {
  prUrl?: string;
  prId?: number;
  repo?: string;
  appRepoPath?: string;
  targetBranch?: string;
  output?: string;
  useGitLocal?: boolean;
  dryRun?: boolean;
  /** Gera saída JSON estruturada para consumo pelo agente IA */
  json?: boolean;
  /** Força geração do relatório MD mesmo com --json (backward compat) */
  mdOnly?: boolean;
}

/** Saída JSON estruturada para o agente IA consumir */
export interface RegressionAnalysisJson {
  pr: PrData;
  files: PrFileChange[];
  areas: FunctionalArea[];
  tests: RegressionTestEntry[];
  gaps: Array<{ file: string; area: string; note: string }>;
  commands: Array<{ label: string; command: string }>;
  summary: RegressionPlan['summary'];
  /** Arquivos com maior impacto (top 5 por convergência e risco) */
  top_impact_files: Array<{
    path: string;
    area: string;
    scope: FunctionalAreaScope;
    test_count: number;
    risk: RiskLevel;
  }>;
  /** Áreas sem cobertura de teste para a IA analisar */
  uncovered_areas: Array<{
    name: string;
    scope: FunctionalAreaScope;
    files: string[];
  }>;
}

/** Camada de teste adicional (API, Unit, etc.) */
export interface TestLayer {
  name: string;       // Identificador da camada: 'e2e' | 'api' | 'unit' | string
  path: string;       // Caminho relativo do diretório de testes
}

/** Parâmetros para o comando generate-regression-map */
export interface GenerateRegressionMapParams {
  output?: string;
  merge?: boolean;
  /** Camadas de teste a varrer. Se omitido, usa paths do project_config.json */
  layers?: TestLayer[];
  /** Caminho do repo da aplicação para gerar app_patterns precisos */
  appRepoPath?: string;
  /** Diretórios fonte da app a varrer (default: auto-detect) */
  appSrcDirs?: string[];
  /** Gera .enrichment-context.json para o agente processar via IA */
  enrich?: boolean;
  /** Usa cache de classificações anteriores */
  cache?: boolean;
  /** Inclui áreas da app sem testes (gaps) no mapa gerado */
  includeGaps?: boolean;
}

/** Resumo do grafo de dependências para o enriquecimento por IA */
export interface EnrichmentContext {
  /** Arquivos com nomes genéricos que precisam de classificação pela IA */
  ambiguous_files: Array<{
    path: string;
    exports: string[];
    current_area: string;
    inferred_area: string | null;
    confidence: string;
  }>;
  /** Arquivos cross-cutting para revisão de escopo */
  cross_cutting: Array<{
    path: string;
    importedBy: string[];
    current_scope: string;
    suggested_scope: 'global' | 'targeted';
    impacted_areas: string[];
  }>;
  /** Áreas da app sem cobertura de testes */
  uncovered_app_areas: string[];
  /** Áreas com nomes de baixa confiança (ex: ticket IDs) */
  low_confidence_areas: Array<{
    area: string;
    tests: string[];
    reason: string;
  }>;
}

// ═══════════════════════════════════════════════════════════════════════════
// Execução de Plano de Regressão
// ═══════════════════════════════════════════════════════════════════════════

/** Resultado possível de um teste executado */
export type TestExecutionOutcome = 'passed' | 'failed' | 'skipped' | 'error';

/** Resultado individual de um teste executado */
export interface TestExecutionResult {
  test: string;
  layer: string;
  outcome: TestExecutionOutcome;
  durationMs: number;
  errorMessage?: string;
  stackTrace?: string;
  /** Arquivo da app que motivou a inclusão deste teste no plano */
  sourceFile: string;
  /** Risco atribuído no plano de regressão */
  riskPlanned: RiskLevel;
}

/** Resumo de resultados por área funcional */
export interface AreaExecutionSummary {
  area: string;
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  errors: number;
}

/** Relatório completo de execução do plano de regressão */
export interface ExecutionReport {
  /** Plano de regressão utilizado como base */
  planFile: string;
  pr: PrData;
  /** Modo de execução: local ou pipeline */
  mode: 'local' | 'pipeline';
  /** Resultados individuais por teste */
  results: TestExecutionResult[];
  /** Testes do plano que não foram encontrados no projeto */
  notFound: string[];
  /** Resumo por área funcional */
  areaResults: AreaExecutionSummary[];
  /** Validação de risco: testes high/critical que falharam */
  riskValidation: {
    highRiskFailures: TestExecutionResult[];
    unexpectedFailures: TestExecutionResult[];
  };
  summary: {
    totalPlanned: number;
    totalExecuted: number;
    passed: number;
    failed: number;
    skipped: number;
    errors: number;
    notFound: number;
    durationMs: number;
    passRate: string;
  };
}

/** Parâmetros para o comando execute-regression-plan */
export interface ExecuteRegressionPlanParams {
  /** Caminho do JSON do plano de regressão */
  plan: string;
  /** Modo de execução: local (default) ou pipeline */
  mode?: 'local' | 'pipeline';
  /** Filtrar por layer: e2e, api, unit ou all (default) */
  layer?: string;
  /** Filtrar por nível de risco mínimo */
  riskLevel?: RiskLevel | 'all';
  /** Caminho de saída do relatório */
  output?: string;
  /** Apenas mostra o que será executado sem rodar */
  dryRun?: boolean;
  /** Timeout em ms por layer (default: 600000 = 10min) */
  timeout?: number;
}
