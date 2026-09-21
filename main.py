from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from abc_analysis import compute_abc
from intelligence import build_intelligence_snapshot
import clients

VERSION="1.4.0"
app = FastAPI(title="UNG-ORACLE",version=VERSION,description="Read-only cross-system logistics and supply-chain intelligence")

class ABCItem(BaseModel):
    item_code: str
    description: str = ""
    annual_usage_qty: float = Field(ge=0)
    unit_price: float = Field(ge=0)

class ABCRequest(BaseModel):
    items: list[ABCItem]

@app.get("/health")
def health(): return {"status":"ok","service":"UNG-ORACLE","version":VERSION,"read_only":True}

@app.get("/ready")
def ready():
    vh=clients.vector_health(); mh=clients.mercury_health(); nh=clients.nova_health()
    connected=sum(bool(x) for x in (vh,mh,nh))
    return {"status":"ready" if connected>=2 else "degraded","vector":"connected" if vh else "unavailable","mercury":"connected" if mh else "unavailable","nova":"connected" if nh else "unavailable","read_only":True}

@app.get("/v1/system")
def system():
    return {"system_id":"UNG-ORACLE","domain":"cross-system-logistics-intelligence","mode":"read-only","version":VERSION,"capabilities":["abc-inventory-classification","vector-live-abc-feed","vector-observation","mercury-observation","annual-consumption-value-analysis","nova-21-kpi-scorecard","supply-chain-executive-intelligence","cross-system-readiness","vector-read-contract-verification","cross-system-intelligence-findings","executive-opportunity-signals"]}

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
        prepared.append({"item_code":row.get("item_code") or "","description":row.get("description") or row.get("item_code") or "","annual_usage_qty":float(row.get("annual_usage_qty") or 0),"unit_price":float(row.get("unit_price") or 0)})
    quality={"inventory_records":feed.get("inventory_records",len(prepared)),"priced_records":feed.get("priced_records",0),"records_with_annual_usage":feed.get("records_with_annual_usage",0),"missing_unit_price":feed.get("missing_price") or [],"generated_at":feed.get("generated_at")}
    return prepared, quality

@app.get("/v1/abc/vector")
def abc_from_vector():
    items,quality=_vector_abc_items(); result=compute_abc(items)
    if result is None:
        return {"status":"insufficient-data","reason":"VECTOR has no inventory yet, or live SKU pricing/annual dispatch usage is not available","data_quality":quality,"items_prepared":items}
    return {"status":"ok","source":"UNG-VECTOR","data_quality":quality,**result}

@app.get("/v1/scorecard")
def executive_scorecard():
    feed=clients.nova_supply_chain_kpis()
    if not feed:
        return {"status":"upstream-unavailable","source":"UNG-NOVA","total":21,"available":0,"awaiting":21,"kpis":[],"generated_at":datetime.now(timezone.utc).isoformat()}
    kpis=feed.get("kpis") or []
    available=sum(1 for k in kpis if k.get("status")=="available" and k.get("value") is not None)
    awaiting=max(0,21-available)
    groups={"fulfillment":[],"planning":[],"supplier":[],"inventory":[],"finance":[],"resilience":[]}
    for k in kpis:
        n=int(k.get("number") or 0)
        target="fulfillment" if n in (1,2,3,16,21) else "planning" if n in (4,5,6) else "supplier" if n in (7,8,9,19) else "inventory" if n in (10,11,12,13,17) else "finance" if n in (14,15) else "resilience"
        groups[target].append(k)
    return {"status":"ok","source":"UNG-NOVA","total":21,"available":available,"awaiting":awaiting,"coverage_pct":round(100*available/21,1),"groups":groups,"kpis":kpis,"generated_at":feed.get("generated_at") or datetime.now(timezone.utc).isoformat()}

@app.get("/v1/upstreams")
def upstreams():
    vector_system=clients.vector_system()
    return {
        "read_only":True,
        "vector":{
            "connected":bool(clients.vector_health()),
            "system":vector_system,
            "read_contract_ok":bool(
                vector_system
                and vector_system.get("system_id")=="UNG-VECTOR"
                and vector_system.get("domain")=="warehouse-logistics"
            ),
        },
        "mercury":{"connected":bool(clients.mercury_health()),"ready":clients.mercury_ready()},
        "nova":{"connected":bool(clients.nova_health())},
        "checked_at":datetime.now(timezone.utc).isoformat(),
    }

@app.get("/v1/intelligence")
def intelligence():
    upstream_state=upstreams()
    vector_summary=clients.vector_summary()
    abc=abc_from_vector()
    scorecard=executive_scorecard()
    return build_intelligence_snapshot(
        vector_summary=vector_summary,
        abc=abc,
        scorecard=scorecard,
        upstreams=upstream_state,
    )

