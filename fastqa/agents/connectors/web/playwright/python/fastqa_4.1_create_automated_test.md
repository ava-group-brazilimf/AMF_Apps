---
name: "fastqa_4.1_create_automated_test_playwright_python_web"
description: "Criador de Testes Automatizados — Playwright + Python (Web)"

tools:
  - playwright mcp
  - memory
  - sequential-thinking
---

# Connector: Playwright + Python

## 🎯 Objetivo
Gerar scripts automatizados em **Playwright + Python** a partir de cenários Gherkin ou evidências manuais, seguindo os design patterns estabelecidos neste connector.

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
- `{{PAGES_DIR}} = automated_test/{platform}/pages`
- `{{CONFIG_DIR}} = automated_test/{platform}/config`
- `{{RESULTS_DIR}} = automated_test/{platform}/results`

Regra de precedência: esta seção prevalece sobre exemplos legados hardcoded eventualmente existentes no restante do documento.

---

## 🏛️ Design Patterns de Arquitetura

Este connector adota **quatro padrões complementares** que devem ser respeitados em toda geração de código.

---

### Pattern 1 — Page Object Model com BasePage (POM Hierárquico)

**Conceito:** Cada tela/página da aplicação é representada por uma classe Python dedicada. Todas herdam de `BasePage`, que centraliza utilitários comuns (navegação, asserções de URL). Nenhum locator ou interação direta com o browser deve aparecer nos arquivos de teste.

**Hierarquia obrigatória:**
```
BasePage                    ← utilitários comuns (open, current_url_should_be)
  └── LoginPage             ← seletores + ações + asserções da tela de login
  └── InventoryPage         ← seletores + ações + asserções do inventário
  └── CartPage              ← seletores + ações + asserções do carrinho
  └── CheckoutPage          ← seletores + ações + asserções do checkout
```

**Regras obrigatórias do Page Object:**
- Seletores declarados como **constantes de classe** (`CLASS_ATTRIBUTE = '[data-test="..."]'`), não inline
- Prioridade de seletores: `data-test` > `aria-label` > `role` > `css` > `xpath`
- Três categorias de métodos por Page Object:
  1. **Ações atômicas** — um passo por método (`fill_username`, `click_login`)
  2. **Ações de negócio** — composição de atômicos (`login(username, password)`)
  3. **Asserções** — sempre prefixadas com `should_` (`should_login_successfully`, `should_show_error`)
- `__init__` recebe `page: Page`, chama `super().__init__(page)` e inicializa URLs via `os.getenv`
- Type hints obrigatórios em todos os métodos (`-> None`, `-> bool`, `-> str`)

**Template: `base_page.py`**
```python
from playwright.sync_api import Page, expect


class BasePage:
    """Classe base para concentrar utilidades comuns e evitar repetição espalhada."""

    def __init__(self, page: Page):
        self.page = page

    def open(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")

    def current_url_should_be(self, expected_url: str) -> None:
        expect(self.page).to_have_url(expected_url)
```

**Template: `{funcionalidade_snake}_page.py`**
```python
import os
from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class LoginPage(BasePage):
    # Seletores declarados como constantes. Código claro vence código "esperto".
    USERNAME_INPUT = '[data-test="username"]'
    PASSWORD_INPUT = '[data-test="password"]'
    LOGIN_BUTTON   = '[data-test="login-button"]'
    ERROR_MESSAGE  = '[data-test="error"]'

    def __init__(self, page: Page):
        super().__init__(page)
        self.base_url = os.getenv("BASE_URL", "https://www.exemplo.com/")

    # --- Ações atômicas ---

    def navigate(self) -> None:
        self.open(self.base_url)

    def fill_username(self, username: str) -> None:
        self.page.locator(self.USERNAME_INPUT).fill(username)

    def fill_password(self, password: str) -> None:
        self.page.locator(self.PASSWORD_INPUT).fill(password)

    def click_login(self) -> None:
        self.page.locator(self.LOGIN_BUTTON).click()

    # --- Ação de negócio ---

    def login(self, username: str, password: str) -> None:
        # Método de negócio: quem lê entende a intenção sem precisar decifrar o fluxo.
        self.fill_username(username)
        self.fill_password(password)
        self.click_login()

    # --- Asserções ---

    def should_login_successfully(self) -> None:
        expect(self.page).to_have_url(f"{self.base_url.rstrip('/')}/dashboard")

    def should_show_error(self, expected_message: str) -> None:
        expect(self.page.locator(self.ERROR_MESSAGE)).to_be_visible()
        expect(self.page.locator(self.ERROR_MESSAGE)).to_contain_text(expected_message)
```

