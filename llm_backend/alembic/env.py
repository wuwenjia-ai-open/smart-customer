"""Alembic 环境配置 — 读取项目 Settings 的 DATABASE_URL"""
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# 把项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base
from app.core.config import settings

# Alembic Config 对象
config = context.config

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 项目使用异步引擎 (mysql+aiomysql), Alembic 需要同步引擎 (mysql+pymysql)
_sync_url = settings.DATABASE_URL.replace("mysql+aiomysql", "mysql+pymysql")
config.set_main_option("sqlalchemy.url", _sync_url)

# 所有模型的 MetaData, 用于 autogenerate
from app.models import User, Conversation, Message, DialogueState, UserProfile  # noqa: F401
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式: 生成 SQL 脚本而不连接数据库"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式: 直接连接数据库执行迁移 (使用同步引擎)"""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
