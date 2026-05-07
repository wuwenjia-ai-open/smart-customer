from pydantic_settings import BaseSettings
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

class Settings(BaseSettings):
    # Deepseek settings
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str
    DEEPSEEK_MODEL: str

    # Vision Model settings
    VISION_API_KEY: str
    VISION_BASE_URL: str
    VISION_MODEL: str

    # Ollama settings (仅用于 embedding 向量匹配)
    OLLAMA_BASE_URL: str
    OLLAMA_EMBEDDING_MODEL: str

    # Database settings
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Neo4j settings
    NEO4J_URL: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"

    # Milvus settings
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "predefined_cypher_vectors"

    # JWT settings
    SECRET_KEY: str = ""  # 生产环境必须设置, 为空则启动报错
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: str = "*"

    # Embedding settings
    EMBEDDING_TYPE: str = "ollama"
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_THRESHOLD: float = 0.90

    # SQLite checkpoint
    CHECKPOINT_DB_PATH: str = "checkpoints.db"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
