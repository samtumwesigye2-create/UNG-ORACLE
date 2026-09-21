from intelligence import build_intelligence_snapshot


def test_snapshot_flags_upstream_and_kpi_issues():
    result = build_intelligence_snapshot(
        vector_summary={"distinct_skus":0,"units_on_hand":0,"movements":0},
        abc={"status":"insufficient-data"},
        scorecard={"status":"ok","coverage_pct":40},
        upstreams={
            "vector":{"connected":True,"read_contract_ok":True},
            "mercury":{"connected":False},
            "nova":{"connected":True},
        },
    )
    codes={item["code"] for item in result["findings"]}
    assert result["status"]=="attention"
    assert "mercury_unavailable" in codes
    assert "kpi_coverage_low" in codes
    assert "no_inventory_skus" in codes


def test_snapshot_surfaces_a_class_opportunity():
    result = build_intelligence_snapshot(
        vector_summary={"distinct_skus":10,"units_on_hand":100,"movements":20},
        abc={"status":"ok","summary_by_band":{"A":{"pct_of_value":82}}},
        scorecard={"status":"ok","coverage_pct":100},
        upstreams={
            "vector":{"connected":True,"read_contract_ok":True},
            "mercury":{"connected":True},
            "nova":{"connected":True},
        },
    )
    codes={item["code"] for item in result["opportunities"]}
    assert result["status"]=="healthy"
    assert "protect_a_class_inventory" in codes
    assert "full_kpi_coverage" in codes
