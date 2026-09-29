---
name: angular-patterns-reference
description: "Referência de padrões Angular 17 / TypeScript para geração de código"
version: "1.0.1"
used_by: [ava-tobe-architecture-technical, ava-stack-angular-frontend]
---

# Angular 17 Patterns Reference

## Naming — Feature-based (naming por feature)

Toda estrutura é organizada por feature/Bounded Context — nunca por tipo técnico.

```
src/app/
├── customers/                        ← feature = BC CustomerSupplier
│   ├── customers-page.component.ts   ← Smart (container)
│   ├── customer-card.component.ts    ← Dumb (presentational)
│   ├── customer.service.ts
│   ├── customer.store.ts
│   └── pipes/
│       └── money-format.pipe.ts
├── accounts-payable/                 ← feature = BC AccountsPayable
│   ├── accounts-payable-page.component.ts
│   └── installment-row.component.ts
```

| Tipo | Convenção | Exemplo ✅ | Exemplo ❌ |
|---|---|---|---|
| Componente | `kebab-case.component.ts` | `customer-card.component.ts` | `CustomerCard.ts`, `custCard.ts` |
| Service | `kebab-case.service.ts` | `party.service.ts` | `PartyService.ts`, `partyHelper.ts` |
| Store (NgRx Signal) | `kebab-case.store.ts` | `customer.store.ts` | `CustomerStore.ts`, `store.ts` |
| Pipe | `kebab-case.pipe.ts` | `money-format.pipe.ts` | `MoneyPipe.ts`, `format.ts` |
| Guard | `kebab-case.guard.ts` | `auth.guard.ts` | `AuthGuard.ts` |
| Interceptor | `kebab-case.interceptor.ts` | `token.interceptor.ts` | `TokenInterceptor.ts` |

> **Invariant:** NUNCA organizar por tipo técnico (`components/`, `services/`, `pipes/` na raiz).
> SEMPRE organizar por feature primeiro — tipos ficam dentro da feature.

---

## Reactive Forms Only

`FormsModule` (template-driven) é proibido. Apenas `ReactiveFormsModule` com `FormGroup` + `FormControl`.

```typescript
// ✅ Correto — Reactive Form
import { FormGroup, FormControl, Validators } from '@angular/forms';

readonly form = new FormGroup({
  taxId:  new FormControl('', [Validators.required, taxIdValidator]),
  name:   new FormControl('', Validators.required),
  type:   new FormControl<'C' | 'F' | 'CF'>('C', Validators.required),
});

// Acessar valor com tipagem
const value = this.form.getRawValue(); // tipado pelo FormGroup

// Validação condicional (ex: CPF vs CNPJ por tipo de pessoa)
this.form.get('type')!.valueChanges.subscribe(tipo => {
  const ctrl = this.form.get('taxId')!;
  ctrl.setValidators(tipo === 'F' ? [cpfValidator] : [cnpjValidator]);
  ctrl.updateValueAndValidity();
});
```

```html
<!-- ✅ Correto -->
<input [formControl]="form.controls.taxId" />
<mat-error *ngIf="form.controls.taxId.hasError('required')">Obrigatório</mat-error>

<!-- ❌ Incorreto — template-driven -->
<input [(ngModel)]="party.taxId" />
```

> **Invariants:**
> - NUNCA `[(ngModel)]` em nenhum formulário
> - NUNCA importar `FormsModule` — apenas `ReactiveFormsModule`
> - Validadores customizados como função pura: `ValidatorFn` tipado
> - `getRawValue()` para leitura — nunca `form.value` (ignora campos disabled)

---

## Smart / Dumb Pattern (Container / Presentational)

Separação obrigatória de responsabilidades entre componentes que acessam estado global
e componentes que apenas renderizam dados recebidos.

