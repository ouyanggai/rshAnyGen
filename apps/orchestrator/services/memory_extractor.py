import json
import re
from typing import List, Dict

from apps.shared.logger import LogManager

logger = LogManager("memory_extractor").get_logger()


class MemoryExtractor:
    """语义记忆抽取器 (LLM + 规则兜底)"""

    def __init__(self, llm_client):
        self.llm = llm_client.get_chat_model(temperature=0.2)

    async def extract_memories(
        self,
        user_message: str,
        ai_response: str,
        max_items: int = 5
    ) -> List[Dict]:
        user_message = (user_message or "").strip()
        ai_response = (ai_response or "").strip()
        if not user_message:
            return []

        prompt = f"""从对话中提取适合长期记忆的事实（偏好、身份、重要约束、长期目标、项目/任务关键信息）。
只保留对未来对话有价值的内容，避免保存临时问题或一次性指令。

对话:
用户: {user_message}
助手: {ai_response}

输出 JSON，格式如下:
{{
  "memories": [
    {{"content": "记忆内容", "importance": 0.6}}
  ]
}}

要求:
- 0~5 条
- content 使用中文自然语言完整描述
- importance 范围 0~1 (越重要越高)
"""

        memories: List[Dict] = []
        try:
            from langchain_core.messages import HumanMessage

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            data = json.loads(raw.strip())
            for item in data.get("memories", []):
                content = (item.get("content") or "").strip()
                if not content:
                    continue
                importance = float(item.get("importance") or 0.5)
                importance = max(min(importance, 1.0), 0.0)
                memories.append({"content": content, "importance": importance})
        except Exception as e:
            logger.warning(f"LLM memory extraction failed, fallback to rules: {e}")

        if not memories:
            memories = self._fallback_rule_extract(user_message)

        # 去重 + 截断
        unique = []
        seen = set()
        for item in memories:
            key = item["content"]
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
            if len(unique) >= max_items:
                break

        return unique

    def _fallback_rule_extract(self, text: str) -> List[Dict]:
        patterns = [
            r"(我叫|我的名字是|叫我)\s*([\u4e00-\u9fa5]{2,4})",
            r"(我是)\s*([\u4e00-\u9fa5A-Za-z0-9_-]{2,20})",
            r"(我在|我住在|我来自)\s*([\u4e00-\u9fa5]{2,10})",
            r"(我喜欢|我爱|我偏好)\s*([^。！!？?]{2,20})",
            r"(我不喜欢|我讨厌)\s*([^。！!？?]{2,20})",
            r"(我的目标是|我计划|我打算)\s*([^。！!？?]{2,30})",
        ]
        memories: List[Dict] = []
        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            if len(match.groups()) >= 2:
                value = match.group(2).strip()
            else:
                value = match.group(1).strip()
            if not value:
                continue
            memories.append({"content": f"用户: {value}", "importance": 0.6})
        return memories
