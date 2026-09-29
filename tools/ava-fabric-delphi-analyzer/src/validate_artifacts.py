"""
validate_artifacts.py — Valida os 8 JSONs de extração contra o JSON Schema do
contrato de artefatos (src/schemas/artifacts.schema.json).

Uso:
    python src/validate_artifacts.py <extraction_dir>

Sai com código 0 (sem violações) ou 1 (imprime cada violação encontrada).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

SCHEMA_PATH = Path(__file__).parent / "schemas" / "artifacts.schema.json"


def validate_dir(extraction_dir: str | Path) -> list[str]:
    """Valida todo *.json em extraction_dir contra o schema. Retorna lista de erros (vazia = ok)."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors: list[str] = []

    extraction_dir = Path(extraction_dir)
    json_files = sorted(extraction_dir.glob("*.json"))
    if not json_files:
        return [f"nenhum .json encontrado em {extraction_dir}"]

    for fp in json_files:
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{fp.name}: JSON inválido ({e})")
            continue
        for err in validator.iter_errors(doc):
            path = "/".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(f"{fp.name}: {path}: {err.message}")

    return errors


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python src/validate_artifacts.py <extraction_dir>", file=sys.stderr)
        sys.exit(1)

    violations = validate_dir(sys.argv[1])
    if violations:
        print(f"FALHA: {len(violations)} violação(ões) de schema:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        sys.exit(1)

    print("OK: todos os artefatos conformes ao schema.")
