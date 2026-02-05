import asyncio
from typing import Optional
from apps.shared.redis_client import RedisOperations
from apps.shared.logger import LogManager
from apps.orchestrator.services.summary_generator import SummaryGenerator
from apps.orchestrator.services.entity_extractor import EntityExtractor
from apps.orchestrator.services.llm_client import LLMClient
from apps.orchestrator.services.memory_extractor import MemoryExtractor
from apps.orchestrator.services.memory_service import MemoryService
from apps.orchestrator.services.title_generator import TitleGenerator

logger = LogManager("background_tasks").get_logger()

class BackgroundTaskProcessor:
    """后台任务处理器"""
    
    def __init__(self):
        self.redis = RedisOperations()
        self.running = False
        self.llm_client = LLMClient()
        # 延迟初始化 embedding client
        self.embedding_client = self.llm_client.get_embedding_client()
        self.memory_extractor = MemoryExtractor(self.llm_client)
        self.memory_service = MemoryService()
        self.title_generator = TitleGenerator(self.llm_client)
        
    async def start(self):
        """启动后台任务"""
        self.running = True
        logger.info("Background task processor started")
        
        await asyncio.gather(
            self._process_summaries(),
            self._process_memory_extraction()
        )
    
    async def stop(self):
        self.running = False
    
    async def _process_summaries(self):
        """处理摘要生成任务"""
        logger.info("Starting summary processing loop")
        
        while self.running:
            try:
                await self.redis.init()
                
                # 从队列获取任务
                # 阻塞 5 秒，避免死循环空转
                task = await self.redis.blpop_json(
                    "queue:summary_tasks",
                    timeout=5
                )
                
                if task:
                    session_id = task.get("session_id")
                    if not session_id:
                        continue
                        
                    logger.info(f"Processing summary for {session_id}")
                    
                    generator = SummaryGenerator(
                        self.llm_client,
                        self.embedding_client
                    )
                    
                    # 检查是否需要生成
                    if await generator.should_generate_summary(session_id):
                         await generator.generate_summary(session_id)
                    else:
                        logger.debug(f"Skipping summary for {session_id} (not needed)")
                
            except Exception as e:
                logger.error(f"Summary processing error: {e}")
                await asyncio.sleep(5)

    async def _process_memory_extraction(self):
        """处理记忆/实体提取任务"""
        logger.info("Starting memory extraction loop")
        
        while self.running:
            try:
                await self.redis.init()
                
                task = await self.redis.blpop_json(
                    "queue:memory_tasks",
                    timeout=5
                )
                
                if task:
                    session_id = task.get("session_id")
                    user_id = task.get("user_id")
                    user_msg = task.get("user_message")
                    ai_msg = task.get("ai_message")
                    
                    if not (session_id and user_id and user_msg):
                        continue
                        
                    logger.info(f"Processing entity extraction for {session_id}")
                    
                    extractor = EntityExtractor(self.llm_client)
                    await extractor.extract_entities(
                        user_message=user_msg,
                        ai_response=ai_msg or "",
                        user_id=user_id,
                        session_id=session_id
                    )

                    # 语义记忆抽取 & 保存
                    try:
                        memories = await self.memory_extractor.extract_memories(
                            user_message=user_msg,
                            ai_response=ai_msg or ""
                        )
                        for memory in memories:
                            await self.memory_service.save_memory_with_dedup(
                                user_id=user_id,
                                content=memory["content"],
                                importance=memory.get("importance", 0.6),
                                session_id=session_id
                            )
                    except Exception as e:
                        logger.error(f"Semantic memory extraction error: {e}")

                    # 智能标题生成（若需要）
                    try:
                        await self.title_generator.generate_title(session_id)
                    except Exception as e:
                        logger.error(f"Title generation error: {e}")
                    
            except Exception as e:
                logger.error(f"Memory extraction error: {e}")
                await asyncio.sleep(5)
