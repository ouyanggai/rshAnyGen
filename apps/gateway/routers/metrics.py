"""监控指标 API"""
from fastapi import APIRouter, Request, HTTPException
from typing import Optional, List, Dict
from apps.shared.metrics import PerformanceMetrics
from apps.shared.redis_client import get_redis
from apps.shared.logger import LogManager

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])
logger = LogManager("gateway").get_logger()


@router.get("/token-usage")
async def get_token_usage_stats(
    window_hours: int = 24,
    req: Request = None
):
    """获取Token使用统计"""
    try:
        redis = get_redis()
        await redis.init()

        # 获取最近N小时的token使用记录
        window_seconds = window_hours * 3600
        token_keys = []
        try:
            metric_names = await redis.smembers("metrics:names")
            token_keys = [f"metrics:{name}" for name in metric_names if name.startswith("tokens:")]
        except Exception:
            token_keys = []

        if not token_keys:
            token_keys = await redis.keys("metrics:tokens:*")
        all_values = []
        by_operation = {}
        for key in token_keys:
            name = key.split("metrics:", 1)[-1]
            operation = name.split("tokens:", 1)[-1]
            values = await PerformanceMetrics.get_metric_values(
                name,
                window_seconds=window_seconds
            )
            if values:
                by_operation[operation] = PerformanceMetrics.compute_stats(values)
                all_values.extend(values)

        stats = PerformanceMetrics.compute_stats(all_values)

        return {
            "status": "success",
            "window_hours": window_hours,
            "stats": stats,
            "by_operation": by_operation
        }
    except Exception as e:
        logger.error(f"Failed to get token usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latency")
async def get_latency_stats(
    operation: Optional[str] = None,
    window_hours: int = 24,
    req: Request = None
):
    """获取延迟统计"""
    try:
        redis = get_redis()
        await redis.init()

        window_seconds = window_hours * 3600

        if operation:
            # 获取特定操作的延迟
            stats = await PerformanceMetrics.get_metric_stats(
                f"latency:{operation}",
                window_seconds=window_seconds
            )
        else:
            # 获取所有延迟指标
            operations = ["context_build", "chat_response", "memory_retrieval"]
            stats = {}
            for op in operations:
                stats[op] = await PerformanceMetrics.get_metric_stats(
                    f"latency:{op}",
                    window_seconds=window_seconds
                )

        return {
            "status": "success",
            "window_hours": window_hours,
            "operation": operation,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get latency stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context-stats")
async def get_context_stats(
    window_hours: int = 24,
    req: Request = None
):
    """获取上下文构建统计"""
    try:
        redis = get_redis()
        await redis.init()

        window_seconds = window_hours * 3600

        # 获取上下文构建相关指标
        token_budget_stats = await PerformanceMetrics.get_metric_stats(
            "context:token_budget",
            window_seconds=window_seconds
        )

        layer_usage_stats = await PerformanceMetrics.get_metric_stats(
            "context:layer_usage",
            window_seconds=window_seconds
        )

        return {
            "status": "success",
            "window_hours": window_hours,
            "token_budget": token_budget_stats,
            "layer_usage": layer_usage_stats
        }
    except Exception as e:
        logger.error(f"Failed to get context stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory-stats")
async def get_memory_stats(
    window_hours: int = 24,
    req: Request = None
):
    """获取记忆系统统计"""
    try:
        redis = get_redis()
        await redis.init()

        window_seconds = window_hours * 3600

        # 获取记忆相关指标
        extraction_stats = await PerformanceMetrics.get_metric_stats(
            "memory:entity_extraction",
            window_seconds=window_seconds
        )

        retrieval_stats = await PerformanceMetrics.get_metric_stats(
            "memory:retrieval",
            window_seconds=window_seconds
        )

        deduplication_stats = await PerformanceMetrics.get_metric_stats(
            "memory:deduplication",
            window_seconds=window_seconds
        )

        return {
            "status": "success",
            "window_hours": window_hours,
            "entity_extraction": extraction_stats,
            "retrieval": retrieval_stats,
            "deduplication": deduplication_stats
        }
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def get_metrics_overview(
    window_hours: int = 24,
    req: Request = None
):
    """获取所有指标概览"""
    try:
        # 并行获取所有统计信息
        token_stats = await get_token_usage_stats(window_hours)
        latency_stats = await get_latency_stats(window_hours=window_hours)
        context_stats = await get_context_stats(window_hours=window_hours)
        memory_stats = await get_memory_stats(window_hours=window_hours)

        return {
            "status": "success",
            "window_hours": window_hours,
            "timestamp": "now",
            "token_usage": token_stats["stats"],
            "latency": latency_stats["stats"],
            "context": context_stats,
            "memory": memory_stats
        }
    except Exception as e:
        logger.error(f"Failed to get metrics overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/active")
async def get_active_sessions(req: Request = None):
    """获取活跃会话统计"""
    try:
        redis = get_redis()
        await redis.init()

        # 获取活跃会话数量
        session_keys = await redis.keys("user:active_session:*")
        active_sessions = len(session_keys)

        # 获取最近活跃的用户
        recent_sessions = []
        for key in session_keys[:10]:
            user_id = key.split(":")[-1]
            recent_sessions.append({"user_id": user_id})

        return {
            "status": "success",
            "active_sessions": active_sessions,
            "recent_users": recent_sessions
        }
    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
