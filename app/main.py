from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, make_asgi_app

from app.config import settings
from app.schemas import IncidentInput
from app.investigator import investigate
from app.storage import init_db, save_incident, get_incidents, get_incident

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="AI-assisted incident investigation platform."
)

init_db()

REQUESTS = Counter(
    "opspilot_incident_requests_total",
    "Incident investigations",
    ["severity", "mode"]
)
LATENCY = Histogram(
    "opspilot_investigation_seconds",
    "Incident investigation duration"
)

app.mount("/metrics", make_asgi_app())
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open("app/static/index.html", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "opspilot-ai",
        "version": "0.2.0"
    }


@app.get("/incidents/demo/{scenario}")
async def demo_incident(scenario: str):
    examples = {
        "database": IncidentInput(
            service="checkout-api",
            severity="critical",
            description="Checkout requests failing after database latency spike",
            logs=[
                "ERROR database timeout after 30000ms",
                "WARN connection pool: too many connections"
            ],
            metrics={
                "cpu_percent": 72,
                "http_5xx_rate": 18.5,
                "db_connections": 250
            }
        ),
        "cpu": IncidentInput(
            service="catalog-api",
            severity="high",
            description="API latency increased and CPU saturation detected",
            logs=[
                "WARN request queue growing",
                "ERROR HTTP 500 on /products"
            ],
            metrics={
                "cpu_percent": 98,
                "http_5xx_rate": 12.0
            }
        ),
        "memory": IncidentInput(
            service="worker",
            severity="high",
            description="Worker restarted after memory limit exceeded",
            logs=["OOMKilled: container exceeded memory limit"],
            metrics={"memory_percent": 99}
        )
    }

    if scenario not in examples:
        raise HTTPException(
            status_code=404,
            detail="Unknown scenario. Choose database, cpu, or memory."
        )

    return await _run_investigation(examples[scenario])


@app.post("/incidents/investigate")
async def investigate_incident(incident: IncidentInput):
    return await _run_investigation(incident)


@app.get("/incidents/history")
async def incident_history(limit: int = Query(default=50, ge=1, le=200)):
    return {
        "count": len(get_incidents(limit)),
        "incidents": get_incidents(limit)
    }


@app.get("/incidents/history/{incident_id}")
async def incident_detail(incident_id: str):
    result = get_incident(incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


async def _run_investigation(incident: IncidentInput):
    with LATENCY.time():
        result = await investigate(incident)

    save_incident(result)

    REQUESTS.labels(
        severity=result["severity"],
        mode=result["mode"]
    ).inc()

    return result
