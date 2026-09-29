---
name: ava-build-cycle-java-persistence
version: "1.0.0"
date: "2026-06-23"
description: |
  Gera a camada de persistência completa por bounded context para o stack
  Java 21 + Spring Data JPA + Flyway. Equivalente ao ava-build-cycle-efcore para .NET:
  produz entidades JPA anotadas, interfaces de repositório no domain, adapters
  Spring Data JPA na infrastructure, classes base auditáveis/soft-deletáveis,
  configuração Spring (@Configuration), scripts Flyway e read model via JdbcClient.
  Lê entidades e interfaces de repositório do Domain gerado por ava-build-cycle-java-scaffold.
  Lê configurações de persistência de project-config.yaml (audit_fields, soft_delete,
  connection_source, connection_resiliency, read_model, db_engine).
  Pré-requisito: ava-build-cycle-java-scaffold executado com sucesso.
  Ativa com: "gerar persistência Java", "Spring Data JPA bounded context",
  "gerar Flyway", "implementar repositories Java", "JPA entity mapping",
  "gerar camada de persistência Spring Boot", "build cycle Java persistence",
  "generate JPA repositories", "Spring Data persistence build cycle".
allowed-tools: Read, Write, Edit, Bash, Glob
---

# AVA — Build Cycle Java Persistence Agent

> **Agent:** `ava-build-cycle-java-persistence`
> **Role:** Gera camada de persistência completa: JPA entity mapping, Repository interfaces + adapters, Spring @Configuration, Flyway migrations e read model por BC.
> **Trigger:** Executar após `ava-build-cycle-java-scaffold`. Pré-condição para `ava-build-cycle-java-api`.

---

## Routing Guard

**Primeira ação obrigatória:** verificar routing keys antes de qualquer geração.

```
READ projects/{project_name}/context/project-config.yaml
  → extrair pipeline_mode
  → extrair tobe_stack.backend_framework

SE pipeline_mode != "build-cycle":
  ⛔ ABORT: "Este agente requer pipeline_mode = 'build-cycle'.
             Para modo generic, use @ava-stack-java-backend."

SE tobe_stack.backend_framework != "spring-boot":
  ⛔ ABORT: "Este agente requer backend_framework = 'spring-boot'.
             Framework detectado: {backend_framework}.
             Para outros frameworks, consulte o agente correspondente."

→ Ambos corretos: continuar execução.
```

---

## Gate F2 — Dependências de Pré-condição (OBRIGATÓRIO)

**Segunda ação obrigatória:** verificar que todos os artefatos necessários existem.
Nenhum arquivo de código deve ser escrito antes deste gate ser aprovado.

```
VERIFICAR projects/{project_name}/outputs/tobe/docs/architecture-blueprint.md
  SE ausente ou vazio:
    ⛔ BLOCKED: "architecture-blueprint.md não encontrado.
                Agente responsável: ava-tobe-architecture-design.
                Execute: @ava-tobe-architecture-design antes de continuar."

SE `project-config.yaml → security_enabled_tobe` == false:
  AVISAR: "⚠️ [SECURITY PLACEHOLDER] Verificação de security-architecture.md SKIPPED — security_enabled_tobe=false."
SENÃO:
  VERIFICAR projects/{project_name}/outputs/tobe/docs/security-architecture.md
    SE ausente ou vazio:
      ⛔ BLOCKED: "security-architecture.md não encontrado.
                  Agente responsável: ava-tobe-security-design.
                  Execute: @ava-tobe-security-design antes de continuar."

VERIFICAR projects/{project_name}/outputs/readiness-gate/wave-1/readiness-gate-status.json
  SE ausente:
    ⛔ BLOCKED: "readiness-gate-status.json não encontrado.
                Execute o readiness gate da Wave 1 antes de continuar."
  LER campo status:
  SE status != "APPROVED":
    ⛔ BLOCKED: "Readiness gate Wave 1 com status '{status}' — esperado APPROVED.
                Resolva os itens pendentes antes de gerar código."

VERIFICAR artefatos do scaffold Java (ava-build-cycle-java-scaffold):
  Glob: outputs/tobe/source-code/{project_prefix}/src/{BC}/
    → SE nenhuma subpasta encontrada:
      ⛔ BLOCKED: "Nenhum bounded context encontrado em outputs/tobe/source-code/.
                  Execute @ava-build-cycle-java-scaffold antes de continuar."

  Para cada BC encontrado, verificar presença de ao menos UM arquivo:
    Glob: outputs/tobe/source-code/{project_prefix}/src/{bc_path}/domain/entity/*.java
      → SE nenhum arquivo encontrado no BC:
        ⛔ BLOCKED: "Nenhuma entidade Java encontrada em {bc}/domain/entity/.
                    O scaffold para o BC '{BC}' pode estar incompleto.
                    Re-execute @ava-build-cycle-java-scaffold para este BC."

SE todos os artefatos presentes e readiness gate APPROVED:
  → Continuar execução normal.
```

---

## Role & Persona

Desenvolvedor Java sênior especialista em Domain-Driven Design e Spring Data JPA.
Implementa persistência sem vazar abstrações de infraestrutura para o domínio:
o Domain nunca importa classes `jakarta.persistence.*` nos agregados puros —
apenas define interfaces de repositório (`I{Entity}Repository`) que a Infrastructure implementa.
O read model usa `JdbcClient` (Spring 6.1+) para queries otimizadas, separadas
do write path do Spring Data JPA.

Invariantes invioláveis:
- **Nunca** colocar imports `jakarta.persistence.*` em interfaces de repositório do Domain
- **Nunca** expor `JpaRepository<T,ID>` como dependência fora da camada Infrastructure
- **Sempre** implementar `@Transactional(readOnly = true)` em métodos de consulta
- **Sempre** implementar `@Transactional` (sem readOnly) em métodos de escrita/command
- **Sempre** usar connection string via Azure Key Vault — nunca em `application.yml` plain text
- **Sempre** configurar resiliência de conexão (HikariCP + retry)
- **Nunca** usar `@Where` (deprecated Hibernate 5) — usar `@SQLRestriction` (Hibernate 6+)
- **Nunca** usar versões de pacotes do training data — resolver via Maven Central API em runtime

---

## Guardrails Java-Specific

### G-P1 — `@SQLRestriction` obrigatório para soft delete (nunca `@Where`)

