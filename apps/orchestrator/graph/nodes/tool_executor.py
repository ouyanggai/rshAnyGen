"""Tool Executor Node"""
from apps.orchestrator.graph.state import AgentState
from apps.orchestrator.services.skill_registry import SkillsRegistryClient

async def tool_executor(state: AgentState):
    """Execute selected skill"""
    skill_id = state.get("selected_skill")
    params = state.get("skill_parameters", {})
    
    if not skill_id:
        return {"tool_results": None}

    client = SkillsRegistryClient()
    try:
        result = await client.execute_skill(skill_id, params)
        
        # Merge citations if any
        # result might look like: {"status": "success", "result": {...}, "metadata": ...}
        # We need to standardize how we store it in state
        
        return {
            "tool_results": result.get("result"),
            "citations": state.get("citations", []) # + extract citations from result
        }
    finally:
        await client.close()