---

### Pattern 2 — Fixture-based Test Setup via conftest.py

**Conceito:** Toda a configuração de browser, contexto, gravação de vídeo e captura de evidências é gerenciada por fixtures do pytest declaradas no `conftest.py`. Os arquivos de teste não instanciam browser diretamente — apenas recebem a fixture `app_page`.

**Fixtures obrigatórias no `conftest.py`:**

| Fixture | Scope | Responsabilidade |
|---------|-------|-----------------|
| `prepare_artifacts` | `session` | Limpa e cria as pastas `artifacts/screenshots`, `artifacts/videos`, `artifacts/logs/tests`, `allure-results` antes da suíte |
| `browser_type_launch_args` | `session` | Configura `slow_mo` para debug/demo |
| `browser_context_args` | `session` | Define viewport, ignora erros HTTPS, ativa gravação de vídeo |
| `app_page` | `function` | Cria contexto + página por teste; lê `HEADLESS` do `.env`; fecha contexto ao final para persistir vídeo |
| `evidence_collector` | `function`, `autouse=True` | Captura screenshot + URL final + status de cada teste automaticamente |
| `pytest_runtest_makereport` | hook | Expõe `rep_call.failed` para uso no `evidence_collector` |

**Template: `conftest.py`**
```python
import os
import shutil
from pathlib import Path

import allure
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Browser, Page

from utils.logger import get_logger
from utils.test_evidence import TestEvidence

load_dotenv()
logger = get_logger("conftest")


@pytest.fixture(scope="session", autouse=True)
def prepare_artifacts():
    """Garante área limpa de evidências antes da execução."""
    folders = [
        "artifacts/screenshots",
        "artifacts/videos",
        "artifacts/logs/tests",
        "allure-results",
    ]
    for folder in folders:
        path = Path(folder)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
    logger.info("Pastas de artefatos preparadas.")
    yield


@pytest.fixture(scope="session")
def browser_type_launch_args():
    return {"slow_mo": 1000}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "ignore_https_errors": True,
        "viewport": {"width": 1440, "height": 900},
        "record_video_dir": "artifacts/videos",
        "record_video_size": {"width": 1280, "height": 720},
    }


@pytest.fixture
def app_page(browser: Browser) -> Page:
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    logger.info("Iniciando contexto | headless=%s", headless)

    context = browser.new_context(
        ignore_https_errors=True,
        viewport={"width": 1440, "height": 900},
        record_video_dir="artifacts/videos",
        record_video_size={"width": 1280, "height": 720},
    )
    page = context.new_page()
    yield page
    page.close()
    context.close()  # fechar contexto persiste o vídeo


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(autouse=True)
def evidence_collector(request, app_page: Page):
    yield

    safe_name = (
        request.node.name.replace("/", "_").replace("\\", "_")
        .replace(" ", "_").replace("::", "_")
    )

    screenshot_dir = Path("artifacts/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / f"{safe_name}.png"

    app_page.screenshot(path=str(screenshot_path), full_page=True)

    with open(screenshot_path, "rb") as f:
        allure.attach(f.read(), name=f"{safe_name}_screenshot",
                      attachment_type=allure.attachment_type.PNG)

    evidence = TestEvidence(request.node.name)
    status = "FALHOU" if (
        getattr(request.node, "rep_call", None) and request.node.rep_call.failed
    ) else "PASSOU"
    evidence.end(status=status, final_url=app_page.url)
```

