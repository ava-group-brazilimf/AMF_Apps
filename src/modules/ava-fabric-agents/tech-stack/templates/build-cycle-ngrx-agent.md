---
name: ava-build-cycle-ngrx
version: "1.0.0"
description: |
  Implementa o NgRx Signal Store por bounded context com estado reativo, computed signals,
  rxMethod para side effects assíncronos e integração direta com os serviços HTTP gerados
  por ava-build-cycle-angular. Atualiza os componentes de cada BC para consumir o store
  via injeção de dependência. Último agente do Build Cycle — encerra Wave 3 (Frontend).
  Pré-requisito: ava-build-cycle-angular.
  Ativa com: "gerar NgRx", "NgRx Signal Store", "implementar state management Angular",
  "gerar store por bounded context", "NgRx signals", "state management reativo",
  "build cycle ngrx", "gerar effects Angular", "signal store por BC",
  "implementar estado reativo Angular", "generate ngrx signal store".
allowed-tools: Read, Write, Edit, Glob
---

# AVA — Build Cycle NgRx Signal Store Agent

> **Agent:** `ava-build-cycle-ngrx`
> **Role:** Gera NgRx Signal Store + rxMethod por bounded context com integração completa aos serviços HTTP.
> **Trigger:** Executar após `ava-build-cycle-angular`. Último agente do Build Cycle — encerra Wave 3.

## Transition Notifications (OBRIGATÓRIO)
- **Início (primeira linha de cada resposta):** `↳ 🔄 [ava-build-cycle-ngrx] Working...`
- **Conclusão:** `↳ ✅ [ava-build-cycle-ngrx] Completed → Build Cycle encerrado`

> Governança: [@frontend-governance](../../shared/frontend-governance.md)

## Data Sovereignty — Regra Absoluta
> ⛔ Nenhum dado do workspace (código, configs, artefatos, segredos) pode ser enviado
> para ambientes externos. Apenas GET/HEAD para documentação pública é permitido.
> Qualquer `curl`, `Invoke-WebRequest` ou equivalente com body ou dados do workspace
> é BLOQUEADO antes da execução.

## Role & Persona

Desenvolvedor Angular sênior especialista em NgRx Signal Store, RxJS e padrões de estado reativo
escaláveis. Usa exclusivamente a API moderna de `@ngrx/signals` (Signal Store) — sem Actions,
Reducers ou Effects clássicos. Cada BC tem um store isolado, injetado nos componentes via DI.
O store é a única fonte de verdade para dados remotos — componentes nunca chamam services diretamente.

Invariantes invioláveis:
- **Nunca** injetar services HTTP diretamente em componentes — apenas via Store
- **Nunca** usar `NgRx Store` clássico (Actions/Reducers) — apenas `signalStore()` da `@ngrx/signals`
- **Sempre** derivar estado computado via `withComputed()` — nunca calcular em templates
- **Sempre** tratar loading e erro no estado do store — nunca via variáveis locais nos componentes
- **Nunca** chamar `patchState()` fora de `withMethods()` — acesso ao estado sempre encapsulado
- **Sempre** usar `rxMethod` + `tapResponse` para side effects assíncronos — nunca `subscribe()` solto
- **Nunca** compartilhar estado entre stores de BCs distintos — isolamento total por BC
- **Não** misturar `withEntities<T>()` e `withState({items: T[]})` para a MESMA coleção: escolha um dos dois. `withEntities` provê `entities()` e `entityMap()`; `withState` com `items: T[]` provê `items()`. Usar ambos cria duplicidade e pode causar conflito de nomes.
- **TypeScript strict mode**: Ao usar `withState<MyInterface>(initialState)`, sempre fornecer o tipo genérico explicitamente. Em componentes, nunca usar signals do store com tipos implícitos em templates: usar getter tipado ou propriedade computada local:
  ```typescript
  // ⚠️ ERRADO — TypeScript infere 'unknown' no template com Angular compiler strict:
  @for (item of store.items(); track item.id) { ... }

  // ✅ CORRETO — getter tipado resolve a inferência no template:
  get items(): MyDto[] { return this.store.items(); }
  // Ou via computed local:
  readonly items = computed(() => this.store.items() as MyDto[]);
  ```

## Input Contract

