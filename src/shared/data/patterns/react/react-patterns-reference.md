---
name: react-patterns-reference
description: "Referência de padrões React 18 / TypeScript strict para geração de código"
version: "1.0.0"
used_by: [ava-stack-react-frontend]
---

# React 18 Patterns Reference

> Contraparte de `src/shared/data/patterns/angular/angular-patterns-reference.md`.
> **REFERÊNCIA VINCULANTE** — nenhuma instrução de agente pode contradizer uma regra definida aqui.

## Naming — Feature-based (naming por Bounded Context)

Toda estrutura é organizada por feature/Bounded Context — nunca por tipo técnico.

```
src/
├── accounts-payable/                       ← feature = BC AccountsPayable
│   ├── domain/
│   │   ├── types.ts                        ← tipos derivados do contrato OpenAPI
│   │   └── ap-form.schema.ts               ← schema Zod da tela
│   ├── application/
│   │   └── hooks/
│   │       ├── useApListQuery.ts           ← 1 hook por tela
│   │       └── useApFormMutation.ts
│   ├── infrastructure/
│   │   └── api/AccountsPayableApi.ts       ← 1 função por operação do contrato
│   └── ui/
│       ├── pages/ApListPage.tsx            ← Smart (container)
│       ├── components/InstallmentRow.tsx   ← Dumb (presentational)
│       └── pages/__tests__/ApListPage.test.tsx
├── shared/
│   ├── ui/                                 ← RX-001..RX-014
│   ├── format/{money.ts,date.ts}
│   └── api/http.ts
```

| Tipo | Convenção | Exemplo ✅ | Exemplo ❌ |
|---|---|---|---|
| Componente | `PascalCase.tsx` | `InstallmentRow.tsx` | `installment-row.tsx`, `instRow.tsx` |
| Página (smart) | `{Pascal}Page.tsx` em `ui/pages/` | `ApListPage.tsx` | `ApList.tsx`, `pages/list.tsx` |
| Hook | `use{Pascal}.ts` | `useApListQuery.ts` | `apListHook.ts`, `hooks.ts` |
| Client de API | `{Pascal}Api.ts` | `AccountsPayableApi.ts` | `api.ts`, `service.ts` |
| Schema Zod | `{kebab}.schema.ts` | `ap-form.schema.ts` | `schemas.ts`, `ApFormSchema.ts` |
| Store Zustand | `{kebab}.store.ts` | `error.store.ts` | `store.ts`, `ErrorStore.ts` |
| Teste | `{Alvo}.test.tsx` em `__tests__/` | `ApListPage.test.tsx` | `test.tsx`, `ApListPage.spec.tsx` |

> **Invariant:** NUNCA organizar por tipo técnico (`components/`, `hooks/`, `services/` na raiz
> de `src/`). SEMPRE por BC primeiro — os tipos ficam dentro do BC. A única exceção é
> `src/shared/`, que é transversal por definição.

---

## React Hook Form + Zod Only

Formulários com `useState` por campo são **proibidos**. Todo `<form>` usa React Hook Form com
resolver Zod. O schema Zod é a fonte única de verdade da validação — é onde as regras de
negócio `BR-XXXX` são codificadas e onde os testes as verificam.

```typescript
// ✅ Correto — ap-form.schema.ts
import { z } from 'zod';

const TEXT_PT_BR = /^[\p{L}\s\-']+$/u;

export const apFormSchema = z.object({
  // Implements: BR-0012 — CNPJ obrigatório para fornecedor pessoa jurídica
  taxId: z.string().min(1, 'CNPJ é obrigatório'),
  name: z
    .string()
    .min(1, 'Razão Social é obrigatória')
    .regex(TEXT_PT_BR, 'Use apenas letras, espaços, hífen e apóstrofo'),
  personType: z.enum(['F', 'J']),
}).superRefine((data, ctx) => {
  // Implements: BR-0034 — pessoa física usa CPF, jurídica usa CNPJ
  const ok = data.personType === 'F'
    ? /^\d{3}\.\d{3}\.\d{3}-\d{2}$/.test(data.taxId)
    : /^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/.test(data.taxId);
  if (!ok) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['taxId'],
      message: data.personType === 'F'
        ? 'CPF inválido — verifique os 11 dígitos e tente novamente'
        : 'CNPJ inválido — verifique os 14 dígitos e tente novamente',
    });
  }
});

export type ApFormValues = z.infer<typeof apFormSchema>;
```

