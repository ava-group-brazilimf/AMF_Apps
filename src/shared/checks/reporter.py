"""
reporter.py — collects and prints check results.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List


@dataclass
class CheckResult:
    suite: str
    name: str
    passed: bool
    detail: str = ""
    #: False para check cuja reprovação é lacuna de QUALIDADE do que foi gerado
    #: (ex.: catálogo tem a regra, nenhuma task a referencia) e não corrupção do
    #: artefato. Só esses podem ser aceitos como risco pelo operador; grafo
    #: cíclico, referência quebrada ou schema inválido nunca são negociáveis.
    blocking: bool = True


class Reporter:
    #: Exit code quando há falhas e TODAS são não-bloqueantes. O runner usa este
    #: código para oferecer a decisão ao operador; qualquer outro não-zero aborta.
    SOFT_FAIL_EXIT = 3

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._results: List[CheckResult] = []

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self._results)

    def to_dict(self) -> dict:
        """Serializa os resultados coletados — mesma fonte usada por print_summary().

        Existe para que o resultado 100% determinístico de uma suíte sobreviva ao
        subprocess que a executou: sem isto, `python -m src.shared.checks` só
        imprime no console, e nada a jusante (agente de compliance, exit gate)
        consegue reagir a um achado como "âncora inexistente" — ele se perde no
        log do runner igual a um achado estocástico do LLM.
        """
        total = len(self._results)
        fails = [r for r in self._results if not r.passed]
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total": total,
            "passed": total - len(fails),
            "failed": len(fails),
            "all_passed": not fails,
            "results": [asdict(r) for r in self._results],
        }

    def write_json(self, path: "str | Path") -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\n  📄 Resultado estruturado salvo: {target}")

    @property
    def hard_failures(self) -> List[CheckResult]:
        return [r for r in self._results if not r.passed and r.blocking]

    @property
    def soft_failures(self) -> List[CheckResult]:
        return [r for r in self._results if not r.passed and not r.blocking]

    @property
    def exit_code(self) -> int:
        """0 tudo passou · 3 só lacunas de qualidade · 1 há falha estrutural."""
        if self.all_passed:
            return 0
        return 1 if self.hard_failures else self.SOFT_FAIL_EXIT

    def record(self, suite: str, name: str, passed: bool, detail: str = "",
               *, blocking: bool = True) -> None:
        self._results.append(CheckResult(suite, name, passed, detail, blocking))
        label = "OK  " if passed else "FAIL"
        line = f"  [{label}] {name}"
        if detail and (not passed or self.verbose):
            line += f"\n         → {detail}"
        print(line)

    def print_summary(self) -> None:
        total = len(self._results)
        fails = sum(1 for r in self._results if not r.passed)
        print()
        if fails == 0:
            print(f"  ✅ All {total} checks passed.")
        else:
            duros, leves = len(self.hard_failures), len(self.soft_failures)
            resumo = f"  ❌ {fails}/{total} checks FAILED."
            if duros and leves:
                resumo += f"  ({duros} estrutural(is), {leves} de cobertura)"
            elif not duros:
                resumo += "  (todas de cobertura — não impedem a fase seguinte)"
            print(resumo)
            print()
            print("  Failed checks:")
            for r in self._results:
                if not r.passed:
                    detail_str = f" — {r.detail}" if r.detail else ""
                    marca = "" if r.blocking else " [cobertura]"
                    print(f"    [{r.suite}]{marca} {r.name}{detail_str}")