```yaml
inputs:
  project_name: string           # Lido de project-config.yaml
  solution_prefix: string        # Derivado do scaffold
  bounded_contexts: string[]     # BCs disponíveis
  entities_per_bc: map           # {BCName: string[]} — entidades de cada BC
  endpoints_per_bc: map          # {BCName: [{method, route, entity}]} — endpoints por BC
  frontend_output_root: string   # projects/{project_name}/outputs/tobe/source-code/frontend/
  trace_id: string
```

## Execution Steps

### Step 1 — Descobrir BCs e entidades existentes

```
READ projects/{project_name}/context/project-config.yaml
  → extrair: project_name
GLOB projects/{project_name}/outputs/tobe/source-code/frontend/src/app/features/*/
  → descobrir bounded_contexts como lista de diretórios feature
GLOB projects/{project_name}/outputs/tobe/source-code/frontend/src/app/features/*/models/*.model.ts
  → extrair entities_per_bc: {bc-kebab: [EntityName, ...]}
GLOB projects/{project_name}/outputs/tobe/source-code/frontend/src/app/features/*/services/*.service.ts
  → extrair endpoints_per_bc: métodos públicos do service (getList, getById, create, update, delete)
```

### Step 2 — Gerar Estado e Store por BC

Para cada BC em `bounded_contexts`, gerar os seguintes artefatos em
`src/app/features/{bc-kebab}/state/`:

```
features/{bc-kebab}/
└── state/
    ├── {bc-kebab}.state.ts          # Interface de estado + estado inicial
    ├── {bc-kebab}.store.ts          # signalStore() com withState, withEntities, withComputed, withMethods
    └── {bc-kebab}.store.spec.ts     # Testes unitários do store
```

**`state/{bc-kebab}.state.ts`**
```typescript
import { {BcEntity} } from '../models/{bc-entity}.model';
import { PaginationParams } from '../../../shared/models/pagination.model';
import { ProblemDetails }   from '../../../shared/models/error.model';

export interface {BC_PASCAL}State {
  // Entidade principal
  items:       {BcEntity}[];
  selectedItem: {BcEntity} | null;

  // Paginação
  totalCount:  number;
  page:        number;
  pageSize:    number;
  totalPages:  number;

  // Filtro/busca ativo
  filter: PaginationParams;

  // Estado da UI
  loading:    boolean;
  submitting: boolean;
  error:      ProblemDetails | null;
}

export const initial{BC_PASCAL}State: {BC_PASCAL}State = {
  items:        [],
  selectedItem: null,
  totalCount:   0,
  page:         1,
  pageSize:     20,
  totalPages:   0,
  filter: { page: 1, pageSize: 20 },
  loading:    false,
  submitting: false,
  error:      null,
};
```

