from fastapi.testclient import TestClient

import main
from abc_analysis import compute_abc


client = TestClient(main.app)


def test_health_contract():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "UNG-ORACLE",
        "version": main.VERSION,
        "read_only": True,
    }


def test_system_contract_is_read_only():
    response = client.get("/v1/system")
    assert response.status_code == 200
    payload = response.json()
    assert payload["system_id"] == "UNG-ORACLE"
    assert payload["mode"] == "read-only"
    assert "abc-inventory-classification" in payload["capabilities"]
    assert "cross-system-readiness" in payload["capabilities"]


def test_abc_analysis_rejects_zero_value_inventory():
    response = client.post(
        "/v1/abc/analyze",
        json={"items": [{"item_code": "SKU-1", "annual_usage_qty": 0, "unit_price": 10}]},
    )
    assert response.status_code == 422


def test_abc_analysis_returns_ranked_inventory():
    result = compute_abc([
        {"item_code": "A", "annual_usage_qty": 10, "unit_price": 10},
        {"item_code": "B", "annual_usage_qty": 5, "unit_price": 10},
        {"item_code": "C", "annual_usage_qty": 1, "unit_price": 10},
    ])
    assert result is not None
    assert result["total_annual_consumption_value"] == 160
    assert [item["item_code"] for item in result["items"]] == ["A", "B", "C"]
    assert set(result["summary_by_band"]) == {"A", "B", "C"}


def test_ready_contract_with_two_connected_upstreams(monkeypatch):
    monkeypatch.setattr(main.clients, "vector_health", lambda: True)
    monkeypatch.setattr(main.clients, "mercury_health", lambda: True)
    monkeypatch.setattr(main.clients, "nova_health", lambda: False)

    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_degrades_with_fewer_than_two_upstreams(monkeypatch):
    monkeypatch.setattr(main.clients, "vector_health", lambda: True)
    monkeypatch.setattr(main.clients, "mercury_health", lambda: False)
    monkeypatch.setattr(main.clients, "nova_health", lambda: False)

    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
