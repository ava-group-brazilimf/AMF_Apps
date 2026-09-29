---
name: testability-gaps-checklist
description: "Checklist de validação de testabilidade arquitetural para designs TO-BE. Detecta anti-patterns que impedem unit testing e integration testing efetivos."
version: "1.0.0"
applies_to: ["backend-dotnet", "frontend-angular"]
---

# Testability Gaps Checklist

> **Propósito**: Identificar barreiras arquiteturais à testabilidade antes da implementação. Usado pelo `ava-qa-gaps-requirements` para análise de `architecture-blueprint.md` e `solution-structure.md`.

---

## Backend — .NET Clean Architecture

### B1 — Controllers (Presentation Layer)

- [ ] 🔴 **Thin Controllers**: Controllers contêm apenas validação de entrada + orquestração de Commands/Queries
- [ ] 🔴 **Sem Lógica de Negócio**: Nenhuma regra de negócio implementada diretamente em controllers
- [ ] 🔴 **Mediator Pattern**: Se `architecture_patterns.mediator: MediatR` → controllers delegam via `IMediator.Send()`
- [ ] ⚠️ **Async/Await Consistente**: Todos os métodos de I/O usam `async Task<IActionResult>`
- [ ] ⚠️ **Dependency Injection**: Controllers recebem dependências via constructor injection (não service locator)

**Indicadores de Gap**:
- Controllers com mais de 50 linhas por action method
- Uso de `new()` dentro de action methods para criar serviços
- Lógica condicional complexa (`if/else` > 3 níveis) em controllers
- Acesso direto a `DbContext` ou repositories em controllers

---

### B2 — Application Layer

- [ ] 🔴 **CQRS Handlers Isolados**: Commands e Queries implementados como handlers separados
- [ ] 🔴 **Validation Pipeline**: FluentValidation configurado como pipeline behavior
- [ ] 🔴 **Sem Dependências Concretas**: Application layer depende apenas de interfaces (abstrações)
- [ ] 🔴 **Unit of Work**: Transações gerenciadas via `IUnitOfWork` (não commits manuais)
- [ ] ⚠️ **Testabilidade de Handlers**: Handlers podem ser testados com mocks de repositories
- [ ] ⚠️ **Result Pattern**: Handlers retornam `Result<T>` ou `ErrorOr<T>` (não exceptions para fluxo de negócio)

**Indicadores de Gap**:
- Handlers com `new DbContext()` ou `new Repository()`
- Application layer referenciando `Microsoft.EntityFrameworkCore` diretamente
- Falta de interfaces para repositories no Application layer
- Handlers com `try/catch` para lógica de negócio (não para exceções de infraestrutura)

---

### B3 — Domain Layer

- [ ] 🔴 **Zero Dependências Externas**: Domain layer é pure C# (nenhum pacote NuGet de infraestrutura)
- [ ] 🔴 **Entities com Encapsulation**: Setters privados, lógica em métodos públicos
- [ ] 🔴 **Value Objects Immutables**: VOs implementados como `record` ou com `init`-only properties
- [ ] 🔴 **Domain Events**: Eventos de domínio desacoplam agregados (não referências diretas)
- [ ] ⚠️ **Guard Clauses**: Validações de invariantes nos construtores e métodos de domínio
- [ ] ⚠️ **Testabilidade Pura**: Entities e VOs testáveis sem mocks (lógica pura)

**Indicadores de Gap**:
- Domain layer com referências a `System.Data`, `Microsoft.EntityFrameworkCore`, ou `Newtonsoft.Json`
- Entities com setters públicos sem validação
- Lógica de persistência ou I/O dentro de entities
- Dependências cíclicas entre agregados

---

### B4 — Infrastructure Layer

- [ ] 🔴 **Dependency Injection Setup**: Arquivo `DependencyInjection.cs` presente por bounded context
- [ ] 🔴 **Repository Implementations**: Repositories implementam interfaces definidas no Application/Domain
- [ ] 🔴 **DbContext Isolado**: `DbContext` usado apenas na Infrastructure layer
- [ ] 🔴 **Configuration via Options Pattern**: Settings carregados via `IOptions<T>` (não `ConfigurationManager` direto)
- [ ] ⚠️ **Testability de Repositories**: Repositories podem ser substituídos por in-memory implementations para testes
- [ ] ⚠️ **Connection Resiliency**: Polly configurado para retry/circuit breaker em acessos externos

