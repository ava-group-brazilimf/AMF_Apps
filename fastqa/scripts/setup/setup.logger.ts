/**
 * FastQA Setup - Logger Utility
 * Estruturado para console com suporte a cores e níveis
 */

export class Logger {
  private colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    dim: '\x1b[2m',
    
    // Foreground colors
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    white: '\x1b[37m',
    
    // Background colors
    bgRed: '\x1b[41m',
    bgGreen: '\x1b[42m',
    bgYellow: '\x1b[43m',
    bgBlue: '\x1b[44m'
  };

  info(message: string): void {
    console.log(`${this.colors.cyan}${message}${this.colors.reset}`);
  }

  success(message: string): void {
    console.log(`${this.colors.green}${message}${this.colors.reset}`);
  }

  warning(message: string): void {
    console.log(`${this.colors.yellow}⚠️  ${message}${this.colors.reset}`);
  }

  error(message: string): void {
    console.error(`${this.colors.red}❌ ${message}${this.colors.reset}`);
  }

  header(message: string): void {
    const separator = '═'.repeat(60);
    console.log(`\n${this.colors.bright}${this.colors.blue}${separator}${this.colors.reset}`);
    console.log(`${this.colors.bright}${this.colors.blue}${message}${this.colors.reset}`);
    console.log(`${this.colors.bright}${this.colors.blue}${separator}${this.colors.reset}\n`);
  }

  section(message: string): void {
    console.log(`\n${this.colors.bright}${this.colors.magenta}${message}${this.colors.reset}`);
  }

  step(number: number, message: string): void {
    console.log(`\n${this.colors.bright}${this.colors.cyan}${number}️⃣  ${message}${this.colors.reset}`);
  }

  option(number: number, text: string): void {
    console.log(`   ${this.colors.dim}${number}.${this.colors.reset} ${text}`);
  }

  summary(label: string, value: string | string[]): void {
    const formattedValue = Array.isArray(value) ? value.join(', ') : value;
    console.log(`${this.colors.bright}${label}:${this.colors.reset} ${formattedValue}`);
  }

  separator(): void {
    console.log(`${this.colors.dim}${'─'.repeat(60)}${this.colors.reset}`);
  }
}
