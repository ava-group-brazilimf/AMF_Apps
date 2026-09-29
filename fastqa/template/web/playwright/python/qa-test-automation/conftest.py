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


# =========================
# Preparação das pastas
# =========================

@pytest.fixture(scope="session", autouse=True)
def prepare_artifacts():
    """Garante uma área limpa para evidências antes da execução."""

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

    logger.info("Pastas de artefatos preparadas com sucesso.")

    yield


# =========================
# Browser lento (debug/demo)
# =========================

@pytest.fixture(scope="session")
def browser_type_launch_args():
    return {
        "slow_mo": 1000
    }


# =========================
# Contexto do browser
# =========================

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "ignore_https_errors": True,
        "viewport": {"width": 1440, "height": 900},
        "record_video_dir": "artifacts/videos",
        "record_video_size": {"width": 1280, "height": 720},
    }


# =========================
# Page fixture
# =========================

@pytest.fixture
def app_page(browser: Browser) -> Page:
    headless = os.getenv("HEADLESS", "false").lower() == "true"

    logger.info(
        "Iniciando contexto de teste | headless=%s",
        headless
    )

    context = browser.new_context(
        ignore_https_errors=True,
        viewport={"width": 1440, "height": 900},
        record_video_dir="artifacts/videos",
        record_video_size={"width": 1280, "height": 720},
    )

    page = context.new_page()

    yield page

    logger.info(
        "Encerrando página e contexto para persistir vídeo."
    )

    page.close()
    context.close()


# =========================
# Captura resultado pytest
# =========================

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    setattr(item, f"rep_{report.when}", report)


# =========================
# Fixture de evidência por teste
# =========================

@pytest.fixture
def test_evidence(request):

    evidence = TestEvidence(request.node.name)

    evidence.start()

    return evidence


# =========================
# Coletor automático de evidência
# =========================

@pytest.fixture(autouse=True)
def evidence_collector(request, app_page: Page):

    yield

    safe_name = (
        request.node.name.replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace("::", "_")
    )

    screenshot_dir = Path("artifacts/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    screenshot_path = screenshot_dir / f"{safe_name}.png"

    app_page.screenshot(
        path=str(screenshot_path),
        full_page=True
    )

    with open(screenshot_path, "rb") as image_file:
        allure.attach(
            image_file.read(),
            name=f"{safe_name}_screenshot",
            attachment_type=allure.attachment_type.PNG,
        )

    logger.info(
        "Screenshot anexado ao Allure: %s",
        screenshot_path
    )

    # =========================
    # URL final
    # =========================

    final_url = ""

    try:
        final_url = app_page.url

    except Exception:

        final_url = (
            "Nao foi possivel obter a URL final."
        )

    # =========================
    # Criar evidência TXT
    # =========================

    evidence = TestEvidence(request.node.name)

    if (
        getattr(request.node, "rep_call", None)
        and request.node.rep_call.failed
    ):

        logger.error(
            "Teste falhou: %s",
            safe_name
        )

        evidence.end(
            status="FAILED",
            final_url=final_url
        )

    else:

        logger.info(
            "Teste concluído com sucesso: %s",
            safe_name
        )

        evidence.end(
            status="PASSED",
            final_url=final_url
        )

    # =========================
    # Anexar TXT no Allure
    # =========================

    txt_log_path = (
        Path("artifacts/logs/tests")
        / f"{safe_name}.txt"
    )

    if txt_log_path.exists():

        with open(
            txt_log_path,
            "rb"
        ) as txt_file:

            allure.attach(
                txt_file.read(),
                name=f"{safe_name}_txt_log",
                attachment_type=allure.attachment_type.TEXT,
            )