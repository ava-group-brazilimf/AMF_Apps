/**
 * ============================================================================
 * FastQA — Azure DevOps TypeScript API Client
 * ============================================================================
 * Client centralizado para todas as operações REST com Azure DevOps via
 * fetch nativo do Node.js. Implementa retry com exponential backoff,
 * logging estruturado e tratamento de erros.
 *
 * Uso:
 *   const client = new AzureDevOpsClient();
 *   const workItem = await client.getWorkItem(123);
 *
 * ============================================================================
 */

import * as fs from 'fs';
import * as path from 'path';
import { config, buildApiUrl, buildTestPlanApiUrl, buildTestRunApiUrl, buildGitApiUrl, buildGitApiUrlForProject, buildCoreApiUrl, buildBuildApiUrl, buildPipelinesApiUrl, buildDistributedTaskApiUrl, buildPipelinePermissionsApiUrl, LINK_TYPES } from './azure-devops.config';
import { Logger } from './utils/logger.util';
import { fileToBase64, getFileSizeBytes } from './utils/base64.util';
import type {
  WorkItem,
  JsonPatchOperation,
  WorkItemType,
  AttachmentUploadResponse,
  TestResultAttachmentPayload,
  TestPlan,
  TestSuite,
  SuiteTestCase,
  TestPoint,
  TestPointsResponse,
  CreateTestRunPayload,
  TestRun,
  TestResult,
  TestOutcome,
  UpdateTestResultPayload,
  TestCaseStep,
  PaginatedResponse,
  GitRepository,
  GitRef,
  GitPushPayload,
  GitPushResult,
  Build,
  BuildTestRun,
  AzureDevOpsProject,
  CreateTestPlanParams,
  UpdateTestPlanParams,
  CreateTestSuiteParams,
  CreatePipelineDefinitionParams,
  RunPipelineParams,
  PipelineRun,
  BuildDefinition,
  CreateVariableGroupParams,
  UpdateVariableGroupParams,
  VariableGroup,
  WiqlQueryResult,
  PipelineDefinition,
  PullRequest,
  PullRequestIteration,
  PullRequestChangeEntry,
  PullRequestWorkItemRef,
} from './types/azure-devops.types';

// ═══════════════════════════════════════════════════════════════════════════
// Client Principal
// ═══════════════════════════════════════════════════════════════════════════

export class AzureDevOpsClient {
  private logger: Logger;

  constructor(logPrefix?: string) {
    this.logger = new Logger(logPrefix || 'AzureDevOpsClient');
  }

  // ─────────────────────────────────────────────────────────────────────
  // HTTP com Retry
  // ─────────────────────────────────────────────────────────────────────

