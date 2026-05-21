"""数据服务层 — 封装所有 Milvus / Neo4j 访问，对外暴露业务方法"""
import logging
from typing import Any, Dict, List, Optional

_log = logging.getLogger(__name__)

# Milvus product search collection
PRODUCT_COLLECTION = "product_descriptions"


class ProductService:
    """产品查询服务 — Milvus 语义搜索 + Neo4j 批量补全关系数据"""

    def __init__(self, neo4j_graph, milvus_client, embedding_model):
        self._neo4j = neo4j_graph
        self._milvus = milvus_client
        self._embed = embedding_model

    # ── search ──

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """语义搜索产品 → Neo4j 批量补全评价/规格"""
        vector = self._embed.embed_query(query)
        results = self._milvus.search(
            collection_name=PRODUCT_COLLECTION,
            data=[vector],
            limit=top_k,
            output_fields=["product_name", "description", "price", "category"],
        )
        records = []
        for hits in results:
            for hit in hits:
                records.append({
                    "product_name": hit.get("product_name", ""),
                    "description": hit.get("description", ""),
                    "price": hit.get("price", ""),
                    "category": hit.get("category", ""),
                    "similarity": round(hit.get("distance", 0), 3),
                })
        if not records:
            return []
        # 批量补全 Neo4j 数据
        return self._enrich_batch(records)

    # ── compare ──

    def compare(self, names: List[str]) -> List[Dict]:
        """批量对比产品 — 一条 Cypher 查所有（含详情和评价）"""
        if not names:
            return []
        rows = self._neo4j.query(
            "MATCH (p:Product) WHERE p.ProductName IN $names "
            "OPTIONAL MATCH (p)-[:HAS_DETAIL]->(d:ProductDetail) "
            "OPTIONAL MATCH (p)<-[:ABOUT]-(r:Review) "
            "RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, p.CategoryName, p.BrandName, "
            "d.KeyFeatures, d.Specifications, "
            "collect({rating: r.Rating, text: r.ReviewText, customer: r.CustomerName}) as reviews",
            params={"names": names},
        )
        return list(rows) if rows else []

    # ── recommend ──

    def recommend(
        self, scenario: str, budget_min: Optional[float], budget_max: Optional[float],
        preferences: Optional[List[str]], exclude_names: Optional[set], top_k: int = 3,
    ) -> List[Dict]:
        """语义搜索 → 预算/偏好过滤 → Neo4j 批量补全"""
        exclude = exclude_names or set()
        prefs = preferences or []

        vector = self._embed.embed_query(scenario)
        results = self._milvus.search(
            collection_name=PRODUCT_COLLECTION,
            data=[vector],
            limit=15,
            output_fields=["product_name", "description", "price", "category"],
        )
        # 过滤
        candidates = []
        for hits in results:
            for hit in hits:
                name = hit.get("product_name", "")
                if name in exclude:
                    continue
                price = float(hit.get("price", 0) or 0)
                if budget_min is not None and price < budget_min:
                    continue
                if budget_max is not None and price > budget_max:
                    continue
                score = hit.get("distance", 0)
                for pref in prefs:
                    desc = hit.get("description", "")
                    if pref in desc:
                        score += 0.1
                candidates.append({
                    "product_name": name,
                    "description": hit.get("description", ""),
                    "price": price,
                    "category": hit.get("category", ""),
                    "score": score,
                })
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[:top_k]
        if not top:
            return []
        # 批量补全
        names = [c["product_name"] for c in top]
        enriched = self._enrich_with_details(names)
        # 合并
        name_map = {e["product_name"]: e for e in enriched}
        for c in top:
            detail = name_map.get(c["product_name"], {})
            c["details"] = detail
        return top

    # ── batch helpers ──

    def _enrich_batch(self, records: List[Dict]) -> List[Dict]:
        """批量从 Neo4j 补全产品评价和品牌"""
        names = [r.get("product_name", "") for r in records if r.get("product_name")]
        if not names:
            return records
        rows = self._neo4j.query(
            "MATCH (p:Product) WHERE p.ProductName IN $names "
            "OPTIONAL MATCH (p)<-[:ABOUT]-(r:Review) "
            "RETURN p.ProductName, p.UnitsInStock, p.BrandName, p.CategoryName, "
            "collect({rating: r.Rating, text: r.ReviewText, customer: r.CustomerName}) as reviews",
            params={"names": names},
        )
        enrich = {}
        for row in (rows or []):
            enrich[row.get("p.ProductName", "")] = row
        for r in records:
            extra = enrich.get(r.get("product_name", ""), {})
            r["stock"] = extra.get("p.UnitsInStock", "")
            r["brand"] = extra.get("p.BrandName", "")
            r["category"] = extra.get("p.CategoryName", "")
            r["reviews"] = extra.get("reviews", [])
        return records

    def _enrich_with_details(self, names: List[str]) -> List[Dict]:
        """批量从 Neo4j 补全产品详情 — 规范化键名为 product_name 等,
        与 Milvus 侧字段保持一致,避免上游访问时 KeyError。
        """
        if not names:
            return []
        rows = self._neo4j.query(
            "MATCH (p:Product) WHERE p.ProductName IN $names "
            "OPTIONAL MATCH (p)-[:HAS_DETAIL]->(d:ProductDetail) "
            "RETURN p.ProductName, p.UnitPrice, p.CategoryName, p.BrandName, "
            "d.KeyFeatures, d.Specifications",
            params={"names": names},
        )
        normalized = []
        for row in rows or []:
            normalized.append({
                "product_name":   row.get("p.ProductName", ""),
                "price":          row.get("p.UnitPrice", ""),
                "category":       row.get("p.CategoryName", ""),
                "brand":          row.get("p.BrandName", ""),
                "key_features":   row.get("d.KeyFeatures", ""),
                "specifications": row.get("d.Specifications", ""),
            })
        return normalized