---

### Pattern 3 — Utilitários de Suporte (utils/)

**Conceito:** Dois utilitários de infraestrutura reutilizáveis concentram responsabilidades transversais — log e evidência textual. Nunca duplicar lógica de log ou de escrita de artefatos nos testes.

**`utils/logger.py` — Logger centralizado**
```python
import logging
from pathlib import Path


def get_logger(name: str = "fastqa") -> logging.Logger:
    """Cria um logger simples, previsível e fácil de rastrear no dia ruim."""
    log_dir = Path("artifacts/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = logging.FileHandler(log_dir / "execution.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
```

**`utils/test_evidence.py` — Evidência textual por teste**
```python
from pathlib import Path
from datetime import datetime


class TestEvidence:
    """Responsável por gerar evidência textual individual por teste."""

    def __init__(self, test_name: str):
        safe_name = (
            test_name.replace("/", "_").replace("\\", "_")
            .replace(" ", "_").replace("::", "_")
        )
        self.test_name = safe_name
        self.log_dir = Path("artifacts/logs/tests")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.log_dir / f"{self.test_name}.txt"

    def write(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} | {message}\n")

    def start(self) -> None:
        self.write(f"INICIO DO TESTE: {self.test_name}")

    def end(self, status: str, final_url: str = "") -> None:
        self.write(f"FIM DO TESTE: {self.test_name}")
        self.write(f"STATUS FINAL: {status}")
        if final_url:
            self.write(f"URL FINAL: {final_url}")
        self.write("-" * 80)
```

---

### Pattern 4 — Arquivo de Teste com Allure + Logger

**Conceito:** Cada arquivo de teste é responsável por **orquestrar** — nunca por interagir com o browser. Passos são agrupados com `allure.step`. Variáveis de ambiente são carregadas via `dotenv` no topo do módulo. Cada teste tem uma única responsabilidade.

**Regras obrigatórias do arquivo de teste:**
- Decorator `@allure.feature` na função para rastreabilidade por feature
- Decorator `@allure.story` na função para rastreabilidade por história
- Passos envolvidos em `with allure.step("...")` com verbo no infinitivo
- `logger.info(...)` no início e no fim de cada teste
- Apenas instanciar Page Objects e chamar métodos de negócio — **zero** `page.locator()`, `page.click()` ou `expect()` diretamente no teste
- Variáveis de ambiente lidas no escopo do módulo (não dentro das funções)
- `pytest.mark.parametrize` para cenários multi-usuário/multi-dado

**Template: `test_{funcionalidade_snake}.py`**
```python
import os

import allure
import pytest
from dotenv import load_dotenv

from pages.login_page import LoginPage
from utils.logger import get_logger

load_dotenv()
logger = get_logger("test_{funcionalidade_snake}")

PASSWORD = os.getenv("VALID_PASSWORD", "secret_sauce")
VALID_USERS = [
    os.getenv("STANDARD_USER", "standard_user"),
    os.getenv("PROBLEM_USER", "problem_user"),
]


@allure.feature("{Feature Name}")
@allure.story("{Story Name}")
@pytest.mark.parametrize("username", VALID_USERS)
def test_should_{cenario_snake}(app_page, username):
    """{Descrição do que o teste valida}"""
    login_page = LoginPage(app_page)

    logger.info("Iniciando teste: %s | usuário: %s", "{cenario_snake}", username)

    with allure.step("Acessar página de login"):
        login_page.navigate()

    with allure.step("Realizar login com usuário válido"):
        login_page.login(username, PASSWORD)
        login_page.should_login_successfully()

    assert "dashboard" in app_page.url
    logger.info("Teste concluído com sucesso: %s", "{cenario_snake}")
```

---

## 📂 Estrutura de Saída

> **📛 Nomenclatura:** arquivos em `snake_case`. Exemplo: funcionalidade `"login usuario"` → `test_login_usuario.py`, `login_usuario_page.py`

