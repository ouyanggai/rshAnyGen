import re
import json
import time
import uuid
from datetime import datetime
from typing import List, Optional
from apps.shared.redis_client import RedisOperations
from apps.shared.logger import LogManager
from apps.shared.metrics import PerformanceMetrics
from apps.orchestrator.models.entity import Entity

logger = LogManager("entity_extractor").get_logger()

class EntityExtractor:
    """实体提取器 (规则 + LLM 混合)"""
    
    # 提取规则
    PATTERNS = {
        "person": [
            r"(?:我|他|她)(?:叫|名字是)\s*([\u4e00-\u9fa5]{2,4})", # 简化：只匹配2-4字中文名
            r"(?:同事|朋友|老师|领导)\s*([\u4e00-\u9fa5]{2,4})",
        ],
        "project": [
            r"(?:项目|系统|产品)(?:叫|名为)\s*(\w{2,20})",
        ],
        "location": [
            r"(?:在|位于)\s*([\u4e00-\u9fa5]{2,10})",
        ]
    }
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.redis = RedisOperations()
    
    async def extract_entities(
        self,
        user_message: str,
        ai_response: str,
        user_id: str,
        session_id: str
    ) -> List[Entity]:
        """提取实体"""
        await self.redis.init()

        self_name = self._extract_self_name(user_message)
        if self_name:
            await self._update_user_profile(user_id, self_name)
        
        entities = []
        
        # 1. 规则提取 (快速、准确)
        rule_entities = self._extract_by_rules(user_message)
        entities.extend(rule_entities)
        
        # 2. LLM提取 (补充、深度)
        if self.llm_client and self._should_use_llm(user_message):
            llm_entities = await self._extract_by_llm(
                user_message,
                ai_response
            )
            entities.extend(llm_entities)
        
        # 3. 去重
        entities = self._deduplicate(entities)
        
        # 4. 保存
        for entity in entities:
            await self._save_entity(entity, user_id, session_id)

        try:
            await PerformanceMetrics.record_metric("memory:entity_extraction", len(entities))
        except Exception as e:
            logger.error(f"Failed to record entity extraction metrics: {e}")
        
        return entities
    
    def _extract_by_rules(self, text: str) -> List[Entity]:
        """规则提取"""
        entities = []
        
        for entity_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    entities.append(Entity(
                        type=entity_type, # type: ignore
                        name=match.strip(),
                        confidence=0.85
                    ))
        
        return entities

    def _extract_self_name(self, text: str) -> Optional[str]:
        patterns = [
            r"(?:我叫|我名字是|我的名字是|叫我)\s*([\u4e00-\u9fa5]{2,4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None
    
    async def _extract_by_llm(
        self,
        user_msg: str,
        ai_msg: str
    ) -> List[Entity]:
        """LLM提取"""
        
        prompt = f"""从对话中提取关键实体。

用户: {user_msg}
AI: {ai_msg}

提取类型: person(人名), project(项目), location(地点), concept(概念)

JSON格式输出:
{{
  "entities": [
    {{"type": "person", "name": "张三", "attributes": {{"role": "同事"}}, "confidence": 0.9}}
  ]
}}
"""
        
        try:
            from langchain_core.messages import HumanMessage
            llm = self.llm_client.get_chat_model(temperature=0.2)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content
            
            # 清理
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            result = json.loads(content.strip())
            return [Entity(**e) for e in result.get("entities", [])]
        
        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")
            return []

    def _should_use_llm(self, text: str) -> bool:
        # 简单策略：如果文本较长，或者包含特定关键词，则使用 LLM
        # 这里简单起见，如果规则提取为空且文本长度 > 10，则尝试 LLM
        return len(text) > 10

    def _deduplicate(self, entities: List[Entity]) -> List[Entity]:
        # 简单按 name + type 去重
        unique = {}
        for e in entities:
            key = f"{e.type}:{e.name}"
            if key not in unique or e.confidence > unique[key].confidence:
                unique[key] = e
        return list(unique.values())
    
    async def _find_existing(self, _entity: Entity, _user_id: str) -> Optional[str]:
        # 从 Redis ZSet 查找
        # user:entities:{type}:{user_id} 存储 entity_id
        # 需要遍历查找 name 匹配的 (性能较低，生产环境应使用反向索引或 Hash 查找)
        
        # 优化：使用 name -> id 的映射?
        # user:entity_map:{user_id} -> {name: id}
        
        # 这里先简化：假设不进行深度查找，只创建新的或更新已知的
        # 如果要支持"更新"，需要知道 ID
        # 暂不实现复杂的查重
        return None

    async def _save_entity(
        self,
        entity: Entity,
        user_id: str,
        session_id: str
    ):
        """保存实体到Redis"""
        
        # 检查是否已存在 (简化版：只检查是否完全一致)
        # 实际应查询 user:entities:{type}:{user_id}
        
        entity_id = f"entity-{entity.type}-{uuid.uuid4().hex[:8]}"
        
        entity_data = {
            "type": entity.type,
            "name": entity.name,
            "attributes": json.dumps(entity.attributes),
            "first_seen": datetime.now().isoformat() if 'datetime' in globals() else time.strftime("%Y-%m-%dT%H:%M:%S"),
            "last_seen": datetime.now().isoformat() if 'datetime' in globals() else time.strftime("%Y-%m-%dT%H:%M:%S"),
            "mention_count": 1,
            "session_id": session_id
        }
        
        await self.redis.hset(
            f"entity:{entity_id}",
            mapping=entity_data
        )
        
        # 加入用户实体索引
        await self.redis.zadd(
            f"user:entities:{entity.type}:{user_id}",
            {entity_id: int(time.time())}
        )

    async def _update_user_profile(self, user_id: str, nickname: str):
        await self.redis.hset(
            f"user:{user_id}",
            {"nickname": nickname, "updated_at": int(time.time())}
        )