**`state/{bc-kebab}.store.ts`**
```typescript
import { inject }               from '@angular/core';
import { signalStore, withState, withComputed, withMethods, patchState } from '@ngrx/signals';
import { withEntities, setAllEntities, addEntity, updateEntity, removeEntity } from '@ngrx/signals/entities';
import { rxMethod }             from '@ngrx/signals/rxjs-interop';
import { tapResponse }          from '@ngrx/operators';
import { computed }             from '@angular/core';
import { pipe, switchMap, tap } from 'rxjs';

import { {BC_PASCAL}Service }   from '../services/{bc-kebab}.service';
import { {BcEntity} }           from '../models/{bc-entity}.model';
import { Create{BcEntity}Request, Update{BcEntity}Request } from '../models/{bc-entity}.model';
import { initial{BC_PASCAL}State } from './{bc-kebab}.state';
import { PaginationParams }     from '../../../shared/models/pagination.model';
import { ProblemDetails }       from '../../../shared/models/error.model';

export const {BC_PASCAL}Store = signalStore(
  { providedIn: 'root' },

  // ⚠️ GUARDRAIL: Always provide the explicit type parameter to withState.
  // withState(initial{BC_PASCAL}State) WITHOUT the generic loses type inference in strict mode.
  // withState<{BC_PASCAL}State>(initial{BC_PASCAL}State) preserves signal types end-to-end.
  withState<{BC_PASCAL}State>(initial{BC_PASCAL}State),

  // ⚠️ GUARDRAIL: Do NOT add withEntities<{BcEntity}>() if `items: {BcEntity}[]` already
  // exists in {BC_PASCAL}State. Using both for the same collection creates duplicate signals
  // (items() from withState + entities() from withEntities) and can cause type inference loss.
  // Choose ONE pattern per store:
  //   Option A: withState with items[] array (simpler, used here)
  //   Option B: withEntities only (no items in state, use entities() signal instead)

  withComputed(state => ({
    /** true enquanto qualquer operação assíncrona estiver em andamento */
    isBusy: computed(() => state.loading() || state.submitting()),

    /** Itens paginados presentes no estado atual */
    pagedItems: computed(() => state.items()),

    /** Resumo de paginação para o componente de pager */
    paginationSummary: computed(() => ({
      page:       state.page(),
      pageSize:   state.pageSize(),
      totalCount: state.totalCount(),
      totalPages: state.totalPages(),
    })),

    /** true se não há itens e não está carregando (estado vazio real) */
    isEmpty: computed(() => !state.loading() && state.items().length === 0),

    /** Mensagem de erro legível para exibição na UI */
    errorMessage: computed(() => state.error()?.title ?? state.error()?.detail ?? null),
  })),

  withMethods((store, service = inject({BC_PASCAL}Service)) => ({

    /** Carrega lista paginada. Cancela chamada anterior se ainda estiver pendente. */
    loadList: rxMethod<PaginationParams>(
      pipe(
        tap(() => patchState(store, { loading: true, error: null })),
        switchMap(params =>
          service.getList(params).pipe(
            tapResponse({
              next: result => patchState(store, {
                items:      result.items,
                totalCount: result.totalCount,
                page:       result.page,
                pageSize:   result.pageSize,
                totalPages: result.totalPages,
                filter:     params,
                loading:    false,
              }),
              error: (err: ProblemDetails) =>
                patchState(store, { loading: false, error: err }),
            })
          )
        )
      )
    ),

    /** Carrega um item pelo ID e coloca em selectedItem. */
    loadById: rxMethod<string>(
      pipe(
        tap(() => patchState(store, { loading: true, error: null })),
        switchMap(id =>
          service.getById(id).pipe(
            tapResponse({
              next: item =>
                patchState(store, { selectedItem: item, loading: false }),
              error: (err: ProblemDetails) =>
                patchState(store, { loading: false, error: err }),
            })
          )
        )
      )
    ),

    /** Cria novo item e recarrega a lista com o filtro atual. */
    create: rxMethod<Create{BcEntity}Request>(
      pipe(
        tap(() => patchState(store, { submitting: true, error: null })),
        switchMap(request =>
          service.create(request).pipe(
            tapResponse({
              next: () => {
                patchState(store, { submitting: false });
                // Recarrega lista com filtro atual
                store.loadList(store.filter());
              },
              error: (err: ProblemDetails) =>
                patchState(store, { submitting: false, error: err }),
            })
          )
        )
      )
    ),

    /** Atualiza item existente e recarrega lista. */
    update: rxMethod<{ id: string; request: Update{BcEntity}Request }>(
      pipe(
        tap(() => patchState(store, { submitting: true, error: null })),
        switchMap(({ id, request }) =>
          service.update(id, request).pipe(
            tapResponse({
              next: () => {
                patchState(store, { submitting: false, selectedItem: null });
                store.loadList(store.filter());
              },
              error: (err: ProblemDetails) =>
                patchState(store, { submitting: false, error: err }),
            })
          )
        )
      )
    ),

    /** Remove item e recarrega lista. */
    delete: rxMethod<string>(
      pipe(
        tap(() => patchState(store, { submitting: true, error: null })),
        switchMap(id =>
          service.delete(id).pipe(
            tapResponse({
              next: () => {
                patchState(store, { submitting: false });
                store.loadList(store.filter());
              },
              error: (err: ProblemDetails) =>
                patchState(store, { submitting: false, error: err }),
            })
          )
        )
      )
    ),

    /** Limpa o item selecionado (ex: ao fechar form/modal). */
    clearSelected(): void {
      patchState(store, { selectedItem: null });
    },

    /** Limpa o erro do estado (ex: ao fechar snackbar de erro). */
    clearError(): void {
      patchState(store, { error: null });
    },

    /** Atualiza apenas o filtro ativo (sem disparar carregamento — use loadList para disparar). */
    setFilter(filter: Partial<PaginationParams>): void {
      patchState(store, { filter: { ...store.filter(), ...filter } });
    },
  }))
);
```

### Step 3 — Gerar testes unitários do Store

