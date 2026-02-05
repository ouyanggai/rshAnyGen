import json
import re
import time
from typing import Optional, List, Dict

from apps.shared.redis_client import RedisOperations
from apps.shared.logger import LogManager

logger = LogManager("title_generator").get_logger()


class TitleGenerator:
    """会话标题智能生成器"""

    def __init__(self, llm_client):
        self.llm = llm_client.get_chat_model(temperature=0.2)
        self.redis = RedisOperations()

    async def generate_title(self, session_id: str, max_len: int = 16) -> Optional[str]:
        await self.redis.init()

        session_key = f"session:{session_id}"
        session = await self.redis.hgetall(session_key)
        if not session:
            return None

        title = session.get("title", "")
        title_source = session.get("title_source", "default")

        # 用户手动设置的标题不覆盖
        if title_source == "user":
            return None

        # 已经智能生成过的不重复生成
        if title_source == "auto_llm":
            return None

        # 准备对话内容
        summary_items = await self.redis.lrange_json(f"session:summaries:{session_id}", 0, -1)
        if summary_items:
            summary_text = "\n".join(
                [f"{item.get('topic', '主题')}: {item.get('summary', '')}" for item in summary_items[:5]]
            )
            content = f"对话摘要:\n{summary_text}"
        else:
            messages = await self.redis.lrange_json(f"session:messages:{session_id}", -12, -1)
            lines = []
            for msg in messages:
                role = "用户" if msg.get("role") == "user" else "助手"
                text = (msg.get("content") or "").strip()
                if not text:
                    continue
                lines.append(f"{role}: {text}")
            if not lines:
                return None
            content = "\n".join(lines)

        prompt = f"""你是一个标题生成器。请根据以下对话内容生成一个简洁准确的会话标题。

要求:
- 4-12个字
- 不要标点
- 不要出现“对话”“聊天”等泛化词
- 只输出 JSON

对话内容:
{content}

返回格式:
{{"title":"标题"}}"""

        try:
            from langchain_core.messages import HumanMessage

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]

            data = json.loads(raw.strip())
            next_title = (data.get("title") or "").strip()
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return None

        next_title = re.sub(r"\s+", " ", next_title).strip()
        if not next_title:
            return None

        if len(next_title) > max_len:
            next_title = next_title[:max_len].rstrip()

        if next_title == title:
            return None

        now = int(time.time())
        await self.redis.hset(session_key, {
            "title": next_title,
            "title_source": "auto_llm",
            "updated_at": now,
        })

        user_id = session.get("user_id")
        if user_id:
            await self.redis.zadd(f"user:sessions:{user_id}", {session_id: float(now)})

        return next_title
