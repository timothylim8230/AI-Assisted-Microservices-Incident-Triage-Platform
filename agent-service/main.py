from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from incidents import (
    create_or_update_incident,
    get_all_incidents,
    get_incident_by_id,
    approve_incident,
    reject_incident,
)

app = FastAPI(title="Incident Agent Service")


class ApprovalRequest(BaseModel):
    approver: str = "manual-user"

@app.get("/")
def root():
    return {"message": "Incident agent is running"}


@app.post("/alerts/webhook")
async def alertmanager_webhook(request: Request):
    payload = await request.json()
    alerts = payload.get("alerts", [])

    processed = []
    for alert in alerts:
        incident, created = create_or_update_incident(alert)
        processed.append({
            "id": incident["id"],
            "alert_name": incident["alert_name"],
            "service": incident["service"],
            "status": incident["status"],
            "incident_state": incident["incident_state"],
            "created_new": created,
        })

    return {
        "status": "received",
        "alerts_received": len(alerts),
        "processed": processed
    }


@app.get("/incidents")
def list_incidents():
    return get_all_incidents()


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: int):
    incident = get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
    
@app.post("/incidents/{incident_id}/approve")
def approve(incident_id: int, body: ApprovalRequest):
    incident = approve_incident(incident_id, body.approver)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@app.post("/incidents/{incident_id}/reject")
def reject(incident_id: int, body: ApprovalRequest):
    incident = reject_incident(incident_id, body.approver)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident