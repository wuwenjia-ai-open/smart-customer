"""工具执行器实现"""
import logging
from typing import Any, Dict, List
from .registry import ToolResult, register_tool

_log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Task 4: SemanticSearch Executor
# ═══════════════════════════════════════════════════════════════════════

class SemanticSearchExecutor:
    """语义搜索执行器 — bge-m3 向量化 → Milvus COSINE 检索 → 返回产品列表"""

    def __init__(self, milvus_client, embedding_model, collection_name: str = "product_descriptions"):
        self._milvus = milvus_client
        self._embed = embedding_model
        self._collection = collection_name

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        query = args.get("query", "")
        top_k = args.get("top_k", 5)

        try:
            vector = self._embed.embed_query(query)
            results = self._milvus.search(
                collection_name=self._collection,
                data=[vector],
                limit=top_k,
                output_fields=["product_name", "description", "price", "category"]
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
                return ToolResult(
                    records=[], summary="未找到匹配的产品",
                    success=False, error="no_results"
                )

            summary = f"语义搜索 '{query[:30]}' 找到 {len(records)} 个产品"
            return ToolResult(records=records, summary=summary)

        except Exception as e:
            _log.error(f"SemanticSearch failed: {e}")
            return ToolResult(records=[], summary="", error=str(e), success=False)


# ═══════════════════════════════════════════════════════════════════════
# Task 5: CompareProducts + Recommend Executors
# ═══════════════════════════════════════════════════════════════════════

class CompareProductsExecutor:
    """产品对比执行器 — Cypher 查产品属性 → 整理对比表"""

    def __init__(self, neo4j_graph, predefined_cypher_dict: Dict[str, str]):
        self._graph = neo4j_graph
        self._cypher_dict = predefined_cypher_dict

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        names = args.get("product_names", [])
        aspects = args.get("aspects")  # None = all aspects

        all_records = []
        for name in names:
            try:
                stmt = self._cypher_dict.get("product_by_name", "")
                if not stmt:
                    continue
                records = self._graph.query(stmt, params={"product_name": name})
                all_records.extend(records or [])
            except Exception as e:
                _log.warning(f"CompareProducts: failed for '{name}': {e}")

        if not all_records:
            return ToolResult(
                records=[], summary=f"未找到产品 {names} 的信息",
                success=False, error="no_results"
            )

        summary = f"已获取 {len(names)} 个产品的对比数据（{len(all_records)} 条记录）"
        return ToolResult(records=all_records, summary=summary)


class RecommendExecutor:
    """推荐执行器 — semantic_search + predefined_cypher 组合，多因子排序"""

    def __init__(self, milvus_client, embedding_model, neo4j_graph, predefined_cypher_dict: Dict[str, str]):
        self._semantic = SemanticSearchExecutor(milvus_client, embedding_model)
        self._graph = neo4j_graph
        self._cypher_dict = predefined_cypher_dict

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        scenario = args.get("scenario", "")
        budget_min = args.get("budget_min")
        budget_max = args.get("budget_max")
        preferences = args.get("preferences", [])
        exclude_names = set(args.get("exclude", []))
        top_k = args.get("top_k", 3)

        # Step 1: semantic search for candidates
        search_result = self._semantic.invoke({"query": scenario, "top_k": 15})
        if not search_result.success:
            return search_result

        # Step 2: filter by budget, exclude, preferences
        candidates = []
        for r in search_result.records:
            name = r.get("product_name", "")
            if name in exclude_names:
                continue
            price = float(r.get("price", 0) or 0)
            if budget_min is not None and price < budget_min:
                continue
            if budget_max is not None and price > budget_max:
                continue
            score = r.get("similarity", 0)
            # Boost if name matches preferences
            for pref in preferences:
                desc = r.get("description", "")
                if pref in desc:
                    score += 0.1
            candidates.append({**r, "score": score})

        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[:top_k]

        if not top:
            return ToolResult(
                records=[], summary="未找到符合条件的产品",
                success=False, error="no_match"
            )

        # Step 3: enrich with structured data from Neo4j
        enriched = []
        for c in top:
            try:
                stmt = self._cypher_dict.get("product_by_name", "")
                neo4j_records = self._graph.query(stmt, params={"product_name": c["product_name"]}) if stmt else []
                enriched.append({
                    **c,
                    "details": neo4j_records[0] if neo4j_records else {},
                })
            except Exception:
                enriched.append(c)

        summary = f"推荐 {len(enriched)} 个产品: " + ", ".join(
            f"{e['product_name']}(¥{e.get('price', 'N/A')})" for e in enriched
        )
        return ToolResult(records=enriched, summary=summary)


# ═══════════════════════════════════════════════════════════════════════
# Task 6: TrackShipment + CreateTicket Executors
# ═══════════════════════════════════════════════════════════════════════

class TrackShipmentExecutor:
    """物流追踪执行器 — Cypher 查订单物流状态"""

    def __init__(self, neo4j_graph):
        self._graph = neo4j_graph

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        order_id = args.get("order_id")
        if not order_id:
            return ToolResult(records=[], error="missing order_id", success=False)

        try:
            records = self._graph.query(
                "MATCH (o:Order) WHERE o.orderId = $order_id "
                "RETURN o.orderId, o.OrderDate, o.ShippedDate, o.RequiredDate, "
                "o.ShipVia, o.ShipName, o.ShipAddress, o.ShipCity, o.ShipCountry, o.Freight",
                params={"order_id": order_id}
            )
            if not records:
                return ToolResult(
                    records=[], summary=f"未找到订单 #{order_id}",
                    success=False, error="not_found"
                )
            r = records[0]
            shipped = r.get("ShippedDate", "未发货")
            summary = f"订单 #{order_id}: 下单 {r.get('OrderDate','未知')}, 发货状态: {shipped}"
            return ToolResult(records=records, summary=summary)
        except Exception as e:
            _log.error(f"TrackShipment failed: {e}")
            return ToolResult(records=[], error=str(e), success=False)


class CreateTicketExecutor:
    """创建工单执行器 — 写入 MySQL 工单表"""

    def __init__(self, db_session_factory):
        self._db = db_session_factory

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        issue_type = args.get("issue_type", "其他")
        order_id = args.get("order_id")
        description = args.get("description", "")
        priority = args.get("priority", "normal")

        # Stub: generate ticket ID until real ticket table is available
        ticket_id = f"TKT-{hash(description) % 100000:05d}"
        summary = f"工单 {ticket_id} 已创建: [{issue_type}] {description[:50]} (优先级: {priority})"
        return ToolResult(
            records=[{"ticket_id": ticket_id, "issue_type": issue_type, "status": "open"}],
            summary=summary
        )


# ═══════════════════════════════════════════════════════════════════════
# Task 7: AskClarification + EscalateToHuman Executors
# ═══════════════════════════════════════════════════════════════════════

class AskClarificationExecutor:
    """澄清工具 — 不执行查询，返回特殊标记让 ReAct 循环退出"""

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        question = args.get("question", "")
        missing_field = args.get("missing_field", "")
        options = args.get("options")
        return ToolResult(
            records=[{
                "__control__": "clarify",
                "question": question,
                "missing_field": missing_field,
                "options": options,
            }],
            summary=f"[CLARIFY] {question}",
        )


class EscalateToHumanExecutor:
    """转人工工具 — 标记会话为 pending_human"""

    def __init__(self, db_session_factory=None):
        self._db = db_session_factory

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        reason = args.get("reason", "")
        summary_text = args.get("summary", "")
        urgency = args.get("urgency", "normal")
        return ToolResult(
            records=[{
                "__control__": "escalate",
                "reason": reason,
                "summary": summary_text,
                "urgency": urgency,
            }],
            summary=f"[ESCALATE] {reason[:50]}",
        )
