/**
 * FastQA Setup - Static Configurations
 * Frameworks, Inputs, Folder Structure definitions
 */

import { FrameworkConfig, InputConfig, PlatformType } from './setup.types';

export const FRAMEWORKS: FrameworkConfig[] = [
  { name: 'Playwright', language: 'TypeScript', supportedPlatforms: ['Web', 'API'] },
  { name: 'Playwright', language: 'Python', supportedPlatforms: ['Web', 'API'] },
  { name: 'Playwright', language: 'Java', supportedPlatforms: ['Web', 'API'] },
  { name: 'Playwright', language: 'C#', supportedPlatforms: ['Web', 'API'] },
  { name: 'Cypress', language: 'TypeScript', supportedPlatforms: ['Web', 'API'] },
  { name: 'Cypress', language: 'JavaScript', supportedPlatforms: ['Web', 'API'] },
  { name: 'Selenium', language: 'Python', supportedPlatforms: ['Web', 'Mobile'] },
  { name: 'Selenium', language: 'Java', supportedPlatforms: ['Web', 'Mobile'] },
  { name: 'Selenium', language: 'C#', supportedPlatforms: ['Web', 'Mobile'] },
  { name: 'Robot Framework', language: 'Python', supportedPlatforms: ['Web', 'API', 'Mobile'] },
  { name: 'WebdriverIO', language: 'TypeScript', supportedPlatforms: ['Web', 'Mobile'] },
  { name: 'WebdriverIO', language: 'JavaScript', supportedPlatforms: ['Web', 'Mobile'] },
  { name: 'Supertest', language: 'TypeScript', supportedPlatforms: ['API'] },
  { name: 'Requests', language: 'Python', supportedPlatforms: ['API'] },
  { name: 'RestAssured', language: 'Java', supportedPlatforms: ['API'] },
  { name: 'Karate', language: 'Java', supportedPlatforms: ['API'] }
];

// Formatos de massa de dados suportados
export const DATA_FORMATS: InputConfig[] = [
  { name: 'JSON (.json)', supportedPlatforms: ['Web', 'API', 'Mobile', 'Desktop'] },
  { name: 'Excel (.xlsx)', supportedPlatforms: ['Web', 'API', 'Mobile', 'Desktop'] },
  { name: 'CSV (.csv)', supportedPlatforms: ['Web', 'API', 'Mobile', 'Desktop'] },
  { name: 'YAML (.yml)', supportedPlatforms: ['Web', 'API', 'Mobile', 'Desktop'] },
  { name: 'XML (.xml)', supportedPlatforms: ['API', 'Web'] },
  { name: 'Banco de Dados (SQL)', supportedPlatforms: ['Web', 'API', 'Mobile', 'Desktop'] },
  { name: 'Fixtures (hardcoded)', supportedPlatforms: ['Web', 'API', 'Mobile', 'Desktop'] }
];

// Manter INPUTS como alias para compatibilidade
export const INPUTS = DATA_FORMATS;

export const BASE_FOLDERS = [
  'agents/core',
  'agents/connectors',
  'manual_test/US',
  'manual_test/gap_analysis',
  'manual_test/estimate_effort',
  'manual_test/requirements_analysis',
  'manual_test/behavior_analysis',
  'manual_test/test_cases',
  'manual_test/evidence',
  'manual_test/regression_analysis',
  'automated_test/shared/constants',
  'automated_test/shared/fixtures',
  'automated_test/shared/helpers',
  'automated_test/shared/types',
  'scripts/azure-devops'
];

export const CONDITIONAL_FOLDERS: Record<string, string[]> = {
  Web: [
    'automated_test/web/config',
    'automated_test/web/data',
    'automated_test/web/pages',
    'automated_test/web/support',
    'automated_test/web/tests',
    'automated_test/web/results'
  ],
  API: [
    'automated_test/api/config',
    'automated_test/api/collections',
    'automated_test/api/schemas',
    'automated_test/api/data',
    'automated_test/api/support',
    'automated_test/api/tests',
    'automated_test/api/results'
  ],
  Mobile: [
    'automated_test/mobile/config',
    'automated_test/mobile/apps',
    'automated_test/mobile/screens',
    'automated_test/mobile/data',
    'automated_test/mobile/support',
    'automated_test/mobile/tests',
    'automated_test/mobile/results'
  ],
  Desktop: [
    'automated_test/desktop/config',
    'automated_test/desktop/data',
    'automated_test/desktop/pages',
    'automated_test/desktop/support',
    'automated_test/desktop/tests',
    'automated_test/desktop/results'
  ]
};

export const TEST_LEVELS = [
  'Funcional',
  'Integração',
  'E2E',
  'Regressão',
  'Performance',
  'Segurança',
  'Acessibilidade',
  'Usabilidade'
];

export const BROWSERS = [
  'Chrome',
  'Firefox',
  'Edge',
  'Safari'
];

export const MOBILE_PLATFORMS = [
  'Android',
  'iOS'
];
