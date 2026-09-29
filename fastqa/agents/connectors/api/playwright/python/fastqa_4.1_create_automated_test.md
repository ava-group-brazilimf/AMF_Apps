---
name: "fastqa_4.1_create_automated_test_playwright_python_api"
description: "Criador de Testes Automatizados — Playwright + Python (API)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Playwright + Python (API)

## 🎯 Objetivo
Gerar testes automatizados de API REST em **Playwright + Python** usando `APIRequestContext`.

---

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `platforms[selected].details.custom_paths.automation_root` → `{{AUTOMATION_ROOT}}`
- `platforms[selected].details.custom_paths.tests` → `{{TESTS_DIR}}`
- `platforms[selected].details.custom_paths.config` → `{{CONFIG_DIR}}`
- `platforms[selected].details.custom_paths.results` → `{{RESULTS_DIR}}`

Fallback (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/api`
- `{{TESTS_DIR}} = automated_test/api/tests`
- `{{CONFIG_DIR}} = automated_test/api/config`
- `{{RESULTS_DIR}} = automated_test/api/results`

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** Gerado a partir da **funcionalidade informada pelo usuário**.
> - Teste: `test_{funcionalidade_snake}_api.py`
> - Client: `{funcionalidade_snake}_client.py`
> - Dados: `{funcionalidade_snake}_data.json`
> - Exemplo: `"autenticacao"` → `test_autenticacao_api.py`, `autenticacao_client.py`

```
{{AUTOMATION_ROOT}}/
├── config/
│   └── conftest.py
├── clients/
│   └── {funcionalidade_snake}_client.py
├── schemas/
│   └── {funcionalidade_snake}_schema.json
├── support/
│   └── api_helpers.py
├── data/
│   └── {funcionalidade_snake}_data.json
├── tests/
│   └── test_{funcionalidade_snake}_api.py
├── results/
└── requirements.txt
```

---

## 📝 Templates

### Spec File (`test_{funcionalidade_snake}_api.py`)
```python
import json
import pytest
from clients.autenticacao_client import AutenticacaoClient

with open("data/autenticacao_data.json") as f:
    test_data = json.load(f)


class TestAutenticacaoApi:
    """{{FEATURE_NAME}}"""

    def test_login_com_credenciais_validas(self, api_request_context):
        """{{SCENARIO_NAME}}"""
        client = AutenticacaoClient(api_request_context)

        response = client.login(
            email=test_data["validUser"]["email"],
            password=test_data["validUser"]["password"]
        )

        assert response.status == 200
        body = response.json()
        assert "token" in body
        assert body["token"]

    def test_login_com_credenciais_invalidas(self, api_request_context):
        """Garantir erro 401 para credenciais inválidas"""
        client = AutenticacaoClient(api_request_context)

        response = client.login(
            email=test_data["invalidUser"]["email"],
            password=test_data["invalidUser"]["password"]
        )

        assert response.status == 401
        body = response.json()
        assert "error" in body
```

### API Client (`{funcionalidade_snake}_client.py`)
```python
class AutenticacaoClient:
    def __init__(self, request_context):
        self.request = request_context

    def login(self, email: str, password: str):
        return self.request.post(
            "/auth/login",
            data={"email": email, "password": password}
        )

    def logout(self, token: str):
        return self.request.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

    def get_profile(self, token: str):
        return self.request.get(
            "/auth/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
```

### Conftest (`config/conftest.py`)
```python
import os
import pytest
from playwright.sync_api import Playwright


@pytest.fixture(scope="session")
def api_request_context(playwright: Playwright):
    base_url = os.getenv("BASE_URL", "{{BASE_URL}}")
    request_context = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    yield request_context
    request_context.dispose()
```

### API Helpers (`support/api_helpers.py`)
```python
def assert_status(response, expected: int):
    assert response.status == expected, (
        f"Esperado {expected}, recebido {response.status}. Body: {response.text()}"
    )


def assert_body_has_key(response, key: str):
    body = response.json()
    assert key in body, f"Chave '{key}' não encontrada. Body: {body}"
    return body[key]
```

### Data File (`{funcionalidade_snake}_data.json`)
```json
{
  "validUser": {
    "email": "usuario@teste.com",
    "password": "Senha@123"
  },
  "invalidUser": {
    "email": "errado@teste.com",
    "password": "senhaerrada"
  }
}
```

### Requirements (`requirements.txt`)
```
pytest>=7.4.0
playwright>=1.40.0
pytest-playwright>=0.4.0
python-dotenv>=1.0.0
```

---

## 📋 Pré-requisitos
- Python 3.10+
- `pip install -r requirements.txt`
- API disponível em `{{BASE_URL}}`

## 🔧 Instalação
```bash
pip install pytest playwright pytest-playwright python-dotenv
playwright install
```

## 🚀 Comandos de Execução
```bash
pytest tests/                                        # Todos os testes
pytest tests/test_{funcionalidade}_api.py -v         # Específico
pytest --html=results/report.html                    # Com relatório
BASE_URL=https://staging.api.com pytest tests/       # URL por variável
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução:**
```bash
pytest tests/test_{funcionalidade_snake}_api.py -v
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **ConnectionRefusedError** → API não está no ar ou `BASE_URL` incorreto
   - **AssertionError: status** → status diferente do esperado; revisar endpoint/payload
   - **KeyError** → campo ausente no response body
   - **ImportError** → verificar imports de `clients/` e `support/`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