```
{{AUTOMATION_ROOT}}/
├── pages/
│   ├── base_page.py                        ← BasePage (Pattern 1)
│   └── {funcionalidade_snake}_page.py      ← Page Object por tela
├── tests/
│   └── test_{funcionalidade_snake}.py      ← Orquestração (Pattern 4)
├── utils/
│   ├── logger.py                           ← Logger centralizado (Pattern 3)
│   └── test_evidence.py                    ← Evidência textual (Pattern 3)
├── artifacts/                              ← Gerado em runtime
│   ├── screenshots/
│   ├── videos/
│   └── logs/
│       ├── execution.log
│       └── tests/
├── allure-results/                         ← Gerado em runtime
├── conftest.py                             ← Fixtures globais (Pattern 2)
├── pytest.ini                              ← Configuração do runner
├── requirements.txt
└── .env.example
```

---

## ⚙️ Arquivos de Configuração

**`pytest.ini`**
```ini
[pytest]
addopts = -v --tb=short --alluredir=allure-results
testpaths = tests
python_files = test_*.py
python_functions = test_*
log_cli = false
```

**`requirements.txt`**
```
playwright==1.58.0
pytest==9.0.2
pytest-playwright==0.7.2
allure-pytest==2.15.3
python-dotenv==1.1.1
```

**`.env.example`**
```
BASE_URL=https://www.exemplo.com/
VALID_PASSWORD=senha_valida
STANDARD_USER=usuario_padrao
HEADLESS=false
```

---

## 📋 Pré-requisitos e Execução

```bash
# 1. Ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# 2. Dependências
pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install --with-deps chromium

# 3. Variáveis de ambiente
copy .env.example .env          # Windows
cp .env.example .env            # Linux/Mac

# 4. Executar
pytest                                              # Todos os testes
pytest tests/test_{funcionalidade}.py               # Arquivo específico
pytest --maxfail=1 --junitxml=test-results.xml      # Pipeline CI/CD
allure generate allure-results --clean && allure open  # Relatório Allure
```

---

## ⚠️ Regras Obrigatórias (Resumo)

| Regra | Local | ❌ Proibido |
|-------|-------|------------|
| Seletores como constantes de classe | Page Object | Locators inline nos métodos |
| Métodos com tipo de retorno | Page Object | Métodos sem type hints |
| `should_` para asserções | Page Object | `assert` dentro do Page Object |
| `app_page` via fixture | Teste | Instanciar `sync_playwright()` no teste |
| `allure.step` para cada passo | Teste | Comentários `# Given/When/Then` sem step |
| `logger.info` no início e fim | Teste | `print()` para debug |
| Zero lógica de browser no teste | Teste | `page.locator()`, `page.click()` no teste |
| `load_dotenv()` no topo do módulo | Teste | `os.getenv` sem carregar `.env` |

---

## 🔄 Fase Final: Auto-Healing Loop (Obrigatório)

> **⚠️ APÓS gerar todos os arquivos, executar obrigatoriamente este ciclo antes de encerrar.**

**Comando de execução:**
```bash
pytest tests/test_{funcionalidade_snake}.py -v --tb=short
```

**Ciclo (máx. 5 tentativas):**
1. Executar o teste → capturar saída completa + exit code
2. Exit code = 0 → ✅ encerrar
3. Exit code ≠ 0 → classificar erro:
   - **ImportError / ModuleNotFoundError** → corrigir import — verificar nome da pasta (`pages/` não `page/`) e nome do arquivo
   - **Locator not found / TimeoutError** → revisar seletor no Page Object — priorizar `data-test` > `aria-label` > `role`
   - **AssertionError** → revisar método `should_` no Page Object ou asserção `assert` no teste
   - **AttributeError** → verificar herança de `BasePage` e chamada a `super().__init__(page)`
   - **FileNotFoundError em artifacts/** → verificar se `prepare_artifacts` fixture está no `conftest.py`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
