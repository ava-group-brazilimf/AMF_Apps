# Guia do Particionador de Módulos (Module Partitioner)

> **Escopo**: AS-IS Diagnostic — Delphi (extensível a VB6/COBOL na Fase 2)
>
> **Artefatos gerados**: `module-partition.json`, `scope-filter-manifest.json`
> **Local**: `projects/{proj}/outputs/asis/ast-raw/{language}/compressed/` (`{language}` = e.g. `delphi`)

---

## O que é?

O **Module Partitioner** é um motor de inferência de módulos / bounded contexts que executa **após** a extração AST do repositório Delphi. Ele analisa o grafo de dependências entre units (cláusulas `uses`) e aplica o algoritmo **Leiden** (detecção de comunidades em grafos) para agrupar unidades fortemente acopladas em módulos lógicos.

**Decisão arquitetural**: a ferramenta AST externa (`ava-fabric-delphi-analyzer`) **não é modificada**. O particionador opera como *post-filter* sobre os 9 JSONs monolíticos já extraídos.

---

## Como funciona o fluxo

```
┌────────────────────────────────────────────┐
│ 1. Extração AST (run_ast_analysis)         │
│    gera 9 JSONs monolíticos                │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│ 2. Module Partitioner (ESTE DOCUMENTO)     │
│    lê 08_code_overview.json + fontes .pas  │
│    constrói grafo de dependências          │
│    executa Leiden → comunidades            │
│    gera module-partition.json              │
│    gera scope-filter-manifest.json         │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│ 3. Agentes F1 (solution-delphi, etc.)      │
│    leem scope-filter-manifest.json         │
│    filtram análises pelas units includas   │
└────────────────────────────────────────────┘
```

---

## Configuração

No `project-config.yaml` do projeto:

```yaml
# Escopo de análise
scope_modules: "all"          # "all" = analisar tudo (padrão)
#                              # ["Financeiro", "Vendas"] = apenas esses módulos

# ── Module Partitioner Configuration ──
module_partitioner_resolution: null   # null = auto-tune (recomendado)
#                                      # < 50 units → 0.5 (módulos grossos)
#                                      # 50–200 units → 1.0 (padrão)
#                                      # > 200 units → 1.5 (mais granular)

module_override_file: "module-override.json"  # arquivo de override manual
```

---

## Seleção de Módulos (`scope_modules`)

### Modo Full — `scope_modules: "all"` (padrão)

O particionador **ainda executa** (se não houver override) e gera o mapeamento completo em `module-partition.json`, mas **não filtra** nada. Todos os agentes F1 processam o repositório inteiro, exatamente como antes.

> ✅ Este modo existe para **preservar regressão** e para que o mapeamento de módulos esteja disponível no relatório mesmo em modernizações completas.

### Modo Parcial — `scope_modules: ["M1", "M2"]`

O particionador filtra apenas as units pertencentes aos módulos solicitados. Gera `scope-filter-manifest.json` com:

```json
{
  "scope_modules": ["Financeiro", "Vendas"],
  "included_units": ["uContasPagar.pas", "uPedido.pas", ...],
  "excluded_units": ["uRH.pas", "uFolhaPagamento.pas", ...],
  "module_partition": {
    "Financeiro": ["uContasPagar.pas", ...],
    "Vendas": ["uPedido.pas", ...]
  }
}
```

**Impacto nos agentes F1**:

- `solution-delphi`: Step 1 carrega `scope-filter-manifest.json` → `included_units`. Filtra `payload.classes` de `08_code_overview.json`, regras de `01_business_rules.json`, etc. antes dos hard caps (500 regras, 200 forms...).
- Todos os diagramas e relatórios passam a conter **apenas** as units dos módulos selecionados.
- O `master-report.md` inclui seção obrigatória de **escopo parcial** listando módulos incluídos e excluídos.

---

## Override Manual (`module-override.json`)

### Quando usar?

- O cliente **já conhece** seus domínios de negócio e não deseja depender da inferência algorítmica.
- A inferência Leiden produziu nomes ou fronteiras que **não correspondem** à linguagem do cliente.
- Necessidade de **consolidar ou separar** manualmente certas units por razões de negócio.