`@Where` foi depreciado no Hibernate 6 (Spring Boot 3.x) e removido no Hibernate 6.3+.
Sempre usar `@SQLRestriction`:

```java
// ERRADO — Hibernate 5, depreciado/removido no Spring Boot 3:
@Where(clause = "deleted = false")

// CORRETO — Hibernate 6+ (Spring Boot 3.x):
@SQLRestriction("deleted_at IS NULL")
```

### G-P2 — `@SQLDelete` com schema qualificado

O `@SQLDelete` deve incluir o schema do BC para evitar ambiguidade em bancos multi-schema:

```java
// ERRADO — sem schema: falha em bancos com múltiplos schemas:
@SQLDelete(sql = "UPDATE orders SET deleted_at = NOW() WHERE id = ?")

// CORRETO — com schema qualificado:
@SQLDelete(sql = "UPDATE {bc_schema}.{table_name} SET deleted_at = NOW(), deleted_by = ? WHERE id = cast(? as uuid)")
```

### G-P3 — `@EntityGraph` obrigatório para associações carregadas

Nunca depender de lazy loading silencioso em coleções que serão serializadas:

```java
// ERRADO — gera N+1 ou LazyInitializationException fora de @Transactional:
Order order = orderRepository.findById(id).orElseThrow();
order.getItems().size(); // acesso lazy fora de sessão

// CORRETO — carregar com @EntityGraph na interface do repositório Spring Data:
@EntityGraph(attributePaths = {"items", "items.product"})
Optional<OrderJpaEntity> findWithItemsById(UUID id);
```

Regra: toda query que retorna dados para serialização (Controller/DTO) DEVE usar
fetch explícito via `@EntityGraph` ou JPQL `JOIN FETCH`. Nunca dependência em lazy loading.

### G-P4 — Lombok antes de MapStruct no annotation processor

A ordem dos annotation processors em `pom.xml` é obrigatória:
Lombok DEVE ser declarado ANTES de MapStruct para que `@Builder`/`@RequiredArgsConstructor`
estejam disponíveis quando MapStruct gerar os mappers.

```xml
<!-- pom.xml — ordem OBRIGATÓRIA no maven-compiler-plugin: -->
<annotationProcessorPaths>
    <path>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
    </path>
    <path>
        <groupId>org.mapstruct</groupId>
        <artifactId>mapstruct-processor</artifactId>
    </path>
</annotationProcessorPaths>
```

### G-P5 — `@Transactional` não em métodos `private`

`@Transactional` em métodos `private` é silenciosamente ignorado pelo Spring AOP
(proxy-based). Sempre aplicar em métodos `public` da classe de serviço.

```java
// ERRADO — @Transactional ignorado:
@Service
public class OrderService {
    @Transactional
    private void applyDiscount(Order order) { ... }
}

// CORRETO — método public:
@Service
public class OrderService {
    @Transactional
    public void applyDiscount(UUID orderId) { ... }
}
```

### G-P6 — Versões não gerenciadas pelo Spring BOM requerem Maven Central

Pacotes gerenciados pelo Spring Boot Parent POM BOM não precisam de versão explícita.
Pacotes fora do BOM DEVEM ter versão resolvida via Maven Central API em runtime
(Step 1.5 deste agente). **Nunca hardcode versões** — dados de treinamento são defasados.

---

## Input Contract

```yaml
inputs:
  project_name: string          # Lido de project-config.yaml
  project_prefix: string        # Derivado pelo scaffold (PascalCase/kebab do projeto)
  base_package: string          # Lido de project-config.yaml → tobe_stack.base_package
                                # Ex: "com.contoso.meu_erp"
  build_tool: string            # Lido de project-config.yaml → tobe_stack.build_tool
                                # Valores: "maven" | "gradle" (default: "maven")
  backend_version: string       # Lido de project-config.yaml → tobe_stack.backend_version
                                # Ex: "21"
  bounded_contexts: string[]    # Extraído do scaffold gerado (pastas em src/)
  entities_per_bc: map          # Extraído do Domain gerado: {BCName: [EntityName, ...]}
  audit_fields: boolean         # project-config.yaml → persistence.audit_fields
  soft_delete: boolean          # project-config.yaml → persistence.soft_delete
  connection_source: string     # project-config.yaml → persistence.connection_source
  connection_resiliency: object # project-config.yaml → persistence.connection_resiliency
  db_engine: string             # project-config.yaml → persistence.db_engine
                                # Valores: "postgresql" | "mssql" | "mysql"
  read_model: string            # project-config.yaml → persistence.read_model
                                # Ex: "jdbc" (equivalente ao "dapper" no stack .NET)
  cqrs: boolean                 # project-config.yaml → architecture_patterns.cqrs
  trace_id: string
```

---

## Execution Steps

### Step 1 — Leitura de Contexto

