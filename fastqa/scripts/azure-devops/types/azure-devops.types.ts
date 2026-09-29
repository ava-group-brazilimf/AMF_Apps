/**
 * ============================================================================
 * FastQA — Azure DevOps TypeScript Types
 * ============================================================================
 * Interfaces e tipos para integração com Azure DevOps REST API v7.1.
 * Cobre Work Items, Test Plans, Test Runs, Attachments e payloads de request.
 *
 * Referência:
 *   https://learn.microsoft.com/en-us/rest/api/azure/devops
 * ============================================================================
 */

// ═══════════════════════════════════════════════════════════════════════════
// Work Items
// ═══════════════════════════════════════════════════════════════════════════

/** Tipos de work item suportados */
export type WorkItemType =
  | 'Bug'
  | 'Product Backlog Item'
  | 'Task'
  | 'Test Case'
  | 'Feature'
  | 'User Story'
  | 'Epic'
  | 'Impediment';

/** Operação JSON Patch para update/create de work items */
export interface JsonPatchOperation {
  op: 'add' | 'replace' | 'remove' | 'test';
  path: string;
  value?: unknown;
  from?: string;
}

/** Work Item retornado pela API */
export interface WorkItem {
  id: number;
  rev: number;
  url: string;
  fields: WorkItemFields;
  relations?: WorkItemRelation[];
  _links?: Record<string, { href: string }>;
}

/** Campos comuns de um Work Item */
export interface WorkItemFields {
  'System.Id'?: number;
  'System.Title'?: string;
  'System.Description'?: string;
  'System.State'?: string;
  'System.WorkItemType'?: string;
  'System.AssignedTo'?: IdentityRef;
  'System.CreatedBy'?: IdentityRef;
  'System.CreatedDate'?: string;
  'System.ChangedDate'?: string;
  'System.AreaPath'?: string;
  'System.IterationPath'?: string;
  'System.Tags'?: string;
  'System.Reason'?: string;
  'System.History'?: string;
  // Bug
  'Microsoft.VSTS.TCM.ReproSteps'?: string;
  'Microsoft.VSTS.Common.Severity'?: string;
  'Microsoft.VSTS.Common.Priority'?: number;
  'Microsoft.VSTS.TCM.SystemInfo'?: string;
  // Test Case
  'Microsoft.VSTS.TCM.Steps'?: string;
  'Microsoft.VSTS.TCM.Parameters'?: string;
  // PBI / User Story
  'Microsoft.VSTS.Common.AcceptanceCriteria'?: string;
  'Microsoft.VSTS.Scheduling.StoryPoints'?: number;
  // Task
  'Microsoft.VSTS.Scheduling.RemainingWork'?: number;
  'Microsoft.VSTS.Common.Activity'?: string;
  // Genérico
  [key: string]: unknown;
}

/** Referência de identidade (usuário) */
export interface IdentityRef {
  displayName: string;
  uniqueName?: string;
  id?: string;
  url?: string;
  imageUrl?: string;
}

/** Relação entre work items */
export interface WorkItemRelation {
  rel: string;
  url: string;
  attributes: {
    name?: string;
    isLocked?: boolean;
    comment?: string;
    [key: string]: unknown;
  };
}

/** Resultado de listagem de work items */
export interface WorkItemQueryResult {
  queryType: string;
  queryResultType: string;
  asOf: string;
  columns: Array<{ referenceName: string; name: string; url: string }>;
  workItems: Array<{ id: number; url: string }>;
}

// ═══════════════════════════════════════════════════════════════════════════
// Attachments
// ═══════════════════════════════════════════════════════════════════════════

/** Resposta de upload de attachment */
export interface AttachmentUploadResponse {
  id: string;
  url: string;
}

/** Payload para upload de attachment ao Test Result */
export interface TestResultAttachmentPayload {
  stream: string; // Base64 encoded
  fileName: string;
  comment?: string;
  attachmentType: 'GeneralAttachment' | 'CodeCoverage' | 'ConsoleLog';
}

