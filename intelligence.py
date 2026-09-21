from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_intelligence_snapshot(
    *,
    vector_summary: dict | None,
    abc: dict | None,
    scorecard: dict | None,
    upstreams: dict | None,
) -> dict:
    findings: list[dict[str, Any]] = []
    opportunities: list[dict[str, Any]] = []

    upstreams = upstreams or {}
    vector = upstreams.get("vector") or {}
    mercury = upstreams.get("mercury") or {}
    nova = upstreams.get("nova") or {}

    if not vector.get("connected"):
        findings.append({"severity":"critical","code":"vector_unavailable","message":"UNG-VECTOR is unavailable to ORACLE."})
    elif not vector.get("read_contract_ok"):
        findings.append({"severity":"warning","code":"vector_contract_mismatch","message":"UNG-VECTOR is reachable but its read contract is not verified."})

    if not mercury.get("connected"):
        findings.append({"severity":"warning","code":"mercury_unavailable","message":"UNG-MERCURY is unavailable to ORACLE."})
    if not nova.get("connected"):
        findings.append({"severity":"warning","code":"nova_unavailable","message":"UNG-NOVA is unavailable to ORACLE."})

    summary = vector_summary or {}
    units_on_hand = summary.get("units_on_hand")
    movements = summary.get("movements")
    distinct_skus = summary.get("distinct_skus")
    if isinstance(distinct_skus, (int, float)) and distinct_skus == 0:
        findings.append({"severity":"warning","code":"no_inventory_skus","message":"VECTOR currently reports no distinct inventory SKUs."})
    if isinstance(units_on_hand, (int, float)) and units_on_hand == 0:
        findings.append({"severity":"warning","code":"no_units_on_hand","message":"VECTOR currently reports zero units on hand."})
    if isinstance(movements, (int, float)) and movements == 0:
        findings.append({"severity":"info","code":"no_inventory_movements","message":"VECTOR currently reports no inventory movements."})

    abc = abc or {}
    if abc.get("status") == "ok":
        bands = abc.get("summary_by_band") or {}
        a_band = bands.get("A") or {}
        a_value_share = a_band.get("pct_of_value")
        if isinstance(a_value_share, (int, float)) and a_value_share >= 70:
            opportunities.append({
                "code":"protect_a_class_inventory",
                "message":"A-class inventory carries most annual consumption value; prioritize service levels, cycle counts, and supplier continuity for these items.",
                "evidence":{"a_class_value_share_pct":a_value_share},
            })
    else:
        findings.append({
            "severity":"info",
            "code":"abc_data_incomplete",
            "message":"ABC inventory intelligence is incomplete because VECTOR pricing or annual usage data is insufficient.",
        })

    scorecard = scorecard or {}
    coverage = scorecard.get("coverage_pct")
    if isinstance(coverage, (int, float)):
        if coverage < 50:
            findings.append({"severity":"warning","code":"kpi_coverage_low","message":"Less than half of the 21 supply-chain KPIs currently have live values.","evidence":{"coverage_pct":coverage}})
        elif coverage < 100:
            findings.append({"severity":"info","code":"kpi_coverage_partial","message":"The supply-chain KPI scorecard is partially populated.","evidence":{"coverage_pct":coverage}})
        else:
            opportunities.append({"code":"full_kpi_coverage","message":"All 21 supply-chain KPIs are populated and available for executive analysis."})
    elif scorecard.get("status") == "upstream-unavailable":
        findings.append({"severity":"warning","code":"kpi_upstream_unavailable","message":"NOVA KPI data is unavailable."})

    severity_order = {"critical":0,"warning":1,"info":2}
    findings.sort(key=lambda item: severity_order.get(item.get("severity","info"), 9))

    return {
        "status":"attention" if any(item["severity"] in {"critical","warning"} for item in findings) else "healthy",
        "read_only":True,
        "finding_count":len(findings),
        "opportunity_count":len(opportunities),
        "findings":findings,
        "opportunities":opportunities,
        "generated_at":datetime.now(timezone.utc).isoformat(),
    }
