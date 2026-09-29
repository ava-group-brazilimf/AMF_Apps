---
name: "fastqa_4.1_create_automated_test_requests"
description: "Criador de Testes Automatizados — Requests + Python (API)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Requests + Python (API)

## 🎯 Objetivo
Gerar scripts automatizados em **Requests + pytest** para testes de API REST.

---

## 🧭 Resolução Dinâmica de Paths (Obrigatório)

Antes de gerar qualquer arquivo, ler `fastqa/scripts/project_config.json` e usar:

- `folder_structure.custom_paths.automation_root` -> `{{AUTOMATION_ROOT}}`
- `folder_structure.custom_paths.tests` -> `{{TESTS_DIR}}`
- `folder_structure.custom_paths.pages` -> `{{PAGES_DIR}}`
- `folder_structure.custom_paths.config` -> `{{CONFIG_DIR}}`
- `folder_structure.custom_paths.results` (opcional) -> `{{RESULTS_DIR}}`

Fallback legado (se vazio):

- `{{AUTOMATION_ROOT}} = automated_test/{platform}`
- `{{TESTS_DIR}} = automated_test/{platform}/tests`
- `{{PAGES_DIR}} = automated_test/{platform}/pages` (ou `screens` para mobile)
- `{{CONFIG_DIR}} = automated_test/{platform}/config`
- `{{RESULTS_DIR}} = automated_test/{platform}/results`

Regra de precedência: esta seção prevalece sobre exemplos legados hardcoded eventualmente existentes no restante do documento.

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura Inteligente:** O nome dos arquivos é gerado a partir da **funcionalidade/endpoint informado pelo usuário** no passo 2 do workflow `automate_test`.
> - Arquivo: `test_{funcionalidade_snake}.py`, `{funcionalidade_snake}_data.json`
> - Exemplo: funcionalidade `"usuarios"` → `test_usuarios.py`, `usuarios_data.json`

```
{{AUTOMATION_ROOT}}/
├── config/
│   └── conftest.py
├── data/
│   └── {funcionalidade_snake}_data.json
├── support/
│   ├── api_client.py
│   └── schemas/
│       └── {funcionalidade_snake}_schema.py
├── tests/
│   └── test_{funcionalidade_snake}.py
├── results/
└── requirements.txt
```

---

## 📝 Templates

### Spec File (`test_{endpoint}.py`)
```python
import pytest
import json
from support.api_client import ApiClient

with open("data/login_data.json") as f:
    test_data = json.load(f)


class TestUsers:
    """{{FEATURE_NAME}}"""

    @pytest.fixture(autouse=True)
    def setup(self, api_client: ApiClient):
        self.api = api_client
        self.api.authenticate(
            test_data["adminUser"]["email"],
            test_data["adminUser"]["password"],
        )

    def test_listar_usuarios_com_sucesso(self):
        response = self.api.get("/api/users")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

    def test_retornar_401_sem_token(self):
        self.api.token = None
        response = self.api.get("/api/users")
        assert response.status_code == 401

    def test_criar_usuario_com_dados_validos(self):
        new_user = test_data["newUser"]
        response = self.api.post("/api/users", json=new_user)
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == new_user["email"]
        assert body["name"] == new_user["name"]
```

### API Client (`api_client.py`)
```python
import requests
from typing import Optional


class ApiClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.token: Optional[str] = None
        self.session = requests.Session()

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def authenticate(self, email: str, password: str):
        res = self.post("/auth/login", json={"email": email, "password": password})
        self.token = res.json().get("token")

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=self.timeout,
            **kwargs,
        )

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.session.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=self.timeout,
            **kwargs,
        )

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.session.put(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=self.timeout,
            **kwargs,
        )

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.session.delete(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=self.timeout,
            **kwargs,
        )
```

### Conftest (`conftest.py`)
```python
import pytest
from support.api_client import ApiClient


@pytest.fixture(scope="session")
def api_client():
    import os
    base_url = os.getenv("API_BASE_URL", "{{BASE_URL}}")
    return ApiClient(base_url)
```

### Requirements (`requirements.txt`)
```
requests>=2.31.0
pytest>=7.4.0
pytest-html>=4.1.0
jsonschema>=4.20.0
python-dotenv>=1.0.0
```

---

## 📋 Pré-requisitos
- Python 3.10+
- `pip install -r requirements.txt`

## 🔧 Comandos de Execução
```bash
pytest tests/                             # Todos
pytest tests/test_{endpoint}.py           # Específico
pytest --html=results/report.html         # Com relatório
```

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução para este framework:**
```bash
pytest tests/test_{funcionalidade_snake}.py -v
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída completa + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **ImportError** → corrigir imports Python
   - **ConnectionError** → verificar `BASE_URL` no `conftest.py`
   - **AssertionError** → ajustar `assert response.status_code ==` ou payload
   - **JSONDecodeError** → verificar resposta da API antes de serializar
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
