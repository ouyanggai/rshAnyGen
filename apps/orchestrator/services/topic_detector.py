from typing import List, Dict, Optional
from apps.shared.logger import LogManager

logger = LogManager("topic_detector").get_logger()

class TopicDetector:
    """主题切换检测器"""
    
    def __init__(self, embedding_client, threshold: float = 0.7):
        self.embedding_client = embedding_client
        self.threshold = threshold
    
    async def detect_topic_change(
        self,
        messages: List[Dict],
        window_size: int = 4
    ) -> bool:
        """检测主题是否切换
        
        Args:
            messages: 消息列表
            window_size: 检测窗口大小
        
        Returns:
            True if topic changed
        """
        user_messages = [
            m for m in messages[-window_size:]
            if m.get("role") == "user"
        ]
        
        if len(user_messages) < 2:
            return False
        
        # 比较最近两条消息的相似度
        recent = user_messages[-2:]
        try:
            embeddings = await self.embedding_client.aembed_documents([
                m["content"] for m in recent
            ])
            
            similarity = self._cosine_similarity(
                embeddings[0], 
                embeddings[1]
            )
            
            logger.debug(f"Topic similarity: {similarity:.3f} (Threshold: {self.threshold})")
            return similarity < self.threshold
            
        except Exception as e:
            logger.error(f"Topic detection failed: {e}")
            return False
    
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        if not v1 or not v2:
            return 0.0
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for a, b in zip(v1, v2):
            dot += a * b
            norm_a += a * a
            norm_b += b * b
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / ((norm_a ** 0.5) * (norm_b ** 0.5))
    
    async def segment_by_topic(
        self,
        messages: List[Dict],
        min_segment_size: int = 6
    ) -> List[Dict]:
        """按主题分段 (用于批处理)
        
        Returns:
            List of segments: [
                {
                    "start_idx": 0,
                    "end_idx": 5,
                    "messages": [...],
                    "topic": None
                }
            ]
        """
        segments = []
        current_start = 0
        
        # 简化版：每隔 min_segment_size 检查一次
        # 实际生产中可能需要逐条检查或使用滑动窗口
        
        for i in range(min_segment_size, len(messages), 2):
            # 检查窗口 messages[i-4:i] 是否发生了主题切换
            # 这里简化逻辑，只看当前点是否是切换点
            # 实际上 detect_topic_change 看的是末尾几条
            
            # 如果我们在 i 处检测到切换，说明 messages[i] 与之前的不同
            # 所以 segment 应该是 [current_start, i-1]
            
            if await self.detect_topic_change(messages[:i+1]):
                segments.append({
                    "start_idx": current_start,
                    "end_idx": i - 1,
                    "messages": messages[current_start:i],
                    "topic": None
                })
                current_start = i
        
        # 最后一段
        if current_start < len(messages):
            segments.append({
                "start_idx": current_start,
                "end_idx": len(messages) - 1,
                "messages": messages[current_start:],
                "topic": None
            })
        
        return segments
