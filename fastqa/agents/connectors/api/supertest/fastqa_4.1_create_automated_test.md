---
name: "fastqa_4.1_create_automated_test_supertest"
description: "Criador de Testes Automatizados — Supertest + TypeScript (API)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Supertest + TypeScript (API)

## 🎯 Objetivo
Gerar scripts automatizados em **Supertest + TypeScript** para testes de API REST.

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `folder_structure.custom_paths.automation_root` -> `{{AUTOMATION_ROOT}}`
- `folder_structure.custom_paths.tests` -> `{{TESTS_DIR}}`
- `folder_structure.custom_paths.config` -> `{{CONFIG_DIR}}`
- `folder_structure.custom_paths.results` (opcional) -> `{{RESULTS_DIR}}`

Fallback legado (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/api`
- `{{TESTS_DIR}} = automated_test/api/tests`
- `{{CONFIG_DIR}} = automated_test/api/config`
- `{{RESULTS_DIR}} = automated_test/api/results`

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** O nome dos arquivos é gerado a partir da **funcionalidade/endpoint informado pelo usuário** no passo 2 do workflow `automate_test`.
> - Arquivo: `{funcionalidade-kebab}.spec.ts`, `{funcionalidade-kebab}_data.json`
> - Exemplo: funcionalidade `"usuarios"` → `usuarios.spec.ts`, `usuarios_data.json`

```
{{AUTOMATION_ROOT}}/
├── config/
│   ├── api.config.ts
│   └── tsconfig.json
├── data/
│   └── {funcionalidade-kebab}_data.json
├── support/
│   ├── api-client.ts
│   └── schemas/
│       └── {funcionalidade-kebab}.schema.ts
├── tests/
│   └── {funcionalidade-kebab}.spec.ts
├── results/
├── package.json
└── jest.config.ts
```

---

## 📝 Templates

### Spec File (`{endpoint}.spec.ts`)
```typescript
import request from "supertest";
import { apiConfig } from "../config/api.config";
import loginData from "../data/login_data.json";

const baseUrl = apiConfig.baseUrl;

describe("{{FEATURE_NAME}}", () => {
  let authToken: string;

  beforeAll(async () => {
    const res = await request(baseUrl)
      .post("/auth/login")
      .send(loginData.adminUser);
    authToken = res.body.token;
  });

  test("deve retornar lista de usuários com sucesso", async () => {
    const response = await request(baseUrl)
      .get("/api/users")
      .set("Authorization", `Bearer ${authToken}`)
      .expect(200);

    expect(response.body).toHaveProperty("data");
    expect(Array.isArray(response.body.data)).toBe(true);
    expect(response.body.data.length).toBeGreaterThan(0);
  });

  test("deve retornar 401 sem token de autenticação", async () => {
    await request(baseUrl)
      .get("/api/users")
      .expect(401);
  });

  test("deve criar um novo usuário com dados válidos", async () => {
    const newUser = loginData.newUser;
    const response = await request(baseUrl)
      .post("/api/users")
      .set("Authorization", `Bearer ${authToken}`)
      .send(newUser)
      .expect(201);

    expect(response.body).toMatchObject({
      email: newUser.email,
      name: newUser.name,
    });
  });
});
```

### API Config (`api.config.ts`)
```typescript
export const apiConfig = {
  baseUrl: process.env.API_BASE_URL || "{{BASE_URL}}",
  timeout: 30000,
  retries: 2,
};
```

### API Client (`api-client.ts`)
```typescript
import request from "supertest";
import { apiConfig } from "../config/api.config";

export class ApiClient {
  private agent: request.SuperTest<request.Test>;
  private token?: string;

  constructor() {
    this.agent = request(apiConfig.baseUrl);
  }

  async authenticate(email: string, password: string): Promise<void> {
    const res = await this.agent
      .post("/auth/login")
      .send({ email, password });
    this.token = res.body.token;
  }

  get(path: string) {
    const req = this.agent.get(path);
    if (this.token) req.set("Authorization", `Bearer ${this.token}`);
    return req;
  }

  post(path: string, body: object) {
    const req = this.agent.post(path).send(body);
    if (this.token) req.set("Authorization", `Bearer ${this.token}`);
    return req;
  }

  put(path: string, body: object) {
    const req = this.agent.put(path).send(body);
    if (this.token) req.set("Authorization", `Bearer ${this.token}`);
    return req;
  }

  delete(path: string) {
    const req = this.agent.delete(path);
    if (this.token) req.set("Authorization", `Bearer ${this.token}`);
    return req;
  }
}
```

### Schema (`{resource}.schema.ts`)
```typescript
export const userSchema = {
  type: "object",
  required: ["id", "email", "name"],
  properties: {
    id: { type: "number" },
    email: { type: "string", format: "email" },
    name: { type: "string" },
    role: { type: "string", enum: ["admin", "user"] },
  },
};
```

### package.json (api section)
```json
{
  "devDependencies": {
    "supertest": "^6.3.0",
    "@types/supertest": "^2.0.0",
    "jest": "^29.7.0",
    "ts-jest": "^29.1.0",
    "@types/jest": "^29.5.0",
    "typescript": "^5.3.0"
  }
}
```

---

## 📋 Pré-requisitos
- Node.js 20+
- `npm install`

## 🔧 Comandos de Execução
```bash
npx jest {{TESTS_DIR}}/                          # Todos
npx jest {{TESTS_DIR}}/{endpoint}.spec.ts        # Específico
npx jest --coverage                      # Com cobertura
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução para este framework:**
```bash
npx jest tests/{funcionalidade-kebab}.spec.ts --verbose
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída completa + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **Compile TypeScript** → corrigir tipos / imports
   - **Connection refused** → verificar `baseUrl` no `api.config.ts`
   - **Status code mismatch** → ajustar `expect(response.status).toBe()` ou header de auth
   - **Timeout** → aumentar `jest.setTimeout()` no bloco `beforeAll`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
