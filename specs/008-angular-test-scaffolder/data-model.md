# Data Model: Angular Test Scaffolder

**Feature**: 008-angular-test-scaffolder
**Created**: 2026-07-09

This document defines the **spec file templates** (the "data model" of the test scaffold) — the structural blueprint for each Angular component type's `*.spec.ts` file that the agent will generate.

---

## 1. Component Type Registry

| Component Type | Source File Pattern | Spec Output Pattern | Mock Dependencies |
|---|---|---|---|
| Service | `{bc}/{name}.service.ts` | `{bc}/{name}.service.spec.ts` | `provideHttpClient()`, `provideHttpClientTesting()` |
| Guard (functional) | `{bc}/guards/{name}.guard.ts` | `{bc}/guards/{name}.guard.spec.ts` | `MsalService` stub, `AuthService` stub, `Router` stub |
| Interceptor (functional) | `core/interceptors/{name}.interceptor.ts` | `core/interceptors/{name}.interceptor.spec.ts` | `provideHttpClient(withInterceptors([...]))`, `provideHttpClientTesting()`, `MsalService` stub |
| Pipe | `shared/pipes/{name}.pipe.ts` | `shared/pipes/{name}.pipe.spec.ts` | None (pure class instantiation) |

---

## 2. Template Structures

### 2.1 Service Spec Template

```typescript
// {name}.service.spec.ts  — Angular {frontend_version}
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { {ServiceClass} } from './{name}.service';

describe('{ServiceClass}', () => {
  let service: {ServiceClass};

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        {ServiceClass},
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });
    service = TestBed.inject({ServiceClass});
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // One it() block per public method — generated from source inspection
  // it('should {method_description}', () => { ... });
});
```

**Invariants**:
- Always use `provideHttpClient()` + `provideHttpClientTesting()` (Angular 17+ standalone API)
- One `it()` block per public method declared in the service
- Methods returning `Observable<T>` → test with `HttpTestingController`

---

### 2.2 Guard Spec Template (Functional Guard)

```typescript
// {name}.guard.spec.ts  — Angular {frontend_version}
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { MsalService } from '@azure/msal-angular';
import { {GuardFn} } from './{name}.guard';

const mockMsalService = {
  instance: {
    getActiveAccount: () => null,
    getAllAccounts: () => []
  }
};
const mockRouter = { navigate: jasmine.createSpy('navigate') };

describe('{GuardFn}', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        { provide: MsalService, useValue: mockMsalService },
        { provide: Router, useValue: mockRouter }
      ]
    });
  });

  it('should allow navigation when user is authenticated', () => {
    mockMsalService.instance.getActiveAccount = () => ({ username: 'user@test.com' } as any);
    const result = TestBed.runInInjectionContext(() => {guardFnName}({} as any, {} as any));
    expect(result).toBeTrue();
  });

  it('should deny navigation when user is not authenticated', () => {
    mockMsalService.instance.getActiveAccount = () => null;
    const result = TestBed.runInInjectionContext(() => {guardFnName}({} as any, {} as any));
    expect(result).toBeFalse();
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/login']);
  });
});
```

**Invariants**:
- Use `TestBed.runInInjectionContext()` for functional guards (Angular 17)
- Always test both `canActivate: true` and `canActivate: false` paths
- Never import the real `MsalModule` — always stub

---

### 2.3 Interceptor Spec Template (Functional Interceptor)

```typescript
// {name}.interceptor.spec.ts  — Angular {frontend_version}
import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors, HttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { MsalService } from '@azure/msal-angular';
import { {interceptorFn} } from './{name}.interceptor';

const mockMsalService = {
  instance: { getActiveAccount: () => null }
};

describe('{interceptorFn}', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([{interceptorFn}])),
        provideHttpClientTesting(),
        { provide: MsalService, useValue: mockMsalService }
      ]
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should pass the request through', () => {
    http.get('/api/test').subscribe();
    const req = httpMock.expectOne('/api/test');
    expect(req.request.method).toBe('GET');
    req.flush({});
  });
});
```

**Invariants**:
- Use `withInterceptors([fn])` — NOT `HTTP_INTERCEPTORS` multi-provider
- Always call `httpMock.verify()` in `afterEach`

---

### 2.4 Pipe Spec Template

```typescript
// {name}.pipe.spec.ts  — Angular {frontend_version}
import { {PipeClass} } from './{name}.pipe';

describe('{PipeClass}', () => {
  let pipe: {PipeClass};

  beforeEach(() => {
    pipe = new {PipeClass}();
  });

  it('should create an instance', () => {
    expect(pipe).toBeTruthy();
  });

  // Nominal transformation
  it('should transform {nominal_input} to {nominal_output}', () => {
    expect(pipe.transform({nominal_input})).toBe({nominal_output});
  });

  // Null/undefined guard
  it('should return empty string for null input', () => {
    expect(pipe.transform(null as any)).toBe('');
  });

  // Invalid type guard
  it('should return empty string for invalid input', () => {
    expect(pipe.transform({invalid_input} as any)).toBe('');
  });
});
```

**Invariants**:
- Pipes are pure classes — no `TestBed` needed
- Always include 3 test cases minimum: nominal, null, invalid
- Nominal input/output derived from the pipe's `transform()` signature inspection

---

## 3. angular.json Coverage Threshold

New fields added to `projects.<project-name>.architect.test.options` in the generated `angular.json`:

```json
{
  "codeCoverage": true,
  "coverageThreshold": {
    "statements": 80,
    "branches": 80,
    "functions": 80,
    "lines": 80
  }
}
```

Values are **not** hardcoded in the agent — they come from `project-config.yaml → coverage_threshold` if present, defaulting to 80.

---

## 4. Consistency Gate — New Checklist Items

Two new items appended to the Step 10 Consistency Verification Gate:

```
TESTES UNITÁRIOS
[✅|❌] Cada service.ts em {bounded_contexts} tem service.spec.ts correspondente
[✅|❌] angular.json → coverageThreshold configurado com mínimo 80
```

---

## 5. Scope Boundary

| In Scope | Out of Scope |
|---|---|
| `*.service.spec.ts` for services | Component `.spec.ts` (next PBI) |
| `*.guard.spec.ts` for guards | E2E test generation |
| `*.interceptor.spec.ts` for interceptors | Jest migration |
| `*.pipe.spec.ts` for pipes | `build-cycle` pipeline path |
| Coverage threshold in `angular.json` | Sophia project execution (PBI 2287 — manual gate) |
