"""聊天接口"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import httpx
import json

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from apps.gateway.models import ChatRequest
from apps.gateway.middleware.auth import require_auth
from apps.gateway.services.context_builder import get_context_builder
from apps.gateway.services.session_service import SessionService
from apps.gateway.services.message_service import MessageService

# 使用共享配置实例
config = ConfigLoader()
# 使用共享日志管理器
logger_manager = LogManager("gateway")
logger = logger_manager.get_logger()

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# 从配置文件读取编排器 URL
ORCHESTRATOR_URL = config.get(
    "services.orchestrator.url",
    "http://localhost:9302"
)


@router.post("/stream")
async def chat_stream(request: ChatRequest, req: Request, _user=Depends(require_auth)):
    """
    流式聊天接口

    请求：
    {
        "session_id": "sess-abc123",
        "message": "帮我搜索最新的AI新闻",
        "stream": true
    }

    响应（SSE Stream）：
    data: {"type": "thinking", "content": "正在分析..."}
    data: {"type": "chunk", "content": "根据搜索结果..."}
    data: {"type": "done"}
    """
    user_id = _user.get("user_id")
    session_id = request.session_id or getattr(req.state, "session_id", None)
    if session_id:
        req.state.session_id = session_id

    session_service = SessionService()
    message_service = MessageService()

    if not session_id:
        session = await session_service.create_session(user_id)
        session_id = session["session_id"]
    else:
        session = await session_service.get_session(session_id)
        if not session:
            session = await session_service.create_session(user_id, session_id=session_id)
        elif session.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Session access denied")

    await session_service.set_active_session(user_id, session_id)
    logger.info(f"Chat request: session={session_id}, message={request.message[:50]}")

    async def stream_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 流"""
        full_response = ""
        try:
            model = request.model or config.get("llm.model", "qwen-max")
            context_builder = get_context_builder(model=model)
            context_messages = await context_builder.build_context(
                session_id=session_id,
                user_id=user_id,
                current_message=request.message,
            )

            await message_service.append_message(session_id, "user", request.message)
            await session_service.touch_session(session_id)

            # 转发到 Orchestrator
            async with httpx.AsyncClient(timeout=30.0) as client:
                orchestrator_request = {
                    "session_id": session_id,
                    "message": request.message,
                    "chat_history": context_messages,
                    "enable_search": request.enable_search,
                    "kb_ids": request.kb_ids or [],
                }

                async with client.stream(
                    "POST",
                    f"{ORCHESTRATOR_URL}/api/v1/chat",
                    json=orchestrator_request
                ) as response:
                    if response.status_code != 200:
                        error_msg = f"Orchestrator error: {response.status_code}"
                        logger.error(error_msg)
                        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if data.get("type") == "chunk":
                                    full_response += data.get("content", "")
                            except Exception:
                                pass
                            yield f"data: {line}\n\n"

        except httpx.ConnectError as e:
            error_msg = f"Cannot connect to Orchestrator at {ORCHESTRATOR_URL}"
            logger.error(f"{error_msg}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        finally:
            if full_response:
                await message_service.append_message(session_id, "assistant", full_response)
                await session_service.touch_session(session_id)
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
