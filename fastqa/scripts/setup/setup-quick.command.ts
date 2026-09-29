#!/usr/bin/env node
/**
 * FastQA Setup Command - Arguments Version
 * Configuração do projeto FastQA via argumentos
 */

import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

interface ProjectConfig {
  purpose: string;
  tool: string;
  platform: string;
  bdd: boolean;
  framework: string;
  language: string;
  inputs: string[];
  avanadeCode: {
    enabled: boolean;
    mode: string | null;
  };
  created_at: string;
}

function parseArgs() {
  const args = process.argv.slice(2);
  const config: any = {};
  
  for (let i = 0; i < args.length; i += 2) {
    if (args[i].startsWith('--')) {
      config[args[i].substring(2)] = args[i + 1];
    }
  }
  
  return config;
}

function mapChoices(args: any): ProjectConfig {
  const toolMap = ['Azure DevOps', 'Jira', 'Nenhuma'];
  const platformMap = ['Web', 'Mobile', 'API', 'Desktop'];
  const frameworkMap = {
    'Web': ['Playwright (TypeScript)', 'Playwright (JavaScript)', 'Playwright (Python)', 'Cypress (TypeScript)', 'Cypress (JavaScript)', 'Selenium', 'Robot Framework'],
    'API': ['Supertest (TypeScript)', 'Requests (Python)', 'RestAssured (Java)', 'Karate (Java)', 'Robot Framework (Python)'],
    'Mobile': ['WebdriverIO (TypeScript)', 'WebdriverIO (JavaScript)', 'Selenium (Python)', 'Selenium (Java)', 'Robot Framework (Python)'],
    'Desktop': ['Selenium (C#)', 'Playwright (C#)']
  };
  
  const platform = platformMap[parseInt(args.platform) - 1];
  const frameworks = frameworkMap[platform as keyof typeof frameworkMap] || [];
  const selectedFramework = frameworks[parseInt(args.framework) - 1];
  
  let inputs = [];
  if (args.inputs === 'todas') {
    inputs = ['Teclado', 'Mouse', 'Touch', 'Upload de arquivos', 'API Calls'];
  } else {
    const inputMap = {
      'Web': ['Teclado', 'Mouse', 'Touch', 'Upload de arquivos', 'API Calls'],
      'API': ['JSON', 'XML', 'Form Data', 'Headers customizados'],
      'Mobile': ['Touch', 'Gestures', 'Sensores', 'Push notifications']
    };
    const available = inputMap[platform as keyof typeof inputMap] || [];
    inputs = args.inputs.split(',').map((i: string) => available[parseInt(i.trim()) - 1]).filter(Boolean);
  }
  
  const avanadeMode = ['isolated', 'team', null][parseInt(args['avanade-code']) - 1];
  
  return {
    purpose: args.purpose,
    tool: toolMap[parseInt(args.tool) - 1],
    platform,
    bdd: args.bdd === '1',
    framework: selectedFramework?.split(' (')[0] || 'Playwright',
    language: selectedFramework?.match(/\((.*)\)/)?.[1] || 'TypeScript',
    inputs,
    avanadeCode: {
      enabled: args['avanade-code'] !== '3',
      mode: avanadeMode
    },
    created_at: new Date().toISOString()
  };
}

function createFolders() {
  const folders = [
    // Manual test folders
    'fastqa/manual_test/US',
    'fastqa/manual_test/gap_analysis',
    'fastqa/manual_test/estimate_effort', 
    'fastqa/manual_test/requirements_analysis',
    'fastqa/manual_test/behavior_analysis',
    'fastqa/manual_test/test_cases',
    'fastqa/manual_test/evidence',
    
    // Web automation folders
    'automated_test/web/tests',
    'automated_test/web/config',
    'automated_test/web/pages',
    'automated_test/web/data',
    'automated_test/web/support',
    'automated_test/web/results',
    
    // API automation folders
    'automated_test/api/tests',
    'automated_test/api/config',
    'automated_test/api/collections',
    'automated_test/api/schemas',
    'automated_test/api/data',
    'automated_test/api/support',
    'automated_test/api/results',
    
    // Mobile automation folders
    'automated_test/mobile/tests',
    'automated_test/mobile/config',
    'automated_test/mobile/screens',
    'automated_test/mobile/apps',
    'automated_test/mobile/data',
    'automated_test/mobile/support',
    'automated_test/mobile/results',
    
    // Shared resources
    'automated_test/shared/constants',
    'automated_test/shared/fixtures',
    'automated_test/shared/helpers',
    'automated_test/shared/types'
  ];
  
  folders.forEach(folder => {
    if (!fs.existsSync(folder)) {
      fs.mkdirSync(folder, { recursive: true });
      // Criar .gitkeep em pastas vazias
      const gitkeepPath = path.join(folder, '.gitkeep');
      if (!fs.existsSync(gitkeepPath)) {
        fs.writeFileSync(gitkeepPath, '');
      }
    }
  });
}

function main() {
  console.log('🚀 FastQA Setup - Configurando projeto...\n');
  
  const args = parseArgs();
  const config = mapChoices(args);
  
  console.log('📋 Configuração:');
  console.log(`✅ Propósito: ${config.purpose}`);
  console.log(`✅ Ferramenta: ${config.tool}`);
  console.log(`✅ Plataforma: ${config.platform}`);
  console.log(`✅ BDD/Gherkin: ${config.bdd ? 'Sim' : 'Não'}`);
  console.log(`✅ Framework: ${config.framework} (${config.language})`);
  console.log(`✅ Inputs: ${config.inputs.join(', ')}`);
  console.log(`✅ Avanade CODE: ${config.avanadeCode.enabled ? 'Habilitado (' + config.avanadeCode.mode + ')' : 'Desabilitado'}\n`);
  
  // Criar estrutura de pastas
  console.log('📁 Criando estrutura de pastas...');
  createFolders();
  
  // Salvar configuração
  console.log('💾 Salvando configuração...');
  fs.writeFileSync('fastqa/scripts/project_config.json', JSON.stringify(config, null, 2));
  
  // Configurar Avanade CODE
  if (config.avanadeCode.enabled && config.avanadeCode.mode === 'isolated') {
    console.log('⚙️  Configurando Avanade CODE...');
    try {
      execSync('npm run setup:bmad', { cwd: 'fastqa/', stdio: 'inherit' });
      console.log('✅ Avanade CODE configurado!');
    } catch (error: any) {
      console.log('⚠️  Avanade CODE: execute "npm run setup:bmad" manualmente');
    }
  } else if (config.avanadeCode.enabled && config.avanadeCode.mode === 'team') {
    console.log('ℹ️  Avanade CODE: configuração integrada será feita pelo time');
  }
  
  console.log('\n✅ Setup concluído com sucesso!');
  console.log('📄 Configuração salva em: fastqa/scripts/project_config.json');
  console.log('📁 Estrutura criada em: fastqa/');
  console.log('\n🚀 Próximos passos:');
  console.log('   - Execute @fastqa:help para ver comandos disponíveis');
  console.log('   - Comece com @fastqa:load_pbi ou @fastqa:identify_gaps');
}

main();