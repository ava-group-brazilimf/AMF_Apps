#!/usr/bin/env python3
"""Unit tests for gen_screen_flow.py covering Delphi and .NET JSON schemas."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

# Import gen_screen_flow as a module from the same directory.
_MODULE_DIR = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "gen_screen_flow", _MODULE_DIR / "gen_screen_flow.py"
)
gen_screen_flow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_screen_flow)


SAMPLE_DELPHI = {
    "payload": {
        "forms": [
            {
                "form_name": "frmCustomer",
                "source_file": "src/modules/customer/frmCustomer.pas",
                "field_count": 12,
                "has_validation": True,
                "event_handler_count": 4,
            },
            {
                "form_name": "frmOrderList",
                "source_file": "src/modules/order/frmOrderList.pas",
                "field_count": 8,
                "has_validation": False,
                "event_handler_count": 2,
            },
            {
                "form_name": "frmProductDetail",
                "source_file": "src/modules/catalog/frmProductDetail.pas",
                "field_count": 15,
                "has_validation": True,
                "event_handler_count": 6,
            },
        ]
    }
}


SAMPLE_DOTNET = {
    "Artifact": "form_business_rules",
    "SchemaVersion": "1.0.0",
    "Payload": [
        {
            "Name": "CustomerController",
            "FormType": "mvc",
            "BaseType": "BaseController",
            "Controls": ["FirstName", "LastName", "Email"],
            "EventHandlers": ["Save", "Cancel"],
            "SourceRef": {
                "file": "src/Presentation/Nop.Web/Controllers/CustomerController.cs",
                "line": 10,
                "containing_type": "CustomerController",
            },
        },
        {
            "Name": "CatalogController",
            "FormType": "mvc",
            "BaseType": "BaseController",
            "Controls": [],
            "EventHandlers": ["Index"],
            "SourceRef": {
                "file": "src/Presentation/Nop.Web/Controllers/CatalogController.cs",
                "line": 20,
                "containing_type": "CatalogController",
            },
        },
        {
            "Name": "ShippingAddressForm",
            "FormType": "webforms",
            "BaseType": "System.Web.UI.Page",
            "Controls": ["Street", "City", "Zip"],
            "EventHandlers": ["Submit"],
            "SourceRef": {
                "file": "src/Presentation/Nop.Web/Administration/ShippingAddressForm.aspx",
                "line": 5,
                "containing_type": "ShippingAddressForm",
            },
        },
    ],
    "_Volatile": {},
}


BC_MAP_DELPHI = """# Bounded Context Map — MeuERP

### BC-01: Customer
**Units list**: uCustomer.pas, frmCustomer.pas
**LOC**: 1200
**Risk**: LOW

### BC-02: Order
**Units list** (forms): uOrder.pas, frmOrderList.pas
**LOC**: 3400
**Risk**: MEDIUM

### BC-03: Catalog
**Units list**: uProduct.pas, frmProductDetail.pas
**LOC**: 2100
**Risk**: LOW
"""


BC_MAP_DOTNET = """# Bounded Context Map — nopCommerce

## BC-01: Customer
**Forms/Pages**: 2
**Files**: CustomerController.cs, CustomerService.cs
**LOC**: 1200
**Risk**: LOW

## BC-02: Catalog
**Forms/Pages**: 1
**Files**: CatalogController.cs, ProductService.cs
**LOC**: 3400
**Risk**: MEDIUM

