*** Variables ***
# ===========================================================================
# Configuração Global — SauceDemo
# Gerado por FastQA | PBI-001 | Fluxo E2E de Compra
# ===========================================================================

# URL Base
${BASE_URL}                   https://www.saucedemo.com

# Configuração do Browser
${BROWSER}                    chromium
${HEADLESS}                   false
${TIMEOUT}                    15s
${NAVIGATION_TIMEOUT}         15s
${NAVIGATION_WAIT_UNTIL}      domcontentloaded

# Credenciais (preferencialmente via variável de ambiente)
${LOGIN_USER}                 %{SAUCEDEMO_USER=standard_user}
${LOGIN_PASS}                 %{SAUCEDEMO_PASS=secret_sauce}

# Rotas do Sistema
${ROUTE_LOGIN}                /
${ROUTE_INVENTORY}            /inventory.html
${ROUTE_CART}                 /cart.html
${ROUTE_CHECKOUT_STEP1}       /checkout-step-one.html
${ROUTE_CHECKOUT_STEP2}       /checkout-step-two.html
${ROUTE_CHECKOUT_DONE}        /checkout-complete.html

# ===========================================================================
# Massa de dados — Checkout
# ===========================================================================
${CHECKOUT_FIRST_NAME}        %{CHECKOUT_FIRST_NAME=Test}
${CHECKOUT_LAST_NAME}         %{CHECKOUT_LAST_NAME=User}
${CHECKOUT_ZIP}               %{CHECKOUT_ZIP=12345}

# ===========================================================================
# Massa de dados — Produtos (SauceDemo Inventory)
# ===========================================================================
${PRODUCT_BACKPACK}           Sauce Labs Backpack
${PRODUCT_BIKE_LIGHT}         Sauce Labs Bike Light
${PRODUCT_BOLT_SHIRT}         Sauce Labs Bolt T-Shirt
${PRODUCT_FLEECE_JACKET}      Sauce Labs Fleece Jacket
${PRODUCT_ONESIE}             Sauce Labs Onesie
${PRODUCT_RED_SHIRT}          Test.allTheThings() T-Shirt (Red)

# ===========================================================================
# Preços esperados dos produtos (validados via inspeção DOM — 14/05/2026)
# ===========================================================================
${PRICE_BACKPACK}             $29.99
${PRICE_BIKE_LIGHT}           $9.99
${PRICE_BOLT_SHIRT}           $15.99
${PRICE_FLEECE_JACKET}        $49.99
${PRICE_ONESIE}               $7.99
${PRICE_RED_SHIRT}            $15.99

# Quantidade total de produtos no inventário
${TOTAL_PRODUCTS}             6
