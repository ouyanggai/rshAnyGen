import json
import math
import time
from typing import Dict, Any, List
from apps.shared.redis_client import get_redis
from apps.shared.logger import LogManager

logger = LogManager("metrics").get_logger()

class PerformanceMetrics:
    """性能指标收集"""
    
    @staticmethod
    async def record_metric(name: str, value: float, metadata: Dict[str, Any] = None):
        """记录指标"""
        try:
            redis = get_redis()
            await redis.init()
            
            data = {
                "value": value,
                "timestamp": time.time(),
                "metadata": metadata or {}
            }
            
            # 使用 Redis List 存储最近的指标
            key = f"metrics:{name}"
            await redis.rpush_json(key, data)
            # 记录指标名称，避免依赖 KEYS
            try:
                await redis.sadd("metrics:names", name)
            except Exception:
                pass
            
            # 保持列表长度在 1000 以内
            await redis.trim_list(key, -1000, -1)
            
        except Exception as e:
            logger.error(f"Failed to record metric {name}: {e}")

    @staticmethod
    async def get_metric_stats(name: str, window_seconds: int = 3600) -> Dict[str, float]:
        """获取指标统计 (最近 N 秒)"""
        try:
            redis = get_redis()
            await redis.init()
            
            key = f"metrics:{name}"
            # 获取最近 1000 条
            items = await redis.lrange_json(key, 0, -1)
            
            if not items:
                return {}
                
            now = time.time()
            values = [
                item["value"]
                for item in items
                if now - item["timestamp"] <= window_seconds
            ]

            return PerformanceMetrics.compute_stats(values)
            
        except Exception as e:
            logger.error(f"Failed to get metric stats {name}: {e}")
            return {}

    @staticmethod
    async def get_metric_values(name: str, window_seconds: int = 3600) -> List[float]:
        try:
            redis = get_redis()
            await redis.init()

            key = f"metrics:{name}"
            items = await redis.lrange_json(key, 0, -1)

            if not items:
                return []

            now = time.time()
            return [
                item["value"]
                for item in items
                if now - item["timestamp"] <= window_seconds
            ]

        except Exception as e:
            logger.error(f"Failed to get metric values {name}: {e}")
            return []

    @staticmethod
    def compute_stats(values: List[float]) -> Dict[str, float]:
        if not values:
            return {}

        def percentile(sorted_values: List[float], p: float) -> float:
            if not sorted_values:
                return 0.0
            if len(sorted_values) == 1:
                return float(sorted_values[0])
            k = (len(sorted_values) - 1) * (p / 100.0)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return float(sorted_values[int(k)])
            d0 = sorted_values[f] * (c - k)
            d1 = sorted_values[c] * (k - f)
            return float(d0 + d1)

        sorted_values = sorted(values)
        total = float(sum(values))
        count = len(values)
        avg = total / count if count else 0.0

        return {
            "count": count,
            "sum": total,
            "avg": avg,
            "p95": percentile(sorted_values, 95),
            "max": float(max(values)),
            "min": float(min(values))
        }

    # 快捷方法
    
    @staticmethod
    async def record_latency(operation: str, duration_ms: float):
        await PerformanceMetrics.record_metric(
            f"latency:{operation}", 
            duration_ms
        )
        
    @staticmethod
    async def record_token_usage(operation: str, tokens: int):
        await PerformanceMetrics.record_metric(
            f"tokens:{operation}", 
            tokens
        )
