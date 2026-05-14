"""测试预定义 Cypher 查询：参数提取、关键词匹配、Cypher 字典"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.predefined_cypher.node import (
    _auto_extract_params,
    _extract_params,
)
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.predefined_cypher.cypher_dict import (
    predefined_cypher_dict,
)


class TestExtractParams:
    def test_extracts_dollar_params(self):
        cypher = "MATCH (p:Product) WHERE p.ProductName CONTAINS $name AND p.UnitPrice < $max_price RETURN p"
        params = _extract_params(cypher)
        assert "name" in params
        assert "max_price" in params

    def test_no_params(self):
        cypher = "MATCH (n) RETURN n LIMIT 10"
        params = _extract_params(cypher)
        assert params == []

    def test_ignores_at_sign(self):
        cypher = "MATCH (n) WHERE n.id = $id RETURN n.name"
        params = _extract_params(cypher)
        assert "id" in params
        assert "name" not in params


class TestAutoExtractParams:
    def test_order_id_chinese(self):
        params = _auto_extract_params("查一下订单5的详情")
        assert params["order_id"] == 5

    def test_order_id_english(self):
        params = _auto_extract_params("show me order 42")
        assert params["order_id"] == 42

    def test_order_id_with_hash(self):
        params = _auto_extract_params("订单号 #99")
        assert params["order_id"] == 99

    def test_price_extraction(self):
        params = _auto_extract_params("价格低于1000的空调")
        assert "max_price" in params
        assert params["max_price"] == "1000"

    def test_no_match(self):
        params = _auto_extract_params("有什么好产品推荐吗")
        assert params == {}

    def test_multiple_params(self):
        params = _auto_extract_params("订单 10 价格低于 500")
        assert params["order_id"] == 10
        assert params["max_price"] == "500"


class TestPredefinedCypherDict:
    def test_has_core_queries(self):
        assert "smart_home_products" in predefined_cypher_dict
        assert "product_reviews" in predefined_cypher_dict
        assert "order_by_id" in predefined_cypher_dict
        assert "recent_orders" in predefined_cypher_dict

    def test_queries_are_valid_cypher_basics(self):
        for name, cypher in predefined_cypher_dict.items():
            upper = cypher.upper().strip()
            assert upper.startswith("MATCH") or upper.startswith("CALL"), \
                f"Query '{name}' does not start with MATCH or CALL: {cypher[:60]}"

    def test_no_queries_contain_drop_or_delete(self):
        dangerous = ["DROP", "DELETE", "REMOVE", "DETACH"]
        for name, cypher in predefined_cypher_dict.items():
            upper = cypher.upper()
            for d in dangerous:
                assert d not in upper, f"Query '{name}' contains dangerous keyword '{d}'"

    def test_query_count(self):
        assert len(predefined_cypher_dict) >= 40

    def test_cheap_products_has_max_price(self):
        assert "max_price" in predefined_cypher_dict.get("cheap_products", "")

    def test_smart_home_products_is_readonly(self):
        q = predefined_cypher_dict.get("smart_home_products", "")
        assert "MATCH" in q.upper()
        assert "RETURN" in q.upper()
