"""User profile builder — 从 dialogue_states 累积的 slots 抽取长期偏好"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


def test_extract_long_term_prefs_from_slots():
    from app.services.profile_builder import extract_long_term_prefs
    slots = {
        "products_mentioned": ["iPhone 16", "小米 15"],
        "budget_max": 5000,
        "preferences": ["拍照好", "续航长"],
        "last_order_id": 1001,
    }
    prefs = extract_long_term_prefs(slots)
    assert "iPhone 16" in prefs["history_products"]
    assert "小米 15" in prefs["history_products"]
    assert prefs["recent_budget"] == 5000
    assert "拍照好" in prefs["interests"]
    assert "last_order_id" not in prefs


def test_extract_returns_empty_when_no_useful_slots():
    from app.services.profile_builder import extract_long_term_prefs
    assert extract_long_term_prefs({}) == {}
    assert extract_long_term_prefs({"last_order_id": 1}) == {}
