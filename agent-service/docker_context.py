import docker

client = docker.from_env()


def get_container_context(service_name: str, log_tail: int = 50):
    """
    Try to find the Docker container by name and return useful debugging context.
    """
    try:
        container = client.containers.get(service_name)
    except docker.errors.NotFound:
        return {
            "service_name": service_name,
            "container_found": False,
            "error": f"Container '{service_name}' not found"
        }
    except Exception as e:
        return {
            "service_name": service_name,
            "container_found": False,
            "error": str(e)
        }

    attrs = container.attrs
    state = attrs.get("State", {})
    health = state.get("Health", {})

    try:
        logs = container.logs(tail=log_tail).decode("utf-8", errors="replace").splitlines()
    except Exception as e:
        logs = [f"Failed to fetch logs: {str(e)}"]

    return {
        "service_name": service_name,
        "container_found": True,
        "container_id": container.short_id,
        "container_name": container.name,
        "image": attrs.get("Config", {}).get("Image"),
        "container_status": container.status,
        "running": state.get("Running"),
        "started_at": state.get("StartedAt"),
        "finished_at": state.get("FinishedAt"),
        "exit_code": state.get("ExitCode"),
        "health_status": health.get("Status", "unknown"),
        "restart_count": attrs.get("RestartCount", 0),
        "recent_logs": logs
    }