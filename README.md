# OpsPilot AI

AI-assisted DevOps incident investigation MVP. Accepts incident evidence, correlates logs and metrics, and produces a probable cause plus suggested remediation. It does not execute infrastructure changes.

## Features
- FastAPI incident API and browser dashboard
- Controlled database, CPU and memory incident scenarios
- Gemini and OpenAI provider support
- Evidence-based local rules fallback for tests/offline use
- Prometheus metrics and Grafana service
- Pytest API tests

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add GEMINI_API_KEY to .env for real Gemini investigation
uvicorn app.main:app --reload
```
Open http://localhost:8000. API docs: http://localhost:8000/docs

## Run tests
```bash
pytest -q
```

## Run with Docker
```bash
cp .env.example .env
# Add an AI key to .env if desired
docker compose up --build -d
docker compose ps
```
- App: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin / opspilot-local-change-me)

Add Prometheus as a Grafana data source with URL `http://prometheus:9090`.

## AI configuration
Set `AI_PROVIDER=gemini` and `GEMINI_API_KEY=...`, or `AI_PROVIDER=openai` and `OPENAI_API_KEY=...`. API keys are read from `.env` and must never be committed. If no key is configured or the provider is unavailable, the application uses deterministic evidence-based rules and labels the result `mode=rules`; it never pretends this is an AI response.

## API
- `GET /health`
- `GET /incidents/demo/{database|cpu|memory}`
- `POST /incidents/investigate`
- `GET /metrics`

Example:
```bash
curl -s http://localhost:8000/incidents/demo/database | python3 -m json.tool
```

## Safety and limitations
- Demo scenarios are synthetic.
- AI output is advisory and can be wrong; validate evidence before acting.
- No remediation command is executed.
- This MVP does not yet ingest real AWS CloudWatch events, Kubernetes events, traces, or persistent incident history. Those are subsequent phases.