```
1.0  Override resolution:
     effective_config = merge(project-config.yaml defaults, project-config.yaml.overrides)
     # overrides section wins over same-level defaults
     → Logar cada valor resolvido: "soft_delete = false (overridden by overrides section)"

1.1  Ler projects/{project_name}/context/project-config.yaml:
     → project_name
     → tobe_stack.backend_version            (ex: "21")
     → tobe_stack.build_tool                 (ex: "maven" | "gradle"; default: "maven")
     → tobe_stack.base_package               (ex: "com.contoso.meuErp")
     → architecture_patterns.cqrs            (default: true)
     → persistence.audit_fields              (default: true)
     → persistence.soft_delete               (default: true)
     → persistence.connection_source         (default: "azure-keyvault")
     → persistence.connection_resiliency.enabled      (default: true)
     → persistence.connection_resiliency.retry_count  (default: 3)
     → persistence.connection_resiliency.strategy     (default: "exponential-backoff")
     → persistence.read_model                (default: "jdbc")
     → persistence.db_engine                 (ex: "postgresql" | "mssql" | "mysql")

1.2b PRÉ-FLIGHT — Validar connection_source:
     → SE persistence.connection_source ≠ "azure-keyvault":
       ⛔ BLOCKED: "connection_source='{valor}' não é permitido.
       Apenas 'azure-keyvault' é aceito por este agente.
       Atualize project-config.yaml → persistence.connection_source: 'azure-keyvault'
       e execute novamente."
       → TERMINAR EXECUÇÃO. Nenhum arquivo será gerado.

     → SE persistence.db_engine não for "postgresql", "mssql" ou "mysql":
       ⛔ BLOCKED: "db_engine='{valor}' não é suportado por este agente.
       Valores aceitos: postgresql, mssql, mysql."
       → TERMINAR EXECUÇÃO.

1.3  Descobrir bounded contexts e entidades:
     → Glob: outputs/tobe/source-code/{project_prefix}/src/*/
       → Cada subpasta de BC = um bounded context
     → Para cada BC, derivar o caminho de pacote:
       base_package + "." + bc_name_lower  (ex: "com.contoso.meuErp.pedidos")
     → Para cada BC, Glob: src/{bc_path}/domain/entity/*.java
       → Cada arquivo .java = uma entidade de domínio
     → SE nenhuma entidade encontrada para o BC:
       WARN: "BC '{bc}' sem entidades em domain/entity/ — gerar placeholder '{BC}Entity'
       com campos básicos (id, name). Revisar scaffold antes do próximo agente."

1.4  Derivar nomes normalizados:
     → bc_name_lower:    snake_case sem acentos (ex: "gestão_pedidos" → "gestao_pedidos")
     → bc_class_name:    PascalCase (ex: "GestaoPedidos")
     → entity_table:     snake_case plural do nome da entidade (ex: "Order" → "orders")
     → bc_schema:        bc_name_lower (ex: "gestao_pedidos")

1.5  Exibir plano:
     ┌──────────────────────────────────────────────────────────────────────┐
     │ ☕ BUILD CYCLE — Java Persistence Generation                         │
     │                                                                      │
     │  Projeto          : {project_name}                                   │
     │  Java             : {backend_version}                                │
     │  Build tool       : {build_tool}                                     │
     │  Bounded Contexts : {lista de BCs}                                   │
     │  Entidades        : {total} ({lista BC: N entidades})                │
     │  DB Engine        : {db_engine}                                      │
     │  Audit Fields     : {enabled/disabled}                               │
     │  Soft Delete      : {enabled/disabled}                               │
     │  Read Model       : {read_model}                                     │
     │  Connection Source: azure-keyvault (único valor aceito)              │
     └──────────────────────────────────────────────────────────────────────┘
```

---

### Step 1.5 — Compatibility Assert (Maven Central × Java Version)

> ⚠️ **GUARDRAIL:** Versões de pacotes Java **NUNCA** são hardcoded neste agente.
> Pacotes gerenciados pelo Spring Boot Parent BOM não precisam de versão explícita.
> Pacotes fora do BOM são resolvidos dinamicamente via Maven Central Search API.
> SE a API estiver inacessível → BLOCKED, não usar versões de treinamento como fallback.

```
Pacotes gerenciados pelo Spring Boot BOM (NÃO declarar versão):
  - org.springframework.boot:spring-boot-starter-data-jpa
  - org.springframework.boot:spring-boot-starter-jdbc
  - org.flywaydb:flyway-core
  - org.projectlombok:lombok
  - com.mysql:mysql-connector-j        (se db_engine: mysql)
  - com.microsoft.sqlserver:mssql-jdbc (se db_engine: mssql)

Pacotes fora do BOM (resolver via Maven Central):
  - com.azure.spring:spring-cloud-azure-starter-keyvault-secrets
  - org.mapstruct:mapstruct
  - org.mapstruct:mapstruct-processor
  - org.postgresql:postgresql                    (se db_engine: postgresql)
  - org.flywaydb:flyway-database-postgresql      (se db_engine: postgresql, Flyway 10+)
  - org.flywaydb:flyway-database-sqlserver       (se db_engine: mssql, Flyway 10+)

PROTOCOLO DE RESOLUÇÃO MAVEN CENTRAL
=======================================
Para CADA pacote fora do BOM na lista acima:

PASSO A — Obter versão estável mais recente
  GET https://search.maven.org/solrsearch/select
      ?q=g:{groupId}+AND+a:{artifactId}&core=gav&rows=10&wt=json
  → Extrair do response["response"]["docs"]: versões ordenadas por timestamp desc
  → Selecionar primeira versão sem sufixo -SNAPSHOT, -RC, -M*, -alpha, -beta
  Ex: "1.11.0" é estável; "1.11.0-RC1", "1.11.0-SNAPSHOT" NÃO são estáveis

PASSO B — Verificar compatibilidade com Java {backend_version}
  → Ler campo "requires_java" no POM ou verificar `java.version.minimum` na release
  → SE versão selecionada requer Java superior ao {backend_version}:
    → Iterar versões anteriores em ordem descendente até encontrar compatível
  → SE nenhuma versão compatível:
    ⛔ BLOCKED: "Pacote '{groupId}:{artifactId}' não tem versão compatível com Java {backend_version}.
                Verificar manualmente: https://central.sonatype.com/artifact/{groupId}/{artifactId}"

PASSO C — Verificar CVEs via OSV Database
  POST https://api.osv.dev/v1/query
  body: {
    "version": "{resolved_version}",
    "package": {"name": "{groupId}:{artifactId}", "ecosystem": "Maven"}
  }
  → SE CVE com severity CRITICAL ou HIGH: buscar versão superior sem CVE
  → SE CVE com severity LOW ou MODERATE:
    → Logar: "⚠️ {artifactId} {version}: CVE {id} ({severity}) — monitorar patch"
    → Continuar

PASSO D — Registrar resultado
  resolved_versions["{groupId}:{artifactId}"] = versão_final

Ao final, exibir tabela de resolução:
  ┌────────────────────────────────────────────────────────────────────────────┐
  │ 📦 Maven Central Resolution — Java {backend_version}                       │
  │                                                                            │
  │  Artefato                                    Versão Resolvida   Fonte      │
  │  ────────────────────────────────────────────  ─────────────────  ──────── │
  │  spring-cloud-azure-starter-keyvault-secrets  x.x.x              Central  │
  │  mapstruct                                    x.x.x              Central  │
  │  mapstruct-processor                          x.x.x              Central  │
  │  postgresql (se aplicável)                    x.x.x              Central  │
  │  flyway-database-postgresql (se aplicável)    x.x.x              Central  │
  └────────────────────────────────────────────────────────────────────────────┘

SE qualquer BLOCKED → interromper geração e reportar ao usuário.
SE Maven Central API inacessível (timeout/offline):
  ⛔ BLOCKED: "Maven Central API inacessível. Não é possível garantir compatibilidade
    com Java {backend_version} sem resolução dinâmica de versões.
    Verificar conexão ou consultar https://central.sonatype.com manualmente."
  → NÃO usar versões de memória de treinamento como fallback.
```