**Indicadores de Gap**:
- Falta de `DependencyInjection.cs` em `Infrastructure` projects
- Repositories com lógica de negócio (além de CRUD + queries)
- `DbContext` exposto via singleton ou usado diretamente em Application layer
- Configurações hardcoded (não injetadas via `IOptions<T>`)

---

### B5 — Bounded Context Isolation

- [ ] 🔴 **Context Map Strategy Definida**: Strategy documentada em `bounded-context-map.md` (ACL, OHS, Conformist, Shared Kernel)
- [ ] 🔴 **Sem Referências Diretas entre BCs**: Bounded contexts não referenciam projetos de outros BCs diretamente
- [ ] 🔴 **Anti-Corruption Layer**: ACL implementado quando necessário (integração com sistemas legados ou BCs externos)
- [ ] ⚠️ **Eventos para Integração**: BCs se comunicam via domain events ou mensageria (não chamadas síncronas diretas)
- [ ] ⚠️ **Shared Kernel Mínimo**: Se usado, limitado a types primitivos ou VOs sem lógica

**Indicadores de Gap**:
- `<ProjectReference>` entre `BC-A.Application` e `BC-B.Application`
- Namespaces de um BC importados em outro BC
- Falta de strategy declarada em `bounded-context-map.md`
- Shared Kernel com entities ou services (deveria ser apenas VOs/DTOs)

---

### B6 — Testability Infrastructure

- [ ] 🔴 **Health Checks**: Endpoints `/health` e `/ready` implementados
- [ ] 🔴 **Structured Logging**: `ILogger<T>` usado (não `Console.WriteLine` ou `Debug.Log`)
- [ ] 🔴 **Test Projects**: Projetos `*.Tests` ou `*.IntegrationTests` definidos em `solution-structure.md`
- [ ] ⚠️ **Testcontainers**: Configuração para testes de integração com containers (SQL Server, Redis)
- [ ] ⚠️ **In-Memory Providers**: Alternativas in-memory configuradas para testes unitários

**Indicadores de Gap**:
- Ausência de health checks em `architecture-blueprint.md`
- Logging via `Console.WriteLine` ou sem structured data
- Falta de projetos de teste na solution structure
- Testes de integração acoplados a banco de dados de desenvolvimento

---

## Frontend — Angular 17+

### F1 — Component Architecture

- [ ] 🔴 **Smart/Dumb Pattern**: Components de página (`*-page.component`) acessam estado; child components apenas `@Input`/`@Output`
- [ ] 🔴 **Sem Lógica de Negócio**: Components contêm apenas apresentação (lógica delegada a Services)
- [ ] 🔴 **Reactive Forms Only**: Uso de `ReactiveFormsModule` (proibido `FormsModule` com `[(ngModel)]`)
- [ ] ⚠️ **Single Responsibility**: Components com < 150 linhas (excluindo templates inline)
- [ ] ⚠️ **OnPush Change Detection**: Components dumb usam `ChangeDetectionStrategy.OnPush`

**Indicadores de Gap**:
- Regras de validação ou cálculos complexos em `.component.ts`
- HTTP calls diretos em components (sem services)
- `[(ngModel)]` usado em formulários
- Components com múltiplas responsabilidades (ex: lista + form no mesmo component)

---

### F2 — State Management

- [ ] 🔴 **Pattern Testável Definido**: Se `architecture_patterns.frontend_state: ngrx` → Store configurado; se `signals` → Signal-based state
- [ ] 🔴 **Sem localStorage Direto**: Abstração (`StorageService`) para acesso a storage
- [ ] 🔴 **Immutability**: Estado nunca mutado diretamente (apenas via actions/signals)
- [ ] ⚠️ **Testability de State**: State pode ser testado isoladamente (sem DOM)
- [ ] ⚠️ **Seletores Puros**: Selectors/computed signals são funções puras (determinísticas)

**Indicadores de Gap**:
- `localStorage.setItem()` usado diretamente em components
- Estado global mutado via atribuição direta (`this.state.value = x`)
- Falta de definição de state management pattern em `architecture-blueprint.md`
- Seletores com side effects

---

### F3 — Service Layer

