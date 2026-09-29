---
name: "fastqa_6.2_generate_regression_map"
description: "Gera regression-map.yaml a partir dos testes existentes no repositório"

tools:
  - memory
  - sequential-thinking
---

# Template: Gerador de Regression Map

## 🎯 Objetivo
Varrer o repositório de testes automatizados e manuais, inferir áreas funcionais a partir dos specs, features e page objects, e gerar o `regression-map.yaml` semi-automaticamente.

**Contexto:** Este agent lê `fastqa/scripts/project_config.json` para obter paths dos testes e configuração do framework.

---

## 📥 Entrada

### Parâmetros Aceitos
```typescript
{
  output?: string;   // Caminho de saída (default: fastqa/scripts/regression-map.yaml)
  merge?: boolean;   // Se true, preserva app_patterns customizados do mapa existente
  layers?: Array<{   // Camadas de teste a varrer
    name: string;    // Identificador: 'e2e', 'api', 'unit', etc.
    path: string;    // Caminho relativo do diretório de testes
  }>;
}
```

### Validações
1. Ler `fastqa/scripts/project_config.json` para obter paths de testes
2. Verificar se diretórios de testes existem
3. Se `--merge` e mapa já existe, preservar customizações

---

## 📤 Saída (Contrato)

### Sucesso
- Arquivo `fastqa/scripts/regression-map.yaml` gerado/atualizado
- Resumo de áreas detectadas, testes mapeados e sugestões pendentes

### Erro
- Mensagem clara indicando diretórios não encontrados ou config ausente

---

## 🔄 Fluxo de Execução

### 1️⃣ Verificar Pré-condições
- Ler `fastqa/scripts/project_config.json`:
  - Framework e linguagem
  - Tipo de plataforma (web, api, mobile)
  - Paths customizados (tests, pages)
- Se config não encontrado:
  ```
  ⚠️ project_config.json não encontrado.
  Execute @fastqa:setup_project primeiro para configurar o projeto.
  ```

### 2️⃣ Solicitar Camadas de Teste

**OBRIGATÓRIO:** Antes de executar a varredura, o agente DEVE perguntar ao usuário **quais camadas de teste** ele quer incluir no mapa de regressão. Esta decisão impacta diretamente o escopo da análise.

**Passo A — Perguntar quais camadas incluir:**

```
🗂️ Quais camadas de teste você quer incluir no mapa de regressão?

  1️⃣ Testes E2E (end-to-end / integração visual)
  2️⃣ Testes de API (integração de endpoints / contratos)
  3️⃣ Testes Unitários (lógica de negócio / componentes isolados)

Escolha uma ou mais opções (ex: "1,2", "todas", "apenas e2e"):
```

- **AGUARDAR** resposta do usuário — NÃO prosseguir sem confirmação
- Se o usuário responder "todas" ou "1,2,3": incluir as 3 camadas
- Se o usuário responder "1,2": incluir apenas E2E e API
- Se o usuário responder "apenas e2e" ou "1": incluir apenas E2E
- Registrar a decisão do usuário — as camadas escolhidas serão usadas em todo o fluxo

> **⚠️ IMPORTANTE:** Não assumir que todas as camadas devem ser incluídas.
> Projetos podem ter testes unitários irrelevantes para regressão funcional,
> ou podem querer focar apenas em E2E para um mapa inicial.

**Passo B — Solicitar caminhos das camadas escolhidas:**

Para cada camada selecionada, perguntar o caminho:
```
📂 Informe os caminhos relativos (a partir da raiz do workspace)
   para as camadas escolhidas:

  {listar apenas as camadas que o usuário escolheu}
  Ex:
    E2E: test/cypress/e2e
    API: test/api
    Unit: test/server

💡 Se não souber o caminho exato, posso procurar automaticamente.
   Basta responder "procurar" e farei um scan do workspace.
```

- **AGUARDAR** resposta do usuário
- Se o usuário responder "procurar": usar `file_search` com patterns `**/*.spec.ts`, `**/*.test.ts`, `**/*Spec.ts` para sugerir paths
- Para cada camada informada, validar que o diretório existe
- Se o diretório não existir, avisar e pedir confirmação

