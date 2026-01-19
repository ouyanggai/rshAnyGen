"""Orchestrator Service - API Entry Point"""

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
from apps.orchestrator.graph.agent_graph import create_agent_graph

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

# Initialize Graph
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

class ChatResponse(BaseModel):
    response: str
    citations: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchestrator"}

@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """Process chat message through agent graph with streaming"""
    async def event_generator():
        try:
            # Initial state
            initial_state = {
                "session_id": request.session_id,
                "user_message": request.message,
                "messages": [], 
            }
            
            config = {"configurable": {"thread_id": request.session_id}}
            
            # Stream events from the graph
            # We use astream_events v2 which provides standardized event schema
            async for event in agent_graph.astream_events(initial_state, config=config, version="v2"):
                kind = event["event"]
                
                # Handle different event types
                if kind == "on_chat_model_stream":
                    # Stream tokens
                    content = event["data"]["chunk"].content
                    if content:
                        yield json.dumps({"type": "chunk", "content": content}) + "\n"
                        
                elif kind == "on_tool_start":
                    # Tool execution started
                    tool_name = event["name"]
                    yield json.dumps({"type": "thinking", "content": f"正在使用工具: {tool_name}..."}) + "\n"
                    
                elif kind == "on_tool_end":
                    # Tool execution finished
                    yield json.dumps({"type": "thinking", "content": f"工具执行完成"}) + "\n"
                
                elif kind == "on_chain_end":
                    # Check if it's the final output
                    if event["name"] == "LangGraph":
                        # We could send citations here if we had them in the state
                        pass

        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    # Return as line-delimited JSON stream
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

if __name__ == "__main__":
    port = config.get("ports", {}).get("orchestrator", 9302)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