- [ ] 🔴 **Business Logic em Services**: Toda lógica de negócio isolada em `@Injectable()` services
- [ ] 🔴 **HTTP Abstraído**: Services encapsulam HTTP calls (components não conhecem `HttpClient`)
- [ ] 🔴 **Interface-based**: Services definem interfaces para facilitar mocking em testes
- [ ] ⚠️ **RxJS Operators**: Uso correto de operators (`switchMap`, `catchError`, `shareReplay`)
- [ ] ⚠️ **Error Handling**: Erros tratados via interceptors ou operators (não `try/catch` em components)

**Indicadores de Gap**:
- Components injetando `HttpClient` diretamente
- Lógica de transformação de dados em components (deveria estar em services)
- Services sem interfaces (dificulta mocking)
- Subscriptions sem unsubscribe (memory leaks)

---

### F4 — Dependency Injection

- [ ] 🔴 **Constructor Injection**: Services injetados via constructor (não property injection)
- [ ] 🔴 **ProvidedIn Root/Scope**: Services configurados com `providedIn` ou em module providers
- [ ] 🔴 **Sem Service Locator**: Código não usa `inject()` function no meio de métodos (apenas no constructor context)
- [ ] ⚠️ **Tree-shakeable**: Services standalone ou com `providedIn: 'root'` para otimização de bundle

**Indicadores de Gap**:
- Services instanciados com `new ServiceName()` em components
- Dependências obtidas via funções factory dentro de métodos
- Falta de configuração de DI em `architecture-blueprint.md`

---

### F5 — Testability

- [ ] 🔴 **Unit Tests**: Componentes e services têm arquivos `.spec.ts` correspondentes
- [ ] 🔴 **Mocking Strategy**: Uso de interfaces ou test doubles para isolar dependências
- [ ] 🔴 **No Side Effects em Constructors**: Constructors apenas atribuem dependências (não fazem HTTP calls)
- [ ] ⚠️ **Integration Tests**: E2E ou component tests com Playwright/Cypress configurados
- [ ] ⚠️ **Test Coverage Target**: `architecture_blueprint.md` define threshold (ex: >80% line coverage)

**Indicadores de Gap**:
- Arquivos `.spec.ts` ausentes em `solution-structure.md`
- HTTP calls iniciados em constructors (impedem testes isolados)
- Components com lógica que não pode ser testada sem DOM real
- Ausência de estratégia de testing em `architecture-blueprint.md`

---

## Cross-Cutting Concerns

### X1 — Observability

- [ ] 🔴 **Structured Logging**: Backend usa `ILogger<T>` com structured data; Frontend usa console com context
- [ ] 🔴 **Distributed Tracing**: OpenTelemetry ou Application Insights configurado (se `observability.tracing: true`)
- [ ] 🔴 **Health Checks**: Backend expõe `/health` e `/ready`; Frontend tem basic monitoring
- [ ] ⚠️ **Metrics**: Counters e gauges para operações críticas

**Indicadores de Gap**:
- Logging com string interpolation (não structured)
- Ausência de correlation IDs em logs distribuídos
- Falta de configuração de observability em `architecture-blueprint.md`

---

### X2 — Security & Compliance

- [ ] 🔴 **Auth/AuthZ Testável**: Policies e handlers de autorização isolados e testáveis
- [ ] 🔴 **Secrets Management**: Configuração via Azure Key Vault ou equivalente (não hardcoded)
- [ ] ⚠️ **PII Masking**: Se `tobe_compliance.lgpd: true` → masking configurado em logs

**Indicadores de Gap**:
- Connection strings hardcoded em `appsettings.json`
- Authorization logic inline em controllers (não em policies)
- Logs com PII não mascarado

---

## Resumo de Criticidade

| Símbolo | Severidade | Impacto | Ação |
|---------|-----------|---------|------|
| 🔴 | **BLOCKER** | Impede testes unitários e/ou integração efetivos | Redesign obrigatório antes de codegen |
| ⚠️ | **WARNING** | Reduz testabilidade mas não impede totalmente | Recomendação forte de correção |

---

## Instruções de Uso

1. **Input**: `architecture-blueprint.md`, `solution-structure.md`, `bounded-context-map.md`
2. **Processo**: Para cada item, verificar presença no design TO-BE
3. **Output**: Marcar `[x]` se atendido, `[ ]` se gap identificado
4. **Rastreabilidade**: Gaps 🔴 geram recomendações no `testability-gaps-report.md`

---

**Versão**: 1.0.0  
**Última atualização**: 2026-05-27  
**Mantido por**: AVA Fabric QA Team
