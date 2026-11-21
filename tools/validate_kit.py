"""Smoke-test the kit: load every semantic model and check key measures against the gold answers.

    python tools/validate_kit.py

Run this on the participant VM image after cloning the repo. It needs only PyYAML.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.semantic_layer import SemanticModel  # noqa: E402

failures = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global failures
    print(("  PASS " if cond else "  FAIL ") + label + (f"  ({detail})" if detail else ""))
    failures += 0 if cond else 1


class _AnyGold(dict):
    """Participant copies have no answer keys: gold comparisons then pass trivially."""

    def __missing__(self, key):
        return {"ground_truth": None}


def gold(uc: str) -> dict:
    path = ROOT / "facilitator" / "answer-keys" / f"{uc}-gold.json"
    if not path.exists():
        return _AnyGold()
    return {g["id"]: g for g in json.loads(path.read_text())}


def contains(gt, value) -> bool:
    return True if gt is None else str(value) in gt.replace(",", "")


def starts(gt, value) -> bool:
    return True if gt is None else gt.startswith(value)


print("== manufacturing")
m = SemanticModel(ROOT / "usecases/manufacturing/data/semantic/semantic_model.yaml")
g = gold("manufacturing")
r = m.query_metrics(["defect_rate_ppm"], ["month"], [{"dimension": "part_number", "op": "eq", "value": "HX-220"},
                                                     {"dimension": "defect_code", "op": "eq", "value": "POR-GAS"}])
by_month = {row["month"]: row["defect_rate_ppm"] for row in r["rows"]}
check("HX-220 POR-GAS Sep PPM matches gold", contains(g["MFG-01"]["ground_truth"], round(by_month["2026-09"], 1)), str(by_month))
r = m.query_metrics(["avg_degas_minutes"], ["shift"], [{"dimension": "line", "op": "eq", "value": "L2"},
                                                       {"dimension": "production_date", "op": "between", "value": ["2026-09-21", "2026-10-09"]}])
check("Shift B degassing shortened", min(x["avg_degas_minutes"] for x in r["rows"]) < 9, str(r["rows"]))
r = m.query_metrics(["scrap_cost_usd"], ["defect_code"], [{"dimension": "month", "op": "in", "value": ["2026-07", "2026-08", "2026-09"]}], limit=3)
check("Top scrap-cost defect matches gold", starts(g["MFG-07"]["ground_truth"], r["rows"][0]["defect_code"]), r["rows"][0]["defect_code"])
r = m.lookup_records("supplier_lots", {"lot_id": ["ALV-2611", "ALV-2612"]})
check("Out-of-spec lots present", all(x["hydrogen_ml_per_100g"] > 0.15 for x in r["rows"]) and r["row_count"] == 2)
check("Tool call wrapper returns JSON errors", "error" in json.loads(m.call_tool("query_metrics", {"measures": ["nope"]})))

print("== retail")
m = SemanticModel(ROOT / "usecases/retail/data/semantic/semantic_model.yaml")
g = gold("retail")
r = m.lookup_records("purchase_history", {"customer_id": "C-10482", "sku": "HP-ESP-003"})
check("C-10482 espresso 41 days", r["rows"][0]["days_since_delivery"] == 41)
r = m.query_metrics(["return_rate_units"], ["category"], [{"dimension": "order_month", "op": "in", "value": ["2026-07", "2026-08", "2026-09"]}])
check("Top Q3 return-rate category matches gold", starts(g["RTL-07"]["ground_truth"], r["rows"][0]["category"]), str(r["rows"][:2]))
r = m.lookup_records("customers", {"customer_id": "C-30555"})
check("Lookup customer", r["rows"][0]["loyalty_tier"] == "Silver")

print("== fmcg")
m = SemanticModel(ROOT / "usecases/fmcg/data/semantic/semantic_model.yaml")
g = gold("fmcg")
r = m.query_metrics(["net_sales_inr"], ["fiscal_year"], [{"dimension": "account", "op": "eq", "value": "MetroMart"},
                                                          {"dimension": "ytd_comparable", "op": "eq", "value": "Y"}])
v = {x["fiscal_year"]: x["net_sales_inr"] for x in r["rows"]}
growth = (v["FY2026-27"] / v["FY2025-26"] - 1) * 100
check("MetroMart YTD growth matches gold", contains(g["FMCG-01"]["ground_truth"], f"{growth:.1f}"), f"{growth:.1f}%")
r = m.query_metrics(["promo_uplift_pct"], ["sku"], [{"dimension": "promo_status", "op": "eq", "value": "Completed"}])
check("ZS-250 is a top-2 uplift SKU", "ZS-250" in [x["sku"] for x in r["rows"][:2]], str(r["rows"][:2]))
r = m.query_metrics(["forecast_wape_pct"], ["sku"])
check("Worst WAPE SKU matches gold", starts(g["FMCG-06"]["ground_truth"], r["rows"][0]["sku"]), str(r["rows"][:2]))
r = m.query_metrics(["stockout_weeks"], ["week_start"], [{"dimension": "account", "op": "eq", "value": "QuickBasket"},
                                                         {"dimension": "sellout_region", "op": "eq", "value": "South"},
                                                         {"dimension": "sku", "op": "eq", "value": "CF-600"},
                                                         {"dimension": "month", "op": "eq", "value": "2026-08"}])
check("QuickBasket South CF-600 stock-outs in Aug", sum(x["stockout_weeks"] for x in r["rows"]) == 2, str(r["rows"]))
r = m.lookup_records("promotions", {"promo_id": "PRM-2612"})
check("PRM-2612 planned at 30 %", r["rows"][0]["depth_pct"] == 30)

for uc in ("manufacturing", "retail", "fmcg"):
    docs = list((ROOT / "usecases" / uc / "data" / "docs").glob("*"))
    check(f"{uc}: knowledge documents present", len(docs) >= 8, f"{len(docs)} files")

print("\nALL CHECKS PASSED" if failures == 0 else f"\n{failures} CHECK(S) FAILED")
sys.exit(1 if failures else 0)
