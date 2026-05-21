"""用户画像构建 — 从 segment slots 提炼长期偏好"""
from typing import Any, Dict, Optional

from app.services.memory_service import MemoryService
from app.core.logger import get_logger

_log = get_logger(service="profile_builder")

# slot key → 长期画像字段的映射(未列在此处的 key 视为短期会话状态,不入画像)
_LONG_TERM_MAP = {
    "products_mentioned": "history_products",
    "budget_max": "recent_budget",
    "preferences": "interests",
}


def extract_long_term_prefs(slots: Dict[str, Any]) -> Dict[str, Any]:
    """从一轮会话累积的 slots 里挑出可沉淀的长期偏好。

    短期 slots(如 last_order_id)不进画像。
    """
    out: Dict[str, Any] = {}
    for src_key, target_key in _LONG_TERM_MAP.items():
        if src_key in slots and slots[src_key]:
            out[target_key] = slots[src_key]
    return out


async def update_user_profile_from_thread(
    thread_id: str, user_id: int, segment_id: Optional[int] = None
) -> None:
    """读取当前段所有 workers 的 slots,抽取长期偏好,合并写入 user_profiles。"""
    try:
        if segment_id:
            worker_slots = await MemoryService.get_all_segment_slots(segment_id)
            # 合并所有 worker 的 slots 用于偏好提取
            merged_slots: Dict[str, Any] = {}
            for wslots in worker_slots.values():
                merged_slots.update(wslots)
        else:
            merged_slots = {}

        prefs = extract_long_term_prefs(merged_slots)
        if not prefs:
            return
        existing = await MemoryService.get_user_profile(user_id)
        # history_products: union,上限 20
        if "history_products" in prefs and "history_products" in existing:
            merged_hp = list(set(existing["history_products"]) | set(prefs["history_products"]))
            prefs["history_products"] = merged_hp[:20]
        # interests: union,上限 10
        if "interests" in prefs and "interests" in existing:
            prefs["interests"] = list(set(existing["interests"]) | set(prefs["interests"]))[:10]
        await MemoryService.upsert_user_profile(user_id, prefs)
        _log.info(f"update_user_profile: user={user_id} seg={segment_id} prefs={list(prefs.keys())}")
    except Exception:
        _log.exception(f"update_user_profile failed for user={user_id} seg={segment_id}")
