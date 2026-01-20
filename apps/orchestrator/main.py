"""Orchestrator Service - API Entry Point"""

import os
# CRITICAL: Clear all proxy settings before any imports
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import json
import asyncio

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from apps.orchestrator.graph import create_agent_graph

# Initialize logging
log_manager = LogManager("orchestrator")
logger = log_manager.get_logger()

# Load config
try:
    config_loader = ConfigLoader()
    config = config_loader.load_defaults()
except Exception as e:
    logger.warning(f"Failed to load config: {e}. Using defaults.")
    config = {}

agent_graph = create_agent_graph()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Orchestrator service starting...")
    yield
    logger.info("Orchestrator service shutting down...")

app = FastAPI(
    title="Agent Orchestrator",
    description="LangGraph-based Agent Orchestrator",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatRequest(BaseModel):
    session_id: str
    message: str
    chat_history: Optional[List[Dict[str, str]]] = None
    llm_config: Optional[Dict[str, str]] = None  # e.g. {"api_key": "...", "base_url": "..."}

class ChatResponse(BaseModel):
    response: str
    citations: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchestrator"}

@app.get("/test/llm")
async def test_llm():
    """Test LLM directly"""
    from apps.orchestrator.services.llm_client import LLMClient

    llm = LLMClient().get_chat_model()
    result = await llm.ainvoke("你好")
    return {"status": "success", "response": result.content}

@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """Process chat message through LangGraph"""
    async def event_generator():
        try:
            state = {
                "session_id": request.session_id,
                "user_message": request.message,
                "messages": request.chat_history or [],
                "intent": "",
                "selected_skill": None,
                "skill_parameters": None,
                "tool_call_approved": True,
                "retrieved_docs": [],
                "reranked_docs": [],
                "tool_results": None,
                "final_answer": "",
                "citations": [],
                "metadata": {},
                "llm_config": request.llm_config,
            }

            node_thinking = {
                "intent_classifier": "正在分析意图...",
                "skill_selector": "正在选择工具...",
                "tool_executor": "正在调用工具...",
                "rag_retriever": "正在检索知识库...",
                "llm_generator": "正在生成回复...",
            }
            emitted = set()
            final_answer = None

            config = {"configurable": {"thread_id": request.session_id}}

            async for event in agent_graph.astream_events(
                state,
                config=config,
                version="v1",
            ):
                event_type = event.get("event")
                name = event.get("name")
                if event_type == "on_chain_start" and name in node_thinking and name not in emitted:
                    emitted.add(name)
                    yield json.dumps({"type": "thinking", "content": node_thinking[name]}) + "\n"

                if event_type == "on_chain_end" and name == "llm_generator":
                    data = event.get("data", {})
                    output = data.get("output") or data.get("outputs") or {}
                    if isinstance(output, dict):
                        final_answer = output.get("final_answer") or final_answer
                    elif isinstance(output, str):
                        final_answer = output

            if final_answer:
                yield json.dumps({"type": "chunk", "content": final_answer}) + "\n"

            yield json.dumps({"type": "done"}) + "\n"

        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

if __name__ == "__main__":
    port = config.get("ports", {}).get("orchestrator", 9302)
    # Use app object directly instead of module string to avoid import issues
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