  /** Executa request com retry e exponential backoff */
  private async requestWithRetry<T>(
    method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE',
    url: string,
    options?: {
      body?: string;
      headers?: Record<string, string>;
    }
  ): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= config.maxRetries; attempt++) {
      try {
        this.logger.debug(`[${method}] ${url} (tentativa ${attempt}/${config.maxRetries})`);

        const headers: Record<string, string> = {
          'Authorization': config.authHeader,
          'Content-Type': 'application/json-patch+json',
          'Accept': 'application/json',
          ...options?.headers,
        };

        const requestInit: RequestInit = {
          method,
          headers,
        };

        if (options?.body) {
          requestInit.body = options.body;
        }

        const response = await fetch(url, requestInit);
        const status = response.status;

        if (status >= 200 && status < 300) {
          const text = await response.text();
          if (!text || text.trim() === '') return {} as T;
          return JSON.parse(text) as T;
        }

        // Erros que NÃO devem ter retry
        if (status === 400 || status === 401 || status === 403 || status === 404 || status === 409) {
          const body = await response.text();
          const errorMsg = this.parseErrorMessage(body, status);
          throw new Error(errorMsg);
        }

        // Erros com retry (429, 5xx)
        const body = await response.text();
        lastError = new Error(`HTTP ${status}: ${this.parseErrorMessage(body, status)}`);
        this.logger.warn(`Tentativa ${attempt} falhou: ${lastError.message}`);

      } catch (error) {
        if (error instanceof Error && !error.message.startsWith('HTTP ')) {
          // Erro de lógica/validação — não fazer retry
          throw error;
        }
        lastError = error instanceof Error ? error : new Error(String(error));
        this.logger.warn(`Tentativa ${attempt} falhou: ${lastError.message}`);
      }

      // Esperar antes do retry (exponential backoff)
      if (attempt < config.maxRetries) {
        const delay = config.retryBaseDelay * Math.pow(2, attempt - 1);
        this.logger.info(`Aguardando ${delay}ms antes da próxima tentativa...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw lastError || new Error('Todas as tentativas falharam');
  }

  /** Extrai mensagem legível de erro da resposta */
  private parseErrorMessage(body: string, statusCode: number): string {
    try {
      const json = JSON.parse(body);
      const message = json.message || json.value?.Message || json.innerException?.message || body;
      return `[${statusCode}] ${message}`;
    } catch {
      return `[${statusCode}] ${body.substring(0, 500)}`;
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Work Items
  // ═══════════════════════════════════════════════════════════════════════

  /** Obter work item por ID com expansão opcional */
  async getWorkItem(
    id: number,
    expand: 'all' | 'relations' | 'fields' | 'none' = 'all'
  ): Promise<WorkItem> {
    const url = buildApiUrl(`wit/workitems/${id}`, { '$expand': expand });
    this.logger.info(`Obtendo work item #${id}...`);
    const result = await this.requestWithRetry<WorkItem>('GET', url);
    this.logger.success(`Work item #${id} obtido: "${result.fields?.['System.Title']}"`);
    return result;
  }

  /** Criar work item de qualquer tipo */
  async createWorkItem(
    type: WorkItemType,
    operations: JsonPatchOperation[]
  ): Promise<WorkItem> {
    const encodedType = encodeURIComponent(type);
    const url = buildApiUrl(`wit/workitems/$${encodedType}`);
    this.logger.info(`Criando work item do tipo "${type}"...`);

    const result = await this.requestWithRetry<WorkItem>('POST', url, {
      body: JSON.stringify(operations),
      headers: { 'Content-Type': 'application/json-patch+json' },
    });

    this.logger.success(`Work item #${result.id} criado: "${result.fields?.['System.Title']}"`);
    return result;
  }

  /** Atualizar work item existente */
  async updateWorkItem(
    id: number,
    operations: JsonPatchOperation[]
  ): Promise<WorkItem> {
    const url = buildApiUrl(`wit/workitems/${id}`);
    this.logger.info(`Atualizando work item #${id}...`);

    const result = await this.requestWithRetry<WorkItem>('PATCH', url, {
      body: JSON.stringify(operations),
      headers: { 'Content-Type': 'application/json-patch+json' },
    });

    this.logger.success(`Work item #${id} atualizado`);
    return result;
  }

  /** Vincular dois work items */
  async linkWorkItems(
    sourceId: number,
    targetId: number,
    linkType: string,
    comment?: string
  ): Promise<WorkItem> {
    const refName = LINK_TYPES[linkType] || linkType;
    const targetUrl = `${config.orgUrl}/${encodeURIComponent(config.project)}/_apis/wit/workitems/${targetId}`;

    const operations: JsonPatchOperation[] = [
      {
        op: 'add',
        path: '/relations/-',
        value: {
          rel: refName,
          url: targetUrl,
          attributes: {
            ...(comment && { comment }),
          },
        },
      },
    ];

    this.logger.info(`Vinculando #${sourceId} → #${targetId} (${linkType})...`);
    const result = await this.updateWorkItem(sourceId, operations);
    this.logger.success(`Vínculo criado: #${sourceId} → #${targetId} (${refName})`);
    return result;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Attachments
  // ═══════════════════════════════════════════════════════════════════════

  /** Upload de arquivo como attachment genérico */
  async uploadAttachment(
    filePath: string,
    fileName?: string
  ): Promise<AttachmentUploadResponse> {
    const resolvedPath = path.resolve(filePath);
    if (!fs.existsSync(resolvedPath)) {
      throw new Error(`Arquivo não encontrado: ${resolvedPath}`);
    }

    const size = getFileSizeBytes(resolvedPath);
    if (size > config.maxFileSize) {
      throw new Error(
        `Arquivo excede limite de ${config.maxFileSize / (1024 * 1024)} MB: ` +
        `${(size / (1024 * 1024)).toFixed(2)} MB`
      );
    }

    const name = fileName || path.basename(resolvedPath);
    const fileBuffer = fs.readFileSync(resolvedPath);
    const url = buildApiUrl('wit/attachments', { fileName: name });

    this.logger.info(`Uploading attachment: ${name} (${(size / 1024).toFixed(1)} KB)...`);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/octet-stream',
        'Authorization': config.authHeader,
      },
      body: fileBuffer,
    });

    if (response.status < 200 || response.status >= 300) {
      const body = await response.text();
      throw new Error(`Upload falhou: ${this.parseErrorMessage(body, response.status)}`);
    }

    const result = (await response.json()) as AttachmentUploadResponse;
    this.logger.success(`Attachment uploaded: ${result.url}`);
    return result;
  }

  /** Vincular attachment a um work item */
  async attachToWorkItem(
    workItemId: number,
    attachmentUrl: string,
    comment?: string
  ): Promise<WorkItem> {
    const operations: JsonPatchOperation[] = [
      {
        op: 'add',
        path: '/relations/-',
        value: {
          rel: 'AttachedFile',
          url: attachmentUrl,
          attributes: { comment: comment || 'Evidência FastQA' },
        },
      },
    ];

    return this.updateWorkItem(workItemId, operations);
  }

  /** Adiciona comentário no Work Item via System.History (PATCH — compatível com todas as versões da API) */
  async addWorkItemDiscussionComment(
    workItemId: number,
    comment: string
  ): Promise<any> {
    const trimmedComment = comment.trim();
    if (!trimmedComment) {
      throw new Error('Comentário não pode ser vazio');
    }

    this.logger.info(`Adicionando comentário no Work Item #${workItemId}...`);

    const operations: JsonPatchOperation[] = [
      {
        op: 'add',
        path: '/fields/System.History',
        value: trimmedComment,
      },
    ];

    return this.updateWorkItem(workItemId, operations);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Test Plans & Suites
  // ═══════════════════════════════════════════════════════════════════════

  /** Listar todos os Test Plans do projeto */
  async getTestPlans(): Promise<PaginatedResponse<TestPlan>> {
    const url = buildTestPlanApiUrl('plans');
    this.logger.info('Listando Test Plans...');
    const result = await this.requestWithRetry<PaginatedResponse<TestPlan>>('GET', url);
    this.logger.success(`${result.value.length} Test Plans encontrados`);
    return result;
  }

  /** Listar Test Suites de um Test Plan */
  async getTestSuites(planId: number): Promise<PaginatedResponse<TestSuite>> {
    const url = buildTestPlanApiUrl(`Plans/${planId}/suites`);
    this.logger.info(`Listando Test Suites do Plan #${planId}...`);
    const result = await this.requestWithRetry<PaginatedResponse<TestSuite>>('GET', url);
    this.logger.success(`${result.value.length} Test Suites encontradas`);
    return result;
  }

  /** Listar Test Cases de uma Suite */
  async getTestCases(
    planId: number,
    suiteId: number
  ): Promise<PaginatedResponse<SuiteTestCase>> {
    const url = buildTestPlanApiUrl(`Plans/${planId}/Suites/${suiteId}/TestCase`);
    this.logger.info(`Listando Test Cases da Suite #${suiteId}...`);
    const result = await this.requestWithRetry<PaginatedResponse<SuiteTestCase>>('GET', url);
    this.logger.success(`${result.value.length} Test Cases encontrados`);
    return result;
  }

  /** Adicionar Test Cases a uma Suite */
  async addTestCaseToSuite(
    planId: number,
    suiteId: number,
    testCaseIds: number[]
  ): Promise<PaginatedResponse<SuiteTestCase>> {
    const body = testCaseIds.map(id => ({ workItem: { id } }));
    const url = buildTestPlanApiUrl(`Plans/${planId}/Suites/${suiteId}/TestCase`);

    this.logger.info(`Adicionando ${testCaseIds.length} Test Cases à Suite #${suiteId}...`);
    const result = await this.requestWithRetry<PaginatedResponse<SuiteTestCase>>('POST', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
    this.logger.success(`Test Cases adicionados à Suite #${suiteId}`);
    return result;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Test Points
  // ═══════════════════════════════════════════════════════════════════════

  /** Obter Test Points (necessário para criar Test Run) */
  async getTestPoints(
    planId: number,
    suiteId: number,
    testCaseId?: number
  ): Promise<TestPointsResponse> {
    const queryParams: Record<string, string | number> = {};
    if (testCaseId) {
      queryParams['testCaseId'] = testCaseId;
    }

    const url = buildTestPlanApiUrl(
      `Plans/${planId}/Suites/${suiteId}/TestPoint`,
      queryParams
    );

    this.logger.info(
      `Obtendo Test Points (Plan: ${planId}, Suite: ${suiteId}` +
      `${testCaseId ? `, TC: ${testCaseId}` : ''})...`
    );

    const result = await this.requestWithRetry<TestPointsResponse>('GET', url);

    if (!result.value || result.value.length === 0) {
      throw new Error(
        `Nenhum Test Point encontrado para Plan ${planId}, Suite ${suiteId}` +
        `${testCaseId ? `, Test Case ${testCaseId}` : ''}. ` +
        `Verifique se o Test Case está associado à Suite.`
      );
    }

    this.logger.success(`${result.value.length} Test Points encontrados`);
    return result;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Test Runs
  // ═══════════════════════════════════════════════════════════════════════

  /** Criar Test Run */
  async createTestRun(
    planId: number,
    pointIds: number[],
    name?: string
  ): Promise<TestRun> {
    const payload: CreateTestRunPayload = {
      name: name || `FastQA Run - ${new Date().toISOString()}`,
      plan: { id: planId },
      pointIds,
      automated: false,
    };

    const url = buildTestRunApiUrl('runs');
    this.logger.info(`Criando Test Run para Plan #${planId}...`);

    const result = await this.requestWithRetry<TestRun>('POST', url, {
      body: JSON.stringify(payload),
      headers: { 'Content-Type': 'application/json' },
    });

    this.logger.success(`Test Run #${result.id} criado: "${result.name}"`);
    return result;
  }

  /** Obter Test Results de um Run */
  async getTestResults(runId: number): Promise<PaginatedResponse<TestResult>> {
    const url = buildTestRunApiUrl(`runs/${runId}/results`);
    this.logger.info(`Obtendo resultados do Test Run #${runId}...`);
    const result = await this.requestWithRetry<PaginatedResponse<TestResult>>('GET', url);
    this.logger.success(`${result.value.length} resultados encontrados`);
    return result;
  }

  /** Upload de attachment no Test Result (Base64) */
  async uploadTestResultAttachment(
    runId: number,
    resultId: number,
    filePath: string,
    comment?: string
  ): Promise<AttachmentUploadResponse> {
    const resolvedPath = path.resolve(filePath);
    if (!fs.existsSync(resolvedPath)) {
      throw new Error(`Arquivo não encontrado: ${resolvedPath}`);
    }

    const size = getFileSizeBytes(resolvedPath);
    if (size > config.maxFileSize) {
      throw new Error(
        `Arquivo excede limite de ${config.maxFileSize / (1024 * 1024)} MB: ` +
        `${(size / (1024 * 1024)).toFixed(2)} MB`
      );
    }

    const fileName = path.basename(resolvedPath);
    const base64Content = fileToBase64(resolvedPath);

    const payload: TestResultAttachmentPayload = {
      stream: base64Content,
      fileName,
      comment: comment || `Evidência FastQA — ${fileName}`,
      attachmentType: 'GeneralAttachment',
    };

    const url = buildTestRunApiUrl(
      `runs/${runId}/results/${resultId}/attachments`
    );

    this.logger.info(`Uploading evidência ao Result #${resultId}: ${fileName} (${(size / 1024).toFixed(1)} KB)...`);

    const result = await this.requestWithRetry<AttachmentUploadResponse>('POST', url, {
      body: JSON.stringify(payload),
      headers: { 'Content-Type': 'application/json' },
    });

    this.logger.success(`Evidência uploaded: ${result.url}`);
    return result;
  }

  /** Atualizar outcome de Test Results */
  async updateTestResults(
    runId: number,
    updates: UpdateTestResultPayload[]
  ): Promise<TestResult[]> {
    const url = buildTestRunApiUrl(`runs/${runId}/results`);
    this.logger.info(`Atualizando ${updates.length} resultados no Run #${runId}...`);

    const result = await this.requestWithRetry<PaginatedResponse<TestResult>>('PATCH', url, {
      body: JSON.stringify(updates),
      headers: { 'Content-Type': 'application/json' },
    });

    this.logger.success(`Resultados atualizados no Run #${runId}`);
    return result.value || [];
  }

  /** Finalizar Test Run (status Completed) */
  async completeTestRun(runId: number, comment?: string): Promise<TestRun> {
    const url = buildTestRunApiUrl(`runs/${runId}`);
    this.logger.info(`Finalizando Test Run #${runId}...`);

    const payload: Record<string, unknown> = {
      state: 'Completed',
    };
    if (comment) payload.comment = comment;

    const result = await this.requestWithRetry<TestRun>('PATCH', url, {
      body: JSON.stringify(payload),
      headers: { 'Content-Type': 'application/json' },
    });

    this.logger.success(`Test Run #${runId} finalizado`);
    return result;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Git Repositories (Fase 6: Repositório & CI/CD)
  // ═══════════════════════════════════════════════════════════════════════

  /** Lista todos os repositórios Git do projeto */
  async getRepositories(): Promise<PaginatedResponse<GitRepository>> {
    const url = buildGitApiUrl('repositories');
    this.logger.info('Listando repositórios Git...');
    return this.requestWithRetry<PaginatedResponse<GitRepository>>('GET', url);
  }

  /** Obtém repositório Git por nome ou ID */
  async getRepository(nameOrId: string): Promise<GitRepository> {
    const url = buildGitApiUrl(`repositories/${encodeURIComponent(nameOrId)}`);
    this.logger.info(`Obtendo repositório "${nameOrId}"...`);
    return this.requestWithRetry<GitRepository>('GET', url);
  }

  /** Lista branches (refs) de um repositório */
  async getBranches(repositoryId: string, filter?: string): Promise<PaginatedResponse<GitRef>> {
    const params: Record<string, string> = {};
    if (filter) params.filter = `heads/${filter}`;
    else params.filter = 'heads/';
    const url = buildGitApiUrl(`repositories/${repositoryId}/refs`, params);
    this.logger.info(`Listando branches do repo ${repositoryId}...`);
    return this.requestWithRetry<PaginatedResponse<GitRef>>('GET', url);
  }

  /** Obtém uma branch específica por nome */
  async getBranch(repositoryId: string, branchName: string): Promise<GitRef | null> {
    const cleanName = branchName.replace(/^refs\/heads\//, '');
    const refs = await this.getBranches(repositoryId, cleanName);
    const targetRef = `refs/heads/${cleanName}`;
    const found = refs.value?.find((r: GitRef) => r.name === targetRef);
    return found ?? null;
  }

  /** Cria um push Git (commits + ref updates) */
  async createGitPush(repositoryId: string, push: GitPushPayload): Promise<GitPushResult> {
    const url = buildGitApiUrl(`repositories/${repositoryId}/pushes`);
    this.logger.info(`Criando push no repo ${repositoryId}...`);
    return this.requestWithRetry<GitPushResult>('POST', url, {
      body: JSON.stringify(push),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /** Cria um push Git em um projeto específico (cross-project) */
  async createGitPushInProject(projectName: string, repositoryId: string, push: GitPushPayload): Promise<GitPushResult> {
    const url = buildGitApiUrlForProject(projectName, `repositories/${repositoryId}/pushes`);
    this.logger.info(`Criando push no repo ${repositoryId} do projeto "${projectName}"...`);
    return this.requestWithRetry<GitPushResult>('POST', url, {
      body: JSON.stringify(push),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /** Obtém informações de um projeto Azure DevOps por nome */
  async getProject(projectName: string): Promise<AzureDevOpsProject> {
    const url = buildCoreApiUrl(`projects/${encodeURIComponent(projectName)}`);
    this.logger.info(`Obtendo projeto "${projectName}"...`);
    return this.requestWithRetry<AzureDevOpsProject>('GET', url);
  }

  /** Cria um novo repositório Git em um projeto Azure DevOps */
  async createRepository(repoName: string, projectId: string, projectName?: string): Promise<GitRepository> {
    const targetProject = projectName ?? config.project;
    const url = buildGitApiUrlForProject(targetProject, 'repositories');
    this.logger.info(`Criando repositório "${repoName}" no projeto "${targetProject}"...`);
    return this.requestWithRetry<GitRepository>('POST', url, {
      body: JSON.stringify({
        name: repoName,
        project: { id: projectId },
      }),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Pull Requests (Regression Analysis)
  // ═══════════════════════════════════════════════════════════════════════

  /** Obtém um Pull Request por ID */
  async getPullRequest(repoNameOrId: string, prId: number): Promise<PullRequest> {
    const url = buildGitApiUrl(`repositories/${encodeURIComponent(repoNameOrId)}/pullrequests/${prId}`);
    this.logger.info(`Obtendo PR #${prId} do repositório "${repoNameOrId}"...`);
    const result = await this.requestWithRetry<PullRequest>('GET', url);
    this.logger.success(`PR #${prId} obtido: "${result.title}"`);
    return result;
  }

  /** Lista iterações de um Pull Request */
  async getPullRequestIterations(repoNameOrId: string, prId: number): Promise<PullRequestIteration[]> {
    const url = buildGitApiUrl(`repositories/${encodeURIComponent(repoNameOrId)}/pullrequests/${prId}/iterations`);
    this.logger.info(`Obtendo iterações do PR #${prId}...`);
    const result = await this.requestWithRetry<PaginatedResponse<PullRequestIteration>>('GET', url);
    return result.value || [];
  }

  /** Obtém alterações de uma iteração do Pull Request */
  async getPullRequestChanges(repoNameOrId: string, prId: number, iterationId?: number): Promise<PullRequestChangeEntry[]> {
    const path = iterationId
      ? `repositories/${encodeURIComponent(repoNameOrId)}/pullrequests/${prId}/iterations/${iterationId}/changes`
      : `repositories/${encodeURIComponent(repoNameOrId)}/pullrequests/${prId}/iterations/1/changes`;
    const url = buildGitApiUrl(path);
    this.logger.info(`Obtendo alterações do PR #${prId}${iterationId ? ` (iteração ${iterationId})` : ''}...`);
    const result = await this.requestWithRetry<{ changeEntries: PullRequestChangeEntry[] }>('GET', url);
    return result.changeEntries || [];
  }

  /** Obtém Work Items associados a um Pull Request */
  async getPullRequestWorkItems(repoNameOrId: string, prId: number): Promise<PullRequestWorkItemRef[]> {
    const url = buildGitApiUrl(`repositories/${encodeURIComponent(repoNameOrId)}/pullrequests/${prId}/workitems`);
    this.logger.info(`Obtendo Work Items do PR #${prId}...`);
    const result = await this.requestWithRetry<PaginatedResponse<PullRequestWorkItemRef>>('GET', url);
    return result.value || [];
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Build & Pipelines (Fase 6: Repositório & CI/CD)
  // ═══════════════════════════════════════════════════════════════════════

  /** Obtém informações de um build */
  async getBuild(buildId: number): Promise<Build> {
    const url = buildBuildApiUrl(`builds/${buildId}`);
    this.logger.info(`Obtendo Build #${buildId}...`);
    return this.requestWithRetry<Build>('GET', url);
  }

  /** Lista builds com filtros opcionais */
  async getBuilds(params?: {
    definitions?: number;
    statusFilter?: string;
    resultFilter?: string;
    top?: number;
    branchName?: string;
  }): Promise<PaginatedResponse<Build>> {
    const queryParams: Record<string, string | number | boolean> = {};
    if (params?.definitions) queryParams.definitions = params.definitions;
    if (params?.statusFilter) queryParams.statusFilter = params.statusFilter;
    if (params?.resultFilter) queryParams.resultFilter = params.resultFilter;
    if (params?.top) queryParams['$top'] = params.top;
    if (params?.branchName) queryParams.branchName = params.branchName;
    const url = buildBuildApiUrl('builds', queryParams);
    this.logger.info('Listando builds...');
    return this.requestWithRetry<PaginatedResponse<Build>>('GET', url);
  }

  /** Obtém test runs associados a um build */
  async getTestRunsByBuild(buildUri: string): Promise<PaginatedResponse<BuildTestRun>> {
    const url = buildTestRunApiUrl('runs', { buildUri });
    this.logger.info(`Obtendo Test Runs do build "${buildUri}"...`);
    return this.requestWithRetry<PaginatedResponse<BuildTestRun>>('GET', url);
  }

  /** Obtém logs de um build */
  async getBuildLogs(buildId: number): Promise<PaginatedResponse<{ id: number; type: string; url: string }>> {
    const url = buildBuildApiUrl(`builds/${buildId}/logs`);
    this.logger.info(`Obtendo logs do Build #${buildId}...`);
    return this.requestWithRetry<PaginatedResponse<{ id: number; type: string; url: string }>>('GET', url);
  }

  /** Obtém conteúdo de um log específico */
  async getBuildLogContent(buildId: number, logId: number): Promise<string> {
    const url = buildBuildApiUrl(`builds/${buildId}/logs/${logId}`);
    this.logger.info(`Obtendo conteúdo do log #${logId} do Build #${buildId}...`);

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Authorization: config.authHeader,
        Accept: 'text/plain',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.text();
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Test Plan CRUD (Fase 7: Fluxo Completo CI/CD)
  // ═══════════════════════════════════════════════════════════════════════

  /** Obtém um Test Plan por ID */
  async getTestPlan(planId: number): Promise<TestPlan> {
    const url = buildTestPlanApiUrl(`plans/${planId}`);
    this.logger.info(`Obtendo Test Plan #${planId}...`);
    return this.requestWithRetry<TestPlan>('GET', url);
  }

  /** Cria um novo Test Plan */
  async createTestPlan(params: CreateTestPlanParams): Promise<TestPlan> {
    const url = buildTestPlanApiUrl('plans');
    this.logger.info(`Criando Test Plan "${params.name}"...`);
    const body: Record<string, unknown> = { name: params.name };
    if (params.areaPath) body.areaPath = params.areaPath;
    if (params.iteration) body.iteration = params.iteration;
    if (params.startDate) body.startDate = params.startDate;
    if (params.endDate) body.endDate = params.endDate;
    if (params.description) body.description = params.description;
    return this.requestWithRetry<TestPlan>('POST', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /** Atualiza um Test Plan existente */
  async updateTestPlan(planId: number, params: UpdateTestPlanParams): Promise<TestPlan> {
    const url = buildTestPlanApiUrl(`plans/${planId}`);
    this.logger.info(`Atualizando Test Plan #${planId}...`);
    const body: Record<string, unknown> = {};
    if (params.name) body.name = params.name;
    if (params.areaPath) body.areaPath = params.areaPath;
    if (params.iteration) body.iteration = params.iteration;
    if (params.startDate) body.startDate = params.startDate;
    if (params.endDate) body.endDate = params.endDate;
    if (params.state) body.state = params.state;
    if (params.description) body.description = params.description;
    return this.requestWithRetry<TestPlan>('PATCH', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /** Cria uma Test Suite dentro de um Test Plan */
  async createTestSuite(planId: number, params: CreateTestSuiteParams): Promise<TestSuite> {
    const url = buildTestPlanApiUrl(`Plans/${planId}/suites`);
    this.logger.info(`Criando Test Suite "${params.name}" no Plan #${planId}...`);
    const body: Record<string, unknown> = {
      name: params.name,
      suiteType: params.suiteType,
      parentSuite: { id: params.parentSuiteId },
    };
    if (params.requirementId) body.requirementId = params.requirementId;
    if (params.queryString) body.queryString = params.queryString;
    return this.requestWithRetry<TestSuite>('POST', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // WIQL & Work Item Batch (Fallback para MCP)
  // ═══════════════════════════════════════════════════════════════════════

  /** Executa uma query WIQL */
  async searchWorkItems(wiql: string): Promise<WiqlQueryResult> {
    const url = buildApiUrl('wit/wiql');
    this.logger.info('Executando query WIQL...');
    return this.requestWithRetry<WiqlQueryResult>('POST', url, {
      body: JSON.stringify({ query: wiql }),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /** Busca work items em lote por IDs */
  async getWorkItemsBatch(ids: number[], fields?: string[]): Promise<WorkItem[]> {
    const url = buildApiUrl('wit/workitemsbatch');
    this.logger.info(`Buscando ${ids.length} work items em lote...`);
    const body: Record<string, unknown> = { ids };
    if (fields?.length) body.fields = fields;
    const result = await this.requestWithRetry<{ value: WorkItem[]; count: number }>('POST', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
    return result.value;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Pipeline Definitions & Runs (Fase 7: Fluxo Completo CI/CD)
  // ═══════════════════════════════════════════════════════════════════════

  /** Cria uma definição de pipeline (build definition) apontando para um YAML no repositório */
  async createPipelineDefinition(params: CreatePipelineDefinitionParams): Promise<BuildDefinition> {
    const url = buildBuildApiUrl('definitions');
    this.logger.info(`Criando pipeline "${params.name}" apontando para "${params.yamlPath}"...`);
    const body = {
      name: params.name,
      type: 'build',
      quality: 'definition',
      path: params.folder || '\\',
      process: {
        type: 2,
        yamlFilename: params.yamlPath,
      },
      repository: {
        id: params.repoId,
        type: 'TfsGit',
        defaultBranch: `refs/heads/${params.branchName || 'main'}`,
      },
      triggers: [],
    };
    return this.requestWithRetry<BuildDefinition>('POST', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /** Lista definições de pipeline com filtro opcional por nome */
  async getPipelineDefinitions(name?: string): Promise<PaginatedResponse<BuildDefinition>> {
    const queryParams: Record<string, string | number | boolean> = {};
    if (name) queryParams.name = name;
    const url = buildBuildApiUrl('definitions', queryParams);
    this.logger.info('Listando pipeline definitions...');
    return this.requestWithRetry<PaginatedResponse<BuildDefinition>>('GET', url);
  }

  /** Dispara execução de pipeline via Pipelines API */
  async runPipeline(pipelineId: number, params?: RunPipelineParams): Promise<PipelineRun> {
    const url = buildPipelinesApiUrl(`${pipelineId}/runs`);
    this.logger.info(`Disparando Pipeline #${pipelineId}...`);
    const body: Record<string, unknown> = {};
    if (params?.branchName) {
      body.resources = {
        repositories: {
          self: { refName: `refs/heads/${params.branchName}` },
        },
      };
    }
    if (params?.variables) {
      body.variables = params.variables;
    }
    return this.requestWithRetry<PipelineRun>('POST', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /** Obtém o status de uma Pipeline Run */
  async getPipelineRun(pipelineId: number, runId: number): Promise<PipelineRun> {
    const url = buildPipelinesApiUrl(`${pipelineId}/runs/${runId}`);
    this.logger.info(`Obtendo Pipeline Run #${runId}...`);
    return this.requestWithRetry<PipelineRun>('GET', url);
  }

  /** Enfileira uma build (alternativa ao runPipeline via Build API) */
  async queueBuild(definitionId: number, sourceBranch?: string, variables?: Record<string, { value: string; isSecret?: boolean }>): Promise<Build> {
    const url = buildBuildApiUrl('builds');
    this.logger.info(`Enfileirando build para definition #${definitionId}...`);
    const body: Record<string, unknown> = {
      definition: { id: definitionId },
      reason: 'manual',
    };
    if (sourceBranch) body.sourceBranch = `refs/heads/${sourceBranch}`;
    if (variables) body.parameters = JSON.stringify(variables);
    return this.requestWithRetry<Build>('POST', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Variable Groups (Fase 7: Fluxo Completo CI/CD)
  // ═══════════════════════════════════════════════════════════════════════

  /** Cria um grupo de variáveis */
  async createVariableGroup(params: CreateVariableGroupParams): Promise<VariableGroup> {
    const url = buildDistributedTaskApiUrl('variablegroups');
    this.logger.info(`Criando Variable Group "${params.name}"...`);
    const body = {
      name: params.name,
      description: params.description || '',
      type: 'Vsts',
      variables: params.variables,
    };
    return this.requestWithRetry<VariableGroup>('POST', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /** Atualiza um grupo de variáveis */
  async updateVariableGroup(groupId: number, existingGroup: VariableGroup, params: UpdateVariableGroupParams): Promise<VariableGroup> {
    const url = buildDistributedTaskApiUrl(`variablegroups/${groupId}`);
    this.logger.info(`Atualizando Variable Group #${groupId}...`);
    const body = {
      name: params.name || existingGroup.name,
      description: params.description ?? existingGroup.description ?? '',
      type: existingGroup.type || 'Vsts',
      variables: params.variables || existingGroup.variables,
    };
    return this.requestWithRetry<VariableGroup>('PUT', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /** Lista grupos de variáveis com filtro opcional por nome */
  async getVariableGroups(name?: string): Promise<PaginatedResponse<VariableGroup>> {
    const queryParams: Record<string, string | number | boolean> = {};
    if (name) queryParams.groupName = name;
    const url = buildDistributedTaskApiUrl('variablegroups', queryParams);
    this.logger.info('Listando Variable Groups...');
    return this.requestWithRetry<PaginatedResponse<VariableGroup>>('GET', url);
  }

  /** Autoriza uma pipeline a usar um variable group */
  async authorizePipelineForVariableGroup(variableGroupId: number, pipelineId: number): Promise<unknown> {
    const url = buildPipelinePermissionsApiUrl(`variablegroup/${variableGroupId}`);
    this.logger.info(`Autorizando Pipeline #${pipelineId} para Variable Group #${variableGroupId}...`);
    const body = {
      pipelines: [{ id: pipelineId, authorized: true }],
    };
    return this.requestWithRetry<unknown>('PATCH', url, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Helpers de Alto Nível (Fluxos compostos)
  // ═══════════════════════════════════════════════════════════════════════

  /**
   * Converte Test Case Steps para formato XML do Azure DevOps.
   * Quando expectedResult não é informado, replica a linha literal em ambos os campos
   * para preservar exatamente o step original do arquivo .feature.
   */
  static buildTestCaseStepsXml(steps: TestCaseStep[]): string {
    const stepElements = steps.map((step, index) => {
      const id = index + 1;
      const action = escapeXml(step.action);
      const expected = escapeXml(step.expectedResult ?? step.action);
      return (
        `  <step id="${id}" type="ActionStep">\n` +
        `    <parameterizedString isformatted="true">${action}</parameterizedString>\n` +
        `    <parameterizedString isformatted="true">${expected}</parameterizedString>\n` +
        `  </step>`
      );
    });

    return (
      `<steps id="0" last="${steps.length}">\n` +
      stepElements.join('\n') +
      '\n</steps>'
    );
  }

  /**
   * Converte linhas de steps Gherkin já extraídas do .feature para XML do Azure DevOps,
   * mantendo o texto literal de cada linha (Given/When/Then/And/But) sem reescrita.
   */
  static buildTestCaseStepsXmlFromFeatureLines(stepLines: string[]): string {
    const normalizedSteps: TestCaseStep[] = stepLines
      .map((line) => line.trim())
      .filter((line) => line.length > 0)
      .map((line) => ({ action: line }));

    return AzureDevOpsClient.buildTestCaseStepsXml(normalizedSteps);
  }

  /**
   * Formata corpo de bug em HTML com template QA padrão.
   */
  static buildBugReproStepsHtml(params: {
    reproSteps: string;
    expectedResult: string;
    actualResult: string;
    environment?: string;
    testData?: string;
  }): string {
    let html = '';
    html += `<b>🔄 Passos de Reprodução:</b>\n${params.reproSteps}\n\n`;
    html += `<b>✅ Resultado Esperado:</b>\n<p>${params.expectedResult}</p>\n\n`;
    html += `<b>❌ Resultado Obtido:</b>\n<p>${params.actualResult}</p>\n\n`;
    if (params.environment) {
      html += `<b>🖥️ Ambiente:</b>\n<p>${params.environment}</p>\n\n`;
    }
    if (params.testData) {
      html += `<b>📎 Dados de Teste:</b>\n<p>${params.testData}</p>\n\n`;
    }
    return html;
  }

  /**
   * Fluxo completo de upload de evidência para Test Result.
   * 1. Obtém Test Point
   * 2. Cria Test Run
   * 3. Obtém Test Result
   * 4. Upload attachment
   * 5. Atualiza outcome
   * 6. Finaliza Run
   */
  async executeTestUploadFlow(params: {
    testPlanId: number;
    testSuiteId: number;
    testCaseId: number;
    evidencePaths: string[];
    outcome: TestOutcome;
    comment?: string;
  }): Promise<{
    testRun: TestRun;
    testResult: TestResult;
    attachments: AttachmentUploadResponse[];
  }> {
    // 1. Obter Test Point
    const points = await this.getTestPoints(
      params.testPlanId,
      params.testSuiteId,
      params.testCaseId
    );
    const pointId = points.value[0].id;

    // 2. Criar Test Run
    const testRun = await this.createTestRun(params.testPlanId, [pointId]);

    // 3. Obter Test Result
    const results = await this.getTestResults(testRun.id);
    if (!results.value || results.value.length === 0) {
      throw new Error(`Nenhum Test Result encontrado para o Run #${testRun.id}`);
    }
    const testResult = results.value[0];

    // 4. Upload de evidências
    const attachments: AttachmentUploadResponse[] = [];
    for (const evidencePath of params.evidencePaths) {
      try {
        const attachment = await this.uploadTestResultAttachment(
          testRun.id,
          testResult.id,
          evidencePath,
          params.comment
        );
        attachments.push(attachment);
      } catch (error) {
        this.logger.error(`Falha no upload de ${evidencePath}: ${error}`);
      }
    }

    // 5. Atualizar outcome
    await this.updateTestResults(testRun.id, [
      {
        id: testResult.id,
        outcome: params.outcome,
        state: 'Completed',
        comment: params.comment || `FastQA — Resultado: ${params.outcome}`,
      },
    ]);

    // 6. Finalizar Run
    const completedRun = await this.completeTestRun(
      testRun.id,
      `FastQA Test Execution — ${params.outcome}`
    );

    return {
      testRun: completedRun,
      testResult: { ...testResult, outcome: params.outcome },
      attachments,
    };
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Helper: withClient (auto-initialize e dispose)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Executa uma função com um client.
 * Simplificado para uso com fetch nativo (não precisa de initialize/dispose).
 *
 * @example
 * const workItem = await withClient(async (client) => {
 *   return client.getWorkItem(123);
 * });
 */
export async function withClient<T>(
  fn: (client: AzureDevOpsClient) => Promise<T>,
  logPrefix?: string
): Promise<T> {
  const client = new AzureDevOpsClient(logPrefix);
  return await fn(client);
}

// ═══════════════════════════════════════════════════════════════════════════
// Utilitários privados
// ═══════════════════════════════════════════════════════════════════════════

function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

export default AzureDevOpsClient;