/** Referência de attachment em um work item */
export interface AttachmentReference {
  id: string;
  url: string;
  name?: string;
  size?: number;
}

// ═══════════════════════════════════════════════════════════════════════════
// Test Plans
// ═══════════════════════════════════════════════════════════════════════════

/** Test Plan */
export interface TestPlan {
  id: number;
  name: string;
  state: string;
  iteration?: string;
  areaPath?: string;
  startDate?: string;
  endDate?: string;
  rootSuite?: { id: number; name: string };
  _links?: Record<string, { href: string }>;
}

/** Test Suite */
export interface TestSuite {
  id: number;
  name: string;
  suiteType: 'StaticTestSuite' | 'DynamicTestSuite' | 'RequirementTestSuite';
  parentSuite?: { id: number; name: string };
  plan?: { id: number; name: string };
  testCaseCount?: number;
  children?: TestSuite[];
  _links?: Record<string, { href: string }>;
}

/** Test Case associado a uma Suite (retornado pela API de TestPlan) */
export interface SuiteTestCase {
  testCase: {
    id: number;
    name: string;
    url: string;
  };
  pointAssignments: Array<{
    id: number;
    configurationId: number;
    configurationName: string;
    tester?: IdentityRef;
  }>;
  workItem?: WorkItem;
}

// ═══════════════════════════════════════════════════════════════════════════
// Test Points
// ═══════════════════════════════════════════════════════════════════════════

/** Test Point — ponto de execução dentro de uma Suite */
export interface TestPoint {
  id: number;
  testCaseReference: {
    id: number;
    name: string;
    state: string;
  };
  testPlan: { id: number; name: string };
  suite: { id: number; name: string };
  configuration?: { id: number; name: string };
  assignedTo?: IdentityRef;
  lastTestRun?: { id: number };
  lastResult?: { id: number };
  outcome?: string;
  state?: string;
}

/** Resposta paginada de Test Points */
export interface TestPointsResponse {
  value: TestPoint[];
  count: number;
}

// ═══════════════════════════════════════════════════════════════════════════
// Test Runs
// ═══════════════════════════════════════════════════════════════════════════

/** Payload para criação de Test Run */
export interface CreateTestRunPayload {
  name: string;
  plan: { id: number };
  pointIds: number[];
  automated?: boolean;
  comment?: string;
  state?: 'NotStarted' | 'InProgress' | 'Completed' | 'Aborted' | 'Waiting';
}

/** Test Run retornado pela API */
export interface TestRun {
  id: number;
  name: string;
  state: string;
  plan: { id: number; name?: string };
  startedDate?: string;
  completedDate?: string;
  totalTests: number;
  passedTests: number;
  unanalyzedTests?: number;
  incompleteTests?: number;
  notApplicableTests?: number;
  url: string;
  webAccessUrl?: string;
  _links?: Record<string, { href: string }>;
}

// ═══════════════════════════════════════════════════════════════════════════
// Test Results
// ═══════════════════════════════════════════════════════════════════════════

/** Outcome de um Test Result */
export type TestOutcome =
  | 'Passed'
  | 'Failed'
  | 'Blocked'
  | 'NotApplicable'
  | 'NotExecuted'
  | 'Inconclusive'
  | 'Timeout'
  | 'Aborted'
  | 'None';

/** Test Result retornado pela API */
export interface TestResult {
  id: number;
  testRun: { id: number; name?: string; url?: string };
  testCase: { id: number; name?: string; url?: string };
  testPoint?: { id: number };
  outcome: TestOutcome;
  state: string;
  startedDate?: string;
  completedDate?: string;
  durationInMs?: number;
  errorMessage?: string;
  comment?: string;
  associatedBugs?: Array<{ id: number; name?: string; url?: string }>;
  url: string;
}

/** Payload para atualização de Test Result */
export interface UpdateTestResultPayload {
  id: number;
  outcome: TestOutcome;
  state?: 'Completed' | 'InProgress' | 'Pending';
  comment?: string;
  errorMessage?: string;
  durationInMs?: number;
  associatedBugs?: Array<{ id: number }>;
}

