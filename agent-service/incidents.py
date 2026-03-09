from datetime import datetime
from docker_context import get_container_context
from llm_triage import triage_incident_with_llm
from remediation import execute_remediation
INCIDENTS = []
INCIDENT_COUNTER = 1

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def extract_service_name(labels: dict) -> str:
    return (
        labels.get("service")
        or labels.get("job")
        or labels.get("container")
        or labels.get("instance", "").split(":")[0]
        or "unknown"
    )

def find_open_incident_by_fingerprint(fingerprint: str):
    for incident in INCIDENTS:
        if (
            incident.get("fingerprint") == fingerprint
            and incident.get("incident_state") != "resolved"
        ):
            return incident
    return None

def create_or_update_incident(alert: dict):
    global INCIDENT_COUNTER

    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    fingerprint = alert.get("fingerprint") or f"{labels.get('alertname','unknown')}::{labels.get('instance','unknown')}"
    service_name = extract_service_name(labels)
    alert_status = alert.get("status", "unknown")
    existing = find_open_incident_by_fingerprint(fingerprint)

    if existing:
        existing["last_seen_at"] = now_iso()
        existing["status"] = alert_status
        existing["summary"] = annotations.get("summary", existing["summary"])
        existing["description"] = annotations.get("description", existing["description"])
        existing["docker_context"] = get_container_context(service_name)

        if alert_status == "resolved":
            existing["incident_state"] = "resolved"
            existing["resolved_at"] = now_iso()

        return existing, False

    docker_context = get_container_context(service_name)

    incident = {
        "id": INCIDENT_COUNTER,
        "fingerprint": fingerprint,
        "created_at": now_iso(),
        "last_seen_at": now_iso(),
        "resolved_at": None,
        "incident_state": "resolved" if alert_status == "resolved" else "open",
        "status": alert_status,
        "alert_name": labels.get("alertname", "unknown"),
        "service": service_name,
        "severity": labels.get("severity", "unknown"),
        "summary": annotations.get("summary", ""),
        "description": annotations.get("description", ""),
        "docker_context": docker_context,
        "raw_alert": alert,
        "approval_status": "pending",
        "action_status": "not_run",
        "action_result": None,
        "llm_triage": None,
    }

    llm_triage = triage_incident_with_llm(incident)
    incident["llm_triage"] = llm_triage
    INCIDENTS.append(incident)
    INCIDENT_COUNTER += 1
    print(f"[INCIDENT CREATED] {incident['alert_name']} for {incident['service']}")
    print(f"[LLM TRIAGE] {incident['llm_triage']}") 
    return incident, True


def get_all_incidents():
    return INCIDENTS

def get_incident_by_id(incident_id: int):
    for incident in INCIDENTS:
        if incident["id"] == incident_id:
            return incident
    return None

def approve_incident(incident_id: int, approver: str = "manual-user"):
    incident = get_incident_by_id(incident_id)
    if not incident:
        return None

    if incident["incident_state"] == "resolved":
        incident["approval_status"] = "rejected"
        incident["action_status"] = "not_run"
        incident["action_result"] = {
            "success": False,
            "timestamp": now_iso(),
            "message": "Incident is already resolved; no action executed"
        }
        return incident

    recommended_action = (incident.get("llm_triage") or {}).get("recommended_action", "investigate_manually")
    target_service = (incident.get("llm_triage") or {}).get("target_service") or incident["service"]

    if recommended_action != "restart_service":
        incident["approval_status"] = "approved"
        incident["action_status"] = "skipped"
        incident["action_result"] = {
            "success": False,
            "timestamp": now_iso(),
            "message": f"Recommended action was '{recommended_action}', so no restart was executed"
        }
        incident["approved_by"] = approver
        incident["approved_at"] = now_iso()
        return incident

    incident["approval_status"] = "approved"
    incident["approved_by"] = approver
    incident["approved_at"] = now_iso()

    result = execute_remediation("restart_service", target_service)
    incident["action_status"] = "completed" if result["success"] else "failed"
    incident["action_result"] = result

    return incident


def reject_incident(incident_id: int, approver: str = "manual-user"):
    incident = get_incident_by_id(incident_id)
    if not incident:
        return None

    incident["approval_status"] = "rejected"
    incident["action_status"] = "not_run"
    incident["action_result"] = {
        "success": False,
        "timestamp": now_iso(),
        "message": "Incident action was rejected by human reviewer"
    }
    incident["approved_by"] = approver
    incident["approved_at"] = now_iso()
    return incident