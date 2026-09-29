"""
save_session.py — FastQA Login Manual Helper
=============================================
Abre o browser na tela de login.
Você faz o login completo (usuário, senha, OTP, etc.).
Quando estiver na home, pressione ENTER aqui no terminal.
O script salva storage_state.json e fecha o browser.

Uso:
    python scripts/save_session.py
"""
import os
import sys
import pathlib
from playwright.sync_api import sync_playwright

# --- Configuração ---
BASE_URL = os.getenv(
    "BASE_URL",
    "https://hiae-cockpit-prm-portaladm-frontend.qas.telemedicinaeinstein.com.br"
)
LOGIN_PATH = "/login"
STORAGE_PATH = pathlib.Path(__file__).parent.parent / ".auth" / "storage_state.json"
STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()

        print(f"\n{'='*60}")
        print("  FastQA — Salvar Sessão de Login")
        print(f"{'='*60}")
        print(f"  Abrindo: {BASE_URL}{LOGIN_PATH}")
        print("  Faça o login completo no browser (usuário, senha, OTP).")
        print("  Quando estiver na tela principal, volte aqui e pressione ENTER.")
        print(f"{'='*60}\n")

        page.goto(f"{BASE_URL}{LOGIN_PATH}")

        input("  >> Pressione ENTER quando estiver logado e na tela inicial: ")

        current_url = page.url
        print(f"\n  URL atual: {current_url}")

        context.storage_state(path=str(STORAGE_PATH))
        print(f"  Sessão salva em: {STORAGE_PATH}")

        browser.close()
        print("\n  Pronto! Agora rode os testes com:")
        print("  robot --outputdir results/attempt6 --include smoke tests/categorias_listagem.robot\n")


if __name__ == "__main__":
    main()