// ═══════════════════════════════════════════════════════════════════════════
// Payloads de Comando
// ═══════════════════════════════════════════════════════════════════════════

/** Parâmetros para criação de bug via comando */
export interface CreateBugParams {
  title: string;
  reproSteps: string;
  expectedResult: string;
  actualResult: string;
  severity: '1 - Critical' | '2 - High' | '3 - Medium' | '4 - Low';
  priority?: 1 | 2 | 3 | 4;
  systemInfo?: string;
  evidencePath?: string;
  parentId?: number;
  tags?: string;
  areaPath?: string;
  iterationPath?: string;
}

/** Parâmetros para criação de test case via comando */
export interface CreateTestCaseParams {
  title: string;
  steps: TestCaseStep[];
  preconditions?: string;
  areaPath?: string;
  iterationPath?: string;
  tags?: string;
  priority?: 1 | 2 | 3 | 4;
}

/** Step de um Test Case */
export interface TestCaseStep {
  action: string;
  expectedResult?: string;
}

/** Parâmetros para upload de evidência */
export interface UploadEvidenceParams {
  testPlanId: number;
  testSuiteId: number;
  testCaseId: number;
  evidencePath: string;
  result: TestOutcome;
  comment?: string;
  attachToWorkItem?: boolean;
}

/** Parâmetros para upload de pasta de evidências */
export interface UploadFolderEvidenceParams extends UploadEvidenceParams {
  recursive?: boolean;
  extensions?: string[];
}

/** Parâmetros para execução completa de teste */
export interface UploadTestExecutionParams extends UploadEvidenceParams {
  autoBug?: boolean;
  bugSeverity?: '1 - Critical' | '2 - High' | '3 - Medium' | '4 - Low';
}

/** Parâmetros para vinculação de work items */
export interface LinkWorkItemsParams {
  sourceId: number;
  targetId: number;
  linkType: string;
  comment?: string;
}

