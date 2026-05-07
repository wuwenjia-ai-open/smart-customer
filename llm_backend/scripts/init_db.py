"""数据库初始化 — 使用 Alembic 迁移 (不再使用 drop_all/create_all)"""
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))


def init_db():
    """运行 Alembic 迁移到最新版本"""
    alembic_dir = ROOT_DIR
    print(f"[init_db] Running Alembic migrations... (dir: {alembic_dir})")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(alembic_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("[init_db] Database migrations applied successfully.")
        print(result.stdout)
    else:
        print(f"[init_db] Migration failed (code {result.returncode}):")
        print(result.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    init_db()
