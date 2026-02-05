from typing import List, Dict, Optional
from datetime import datetime
import json

from apps.shared.redis_client import RedisOperations
from apps.shared.logger import LogManager
from apps.shared.token_counter import get_token_counter
from apps.orchestrator.services.topic_detector import TopicDetector
from apps.shared.config_loader import ConfigLoader

logger = LogManager("summary_generator").get_logger()
config = ConfigLoader()

class SummaryGenerator:
    """智能摘要生成器"""
    
    def __init__(self, llm_client, embedding_client):
        self.llm = llm_client.get_chat_model()
        self.topic_detector = TopicDetector(embedding_client)
        self.redis = RedisOperations()
    
    async def should_generate_summary(
        self,
        session_id: str,
        trigger_token_count: int = None
    ) -> bool:
        """判断是否需要生成摘要"""
        await self.redis.init()
        messages = await self.redis.lrange_json(
            f"session:messages:{session_id}",
            0,
            -1
        )
        
        token_counter = get_token_counter()
        total_tokens = token_counter.count_messages(messages)

        if trigger_token_count is None:
            trigger_token_count = config.get("context.short_term_summary.trigger_tokens", 8192)
        
        # 如果已经生成过摘要，只看未摘要的部分？
        # 简化策略：如果总长度超过阈值，且距离上次生成摘要有一定间隔（这里暂不判断间隔）
        # 更好的策略：检查是否有新的长段落未被摘要
        
        # 获取已有的摘要数量
        summary_count = await self.redis.llen(f"session:summaries:{session_id}")
        
        # 简单的启发式：每增加 2000 tokens 或 10 条消息 尝试生成一次？
        # 这里沿用文档逻辑：总 tokens > 阈值
        
        return total_tokens > trigger_token_count
    
    async def generate_summary(
        self,
        session_id: str
    ) -> List[Dict]:
        """生成分段摘要"""
        await self.redis.init()
        
        # 1. 获取所有消息
        messages = await self.redis.lrange_json(
            f"session:messages:{session_id}",
            0,
            -1
        )
        
        if not messages:
            return []
            
        # 2. 按主题分段
        segments = await self.topic_detector.segment_by_topic(messages)
        
        logger.info(
            f"Session {session_id} segmented into {len(segments)} topics"
        )
        
        # 3. 为每段生成摘要
        # 优化：只为尚未摘要的段生成？
        # 为简化，全量重新生成 (注意：生产环境应增量生成)
        # 这里我们假设是全量覆盖
        
        summaries = []
        for segment in segments:
            # 跳过太短的段
            if len(segment["messages"]) < 2:
                continue
                
            summary = await self._summarize_segment(segment["messages"])
            
            summaries.append({
                "topic": summary.get("topic", "未知主题"),
                "summary": summary.get("content", ""),
                "message_range": [
                    segment["start_idx"],
                    segment["end_idx"]
                ],
                "created_at": datetime.now().isoformat()
            })
        
        # 4. 保存摘要 (覆盖)
        if summaries:
            key = f"session:summaries:{session_id}"
            await self.redis.delete(key)
            for summary in summaries:
                await self.redis.rpush_json(key, summary)
            
            logger.info(f"Generated {len(summaries)} summaries for {session_id}")
            
        return summaries
    
    async def _summarize_segment(
        self,
        messages: List[Dict]
    ) -> Dict:
        """为单个主题段生成摘要"""
        
        # 格式化对话
        conversation = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "AI"
            conversation.append(f"{role}: {msg['content']}")
        
        conv_text = "\n".join(conversation)
        
        prompt = f"""分析以下对话，生成简洁摘要。

对话内容:
{conv_text}

要求:
1. 用3-5个字概括主题
2. 用1-2句话总结关键信息
3. 保留重要决策和结论
4. 忽略闲聊和重复内容

请以JSON格式输出:
{{
  "topic": "主题",
  "content": "摘要内容"
}}
"""
        try:
            from langchain_core.messages import HumanMessage
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content
            
            # 清理 markdown code block
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            result = json.loads(content.strip())
            return result
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {
                "topic": "对话片段",
                "content": "摘要生成失败"
            }
