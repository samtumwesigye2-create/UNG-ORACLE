"""ABC inventory classification for UNG-ORACLE.

Rule-based, not ML. Items are ranked by annual consumption value and assigned
A/B/C bands from cumulative value share. Defaults: A <=80%, B <=95%, C >95%.
"""
from typing import Optional

BAND_A_CUTOFF = 80.0
BAND_B_CUTOFF = 95.0


def _band_for(cumulative_pct: float) -> str:
    if cumulative_pct <= BAND_A_CUTOFF:
        return "A"
    if cumulative_pct <= BAND_B_CUTOFF:
        return "B"
    return "C"


def compute_abc(items: list[dict]) -> Optional[dict]:
    if not items:
        return None

    enriched = []
    for item in items:
        qty = item.get("annual_usage_qty") or 0
        price = item.get("unit_price") or 0
        value = qty * price
        enriched.append({**item, "annual_consumption_value": value})

    total_value = sum(i["annual_consumption_value"] for i in enriched)
    if total_value <= 0:
        return None

    enriched.sort(key=lambda i: i["annual_consumption_value"], reverse=True)
    cumulative_value = 0.0
    results = []
    for item in enriched:
        cumulative_value += item["annual_consumption_value"]
        pct_of_value = item["annual_consumption_value"] / total_value * 100
        cumulative_pct = cumulative_value / total_value * 100
        results.append({
            **item,
            "pct_of_total_value": round(pct_of_value, 1),
            "cumulative_pct_of_value": round(cumulative_pct, 1),
            "abc_category": _band_for(cumulative_pct),
        })

    total_items = len(results)
    summary_by_band = {}
    for band in ("A", "B", "C"):
        band_items = [r for r in results if r["abc_category"] == band]
        band_value = sum(r["annual_consumption_value"] for r in band_items)
        summary_by_band[band] = {
            "item_count": len(band_items),
            "pct_of_items": round(len(band_items) / total_items * 100, 1),
            "value": round(band_value, 2),
            "pct_of_value": round(band_value / total_value * 100, 1),
        }

    return {
        "total_items": total_items,
        "total_annual_consumption_value": round(total_value, 2),
        "summary_by_band": summary_by_band,
        "items": results,
    }
