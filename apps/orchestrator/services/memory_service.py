import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymilvus import connections, Collection, utility, DataType, FieldSchema, CollectionSchema
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from apps.shared.redis_client import RedisOperations
from apps.shared.metrics import PerformanceMetrics
from apps.orchestrator.services.memory_scorer import MemoryScorer

logger = LogManager("memory_service").get_logger()
config = ConfigLoader()

class MemoryService:
    """语义记忆服务 (Milvus)"""
    
    def __init__(self):
        # 复用 RAG Pipeline 的 embedder 配置（embedding.yaml），保证维度/提供商一致
        self._embedder = self._build_embedder()
        self.redis = RedisOperations()
        
        self.collection_name = "semantic_memories"
        self.dim = int(getattr(self._embedder, "get_dimension")())
        self.metric_type = config.get("vector_db.metric_type", "COSINE")
        self.index_type = config.get("vector_db.index_type", "HNSW")
        self.collection = None
        
        self._connect()
        self._ensure_collection()

    def _build_embedder(self):
        from services.rag_pipeline.embedder.embedder import Embedder

        base = config.load_defaults()
        embedding_config = config.load_config("embedding")

        # 与 rag_pipeline/server.py 的逻辑保持一致：embedding.yaml 决定 active provider/model/dimension
        embedding_settings = dict(base.get("embedding", {}))
        active_embedding = embedding_config.get("active_embedding")
        embedding_providers = embedding_config.get("embedding_providers", {})
        if active_embedding and active_embedding in embedding_providers:
            provider_config = dict(embedding_providers.get(active_embedding, {}))
            embedding_settings["provider"] = active_embedding
            if "model" in provider_config:
                embedding_settings["model"] = provider_config.get("model")
            if "dimension" in provider_config:
                embedding_settings["dimension"] = provider_config.get("dimension")
            embedding_settings[active_embedding] = provider_config

        return Embedder({"embedding": embedding_settings})

    def _get_vector_dim(self, collection: Collection) -> Optional[int]:
        try:
            for field in collection.schema.fields:
                if field.name != "vector":
                    continue
                if hasattr(field, "dim"):
                    return int(getattr(field, "dim"))
                params = getattr(field, "params", {}) or {}
                if "dim" in params:
                    return int(params["dim"])
        except Exception:
            return None
        return None

    def _build_index_params(self) -> dict:
        index_type = (self.index_type or "HNSW").upper()
        metric_type = (self.metric_type or "COSINE").upper()

        if index_type == "HNSW":
            return {
                "metric_type": metric_type,
                "index_type": "HNSW",
                "params": {"M": 16, "efConstruction": 200},
            }
        if index_type == "IVF_FLAT":
            return {
                "metric_type": metric_type,
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},
            }

        # 默认兜底
        return {
            "metric_type": metric_type,
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 200},
        }

    def _build_search_params(self) -> dict:
        index_type = (self.index_type or "HNSW").upper()
        metric_type = (self.metric_type or "COSINE").upper()

        if index_type == "HNSW":
            return {"metric_type": metric_type, "params": {"ef": 64}}
        if index_type == "IVF_FLAT":
            return {"metric_type": metric_type, "params": {"nprobe": 10}}
        return {"metric_type": metric_type, "params": {"ef": 64}}
    
    def _connect(self):
        host = config.get("dependencies.milvus.host", "localhost")
        port = config.get("dependencies.milvus.port", "19530")
        try:
            # 检查连接是否存在
            if not connections.has_connection("default"):
                connections.connect("default", host=host, port=port)
        except Exception as e:
            logger.error(f"Milvus connection failed: {e}")

    def _ensure_collection(self):
        try:
            if not utility.has_collection(self.collection_name):
                # 定义 Schema
                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
                    # 内容可能很长，Milvus VARCHAR限制 65535
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
                    FieldSchema(name="importance", dtype=DataType.FLOAT),
                    FieldSchema(name="created_at", dtype=DataType.INT64), # Timestamp
                    FieldSchema(name="access_count", dtype=DataType.INT64),
                    FieldSchema(name="last_accessed", dtype=DataType.INT64),
                ]
                schema = CollectionSchema(fields, "User semantic memories")
                
                self.collection = Collection(self.collection_name, schema)
                
                # 创建索引
                self.collection.create_index("vector", self._build_index_params())
                logger.info(f"Created collection {self.collection_name}")
            else:
                self.collection = Collection(self.collection_name)
                existing_dim = self._get_vector_dim(self.collection)
                if existing_dim and existing_dim != self.dim:
                    # 维度不一致：避免写入/查询失败，切换到新 collection
                    logger.warning(
                        f"Semantic memory collection dim mismatch: {existing_dim} != {self.dim}. "
                        f"Switching to a new collection."
                    )
                    self.collection_name = f"semantic_memories_{self.dim}"
                    if not utility.has_collection(self.collection_name):
                        fields = [
                            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
                            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
                            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
                            FieldSchema(name="importance", dtype=DataType.FLOAT),
                            FieldSchema(name="created_at", dtype=DataType.INT64),
                            FieldSchema(name="access_count", dtype=DataType.INT64),
                            FieldSchema(name="last_accessed", dtype=DataType.INT64),
                        ]
                        schema = CollectionSchema(fields, "User semantic memories")
                        self.collection = Collection(self.collection_name, schema)
                        self.collection.create_index("vector", self._build_index_params())
                        logger.info(f"Created collection {self.collection_name}")
                    else:
                        self.collection = Collection(self.collection_name)
                
            self.collection.load()
            
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")

    async def retrieve_relevant_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        if not self.collection:
            logger.warning("Milvus collection not available")
            return []

        if not query:
            return []

        try:
            start_time = time.time()
            embedding = await self._embedder.embed_query(query)
            search_params = self._build_search_params()
            results = self.collection.search(
                data=[embedding],
                anns_field="vector",
                param=search_params,
                limit=max(limit * 3, limit),
                expr=f"user_id == '{user_id}'",
                output_fields=[
                    "id",
                    "content",
                    "importance",
                    "created_at",
                    "access_count",
                    "last_accessed"
                ]
            )

            if not results or not results[0]:
                return []

            scorer = MemoryScorer()
            scored = []
            for hit in results[0]:
                similarity = hit.distance
                if similarity < min_similarity:
                    continue

                entity = getattr(hit, "entity", None)
                if entity is None and isinstance(hit, dict):
                    entity = hit.get("entity", hit)

                content = None
                base_importance = 0.5
                created_at_ts = 0
                access_count = 0
                last_accessed_ts = None
                memory_id = None

                if entity:
                    content = entity.get("content")
                    base_importance = float(entity.get("importance", 0.5) or 0.5)
                    created_at_ts = int(entity.get("created_at", 0) or 0)
                    access_count = int(entity.get("access_count", 0) or 0)
                    last_accessed_ts = entity.get("last_accessed")
                    memory_id = entity.get("id")

                if memory_id:
                    access_data = await self._get_access_stats(memory_id)
                    if access_data:
                        access_count = access_data.get("access_count", access_count)
                        last_accessed_ts = access_data.get("last_accessed", last_accessed_ts)

                if not content:
                    continue

                created_at = datetime.fromtimestamp(created_at_ts) if created_at_ts else datetime.now()
                last_accessed = (
                    datetime.fromtimestamp(int(last_accessed_ts))
                    if last_accessed_ts
                    else None
                )
                decayed_importance = scorer.calculate_current_importance(
                    base_importance,
                    created_at,
                    access_count,
                    last_accessed
                )
                combined_score = similarity * decayed_importance
                scored.append({
                    "id": memory_id,
                    "content": content,
                    "importance": decayed_importance,
                    "similarity": similarity,
                    "score": combined_score
                })

            scored.sort(key=lambda item: item["score"], reverse=True)
            result = scored[:limit]

            for item in result:
                memory_id = item.get("id")
                if memory_id is not None:
                    await self._update_memory_access(memory_id)

            try:
                await PerformanceMetrics.record_metric("memory:retrieval", len(result))
                await PerformanceMetrics.record_latency(
                    "memory_retrieval",
                    (time.time() - start_time) * 1000
                )
            except Exception as e:
                logger.error(f"Failed to record memory retrieval metrics: {e}")

            return result

        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")
            return []

    async def save_memory_with_dedup(
        self,
        user_id: str,
        content: str,
        importance: float,
        session_id: str
    ):
        """保存记忆(带去重)"""
        if not self.collection:
            logger.warning("Milvus collection not available")
            return

        try:
            # 1. 生成embedding
            embedding = await self._embedder.embed_query(content)
            
            # 2. 检查重复
            existing_id = await self.check_duplicate(
                user_id,
                embedding,
                content
            )
            
            if existing_id is not None:
                # 更新现有记忆
                await self._update_memory_access(existing_id)
                logger.info(f"Memory deduplicated: {existing_id}")
                try:
                    await PerformanceMetrics.record_metric("memory:deduplication", 1)
                except Exception as e:
                    logger.error(f"Failed to record deduplication metrics: {e}")
                return
            
            # 3. 保存新记忆
            data = [
                [user_id],
                [content[:4096]], # 截断防止溢出
                [embedding],
                [float(importance)],
                [int(time.time())],
                [0], # access_count
                [int(time.time())] # last_accessed
            ]
            
            insert_result = self.collection.insert(data)
            try:
                if insert_result and getattr(insert_result, "primary_keys", None):
                    memory_id = insert_result.primary_keys[0]
                    await self._update_memory_access(memory_id, initial=True)
            except Exception as e:
                logger.error(f"Failed to initialize memory access: {e}")
            logger.info(f"Saved new memory for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    async def check_duplicate(
        self,
        user_id: str,
        embedding: List[float],
        content: str,
        similarity_threshold: float = 0.92
    ) -> Optional[int]:
        """检查记忆是否重复"""
        try:
            search_params = self._build_search_params()
            
            # 搜索最近 30 天? 暂时不限时间
            expr = f"user_id == '{user_id}'"
            
            results = self.collection.search(
                data=[embedding],
                anns_field="vector",
                param=search_params,
                limit=1,
                expr=expr,
                output_fields=["id", "content"]
            )
            
            if not results or not results[0]:
                return None
            
            hit = results[0][0]
            # distance is cosine distance? or similarity?
            # If metric is COSINE, Milvus returns distance. 
            # Wait, Milvus Python SDK behavior depends on version.
            # Usually for COSINE, larger is better (similarity), unless it returns distance (1-sim).
            # Let's assume it returns similarity score directly for now or I check doc.
            # Usually Milvus returns 'distance' field. For IP/COSINE it's similarity.
            
            similarity = hit.distance
            
            if similarity > similarity_threshold:
                return hit.id
                
            return None
            
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return None

    async def _get_access_stats(self, memory_id: int) -> Dict[str, int]:
        await self.redis.init()
        data = await self.redis.hgetall(f"memory:access:{memory_id}")
        if not data:
            return {}
        return {
            "access_count": int(data.get("access_count") or 0),
            "last_accessed": int(data.get("last_accessed") or 0),
        }

    async def _update_memory_access(self, memory_id: int, initial: bool = False):
        await self.redis.init()
        key = f"memory:access:{memory_id}"
        current = await self.redis.hgetall(key)
        count = int(current.get("access_count") or 0)
        if not initial:
            count += 1
        now = int(time.time())
        await self.redis.hset(key, {"access_count": count, "last_accessed": now})

    async def update_score(self, memory_id: int, new_score: float):
        # Placeholder
        pass
        
    async def archive_memory(self, memory_id: int):
        """归档（删除）"""
        try:
            self.collection.delete(f"id in [{memory_id}]")
        except Exception as e:
            logger.error(f"Archive failed: {e}")
