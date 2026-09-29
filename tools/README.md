# IMF AVA Tools — Monorepo de Ferramentas para Migração

**Um repositório centralizado de ferramentas determinísticas e de alta qualidade para suportar as fábricas de modernização de aplicações legadas.**

## 📋 Objetivo do Projeto

Este monorepo centraliza as **ferramentas (tools) reutilizáveis** que as fábricas de migração de aplicações (*migration factories*) utilizam para:

1. **Extrair e analisar código legado** de forma determinística (sem dependência de LLM)
2. **Pré-processar artefatos** antes da interpretação por agentes de IA (reduzindo custo de tokens)
3. **Validar e estruturar dados** segundo esquemas JSON predefinidos
4. **Gerar relatórios e dashboards** para tomadas de decisão arquitetural

Cada ferramenta segue o padrão **determinístico → LLM**, garantindo:
- ✅ Reprodutibilidade (mesma entrada, mesma saída)
- ✅ Economia de tokens (compressão com Headroom antes de entregar ao modelo)
- ✅ Rastreabilidade (artefatos estruturados, auditáveis)
- ✅ Integração com agentes GitHub Copilot/AVA Fabric

---

## 🛠️ Tools Disponíveis

### 1. **AVA Fabric — Delphi Analyzer** (`ava-fabric-delphi-analyzer/`)

Ferramenta para modernização de sistemas legados em **Delphi/Object Pascal** → **.NET 8**.

#### 📌 O que faz

Executa um pipeline em duas etapas:

```
Código Delphi legado (.pas/.dfm)
   │
   ├─ [STEP 1] Extração determinística (AST real via DelphiAST)
   │           └─ Produz 9 artefatos JSON estruturados
   │
   ├─ [STEP 2] Compressão inteligente (Headroom)
   │           └─ Reduz tokens em ~57% (média real)
   │
   └─ [STEP 3] Interpretação por agente Copilot
               └─ Produz levantamento de modernização detalhado
```

#### 📦 Artefatos Gerados (9 JSONs)

| Artefato | Descrição | Exemplo |
|----------|-----------|---------|
| `01_business_rules.json` | Validações, cálculos e regras de negócio mapeadas por função | Conversões de moeda, validações de CPF |
| `02_form_business_rules.json` | Lógica específica de telas (forms) e handlers de eventos | Habilitação condicional de campos, máscaras |
| `03_database_rules.json` | Restrições, gatilhos e operações no banco de dados | Foreign keys, CHECK constraints, triggers |
| `04_database_schemas.json` | Estrutura de tabelas, colunas e índices | Schema da base de dados |
| `05_procedures.json` | Procedures, functions e métodos de negócio | Funções de cálculo, processamento em lote |
| `06_integrations.json` | Integrações com sistemas externos (WebServices, APIs) | Chamadas a APIs de terceiros, EDI |
| `07_apis.json` | APIs e endpoints expostos pelo sistema | Serviços REST/SOAP, pontos de integração |
| `08_code_overview.json` | Visão geral: complexidade ciclomática, tamanho, dependências | Hotspots de migração, módulos críticos |
| `09_test_coverage.json` | Suites de testes, frameworks e cobertura | DUnit/DUnitX, fixtures, testes unitários |

#### 🔧 Requisitos

- **Python 3.10+**
- Dependências Python:
  - `headroom-ai[all]>=0.22` (compressor inteligente; fallback SmartCrusher-lite se não instalado)
  - `jsonschema>=4.20` (validação de contratos)
  - `xlsxwriter>=3.1` (geração de dashboards)
- (Opcional, recomendado) Binário DelphiAST (`bin/ava_ast_cli`) — extrator AST real. Sem ele, usa fallback regex por arquivo.

#### 🚀 Quick Start

```bash
# 1. Instalar dependências
cd ava-fabric-delphi-analyzer/
pip install -r requirements.txt

# 2. Configurar binário DelphiAST (Linux/macOS)
export AVA_AST_CLI=./bin/ava_ast_cli
chmod +x ./bin/ava_ast_cli

# 2b. Para Windows: compile o .exe local (veja docs/BUILD_WINDOWS.md)
$env:AVA_AST_CLI = ".\bin\ava_ast_cli.exe"

# 3. Rodar no seu projeto Delphi
python src/run_pipeline.py C:\Desenv\MeuProjeto \
    --extraction ./.ava-fabric/extraction \
    --compressed ./.ava-fabric/compressed

# 4. Usar os artefatos em GitHub Copilot
# Copie agents/delphi-analyzer.prompt.md para .github/prompts/
# no repositório alvo e configure no chat do Copilot
```

#### 📚 Documentação Detalhada

- **[README da tool](ava-fabric-delphi-analyzer/README.md)** — guia completo de uso
- **[Guia Headroom](ava-fabric-delphi-analyzer/docs/GUIA_HEADROOM.md)** — compressão real vs. fallback
- **[Integração AVA Fabric Agents](ava-fabric-delphi-analyzer/docs/GUIA_ESTEIRA.md)** — uso na esteira de agentes
- **[Build do binário DelphiAST](ava-fabric-delphi-analyzer/docs/BUILD_WINDOWS.md)** — recompilar no Windows