**Montar argumento --layers:**
A partir das respostas, montar o argumento CLI. Exemplo:
- E2E: `test/cypress/e2e` → `e2e:test/cypress/e2e`
- API: `test/api` → `api:test/api`
- Unit: `server/test` → `unit:server/test`
- Resultado: `--layers e2e:test/cypress/e2e,api:test/api,unit:server/test`

**Se o usuário informar apenas 1 camada:** o script funciona sem prefixos (backward-compatible).
**Se o usuário informar múltiplas camadas:** testes serão prefixados com `[layer]` no YAML (ex: `[api] loginApiSpec.ts`).

### 2.5️⃣ Solicitar Caminho da Aplicação (App-Aware Patterns)

Após coletar as camadas de teste, perguntar:

```
📂 Para gerar app_patterns precisos, informe o caminho do repositório
   da aplicação (código de produção):

   Ex: C:\Repos\juice-shop, ../my-app, /home/user/my-app

💡 Se omitido, os app_patterns serão sugeridos genericamente
   (ex: **/login*) e precisarão de revisão manual.

📁 Opcionalmente, informe os diretórios fonte da aplicação
   (vírgula-separado): src, lib, routes
   Se omitido, o script varre toda a raiz (excluindo node_modules, dist, etc.)
```

- **AGUARDAR** resposta do usuário
- Se fornecido, validar que o caminho existe
- Montar argumento: `--app-repo-path <path> [--app-src-dirs <dirs>]`
- Se omitido, prosseguir sem (backward-compatible, patterns genéricos)

### 3️⃣ Verificar Mapa Existente
- Se `fastqa/scripts/regression-map.yaml` já existe:
  ```
  📂 regression-map.yaml já existe com {N} áreas configuradas.
  
  O que deseja fazer?
    1️⃣ Merge — preserva seus app_patterns e adiciona testes novos
    2️⃣ Sobrescrever — gera do zero (perde customizações manuais)
    3️⃣ Cancelar
  ```
- **AGUARDAR** resposta do usuário

### 4️⃣ Executar Geração
- Executar o script **sempre** com `--enrich` para gerar contexto de revisão AI:
  ```bash
  npx tsx fastqa/scripts/regression/commands/generate-regression-map.command.ts \
    [--merge] \
    [--layers e2e:path/e2e,api:path/api,unit:path/unit] \
    [--app-repo-path <path>] \
    [--app-src-dirs <dirs>] \
    --enrich --include-gaps
  ```
- O script varre automaticamente cada camada informada:
  - `**/*.spec.ts`, `**/*.test.ts`, `**/*Spec.ts` → extrai nomes de describe/test
  - `manual_test/test_cases/**/*.feature` → extrai tags (@checkout, @login)
  - `{pages_dir}/**/*Page.ts` ou `*Screen.ts` → extrai nomes e URLs
- Se `--app-repo-path` fornecido: varre a aplicação e gera patterns precisos cruzando nomes de áreas
- Agrupa por similaridade e gera o YAML

### 5️⃣ Apresentar Resultado Bruto

```
✅ Regression Map Gerado (bruto)

📄 Arquivo: fastqa/scripts/regression-map.yaml
🗂️  Áreas: {N}
📄 Testes: {N} (E2E: {N}, API: {N}, Unit: {N})
📋 Features: {N}
🏷️  Tags: {N}

{tabela de áreas com contagens}

🤖 Iniciando Revisão Inteligente (AI Review)...
```

### 6️⃣ Revisão Inteligente (AI Review)

> **OBRIGATÓRIO** (a menos que o usuário passe `--no-ai-review`).
> Esta é a fase que transforma o YAML bruto gerado pelo script em um mapa
> de regressão pronto para uso, com áreas consolidadas, descrições claras
> e `app_patterns` baseados em paths reais do código.

**O agente IA DEVE executar as seguintes ações programaticamente:**

