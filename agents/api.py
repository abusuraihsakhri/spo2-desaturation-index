"""
FastAPI REST API Server for Spo2 Desaturation Index.
"""
from typing import Dict, Any, List, Annotated
from fastapi import FastAPI, HTTPException
from pydantic import Field
from spo2_odi import analyze_spo2_recording
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Spo2 Desaturation Index API",
    description="Experimental pulse oximetry analysis API and example supervisor",
    version="3.1.0",
)


class ChatRequest(BaseModel):
    query: str


class RecordingRequest(BaseModel):
    spo2_values: List[Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]] = Field(min_length=1, max_length=150000)
    sampling_interval_sec: float = Field(default=1.0, gt=0, allow_inf_nan=False)
    threshold_pct: float = Field(default=3.0, gt=0, le=100, allow_inf_nan=False)
    fio2: float | None = Field(default=None, gt=0, le=1, allow_inf_nan=False)


@app.post("/api/odi")
def api_odi(req: RecordingRequest):
    """Compute ODI, T90 and events without storing recording samples."""
    try:
        return analyze_spo2_recording(
            req.spo2_values, req.sampling_interval_sec, req.threshold_pct, req.fio2
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "spo2-desaturation-index", "domain": "Pulse oximetry", "version": "3.1.0"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "AVAILABLE"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
