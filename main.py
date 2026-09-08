from collections import defaultdict
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from abc_analysis import compute_abc
import clients

app = FastAPI(
    title="UNG-ORACLE",
    version="1.0.0",
    description="Read-only cross-system logistics intelligence for MERCURY + VECTOR",
)


class ABCItem(BaseModel):
    item_code: str
    description: str = ""
    annual_usage_qty: float = Field(ge=0)
    unit_price: float = Field(ge=0)


class ABCRequest(BaseModel):
    items: list[ABCItem]


@app.get("/health")
def health():
    return {"status": "ok", "service": "UNG-ORACLE", "version": "1.0.0", "read_only": True}


@app.get("/ready")
def ready():
    vh = clients.vector_health()
    mh = clients.mercury_health()
    return {
        "status": "ready" if vh or mh else "degraded",
        "vector": "connected" if vh else "unavailable",
        "mercury": "connected" if mh else "unavailable",
        "read_only": True,
    }


@app.get("/v1/system")
def system():
    return {
        "system_id": "UNG-ORACLE",
        "domain": "cross-system-logistics-intelligence",
        "mode": "read-only",
        "capabilities": [
            "abc-inventory-classification",
            "vector-observation",
            "mercury-observation",
            "annual-consumption-value-analysis",
            "cross-system-readiness",
        ],
    }


@app.post("/v1/abc/analyze")
def analyze_abc(body: ABCRequest):
    result = compute_abc([i.model_dump() for i in body.items])
    if result is None:
        raise HTTPException(422, "ABC analysis requires at least one item with positive annual consumption value")
    return result


def _vector_abc_items():
    inventory = clients.vector_inventory()
    movements = clients.vector_movements()
    if not inventory:
        return [], {"inventory_records": 0, "movement_records": len(movements), "missing_unit_price": []}

    annual_usage = defaultdict(float)
    for movement in movements:
        if movement.get("movement_type") == "dispatch":
            annual_usage[str(movement.get("sku"))] += float(movement.get("quantity") or 0)

    grouped = {}
    missing_price = []
    for row in inventory:
        sku = str(row.get("sku") or "")
        if not sku:
            continue
        current = grouped.setdefault(sku, {
            "item_code": sku,
            "description": row.get("description") or sku,
            "annual_usage_qty": annual_usage.get(sku, 0.0),
            "unit_price": row.get("unit_price"),
        })
        if row.get("description") and current["description"] == sku:
            current["description"] = row["description"]

    items = []
    for sku, item in grouped.items():
        if item.get("unit_price") is None:
            missing_price.append(sku)
            item["unit_price"] = 0
        items.append(item)
    return items, {
        "inventory_records": len(inventory),
        "movement_records": len(movements),
        "missing_unit_price": missing_price,
    }


@app.get("/v1/abc/vector")
def abc_from_vector():
    items, quality = _vector_abc_items()
    result = compute_abc(items)
    if result is None:
        return {
            "status": "insufficient-data",
            "reason": "VECTOR currently lacks positive unit_price and/or annual dispatch usage needed for annual consumption value",
            "data_quality": quality,
            "items_prepared": items,
        }
    return {"status": "ok", "source": "UNG-VECTOR", "data_quality": quality, **result}


@app.get("/v1/dashboard")
def dashboard_data():
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "vector_health": clients.vector_health(),
        "mercury_health": clients.mercury_health(),
        "mercury_ready": clients.mercury_ready(),
        "vector_summary": clients.vector_summary(),
        "abc": abc_from_vector(),
    }


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>UNG-ORACLE</title><style>body{margin:0;background:#0b1220;color:#e8eef8;font-family:system-ui,-apple-system,sans-serif}header{padding:20px;border-bottom:1px solid #25334b;background:#101a2c}main{max-width:1050px;margin:auto;padding:18px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.card{background:#111d31;border:1px solid #293a56;border-radius:16px;padding:16px}.metric{font-size:28px;font-weight:800}.muted{color:#92a4bf}.ok{color:#72e6a6}.warn{color:#ffc96b}pre{white-space:pre-wrap;overflow:auto}.tag{display:inline-block;padding:5px 9px;border-radius:999px;background:#1d2c44;margin-right:6px}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style></head><body><header><strong>UNG-ORACLE</strong><div class='muted'>Read-only logistics intelligence</div></header><main><div class='grid'><div class='card'><div class='muted'>VECTOR</div><div id='v' class='metric'>…</div></div><div class='card'><div class='muted'>MERCURY</div><div id='m' class='metric'>…</div></div><div class='card'><div class='muted'>Mode</div><div class='metric ok'>READ ONLY</div></div></div><div class='card' style='margin-top:12px'><h2>ABC Inventory Analysis</h2><div id='abc'>Loading…</div></div><div class='card' style='margin-top:12px'><h2>Live data</h2><pre id='raw'>Loading…</pre></div></main><script>fetch('/v1/dashboard').then(r=>r.json()).then(d=>{document.getElementById('v').textContent=d.vector_health?'ONLINE':'OFFLINE';document.getElementById('m').textContent=d.mercury_health?'ONLINE':'OFFLINE';let a=d.abc||{};document.getElementById('abc').innerHTML=a.status==='ok'?['A','B','C'].map(x=>`<span class='tag'>${x}: ${a.summary_by_band[x].item_count} items</span>`).join(''):`<span class='warn'>${a.reason||'Insufficient data'}</span>`;document.getElementById('raw').textContent=JSON.stringify(d,null,2)}).catch(e=>document.getElementById('raw').textContent=e.toString())</script></body></html>""")
