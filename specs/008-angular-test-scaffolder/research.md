# Research: Angular Test Scaffolder

**Feature**: 008-angular-test-scaffolder
**Created**: 2026-07-09

---

## R-01: Test Runner — Karma vs Jest

**Decision**: Default to **Karma + Jasmine** (Angular CLI default).  
**Rationale**: The agent already scaffolds `karma.conf.js`, `@types/jasmine`, `karma-coverage`, and `karma-jasmine` in Step 2 (`package.json` devDependencies). Using a different runner would require re-scaffolding those files. If `tobe_stack.test_runner = "jest"` is present in `project-config.yaml`, the agent MUST switch to Jest syntax — but Karma+Jasmine is the safe default requiring no additional configuration.  
**Alternatives considered**: Jest (faster, no browser) — deferred; Jest migration is a separate PBI. Playwright CT — out of scope for unit tests.  
**Resolution**: Use Karma+Jasmine syntax. Read `project-config.yaml → tobe_stack.test_runner` at Step 9.5 start; if `"jest"`, emit a WARNING and continue with Karma/Jasmine (Jest migration not in scope for this PBI).

---

## R-02: angular.json Coverage Threshold Format

**Decision**: Insert under `projects.<project-name>.architect.test.options` as:
```json
"codeCoverage": true,
"codeCoverageExclude": [],
"karmaConfig": "karma.conf.js",
"coverageThreshold": {
  "statements": 80,
  "branches": 80,
  "functions": 80,
  "lines": 80
}
```
**Rationale**: `coverageThreshold` is the Angular/Karma option recognised by `karma-coverage` v2.x (already in devDependencies at `~2.2.0`). Setting `codeCoverage: true` by default ensures the threshold is enforced on every `ng test` run.  
**Alternatives considered**: Setting threshold in `karma.conf.js` directly — less discoverable; Angular recommends `angular.json`.  
**Resolution**: The agent modifies the generated `angular.json` in Step 2 (scaffold root) AND adds a Consistency Gate check in Step 10. The `coverageThreshold` values come from a constant in the agent — no hardcoding of Angular version.

---

## R-03: HttpClientTestingModule Mock Pattern

**Decision**: Use `provideHttpClient()` + `provideHttpClientTesting()` (Angular 17+ standalone API).  
**Rationale**: The agent already targets `frontend_version: "17"` from ConfigStackDotNet.yaml. `HttpClientModule`/`HttpClientTestingModule` are the legacy NgModule API. Angular 17 standalone projects use `provideHttpClient(withInterceptors([]))` + `provideHttpClientTesting()` in `TestBed.configureTestingModule({ providers: [...] })`.  
**Alternatives considered**: `HttpClientTestingModule` (still works in v17 but deprecated path) — rejected to stay consistent with the agent's standalone-first mandate.  
**Resolution**: Service spec template uses:
```typescript
TestBed.configureTestingModule({
  providers: [
    {provider-name},
    provideHttpClient(),
    provideHttpClientTesting()
  ]
});
```

---

## R-04: MsalService Mock Pattern for Guards

**Decision**: Provide a minimal `MsalService` stub via `{ provide: MsalService, useValue: mockMsalService }`.  
**Rationale**: Full `MsalService` requires `IPublicClientApplication` which in turn requires real MSAL config. A simple stub object satisfying the `canActivate` call chain is safer and faster.  
**Template stub**:
```typescript
const mockMsalService = {
  instance: { getActiveAccount: () => null, getAllAccounts: () => [] }
};
const mockAuthService = { isAuthenticated: jasmine.createSpy('isAuthenticated').and.returnValue(true) };
```
**Resolution**: Guard spec provides both stubs. Interceptor spec uses `HttpClientTestingModule` + `HTTP_INTERCEPTORS` token injection.

---

## R-05: Interceptor Spec Pattern (Angular 17 Functional Interceptors)

**Decision**: Use `withInterceptors([interceptorFn])` in `TestBed` providers.  
**Rationale**: The agent generates functional interceptors (`export const authInterceptor: HttpInterceptorFn`) per Angular 17 standalone convention. Class-based `HTTP_INTERCEPTORS` multi-provider is the old pattern.  
**Resolution**: Interceptor spec template:
```typescript
TestBed.configureTestingModule({
  providers: [
    provideHttpClient(withInterceptors([authInterceptor])),
    provideHttpClientTesting(),
    { provide: MsalService, useValue: mockMsalService }
  ]
});
```

---

## R-06: Where to Insert the New Execution Step

**Decision**: Insert as **Step 9.5 — Test Scaffolder** between the current Step 9 (Route Consolidation + Sidenav Layout) and Step 10 (Quality Gate + Docs).  
**Rationale**: Tests reference components, services, guards and pipes that must all exist before the scaffold runs. Placing it after Step 9 guarantees all source files exist. Placing it before Step 10 means the Consistency Gate can include a test-file check.  
**Resolution**: Step 10 Consistency Gate gains 2 new checklist items:
- `[✅|❌]` Each `{bc}.service.ts` has `{bc}.service.spec.ts`
- `[✅|❌]` `angular.json → coverageThreshold` is set to 80

---

## R-07: Pipe Spec Test Case Generation

**Decision**: For each `transform(value, ...args)` signature detected in the pipe, generate 3 test cases: nominal value, null/undefined input (edge), and invalid type.  
**Rationale**: A pipe spec with only `it('should be created', ...)` gives near-zero branch coverage on the transform logic.  
**Resolution**: Agent instruction tells the model to inspect the pipe's `transform()` signature and generate appropriate Jasmine `it()` blocks. Template structure:
```typescript
describe('{PipeName}Pipe', () => {
  it('should create an instance', () => expect(new {PipeName}Pipe()).toBeTruthy());
  it('should transform {nominal_value}', () => expect(pipe.transform({input})).toBe({expected}));
  it('should return empty string for null input', () => expect(pipe.transform(null)).toBe(''));
});
```

---

## R-08: Version Bump

**Decision**: `1.0.0` → `1.1.0` (MINOR bump).  
**Rationale**: New non-breaking behaviour (test scaffolding) added as an optional execution step. No existing output paths removed or changed. Existing projects with `pipeline_mode: generic` auto-benefit on next invocation.  
**Alternatives**: PATCH (too small — this is visible new behaviour); MAJOR (no breaking changes).  
**Resolution**: Bump version in frontmatter. Also remove the duplicate `version:` and `date:` keys currently in the frontmatter (bugfix in same MINOR bump).
