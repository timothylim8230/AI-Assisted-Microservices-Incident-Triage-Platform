import os
import json
import re
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_json(text: str) -> str:
    text = text.strip()

    # Remove ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    return text.strip()

def build_incident_prompt(incident: dict) -> str:
    docker_context = incident.get("docker_context", {})

    trimmed_logs = docker_context.get("recent_logs", [])[-20:]

    prompt = f"""
You are an incident triage assistant for Docker microservices.

Analyze the incident and return ONLY valid JSON with these fields:
- summary
- likely_cause
- recommended_action
- target_service
- confidence
- warning

Rules:
- recommended_action must be one of:
  - restart_service
  - investigate_manually
  - no_action
- target_service must be the affected service name
- confidence must be one of:
  - low
  - medium
  - high
- Keep answers concise and operationally realistic
- Do not invent missing facts
- If uncertain, prefer investigate_manually

Incident data:
{json.dumps({
    "alert_name": incident.get("alert_name"),
    "service": incident.get("service"),
    "severity": incident.get("severity"),
    "summary": incident.get("summary"),
    "description": incident.get("description"),
    "docker_context": {
        "container_status": docker_context.get("container_status"),
        "health_status": docker_context.get("health_status"),
        "restart_count": docker_context.get("restart_count"),
        "recent_logs": trimmed_logs
    }
}, indent=2)}
"""
    return prompt


def triage_incident_with_llm(incident: dict) -> dict:
    prompt = build_incident_prompt(incident)

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You are a careful DevOps incident triage assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        text = response.choices[0].message.content.strip()

        try:
            cleaned = extract_json(text)
            parsed = json.loads(cleaned)
            return parsed
        except Exception:
            return {
                "summary": "Failed to parse LLM response",
                "likely_cause": "Unknown",
                "recommended_action": "investigate_manually",
                "target_service": incident.get("service", "unknown"),
                "confidence": "low",
                "warning": f"Raw response was not valid JSON: {text}"
            }
    except Exception as e:
        return {
            "summary": "LLM triage unavailable",
            "likely_cause": "API Error",
            "recommended_action": "investigate_manually",
            "target_service": incident.get("service", "unknown"),
            "confidence": "low",
            "warning": f"OpenAI API error: {str(e)}"
        }