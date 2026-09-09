import json
import os
import urllib.error
import urllib.request
from typing import Any

VECTOR_BASE_URL = os.getenv("VECTOR_BASE_URL", "https://ung-vector-production.up.railway.app").rstrip("/")
MERCURY_BASE_URL = os.getenv("MERCURY_BASE_URL", "https://ung-mercury-production.up.railway.app").rstrip("/")
NOVA_BASE_URL = os.getenv("NOVA_BASE_URL", "https://ung-nova-production.up.railway.app").rstrip("/")
VECTOR_TOKEN = os.getenv("ORACLE_VECTOR_SERVICE_TOKEN", "")
MERCURY_TOKEN = os.getenv("ORACLE_MERCURY_SERVICE_TOKEN", "")
NOVA_READ_PERMISSION = os.getenv("ORACLE_NOVA_READ_PERMISSION", "nova.datasets.read")
TIMEOUT = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "6"))


def _get(base: str, path: str, token: str = "", extra_headers: dict[str,str] | None = None) -> Any:
    headers = {"User-Agent": "UNG-ORACLE/1.2"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(base + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode() or "null")
    except Exception:
        return None


def vector_health():
    return _get(VECTOR_BASE_URL, "/health")


def vector_summary():
    return _get(VECTOR_BASE_URL, "/v1/summary", VECTOR_TOKEN)


def vector_inventory():
    return _get(VECTOR_BASE_URL, "/v1/inventory", VECTOR_TOKEN) or []


def vector_movements():
    return _get(VECTOR_BASE_URL, "/v1/movements", VECTOR_TOKEN) or []


def vector_abc_input():
    return _get(VECTOR_BASE_URL, "/v1/oracle/abc-input", VECTOR_TOKEN)


def mercury_health():
    return _get(MERCURY_BASE_URL, "/health")


def mercury_ready():
    return _get(MERCURY_BASE_URL, "/ready")


def nova_health():
    return _get(NOVA_BASE_URL, "/health")


def nova_supply_chain_kpis():
    return _get(NOVA_BASE_URL, "/v1/supply-chain/kpis", extra_headers={"X-UNG-Permissions": NOVA_READ_PERMISSION})