/** Parâmetros para geração de relatório */
export interface GenerateReportParams {
  testPlanId?: number;
  testRunId?: number;
  testSuiteId?: number;
  format?: 'markdown' | 'json';
  outputPath?: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Respostas paginadas (padrão Azure DevOps)
// ═══════════════════════════════════════════════════════════════════════════

/** Resposta paginada genérica */
export interface PaginatedResponse<T> {
  value: T[];
  count: number;
  continuationToken?: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Resultado de operação de comando
// ═══════════════════════════════════════════════════════════════════════════

/** Resultado padronizado retornado pelos scripts de comando */
export interface CommandResult<T = unknown> {
  success: boolean;
  command: string;
  timestamp: string;
  duration: number;
  data?: T;
  error?: {
    message: string;
    statusCode?: number;
    details?: unknown;
  };
}

/** Resultado de upload de evidência */
export interface UploadEvidenceResult {
  testRunId: number;
  testRunUrl: string;
  testResultId: number;
  attachmentUrl: string;
  outcome: TestOutcome;
  fileName: string;
  fileSize: number;
  bugId?: number;
  bugUrl?: string;
}

/** Resultado de upload de pasta */
export interface UploadFolderResult {
  testRunId: number;
  testRunUrl: string;
  testResultId: number;
  outcome: TestOutcome;
  totalFiles: number;
  uploadedFiles: number;
  failedFiles: number;
  totalSize: number;
  files: Array<{
    fileName: string;
    size: number;
    status: 'success' | 'failed';
    attachmentUrl?: string;
    error?: string;
  }>;
}

// ═══════════════════════════════════════════════════════════════════════════
// Git Repositories (Fase 6: Repositório & CI/CD)
// ═══════════════════════════════════════════════════════════════════════════

/** Repositório Git do Azure DevOps */
export interface GitRepository {
  id: string;
  name: string;
  url: string;
  project: { id: string; name: string };
  defaultBranch?: string;
  size?: number;
  remoteUrl?: string;
  sshUrl?: string;
  webUrl?: string;
  isFork?: boolean;
}

/** Referência Git (branch, tag) */
export interface GitRef {
  name: string;
  objectId: string;
  creator?: IdentityRef;
  url?: string;
}

/** Mudança em um commit Git */
export interface GitChange {
  changeType: 'add' | 'edit' | 'delete' | 'rename';
  item: {
    path: string;
  };
  newContent?: {
    content: string;
    contentType: 'rawtext' | 'base64encoded';
  };
}

/** Commit para push Git */
export interface GitCommitPayload {
  comment: string;
  changes: GitChange[];
}

/** RefUpdate para push Git */
export interface GitRefUpdate {
  name: string;
  oldObjectId: string;
  newObjectId?: string;
}

/** Payload de push Git */
export interface GitPushPayload {
  refUpdates: GitRefUpdate[];
  commits: GitCommitPayload[];
}

/** Resultado de push Git */
export interface GitPushResult {
  pushId: number;
  date: string;
  url: string;
  refUpdates: GitRefUpdate[];
  commits: Array<{
    commitId: string;
    comment: string;
    url: string;
  }>;
  pushedBy: IdentityRef;
}

// ═══════════════════════════════════════════════════════════════════════════
// Pipelines & Builds (Fase 6: Repositório & CI/CD)
// ═══════════════════════════════════════════════════════════════════════════

/** Pipeline Definition */
export interface PipelineDefinition {
  id: number;
  name: string;
  folder?: string;
  url: string;
  revision?: number;
  _links?: Record<string, { href: string }>;
  configuration?: {
    type: 'yaml';
    path: string;
    repository: {
      id: string;
      type: string;
    };
  };
}

/** Pipeline Run */
export interface PipelineRun {
  id: number;
  name: string;
  state: 'unknown' | 'inProgress' | 'canceling' | 'completed';
  result?: 'unknown' | 'succeeded' | 'failed' | 'canceled';
  createdDate: string;
  finishedDate?: string;
  url: string;
  pipeline: { id: number; name: string };
  _links?: Record<string, { href: string }>;
}

/** Build (representação da Build API) */
export interface Build {
  id: number;
  buildNumber: string;
  status: 'all' | 'cancelling' | 'completed' | 'inProgress' | 'none' | 'notStarted' | 'postponed';
  result?: 'canceled' | 'failed' | 'none' | 'partiallySucceeded' | 'succeeded';
  sourceBranch: string;
  sourceVersion: string;
  definition: { id: number; name: string };
  project: { id: string; name: string };
  startTime?: string;
  finishTime?: string;
  url: string;
  _links?: Record<string, { href: string }>;
}

/** Build Log */
export interface BuildLog {
  id: number;
  type: string;
  url: string;
  lineCount?: number;
}

/** Test Run associado a um Build */
export interface BuildTestRun {
  id: number;
  name: string;
  state: string;
  totalTests: number;
  passedTests: number;
  incompleteTests: number;
  unanalyzedTests: number;
  notApplicableTests: number;
  url: string;
  webAccessUrl?: string;
  buildConfiguration?: { id: number; number: string };
}

// ═══════════════════════════════════════════════════════════════════════════
// Parâmetros de Comando — Repositório & CI/CD
// ═══════════════════════════════════════════════════════════════════════════

/** Parâmetros para push de código de automação */
export interface PushAutomationParams {
  repositoryName: string;
  branchName: string;
  commitMessage: string;
  platform: 'web' | 'api' | 'mobile';
  basePath?: string;
  targetPath?: string;
  createBranch?: boolean;
  sourceBranch?: string;
  includeShared?: boolean;
}

/** Parâmetros para geração de pipeline YAML */
export interface GeneratePipelineYamlParams {
  framework: string;
  language: string;
  platform: 'web' | 'api' | 'mobile';
  repositoryName?: string;
  branchName?: string;
  triggerBranch?: string;
  testDirectory?: string;
  outputPath?: string;
  includeTestResults?: boolean;
  includeTestPlanSync?: boolean;
  testPlanId?: number;
  testSuiteId?: number;
}

/** Parâmetros para sincronização de resultados de pipeline */
export interface SyncPipelineResultsParams {
  buildId: number;
  testPlanId: number;
  testSuiteId: number;
  mapTestCaseByName?: boolean;
  comment?: string;
  createBugOnFailure?: boolean;
  bugSeverity?: '1 - Critical' | '2 - High' | '3 - Medium' | '4 - Low';
}

/** Resultado do push de automação */
export interface PushAutomationResult {
  pushId: number;
  commitId: string;
  commitUrl: string;
  repositoryName: string;
  branchName: string;
  filesCount: number;
  totalSize: number;
  files: Array<{
    path: string;
    size: number;
    changeType: 'add' | 'edit';
  }>;
}

/** Resultado da sincronização de pipeline */
export interface SyncPipelineResult {
  buildId: number;
  buildStatus: string;
  buildResult: string;
  totalTests: number;
  passedTests: number;
  failedTests: number;
  otherTests: number;
  testRunsUpdated: number;
  testRunsCreated: number;
  bugsCreated: number;
  details: Array<{
    testCaseId?: number;
    testCaseName: string;
    outcome: TestOutcome;
    duration?: number;
    errorMessage?: string;
    testRunId?: number;
    bugId?: number;
  }>;
}

/** Mapeamento de framework para configuração de pipeline */
export interface PipelineFrameworkConfig {
  framework: string;
  language: string;
  nodeVersion?: string;
  pythonVersion?: string;
  javaVersion?: string;
  dotnetVersion?: string;
  installCommand: string;
  testCommand: string;
  testResultsFormat: 'JUnit' | 'NUnit' | 'VSTest' | 'XUnit' | 'CTest';
  testResultsFiles: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Criação de Repositório (Comando 18)
// ═══════════════════════════════════════════════════════════════════════════

/** Referência a um projeto Azure DevOps */
export interface AzureDevOpsProject {
  id: string;
  name: string;
  description?: string;
  url: string;
  state: string;
  visibility?: string;
}

/** Parâmetros para criação de repositório */
export interface CreateRepoParams {
  /** Nome do novo repositório */
  repoName: string;
  /** Projeto de destino (padrão: projeto configurado no .env) */
  projectName?: string;
  /** Diretório fonte da automação (caminho local) */
  automationDir: string;
  /** Descrição opcional do repositório */
  description?: string;
  /** Nome da branch padrão (padrão: 'main') */
  defaultBranch?: string;
  /** Incluir pasta shared/ do automated_test */
  includeShared?: boolean;
  /** Gerar .gitignore adequado ao framework */
  generateGitignore?: boolean;
  /** Prefixo do caminho de destino dentro do repositório */
  targetPath?: string;
  /** Modo dry-run: lista arquivos sem criar */
  dryRun?: boolean;
}

/** Resultado da criação de repositório */
export interface CreateRepoResult {
  /** Repositório criado */
  repository: GitRepository;
  /** ID do push inicial */
  pushId: number;
  /** ID do commit inicial */
  commitId: string;
  /** URL do commit */
  commitUrl: string;
  /** Quantidade de arquivos enviados */
  filesCount: number;
  /** Tamanho total em bytes */
  totalSize: number;
  /** URL web do repositório */
  repoUrl: string;
  /** URL para clone HTTPS */
  cloneUrl: string;
  /** Lista de arquivos incluídos */
  files: Array<{
    path: string;
    size: number;
  }>;
}

// ═══════════════════════════════════════════════════════════════════════════
// Test Plan CRUD (Fase 7: Fluxo Completo CI/CD)
// ═══════════════════════════════════════════════════════════════════════════

/** Parâmetros para criação de Test Plan */
export interface CreateTestPlanParams {
  name: string;
  areaPath?: string;
  iteration?: string;
  startDate?: string;
  endDate?: string;
  description?: string;
}

/** Parâmetros para atualização de Test Plan */
export interface UpdateTestPlanParams {
  name?: string;
  areaPath?: string;
  iteration?: string;
  startDate?: string;
  endDate?: string;
  state?: 'Active' | 'Inactive';
  description?: string;
}

/** Parâmetros para criação de Test Suite */
export interface CreateTestSuiteParams {
  name: string;
  parentSuiteId: number;
  suiteType: 'StaticTestSuite' | 'DynamicTestSuite' | 'RequirementTestSuite';
  requirementId?: number;
  queryString?: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Pipeline Definitions & Runs (Fase 7: Fluxo Completo CI/CD)
// ═══════════════════════════════════════════════════════════════════════════

/** Parâmetros para criação de Pipeline Definition */
export interface CreatePipelineDefinitionParams {
  name: string;
  repoId: string;
  yamlPath: string;
  folder?: string;
  branchName?: string;
}

/** Parâmetros para execução de Pipeline */
export interface RunPipelineParams {
  branchName?: string;
  variables?: Record<string, { value: string; isSecret?: boolean }>;
}

/** Parâmetros para monitoramento de Pipeline */
export interface MonitorPipelineParams {
  buildId: number;
  pollingIntervalMs?: number;
  timeoutMs?: number;
}

/** Build Definition (representação da definição de build/pipeline) */
export interface BuildDefinition {
  id: number;
  name: string;
  path: string;
  url: string;
  project: { id: string; name: string };
  repository?: { id: string; type: string; name: string; defaultBranch?: string };
  process?: { type: number; yamlFilename?: string };
  _links?: Record<string, { href: string }>;
}

// ═══════════════════════════════════════════════════════════════════════════
// Variable Groups (Fase 7: Fluxo Completo CI/CD)
// ═══════════════════════════════════════════════════════════════════════════

/** Variável de pipeline */
export interface PipelineVariable {
  value: string;
  isSecret?: boolean;
}

/** Grupo de variáveis */
export interface VariableGroup {
  id: number;
  name: string;
  description?: string;
  variables: Record<string, PipelineVariable>;
  createdBy?: IdentityRef;
  modifiedBy?: IdentityRef;
  type?: string;
}

/** Parâmetros para criação de Variable Group */
export interface CreateVariableGroupParams {
  name: string;
  description?: string;
  variables: Record<string, PipelineVariable>;
}

/** Parâmetros para atualização de Variable Group */
export interface UpdateVariableGroupParams {
  name?: string;
  description?: string;
  variables?: Record<string, PipelineVariable>;
}

// ═══════════════════════════════════════════════════════════════════════════
// Pull Requests (Regression Analysis)
// ═══════════════════════════════════════════════════════════════════════════

/** Pull Request do Azure DevOps */
export interface PullRequest {
  pullRequestId: number;
  title: string;
  description?: string;
  sourceRefName: string;
  targetRefName: string;
  status: 'active' | 'abandoned' | 'completed' | 'notSet' | 'all';
  createdBy: IdentityRef;
  creationDate: string;
  closedDate?: string;
  mergeStatus?: string;
  isDraft?: boolean;
  url: string;
  _links?: Record<string, { href: string }>;
}

/** Iteração de um Pull Request */
export interface PullRequestIteration {
  id: number;
  createdDate: string;
  updatedDate: string;
  sourceRefCommit: { commitId: string };
  targetRefCommit: { commitId: string };
  description?: string;
}

/** Entrada de alteração em um Pull Request */
export interface PullRequestChangeEntry {
  changeType: 'add' | 'edit' | 'delete' | 'rename';
  item: { path: string };
}

/** Referência de Work Item associado a um Pull Request */
export interface PullRequestWorkItemRef {
  id: string;
  url: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// WIQL & Work Item Batch (Fallback para MCP)
// ═══════════════════════════════════════════════════════════════════════════

/** Resultado de query WIQL */
export interface WiqlQueryResult {
  queryType: string;
  queryResultType: string;
  asOf: string;
  columns: Array<{ referenceName: string; name: string; url: string }>;
  workItems: Array<{ id: number; url: string }>;
}