```tsx
// ✅ Correto — uso na página
const { register, handleSubmit, formState: { errors, isValid } } = useForm<ApFormValues>({
  resolver: zodResolver(apFormSchema),
  mode: 'onBlur',
});

<input id="taxId" {...register('taxId')} aria-invalid={!!errors.taxId}
       aria-describedby="taxId-error taxId-hint" />
<FieldError id="taxId-error" error={errors.taxId} />

// ❌ Incorreto — estado por campo, validação manual
const [taxId, setTaxId] = useState('');
if (!taxId) setError('obrigatório');
```

> **Invariants:**
> - NUNCA `useState` por campo de formulário — sempre RHF
> - NUNCA validar manualmente no `onSubmit` — sempre schema Zod via `zodResolver`
> - `mode: 'onBlur'` — feedback ao sair do campo, não a cada tecla
> - Mensagens de erro descrevem o problema **e** sugerem a ação corretiva (heurística H9)
> - O tipo do formulário vem de `z.infer<>` — nunca declarado à mão em paralelo ao schema

---

## Smart / Dumb Pattern (Container / Presentational)

| | Smart (Container) | Dumb (Presentational) |
|---|---|---|
| **Local** | `ui/pages/{Pascal}Page.tsx` | `ui/components/{Pascal}.tsx` |
| **Chama hooks de dados?** | ✅ Sim (`useQuery`/`useMutation`) | ❌ Nunca |
| **Acessa store?** | ✅ Sim | ❌ Nunca |
| **Recebe dados via** | hooks | `props` tipadas |
| **Emite eventos via** | — | callbacks em `props` |
| **Testabilidade** | requer providers mockados | teste puro com props |

```tsx
// ✅ Smart — ui/pages/ApListPage.tsx
export function ApListPage() {
  const { data = [], isLoading, error } = useApListQuery();
  const confirm = useConfirm();
  const remove = useApDeleteMutation();

  const onDelete = async (id: string) => {
    if (await confirm({ title: 'Excluir título', message: 'Esta ação não pode ser desfeita.' })) {
      remove.mutate(id);
    }
  };

  return <DataTable rows={data} columns={COLUMNS} getRowId={(r) => r.id} onRowAction={...} />;
}

// ✅ Dumb — ui/components/InstallmentRow.tsx
interface InstallmentRowProps {
  installment: Installment;
  onDelete: (id: string) => void;
}
export function InstallmentRow({ installment, onDelete }: InstallmentRowProps) {
  return <tr>…</tr>;
  // ❌ Nunca: useQuery / useStore aqui
}
```

> **Invariants:**
> - `useQuery` / `useMutation` / stores SOMENTE em `ui/pages/*Page.tsx`
> - Componentes em `ui/components/` são 100% reutilizáveis e testáveis sem provider
> - Props sempre com `interface {Nome}Props` explícita — nunca `any` nem props implícitas

---

## Formatação — Monetária e de Data

Formatação SEMPRE via helper dedicado em `src/shared/format/` — nunca inline no JSX.

```typescript
// ✅ Correto — src/shared/format/money.ts
export interface Money { amount: number; currency: string; }

export function formatMoney(value: Money | null | undefined, locale = 'pt-BR'): string {
  if (value == null) return '—';
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: value.currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,   // DECIMAL(18,4) no banco — preservar precisão (ADR-002)
  }).format(value.amount);
}

// ✅ Correto — src/shared/format/date.ts
const DATE_FMT = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit', month: '2-digit', year: 'numeric',
});

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return DATE_FMT.format(new Date(iso));   // ISO 8601 UTC é parseado corretamente
}
```

```tsx
{/* ✅ Correto */}
<td>{formatMoney(installment.amount)}</td>
<td>{formatDate(installment.dueDate)}</td>

{/* ❌ Incorreto — formatação inline */}
<td>{installment.amount.amount.toFixed(2)}</td>
<td>{new Date(item.dueDate).toLocaleDateString()}</td>
<td>{item.dueDate}</td>
```

> **Invariants:**
> - Helpers são funções puras, sem side effects, testáveis isoladamente
> - `null`/`undefined` retorna `'—'` — nunca lançar exceção durante o render
> - O shape `Money` vem do contrato OpenAPI — não redefinir manualmente
> - `Intl.DateTimeFormat` instanciado **uma vez** no módulo — criar por render é caro
> - Datas ISO 8601 UTC da API são exibidas como DD/MM/YYYY sem conversão manual

---

## PT-BR Validation Patterns

> **Invariant:** NUNCA usar `[a-zA-Z]` para validar campos de texto em domínios PT-BR.
> SEMPRE `\p{L}` (categoria Unicode "Letter") com a flag `u`.