#### 📊 Resultados Típicos

```
Projeto: Meu-ERP (1.240 funções, 89 tabelas, 34 forms)

Extração AST:
  ✓ 01_business_rules        84 regras identificadas
  ✓ 02_form_business_rules   127 handlers mapeados
  ✓ 03_database_rules        22 constraints + triggers
  ✓ 04_database_schemas      89 tabelas, 567 colunas
  ✓ 05_procedures            1.240 procedures/functions
  ✓ 06_integrations          8 integrações externas
  ✓ 07_apis                  3 APIs/WebServices
  ✓ 08_code_overview         Complexidade média: 7.2
  ✓ 09_test_coverage         0 testes automatizados (⚠️ risco)

Compressão Headroom:
  Total: 54.907 tokens → 23.567 tokens (-57,1%)
  Economia em LLM: ~$0,35/análise (vs. $0,82 sem compressão)
```

---

## 🚀 Getting Started

### Instalação Rápida

```bash
# Clone o repositório
git clone https://github.com/seu-org/imfai-ava-tools.git
cd imfai-ava-tools

# Para usar Delphi Analyzer
cd ava-fabric-delphi-analyzer
pip install -r requirements.txt
```

### Software Mínimo Necessário

| Software | Versão | Propósito |
|----------|--------|----------|
| Python | 3.10+ | Runtime das tools |
| Git | 2.0+ | Clonar ferramentas |
| Headroom (opcional) | 0.22+ | Compressor inteligente |

### Executar a Primeira Análise

```bash
# Com o exemplo vendorizado (Meu-ERP)
python ava-fabric-delphi-analyzer/src/run_pipeline.py \
    ava-fabric-delphi-analyzer/examples/Meu-ERP \
    --extraction ./.ava-fabric/extraction \
    --compressed ./.ava-fabric/compressed

# Ver os artefatos gerados
ls -la .ava-fabric/compressed/
```

---

## 🔨 Build e Validação

### Validar Artefatos contra Schema

```bash
python ava-fabric-delphi-analyzer/src/validate_artifacts.py \
    ./.ava-fabric/compressed/ \
    --schema ava-fabric-delphi-analyzer/src/schemas/artifacts.schema.json
```

### Gerar Dashboard Excel

```bash
python ava-fabric-delphi-analyzer/src/generate_excel_report.py \
    ./.ava-fabric/compressed/ \
    --output relatorio-modernizacao.xlsx
```

### Rodar em Modo Fallback (sem Headroom real)

```bash
# Usa o SmartCrusher-lite embutido (sem instalar headroom-ai)
python ava-fabric-delphi-analyzer/src/run_pipeline.py \
    /caminho/do/legado \
    --extraction ./.ava-fabric/extraction \
    --compressed ./.ava-fabric/compressed \
    --no-headroom
```

---

## 🤝 Contribuir

Este monorepo é **aberto a contribuições** de equipes de migração. Para adicionar uma nova tool ou melhorar a existente:

### 1. Criar uma Nova Tool

```bash
# Estrutura recomendada
mkdir -p ava-fabric-<nome-tool>/{src,agents,docs,examples,bin}

# Arquivos mínimos
touch ava-fabric-<nome-tool>/{README.md,requirements.txt}
```

### 2. Padrões de Desenvolvimento

- ✅ **Determinismo**: a ferramenta deve produzir **mesma saída para mesma entrada**
- ✅ **JSON estruturado**: artefatos devem ter schema JSON predefinido
- ✅ **Validação**: incluir `validate_artifacts.py` ou similar
- ✅ **Documentação**: README + guia de uso + exemplos
- ✅ **Agente Copilot**: incluir `.prompt.md` para integração com GitHub Copilot
- ✅ **Tests**: ao menos validação de artefatos e exemplo end-to-end

### 3. Submeter uma PR

1. Fork este repositório
2. Crie uma branch: `git checkout -b feature/nova-tool`
3. Desenvolva e teste localmente
4. Valide contra os padrões acima
5. Abra PR com descrição clara do problema/oportunidade

---

## 📞 Suporte e Referências

### Links Importantes

- [DelphiAST Parser](ava-fabric-delphi-analyzer/examples/DelphiAST/) — fonte do parser Delphi
- [Headroom AI](https://github.com/your-org/headroom) — compressor inteligente de artefatos
- [GitHub Copilot Agent Mode](https://docs.github.com/en/copilot/using-github-copilot/asking-github-copilot-questions) — integração com Copilot

### Contato

Para dúvidas, sugestões ou relatórios de bug, abra uma **Issue** neste repositório.

---

**Última atualização**: July 2026  
**Versão**: 0.1.0 (Preview)