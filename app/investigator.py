from uuid import uuid4
from app.schemas import IncidentInput
from app.ai.provider import investigate_with_ai

def build_context(incident: IncidentInput) -> dict:
    return {
        "service": incident.service,
        "severity": incident.severity,
        "description": incident.description,
        "logs": incident.logs,
        "metrics": incident.metrics,
    }

def rule_based_result(context: dict) -> dict:
    logs = " ".join(context["logs"]).lower()
    metrics = context["metrics"]
    evidence = [f"Incident description: {context['description']}"]
    evidence.extend(f"Log evidence: {line}" for line in context["logs"][:8])
    evidence.extend(f"Metric observed: {key}={value}" for key, value in metrics.items())
    cause = "Insufficient evidence to identify a specific root cause. Collect application logs, dependency health and recent deployment events."
    fixes = ["Check service health and recent deployment/configuration changes.",
             "Review application and dependency logs around the incident timestamp.",
             "Apply a reversible change only after an engineer validates the evidence."]
    confidence = 0.25
    if any(x in logs for x in ["database timeout", "connection pool", "too many connections"]):
        cause = "Database connectivity or connection-pool exhaustion is a plausible cause."
        fixes = ["Check database availability and connection limits.",
                 "Inspect connection-pool settings and slow queries.",
                 "If correlated with a recent release, consider a human-approved rollback."]
        confidence = 0.78
    elif any(x in logs for x in ["out of memory", "oomkilled", "memory limit"]):
        cause = "Memory pressure or an out-of-memory condition is a plausible cause."
        fixes = ["Inspect memory usage and container limits.",
                 "Capture a heap/profile snapshot if safe.",
                 "Consider a controlled restart only after preserving diagnostic evidence."]
        confidence = 0.78
    elif any(x in logs for x in ["http 500", "internal server error"]) or metrics.get("http_5xx_rate", 0) > 0:
        cause = "Application errors are occurring; inspect the failing request path and recent code/configuration changes."
        fixes = ["Group 5xx errors by endpoint and correlate with application logs.",
                 "Check the latest deployment and dependency health.",
                 "Use a human-approved rollback if the incident began immediately after a release."]
        confidence = 0.65
    if metrics.get("cpu_percent", 0) >= 90:
        evidence.append("CPU utilization is at or above 90%.")
        if confidence < 0.7:
            cause = "High CPU utilization is a likely contributor; correlate hot processes with request volume and recent changes."
            confidence = 0.68
        fixes.insert(0, "Identify CPU-intensive processes and inspect traffic/request-rate changes.")
    return {"summary": f"{context['severity'].upper()} incident affecting {context['service']}.",
            "probable_root_cause": cause, "confidence": confidence,
            "evidence": evidence, "remediation": fixes}

async def investigate(incident: IncidentInput) -> dict:
    context = build_context(incident)
    ai_result, provider = await investigate_with_ai(context)
    if ai_result:
        result, mode = ai_result, "ai"
        required = {"summary", "probable_root_cause", "confidence", "evidence", "remediation"}
        if not required.issubset(result):
            result, mode, provider = rule_based_result(context), "rules", "rules"
    else:
        result, mode = rule_based_result(context), "rules"
        if provider not in ("gemini", "openai"):
            provider = "rules"
    return {
        "incident_id": str(uuid4()),
        "service": incident.service,
        "severity": incident.severity,
        **result,
        "provider": provider,
        "mode": mode,
        "status": "investigated",
        "raw_context": context,
    }
