# Fase de Scaffold — fluxo único, determinístico e aprovado

> Substitui os dois caminhos de scaffold que coexistiam até esta mudança.
> Leia **Migração** antes de rodar num projeto já existente.

## O que mudou, em uma frase

O esqueleto do frontend e do backend passa a ser **gerado por templates
versionados e compilado de verdade** antes de qualquer agente coder escrever
uma linha de código de feature. Um gate de 60s oferece o veto ao operador;
sem resposta, o baseline é aprovado automaticamente.

## Fluxo

```
ava-stack-orchestrator (Step 0.0)
   └─> scaffold_runner.py
         ├─ 1. resolve stacks de project-config.yaml → tobe_stack
         ├─ 2. FRONTEND  generator  → source-code/frontend/
         ├─ 3. FRONTEND  verifier   → build real            ─┐ falhou aqui?
         ├─ 4. tasks-progress.json                               │ backend nem começa
         ├─ 5. BACKEND   generator  → source-code/backend/  ─┘
         ├─ 6. BACKEND   verifier   → restore + build reais
         ├─ 7. tasks-progress.json
         ├─ 8. git baseline em source-code/  (só se AMBOS compilaram)
         └─ 9. GATE HUMANO (60s)
                ├─ [A] aprovado  → agentes coder liberados
                ├─ [R] rejeitado → esteira para, scaffolds preservados
                └─ sem resposta  → APROVA automaticamente e libera os coders
```

A ordem está em código (`scaffold_paths.COMPONENT_TYPES`), não na interpretação
de um modelo.

## A regra de diretórios

O diretório é definido pela **responsabilidade arquitetural**, nunca pela
tecnologia:

| Componente | Diretório | Stacks |
|---|---|---|
| frontend | `source-code/frontend/` | angular, react, vue, svelte, blazor |
| backend | `source-code/backend/` | dotnet, java, spring-boot, node, nestjs, python, fastapi, go, gin |

**Proibido**: `source-code/angular/`, `source-code/dotnet/`,
`source-code/{stack}/`, ou qualquer nome derivado de linguagem/framework.
Trocar Angular por React muda generator, verifier, templates, versões e comandos
de build — **nunca o caminho**. A stack vive como metadado em
`tasks-progress.json → tasks[].stack`.

A resolução é centralizada em `scaffold_paths.resolve_source_code_path(component_type)`.
Nenhum generator calcula seu próprio destino: ele recebe o caminho já resolvido
e o valida antes de escrever.

## Configurar uma stack

O front-matter do `{stack}-scaffold.md` é a **fonte única** de configuração:

```yaml
---
component_type: backend            # frontend | backend — define o diretório
stack: dotnet                      # metadado; escolhe generator/templates
generator: src/shared/tools/f4s_dotnet_scaffold.py
verifier: src/shared/utils/verify_dotnet_solution.py
template_path: src/shared/templates/dotnet-scaffold
version_source: versions.yaml
build_command: dotnet build
manifest: dotnet
---
```

`output_path` **não** deve ser declarado — é calculado. Se declarado por
compatibilidade, precisa ser exatamente o canônico do `component_type`; qualquer
divergência é erro de configuração antes de qualquer geração.

### Allowlist de segurança

O front-matter é configuração *executável*, então tudo passa por validação
antes de rodar:

- `generator`/`verifier`: só sob `src/shared/tools/` ou `src/shared/utils/`, só `.py`;
- `template_path`: só sob `src/shared/templates/`;
- caminho absoluto, `..`, symlink para fora do repo → rejeitado;
- campo desconhecido no front-matter → erro (typo não passa em silêncio);
- `stack` incoerente com `component_type` → erro.

### Adicionar uma stack nova

1. Crie `src/shared/templates/{stack}-scaffold/` com `versions.yaml`.
2. Crie o generator em `src/shared/tools/` e o verifier em `src/shared/utils/`,
   ambos com saída JSON estruturada e exit code honesto.
3. Registre a stack em `scaffold_paths.STACK_COMPONENT_TYPES`.
4. Crie `{stack}-scaffold.md` com o front-matter acima.

Não há fallback genérico: stack sem receita determinística **bloqueia**, em vez
de gerar um esqueleto que não compila.

## Comandos

```bash
# executa a fase (idempotente — scaffold válido é reaproveitado)
python src/shared/tools/scaffold_runner.py --project <projeto> --json

# decide o gate sem terminal (CI, retomada)
python src/shared/tools/scaffold_runner.py --project <projeto> --approve
python src/shared/tools/scaffold_runner.py --project <projeto> --reject

# regenerar do zero
python src/shared/tools/scaffold_runner.py --project <projeto> --no-reuse --force
```

## O gate de aprovação

O operador tem **60 segundos** para decidir. Esgotado o prazo — ou não havendo
terminal — o baseline é **aprovado automaticamente** e os agentes coder são
despachados.

> **O que isso custa.** O gate deixa de ser barreira e vira janela de veto. Um
> baseline que *compila mas está errado* (BC faltando, versão de framework
> trocada, blueprint desatualizado) passa sozinho quando ninguém está olhando, e
> os coders geram features inteiras sobre ele. Em execução desassistida, na
> prática, não há revisão humana do scaffold.

Para tornar isso auditável, a decisão é gravada com sua procedência:

| `decided_by` | Quando | `auto_approved` | `user` |
|---|---|---|---|
| `user` | respondeu `[A]`/`[R]`, ou usou `--approve`/`--reject` | `false` | quem decidiu |
| `timeout` | prazo esgotou num terminal | `true` | `null` |
| `non-interactive` | sem TTY (esteira automática, CI) | `true` | `null` |

Duas coisas o automatismo **não** faz:

- **nunca rejeita sozinho** — rejeição exige ato explícito;
- **nunca trata resposta ilegível como aprovação** — quem digitou algo estava
  presente e quis decidir; um typo vira `awaiting_user_approval`, não `approved`.

### Ajustar ou desligar o prazo

```bash
# modo estrito: sem resposta, nada avança (comportamento original)
python src/shared/tools/scaffold_runner.py --project <p> --approval-timeout 0

# prazo diferente
python src/shared/tools/scaffold_runner.py --project <p> --approval-timeout 300

# por ambiente, para a esteira inteira
export AVA_SCAFFOLD_APPROVAL_TIMEOUT=0
```

## `tasks-progress.json`

Vive em `projects/{p}/outputs/tobe/speckit/tasks-progress.json`. Escrita atômica
(temporário + `os.replace`): uma interrupção não deixa JSON truncado.

```json
{
  "tasks": {
    "T-SCAFFOLD-FRONTEND-001": {
      "component_type": "frontend", "stack": "angular",
      "status": "completed", "output_path": "source-code/frontend",
      "build_status": "succeeded", "verification_status": "succeeded",
      "attempts": 1, "commit_sha": "..."
    },
    "T-SCAFFOLD-BACKEND-001": {
      "component_type": "backend", "stack": "dotnet",
      "restore_status": "succeeded", "build_status": "succeeded"
    }
  },
  "approval": { "status": "approved", "user": "...", "decided_at": "..." },
  "artifacts": {
    "artifact:scaffold:frontend": {},
    "artifact:scaffold:backend": {},
    "artifact:approval:code-generation": {}
  }
}
```

Estados: `pending`, `running`, `generated`, `verifying`, `completed`, `failed`,
`blocked`, `awaiting_user_approval`, `approved`, `rejected`, `cancelled`.
Transições inválidas são recusadas (`StateError`).

## Retomada

Ao reexecutar, o runner:

1. lê `tasks-progress.json`;
2. confere se o diretório canônico **existe e não está vazio** — estado
   persistido sozinho não basta;
3. reaproveita o que está válido e regenera o resto;
4. reapresenta o gate se estiver em `awaiting_user_approval`.

## Falhas

| Situação | Comportamento |
|---|---|
| Frontend falha | backend não é gerado; sem baseline; sem coder |
| Backend falha | frontend preservado; sem baseline; sem coder |
| 3 tentativas esgotadas | falha controlada; não chega ao gate |
| Rejeição | scaffolds preservados; `downstream: blocked`; resultado controlado, não falha técnica |
| Sem resposta (60s) | **aprova automaticamente** e libera os coders; gravado como `decided_by: timeout` |
| Sem terminal | **aprova automaticamente**; gravado como `decided_by: non-interactive` |
| Modo estrito (`--approval-timeout 0`) | `awaiting_user_approval`; nada avança |
| SDK ausente | verifier reprova (`toolchain_unavailable`); sem commit |

## Migração

### Mudanças incompatíveis

1. **Diretório de saída**: `source-code/{stack}/` → `source-code/{component_type}/`.
   O `f4s_phase_runner.py` gravava em `source-code/angular` / `source-code/dotnet`.
2. **Repositório git**: era um repo por stack (`source-code/{stack}/.git`);
   agora é **um repo em `source-code/`** contendo frontend e backend. Só assim
   existe um commit que significa "o sistema compila", e não "esta metade compila".
3. **Ids de task e artifact**: `T-SCAFFOLD-DOTNET-001` → `T-SCAFFOLD-BACKEND-001`;
   `artifact:scaffold:angular` → `artifact:scaffold:frontend`. Artifacts antigos
   ainda podem ser LIDOS durante a migração, mas não são mais produzidos.
4. **`spec.md` do W0**: a receita não é mais copiada para dentro dele; passa a
   referenciar o `{stack}-scaffold.md` com `sha256`.

### Projeto existente com diretório legado

A fase **detecta e reporta**, nunca move nem sobrescreve:

```
⚠ diretório legado detectado: source-code/angular/ (canônico: source-code/frontend). Nada foi movido.
```

O commit de baseline é **recusado** enquanto houver código num diretório
derivado de tecnologia — commitá-lo congelaria a duplicidade. Migração é ato
explícito:

```bash
cd projects/<p>/outputs/tobe/source-code
git mv angular frontend      # preserva histórico se já houver repo
python ../../../../../src/shared/tools/scaffold_runner.py --project <p>
```

Revalide o build depois de mover.

## Ferramentas

| Arquivo | Papel |
|---|---|
| `src/shared/tools/scaffold_paths.py` | resolução canônica de caminho + detecção de legado |
| `src/shared/tools/scaffold_frontmatter.py` | parser + schema + allowlist do front-matter |
| `src/shared/tools/scaffold_state.py` | `tasks-progress.json`: escrita atômica e máquina de estados |
| `src/shared/tools/scaffold_approval.py` | gate humano |
| `src/shared/tools/scaffold_runner.py` | orquestração da fase |
| `src/shared/tools/f4s_angular_scaffold.py` | generator Angular |
| `src/shared/tools/f4s_dotnet_scaffold.py` | generator .NET |
| `src/shared/utils/verify_angular_app.py` | verifier Angular (npm install + ng build + health) |
| `src/shared/utils/verify_dotnet_solution.py` | verifier .NET (estrutura + restore + build + test) |
