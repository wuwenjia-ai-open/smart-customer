"""Neo4j 连接工厂（单例）"""
from functools import lru_cache
from langchain_neo4j import Neo4jGraph
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="neo4j_conn")


@lru_cache(maxsize=1)
def get_neo4j_graph() -> Neo4jGraph:
    logger.info(f"Initializing Neo4j connection: {settings.NEO4J_URL}")
    return Neo4jGraph(
        url=settings.NEO4J_URL,
        username=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD,
        database=settings.NEO4J_DATABASE,
    )