#### 6.1 — Carregar Contexto
1. **Ler** `fastqa/scripts/regression-map.yaml` (o YAML bruto do passo 4)
2. **Tentar ler** `fastqa/scripts/.enrichment-context.json` (gerado com `--enrich`):
   - Se o arquivo existir: usar como fonte principal de contexto (areas, patterns, gaps detectados pelo script)
   - **Se NÃO existir** (ex: `--enrich` não foi passado ou falhou): fazer discovery manual:
     - Usar `list_dir` em `routes/`, `models/`, `lib/`, `frontend/src/app/`, `data/` para mapear a estrutura
     - Usar `file_search` com patterns como `**/*Controller*`, `**/*Service*`, `**/*Route*` para encontrar artefatos chave
     - Montar o contexto de áreas a partir dos nomes de arquivo encontrados
3. **Explorar** a estrutura real da aplicação (complementar ao enrichment):
   - `list_dir` em `routes/`, `models/`, `lib/`, `frontend/src/app/`, `data/`
   - Identificar pastas de componentes, services, e arquivos de rota

#### 6.2 — Consolidar Áreas Semanticamente Equivalentes
Aplicar regras de fusão:

| Padrão | Ação |
|--------|------|
| Tags de `.feature` genéricas (`@logo`, `@responsive`, `@accessibility`, `@crossbrowser`, `@contato`) vindas do **mesmo arquivo .feature** | Fundir em uma única área temática (ex: `ui`) |
| Área `pbi-{N}` ou `us-{N}` (nomes de ticket) | Fundir na área funcional correspondente baseando-se nos testes/features |
| Áreas com mesmo nome no singular/plural | Manter singular |
| Áreas `rest-products-reviews` + `nosql` | Verificar se referem ao mesmo domínio e consolidar |
| Áreas `b2border` + `b2b-v2-order` | Fundir como `b2b-order` (mesmo spec) |

**Resultado:** Registrar num mapa `merges: Record<string, string[]>` as fusões feitas para rastrear.

#### 6.3 — Enriquecer app_patterns com Paths Reais
Para **cada área** do YAML:

1. **Buscar route handler:** Procurar em `routes/` um arquivo cujo nome contenha o nome da área.
   - Ex: área `login` → `routes/login.ts` ✓
   - Ex: área `changepassword` → `routes/changePassword.ts` ✓
   - Variações: kebab-case, camelCase, com/sem sufixos (Api, Items, etc.)

2. **Buscar model:** Procurar em `models/` um arquivo cujo nome contenha o nome da área.
   - Ex: área `basket` → `models/basket.ts`, `models/basketitem.ts` ✓

3. **Buscar componente Angular:** Procurar em `frontend/src/app/` uma pasta cujo nome contenha o nome da área.
   - Ex: área `login` → `frontend/src/app/login/**` ✓
   - Inclui padrão `/**` para cobrir component, module, spec.

4. **Buscar service:** Procurar em `frontend/src/app/Services/` um arquivo cujo nome contenha o nome da área.
   - Ex: área `basket` → `frontend/src/app/Services/basket.service.ts` ✓

5. **Buscar lib:** Procurar em `lib/` um arquivo cujo nome contenha o nome da área.
   - Ex: área `chatbot` → `lib/botUtils.ts` ✓

6. **Buscar data:** Procurar em `data/` pastas ou arquivos relacionados.
   - Ex: área `chatbot` → `data/chatbot/**` ✓

7. **Descartar patterns genéricos:** Remover qualquer `app_patterns` que seja apenas `**/{areaName}*` se patterns mais precisos foram encontrados.

8. **Manter patterns do script** que já são precisos (ex: `routes/login.ts` gerado pelo app-aware scan).

> **Regra:** Os `app_patterns` devem referenciar **arquivos e diretórios reais** do código da aplicação.
> Usar `list_dir` e `file_search` para confirmar existência antes de incluir.

#### 6.4 — Adicionar Descrições
Para cada área, gerar uma descrição concisa (1 linha) baseada em:
- Nome da área e contexto funcional
- Tipo de testes associados (E2E, API, unit)
- Função no sistema (autenticação, compra, admin, etc.)

Formato: `"Descrição curta da funcionalidade"` (sem `# TODO`)

#### 6.5 — Organizar em Seções Temáticas
Agrupar as áreas por domínio funcional usando comentários YAML:

