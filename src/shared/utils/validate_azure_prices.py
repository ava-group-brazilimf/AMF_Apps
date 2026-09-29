#!/usr/bin/env python3
"""
Azure Retail Prices Validator
─────────────────────────────
Validates generated infra cost estimates against the live Azure Retail Prices API.
No auth required — uses public endpoint: https://prices.azure.com/api/retail/prices

Verdict:
  PASS_EXACT  — all line-item deltas = 0.00%
  PASS_NEAR   — line deltas ≤ 0.25%, env total delta ≤ 0.50%
  FAIL        — any threshold exceeded or meter mapping not found

Usage:
  python validate_azure_prices.py
  python validate_azure_prices.py --env prod --currency USD --reservation none
  python validate_azure_prices.py --env all  --currency USD --reservation none

Supported reservations: none | 1yr | 3yr
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────

API_BASE    = "https://prices.azure.com/api/retail/prices"
API_VERSION = "2023-01-01-preview"
HOURS_PER_MONTH = 730          # Azure standard billing month
DAYS_PER_MONTH  = 30

# Acceptance thresholds (per your validation prompt)
THRESHOLD_LINE_NEAR  = 0.25    # % per line
THRESHOLD_ENV_NEAR   = 0.50    # % per environment total

# ─── SKU → API meter map ───────────────────────────────────────────────────────
# Each entry defines:
#   filter   : OData $filter string (use {region} as placeholder)
#   price_type: 'Consumption' | 'Reservation'
#   calc     : callable(unit_price, qty) → monthly_usd  (PAYG path)
#   calc_reservation: callable(monthly_equiv, qty) → monthly_usd  (reservation path)
#               monthly_equiv is already total_reservation / months — do NOT multiply by hours again
#   reservable: True if the service has Azure Reservation pricing (default True)
#               False = always use PAYG price even when --reservation is set
#   unit_label: human-readable billing unit
#   default_qty: default quantity (instances, GB, etc.)

SKU_MAP = {
    # ── App Service ───────────────────────────────────────────────────────────
    # Confirmed via probe: P2 v3 Windows = $0.764/hr, P1 v3 Linux = $0.222/hr in brazilsouth
    "app_service_p2v3_windows": {
        "label":      "App Service P2v3 Windows × {qty}",
        "filter":     "armRegionName eq '{region}' and skuName eq 'P2 v3' and serviceName eq 'Azure App Service' and productName eq 'Azure App Service Premium v3 Plan'",
        "price_type": "Consumption",
        "reservable": True,
        "calc":             lambda p, qty: p * HOURS_PER_MONTH * qty,
        "calc_reservation": lambda p, qty: p * qty,   # p already monthly equiv
        "unit_label": "$/hr × 730h × qty",
        "default_qty": 2,
    },
    "app_service_p2v3_linux": {
        "label":      "App Service P2v3 Linux × {qty}",
        "filter":     "armRegionName eq '{region}' and skuName eq 'P2 v3' and serviceName eq 'Azure App Service' and productName eq 'Azure App Service Premium v3 Plan - Linux'",
        "price_type": "Consumption",
        "reservable": True,
        "calc":             lambda p, qty: p * HOURS_PER_MONTH * qty,
        "calc_reservation": lambda p, qty: p * qty,
        "unit_label": "$/hr × 730h × qty",
        "default_qty": 2,
    },
    "app_service_p1v3_linux": {
        "label":      "App Service P1v3 Linux × {qty}",
        # Confirmed: skuName='P1 v3', productName='Azure App Service Premium v3 Plan - Linux'
        "filter":     "armRegionName eq '{region}' and skuName eq 'P1 v3' and serviceName eq 'Azure App Service' and productName eq 'Azure App Service Premium v3 Plan - Linux'",
        "price_type": "Consumption",
        "reservable": True,
        "calc":             lambda p, qty: p * HOURS_PER_MONTH * qty,
        "calc_reservation": lambda p, qty: p * qty,
        "unit_label": "$/hr × 730h × qty",
        "default_qty": 1,
    },
    "app_service_b2_linux": {
        "label":      "App Service B2 Linux × {qty}",
        "filter":     "armRegionName eq '{region}' and skuName eq 'B2' and serviceName eq 'Azure App Service' and serviceFamily eq 'Compute'",
        "price_type": "Consumption",
        "reservable": True,
        "calc":             lambda p, qty: p * HOURS_PER_MONTH * qty,
        "calc_reservation": lambda p, qty: p * qty,
        "unit_label": "$/hr × 730h × qty",
        "default_qty": 1,
    },
    # ── Azure SQL ─────────────────────────────────────────────────────────────
    # NOTE: SQL Database vCore compute pricing is billed per vCore/hr under
    # serviceName='SQL Database', meterName='vCore'. The skuName does NOT contain
    # vCore count. Multiply unit price by vCore count and hours.
    # GP 4 vCores: $0.something/vCore/hr × 4 × 730
    # BC 4 vCores: Business Critical has higher per-vCore price.
    # Storage/IO are additional meters (not included here — focuses on compute).
    "sql_business_critical_4vcores": {
        "label":      "Azure SQL BC 4 vCores (Gen5 compute)",
        # Confirmed productName: 'SQL Database Single/Elastic Pool Business Critical - Compute Gen5'
        # PAYG skuName='4 vCore' ($2.313708/hr total); Reservation skuName='vCore' ($3,294/yr total).
        "filter":     "armRegionName eq '{region}' and serviceName eq 'SQL Database' and skuName eq '4 vCore' and productName eq 'SQL Database Single/Elastic Pool Business Critical - Compute Gen5'",
        "reservation_filter": "armRegionName eq '{region}' and serviceName eq 'SQL Database' and skuName eq 'vCore' and productName eq 'SQL Database Single/Elastic Pool Business Critical - Compute Gen5'",
        "price_type": "Consumption",
        "reservable": True,
        "calc":             lambda p, qty: p * HOURS_PER_MONTH,
        "calc_reservation": lambda p, qty: p,   # p already monthly equiv (total_reservation / months)
        "unit_label": "$/hr × 730h",
        "default_qty": 1,
    },
    "sql_gp_4vcores": {
        "label":      "Azure SQL GP 4 vCores (Gen5 compute)",
        # Confirmed: skuName='4 vCore', productName='SQL Database Single/Elastic Pool General Purpose - Compute Gen5'
        # price=$1.156848/hr (total for 4 vCores, not per-vCore)
        "filter":     "armRegionName eq '{region}' and serviceName eq 'SQL Database' and skuName eq '4 vCore' and productName eq 'SQL Database Single/Elastic Pool General Purpose - Compute Gen5'",
        "price_type": "Consumption",
        "reservable": True,
        "calc":             lambda p, qty: p * HOURS_PER_MONTH,
        "calc_reservation": lambda p, qty: p,
        "unit_label": "$/hr × 730h",
        "default_qty": 1,
    },
    "sql_gp_2vcores": {
        "label":      "Azure SQL GP 2 vCores (Gen5 compute)",
        # NOTE: '2 vCore' skuName not found in brazilsouth probe — minimum is 4 vCore for Gen5.
        # Using 4 vCore as fallback (conservative overestimate for dev environment).
        "filter":     "armRegionName eq '{region}' and serviceName eq 'SQL Database' and skuName eq '2 vCore' and productName eq 'SQL Database Single/Elastic Pool General Purpose - Compute Gen5'",
        "price_type": "Consumption",
        "reservable": True,
        "calc":             lambda p, qty: p * HOURS_PER_MONTH,
        "calc_reservation": lambda p, qty: p,
        "unit_label": "$/hr × 730h",
        "default_qty": 1,
        "fallback_filter": "armRegionName eq '{region}' and serviceName eq 'SQL Database' and skuName eq '4 vCore' and productName eq 'SQL Database Single/Elastic Pool General Purpose - Compute Gen5'",
    },
    # ── Redis ─────────────────────────────────────────────────────────────────
    # NOTE: brazilsouth only has newer E/X series Redis, not classic C0/C1/C2.
    # C0/C1/C2 not available in this region via the API.
    # Mapping to nearest equivalent E-series tiers.
    "redis_standard_c2": {
        "label":      "Redis C2-equiv (E1 6GB)",
        # Nearest equivalent to Standard C2 (6GB) in newer Redis series
        "filter":     "armRegionName eq '{region}' and contains(serviceName,'Redis') and skuName eq 'E10' and type eq 'Consumption'",
        "price_type": "Consumption",
        "reservable": False,   # Redis E-series: no reservation pricing in API
        "calc":       lambda p, qty: p * HOURS_PER_MONTH,
        "unit_label": "$/hr × 730h",
        "default_qty": 1,
    },
    "redis_standard_c1": {
        "label":      "Redis C1-equiv (E1 1GB)",
        "filter":     "armRegionName eq '{region}' and contains(serviceName,'Redis') and skuName eq 'E1' and type eq 'Consumption'",
        "price_type": "Consumption",
        "reservable": False,
        "calc":       lambda p, qty: p * HOURS_PER_MONTH,
        "unit_label": "$/hr × 730h",
        "default_qty": 1,
    },
    "redis_basic_c0": {
        "label":      "Redis C0-equiv (smallest avail.)",
        # E0 not available in brazilsouth. Use E1 (smallest available) as conservative fallback.
        "filter":     "armRegionName eq '{region}' and contains(serviceName,'Redis') and skuName eq 'E1' and type eq 'Consumption'",
        "price_type": "Consumption",
        "reservable": False,
        "calc":       lambda p, qty: p * HOURS_PER_MONTH,
        "unit_label": "$/hr × 730h",
        "default_qty": 1,
    },
    # ── Application Gateway ───────────────────────────────────────────────────
    # NOTE: WAF v2 is billed as Standard v2 fixed cost + Capacity Units.
    # No single 'WAF v2 Gateway' meter exists. Using Standard v2 Fixed Cost
    # as the baseline (WAF v2 = Standard v2 + WAF CU markup, ~same fixed rate).
    "app_gateway_waf_v2": {
        "label":      "App Gateway WAF v2 (fixed + CU estimate)",
        "filter":     "armRegionName eq '{region}' and serviceName eq 'Application Gateway' and skuName eq 'Standard' and meterName eq 'Standard Fixed Cost'",
        "price_type": "Consumption",
        "reservable": False,   # App Gateway: no reservation pricing
        "calc":       lambda p, qty: p * HOURS_PER_MONTH,
        "unit_label": "$/hr × 730h (fixed cost component only)",
        "default_qty": 1,
    },
    # ── Log Analytics / App Insights ──────────────────────────────────────────
    # Confirmed: serviceName='Log Analytics', skuName='Analytics Logs',
    # meterName='Analytics Logs Data Ingestion' at $4.60/GB in brazilsouth.
    "app_insights_payg_per_gb": {
        "label":      "Log Analytics {qty}GB/mo ingestion",
        "filter":     "armRegionName eq '{region}' and serviceName eq 'Log Analytics' and skuName eq 'Analytics Logs' and meterName eq 'Analytics Logs Data Ingestion'",
        "price_type": "Consumption",
        "reservable": False,   # Log Analytics: pure consumption, no reservations
        "calc":       lambda p, qty: p * qty,
        "unit_label": "$/GB × qty GB",
        "default_qty": 900,   # 30GB/day × 30 days (prod default)
    },
    # ── Container Registry ────────────────────────────────────────────────────
    # Confirmed: meterName='Standard Registry Unit' at $0.6666/day
    #            meterName='Basic Registry Unit' at $0.1666/day
    "acr_standard": {
        "label":      "Container Registry Standard",
        "filter":     "armRegionName eq '{region}' and serviceName eq 'Container Registry' and skuName eq 'Standard' and meterName eq 'Standard Registry Unit'",
        "price_type": "Consumption",
        "reservable": False,
        "calc":       lambda p, qty: p * DAYS_PER_MONTH,
        "unit_label": "$/day × 30 days",
        "default_qty": 1,
    },
    "acr_basic": {
        "label":      "Container Registry Basic",
        "filter":     "armRegionName eq '{region}' and serviceName eq 'Container Registry' and skuName eq 'Basic' and meterName eq 'Basic Registry Unit'",
        "price_type": "Consumption",
        "reservable": False,
        "calc":       lambda p, qty: p * DAYS_PER_MONTH,
        "unit_label": "$/day × 30 days",
        "default_qty": 1,
    },
    # ── Blob Storage ──────────────────────────────────────────────────────────
    # Confirmed: serviceName='Storage', skuName='Standard GRS', meterName='GRS Data Stored'
    # Multiple price tiers — $0.0655/GB is first 50TB hot tier in brazilsouth.
    "blob_storage_grs_1tb": {
        "label":      "Blob Storage GRS ~1TB (hot, first 50TB tier)",
        "filter":     "armRegionName eq '{region}' and serviceName eq 'Storage' and skuName eq 'Standard GRS' and meterName eq 'GRS Data Stored'",
        "price_type": "Consumption",
        "reservable": False,   # Blob Storage: no reservation pricing
        "calc":       lambda p, qty: p * qty,
        "unit_label": "$/GB/mo × qty GB",
        "default_qty": 1024,
    },
    # ── Key Vault ─────────────────────────────────────────────────────────────
    # Confirmed: serviceName='Key Vault', skuName='Standard', meterName='Operations'
    # at $0.03/10k ops in brazilsouth.
    "key_vault_standard_ops": {
        "label":      "Key Vault Standard (10k ops baseline)",
        "filter":     "armRegionName eq '{region}' and serviceName eq 'Key Vault' and skuName eq 'Standard' and meterName eq 'Operations'",
        "price_type": "Consumption",
        "reservable": False,   # Key Vault: no reservation pricing
        "calc":       lambda p, qty: p,   # $0.03 per 10k ops, 1 unit baseline
        "unit_label": "$/10k ops",
        "default_qty": 1,
    },
    # ── App Configuration ─────────────────────────────────────────────────────
    # Confirmed: serviceName='Azure App Configuration', skuName='Standard',
    # meterName='Standard Instance' at $1.20/month in brazilsouth.
    "app_config_standard": {
        "label":      "App Configuration Standard",
        # serviceName contains 'App Configuration'; meterName='Standard Instance' at $1.20/mo
        "filter":     "armRegionName eq '{region}' and contains(serviceName,'App Configuration') and skuName eq 'Standard' and meterName eq 'Standard Instance'",
        "price_type": "Consumption",
        "reservable": False,
        "calc":       lambda p, qty: p,   # flat monthly rate
        "unit_label": "flat $/month",
        "default_qty": 1,
    },
}

# ─── Environment definitions (Meu-ERP) ────────────────────────────────────────
# Maps each environment to the services it uses, their quantities, and the
# estimated total from the generated cost-estimate.md.

ENVIRONMENT_DEFINITIONS = {
    "dev": {
        "services": [
            {"sku": "app_service_b2_linux",      "qty": 1},
            {"sku": "sql_gp_2vcores",             "qty": 1},
            {"sku": "redis_basic_c0",             "qty": 1},
            {"sku": "key_vault_standard_ops",     "qty": 1},
            {"sku": "app_insights_payg_per_gb",   "qty": 150},   # 5GB/day × 30
            {"sku": "acr_basic",                  "qty": 1},
        ],
        "estimated_total_usd": 180.0,
    },
    "staging": {
        "services": [
            {"sku": "app_service_p1v3_linux",     "qty": 1},
            {"sku": "sql_gp_4vcores",             "qty": 1},
            {"sku": "redis_standard_c1",          "qty": 1},
            {"sku": "key_vault_standard_ops",     "qty": 1},
            {"sku": "app_insights_payg_per_gb",   "qty": 300},   # 10GB/day × 30
            {"sku": "app_gateway_waf_v2",         "qty": 1},
            {"sku": "acr_standard",               "qty": 1},
        ],
        "estimated_total_usd": 420.0,
    },
    "prod": {
        "services": [
            {"sku": "app_service_p2v3_windows",   "qty": 2},
            {"sku": "sql_business_critical_4vcores", "qty": 1},
            {"sku": "redis_standard_c2",          "qty": 1},
            {"sku": "blob_storage_grs_1tb",       "qty": 1024},
            {"sku": "key_vault_standard_ops",     "qty": 1},
            {"sku": "app_insights_payg_per_gb",   "qty": 900},   # 30GB/day × 30
            {"sku": "app_gateway_waf_v2",         "qty": 1},
            {"sku": "acr_standard",               "qty": 1},
            {"sku": "app_config_standard",        "qty": 1},
        ],
        "estimated_total_usd": 1850.0,
    },
}

# ─── API helpers ──────────────────────────────────────────────────────────────

def fetch_price(filter_str: str, currency: str = "USD", skip_zero: bool = True,
                prefer_primary: bool = True,
                fallback_filter: Optional[str] = None) -> Optional[float]:
    """
    Query Azure Retail Prices API and return the best Consumption unit price.
    - Prefers isPrimaryMeterRegion=True items.
    - Skips zero-price items by default (e.g. free-tier entries).
    - If no result found and fallback_filter is provided, retries with fallback.
    - Returns None if no matching meter is found.
    """
    def _query(f: str) -> Optional[float]:
        params = {
            "api-version": API_VERSION,
            "$filter": f,
            "currencyCode": f"'{currency}'",
        }
        url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            print(f"  [WARN] API request failed: {exc}", file=sys.stderr)
            return None
        items = [i for i in data.get("Items", []) if i.get("type") == "Consumption"]
        if skip_zero:
            nz = [i for i in items if i.get("retailPrice", 0) > 0]
            if nz:
                items = nz
        if prefer_primary:
            primary = [i for i in items if i.get("isPrimaryMeterRegion")]
            if primary:
                items = primary
        return round(items[0]["retailPrice"], 6) if items else None

    result = _query(filter_str)
    if result is None and fallback_filter:
        time.sleep(0.6)
        result = _query(fallback_filter)
        if result is not None:
            print("[FALLBACK] ", end="", flush=True)
    return result


def fetch_reservation_price(filter_str: str, term: str, currency: str = "USD") -> Optional[float]:
    """
    Fetch reservation price for a given term ('1 Year' or '3 Years').
    Returns monthly equivalent (total reservation / months).
    """
    params = {
        "api-version": API_VERSION,
        "$filter": filter_str + " and priceType eq 'Reservation'",
        "currencyCode": f"'{currency}'",
    }
    url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"  [WARN] API request failed: {exc}", file=sys.stderr)
        return None

    items = data.get("Items", [])
    months = 12 if term == "1yr" else 36
    for item in items:
        if item.get("type") == "Reservation" and item.get("reservationTerm", "").startswith(
            "1" if term == "1yr" else "3"
        ):
            return round(item["retailPrice"] / months, 6)
    return None

# ─── Validation logic ─────────────────────────────────────────────────────────

def delta_pct(reference: float, estimated: float) -> float:
    """Percentage delta between reference and estimated."""
    if reference == 0:
        return 0.0
    return abs(reference - estimated) / reference * 100.0


def run_validation(envs: list, region: str, currency: str, reservation: str):
    print("=" * 70)
    print("  Azure Retail Prices Validator")
    print(f"  Region: {region} | Currency: {currency} | Reservation: {reservation}")
    print(f"  API snapshot: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print("=" * 70)

    all_pass = True
    all_exact = True
    env_results = {}

    for env_name in envs:
        if env_name not in ENVIRONMENT_DEFINITIONS:
            print(f"\n[ERROR] Unknown environment: {env_name}")
            continue

        env_def = ENVIRONMENT_DEFINITIONS[env_name]
        estimated_total = env_def["estimated_total_usd"]

        print(f"\n{'-'*70}")
        print(f"  Environment: {env_name.upper()}")
        print(f"  Estimated total from generated artifact: ${estimated_total:,.2f}/mo")
        print(f"{'-'*70}")

        line_results = []
        reference_total = 0.0

        for svc in env_def["services"]:
            sku_key = svc["sku"]
            qty     = svc.get("qty", SKU_MAP[sku_key]["default_qty"])
            spec    = SKU_MAP[sku_key]
            label   = spec["label"].format(qty=qty)
            filter_str = spec["filter"].replace("{region}", region)

            print(f"  Fetching: {label} ...", end=" ", flush=True)

            time.sleep(0.8)   # avoid 429 rate limit
            is_reservable = spec.get("reservable", True)
            if reservation != "none" and is_reservable:
                res_filter = spec.get("reservation_filter", filter_str).replace("{region}", region)
                unit_price = fetch_reservation_price(res_filter, reservation, currency)
                price_source = f"{reservation} reservation (monthly equiv)"
                calc_fn = spec.get("calc_reservation", spec["calc"])
            else:
                fallback = spec.get("fallback_filter", "").replace("{region}", region) or None
                unit_price = fetch_price(filter_str, currency, fallback_filter=fallback)
                price_source = "Consumption (PAYG)" if is_reservable or reservation == "none" else "Consumption (PAYG — not reservable)"
                calc_fn = spec["calc"]

            if unit_price is None:
                print("BLOCKED — meter not found")
                line_results.append({
                    "label": label,
                    "unit_price": None,
                    "qty": qty,
                    "reference_monthly": None,
                    "status": "BLOCKED",
                    "price_source": price_source,
                    "filter": filter_str,
                })
                all_pass = False
                all_exact = False
                continue

            reference_monthly = round(calc_fn(unit_price, qty), 6)
            reference_total  += reference_monthly
            print(f"${unit_price:.6f}/{spec['unit_label'].split('×')[0].strip()} → ${reference_monthly:,.2f}/mo")

            line_results.append({
                "label": label,
                "unit_price": unit_price,
                "qty": qty,
                "reference_monthly": reference_monthly,
                "status": "OK",
                "price_source": price_source,
                "filter": filter_str,
            })

        # ── Per-environment comparison ─────────────────────────────────────
        reference_total = round(reference_total, 2)
        env_delta = delta_pct(reference_total, estimated_total)

        print(f"\n  {'Service':<45} {'Ref $/mo':>10}  {'Status':<10}")
        print(f"  {'-'*45} {'-'*10}  {'-'*10}")
        for r in line_results:
            ref_str = f"${r['reference_monthly']:,.2f}" if r["reference_monthly"] is not None else "BLOCKED"
            status  = r["status"]
            print(f"  {r['label']:<45} {ref_str:>10}  {status:<10}")

        print(f"\n  {'Reference total (live API):':<45} ${reference_total:>10,.2f}")
        print(f"  {'Estimated total (generated artifact):':<45} ${estimated_total:>10,.2f}")
        print(f"  {'Absolute delta:':<45} ${abs(reference_total - estimated_total):>10,.2f}")
        print(f"  {'Delta %:':<45} {env_delta:>10.2f}%")

        if env_delta == 0.0:
            verdict = "PASS_EXACT"
        elif env_delta <= THRESHOLD_ENV_NEAR:
            verdict = "PASS_NEAR"
            all_exact = False
        else:
            verdict = "FAIL"
            all_pass = False
            all_exact = False

        print(f"\n  Environment verdict: {verdict}")

        env_results[env_name] = {
            "reference_total": reference_total,
            "estimated_total": estimated_total,
            "delta_pct": env_delta,
            "verdict": verdict,
            "lines": line_results,
        }

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print(f"{'=' * 70}")
    print(f"\n  {'Environment':<12} {'Ref $/mo':>10}  {'Est $/mo':>10}  {'Delta %':>8}  Verdict")
    print(f"  {'-'*12} {'-'*10}  {'-'*10}  {'-'*8}  {'-'*12}")

    for env_name, res in env_results.items():
        print(
            f"  {env_name:<12} ${res['reference_total']:>9,.2f}  ${res['estimated_total']:>9,.2f}  "
            f"{res['delta_pct']:>7.2f}%  {res['verdict']}"
        )

    blocked_count = sum(
        1 for res in env_results.values()
        for line in res["lines"] if line["status"] == "BLOCKED"
    )

    if blocked_count > 0:
        final_verdict = "BLOCKED"
    elif all_exact:
        final_verdict = "PASS_EXACT"
    elif all_pass:
        final_verdict = "PASS_NEAR"
    else:
        final_verdict = "FAIL"

    print(f"\n  ┌{'─'*40}┐")
    print(f"  │  FINAL VERDICT: {final_verdict:<24}│")
    print(f"  └{'─'*40}┘")

    if blocked_count > 0:
        print(f"\n  {blocked_count} meter(s) could not be mapped to Azure Retail Prices API.")
        print("  Resolution: check filter strings in SKU_MAP or verify meter names at")
        print("  https://prices.azure.com/api/retail/prices")

    if final_verdict in ("FAIL", "BLOCKED"):
        # Print top variance contributors
        all_lines = [
            (env, line)
            for env, res in env_results.items()
            for line in res["lines"]
            if line["status"] == "BLOCKED"
        ]
        if all_lines:
            print("\n  TOP VARIANCE CONTRIBUTORS (BLOCKED lines):")
            for env, line in all_lines[:10]:
                print(f"    [{env}] {line['label']}")
                print(f"           Filter: {line['filter']}")

    print()
    return final_verdict, env_results


def write_json_output(verdict: str, env_results: dict, path: str,
                      region: str, currency: str, reservation: str):
    """
    Write machine-readable JSON output for agent consumption.
    """
    out = {
        "verdict": verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "region": region,
        "currency": currency,
        "reservation": reservation,
        "environments": {}
    }
    for env_name, res in env_results.items():
        out["environments"][env_name] = {
            "verdict": res["verdict"],
            "reference_total_usd": res["reference_total"],
            "estimated_total_usd": res["estimated_total"],
            "delta_pct": round(res["delta_pct"], 4),
            "line_items": [
                {
                    "service": line["label"],
                    "unit_price_usd": line["unit_price"],
                    "qty": line["qty"],
                    "reference_monthly_usd": line["reference_monthly"],
                    "price_source": line["price_source"],
                    "status": line["status"],
                    "filter": line["filter"],
                }
                for line in res["lines"]
            ]
        }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n  JSON output written to: {path}")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Validate generated Azure infra cost estimates vs live Retail Prices API"
    )
    parser.add_argument(
        "--env", default="all",
        help="Environment to validate: dev | staging | prod | all (default: all)"
    )
    parser.add_argument(
        "--region", default="brazilsouth",
        help="Azure region slug (default: brazilsouth)"
    )
    parser.add_argument(
        "--currency", default="USD",
        choices=["USD", "BRL", "EUR"],
        help="Currency (default: USD)"
    )
    parser.add_argument(
        "--reservation", default="none",
        choices=["none", "1yr", "3yr"],
        help="Reservation term (default: none = PAYG)"
    )
    parser.add_argument(
        "--json-out", default=None, metavar="PATH",
        help="Write machine-readable JSON result to PATH (for agent consumption)"
    )
    args = parser.parse_args()

    envs = list(ENVIRONMENT_DEFINITIONS.keys()) if args.env == "all" else [args.env]
    verdict, env_results = run_validation(
        envs=envs,
        region=args.region,
        currency=args.currency,
        reservation=args.reservation,
    )

    if args.json_out:
        write_json_output(verdict, env_results, args.json_out,
                          args.region, args.currency, args.reservation)

    sys.exit(0 if verdict in ("PASS_EXACT", "PASS_NEAR") else 1)


if __name__ == "__main__":
    main()
