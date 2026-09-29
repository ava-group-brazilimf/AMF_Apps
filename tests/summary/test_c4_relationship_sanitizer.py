import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py"
spec = importlib.util.spec_from_file_location("summary_builder", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_quotes_observed_c4_relationship_arguments():
    source = (ROOT / "tests/summary/fixtures/c4-rel-malformed-observed.mmd").read_text(encoding="utf-8")
    corrected = module._quote_c4_relationship_arguments(source)
    assert 'Rel(a, b, "Integrates with", "REST API")' in corrected
    assert 'Rel(a, b, "Validates tokens", "MSAL")' in corrected
    assert 'Rel(a, b, "Reads via", "Dapper read model")' in corrected


def test_multiline_c4_relationship_is_quoted():
    source = 'Rel(api, auth,\n    Validates tokens, MSAL)\n'
    corrected = module._quote_c4_relationship_arguments(source)
    assert 'Rel(api, auth, "Validates tokens", "MSAL")' in corrected
