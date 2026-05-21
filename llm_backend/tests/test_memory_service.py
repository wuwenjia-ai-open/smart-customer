"""MemoryService 集成测试 — 三层记忆 (依赖 MySQL)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pytest_asyncio

# 所有用例都依赖真实 MySQL，整体标记为 integration，CI 默认跳过
pytestmark = pytest.mark.integration
from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.conversation import Conversation, DialogueType
from app.models.topic_segment import TopicSegment
from app.models.dialogue_state import DialogueState
from app.models.message import Message
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.memory_service import MemoryService


@pytest_asyncio.fixture(loop_scope="session")
async def seed_conversation():
    """准备一个 user + conversation + thread_id + topic_segment"""
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
        if not user:
            user = User(username="test_memory_user", email="t@t.com", hashed_password="x")
            db.add(user)
            await db.commit()
            await db.refresh(user)
        thread_id = "test-thread-mem-001"
        # 清理可能存在的旧数据
        old_convs = (await db.execute(
            select(Conversation.id).where(Conversation.thread_id == thread_id)
        )).scalars().all()
        for cid in old_convs:
            old_segs = (await db.execute(
                select(TopicSegment.id).where(TopicSegment.conversation_id == cid)
            )).scalars().all()
            for sid in old_segs:
                await db.execute(delete(DialogueState).where(DialogueState.segment_id == sid))
            await db.execute(delete(TopicSegment).where(TopicSegment.conversation_id == cid))
            await db.execute(delete(Message).where(Message.conversation_id == cid))
        await db.execute(delete(Conversation).where(Conversation.thread_id == thread_id))
        await db.commit()

        conv = Conversation(
            user_id=user.id, title="test", thread_id=thread_id,
            dialogue_type=DialogueType.AGENT,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        seg = TopicSegment(conversation_id=conv.id)
        db.add(seg)
        await db.commit()
        await db.refresh(seg)

        yield thread_id, user.id, conv.id, seg.id

        # 清理
        await db.execute(delete(DialogueState).where(DialogueState.segment_id == seg.id))
        await db.execute(delete(TopicSegment).where(TopicSegment.conversation_id == conv.id))
        await db.execute(delete(Message).where(Message.conversation_id == conv.id))
        await db.execute(delete(Conversation).where(Conversation.id == conv.id))
        await db.execute(delete(UserProfile).where(UserProfile.user_id == user.id))
        await db.commit()


# ── 短期:消息历史 ──

@pytest.mark.asyncio
async def test_save_message_pair_creates_two_rows(seed_conversation):
    thread_id, user_id, conv_id, seg_id = seed_conversation
    await MemoryService.save_message_pair(thread_id, "你好", "亲～有什么可以帮您的")
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
        )).scalars().all()
        assert len(rows) == 2
        assert rows[0].sender == "user" and rows[0].content == "你好"
        assert rows[1].sender == "assistant" and rows[1].content == "亲～有什么可以帮您的"


@pytest.mark.asyncio
async def test_get_recent_messages_returns_sliding_window(seed_conversation):
    thread_id, user_id, conv_id, seg_id = seed_conversation
    for i in range(6):
        await MemoryService.save_message_pair(thread_id, f"q{i}", f"a{i}")
    recent = await MemoryService.get_recent_messages(thread_id, limit=4)
    assert len(recent) == 4
    assert recent[-1]["content"] == "a5"
    assert recent[0]["sender"] in ("user", "assistant")


@pytest.mark.asyncio
async def test_get_recent_messages_missing_thread_returns_empty():
    rows = await MemoryService.get_recent_messages("nonexistent-thread-xxx", limit=8)
    assert rows == []


# ── 中期:segment 隔离 slots ──

@pytest.mark.asyncio
async def test_segment_slots_default_empty(seed_conversation):
    _, _, _, seg_id = seed_conversation
    slots = await MemoryService.get_segment_slots(seg_id, "product_qa")
    assert slots == {}


@pytest.mark.asyncio
async def test_write_slot_merges_within_worker(seed_conversation):
    _, _, _, seg_id = seed_conversation
    await MemoryService.write_slot(seg_id, "product_qa", {"products_mentioned": ["小米15"]})
    s1 = await MemoryService.get_segment_slots(seg_id, "product_qa")
    assert s1["products_mentioned"] == ["小米15"]

    await MemoryService.write_slot(seg_id, "product_qa", {"budget_max": 5000})
    s2 = await MemoryService.get_segment_slots(seg_id, "product_qa")
    assert s2["products_mentioned"] == ["小米15"]  # 旧 key 保留
    assert s2["budget_max"] == 5000                # 新 key 追加


@pytest.mark.asyncio
async def test_write_slot_isolated_by_worker(seed_conversation):
    _, _, _, seg_id = seed_conversation
    await MemoryService.write_slot(seg_id, "order_qa", {"last_order_id": "ORD-999"})
    product_slots = await MemoryService.get_segment_slots(seg_id, "product_qa")
    order_slots = await MemoryService.get_segment_slots(seg_id, "order_qa")
    # order_qa 的 slot 不污染 product_qa
    assert "last_order_id" not in product_slots
    assert order_slots["last_order_id"] == "ORD-999"


@pytest.mark.asyncio
async def test_get_all_segment_slots_groups_by_worker(seed_conversation):
    _, _, _, seg_id = seed_conversation
    await MemoryService.write_slot(seg_id, "product_qa", {"q": 1})
    await MemoryService.write_slot(seg_id, "order_qa", {"o": 2})
    all_slots = await MemoryService.get_all_segment_slots(seg_id)
    assert "product_qa" in all_slots
    assert "order_qa" in all_slots
    assert all_slots["product_qa"].get("q") == 1
    assert all_slots["order_qa"].get("o") == 2


# ── 长期:用户画像 + 对话摘要 ──

@pytest.mark.asyncio
async def test_user_profile_default_empty(seed_conversation):
    _, user_id, _, _ = seed_conversation
    prof = await MemoryService.get_user_profile(user_id)
    assert prof == {}


@pytest.mark.asyncio
async def test_user_profile_upsert_merges(seed_conversation):
    _, user_id, _, _ = seed_conversation
    await MemoryService.upsert_user_profile(user_id, {"preferred_brands": ["小米", "华为"]})
    p1 = await MemoryService.get_user_profile(user_id)
    assert p1["preferred_brands"] == ["小米", "华为"]
    await MemoryService.upsert_user_profile(user_id, {"budget_range": [3000, 5000]})
    p2 = await MemoryService.get_user_profile(user_id)
    assert p2["preferred_brands"] == ["小米", "华为"]
    assert p2["budget_range"] == [3000, 5000]


@pytest.mark.asyncio
async def test_conversation_summary_set_and_get(seed_conversation):
    thread_id, *_ = seed_conversation
    await MemoryService.set_summary(thread_id, "用户咨询 iPhone 16 价格,推荐了 3 款手机。")
    s = await MemoryService.get_summary(thread_id)
    assert "iPhone" in s


# ── 长对话摘要 ──

@pytest.mark.asyncio
async def test_summarize_if_needed_skips_when_under_threshold(seed_conversation):
    thread_id, *_ = seed_conversation
    await MemoryService.save_message_pair(thread_id, "q1", "a1")
    called = {"n": 0}

    class StubLLM:
        async def ainvoke(self, *a, **k):
            called["n"] += 1
            class R: content = "fake summary"
            return R()

    await MemoryService.summarize_if_needed(thread_id, StubLLM(), threshold=10, keep_recent=8)
    assert called["n"] == 0
    assert (await MemoryService.get_summary(thread_id)) is None


@pytest.mark.asyncio
async def test_summarize_if_needed_compresses_old_messages(seed_conversation, monkeypatch):
    thread_id, *_ = seed_conversation
    for i in range(7):
        await MemoryService.save_message_pair(thread_id, f"q{i}", f"a{i}")

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatResult, ChatGeneration

    class StubLLM(BaseChatModel):
        @property
        def _llm_type(self): return "stub"
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="用户问了 7 个问题"))])

    await MemoryService.summarize_if_needed(thread_id, StubLLM(), threshold=10, keep_recent=8)
    s = await MemoryService.get_summary(thread_id)
    assert s == "用户问了 7 个问题"
