from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.upload import router as upload_router
from app.api.langgraph import router as langgraph_router
from app.api.conversations import router as conversations_router

api_router = APIRouter()
api_router.include_router(auth_router, tags=["authentication"])
api_router.include_router(chat_router, tags=["chat"])
api_router.include_router(upload_router, tags=["upload"])
api_router.include_router(langgraph_router, tags=["langgraph"])
api_router.include_router(conversations_router, tags=["conversations"])
