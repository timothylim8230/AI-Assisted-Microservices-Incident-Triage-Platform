import docker
from datetime import datetime

client = docker.from_env()

ALLOWED_SERVICES = {"service-b"}
ALLOWED_ACTIONS = {"restart_service"}


def execute_remediation(action: str, service_name: str) -> dict:
    if action not in ALLOWED_ACTIONS:
        return {
            "success": False,
            "action": action,
            "service": service_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": f"Action '{action}' is not allowed"
        }

    if service_name not in ALLOWED_SERVICES:
        return {
            "success": False,
            "action": action,
            "service": service_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": f"Service '{service_name}' is not in allowlist"
        }

    try:
        container = client.containers.get(service_name)

        if action == "restart_service":
            container.restart()

        return {
            "success": True,
            "action": action,
            "service": service_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": f"Successfully executed {action} on {service_name}"
        }

    except docker.errors.NotFound:
        return {
            "success": False,
            "action": action,
            "service": service_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": f"Container '{service_name}' not found"
        }
    except Exception as e:
        return {
            "success": False,
            "action": action,
            "service": service_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": str(e)
        }