```yaml
areas:
  # ═══════════════════════════════════════════════════════════════
  # AUTENTICAÇÃO & AUTORIZAÇÃO
  # ═══════════════════════════════════════════════════════════════
  login:
    ...
  register:
    ...

  # ═══════════════════════════════════════════════════════════════
  # PRODUTOS & COMPRAS
  # ═══════════════════════════════════════════════════════════════
  basket:
    ...
```

Seções sugeridas (adaptar conforme o projeto):
- Autenticação & Autorização
- Produtos & Compras
- Feedback & Reclamações
- Privacidade & Segurança do Usuário
- Perfil & Administração
- Challenges & Gamificação
- Segurança (Vulnerabilidades Intencionais)
- Chatbot & Comunicação
- Servidor & Infraestrutura
- UI / Testes Visuais (manual)
- GAPS (áreas sem cobertura)

#### 6.6 — Refinar global_triggers
Substituir triggers genéricos por paths reais de infraestrutura da aplicação:

1. **Manter** patterns universais: `**/.env*`, `**/Dockerfile*`, `**/docker-compose*`
2. **Adicionar** paths específicos da app detectados:
   - Entry points: `app.ts`, `server.ts`
   - Startup/bootstrap: `lib/startup/**`
   - Data layer core: `data/datacache.ts`, `data/datacreator.ts`, `data/staticData.ts`
   - Model registry: `models/index.ts`, `models/relations.ts`
   - Config: `**/config/**`
   - CI/CD: `.github/workflows/**`
   - Package deps: `package.json`
3. **Remover** triggers que não existem na aplicação

#### 6.7 — Reescrever regression-map.yaml
1. **Remover** o YAML bruto gerado pelo script
2. **Escrever** o YAML revisado com:
   - Cabeçalho com timestamp de revisão
   - Áreas organizadas por seções temáticas
   - Todos os `app_patterns` com paths reais
   - Todas as `description` preenchidas
   - `global_triggers` refinados
3. **Manter** metadados do script: `version`, `layers_used`
4. **Manter** campos gerados pelo script: `dependencies`, `dependents`, `shared`, `impact_scope`, `coverage`

### 7️⃣ Apresentar Resultado Revisado

```
✅ Regression Map Revisado (AI Review)

📄 Arquivo: fastqa/scripts/regression-map.yaml
🗂️  Áreas: {N_revisado} (de {N_bruto} bruto)
📄 Testes: {N}
🔄 Fusões realizadas: {N} (ex: logo+responsive+accessibility → ui)
📝 Descrições preenchidas: {N}/{N_total}
🎯 app_patterns com paths reais: {N}/{N_total}
🌐 Global triggers: {N}

{tabela resumida por seção temática}
```

### 8️⃣ Revisão Manual (Opcional)

```
💡 A IA já revisou e enriqueceu o mapa. Se desejar ajustes adicionais:
   📝 Edite fastqa/scripts/regression-map.yaml diretamente
   
   Itens que podem merecer atenção:
   - Áreas com poucos testes (cobertura parcial)
   - Gaps detectados (áreas da app sem testes)
   - app_patterns que podem ser refinados
```

### 9️⃣ Confirmar e Finalizar

```
📋 Próximos passos:
  1️⃣ Execute @fastqa:regression_analyze para testar o mapa com um PR real
  2️⃣ Re-execute este comando com --merge quando criar novos testes
```

---

## 🔄 Continuidade da Jornada

Após concluir este comando, siga as regras de continuidade:

1. **Leia** `fastqa/scripts/journey_state.json`
2. **Se `active_journey` não é null** (jornada ativa):
   - Marque o step atual como `"completed"`
   - Adicione artefatos: `scripts/regression-map.yaml`
   - Atualize `context` com: `areas_count`, `tests_mapped`, `ai_reviewed: true`
   - Grave o arquivo `journey_state.json`
   - **Fallback:** Se `journey_state.json` estiver malformado ou ausente, recriar com estado atual
3. **Se `active_journey` é null:**
   - Sugerir próximo passo: `@fastqa:regression_analyze` para testar o mapa com um PR real
