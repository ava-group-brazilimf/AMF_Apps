# Especificação do Protótipo Navegável — {PROJECT_NAME}

> **Spec ID**: SPEC-PROTO-001 · **Fonte**: `outputs/tobe/prototype/`
> **Constituição**: outputs/tobe/speckit/constitution.md · **trace_id**: {trace_id}
> **Gerado por**: ava-speckit-prototype-spec v1.0.0 · **Data**: {data}
> Autoridade: `screen-list.md` decide *quais* telas · `index.html` decide *como* cada uma é ·
> contrato OpenAPI decide método, path e tipos · `figma-spec.md` é consultivo.

---

## 1. Visão Geral do Protótipo

- **Propósito**: {para que o protótipo foi construído}
- **Jornadas alvo**: {jornadas de usuário representadas}
- **Fluxos de negócio**: {fluxos principais}
- **Suposições identificadas**: {o que o protótipo assume sem declarar}

### Avisos herdados da fonte

> Reemitir aqui, literalmente, a seção `## Warnings` do `screen-list.md`. O motivo da
> qualidade reduzida precisa sobreviver de F3 até a F4 — CHK-PROTO-007 confere.

| Artefato ausente na origem | Consequência declarada |
|---|---|

### Contagem de telas

| Status | Qtd | Observação |
|---|---|---|
| `included` | {n} | viram trabalho |
| `excluded` | {n} | com motivo registrado |
| `deferred` | {n} | com motivo registrado |

---

## 2. Inventário de Telas

> Uma subseção por tela `included`. Nenhuma pode faltar — CHK-PROTO-001 reprova.

#### SCREEN-{NNN} — {Nome da Tela}

| Campo | Valor |
|---|---|
| `screen_id` | `screen-{kebab}` |
| Rota | `/{path}` |
| Bounded Context | {BC} |
| Propósito de negócio | {frase} |
| Referência AS-IS | {classe ou form legado} |
| Status no protótipo | `included` |
| Âncora | `screen-list.md` linha "{nome literal}" |

- **Componentes necessários**: {lista}
- **Dados necessários**: {campos}
- **Chamadas de API**: {método e path, conforme o contrato}
- **Validações**: {regras}
- **Entrada de navegação**: {de onde se chega}
- **Saída de navegação**: {para onde se vai, e sob que condição}
- **Estados**: carregando · vazio · erro · {específicos}
- **UX rules aplicadas**: {H1..H10 do metadata da tela}

---

## 3. Especificação de Navegação

- **Jornadas completas**: {sequência de telas por jornada}
- **Transições**: origem → destino, gatilho, pré-condição
- **Navegação condicional**: {regra e critério}
- **Navegação de erro**: {para onde vai quando falha}
- **Estados vazio, sucesso e fallback**: {comportamento}

---

## 4. Especificação de Componentes

#### {NomeDoComponente}

| Aspecto | Definição |
|---|---|
| Responsabilidade | {uma frase} |
| Propriedades de entrada | {nome, tipo, obrigatoriedade} |
| Eventos de saída | {nome, payload} |
| Dependências de estado | {store, service, contexto} |
| Comportamento de validação | {regras} |
| Comportamento visual | {estados} |
| Dependências de integração | {APIs} |

---

## 5. Formulários e Validação

#### {NomeDoFormulário} — tela `{screen_id}`

| Campo | Tipo | Obrigatório | Regra | Mensagem de erro |
|---|---|---|---|---|

- **Submit**: {comportamento, endpoint, resultado}
- **Cancel**: {comportamento}
- **Reset**: {comportamento}
- **Cenário de sucesso**: {o que o usuário vê}
- **Cenário de falha**: {o que o usuário vê, com id de correlação}

---

## 6. Mapa de Integração de API

| Tela | Componente | Ação | Endpoint | Payload | Resposta | Erro | Loading | Retry |
|---|---|---|---|---|---|---|---|---|

### Divergências resolvidas a favor do contrato

| Tela | Endpoint declarado no protótipo | Contrato OpenAPI | Adotado |
|---|---|---|---|

---

## 7. Mapeamento para a Arquitetura Frontend

| Elemento | Caminho alvo |
|---|---|
| Módulo / feature folder | {caminho} |
| Página | {caminho} |
| Rota | {declaração} |
| Container | {caminho} |
| Componentes de apresentação | {caminhos} |
| Service | {caminho} |
| Hook ou store | {caminho} |
| Models / types | {caminho} |
| Validators | {caminho} |
| Arquivos de teste | {caminhos} |

---

## 8. UX e Acessibilidade

- **Responsivo**: {breakpoints e comportamento}
- **Navegação por teclado**: {ordem de foco, atalhos}
- **Rótulos acessíveis**: {`aria-*` extraídos do protótipo}
- **Estados**: carregando · vazio · erro · confirmação · sucesso
- **Idioma da interface**: {herdado do protótipo — é requisito, não detalhe}

### Mapa de tokens

| Token | Valor | Origem | Alvo na stack |
|---|---|---|---|

---

## 9. Cenários de Teste

| ID | Tela | Cenário | Tipo |
|---|---|---|---|

> Cobrir: renderização, fluxo de navegação, validação de formulário, ações do usuário,
> resposta de API com sucesso, resposta de API com erro, estado vazio, estado de carregamento,
> comportamento por permissão e comportamento responsivo.

---

## 10. Entrada para o Planejamento

| Agrupamento sugerido | Telas / componentes | Stack alvo |
|---|---|---|

---

> As seis seções abaixo têm heading **literal em inglês**: o readiness-gate C2 as confere
> por glob. Traduzi-las reprova o gate e bloqueia a wave do Build Cycle.

## Context

{Por que esta especificação existe e onde se encaixa na esteira.}

## Input

`prototype/index.html`, `screen-list.md`, `design-tokens.json`, contrato OpenAPI.

## Processing

Extração conforme `prototype-conversion-protocol.md` §2; contrato vence o metadata.

## Output

Telas, rotas, componentes, formulários, integrações e cenários de teste.

## Examples

{Uma tela completa, de `screen_id` a cenário de teste.}

## Failure Modes

Fonte obrigatória ausente ⇒ BLOQUEADO. Divergência com o contrato ⇒ registrada, nunca
silenciada. Warning da fonte ⇒ reemitido na seção 1.
