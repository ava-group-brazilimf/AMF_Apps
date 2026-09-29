/**
 * ============================================================================
 * FastQA — Logger Utility
 * ============================================================================
 * Logger estruturado com output para console (colorido) e arquivo.
 * Cada instância escreve em um arquivo de log separado no diretório logs/.
 * ============================================================================
 */

import * as fs from 'fs';
import * as path from 'path';
import { config } from '../azure-devops.config';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'success';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  prefix: string;
  message: string;
}

// Cores ANSI para console
const COLORS: Record<LogLevel, string> = {
  debug: '\x1b[90m',   // cinza
  info: '\x1b[36m',    // ciano
  warn: '\x1b[33m',    // amarelo
  error: '\x1b[31m',   // vermelho
  success: '\x1b[32m', // verde
};

const ICONS: Record<LogLevel, string> = {
  debug: '🔍',
  info: 'ℹ️ ',
  warn: '⚠️ ',
  error: '❌',
  success: '✅',
};

const RESET = '\x1b[0m';

export class Logger {
  private prefix: string;
  private logFilePath: string;
  private entries: LogEntry[] = [];

  constructor(prefix: string) {
    this.prefix = prefix;

    // Garante que o diretório de logs existe
    if (!fs.existsSync(config.logsDir)) {
      fs.mkdirSync(config.logsDir, { recursive: true });
    }

    // Cria arquivo de log com timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const sanitizedPrefix = prefix.replace(/[^a-zA-Z0-9_-]/g, '_');
    this.logFilePath = path.join(config.logsDir, `${sanitizedPrefix}-${timestamp}.log`);
  }

  /** Log de nível debug (cinza) */
  debug(message: string): void {
    this.log('debug', message);
  }

  /** Log de nível info (ciano) */
  info(message: string): void {
    this.log('info', message);
  }

  /** Log de nível warn (amarelo) */
  warn(message: string): void {
    this.log('warn', message);
  }

  /** Log de nível error (vermelho) */
  error(message: string): void {
    this.log('error', message);
  }

  /** Log de nível success (verde) */
  success(message: string): void {
    this.log('success', message);
  }

  /** Retorna todas as entradas de log */
  getEntries(): LogEntry[] {
    return [...this.entries];
  }

  /** Retorna o caminho do arquivo de log */
  getLogFilePath(): string {
    return this.logFilePath;
  }

  // ─────────────────────────────────────────────────────────────────────
  // Métodos privados
  // ─────────────────────────────────────────────────────────────────────

  private log(level: LogLevel, message: string): void {
    const timestamp = new Date().toISOString();
    const entry: LogEntry = { timestamp, level, prefix: this.prefix, message };
    this.entries.push(entry);

    // Console output (colorido)
    const color = COLORS[level];
    const icon = ICONS[level];
    const levelLabel = level.toUpperCase().padEnd(7);
    console.log(
      `${color}${icon} [${timestamp}] [${this.prefix}] ${levelLabel}${RESET} ${message}`
    );

    // File output (texto plano)
    try {
      const fileLine = `[${timestamp}] [${this.prefix}] [${level.toUpperCase()}] ${message}\n`;
      fs.appendFileSync(this.logFilePath, fileLine, 'utf-8');
    } catch {
      // Falha silenciosa no log de arquivo — não deve interromper operação
    }
  }
}

/**
 * Cria logger padrão para um script de comando.
 * O nome do arquivo de log será baseado no nome do comando.
 *
 * @example
 * const logger = createCommandLogger('get-work-item');
 * logger.info('Buscando work item #123...');
 */
export function createCommandLogger(commandName: string): Logger {
  return new Logger(commandName);
}

export default Logger;