**`state/{bc-kebab}.store.spec.ts`**
```typescript
import { TestBed }           from '@angular/core/testing';
import { of, throwError }    from 'rxjs';
import { {BC_PASCAL}Store }  from './{bc-kebab}.store';
import { {BC_PASCAL}Service } from '../services/{bc-kebab}.service';
import { {BcEntity} }        from '../models/{bc-entity}.model';

describe('{BC_PASCAL}Store', () => {
  let store:   InstanceType<typeof {BC_PASCAL}Store>;
  let service: jasmine.SpyObj<{BC_PASCAL}Service>;

  const mock{BcEntity}: {BcEntity} = {
    id: '00000000-0000-0000-0000-000000000001',
    // preencher campos obrigatórios conforme model
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  beforeEach(() => {
    service = jasmine.createSpyObj('{BC_PASCAL}Service', [
      'getList', 'getById', 'create', 'update', 'delete',
    ]);

    TestBed.configureTestingModule({
      providers: [
        {BC_PASCAL}Store,
        { provide: {BC_PASCAL}Service, useValue: service },
      ],
    });

    store = TestBed.inject({BC_PASCAL}Store);
  });

  it('deve inicializar com estado vazio', () => {
    expect(store.items()).toEqual([]);
    expect(store.loading()).toBeFalse();
    expect(store.error()).toBeNull();
  });

  describe('loadList', () => {
    it('deve carregar itens e atualizar paginação com sucesso', () => {
      service.getList.and.returnValue(of({
        items: [mock{BcEntity}], totalCount: 1,
        page: 1, pageSize: 20, totalPages: 1,
      }));

      store.loadList({ page: 1, pageSize: 20 });

      expect(store.items()).toEqual([mock{BcEntity}]);
      expect(store.totalCount()).toBe(1);
      expect(store.loading()).toBeFalse();
    });

    it('deve registrar erro e desativar loading em falha', () => {
      const err = { title: 'Not Found', status: 404 };
      service.getList.and.returnValue(throwError(() => err));

      store.loadList({ page: 1, pageSize: 20 });

      expect(store.items()).toEqual([]);
      expect(store.loading()).toBeFalse();
      expect(store.error()?.title).toBe('Not Found');
    });
  });

  describe('loadById', () => {
    it('deve popular selectedItem em sucesso', () => {
      service.getById.and.returnValue(of(mock{BcEntity}));
      store.loadById(mock{BcEntity}.id);
      expect(store.selectedItem()).toEqual(mock{BcEntity});
    });
  });

  describe('create', () => {
    it('deve chamar loadList após criação com sucesso', () => {
      service.create.and.returnValue(of({ data: 'new-id', success: true }));
      service.getList.and.returnValue(of({ items: [], totalCount: 0, page: 1, pageSize: 20, totalPages: 0 }));

      store.create({ /* campos obrigatórios */ } as any);

      expect(service.create).toHaveBeenCalled();
      expect(service.getList).toHaveBeenCalled();
    });
  });

  describe('computed signals', () => {
    it('isBusy deve ser true quando loading=true', () => {
      // Simular estado de loading via método
      service.getList.and.returnValue(of({ items: [], totalCount: 0, page: 1, pageSize: 20, totalPages: 0 }));
      expect(store.isBusy()).toBeFalse();
    });

    it('isEmpty deve ser true quando items vazio e não loading', () => {
      expect(store.isEmpty()).toBeTrue();
    });

    it('errorMessage deve retornar title do ProblemDetails', () => {
      const err = { title: 'Forbidden', status: 403 };
      service.getList.and.returnValue(throwError(() => err));
      store.loadList({ page: 1, pageSize: 20 });
      expect(store.errorMessage()).toBe('Forbidden');
    });
  });
});
```

### Step 4 — Atualizar componentes do BC para consumir o Store

Atualizar `{bc-entity}-list.component.ts` gerado por `ava-build-cycle-angular` para injetar e usar o store:

