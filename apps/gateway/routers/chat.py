"""聊天接口"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import httpx
import json
import time
import re

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from apps.shared.metrics import PerformanceMetrics
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


def _generate_session_title(message: str, max_len: int = 24) -> str:
    text = (message or "").strip()
    if not text:
        return "新会话"
    first_line = text.splitlines()[0]
    cleaned = re.sub(r"\s+", " ", first_line).strip()
    if not cleaned:
        return "新会话"
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rstrip() + "..."


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
    logger.info(f"🚀 DEBUG: Chat request received! User: {_user.get('username')}")
    user_id = _user.get("user_id")
    header_session_id = req.headers.get("X-Session-ID")
    session_id = request.session_id or header_session_id
    logger.info(f"🚀 DEBUG: Session ID: {session_id}, User ID: {user_id}")

    session_service = SessionService()
    message_service = MessageService()

    if not session_id:
        session_id = await session_service.get_active_session(user_id)

    if not session_id:
        session = await session_service.create_session(user_id)
        session_id = session["session_id"]
    else:
        session = await session_service.get_session(session_id)
        if not session:
            session = await session_service.create_session(user_id, session_id=session_id)
        elif session.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Session access denied")

    title_source = session.get("title_source") if session else None
    if session and title_source != "user" and session.get("title") in (None, "", "新会话"):
        next_title = _generate_session_title(request.message)
        if next_title and next_title != session.get("title"):
            await session_service.update_title(session_id, next_title, source="auto")

    req.state.session_id = session_id

    await session_service.set_active_session(user_id, session_id)
    logger.info(f"Chat request: session={session_id}, message={request.message[:50]}")

    async def stream_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 流"""
        full_response = ""
        start_time = time.time()
        try:
            model = request.model or config.get("llm.model", "qwen-max")
            context_builder = get_context_builder(model=model)

            # 记录上下文构建开始时间
            context_start = time.time()

            context_messages = await context_builder.build_context(
                session_id=session_id,
                user_id=user_id,
                current_message=request.message,
            )

            # 记录上下文构建延迟和Token使用
            context_duration = (time.time() - context_start) * 1000
            await PerformanceMetrics.record_latency("context_build", context_duration)

            # 计算上下文Token使用量
            from apps.shared.token_counter import get_token_counter
            token_counter = get_token_counter(model)
            context_tokens = token_counter.count_messages(context_messages)
            await PerformanceMetrics.record_token_usage("context_build", context_tokens)

            await message_service.append_message(session_id, "user", request.message)
            await session_service.touch_session(session_id)

            # 转发到 Orchestrator
            # trust_env=False：避免本机代理环境变量影响本地服务互调
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                # 过滤掉聊天历史中的 ts 字段，转换为Orchestrator期望的格式
                clean_chat_history = []
                for msg in context_messages:
                    clean_msg = {k: v for k, v in msg.items() if k != 'ts'}
                    clean_chat_history.append(clean_msg)

                kb_ids = request.kb_ids or (session.get("kb_ids") if session else []) or []
                orchestrator_request = {
                    "session_id": session_id,
                    "message": request.message,
                    "chat_history": clean_chat_history,
                    "enable_search": request.enable_search,
                    "kb_ids": kb_ids,
                }

                logger.info(f"Sending to Orchestrator: {json.dumps(orchestrator_request, ensure_ascii=False, indent=2)}")

                async with client.stream(
                    "POST",
                    f"{ORCHESTRATOR_URL}/api/v1/chat",
                    json=orchestrator_request
                ) as response:
                    # 对于流式响应，不应该直接访问 text 或 aread()
                    # 只能在 aiter_lines() 过程中处理
                    if response.status_code != 200:
                        # 流式响应出错时，我们只能读取前几行来判断错误类型
                        error_lines = []
                        async for line in response.aiter_lines():
                            error_lines.append(line)
                            if len(error_lines) >= 5:  # 只读取前5行
                                break
                        error_body = "\n".join(error_lines)
                        error_msg = f"Orchestrator error: {response.status_code}, response: {error_body}"
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
            # 记录聊天响应延迟
            chat_duration = (time.time() - start_time) * 1000
            await PerformanceMetrics.record_latency("chat_response", chat_duration)

            if full_response:
                await message_service.append_message(session_id, "assistant", full_response)
                await session_service.touch_session(session_id)

                # 计算响应Token使用量
                from apps.shared.token_counter import get_token_counter
                token_counter = get_token_counter(model)
                response_tokens = token_counter.count_text(full_response)
                await PerformanceMetrics.record_token_usage("chat_response", response_tokens)

                # 触发后台任务 (摘要生成等)
                try:
                    # 摘要任务
                    await session_service.redis.rpush_json(
                        "queue:summary_tasks",
                        {"session_id": session_id}
                    )

                    # 记忆提取任务
                    await session_service.redis.rpush_json(
                        "queue:memory_tasks",
                        {
                            "session_id": session_id,
                            "user_id": user_id,
                            "user_message": request.message,
                            "ai_message": full_response
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to push background tasks: {e}")

            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-ID": session_id,
        }
    )