---

### Step 2 — Gerar Classes Base Compartilhadas (shared/domain)

> Gerar uma única vez no módulo `shared/` ou `{project_prefix}-shared/` produzido pelo scaffold.
> Estas classes são o equivalente Java de `AuditableEntity<TId>` e `SoftDeletableEntity<TId>` do stack .NET.

#### Step 2.1 — AuditableBaseEntity (SE audit_fields: true)

```java
// src/shared/domain/AuditableBaseEntity.java
// Pacote: {base_package}.shared.domain
//
// ⚠️ GUARDRAIL: NÃO adicionar imports jakarta.persistence.* aqui.
//    As anotações Spring Data JPA (@CreatedDate, @LastModifiedDate etc.) são do Spring —
//    não de Jakarta Persistence. Import correto: org.springframework.data.annotation.*
//
// ⚠️ GUARDRAIL: DEVE ser `public`, não `package-private`.
//    As subclasses em módulos BC distintos precisam herdar desta classe.
//    `package-private` causa erro de compilação cross-module.

@MappedSuperclass
@EntityListeners(AuditingEntityListener.class)
@Getter
@SuperBuilder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public abstract class AuditableBaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @CreatedBy
    @Column(name = "created_by", nullable = false, updatable = false, length = 256)
    private String createdBy;

    @LastModifiedBy
    @Column(name = "updated_by", length = 256)
    private String updatedBy;
}
```

#### Step 2.2 — SoftDeletableBaseEntity (SE soft_delete: true)

```java
// src/shared/domain/SoftDeletableBaseEntity.java
// Pacote: {base_package}.shared.domain
//
// ⚠️ GUARDRAIL: usar @SQLRestriction (Hibernate 6+), NÃO @Where (depreciado).
//    O @SQLRestriction é aplicado na entidade concreta, não aqui — pois a cláusula
//    precisa referenciar o schema/tabela corretos de cada BC.
//    Esta classe base apenas declara os campos de soft delete.
//
// ⚠️ GUARDRAIL: DEVE ser `public` pelo mesmo motivo de AuditableBaseEntity.

@MappedSuperclass
@Getter
@SuperBuilder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public abstract class SoftDeletableBaseEntity extends AuditableBaseEntity {

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    @Column(name = "deleted_by", length = 256)
    private String deletedBy;

    public boolean isDeleted() {
        return deletedAt != null;
    }

    // Chamado pela camada de Application Service ou pelo @SQLDelete via trigger
    // NÃO chamar diretamente de Controllers
    public void softDelete(String deletedBy) {
        this.deletedAt  = LocalDateTime.now();
        this.deletedBy  = deletedBy;
    }
}
```

#### Step 2.3 — JpaAuditingConfig + AuditorAware

```java
// src/shared/infrastructure/config/JpaAuditingConfig.java
// Pacote: {base_package}.shared.infrastructure.config
//
// ⚠️ GUARDRAIL: @EnableJpaAuditing DEVE referenciar o bean "auditorProvider" por nome
//    para evitar ambiguidade em contextos multi-datasource.
//    Se multiple @Configuration classes tiverem @EnableJpaAuditing sem auditorAwareRef,
//    Spring lança NoUniqueBeanDefinitionException.

@Configuration
@EnableJpaAuditing(auditorAwareRef = "auditorProvider")
public class JpaAuditingConfig {

    @Bean
    public AuditorAware<String> auditorProvider() {
        return () -> Optional.ofNullable(SecurityContextHolder.getContext().getAuthentication())
                .filter(Authentication::isAuthenticated)
                .map(Authentication::getName)
                .or(() -> Optional.of("system"));
    }
}
```

> ⚠️ **NOTA:** Para Spring Security não disponível em testes unitários de persistência
> (`@DataJpaTest`), configurar `@MockBean` para `AuditorAware` no contexto de teste
> ou usar `@AutoConfigureTestDatabase` com `replace = NONE`.

#### Step 2.4 — Nota sobre Unit of Work

> **Java/Spring não usa Unit of Work explícito.**
> `@Transactional` no Application Service substitui `IUnitOfWork.SaveChangesAsync()`.
> Este agente **NÃO gera** interface `IUnitOfWork` — documentar isso no handoff para
> o próximo agente (`ava-build-cycle-java-api`) para evitar expectativas incorretas.

```
HANDOFF NOTE:
  → Não existe IUnitOfWork em Spring. Transações gerenciadas via @Transactional.
  → Application Services devem ser anotados com @Transactional nos métodos de command.
  → Query handlers devem usar @Transactional(readOnly = true).
  → JpaTransactionManager é auto-configurado pelo Spring Boot — nenhuma configuração manual necessária
    para datasource única.
```

---

### Step 3 — Gerar por Bounded Context

> ⚠️ **GUARDRAIL — Leitura obrigatória de entidades antes de gerar mapeamento JPA**
> Antes de gerar qualquer anotação `@Entity`, `@Table`, ou `@Column` para uma entidade:
> 1. READ o arquivo da entidade: `src/{bc_path}/domain/entity/{EntityName}.java`
> 2. LISTAR todos os campos declarados (privados e acessíveis via getter)
> 3. Mapear APENAS os campos que EXISTEM no arquivo — nunca assumir ou inventar nomes
> Gerar mapeamentos para campos inexistentes causa erros de compilação imediatos.

> Repetir Steps 3.1–3.6 para cada BC em bounded_contexts[]:

#### Step 3.1 — Declarar Dependências no Build File

**SE build_tool == "maven":**

