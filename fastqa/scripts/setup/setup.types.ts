/**
 * FastQA Setup - TypeScript Type Definitions
 * Interfaces e tipos para configuração do projeto
 */

export type IntegrationType =
  | 'Azure DevOps + Test Plans'
  | 'Azure DevOps (sem Test Plans)'
  | 'Jira + Xray'
  | 'Jira + Zephyr Scale'
  | 'Jira + AssertThat'
  | 'Jira (sem gerenciamento de testes)'
  | 'Nenhuma'
  | 'Outro';
/** @deprecated Usar IntegrationType. Mantido para compatibilidade. */
export type ToolType = 'Azure DevOps' | 'Jira' | 'Nenhuma';
export type TestCaseFormatType = 'gherkin' | 'step_by_step' | 'none' | string;
export type PlatformType = 'Web' | 'Mobile' | 'API' | 'Desktop';
export type BDDOption = 'Sim' | 'Não';
export type AvanadeCodeConfig = 'Isolada' | 'Integrada com o Time' | 'Não instalar no momento';

export interface AzureDevOpsSetupConfig {
  configure_mcp: boolean;
  org_url: string;
  pat: string;
  default_project: string;
}

export interface FrameworkConfig {
  name: string;
  language: string;
  supportedPlatforms: PlatformType[];
}

export interface InputConfig {
  name: string;
  supportedPlatforms: PlatformType[];
}

export interface ProjectConfigJson {
  metadata: {
    created_at: string;
    updated_at: string;
    version: string;
    status: string;
  };
  analysis: {
    purpose: string;
    application_description: string;
    domain: string;
  };
  project_management: {
    tool: string;
    azure_devops: {
      enabled: boolean;
      org_url: string;
      project: string;
      pat: string;
      test_plan_id: number | null;
      test_suite_id: number | null;
    };
    jira: {
      enabled: boolean;
      url: string;
      project_key: string;
      api_token: string;
    };
  };
  platform: {
    type: string;
    details: {
      browsers: string[];
      devices: string[];
      api_base_url: string;
      swagger_url: string;
      apk_path: string;
      desktop_app_path: string;
    };
  };
  testing_approach: {
    use_gherkin_bdd: boolean;
    test_levels: string[];
  };
  connectors: {
    output: {
      automation_framework: string;
      language: string;
    };
    input: {
      type: string;
      sources: string[];
    };
  };
  folder_structure: {
    root: string;
    directories: string[];
  };
  avanade_code?: {
    enabled: boolean;
    mode: AvanadeCodeConfig | null;
    configured_at: string | null;
  };
}

export interface WizardResult {
  purpose: string;
  integration: IntegrationType;
  testManagementTool: string;
  toolManagement: string;
  platform: PlatformType;
  testCaseFormat: TestCaseFormatType;
  useBDD: boolean;
  framework: {
    name: string;
    language: string;
  };
  inputs: string[];
  azureDevOps?: AzureDevOpsSetupConfig;
  avanadeCode: {
    enabled: boolean;
    mode: AvanadeCodeConfig | null;
    configuredAt: string | null;
  };
}

export interface FolderStructure {
  baseFolders: string[];
  conditionalFolders: Record<string, string[]>;
}