## BC-03: Shipping
**Forms/Pages**: 1
**Files**: ShippingAddressForm.aspx, ShippingService.cs
**LOC**: 2100
**Risk**: LOW
"""


class TestSchemaExtraction(unittest.TestCase):
    def test_extract_forms_delphi(self):
        forms = gen_screen_flow.extract_forms(SAMPLE_DELPHI)
        self.assertEqual(len(forms), 3)
        self.assertEqual(forms[0]["form_name"], "frmCustomer")

    def test_extract_forms_dotnet(self):
        forms = gen_screen_flow.extract_forms(SAMPLE_DOTNET)
        self.assertEqual(len(forms), 3)
        self.assertEqual(forms[0]["Name"], "CustomerController")

    def test_extract_forms_empty(self):
        self.assertEqual(gen_screen_flow.extract_forms({}), [])
        self.assertEqual(gen_screen_flow.extract_forms({"payload": {"forms": []}}), [])
        self.assertEqual(gen_screen_flow.extract_forms({"Payload": []}), [])


class TestFormNormalization(unittest.TestCase):
    def test_normalize_delphi(self):
        raw = SAMPLE_DELPHI["payload"]["forms"][0]
        norm = gen_screen_flow.normalize_form(raw)
        self.assertEqual(norm["form_name"], "frmCustomer")
        self.assertEqual(norm["source_file"], "src/modules/customer/frmCustomer.pas")
        self.assertEqual(norm["field_count"], 12)

    def test_normalize_dotnet(self):
        raw = SAMPLE_DOTNET["Payload"][0]
        norm = gen_screen_flow.normalize_form(raw)
        self.assertEqual(norm["form_name"], "CustomerController")
        self.assertEqual(
            norm["source_file"],
            "src/Presentation/Nop.Web/Controllers/CustomerController.cs",
        )
        self.assertEqual(norm["field_count"], 3)
        self.assertEqual(norm["form_type"], "mvc")

    def test_normalize_dotnet_empty_controls(self):
        raw = SAMPLE_DOTNET["Payload"][1]
        norm = gen_screen_flow.normalize_form(raw)
        self.assertEqual(norm["field_count"], 0)


class TestTokenizer(unittest.TestCase):
    def test_tokenize_pascalcase(self):
        self.assertIn("customer", gen_screen_flow.tokenize("CustomerController"))
        self.assertIn("controller", gen_screen_flow.tokenize("CustomerController"))

    def test_tokenize_snake_case(self):
        tokens = gen_screen_flow.tokenize("customer_order_detail")
        self.assertIn("customer", tokens)
        self.assertIn("order", tokens)
        self.assertIn("detail", tokens)

    def test_tokenize_kebab_case(self):
        tokens = gen_screen_flow.tokenize("customer-order-detail")
        self.assertIn("customer", tokens)
        self.assertIn("order", tokens)
        self.assertIn("detail", tokens)

    def test_noise_filters_net_extensions(self):
        # tokenize() only splits text; the NOISE set is applied by build_token_index().
        bcs = {
            "BC-01: Catalog": {
                "name": "Catalog",
                "units": ["catalogcontroller"],
                "tokens": set(),
            }
        }
        exact, token_pairs = gen_screen_flow.build_token_index(bcs)
        self.assertEqual(exact.get("catalogcontroller"), "BC-01: Catalog")
        # Extension-only and framework-only tokens must not create token pairs.
        noise_tokens = {"cs", "aspx", "vb", "controller", "view", "model", "page"}
        found = {tok for tok, _ in token_pairs}
        self.assertTrue(
            found.isdisjoint(noise_tokens),
            f"Noise tokens leaked into token_pairs: {found & noise_tokens}",
        )


class TestBcMapParsing(unittest.TestCase):
    def _write_bc_map(self, content):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            return Path(fh.name)

    def test_parse_delphi_bc_map(self):
        path = self._write_bc_map(BC_MAP_DELPHI)
        try:
            bcs = gen_screen_flow.parse_bc_map(path)
            self.assertEqual(len(bcs), 3)
            self.assertIn("BC-01: Customer", bcs)
            self.assertIn("frmcustomer", bcs["BC-01: Customer"]["units"])
        finally:
            os.unlink(path)

    def test_parse_dotnet_bc_map(self):
        path = self._write_bc_map(BC_MAP_DOTNET)
        try:
            bcs = gen_screen_flow.parse_bc_map(path)
            self.assertEqual(len(bcs), 3)
            self.assertIn("BC-01: Customer", bcs)
            self.assertIn("customercontroller", bcs["BC-01: Customer"]["units"])
            self.assertIn("catalogcontroller", bcs["BC-02: Catalog"]["units"])
        finally:
            os.unlink(path)


class TestClassification(unittest.TestCase):
    def test_classify_dotnet_with_bc_map(self):
        path = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        path.write(BC_MAP_DOTNET)
        path.close()
        try:
            bcs = gen_screen_flow.parse_bc_map(Path(path.name))
            exact, token_pairs = gen_screen_flow.build_token_index(bcs)
            customer = gen_screen_flow.normalize_form(SAMPLE_DOTNET["Payload"][0])
            catalog = gen_screen_flow.normalize_form(SAMPLE_DOTNET["Payload"][1])
            shipping = gen_screen_flow.normalize_form(SAMPLE_DOTNET["Payload"][2])

            self.assertEqual(
                gen_screen_flow.classify_form(customer, exact, token_pairs),
                "BC-01: Customer",
            )
            self.assertEqual(
                gen_screen_flow.classify_form(catalog, exact, token_pairs),
                "BC-02: Catalog",
            )
            self.assertEqual(
                gen_screen_flow.classify_form(shipping, exact, token_pairs),
                "BC-03: Shipping",
            )
        finally:
            os.unlink(path.name)


class TestEndToEnd(unittest.TestCase):
    def _run_script(self, payload, bc_map_content=None):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "forms.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")

            output_path = Path(tmpdir) / "screen-flow.mmd"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            bc_map_path = None
            if bc_map_content:
                bc_map_path = Path(tmpdir) / "bounded-context-map.md"
                bc_map_path.write_text(bc_map_content, encoding="utf-8")

            argv = [
                "gen_screen_flow.py",
                "--project",
                "testproject",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
            ]
            if bc_map_path:
                argv.extend(["--bc-map", str(bc_map_path)])

            old_argv = list(gen_screen_flow.sys.argv)
            try:
                gen_screen_flow.sys.argv = argv
                with self.assertRaises(SystemExit) as cm:
                    gen_screen_flow.main()
            finally:
                gen_screen_flow.sys.argv = old_argv
            self.assertEqual(cm.exception.code, 0)

            self.assertTrue(output_path.exists())
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("flowchart TD", content)
            return {f.name for f in output_path.parent.glob("*")}

    def test_end_to_end_dotnet(self):
        names = self._run_script(SAMPLE_DOTNET, BC_MAP_DOTNET)
        self.assertIn("screen-flow-BC-01--Customer.mmd", names)
        self.assertIn("screen-flow-manifest.json", names)

    def test_end_to_end_delphi(self):
        names = self._run_script(SAMPLE_DELPHI, BC_MAP_DELPHI)
        self.assertIn("screen-flow-BC-01--Customer.mmd", names)
        self.assertIn("screen-flow-manifest.json", names)

    def test_end_to_end_recursive_split(self):
        """Large BC should be recursively split into subgroup diagrams."""
        forms = {
            "payload": {
                "forms": [
                    {
                        "form_name": f"frmProduct{i:03d}",
                        "source_file": f"src/modules/catalog/frmProduct{i:03d}.pas",
                        "field_count": 5,
                    }
                    for i in range(100)
                ]
            }
        }
        names = self._run_script(forms, BC_MAP_DELPHI)
        subgroup_names = [n for n in names if n.startswith("screen-flow-") and "-frmproduct" in n and n.endswith(".mmd")]
        self.assertGreater(len(subgroup_names), 1, "Expected recursive subgroup diagrams")
        self.assertIn("screen-flow-manifest.json", names)


if __name__ == "__main__":
    unittest.main()