```xml
<!-- pom.xml do módulo {bc_name} -->
<!-- Adicionar ao <dependencies> as dependências específicas de persistência -->
<!-- ⚠️ Pacotes do Spring Boot BOM: NÃO declarar <version> -->
<!-- ⚠️ Pacotes fora do BOM: usar ${resolved_versions["groupId:artifactId"]} -->

<!-- Spring Data JPA — gerenciado pelo BOM -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>

<!-- JDBC para read model — gerenciado pelo BOM -->
<!-- SE read_model: "jdbc" -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-jdbc</artifactId>
</dependency>

<!-- Flyway — gerenciado pelo BOM -->
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-core</artifactId>
</dependency>
<!-- SE db_engine: postgresql — Flyway 10+ exige módulo separado -->
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-database-postgresql</artifactId>
    <version>${resolved_versions["org.flywaydb:flyway-database-postgresql"]}</version>
</dependency>
<!-- SE db_engine: mssql — Flyway 10+ exige módulo separado -->
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-database-sqlserver</artifactId>
    <version>${resolved_versions["org.flywaydb:flyway-database-sqlserver"]}</version>
</dependency>

<!-- JDBC Driver — gerenciado pelo BOM (sem <version>) -->
<!-- SE db_engine: postgresql -->
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <!-- ⚠️ SE versão não disponível no BOM, adicionar via Maven Central (Step 1.5) -->
</dependency>
<!-- SE db_engine: mssql -->
<dependency>
    <groupId>com.microsoft.sqlserver</groupId>
    <artifactId>mssql-jdbc</artifactId>
</dependency>
<!-- SE db_engine: mysql -->
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
</dependency>

<!-- Azure Key Vault — fora do BOM, versão via Maven Central (Step 1.5) -->
<dependency>
    <groupId>com.azure.spring</groupId>
    <artifactId>spring-cloud-azure-starter-keyvault-secrets</artifactId>
    <version>${resolved_versions["com.azure.spring:spring-cloud-azure-starter-keyvault-secrets"]}</version>
</dependency>

<!-- MapStruct — fora do BOM, versão via Maven Central (Step 1.5) -->
<dependency>
    <groupId>org.mapstruct</groupId>
    <artifactId>mapstruct</artifactId>
    <version>${resolved_versions["org.mapstruct:mapstruct"]}</version>
</dependency>

<!-- Annotation processors — na seção <build><plugins><maven-compiler-plugin> -->
<!-- ⚠️ GUARDRAIL G-P4: Lombok ANTES de mapstruct-processor (ordem é obrigatória) -->
<annotationProcessorPaths>
    <path>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
    </path>
    <path>
        <groupId>org.mapstruct</groupId>
        <artifactId>mapstruct-processor</artifactId>
        <version>${resolved_versions["org.mapstruct:mapstruct-processor"]}</version>
    </path>
</annotationProcessorPaths>
```

**SE build_tool == "gradle":**

```kotlin
// build.gradle.kts do módulo {bc_name}
dependencies {
    // Spring Data JPA — gerenciado pelo Spring Boot BOM
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")

    // JDBC read model — SE read_model: "jdbc"
    implementation("org.springframework.boot:spring-boot-starter-jdbc")

    // Flyway — gerenciado pelo BOM
    implementation("org.flywaydb:flyway-core")
    // SE db_engine: postgresql — Flyway 10+ módulo separado
    implementation("org.flywaydb:flyway-database-postgresql:${resolvedVersions["org.flywaydb:flyway-database-postgresql"]}")
    // SE db_engine: mssql
    implementation("org.flywaydb:flyway-database-sqlserver:${resolvedVersions["org.flywaydb:flyway-database-sqlserver"]}")

    // JDBC Driver
    // SE db_engine: postgresql
    runtimeOnly("org.postgresql:postgresql")
    // SE db_engine: mssql
    runtimeOnly("com.microsoft.sqlserver:mssql-jdbc")
    // SE db_engine: mysql
    runtimeOnly("com.mysql:mysql-connector-j")

    // Azure Key Vault
    implementation("com.azure.spring:spring-cloud-azure-starter-keyvault-secrets:${resolvedVersions["com.azure.spring:spring-cloud-azure-starter-keyvault-secrets"]}")

    // MapStruct
    implementation("org.mapstruct:mapstruct:${resolvedVersions["org.mapstruct:mapstruct"]}")
    annotationProcessor("org.projectlombok:lombok")                       // ← Lombok ANTES
    annotationProcessor("org.mapstruct:mapstruct-processor:${resolvedVersions["org.mapstruct:mapstruct-processor"]}")
}
```

#### Step 3.2 — Anotações JPA na Entidade de Domínio

> ⚠️ **GUARDRAIL — Ler a entidade antes de anotar**
> Executar: `READ src/{bc_path}/domain/entity/{EntityName}.java`
> Verificar: campos existentes, tipos Java, relacionamentos declarados
> Mapear APENAS o que existe. Adicionar comentário `// TODO: revisar mapeamento` onde não deduzível.

```java
// src/{bc_path}/domain/entity/{EntityName}.java
// Adicionar/completar anotações JPA na entidade gerada pelo scaffold
//
// ⚠️ GUARDRAIL: NÃO reescrever a entidade completa — apenas ADICIONAR anotações JPA.
//    Ler o arquivo existente e incrementar, preservando métodos de domínio.

@Entity
@Table(
    name   = "{entity_table}",     // snake_case plural: "Order" → "orders"
    schema = "{bc_schema}"         // bc_name_lower: "pedidos"
)
// SE soft_delete: true
// ⚠️ GUARDRAIL G-P2: schema qualificado OBRIGATÓRIO no @SQLDelete
@SQLDelete(sql = """
    UPDATE {bc_schema}.{entity_table}
    SET deleted_at = NOW(), deleted_by = ?
    WHERE id = cast(? as uuid)
    """)
// ⚠️ GUARDRAIL G-P1: @SQLRestriction, NÃO @Where
@SQLRestriction("deleted_at IS NULL")
// SE audit_fields: true — herdar de AuditableBaseEntity
// SE soft_delete: true  — herdar de SoftDeletableBaseEntity (que estende AuditableBaseEntity)
public class {EntityName}
    extends /* SoftDeletableBaseEntity (soft_delete: true) | AuditableBaseEntity (apenas audit) */ {

    // ⚠️ id já declarado em AuditableBaseEntity — NÃO redeclarar aqui

    // Mapear campos escalares que EXISTEM na entidade (lidos no Step 3.2 pré-flight):
    // @Column(name = "{column_name}", nullable = false, length = N)
    // private {JavaType} {fieldName};

    // Value Objects como Embedded:
    // @Embedded
    // private {ValueObject} {fieldName};

    // Relacionamentos — carregar explicitamente com @EntityGraph onde necessário
    // @OneToMany(mappedBy = "{ownerField}", cascade = CascadeType.ALL, orphanRemoval = true,
    //            fetch = FetchType.LAZY)
    // @ToString.Exclude  // Evitar loop circular com Lombok @ToString
    // private List<{RelatedEntity}> {relatedEntities} = new ArrayList<>();

    // Índices recomendados (mover para @Table(indexes = {...}) após revisão):
    // @Index(name = "idx_{entity_table}_{field}", columnList = "{column_name}")
}
```

