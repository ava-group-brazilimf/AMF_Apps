from pathlib import Path
from datetime import datetime


class TestEvidence:
    """Responsável por gerar evidência textual individual por teste."""

    def __init__(self, test_name: str):
        safe_name = (
            test_name.replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
            .replace("::", "_")
        )

        self.test_name = safe_name

        self.log_dir = Path("artifacts/logs/tests")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.file_path = self.log_dir / f"{self.test_name}.txt"

    def write(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.file_path, "a", encoding="utf-8") as file:
            file.write(f"{timestamp} | {message}\n")

    def start(self) -> None:
        self.write(f"INICIO DO TESTE: {self.test_name}")

    def end(self, status: str, final_url: str = "") -> None:
        self.write(f"FIM DO TESTE: {self.test_name}")
        self.write(f"STATUS FINAL: {status}")

        if final_url:
            self.write(f"URL FINAL: {final_url}")

        self.write("-" * 80)