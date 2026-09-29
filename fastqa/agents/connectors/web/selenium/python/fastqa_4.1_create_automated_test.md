---
name: "fastqa_4.1_create_automated_test_selenium_python_web"
description: "Criador de Testes Automatizados — Selenium + Python (Web)"

tools:
  - memory
  - sequential-thinking
---

# Connector: Selenium + Python

## 🎯 Objetivo
Gerar scripts automatizados em **Selenium + Python** a partir de cenários Gherkin.

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

> **📛 Nomenclatura Inteligente:** O nome dos arquivos é gerado a partir da **funcionalidade informada pelo usuário** no passo 2 do workflow `automate_test`.
> - Arquivo: `test_{funcionalidade_snake}.py`, `{funcionalidade_snake}_data.json`
> - Page Object: `{funcionalidade_snake}_page.py`
> - Exemplo: funcionalidade `"login usuario"` → `test_login_usuario.py`, `login_usuario_page.py`

```
{{AUTOMATION_ROOT}}/
├── config/
│   ├── conftest.py
│   └── settings.py
├── data/
│   └── {funcionalidade_snake}_data.json
├── page/
│   ├── base_page.py
│   └── {funcionalidade_snake}_page.py
├── support/
│   └── helpers.py
├── tests/
│   └── test_{funcionalidade_snake}.py
├── results/
└── requirements.txt
```

---

## 📝 Templates

### Spec File (`test_{feature}.py`)
```python
import pytest
import json
from page.login_page import LoginPage

with open("data/login_data.json") as f:
    test_data = json.load(f)


class TestLogin:
    """{{FEATURE_NAME}}"""

    def test_login_com_credenciais_validas(self, browser):
        """{{SCENARIO_NAME}}"""
        login_page = LoginPage(browser)

        # Given
        login_page.navigate()

        # When
        login_page.fill_email(test_data["validUser"]["email"])
        login_page.fill_password(test_data["validUser"]["password"])
        login_page.click_login()

        # Then
        assert "/dashboard" in browser.current_url
        assert login_page.get_welcome_message() == "Bem-vindo"
```

### Page Object (`{page_name}_page.py`)
```python
from selenium.webdriver.common.by import By
from page.base_page import BasePage


class LoginPage(BasePage):
    EMAIL_INPUT = (By.ID, "email")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
    WELCOME_MSG = (By.CLASS_NAME, "welcome-text")

    def __init__(self, driver):
        super().__init__(driver)
        self.url = f"{{BASE_URL}}/login"

    def navigate(self):
        self.driver.get(self.url)

    def fill_email(self, email: str):
        self.wait_and_type(self.EMAIL_INPUT, email)

    def fill_password(self, password: str):
        self.wait_and_type(self.PASSWORD_INPUT, password)

    def click_login(self):
        self.wait_and_click(self.LOGIN_BUTTON)

    def get_welcome_message(self) -> str:
        return self.wait_for_element(self.WELCOME_MSG).text
```

### Base Page (`base_page.py`)
```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BasePage:
    def __init__(self, driver, timeout=10):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def wait_for_element(self, locator):
        return self.wait.until(EC.visibility_of_element_located(locator))

    def wait_and_click(self, locator):
        self.wait.until(EC.element_to_be_clickable(locator)).click()

    def wait_and_type(self, locator, text: str):
        element = self.wait_for_element(locator)
        element.clear()
        element.send_keys(text)
```

### Conftest (`conftest.py`)
```python
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


@pytest.fixture(scope="function")
def browser():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1366,768")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()
```

### Requirements (`requirements.txt`)
```
selenium>=4.15.0
pytest>=7.4.0
pytest-html>=4.1.0
webdriver-manager>=4.0.0
```

---

## 📋 Pré-requisitos
- Python 3.10+
- `pip install -r requirements.txt`
- ChromeDriver compatível

## 🔧 Comandos de Execução
```bash
pytest tests/                               # Todos os testes
pytest tests/test_{feature}.py              # Específico
pytest --html=results/report.html           # Com relatório
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
   - **ImportError** → corrigir imports Python / caminho do Page Object
   - **NoSuchElementException** → revisar `By` locator no Page Object
   - **AssertionError** → ajustar `assert` ou pré-condição
   - **TimeoutException** → aumentar `WebDriverWait` / adicionar `explicit wait`
4. Corrigir → voltar ao passo 1
5. Após 5 falhas → reportar diagnóstico: tentativas realizadas, erro remanescente, arquivo e linha, sugestão manual