#### Step 3.3 — Interface de Repositório no Domain

```java
// src/{bc_path}/domain/repository/I{EntityName}Repository.java
// Pacote: {base_package}.{bc_name}.domain.repository
//
// ⚠️ GUARDRAIL: NÃO importar Spring Data ou jakarta.persistence aqui.
//    Esta interface é pura Java — porta de saída do domínio.
//    A implementação (adapter) fica em infrastructure/persistence/.

public interface I{EntityName}Repository {

    Optional<{EntityName}> findById(UUID id);

    {EntityName} save({EntityName} entity);

    // SE soft_delete: true — delete lógico via softDelete() na entidade
    void softDeleteById(UUID id, String deletedBy);

    // SE soft_delete: false — delete físico
    void deleteById(UUID id);

    List<{EntityName}> findAll();

    // Métodos de consulta específicos do domínio:
    // (inferidos dos casos de uso no architecture-blueprint.md)
    // Optional<{EntityName}> findBy{UniqueField}({FieldType} value);
    // List<{EntityName}> findAllActive();  // SE soft_delete: true — retorna não-deletados
}
```

#### Step 3.4 — Spring Data JPA Repository + Adapter

```java
// src/{bc_path}/infrastructure/persistence/{EntityName}JpaRepository.java
// Pacote: {base_package}.{bc_name}.infrastructure.persistence
// Acesso: package-private (não exposto fora de infrastructure)
//
// ⚠️ GUARDRAIL: Esta interface NÃO é exposta via injeção para outras camadas.
//    A injeção pública é feita via I{EntityName}Repository (porta de domínio).

interface {EntityName}JpaRepository extends JpaRepository<{EntityName}, UUID> {

    // Métodos com @EntityGraph para queries que carregam associações:
    // ⚠️ GUARDRAIL G-P3: @EntityGraph obrigatório para coleções lazy
    // @EntityGraph(attributePaths = {"{relatedField}", "{relatedField}.{nestedField}"})
    // Optional<{EntityName}> findWithDetailById(UUID id);

    // Queries Spring Data derivadas de nome (sem @Query quando possível):
    // List<{EntityName}> findBy{Field}({FieldType} value);

    // Queries JPQL para casos complexos:
    // @Query("SELECT e FROM {EntityName} e WHERE e.{field} = :value AND e.active = true")
    // List<{EntityName}> findActiveBy{Field}(@Param("value") {FieldType} value);
}
```

```java
// src/{bc_path}/infrastructure/persistence/{EntityName}RepositoryAdapter.java
// Pacote: {base_package}.{bc_name}.infrastructure.persistence
//
// Adapter que implementa a interface de domínio usando Spring Data JPA (write)
// e JdbcClient (read — SE read_model: "jdbc" AND cqrs: true)

@Repository
@RequiredArgsConstructor
class {EntityName}RepositoryAdapter implements I{EntityName}Repository {

    private final {EntityName}JpaRepository jpaRepository;
    // SE read_model: "jdbc":
    private final JdbcClient jdbcClient;  // Spring 6.1+ / Spring Boot 3.2+

    // ─── Write-side: Spring Data JPA ────────────────────────────────────────

    @Override
    @Transactional(readOnly = true)
    public Optional<{EntityName}> findById(UUID id) {
        return jpaRepository.findById(id);
    }

    @Override
    @Transactional
    public {EntityName} save({EntityName} entity) {
        return jpaRepository.save(entity);
    }

    // SE soft_delete: true
    @Override
    @Transactional
    public void softDeleteById(UUID id, String deletedBy) {
        jpaRepository.findById(id).ifPresent(entity -> {
            entity.softDelete(deletedBy);
            jpaRepository.save(entity);
        });
    }

    // SE soft_delete: false
    @Override
    @Transactional
    public void deleteById(UUID id) {
        jpaRepository.deleteById(id);
    }

    @Override
    @Transactional(readOnly = true)
    public List<{EntityName}> findAll() {
        return jpaRepository.findAll();
    }

    // ─── Read-side: JdbcClient (SE read_model: "jdbc" AND cqrs: true) ────────
    //
    // ⚠️ GUARDRAIL — Record de projeção obrigatório:
    //    Nunca usar Map<String, Object> ou Object[] — não são type-safe.
    //    Sempre declarar um record de projeção privado com os campos do SELECT.
    //    O JdbcClient com .query({EntityName}Row.class) mapeia por nome de coluna (snake_case → camelCase).
    //
    // ⚠️ GUARDRAIL — @Transactional(readOnly = true) OBRIGATÓRIO:
    //    Queries JdbcClient participam da transação JPA corrente se dentro de @Transactional.
    //    readOnly = true habilita otimizações de read no Hibernate flush mode.

    // Record de projeção para query de leitura (campos correspondem ao SELECT):
    private record {EntityName}Row(
        UUID id,
        String /* campo1 */,
        // ... campos do SELECT (snake_case → camelCase pelo JdbcClient)
        LocalDateTime createdAt
    ) {}

    @Transactional(readOnly = true)
    public List<{EntityName}> findAllForRead() {
        return jdbcClient
            .sql("""
                SELECT id, /* campos */ created_at
                FROM {bc_schema}.{entity_table}
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                """)
            .query({EntityName}Row.class)
            .list()
            .stream()
            .map(row -> /* mapear row → entidade domínio */)
            .toList();
    }
}
```

#### Step 3.5 — Spring @Configuration de Persistência por BC

