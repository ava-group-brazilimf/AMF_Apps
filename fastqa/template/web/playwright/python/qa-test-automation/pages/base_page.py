from playwright.sync_api import Page, expect


class BasePage:
    """Classe base para concentrar utilidades comuns e evitar repetição espalhada."""

    def __init__(self, page: Page):
        self.page = page

    def open(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")

    def current_url_should_be(self, expected_url: str) -> None:
        expect(self.page).to_have_url(expected_url)
