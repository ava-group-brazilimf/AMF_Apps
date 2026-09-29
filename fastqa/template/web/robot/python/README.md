# FastQA Automation — SauceDemo E2E (Robot Framework + Python)

Projeto de automação de testes web **E2E** gerado pelo **FastQA** para o [SauceDemo](https://www.saucedemo.com/), cobrindo o fluxo completo de compra: login → inventário → carrinho → checkout → confirmação → logout.

> **PBI-001** — Validação E2E do Fluxo de Compra após Login no SauceDemo

---

## Stack

| Camada | Tecnologia |
|---|---|
| Framework de testes | Robot Framework ≥ 7.0 |
| Driver de browser | robotframework-browser ≥ 18.0 (Playwright) |
| Execução paralela | robotframework-pabot ≥ 2.16 |
| Utilitários Python | requests, faker, python-dotenv |
| Plataforma alvo | Web — https://www.saucedemo.com |

---

## Estrutura do Projeto

```
python/
├── config/
│   ├── variables.robot        # Variáveis globais: URL base, rotas, credenciais, produtos e preços
│   └── auth_config.robot      # Configuração de autenticação (seletores, mensagens de erro)
│
├── custom_libraries/
│   └── __init__.py            # Pacote Python (extensível para helpers futuros)
│
├── data/
│   └── saucedemo.json         # Massa de dados: produtos, preços, credenciais, checkout
│
├── pages/                     # Page Objects — Keywords Robot por tela
│   ├── LoginPage.robot        # Tela de login: seletores, preencher, verificar erros
│   ├── HeaderPage.robot       # Cabeçalho compartilhado: logo, badge do carrinho, menu lateral
│   ├── InventoryPage.robot    # Inventário: listar, add/remove, badge, ordenação, detalhe
│   ├── CartPage.robot         # Carrinho: verificar itens, preços, remove, continuar, checkout
│   ├── CheckoutInformationPage.robot  # Checkout Step 1: formulário de dados pessoais
│   ├── CheckoutOverviewPage.robot     # Checkout Step 2: resumo do pedido, subtotal, finish
│   ├── CheckoutCompletePage.robot     # Confirmação: "Thank you for your order!", Back Home
│   └── ProductDetailPage.robot        # Detalhe do produto: nome, preço, add to cart, voltar
│
├── results/                   # Relatórios gerados em execução (ignorado pelo git)
│
├── support/
│   └── auth.resource          # Keywords de autenticação: login, logout, reset de estado
│
├── tests/                     # Suítes de teste por feature
│   ├── login.robot            # CT-01 a CT-07: login válido, bloqueado, inválido, campos, UI
│   ├── inventory.robot        # CT-01 a CT-10: catálogo, add/remove, badge, ordenação, detalhe
│   ├── cart.robot             # CT-01 a CT-08: carrinho vazio, itens, preços, remoção, checkout
│   ├── checkout_information.robot  # CT-01 a CT-07: formulário step 1, validação de campos obrigatórios
│   ├── checkout_overview.robot     # CT-01 a CT-08: resumo, preços, finish, cancel
│   └── e2e_compra.robot       # CT-01 a CT-06: fluxo E2E completo (PBI-001 checklist)
│
├── .env.example               # Modelo de variáveis de ambiente
├── .gitignore
├── PBI-001.txt                # Especificação do PBI de referência
└── requirements.txt
```

---

## Cobertura de Testes (PBI-001 Checklist)

| Item do Checklist | Suíte | CT |
|---|---|---|
| Login com sucesso → inventário | `login.robot` | CT-01 |
| Lista de produtos exibida | `inventory.robot` | CT-01, CT-02 |
| Produto adicionado — badge atualizado | `inventory.robot` | CT-03, CT-04 |
| Produto removido — badge atualizado | `inventory.robot` | CT-05 |
| Navegação para o carrinho | `cart.robot` | CT-01 |
| Checkout → etapa de informações | `cart.robot` | CT-08 |
| Campos obrigatórios validados | `checkout_information.robot` | CT-03, CT-04, CT-05 |
| Continue → visão geral do pedido | `checkout_information.robot` | CT-06 |
| Itens e preços no resumo | `checkout_overview.robot` | CT-02, CT-04, CT-05 |
| Finish → compra concluída | `checkout_overview.robot` | CT-07 |
| Mensagem de confirmação | `e2e_compra.robot` | CT-01 |
| Back Home → inventário | `e2e_compra.robot` | CT-04 |
| Logout → impede acesso direto | `e2e_compra.robot` | CT-05 |

**Total: 37 cenários de teste** distribuídos em 6 suítes.

---

## Pré-requisitos

- Python 3.11+
- Node.js 18+ (necessário para a biblioteca Browser/Playwright)
- pip

---

## Instalação

```bash
# 1. Crie e ative o ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. Instale as dependências Python
pip install -r requirements.txt

# 3. Inicialize os navegadores do Playwright (obrigatório na primeira vez)
rfbrowser init
```

---

## Configuração de Ambiente

Copie o arquivo de exemplo. As credenciais padrão do SauceDemo já estão preenchidas.

```bash
cp .env.example .env
```

| Variável | Padrão | Descrição |
|---|---|---|
| `SAUCEDEMO_USER` | `standard_user` | Usuário de login |
| `SAUCEDEMO_PASS` | `secret_sauce` | Senha |
| `CHECKOUT_FIRST_NAME` | `Test` | Primeiro nome no checkout |
| `CHECKOUT_LAST_NAME` | `User` | Último nome no checkout |
| `CHECKOUT_ZIP` | `12345` | CEP no checkout |

### Usuários disponíveis no SauceDemo

| Usuário | Comportamento |
|---|---|
| `standard_user` | Fluxo padrão — todos os testes funcionam |
| `locked_out_user` | Bloqueado — testa mensagem de erro de login |
| `error_user` | Gera erros em ações específicas |
| `performance_glitch_user` | Latência artificial — testes de performance |

---

## Autenticação

O SauceDemo **não possui MFA**. O `support/auth.resource` abre o browser, preenche credenciais automaticamente e aguarda o inventário carregar.

```robot
Suite Setup    Autenticar Na Aplicacao
Test Setup     Resetar Estado Da Aplicacao
Suite Teardown Close Browser    ALL
```

A keyword `Resetar Estado Da Aplicacao` usa o menu "Reset App State" do SauceDemo para garantir estado limpo antes de cada teste (carrinho e preferências zerados).

---

## Executando os Testes

### Suíte completa
```bash
robot --outputdir results tests/
```

### Por tag
```bash
# Apenas cenários smoke (rápidos)
robot --outputdir results --include smoke tests/

# Todos os fluxos E2E
robot --outputdir results --include e2e tests/

# Regressão completa
robot --outputdir results --include regression tests/
```

### Suíte específica
```bash
robot --outputdir results tests/e2e_compra.robot
robot --outputdir results tests/login.robot
robot --outputdir results tests/inventory.robot
robot --outputdir results tests/cart.robot
robot --outputdir results tests/checkout_information.robot
robot --outputdir results tests/checkout_overview.robot
```

### Execução paralela (pabot)
```bash
pabot --outputdir results --processes 4 tests/
```

---

## Tags Disponíveis

| Tag | Descrição |
|---|---|
| `smoke` | Cenários críticos de verificação rápida |
| `critical` | Cenários de alto impacto no fluxo |
| `regression` | Cobertura completa de regressão |
| `e2e` / `jornada` | Fluxo de ponta a ponta |
| `ui` | Validações visuais e estruturais |
| `positive` / `negative` | Fluxo esperado / fluxo de erro |
| `validation` | Validações de campos obrigatórios |
| `security` | Controle de acesso pós-logout |
| `login` | Cenários da tela de login |
| `inventory` | Cenários do catálogo de produtos |
| `cart` | Cenários do carrinho |
| `checkout` / `checkout-step1` / `checkout-step2` | Cenários de checkout |
| `feature-e2e-compra` | Suíte E2E completa |

---

## Relatórios

Após a execução, os relatórios são gerados em `results/`:

```
results/
├── log.html      # Log detalhado de cada keyword executada
├── report.html   # Sumário executivo com pass/fail por suíte
└── output.xml    # Saída bruta para integração CI/CD
```

> Arquivos de relatório estão no `.gitignore` e não são versionados.

---

## Arquivos Ignorados pelo Git

```
.env              # Variáveis de ambiente com credenciais
results/          # Relatórios de execução
log.html / report.html / output.xml
*.png             # Screenshots capturadas em falhas
playwright-log.txt
browser/          # Binários dos navegadores Playwright
__pycache__/ *.pyc
.venv/
```

---

## Gerado por

**FastQA** — Plataforma de automação inteligente de testes.  
PBI-001 | Framework: Robot Framework + Python | Plataforma: Web | SauceDemo