class OrderService:
    """订单/物流查询服务"""

    def __init__(self, neo4j_graph):
        self._neo4j = neo4j_graph

    def get_order(self, order_id: int) -> Optional[Dict]:
        """查询订单 + 商品明细 — 字段与 scripts/seed_electronics.py 保持一致"""
        rows = self._neo4j.query(
            "MATCH (o:Order) WHERE o.orderId = $order_id "
            "OPTIONAL MATCH (o)-[c:CONTAINS]->(p:Product) "
            "RETURN o.orderId, o.OrderDate, o.ShippedDate, o.CustomerName, "
            "o.ShipName, o.ShipAddress, o.ShipCity, o.ShipCountry, o.Freight, "
            "collect({product: p.ProductName, qty: c.Quantity, unitPrice: c.UnitPrice}) as items",
            params={"order_id": order_id},
        )
        if not rows:
            return None
        return rows[0]

    def track_shipment(self, order_id: int) -> Optional[Dict]:
        """追踪物流"""
        return self.get_order(order_id)


class PolicyService:
    """FAQ / 售后政策查询服务"""

    def __init__(self, neo4j_graph):
        self._neo4j = neo4j_graph

    def search_faq(self, keyword: str) -> List[Dict]:
        """关键词搜索 FAQ"""
        rows = self._neo4j.query(
            "MATCH (f:FAQ) WHERE f.question CONTAINS $keyword OR f.category CONTAINS $keyword "
            "RETURN f.category, f.question, f.answer",
            params={"keyword": keyword},
        )
        return list(rows) if rows else []

    def get_policy(self, policy_type: str) -> List[Dict]:
        """查询售后政策"""
        rows = self._neo4j.query(
            "MATCH (p:AfterSalesPolicy) WHERE p.policyType CONTAINS $policy_type "
            "RETURN p.policyType, p.content",
            params={"policy_type": policy_type},
        )
        return list(rows) if rows else []
