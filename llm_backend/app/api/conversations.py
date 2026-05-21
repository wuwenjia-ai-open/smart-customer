"""会话管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.conversation_service import ConversationService
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger(service="conversations")


@router.get("/conversations/mine")
async def list_my_conversations(current_user: User = Depends(get_current_user)):
    """列出当前用户的所有会话(JWT 鉴权),按 updated_at 倒序。

    每条带最后一条消息的预览,供前端历史抽屉展示。
    无消息的空会话被过滤掉(避免显示 auto-created 但用户没发过的)。
    """
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Conversation)
            .where(Conversation.user_id == current_user.id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        )).scalars().all()

        result = []
        for conv in rows:
            last_msg = (await db.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.id.desc())
                .limit(1)
            )).scalar_one_or_none()
            if not last_msg:
                continue  # 空会话不显示
            result.append({
                "thread_id": conv.thread_id,
                "title": conv.title or "新对话",
                "preview": (last_msg.content or "")[:60],
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            })
        return result


@router.delete("/conversations/by-thread/{thread_id}")
async def delete_conversation_by_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
):
    """按 thread_id 删除会话(JWT 鉴权),级联删除关联消息。"""
    async with AsyncSessionLocal() as db:
        conv = (await db.execute(
            select(Conversation).where(Conversation.thread_id == thread_id)
        )).scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        await db.delete(conv)
        await db.commit()
        return {"deleted": thread_id}


@router.get("/conversations/latest")
async def get_latest_conversation(current_user: User = Depends(get_current_user)):
    """返回当前用户最近一条对话(按 updated_at 倒序),用于登录后自动恢复 thread_id。

    没有任何对话时返回 {"thread_id": null}。
    """
    async with AsyncSessionLocal() as db:
        row = (await db.execute(
            select(Conversation)
            .where(Conversation.user_id == current_user.id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(1)
        )).scalar_one_or_none()
        if not row:
            return {"thread_id": None}
        return {
            "id": row.id,
            "thread_id": row.thread_id,
            "title": row.title,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


@router.get("/conversations/by-thread/{thread_id}/messages")
async def get_messages_by_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
):
    """按 thread_id (UUID 字符串) 拉取消息历史,前端登录后用 localStorage 里的
    thread_id 直接拉历史,无需先查 conversation_id。
    """
    async with AsyncSessionLocal() as db:
        conv = (await db.execute(
            select(Conversation).where(Conversation.thread_id == thread_id)
        )).scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")

        rows = (await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.id.asc())
        )).scalars().all()
        return [
            {
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in rows
        ]


class CreateConversationRequest(BaseModel):
    user_id: int


class UpdateConversationNameRequest(BaseModel):
    name: str


@router.post("/conversations")
async def create_conversation(request: CreateConversationRequest):
    try:
        conversation_id = await ConversationService.create_conversation(request.user_id)
        return {"conversation_id": conversation_id}
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/user/{user_id}")
async def get_user_conversations(user_id: int):
    try:
        conversations = await ConversationService.get_user_conversations(user_id)
        return conversations
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int, user_id: int):
    try:
        messages = await ConversationService.get_conversation_messages(conversation_id, user_id)
        return messages
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, user_id: int):
    try:
        conversation_service = ConversationService()
        await conversation_service.delete_conversation(conversation_id, user_id)
        return {"message": "会话已删除"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/conversations/{conversation_id}/name")
async def update_conversation_name(conversation_id: int, request: UpdateConversationNameRequest):
    try:
        conversation_service = ConversationService()
        await conversation_service.update_conversation_name(conversation_id, request.name)
        return {"message": "会话名称已更新"}
    except Exception as e:
        logger.error(f"更新会话名称失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