### Como criar

Coloque o arquivo no diretório `context/` do projeto:

```json
{
  "modules": {
    "Financeiro": [
      "uContasPagar.pas",
      "uContasReceber.pas",
      "uNotaFiscal.pas",
      "uBanco.pas"
    ],
    "Vendas": [
      "uPedido.pas",
      "uCliente.pas",
      "uProduto.pas"
    ],
    "RH": [
      "uFuncionario.pas",
      "uFolhaPagamento.pas"
    ]
  },
  "source": "manual"
}
```

> ⚡ **Se este arquivo existir, o algoritmo Leiden é completamente ignorado.**
> O console exibirá: `Module override detectado — pulando inferência Leiden.`

### Convenções

- O nome da unit deve coincidir exatamente com o nome do arquivo (ex.: `uContasPagar.pas`).
- Units listadas em mais de um módulo são aceitas (duplicidade), mas o manifesto de escopo as tratará como incluídas se **qualquer** módulo solicitado as referenciar.
- Units **não listadas** em nenhum módulo serão tratadas como `excluded` em modo parcial.

---

## Algoritmo Leiden — Auto-tuning de Resolução

O parâmetro `resolution` controla a granularidade das comunidades detectadas:

| Tamanho do repositório | Resolução | Comportamento                                   |
| ----------------------- | ----------- | ----------------------------------------------- |
| < 50 units              | `0.5`     | Módulos mais abrangentes (menos granularidade) |
| 50 – 200 units         | `1.0`     | Balanceado (padrão)                            |
| > 200 units             | `1.5`     | Módulos mais específicos (mais granularidade) |

### Quando override a resolução?

No `project-config.yaml`:

```yaml
module_partitioner_resolution: 0.8   # exemplo: forçar módulos mais abrangentes
```

**Sintomas e ajustes**:

| Sintoma                                                          | Causa provável                                  | Ajuste                       |
| ---------------------------------------------------------------- | ------------------------------------------------ | ---------------------------- |
| Muitos módulos pequenos (ex.: 30 módulos em repo de 100 units) | Resolução muito alta para o domínio           | Diminuir (`0.5`–`0.8`)  |
| Poucos módulos enormes (ex.: 2 módulos em repo de 500 units)   | Resolução muito baixa                          | Aumentar (`1.5`–`2.0`)  |
| Nomes de módulos não fazem sentido de negócio                 | Grafo esparsa ou units sem prefixo de diretório | Usar`module-override.json` |

---

## Troubleshooting

### "O partitioner não encontrou nenhuma aresta"

- **Causa**: O repositório pode não ter cláusulas `uses` explícitas, ou o `08_code_overview.json` não contém dados de `parent`.
- **Resultado**: O particionador cai em partição trivial (1 unit = 1 módulo).
- **Mitigação**: Use `module-override.json`.

### "Módulos solicitados não encontrados na partição"

- **Causa**: O nome do módulo na configuração difere do nome inferido (case-insensitive, mas pode havar diferença de acentuação).
- **Solução**: Verifique o `module-partition.json` gerado para ver os nomes exatos inferidos, ou use `module-override.json` para definir os nomes desejados.

### "Análise continua usando todo o repo mesmo com scope definido"

- **Causa**: O agente downstream pode não estar lendo `scope-filter-manifest.json` (spec não atualizado).
- **Solução**: Verifique se o spec do agente (ex.: `solution-delphi.md`) foi atualizado para consumir o manifesto no Step 0.

---

## Referências

- **Algoritmo**: Traag, V. A., Waltman, L., & van Eck, N. J. (2019). From Louvain to Leiden: guaranteeing well-connected communities. *Scientific Reports*, 9(1), 5233.
- **Implementação**: `src/modules/ava-fabric-agents/asis-diagnostic/utils/module_partitioner.py`
- **Integração AST**: `src/modules/ava-fabric-agents/asis-diagnostic/utils/run_ast_analysis.py`
