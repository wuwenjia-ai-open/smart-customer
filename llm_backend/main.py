from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.logger import get_logger
from app.core.middleware import LoggingMiddleware
from app.core.config import settings
from app.api import api_router
from app.core.security import get_current_user
from app.models.user import User

logger = get_logger(service="main")

app = FastAPI(title="灵犀智购 REST API")

app.add_middleware(LoggingMiddleware)

allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False if settings.ALLOWED_ORIGINS == "*" else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    neo4j_ok = False
    try:
        from app.lg_agent.data.neo4j_conn import get_neo4j_graph
        get_neo4j_graph().query("RETURN 1")
        neo4j_ok = True
    except Exception:
        pass

    db_ok = False
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {"status": "ok", "neo4j": neo4j_ok, "mysql": db_ok}


@app.get("/api/validate-token")
async def validate_token(current_user: User = Depends(get_current_user)):
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
        },
    }


STATIC_DIR = Path(__file__).parent / "static" / "dist"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
