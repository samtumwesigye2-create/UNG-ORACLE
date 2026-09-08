from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from abc_analysis import compute_abc
import clients

app = FastAPI(title="UNG-ORACLE",version="1.1.0",description="Read-only cross-system logistics intelligence for MERCURY + VECTOR")

class ABCItem(BaseModel):
    item_code: str
    description: str = ""
    annual_usage_qty: float = Field(ge=0)
    unit_price: float = Field(ge=0)

class ABCRequest(BaseModel):
    items: list[ABCItem]

@app.get("/health")
def health(): return {"status":"ok","service":"UNG-ORACLE","version":"1.1.0","read_only":True}

@app.get("/ready")
def ready():
    vh=clients.vector_health(); mh=clients.mercury_health()
    return {"status":"ready" if vh or mh else "degraded","vector":"connected" if vh else "unavailable","mercury":"connected" if mh else "unavailable","read_only":True}

@app.get("/v1/system")
def system():
    return {"system_id":"UNG-ORACLE","domain":"cross-system-logistics-intelligence","mode":"read-only","capabilities":["abc-inventory-classification","vector-live-abc-feed","vector-observation","mercury-observation","annual-consumption-value-analysis","cross-system-readiness"]}

@app.post("/v1/abc/analyze")
def analyze_abc(body: ABCRequest):
    result=compute_abc([i.model_dump() for i in body.items])
    if result is None: raise HTTPException(422,"ABC analysis requires at least one item with positive annual consumption value")
    return result

def _vector_abc_items():
    feed=clients.vector_abc_input()
    if not feed:
        return [], {"inventory_records":0,"priced_records":0,"records_with_annual_usage":0,"missing_unit_price":[],"upstream":"unavailable"}
    prepared=[]
    for row in feed.get("items") or []:
        prepared.append({
            "item_code":row.get("item_code") or "",
            "description":row.get("description") or row.get("item_code") or "",
            "annual_usage_qty":float(row.get("annual_usage_qty") or 0),
            "unit_price":float(row.get("unit_price") or 0),
        })
    quality={
        "inventory_records":feed.get("inventory_records",len(prepared)),
        "priced_records":feed.get("priced_records",0),
        "records_with_annual_usage":feed.get("records_with_annual_usage",0),
        "missing_unit_price":feed.get("missing_price") or [],
        "generated_at":feed.get("generated_at"),
    }
    return prepared, quality

@app.get("/v1/abc/vector")
def abc_from_vector():
    items,quality=_vector_abc_items(); result=compute_abc(items)
    if result is None:
        return {"status":"insufficient-data","reason":"VECTOR has no inventory yet, or live SKU pricing/annual dispatch usage is not available","data_quality":quality,"items_prepared":items}
    return {"status":"ok","source":"UNG-VECTOR","data_quality":quality,**result}

@app.get("/v1/dashboard")
def dashboard_data():
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"read_only":True,"vector_health":clients.vector_health(),"mercury_health":clients.mercury_health(),"mercury_ready":clients.mercury_ready(),"vector_summary":clients.vector_summary(),"abc":abc_from_vector()}

@app.get("/",response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>UNG-ORACLE</title><style>body{margin:0;background:#0b1220;color:#e8eef8;font-family:system-ui,-apple-system,sans-serif}header{padding:20px;border-bottom:1px solid #25334b;background:#101a2c}main{max-width:1050px;margin:auto;padding:18px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.card{background:#111d31;border:1px solid #293a56;border-radius:16px;padding:16px}.metric{font-size:28px;font-weight:800}.muted{color:#92a4bf}.ok{color:#72e6a6}.warn{color:#ffc96b}pre{white-space:pre-wrap;overflow:auto}.tag{display:inline-block;padding:5px 9px;border-radius:999px;background:#1d2c44;margin-right:6px}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style></head><body><header><strong>UNG-ORACLE</strong><div class='muted'>Read-only logistics intelligence</div></header><main><div class='grid'><div class='card'><div class='muted'>VECTOR</div><div id='v' class='metric'>…</div></div><div class='card'><div class='muted'>MERCURY</div><div id='m' class='metric'>…</div></div><div class='card'><div class='muted'>Mode</div><div class='metric ok'>READ ONLY</div></div></div><div class='card' style='margin-top:12px'><h2>ABC Inventory Analysis</h2><div id='abc'>Loading…</div></div><div class='card' style='margin-top:12px'><h2>Live data</h2><pre id='raw'>Loading…</pre></div></main><script>fetch('/v1/dashboard').then(r=>r.json()).then(d=>{document.getElementById('v').textContent=d.vector_health?'ONLINE':'OFFLINE';document.getElementById('m').textContent=d.mercury_health?'ONLINE':'OFFLINE';let a=d.abc||{};document.getElementById('abc').innerHTML=a.status==='ok'?['A','B','C'].map(x=>`<span class='tag'>${x}: ${a.summary_by_band[x].item_count} items</span>`).join(''):`<span class='warn'>${a.reason||'Insufficient data'}</span>`;document.getElementById('raw').textContent=JSON.stringify(d,null,2)}).catch(e=>document.getElementById('raw').textContent=e.toString())</script></body></html>""")
