"""预定义 Cypher 查询节点 — 向量匹配 → 直接执行"""
import re
from typing import Any, Callable, Dict, List

from langchain_neo4j import Neo4jGraph

from .utils import create_vector_query_matcher
from .descriptions import QUERY_DESCRIPTIONS
from ..state import CypherOutputState


def _extract_params(cypher: str) -> List[str]:
    return re.findall(r'\$(\w+)', cypher)



def _auto_extract_params(task: str) -> dict:
    """从用户问题中自动提取参数"""
    params = {}
    # 提取订单号: 订单 5, 订单号 5, order 5, #5
    m = re.search(r'(?:订单|订单号|order)\s*#?\s*(\d+)', task, re.IGNORECASE)
    if m:
        params["order_id"] = int(m.group(1))
    # 提取产品名: 引号内或特定模式
    m = re.search(r'["""]([^"""]+)["""]', task)
    if m:
        params["product_name"] = m.group(1)
    # 提取金额
    m = re.search(r'(?:价格|金额|运费|低于|高于|超过|大于|小于)\s*(\d+)', task)
    if m:
        params["max_price"] = m.group(1)
    return params

def create_predefined_cypher_node(
    graph: Neo4jGraph,
    predefined_cypher_dict: Dict[str, str],
) -> Callable:
    """创建预定义查询节点"""

    matcher = create_vector_query_matcher(predefined_cypher_dict, QUERY_DESCRIPTIONS)

    async def predefined_cypher(state: Dict[str, Any]) -> Dict[str, Any]:
        task = state.get("task", "") or state.get("question", "")
        params = state.get("query_parameters", {})
        available = params.get("parameters", {}) if isinstance(params, dict) else {}
        if not isinstance(available, dict):
            available = {}

        errors = []
        records = []
        statement = ""

        auto_params = _auto_extract_params(task)
        if auto_params:
            available.update(auto_params)

        import logging; _log = logging.getLogger('predefined')

        # ── 主匹配：关键词直达（快、准） ──
        import re as _re
        _task_lower = task.lower()
        kw_map = []
        # 订单
        if _re.search(r'(订单|order|订单号)', _task_lower):
            oid = _re.search(r'(\d+)', task)
            if oid: kw_map.append(('order_by_id', {'order_id': int(oid.group(1))}))
            kw_map.append(('recent_orders', {}))
        # 物流
        if _re.search(r'(物流|快递|配送|发货|shipping)', _task_lower):
            oid = _re.search(r'(\d+)', task)
            if oid: kw_map.append(('order_shipping', {'order_id': int(oid.group(1))}))
        # 价格
        if _re.search(r'(价格|多少钱|便宜|低价|低于|价位|预算|之间|以下|以上|不超过|以内)', _task_lower):
            prices = _re.findall(r'(\d+)', task)
            if len(prices) >= 2:
                kw_map.append(('products_price_range', {'min_price': int(prices[0]), 'max_price': int(prices[1])}))
            elif len(prices) == 1:
                kw_map.append(('cheap_products', {'max_price': int(prices[0])}))
        # 评价
        if _re.search(r'(评价|评论|评分|review)', _task_lower):
            pn = _re.search(r'(?:智能|谷歌|小米|索尼|松下|博世|亚马逊|西门子)\s*\S+|智能\S+', task)
            if pn: kw_map.append(('product_reviews', {'product_name': pn.group(0)}))
            kw_map.append(('recent_reviews', {}))
        # 员工
        if _re.search(r'(员工|雇员|employee|谁)', _task_lower):
            kw_map.append(('employee_list', {}))
        # 产品功能/详情
        if _re.search(r'(功能|参数|规格|配置|怎么样|好用|介绍|详情|卖点|特点)', _task_lower):
            pn = _re.search(r'(?:谷歌|小米|索尼|松下|博世|亚马逊|西门子)\s*\S+|智能\S+', task)
            if pn: kw_map.append(('product_detail', {'product_name': pn.group(0)}))
        # 退货
        if _re.search(r'(退货|退换|退款|退了)', _task_lower):
            kw_map.append(('return_policy', {}))
            kw_map.append(('after_sales_policy', {'keyword': '退换货'}))
        # 保修
        if _re.search(r'(保修|维修|坏了|质保|保质)', _task_lower):
            kw_map.append(('warranty_policy', {}))
            kw_map.append(('faq_search', {'keyword': '保修'}))
        # 物流时效
        if _re.search(r'(多久.*[到发]|[到发].*多久|几天.*[到发]|什么时候.*[到发])', _task_lower):
            kw_map.append(('shipping_policy', {}))
        # FAQ
        if _re.search(r'(怎么|如何|怎样|咋|吗\?|吗$|能不能|可不可以)', _task_lower):
            kw_map.append(('faq_search', {'keyword': task[:30]}))
        # 支付/发票
        if _re.search(r'(支付|付款|发票|开票|税号)', _task_lower):
            kw_map.append(('faq_search', {'keyword': '支付'}))

        # 执行关键词匹配
        for name, params in kw_map:
            stmt = predefined_cypher_dict.get(name, '')
            if not stmt: continue
            try:
                records = graph.query(stmt, params=params)
                if records: statement = stmt; _log.warning(f'Keyword hit: {name} -> {len(records)} records'); break
            except Exception as e:
                errors.append(f'{name} failed: {e}')

        # ── 备用：Milvus 向量匹配 ──
        if not records:
            matches = matcher.match_query(task, top_k=5)
            _log.warning(f'Keyword miss, Milvus top-5: {[(m["query_name"], round(m["similarity"],3)) for m in matches]}')
            for m in matches:
                required = _extract_params(m["cypher"])
                missing = [p for p in required if p not in available or not available.get(p)]
                if missing: errors.append(f"{m['query_name']} needs params: {missing}"); continue
                try:
                    records = graph.query(m["cypher"], params=available)
                    if records: statement = m["cypher"]; break
                except Exception as e:
                    errors.append(f"{m['query_name']} failed: {e}")

        # ── 最终兜底：任务有明显约束(数字/品类)时交给动态Cypher，否则查全部产品 ──
        if not records:
            has_constraint = bool(_re.search(r'(\d+|智能\S+|手环|冰箱|空调|门锁|灯具|插座|摄像头|音箱|电视|马桶|窗帘|门铃|体重秤|净水器|加湿器|开关|电饭煲|扫地|洗衣机|空气净化)', task))
            if has_constraint:
                _log.warning(f'Task has constraints, skip fallback -> cypher_query will handle')
            else:
                try:
                    records = graph.query(predefined_cypher_dict['smart_home_products'], params={})
                    if records: statement = predefined_cypher_dict['smart_home_products']; _log.warning('Final fallback: smart_home_products')
                except Exception as e:
                    errors.append(f'Final fallback failed: {e}')

        if not records:
            errors.append(f"No predefined query matched: {task}")
            _log.warning(f"ALL FAILED, errors: {errors[-3:]}")

        return {
            "cyphers": [CypherOutputState(
                task=task, statement=statement, parameters=available,
                errors=errors, records=records, steps=["predefined_cypher"]
            )],
            "steps": ["predefined_cypher"],
        }

    return predefined_cypher
