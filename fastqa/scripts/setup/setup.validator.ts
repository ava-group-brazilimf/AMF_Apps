/**
 * FastQA Setup - Configuration Validator
 * Valida a configuração gerada pelo wizard
 */

import { ProjectConfigJson, WizardResult } from './setup.types';
import { Logger } from './setup.logger';

const logger = new Logger();

export function validateWizardResult(result: WizardResult): boolean {
  const errors: string[] = [];

  // Validar propósito
  if (!result.purpose || result.purpose.trim().length < 5) {
    errors.push('Propósito deve ter no mínimo 5 caracteres');
  }

  // Validar framework
  if (!result.framework.name || !result.framework.language) {
    errors.push('Framework e linguagem devem ser selecionados');
  }

  // Validar inputs
  if (!result.inputs || result.inputs.length === 0) {
    errors.push('Pelo menos um input deve ser selecionado');
  }

  // Validar plataforma
  const validPlatforms = ['Web', 'Mobile', 'API', 'Desktop'];
  if (!validPlatforms.includes(result.platform)) {
    errors.push(`Plataforma inválida: ${result.platform}`);
  }

  if (errors.length > 0) {
    logger.error('⚠️  Erros de validação encontrados:');
    errors.forEach(err => logger.error(`   - ${err}`));
    return false;
  }

  return true;
}

export function validateProjectConfig(config: ProjectConfigJson): boolean {
  const errors: string[] = [];

  // Validar estrutura básica
  if (!config.metadata || !config.analysis || !config.platform) {
    errors.push('Estrutura de configuração incompleta');
  }

  // Validar ferramentas de gestão (configurações específicas podem ser definidas posteriormente)
  // Azure DevOps e Jira podem ser configurados após setup inicial



  if (errors.length > 0) {
    logger.error('⚠️  Configuração inválida:');
    errors.forEach(err => logger.error(`   - ${err}`));
    return false;
  }

  return true;
}

export function validateFolderPath(folderPath: string): boolean {
  // Em Windows, o prefixo de drive (ex: C:) é válido.
  // Remove apenas esse prefixo para validar o restante do caminho.
  const normalizedPath = folderPath.replace(/^[a-zA-Z]:/, '');

  // Validar caracteres inválidos no caminho
  const invalidChars = /[<>:"|?*]/;
  if (invalidChars.test(normalizedPath)) {
    logger.error(`Caminho inválido: ${folderPath} contém caracteres não permitidos`);
    return false;
  }

  return true;
}