| | Smart (Container) | Dumb (Presentational) |
|---|---|---|
| **Sufixo de arquivo** | `-page.component.ts` | `.component.ts` |
| **Acessa Store?** | ✅ Sim | ❌ Nunca |
| **Despacha actions?** | ✅ Sim | ❌ Nunca |
| **Recebe dados via** | `Signal` / `Observable` do Store | `@Input()` tipado |
| **Emite eventos via** | — | `@Output() EventEmitter` |
| **Testabilidade** | requer mock do Store | teste puro com `@Input` |

```typescript
// ✅ Smart — customers-page.component.ts
@Component({ selector: 'app-customers-page', standalone: true, ... })
export class CustomersPageComponent {
  private readonly store = inject(CustomerStore);

  readonly customers = this.store.customers;         // Signal
  readonly isLoading  = this.store.isLoading;

  onSearch(term: string) { this.store.search(term); }
  onDelete(id: string)   { this.store.delete(id); }
}

// ✅ Dumb — customer-card.component.ts
@Component({ selector: 'app-customer-card', standalone: true, ... })
export class CustomerCardComponent {
  @Input({ required: true }) customer!: CustomerDto;
  @Output() delete = new EventEmitter<string>();

  onDelete() { this.delete.emit(this.customer.id); }
  // ❌ Nunca: inject(CustomerStore) aqui
}
```

> **Invariants:**
> - `inject(Store)` SOMENTE em `*-page.component.ts`
> - Dumb components são 100% reutilizáveis e testáveis sem mock
> - Comunicação Smart → Dumb: apenas `@Input()` e `@Output()`

---

## Pipes — Formatação Monetária

Formatação de valores monetários SEMPRE via pipe dedicado — nunca inline no template.
O pipe consome o shape do VO `Money` gerado pelo NSwag (`{ amount: number; currency: string }`).

```typescript
// ✅ Correto — money-format.pipe.ts
import { Pipe, PipeTransform } from '@angular/core';

export interface Money { amount: number; currency: string; }

@Pipe({ name: 'moneyFormat', standalone: true, pure: true })
export class MoneyFormatPipe implements PipeTransform {
  transform(value: Money | null | undefined, locale = 'pt-BR'): string {
    if (value == null) return '—';
    return new Intl.NumberFormat(locale, {
      style:    'currency',
      currency: value.currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,   // DECIMAL(18,4) no banco — preservar precisão
    }).format(value.amount);
  }
}
```

```html
<!-- ✅ Correto -->
{{ installment.amount | moneyFormat }}
{{ account.balance   | moneyFormat:'en-US' }}

<!-- ❌ Incorreto — formata sem conhecer o currency do VO -->
{{ installment.amount.amount | currency:'BRL' }}

<!-- ❌ Incorreto — lógica de formatação inline no template -->
{{ installment.amount.amount.toFixed(2) }}
```

> **Invariants:**
> - `pure: true` — pipe é stateless, sem side effects
> - `null`/`undefined` retorna `'—'` — nunca lançar exceção no template
> - O shape `Money` é gerado pelo NSwag a partir do OpenAPI — não redefinir manualmente
> - `minimumFractionDigits: 2` / `maximumFractionDigits: 4` alinhado com `DECIMAL(18,4)` (ADR-002)

---

## PT-BR Validation Patterns

Padrões canônicos de validação para campos de texto em sistemas brasileiros.
Consumido por: `ava-stack-dotnet-backend` (G10), `ava-stack-angular-frontend` (GUARDRAIL Unicode Regex PT-BR).

> **Invariant:** NUNCA usar `[a-zA-Z]` para validar campos de texto em domínios PT-BR.
> SEMPRE usar `\p{L}` (categoria Unicode "Letter") com a flag `u` no frontend.

### Angular — Validators.pattern (Reactive Forms)

| Campo | Padrão canônico (`u` flag obrigatória) | Padrão proibido |
|---|---|---|
| Nome / texto livre | `/^[\p{L}\s\-']+$/u` | `/^[a-zA-Z\s]+$/` |
| Busca / filtro texto | `/^[\p{L}\d\s\-'.]+$/u` | `/^[a-zA-Z0-9\s]+$/` |
| CPF | `/^\d{3}\.\d{3}\.\d{3}-\d{2}$/` | — |
| CNPJ | `/^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/` | — |
| CEP | `/^\d{5}-?\d{3}$/` | — |
| Telefone | `/^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$/` | — |
| E-mail | usar `Validators.email` (builtin) | — |