| Campo | Padrão canônico (flag `u` obrigatória) | Padrão proibido |
|---|---|---|
| Nome / texto livre | `/^[\p{L}\s\-']+$/u` | `/^[a-zA-Z\s]+$/` |
| Busca / filtro texto | `/^[\p{L}\d\s\-'.]+$/u` | `/^[a-zA-Z0-9\s]+$/` |
| CPF | `/^\d{3}\.\d{3}\.\d{3}-\d{2}$/` | — |
| CNPJ | `/^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/` | — |
| CEP | `/^\d{5}-?\d{3}$/` | — |
| Telefone | `/^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$/` | — |
| E-mail | `z.string().email(...)` (builtin) | — |

Em Zod: `z.string().regex(/^[\p{L}\s\-']+$/u, 'mensagem')`.

> **Exemplos de nomes válidos PT-BR que DEVEM ser aceitos:**
> José, João, Márcia, Renata, André, Ângela, Luís, Conceição, Sebastião, Cristóvão.

---

## TanStack Query — Query Keys e Invalidação

Convenção hierárquica de chave, para que a invalidação por BC funcione sem enumerar telas.

```typescript
// ✅ Correto — chave hierárquica [bc, escopo, params]
export const apKeys = {
  all:    ['ap'] as const,
  lists:  () => [...apKeys.all, 'list'] as const,
  list:   (filters: ApFilters) => [...apKeys.lists(), filters] as const,
  details:() => [...apKeys.all, 'detail'] as const,
  detail: (id: string) => [...apKeys.details(), id] as const,
};

export function useApListQuery(filters: ApFilters) {
  return useQuery({ queryKey: apKeys.list(filters), queryFn: () => listAccountsPayable(filters) });
}

export function useApDeleteMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteAccountsPayable,
    onSuccess: () => qc.invalidateQueries({ queryKey: apKeys.all }),  // invalida o BC inteiro
  });
}

// ❌ Incorreto — chave string solta, impossível de invalidar por escopo
useQuery({ queryKey: ['apList'], ... });
```

> **Invariants:**
> - Um objeto `{bc}Keys` por BC, sempre com `all` na raiz
> - Toda mutation invalida no mínimo `{bc}Keys.all` em `onSuccess`
> - `queryFn` chama a função tipada de `infrastructure/api/` — nunca `fetch` direto na página
> - Em testes, `QueryClient` com `retry: false` (senão o teste de erro espera os retries)

---

## Zustand — Convenção de Slice

Zustand é para estado **global de UI** (erro, loading, sessão). Estado de servidor pertence ao
TanStack Query — nunca duplicar dados de API em store.

```typescript
// ✅ Correto — src/shared/store/error.store.ts
interface ErrorState {
  blocking: { title: string; message: string; correlationId?: string } | null;
  showBlocking: (e: NonNullable<ErrorState['blocking']>) => void;
  dismiss: () => void;
}

export const useErrorStore = create<ErrorState>((set) => ({
  blocking: null,
  showBlocking: (e) => set({ blocking: e }),
  dismiss: () => set({ blocking: null }),
}));

// Consumo com selector — evita re-render desnecessário
const blocking = useErrorStore((s) => s.blocking);

// ❌ Incorreto — cache de dados de API em store
const useApStore = create((set) => ({ items: [], fetchItems: async () => { ... } }));

// ❌ Incorreto — consumir a store inteira (re-renderiza a cada mudança de qualquer campo)
const store = useErrorStore();
```

> **Invariants:**
> - Uma store por preocupação transversal — nunca uma store global única
> - SEMPRE consumir com selector: `useStore((s) => s.campo)`
> - Dados de servidor NUNCA vão para store — pertencem ao TanStack Query
> - Actions declaradas dentro do próprio `create<T>()`, tipadas na interface

---

## Segurança e Acessibilidade

```tsx
{/* ✅ XSS — sanitizar antes de qualquer HTML dinâmico */}
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />

{/* ❌ */}
<div dangerouslySetInnerHTML={{ __html: apiData }} />
```

> **Invariants:**
> - `dangerouslySetInnerHTML` só com valor passado por `DOMPurify.sanitize()`
> - Segredos (client id, tenant id, URLs de API) só via `import.meta.env.VITE_*` — nunca hardcode
> - Nunca logar PII (nome, e-mail, CPF) — apenas IDs e códigos de erro
> - `aria-label` obrigatório em botão de ícone sem texto visível — e também `title` (heurística H7)
> - `alt` obrigatório em toda `<img>`
> - Todo `<input>` tem `<label htmlFor>` visível — placeholder NUNCA substitui label (H6)
> - Contraste WCAG 2.1 AA: 4.5:1 para texto, 3:1 para componentes de UI