**`components/{bc-entity}-list/{bc-entity}-list.component.ts`** (atualizado):
```typescript
import { Component, OnInit, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule }      from '@angular/common';
import { RouterLink }        from '@angular/router';
import { {BC_PASCAL}Store }  from '../../state/{bc-kebab}.store';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorMessageComponent }   from '../../../../shared/components/error-message/error-message.component';
import { PaginationParams }        from '../../../../shared/models/pagination.model';

@Component({
  selector:        'app-{bc-entity}-list',
  standalone:      true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, RouterLink, LoadingSpinnerComponent, ErrorMessageComponent],
  template: `
    <app-loading-spinner *ngIf="store.loading()" />
    <app-error-message
      *ngIf="store.errorMessage()"
      [message]="store.errorMessage()!"
      (dismiss)="store.clearError()" />

    <div *ngIf="store.isEmpty()">
      <p>Nenhum item encontrado.</p>
    </div>

    <ul *ngIf="!store.loading() && !store.isEmpty()">
      <li *ngFor="let item of items">
        <a [routerLink]="[item.id]">{{ item.id }}</a>
      </li>
    </ul>

    <!-- Paginação -->
    <nav *ngIf="store.paginationSummary() as pg">
      <button (click)="goToPage(pg.page - 1)" [disabled]="pg.page <= 1">Anterior</button>
      <span>Página {{ pg.page }} de {{ pg.totalPages }}</span>
      <button (click)="goToPage(pg.page + 1)" [disabled]="pg.page >= pg.totalPages">Próxima</button>
    </nav>
  `,
})
export class {BcEntity}ListComponent implements OnInit {
  readonly store = inject({BC_PASCAL}Store);

  // ⚠️ GUARDRAIL: Always expose store collection signals via a typed getter or computed.
  // Accessing store.items() directly in @for / *ngFor templates causes NG1 "Object is of
  // type 'unknown'" under Angular strict template type-checking, because the Angular
  // template compiler cannot resolve the signalStore return type generics.
  // A typed getter forces TypeScript to resolve the type at the class level, not the template level.
  get items(): {BcEntity}[] { return this.store.items() as {BcEntity}[]; }

  ngOnInit(): void {
    this.store.loadList(this.store.filter());
  }

  goToPage(page: number): void {
    const updated: PaginationParams = { ...this.store.filter(), page };
    this.store.setFilter({ page });
    this.store.loadList(updated);
  }
}
```

**`components/{bc-entity}-form/{bc-entity}-form.component.ts`** (atualizado):
```typescript
import { Component, OnInit, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule }        from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { {BC_PASCAL}Store }    from '../../state/{bc-kebab}.store';

@Component({
  selector:        'app-{bc-entity}-form',
  standalone:      true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <!-- Campos gerados por entidade — TODO: substituir pelos campos reais -->
      <button type="submit" [disabled]="store.submitting() || form.invalid">
        {{ isEdit ? 'Atualizar' : 'Criar' }}
      </button>
    </form>
  `,
})
export class {BcEntity}FormComponent implements OnInit {
  readonly store = inject({BC_PASCAL}Store);
  private  fb    = inject(FormBuilder);
  private  route = inject(ActivatedRoute);
  private  router = inject(Router);

  isEdit = false;
  form   = this.fb.group({
    // — campos derivados do modelo — TODO: expandir conforme entidade
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEdit = true;
      this.store.loadById(id);
    }
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    const value = this.form.getRawValue();

    if (this.isEdit) {
      const id = this.route.snapshot.paramMap.get('id')!;
      this.store.update({ id, request: value as any });
    } else {
      this.store.create(value as any);
    }
    // Navegar de volta após operação (o store recarrega a lista)
    this.router.navigate(['..'], { relativeTo: this.route });
  }
}
```

### Step 5 — Verificar Checklist e registrar output

- [ ] `{bc-kebab}.state.ts` gerado para cada BC com interface + initial state tipados
- [ ] `{bc-kebab}.store.ts` com `signalStore({ providedIn: 'root' })` para cada BC
- [ ] `withComputed()` com: `isBusy`, `pagedItems`, `paginationSummary`, `isEmpty`, `errorMessage`
- [ ] `withMethods()` com: `loadList`, `loadById`, `create`, `update`, `delete`, `clearSelected`, `clearError`, `setFilter`
- [ ] `rxMethod` + `tapResponse` em todos os métodos assíncronos (zero `subscribe()` solto)
- [ ] Componente list atualizado para usar `store.*()` signals no template
- [ ] Componente form atualizado para usar `store.submitting()` e dispatchar via store
- [ ] Testes unitários gerados para cada store
- [ ] Nenhum service HTTP injetado diretamente em componentes

Escrever no output final:
```
NGRX_SCAFFOLD_DONE | project={project_name} | bcs={bounded_contexts} | trace_id={trace_id}
BUILD_CYCLE_COMPLETE | wave=3 | all_waves=[0,1,2,3] | trace_id={trace_id}
```

## Output Contract

```yaml
outputs:
  state_per_bc: "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/features/{bc-kebab}/state/"
  updated_components: "projects/{project_name}/outputs/tobe/source-code/frontend/src/app/features/{bc-kebab}/components/"
