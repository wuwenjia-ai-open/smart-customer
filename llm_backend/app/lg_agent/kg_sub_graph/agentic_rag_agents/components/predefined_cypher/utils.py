"""向量匹配工具 — Milvus 存储 + Ollama bge-m3 embedding"""
import numpy as np
from typing import Dict, List, Optional
from pymilvus import MilvusClient, DataType, FieldSchema, CollectionSchema
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="vector_matcher")

# Milvus vector dimension (bge-m3 produces 1024-dim vectors)
VECTOR_DIM = 1024


class VectorQueryMatcher:
    def __init__(
        self,
        predefined_cypher_dict: Dict[str, str],
        query_descriptions: Dict[str, str],
        similarity_threshold: float = 0.5,
    ):
        self.predefined_cypher_dict = predefined_cypher_dict
        self.query_descriptions = query_descriptions
        self.similarity_threshold = similarity_threshold
        self.ollama_url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embed"
        self.ollama_model = settings.OLLAMA_EMBEDDING_MODEL
        self.collection_name = settings.MILVUS_COLLECTION

        # Milvus client
        self.milvus_client = MilvusClient(uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}")

        # Initialize or load collection
        self._init_collection()

        # Load existing vectors from Milvus
        self.query_vectors = self._load_or_compute_vectors()

    def _check_ollama(self) -> bool:
        """检查 Ollama 连通性并确认 embedding 模型可用"""
        import requests
        try:
            r = requests.post(
                self.ollama_url,
                json={"model": self.ollama_model, "input": ["ping"]},
            )
            r.raise_for_status()
            data = r.json()
            if "embeddings" not in data or not data["embeddings"]:
                return False
            return True
        except Exception as e:
            logger.error(f"Ollama embedding 不可用: {e}")
            return False

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        import requests
        try:
            r = requests.post(self.ollama_url, json={"model": self.ollama_model, "input": texts})
            r.raise_for_status()
            return r.json()["embeddings"]
        except Exception as e:
            logger.error(f"Embedding 请求失败: {e}")
            raise RuntimeError(
                f"Ollama embedding 服务不可用 ({self.ollama_url}). "
                f"请确保 Ollama 已启动且模型 {self.ollama_model} 已拉取."
            )

    def _init_collection(self):
        """初始化 Milvus collection（不存在则创建）"""
        if self.milvus_client.has_collection(self.collection_name):
            logger.info(f"Milvus collection '{self.collection_name}' 已存在，加载中...")
            self.milvus_client.load_collection(self.collection_name)
        else:
            logger.info(f"创建 Milvus collection '{self.collection_name}'...")
            # 创建 schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="query_name", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
            ]
            schema = CollectionSchema(fields=fields, description="预定义查询向量库")
            self.milvus_client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                dimension=VECTOR_DIM,
                metric_type="COSINE",
            )
            # 创建索引并加载
            index_params = self.milvus_client.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                index_type="IVF_FLAT",
                metric_type="COSINE",
                params={"nlist": 128},
            )
            self.milvus_client.create_index(
                collection_name=self.collection_name,
                index_params=index_params,
            )
            self.milvus_client.load_collection(self.collection_name)
            logger.info(f"Milvus collection '{self.collection_name}' 创建成功并已加载")

    def _load_or_compute_vectors(self) -> Dict[str, np.ndarray]:
        """从 Milvus 加载向量，若无则计算并插入"""
        query_texts = []
        query_keys = []

        for name, cypher in self.predefined_cypher_dict.items():
            desc = self.query_descriptions.get(name, "")
            query_texts.append(f"{name} {desc}")
            query_keys.append(name)

        # 检查 Milvus 中是否已有数据
        existing = self.milvus_client.query(
            collection_name=self.collection_name,
            output_fields=["query_name", "vector"],
            limit=1000,
        )

        # 构建已存储向量的字典
        stored_vectors: Dict[str, np.ndarray] = {}
        if existing and len(existing) > 0:
            for item in existing:
                qname = item.get("query_name")
                vec = item.get("vector")
                if qname and vec:
                    stored_vectors[qname] = np.array(vec)
            logger.info(f"从 Milvus 加载了 {len(stored_vectors)} 条向量")

        # 检查是否所有查询都已存储
        missing_names = [k for k in query_keys if k not in stored_vectors]

        if not missing_names:
            logger.info("所有向量已存在，无需重新计算")
            return stored_vectors

        # 验证 Ollama 可用
        if not self._check_ollama():
            raise RuntimeError(
                f"Ollama embedding 服务连接失败. "
                f"请检查 OLLAMA_BASE_URL={self.ollama_url} 配置."
            )

        # 计算缺失的向量
        logger.info(f"需要计算 {len(missing_names)} 条缺失向量...")
        missing_texts = [f"{n} {self.query_descriptions.get(n, '')}" for n in missing_names]

        batch_size = 2
        all_new_vectors = []
        for i in range(0, len(missing_texts), batch_size):
            batch = missing_texts[i:i + batch_size]
            vectors = self._embed_texts(batch)
            all_new_vectors.extend(vectors)

        # 插入 Milvus
        for name, vec in zip(missing_names, all_new_vectors):
            self.milvus_client.insert(
                collection_name=self.collection_name,
                data={
                    "query_name": name,
                    "vector": vec,
                },
            )
            stored_vectors[name] = np.array(vec)

        logger.info(f"向 Milvus 插入 {len(missing_names)} 条新向量，完成")

        return stored_vectors

    def match_query(self, user_question: str, top_k: int = 3) -> List[Dict]:
        """检索与用户问题最相似的预定义查询"""
        # 将用户问题向量化
        q_vec = np.array(self._embed_texts([user_question])[0])

        # 在 Milvus 中搜索
        search_results = self.milvus_client.search(
            collection_name=self.collection_name,
            data=[q_vec.tolist()],
            limit=top_k,
            output_fields=["query_name", "vector"],
        )

        results = []
        if search_results and len(search_results) > 0:
            for res in search_results[0]:
                distance = res.get("distance", 0)
                # Milvus cosine distance → 相似度: similarity = 1 - distance
                score = 1 - distance
                query_name = res.get("entity", {}).get("query_name", "")

                if score >= self.similarity_threshold and query_name in self.predefined_cypher_dict:
                    results.append({
                        "query_name": query_name,
                        "similarity": float(score),
                        "cypher": self.predefined_cypher_dict[query_name],
                    })

        return results


def create_vector_query_matcher(
    predefined_cypher_dict: Dict[str, str],
    query_descriptions: Optional[Dict[str, str]] = None,
) -> VectorQueryMatcher:
    if query_descriptions is None:
        query_descriptions = {k: k.replace("_", " ") for k in predefined_cypher_dict}
    return VectorQueryMatcher(predefined_cypher_dict, query_descriptions)