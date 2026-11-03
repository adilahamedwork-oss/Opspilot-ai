from typing import Any, Literal
from pydantic import BaseModel, Field

class IncidentInput(BaseModel):
    service: str = Field(min_length=1, max_length=100)
    severity: Literal["low", "medium", "high", "critical"] = "high"
    description: str = Field(min_length=3, max_length=2000)
    logs: list[str] = Field(default_factory=list, max_length=100)
    metrics: dict[str, float] = Field(default_factory=dict)

class InvestigationResult(BaseModel):
    incident_id: str
    service: str
    severity: str
    summary: str
    probable_root_cause: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]
    remediation: list[str]
    provider: str
    mode: Literal["ai", "rules"]
    status: str = "investigated"
    raw_context: dict[str, Any] = Field(default_factory=dict)