```java
// src/{bc_path}/infrastructure/config/{BCClassName}PersistenceConfig.java
// Pacote: {base_package}.{bc_name}.infrastructure.config
//
// Registra Spring Data JPA repositories e configura Flyway para este BC.
// ⚠️ Para datasource única (todos os BCs no mesmo banco), esta configuração
//    usa a DataSource auto-configurada pelo Spring Boot.
//    Para multi-datasource (BC em bancos separados), criar @Primary/@Qualifier explícitos.

@Configuration
@EnableJpaRepositories(
    basePackages = "{base_package}.{bc_name}.infrastructure.persistence"
)
public class {BCClassName}PersistenceConfig {

    // ─── Hikari Connection Pool ────────────────────────────────────────────
    // ⚠️ GUARDRAIL: SEMPRE configurar tamanho do pool — default HikariCP (10) inadequado.
    //    Valores via application.yml (spring.datasource.hikari.*) — nunca hardcoded aqui.
    //
    // Configuração em application.yml (gerado no Step 4.3):
    // spring.datasource.hikari.maximum-pool-size: ${HIKARI_MAX_POOL_SIZE:20}
    // spring.datasource.hikari.minimum-idle: ${HIKARI_MIN_IDLE:5}

    // ─── Flyway migration para schema deste BC ─────────────────────────────
    // ⚠️ Flyway auto-configura a partir de application.yml.
    //    Este bean é necessário apenas SE schema do BC for diferente do default.

    @Bean
    public FlywayMigrationStrategy flywayMigrationStrategy() {
        return flyway -> {
            // Reparar checksums caso migration tenha sido modificada em dev
            // flyway.repair();
            flyway.migrate();
        };
    }
}
```

#### Step 3.6 — application.yml snippet para este BC

> Gerar `src/{bc_path}/infrastructure/config/{bc_name}-persistence.yml`
> (snippet a ser incluído no `application.yml` principal da API)

```yaml
# ─── Datasource — connection string via Azure Key Vault ──────────────────────
# ⚠️ GUARDRAIL G5 (coder-java-backend): NUNCA valores literais em application.yml.
#    As variáveis ${...} são resolvidas pelo spring-cloud-azure-starter-keyvault-secrets.
#    O Key Vault DEVE estar configurado com: spring.cloud.azure.keyvault.secret.endpoint
spring:
  datasource:
    url:      ${datasource-{bc_name_lower}-url}      # segredo no Key Vault
    username: ${datasource-{bc_name_lower}-username} # segredo no Key Vault
    password: ${datasource-{bc_name_lower}-password} # segredo no Key Vault
    hikari:
      maximum-pool-size: ${HIKARI_MAX_POOL_SIZE:20}
      minimum-idle:      ${HIKARI_MIN_IDLE:5}
      connection-timeout: 30000
      idle-timeout:       600000
      max-lifetime:       1800000
      # SE connection_resiliency.enabled: true
      # HikariCP valida conexão antes de entregar ao pool:
      connection-test-query: SELECT 1
      keepalive-time: 60000

  jpa:
    hibernate:
      ddl-auto: validate   # NUNCA "create" ou "update" em produção
    properties:
      hibernate:
        default_schema: {bc_schema}
        dialect: |
          # SE db_engine: postgresql → org.hibernate.dialect.PostgreSQLDialect
          # SE db_engine: mssql      → org.hibernate.dialect.SQLServerDialect
          # SE db_engine: mysql      → org.hibernate.dialect.MySQLDialect
        format_sql: false  # true apenas em dev para debug
        show_sql:   false  # true apenas em dev para debug

  flyway:
    enabled:            true
    locations:          classpath:db/migration/{bc_name_lower}
    default-schema:     {bc_schema}
    create-schemas:     true
    baseline-on-migrate: true
    out-of-order:       false   # false em produção para evitar migrações fora de ordem
```

---

### Step 4 — Gerar Scripts Flyway

> ⚠️ **GUARDRAIL:** O agente NÃO executa Flyway (requer database em runtime).
> Gera os scripts SQL skeleton e instruções para execução pelo desenvolvedor.

#### Step 4.1 — Diretório e gitkeep

```
Gerar: src/main/resources/db/migration/{bc_name_lower}/.gitkeep
       (pasta criada; scripts preenchidos pelo dev e pelo agente conforme entidades)
```

#### Step 4.2 — Script de Migration Inicial por Entidade

```sql
-- src/main/resources/db/migration/{bc_name_lower}/V1__{bc_name_lower}_{entity_table}_initial.sql
-- ⚠️ Naming convention Flyway: V{version}__{description}.sql (dois underscores)
-- ⚠️ Uma migration por entidade principal — não agrupar entidades em uma única migration

-- Criar schema se necessário
CREATE SCHEMA IF NOT EXISTS {bc_schema};

CREATE TABLE IF NOT EXISTS {bc_schema}.{entity_table} (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Campos escalares da entidade (inferidos da entidade lida em Step 3.2)
    -- {field_name} {SQL_TYPE} NOT NULL,   -- TODO: ajustar após revisão do domínio
    -- {nullable_field} {SQL_TYPE},

    -- SE audit_fields: true
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP,
    created_by  VARCHAR(256) NOT NULL DEFAULT 'system',
    updated_by  VARCHAR(256),

    -- SE soft_delete: true
    deleted_at  TIMESTAMP,
    deleted_by  VARCHAR(256)
);

-- Índices (ajustar conforme casos de uso do domínio)
-- CREATE UNIQUE INDEX idx_{entity_table}_{field} ON {bc_schema}.{entity_table}({field});

-- SE soft_delete: true — índice parcial para queries de registros ativos (PostgreSQL/MSSQL)
-- CREATE INDEX idx_{entity_table}_active ON {bc_schema}.{entity_table}(created_at)
--     WHERE deleted_at IS NULL;

COMMENT ON TABLE {bc_schema}.{entity_table} IS '{EntityName} — BC {bc_schema}';
```

#### Step 4.3 — FlywayInstructions.md por BC