@app.get("/v1/dashboard")
def dashboard_data():
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"read_only":True,"vector_health":clients.vector_health(),"vector_system":clients.vector_system(),"mercury_health":clients.mercury_health(),"nova_health":clients.nova_health(),"mercury_ready":clients.mercury_ready(),"vector_summary":clients.vector_summary(),"abc":abc_from_vector(),"scorecard":executive_scorecard(),"intelligence":intelligence()}

@app.get("/",response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>UNG-ORACLE</title><style>body{margin:0;background:#0b1220;color:#e8eef8;font-family:system-ui,-apple-system,sans-serif}header{padding:20px;border-bottom:1px solid #25334b;background:#101a2c}main{max-width:1180px;margin:auto;padding:18px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.kgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.card{background:#111d31;border:1px solid #293a56;border-radius:16px;padding:16px}.kpi{background:#0e192a;border:1px solid #253750;border-radius:12px;padding:13px}.metric{font-size:28px;font-weight:800}.value{font-size:22px;font-weight:800;margin-top:6px}.muted{color:#92a4bf}.ok{color:#72e6a6}.warn{color:#ffc96b}.off{color:#ff8d97}.tag{display:inline-block;padding:5px 9px;border-radius:999px;background:#1d2c44;margin-right:6px}.bar{height:8px;background:#22324a;border-radius:6px;overflow:hidden;margin-top:8px}.fill{height:100%;background:#72e6a6}h2{margin-bottom:10px}small{color:#92a4bf}@media(max-width:850px){.grid{grid-template-columns:repeat(2,1fr)}.kgrid{grid-template-columns:1fr}}@media(max-width:520px){.grid{grid-template-columns:1fr}}</style></head><body><header><strong>UNG-ORACLE</strong><div class='muted'>Read-only enterprise supply-chain intelligence</div></header><main><div class='grid'><div class='card'><div class='muted'>VECTOR</div><div id='v' class='metric'>…</div></div><div class='card'><div class='muted'>MERCURY</div><div id='m' class='metric'>…</div></div><div class='card'><div class='muted'>NOVA</div><div id='n' class='metric'>…</div></div><div class='card'><div class='muted'>Mode</div><div class='metric ok'>READ ONLY</div></div></div><div class='card' style='margin-top:12px'><h2>21-KPI Supply Chain Scorecard</h2><div><span id='coverage' class='metric'>…</span> <span class='muted'>live KPI coverage</span></div><div class='bar'><div id='fill' class='fill' style='width:0%'></div></div><div id='kpis' class='kgrid' style='margin-top:14px'></div></div><div class='card' style='margin-top:12px'><h2>ABC Inventory Analysis</h2><div id='abc'>Loading…</div></div></main><script>function health(el,x){let e=document.getElementById(el);e.textContent=x?'ONLINE':'OFFLINE';e.className='metric '+(x?'ok':'off')}function fmt(k){if(k.value===null||k.value===undefined)return 'Awaiting data';let v=Number(k.value);let u=k.unit||'';if(u==='percent')return v.toFixed(1)+'%';if(u==='days')return v.toFixed(1)+' days';if(u==='minutes')return v.toFixed(1)+' min';if(u==='currency'||u==='currency/order')return '$'+v.toFixed(2);return v.toFixed(3)+' '+u}fetch('/v1/dashboard').then(r=>r.json()).then(d=>{health('v',d.vector_health);health('m',d.mercury_health);health('n',d.nova_health);let s=d.scorecard||{};document.getElementById('coverage').textContent=(s.coverage_pct||0)+'%';document.getElementById('fill').style.width=(s.coverage_pct||0)+'%';document.getElementById('kpis').innerHTML=(s.kpis||[]).map(k=>`<div class='kpi'><small>#${k.number} · ${k.source||'AWAITING SOURCE'}</small><div><strong>${k.name}</strong></div><div class='value ${k.status==='available'?'ok':'warn'}'>${fmt(k)}</div></div>`).join('')||'<span class="warn">NOVA scorecard unavailable</span>';let a=d.abc||{};document.getElementById('abc').innerHTML=a.status==='ok'?['A','B','C'].map(x=>`<span class='tag'>${x}: ${a.summary_by_band[x].item_count} items</span>`).join(''):`<span class='warn'>${a.reason||'Insufficient data'}</span>`}).catch(e=>{document.getElementById('kpis').innerHTML='<span class="off">'+e.toString()+'</span>'})</script></body></html>""")
