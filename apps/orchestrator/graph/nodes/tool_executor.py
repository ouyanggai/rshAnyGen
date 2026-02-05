"""Tool Executor Node"""
import json
from apps.orchestrator.graph.state import AgentState
from apps.orchestrator.services.skill_registry import SkillsRegistryClient

def _normalize_tool_result(skill_id: str, raw: dict) -> str:
    payload = {
        "skill": skill_id,
        "status": raw.get("status", "success"),
        "data": raw.get("result") if isinstance(raw, dict) else raw,
        "error": raw.get("error") if isinstance(raw, dict) else None,
        "execution_time_ms": raw.get("execution_time_ms") if isinstance(raw, dict) else None,
        "executor": raw.get("executor") if isinstance(raw, dict) else None,
        "metadata": raw.get("metadata", {}) if isinstance(raw, dict) else {},
    }
    return json.dumps(payload, ensure_ascii=False)

async def tool_executor(state: AgentState):
    """Execute selected skill"""
    skill_id = state.get("selected_skill")
    params = state.get("skill_parameters", {})

    if not skill_id:
        return {"tool_results": None}

    client = SkillsRegistryClient()
    try:
        context = {
            "session_id": state.get("session_id"),
            "intent": state.get("intent"),
            "kb_ids": state.get("kb_ids", []),
            "user_message": state.get("user_message"),
        }
        result = await client.execute_skill(skill_id, params, context=context)
        normalized = _normalize_tool_result(skill_id, result or {})

        return {
            "tool_results": normalized,
            "citations": state.get("citations", [])
        }
    finally:
        await client.close()