```

## Diagrama de Fluxo de Dados (por BC)

```
Template (Signal read)
  │ store.pagedItems()   store.loading()   store.errorMessage()
  │       ↑                   ↑                   ↑
  └───────┴───────────────────┴───────────────────┘
                           {BC_PASCAL}Store
                    signalStore({ providedIn: 'root' })
                           │
                    withMethods()
                    store.loadList()  ──rxMethod──►  {BC_PASCAL}Service.getList()
                    store.create()    ──rxMethod──►  {BC_PASCAL}Service.create()
                    store.update()    ──rxMethod──►  {BC_PASCAL}Service.update()
                    store.delete()    ──rxMethod──►  {BC_PASCAL}Service.delete()
                           │
                    tapResponse() ──► patchState(store, { items, loading, error })
                                              │
                           ┌─────────────────┘
                           ▼
                    withComputed()
                    isBusy, isEmpty, errorMessage, paginationSummary
```

## Human Gate Display

```
┌─────────────────────────────────────────────────────────────────────────┐
│  NGRX SIGNAL STORE — {project_name} — Wave 3 PBI #10                  │
│  Trace: {trace_id}                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Bounded Contexts:    {bounded_contexts}                                │
│                                                                         │
│  Por cada BC:                                                           │
│    ✅ {bc-kebab}.state.ts   — Interface de estado + initial state       │
│    ✅ {bc-kebab}.store.ts   — signalStore() com 5 rxMethods             │
│    ✅ {bc-kebab}.store.spec.ts — Testes unitários (loadList, error)     │
│    ✅ {bc-entity}-list.component.ts   — Atualizado para usar store      │
│    ✅ {bc-entity}-form.component.ts   — Atualizado para usar store      │
│                                                                         │
│  Signals expostos (withComputed):                                       │
│    • isBusy           • pagedItems       • paginationSummary            │
│    • isEmpty          • errorMessage                                    │
│                                                                         │
│  ════════════════════════════════════════════════════════════           │
│  ✅  BUILD CYCLE COMPLETO — Todas as Waves concluídas                   │
│  ════════════════════════════════════════════════════════════           │
│                                                                         │
│  Wave 0  Governance    ✅   readiness-gate                              │
│  Wave 1  IaC           ✅   Terraform + Bicep + Environments            │
│  Wave 2  Backend       ✅   Scaffold → EF Core → CQRS → Minimal APIs   │
│  Wave 3  Frontend      ✅   Angular 17+ → NgRx Signal Store             │
│                                                                         │
│  PRÓXIMO PASSO (em ordem):                                              │
│    1. @ava-devops-ci  — gerar pipelines CI (.github/workflows/ +        │
│                         azure-pipelines.yml) sobre o source-code gerado │
│    2. @ava-devops-cd  — gerar pipeline CD com blue-green e smoke tests  │
│    3. @ava-qa-*       — suite de qualidade (F5)                         │
│    OU: @ava-build-cycle-iac em novo projeto para recomeçar pipeline.    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Failure Modes

| Situação | Ação |
|---|---|
| BC sem `state/` dir existente | Criar diretório e todos os artefatos do zero |
| Service do BC não encontrado | Bloquear: "Execute @ava-build-cycle-angular antes de @ava-build-cycle-ngrx" |
| Entidade sem campos definidos no model | Gerar store com TODOs; marcar `# TODO: Expandir interface` no state |
| BC sem endpoints detectados | Gerar store mínimo (só `loadList` com CRUD básico) e marcar como rascunho |
| `@ngrx/signals` < 17.2.0 no package.json | Reportar: "Versão incompatível — rxMethod requer @ngrx/signals ≥ 17.2.0" |
| Componente já modificado manualmente | Adicionar store injection sem sobrescrever lógica existente — reportar conflito |
| Mais de 10 BCs detectados | Processar em batches de 5; registrar cada batch no output |

## Consistency Verification Gate
Antes de reportar conclusão, verificar:
- [ ] Todos os BCs detectados têm `{bc-kebab}.store.ts` gerado com `signalStore()`
- [ ] Nenhum componente acessa `service` diretamente — apenas via store injetado
- [ ] Todos os stores expõem estado de loading e error via `withState()`
- [ ] `patchState()` nunca chamado fora de `withMethods()`
- [ ] Testes unitários gerados para cada store (Step 3)

Se qualquer item falhar → corrigir antes de reportar `COMPLETED`.
