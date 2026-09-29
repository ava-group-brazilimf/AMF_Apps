"""
Script de inspeção: abre o Chromium, pausa para login manual,
injeta mock HTTP 500 em /grupos, abre um Side Sheet e
imprime o HTML interno do ZdsSideSheet para identificar
o seletor correto do estado de erro.
"""
from playwright.sync_api import sync_playwright
import time

BASE_URL = "https://hiae-cockpit-prm-portaladm-frontend.qas.telemedicinaeinstein.com.br"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--start-maximized"])
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()

    print("Abrindo página de login...")
    page.goto(f"{BASE_URL}/login/")

    input("\n>>> Faça o login manualmente (senha + OTP). Quando o portal carregar, pressione ENTER aqui: ")

    # Navegar para atividades
    page.goto(f"{BASE_URL}/prm-backoffice/atividades")
    page.wait_for_selector("table tbody tr", timeout=30000)
    print("Grid de atividades carregada.")

    # Injetar mock HTTP 500
    page.evaluate("""() => {
        window.__origFetch = window.fetch;
        window.fetch = function(u, o) {
            if (String(u).includes('/grupos')) {
                console.log('[MOCK] Intercepted /grupos → 500');
                return Promise.resolve(new Response(
                    JSON.stringify({error:'Internal Server Error'}),
                    {status:500, headers:{'Content-Type':'application/json'}}
                ));
            }
            return window.__origFetch.call(this, u, o);
        };
    }""")
    print("Mock HTTP 500 injetado.")

    # Clicar no primeiro botão Visualizar habilitado
    btns = page.locator("button[aria-label^='Visualizar ']:not([disabled])").all()
    if not btns:
        print("ERRO: Nenhum botão 'Visualizar' habilitado encontrado!")
    else:
        btns[0].click()
        print(f"Clicado em: {btns[0].get_attribute('aria-label')}")
        # Aguardar o Side Sheet aparecer
        page.wait_for_selector("[data-zds-id='ZdsSideSheet']", timeout=10000)
        print("Side Sheet aberto. Aguardando estado de erro (5s)...")
        time.sleep(5)

        # Capturar HTML interno
        html = page.locator("[data-zds-id='ZdsSideSheet']").inner_html()
        print("\n" + "="*60)
        print("HTML do ZdsSideSheet (truncado em 4000 chars):")
        print("="*60)
        print(html[:4000])
        print("="*60)

        # Listar todos os atributos data-* e class dos elementos filhos
        elements_info = page.evaluate("""() => {
            const ss = document.querySelector('[data-zds-id="ZdsSideSheet"]');
            if (!ss) return [];
            return Array.from(ss.querySelectorAll('*')).map(el => ({
                tag: el.tagName,
                dataZds: el.getAttribute('data-zds-id'),
                role: el.getAttribute('role'),
                classes: el.className,
                text: el.innerText?.slice(0, 80)
            })).filter(e => e.dataZds || e.role || e.classes?.includes('error') || e.classes?.includes('Error') || e.classes?.includes('Alert') || e.classes?.includes('alert'));
        }""")
        print("\nElementos relevantes dentro do ZdsSideSheet:")
        for el in elements_info:
            print(f"  {el['tag']} | data-zds-id={el['dataZds']} | role={el['role']} | class={el['classes'][:80]} | text={el['text']}")

    input("\nPressione ENTER para fechar o browser...")
    browser.close()