### C# — [RegularExpression] (System.ComponentModel.DataAnnotations)

| Campo | Padrão canônico | Padrão proibido |
|---|---|---|
| Nome / texto livre | `@"^\p{L}[\p{L}\s'-]*$"` | `@"^[a-zA-Z\s]+$"` |
| Descrição longa | `@"^[\p{L}\p{N}\s\-'.,!?()]+$"` | `@"^[a-zA-Z0-9\s]+$"` |
| CPF | `@"^\d{3}\.\d{3}\.\d{3}-\d{2}$"` | — |
| CEP | `@"^\d{5}-?\d{3}$"` | — |

> **Exemplos de nomes válidos PT-BR que DEVEM ser aceitos:**
> José, João, Márcia, Renata, André, Ângela, Luís, Conceição, Sebastião, Cristóvão.
## Padrões de Data e Hora

O sistema exibe datas no formato **DD/MM/YYYY** (padrão brasileiro). A ausência de configuração
de locale resulta no formato americano MM/DD/YYYY — um bug de apresentação crítico.

### Configuração de Locale (app.config.ts)

```typescript
// ✅ Correto — app.config.ts com locale pt-BR
import { ApplicationConfig, LOCALE_ID } from '@angular/core';
import { registerLocaleData } from '@angular/common';
import localePtBr from '@angular/common/locales/pt';
import { MAT_DATE_LOCALE } from '@angular/material/core';

registerLocaleData(localePtBr);

export const appConfig: ApplicationConfig = {
  providers: [
    { provide: LOCALE_ID,        useValue: 'pt-BR' },  // DatePipe, CurrencyPipe, etc.
    { provide: MAT_DATE_LOCALE,  useValue: 'pt-BR' },  // MatDatepicker
    // ...
  ],
};

// ❌ Incorreto — LOCALE_ID ausente (exibe MM/DD/YYYY no browser)
export const appConfig: ApplicationConfig = {
  providers: [ /* sem LOCALE_ID */ ],
};
```

### DatePipe — Formato Explícito Obrigatório

```html
<!-- ✅ Correto — formato dd/MM/yyyy explícito -->
{{ item.dueDate   | date:'dd/MM/yyyy' }}
{{ item.createdAt | date:'dd/MM/yyyy HH:mm' }}

<!-- ❌ Incorreto — pipe sem argumento (formato depende do ambiente) -->
{{ item.dueDate | date }}
{{ item.dueDate | date:'short' }}

<!-- ❌ Incorreto — formatação inline sem pipe -->
{{ item.dueDate.toLocaleDateString() }}
new Date(item.dueDate).toLocaleDateString('pt-BR')  <!-- nunca inline no template -->
```

### Fluxo API → Frontend

A API retorna datas em **ISO 8601 UTC** (`2026-07-06T00:00:00Z`).
O `DatePipe` com `'dd/MM/yyyy'` converte corretamente para `06/07/2026`.

```
API response: { "dueDate": "2026-07-06T00:00:00Z" }
                                ↓  DatePipe:'dd/MM/yyyy'
Template output: "06/07/2026"
```

> **Invariants:**
> - `LOCALE_ID='pt-BR'` **obrigatório** em `app.config.ts` — sem exceções
> - `registerLocaleData(localePtBr)` **obrigatório** antes de usar DatePipe com pt-BR
> - `MAT_DATE_LOCALE='pt-BR'` **obrigatório** em projetos com `@angular/material`
> - `DatePipe` SEMPRE com argumento `'dd/MM/yyyy'` — nunca chamado sem formato
> - Datas ISO 8601 da API são exibidas como DD/MM/YYYY — nenhuma conversão manual necessária
> - `DateTime.Now` / `DateTimeKind.Local` no backend geram offsets incorretos → ver G10 em coder-dotnet-backend.md