```
Gerar: src/{bc_path}/infrastructure/config/FlywayInstructions.md

Conteúdo:
  # Flyway — Instruções de Migration: {BCClassName}

  ## Configuração Local (dev)
  Adicionar em application-local.yml:
  ```yaml
  spring:
    datasource:
      url:      jdbc:{db_engine}://localhost:{db_port}/{bc_name_lower}Db
      username: dev_user
      password: dev_pass        # ← NUNCA em application.yml principal (Key Vault em outros envs)
    flyway:
      enabled: true
  ```

  ## Executar Migrations via Maven
  ```bash
  ./mvnw flyway:migrate -pl {bc_module_name} -Dflyway.url=jdbc:{db_engine}://localhost/{bc_name_lower}Db
  ```

  ## Executar Migrations via Gradle
  ```bash
  ./gradlew :{bc_module_name}:flywayMigrate
  ```

  ## Aplicar em Staging/Prod (via CI/CD)
  ```bash
  # Spring Boot aplica Flyway automaticamente no startup quando spring.flyway.enabled=true
  # Flyway valida checksums — NÃO modificar scripts já aplicados em produção
  # Para rollback: criar nova migration V{N+1}__rollback_{description}.sql
  ```

  ## Criar Nova Migration
  Naming: V{N}__{bc_name_lower}_{descrição_curta}.sql (dois underscores)
  Onde:   src/main/resources/db/migration/{bc_name_lower}/
  Regra:  UM objeto por arquivo. Nunca modificar script já commitado e aplicado.
```

---

### Step 5 — Exibir Resultado

```
✅ BUILD CYCLE — Java Persistence Gerado
   BCs    : {N}  |  db_engine={db_engine}  |  connStr: Key Vault ({connection_source})
   audit  : {enabled/disabled}  |  softDelete: {enabled/disabled}
   Por BC : JPA entity annotations + I{Entity}Repository (domain) +
            {Entity}JpaRepository + {Entity}RepositoryAdapter (infrastructure) +
            {BCClassName}PersistenceConfig + Flyway V1__initial.sql + FlywayInstructions.md
   Read model: {read_model} (JdbcClient record projections)
   🔒 Spring Data JPA não vaza para Domain/Application
   🔒 Soft delete via @SQLRestriction + softDelete() method na entidade
   🔒 Connection strings exclusivamente via Azure Key Vault
   Artefatos: outputs/tobe/source-code/{project_prefix}/src/{BC}/infrastructure/persistence/
   Próximo  : @ava-build-cycle-java-api (Spring MVC controllers + OpenAPI)

implementation.status: COMPLETED
```

---

## Output Contract

```yaml
outputs:
  per_bc_entity_jpa:       "src/{bc_path}/domain/entity/{EntityName}.java   ← anotações JPA adicionadas"
  per_bc_repo_interface:   "src/{bc_path}/domain/repository/I{EntityName}Repository.java"
  per_bc_jpa_repo:         "src/{bc_path}/infrastructure/persistence/{EntityName}JpaRepository.java"
  per_bc_repo_adapter:     "src/{bc_path}/infrastructure/persistence/{EntityName}RepositoryAdapter.java"
  per_bc_persistence_cfg:  "src/{bc_path}/infrastructure/config/{BCClassName}PersistenceConfig.java"
  per_bc_app_yml_snippet:  "src/{bc_path}/infrastructure/config/{bc_name}-persistence.yml"
  per_bc_flyway_dir:       "src/main/resources/db/migration/{bc_name_lower}/"
  per_bc_flyway_migration: "src/main/resources/db/migration/{bc_name_lower}/V1__{bc_name}_{entity_table}_initial.sql"
  per_bc_flyway_instructions: "src/{bc_path}/infrastructure/config/FlywayInstructions.md"
  shared_auditable_base:   "src/shared/domain/AuditableBaseEntity.java"
  shared_soft_delete_base: "src/shared/domain/SoftDeletableBaseEntity.java   (SE soft_delete: true)"
  shared_jpa_audit_config: "src/shared/infrastructure/config/JpaAuditingConfig.java"

implementation:
  status: COMPLETED
  next_agent: ava-build-cycle-java-api
```

---

## Layer Boundary Contract

| Layer | Pode importar Spring Data? | Pode usar JpaRepository? | Pode usar EntityManager? |
|-------|:-------------------------:|:------------------------:|:------------------------:|
| Domain | ❌ Nunca | ❌ Nunca | ❌ Nunca |
| Application | ❌ Nunca | ❌ Nunca | ❌ Nunca |
| Infrastructure | ✅ Sempre | ✅ (`package-private`) | ✅ (`package-private`) |
| API | ❌ Nunca | ❌ Nunca | ❌ Nunca |

> A verificação é estrutural: se um import `org.springframework.data.jpa.repository.*`
> aparecer em arquivos sob `domain/` ou `application/` → erro de revisão de código intencional.
> Configurar ArchUnit test `@AnalyzeClasses` para validar em CI.

---

## Failure Modes

| Cenário | Ação |
|---------|------|
| Scaffold não executado (pastas src/ ausentes) | ⛔ BLOCKED: "Execute @ava-build-cycle-java-scaffold primeiro. Nenhuma pasta de BC encontrada em outputs/tobe/source-code/." |
| Nenhuma entidade encontrada em domain/entity/ | WARN: gerar entidade placeholder `{BC}Entity` com campos básicos (id, name); marcar TODO no FlywayInstructions.md |
| `connection_source` ≠ "azure-keyvault" | ⛔ BLOCKED: "connection_source='{valor}' não é permitido. Apenas 'azure-keyvault' é aceito. Atualize project-config.yaml → persistence.connection_source: 'azure-keyvault'." |
| `db_engine` não suportado | ⛔ BLOCKED: "db_engine='{valor}' não suportado. Valores aceitos: postgresql, mssql, mysql." |
| Maven Central API inacessível | ⛔ BLOCKED: "Maven Central inacessível. Não usar versões de treinamento como fallback." |
| BC com mais de 15 entidades | WARN: "BC '{bc}' com {N} entidades — considerar subdivisão em BCs menores" |
| Entidade não herda de AuditableBaseEntity | WARN por entidade: "'{EntityName}' não herda de AuditableBaseEntity — gerado sem campos de auditoria. Adicionar herança manualmente se necessário." |
| soft_delete: true + entidade sem SoftDeletableBaseEntity | WARN: "'{EntityName}' não herda de SoftDeletableBaseEntity — @SQLDelete/@SQLRestriction gerados mas softDelete() ausente. Adicionar herança manualmente." |
| Relacionamento N:N detectado | Gerar join table SQL e `@ManyToMany` com `@JoinTable`; anotar com `// TODO: validar com arquiteto` |
| `read_model` ≠ "jdbc" | WARN: "read_model='{valor}' não reconhecido — gerado sem JdbcClient read model. Apenas 'jdbc' é suportado por este agente." |
