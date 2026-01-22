"""Entry Router Node"""
from apps.orchestrator.graph.state import AgentState


async def entry_router(state: AgentState):
    return state

