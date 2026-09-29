# Data Model: coder-react-frontend Agent

## Agent Structure

The agent `coder-react-frontend.md` is an **LLM prompt file** (not compiled code).
Its "data model" is the structure of its instruction sections and the contracts it
exchanges with the pipeline.

---

## Input Contract Fields

| Field | Type | Source | Criticality |
|-------|------|--------|-------------|
| `project_name` | string | `project-config.yaml` | HARD STOP if absent |
| `pipeline_mode` | string | `project-config.yaml` | HARD STOP — must be `"generic"` |
| `frontend_framework` | string | `project-config.yaml → tobe_stack.frontend_framework` | HARD STOP — must be `"react"` |
| `frontend_version` | string | `project-config.yaml → tobe_stack.frontend_version` | Required (e.g. `"18"`) |
| `auth_provider` | string | `project-config.yaml → auth.provider` | Required (e.g. `"azure-ad"`, `"none"`) |
| `bounded_contexts` | string[] | derived from `bounded-context-map.md` + task description | Required |
| `trace_id` | string | `project-config.yaml → trace_id` | Required |
| `ui_library` | string | `project-config.yaml → tobe_stack.ui_library` | Optional (defaults to Recharts + no component lib) |
| `openapi_spec_paths` | map[bc → url/path] | `project-config.yaml → tobe_stack.openapi_specs` | Optional (degraded mode if absent) |
| `language` | string | `project-config.yaml → language` | Optional (default `"pt"`) |
| `client_name` | string | `project-config.yaml → client_name` | Optional |
| `react_patterns` | file | `src/shared/data/patterns/react/` (if it exists) | Optional reference |

---

## Output Contract Paths

```
projects/{project_name}/outputs/tobe/source-code/frontend/
  ├── index.html
  ├── vite.config.ts
  ├── tsconfig.json
  ├── vitest.config.ts
  ├── package.json
  └── src/
      ├── main.tsx
      ├── App.tsx
      └── features/
          └── {bc-name}/
              ├── components/
              │   ├── {ComponentName}.tsx
              │   └── {ComponentName}.spec.tsx
              ├── hooks/
              │   ├── use{Domain}Query.ts
              │   └── use{Domain}Mutation.ts
              ├── stores/
              │   └── {domain}Store.ts
              ├── services/
              │   └── {domain}Api.ts
              └── types/
                  ├── index.ts
                  └── api.d.ts          # generated from openapi-typescript

projects/{project_name}/outputs/tobe/docs/
  ├── delivery/
  │   ├── ImplementationNotes.md
  │   └── ChangedScreens.md
  └── security/
      └── SecurityComplianceReport-Frontend.md
```

---

## Agent Section Structure (Instruction Body)

The agent `.md` file body is organized in these sections (in order):

1. **Routing Guard** — Checks `pipeline_mode` and `frontend_framework`; HARD STOP on mismatch
2. **Transition Notifications** — Start/completion banners (parity with Angular agent)
3. **Data Sovereignty Rule** — No workspace data to external endpoints
4. **Role & Persona** — Desenvolvedor React sênior, TypeScript strict
5. **Input Contract** — YAML block with all fields above
6. **Output Contract** — YAML block with all output paths
7. **Required Scaffolding Files** — Non-negotiable files that prevent `vite build` failure
8. **Padrões Obrigatórios** — Mandatory patterns (Vite, TS strict, feature-based structure, etc.)
9. **Modal Pattern** — isOpen boolean, typed props, no state leakage
10. **FilterPanel Pattern** — Zustand `useFilterStore`, `useMemo` with AND-conjunction
11. **CRUD Pattern** — useQuery + useMutation + cache invalidation
12. **Update Form Pattern** — useQuery pre-population on mount
13. **Service Layer** — openapi-typescript codegen flow
14. **Chart Guardrail** — Schema-driven axis key resolution
15. **Security Invariants** — XSS, PII, secrets, input validation
16. **Accessibility Invariants** — WCAG 2.1 AA (parity with Angular agent)
17. **Testing Requirements** — Vitest + RTL spec generation rules
18. **Security Compliance Review Gate** — Runs after codegen, before handoff
19. **Execution Steps** — Numbered steps (1–N)
20. **Handoff** — next_agent, AgentResult structure

---

## AgentResult Structure (JSON handoff)

```json
{
  "agent": "ava-stack-react-frontend",
  "version": "1.0.0",
  "trace_id": "{trace_id}",
  "success": true,
  "next_agent": "ava-stack-orchestrator",
  "artifacts": [
    "projects/{project_name}/outputs/tobe/source-code/frontend/index.html",
    "projects/{project_name}/outputs/tobe/source-code/frontend/src/features/{bc}/..."
  ],
  "security_gate": "APPROVED | APPROVED_WITH_RISKS | BLOCKED",
  "risk": {
    "level": "low | medium | high | critical",
    "findings": []
  },
  "implementation": {
    "status": "COMPLETE",
    "bounded_contexts_generated": ["{bc1}", "{bc2}"],
    "openapi_missing_for": [],
    "stub_patterns_used": []
  }
}
```

---

## Version Bump Assessment

| From | To | Type | Reason |
|------|-----|------|--------|
| `0.1.0-stub` | `1.0.0` | **MAJOR** | Output Contract changes from empty (`outputs_generated: []`) to full artifact set; `implementation.status` changes from `STUB` to `COMPLETE`; all downstream consumers that check `status: STUB` must be updated (stub-registry.yaml, module.yaml, orchestrator-stack.md) |
