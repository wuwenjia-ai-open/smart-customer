"""Text2Cypher 动态查询 — 生成 → 语法校验 → 执行（失败重试1次）"""
from typing import Any, Callable, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import Neo4jGraph

from ..state import CypherOutputState

FEWSHOT = """
## 产品
- 查产品: MATCH (p:Product) WHERE p.ProductName CONTAINS $name RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, p.CategoryName, p.SupplierName
- 按类别: MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE c.CategoryName = $cat RETURN p.ProductName, p.UnitPrice, p.UnitsInStock
- 低价产品: MATCH (p:Product) WHERE toFloat(p.UnitPrice) < $max_price RETURN p.ProductName, p.UnitPrice, p.UnitsInStock ORDER BY toFloat(p.UnitPrice)
- 热门: MATCH (p:Product)<-[:ABOUT]-(r:Review) RETURN p.ProductName, count(r) as cnt, avg(toFloat(r.Rating)) as r ORDER BY cnt DESC LIMIT 10
- 高分: MATCH (p:Product)<-[:ABOUT]-(r:Review) WITH p.ProductName as n, avg(toFloat(r.Rating)) as r, count(r) as c WHERE c > 3 RETURN n, r, c ORDER BY r DESC LIMIT 10
## 订单
- 查订单: MATCH (o:Order) WHERE o.orderId = $id OPTIONAL MATCH (o)-[c:CONTAINS]->(p:Product) RETURN o.orderId, o.OrderDate, o.RequiredDate, o.ShippedDate, o.Freight, p.ProductName, c.Quantity, c.UnitPrice
- 最近: MATCH (o:Order) RETURN o.orderId, o.OrderDate, o.ShippedDate, o.Freight ORDER BY o.OrderDate DESC LIMIT 10
- 未发货: MATCH (o:Order) WHERE o.ShippedDate IS NULL RETURN o.orderId, o.OrderDate, o.RequiredDate ORDER BY o.OrderDate
- 订单详情: MATCH (o:Order)-[c:CONTAINS]->(p:Product) WHERE o.orderId = $id RETURN p.ProductName, c.Quantity, c.UnitPrice, c.Discount
## 客户
- 查客户: MATCH (c:Customer) WHERE c.CompanyName CONTAINS $name RETURN c.CompanyName, c.ContactName, c.Phone, c.City, c.Country
- 客户订单: MATCH (c:Customer)-[:PLACED]->(o:Order) WHERE c.CompanyName = $name RETURN o.orderId, o.OrderDate, o.ShippedDate
## 供应商
- 供应商产品: MATCH (p:Product)-[:SUPPLIED_BY]->(s:Supplier) WHERE s.CompanyName CONTAINS $name RETURN p.ProductName, p.UnitPrice
## 物流
- 订单物流: MATCH (o:Order)-[:SHIPPED_VIA]->(s:Shipper) WHERE o.orderId = $id RETURN s.CompanyName, s.Phone
- 物流公司列表: MATCH (s:Shipper) RETURN s.ShipperID, s.CompanyName, s.Phone
## 评价
- 产品评价: MATCH (p:Product)<-[:ABOUT]-(r:Review) WHERE p.ProductName = $name RETURN r.CustomerName, r.Rating, r.ReviewText, r.ReviewDate ORDER BY r.ReviewDate DESC
- 客户评价: MATCH (c:Customer)-[:WROTE]->(r:Review)-[:ABOUT]->(p:Product) WHERE c.CompanyName = $name RETURN p.ProductName, r.Rating, r.ReviewText
## 员工
- 员工列表: MATCH (e:Employee) RETURN e.FirstName, e.LastName, e.Title, e.HireDate
- 员工处理订单: MATCH (e:Employee)-[:PROCESSED]->(o:Order) WHERE e.LastName = $name RETURN o.orderId, o.OrderDate
- 下属: MATCH (e1:Employee)-[:REPORTS_TO]->(e2:Employee) WHERE e2.LastName = $name RETURN e1.FirstName, e1.LastName, e1.Title
## 销售/关联
- 类别销量: MATCH (o:Order)-[c:CONTAINS]->(p:Product)-[:BELONGS_TO]->(cat:Category) RETURN cat.CategoryName, sum(toFloat(c.Quantity)*toFloat(c.UnitPrice)) as s ORDER BY s DESC
- 产品销量: MATCH (o:Order)-[c:CONTAINS]->(p:Product) RETURN p.ProductName, sum(toFloat(c.Quantity)) as q, sum(toFloat(c.Quantity)*toFloat(c.UnitPrice)) as rev ORDER BY rev DESC LIMIT 10
- 买了X还买了什么: MATCH (p1:Product)<-[:CONTAINS]-(o:Order)-[:CONTAINS]->(p2:Product) WHERE p1.ProductName CONTAINS $name AND p1 <> p2 RETURN p2.ProductName, count(*) as cnt ORDER BY cnt DESC LIMIT 5
"""

GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""你是 Neo4j Cypher 专家。根据用户问题生成 Cypher 查询。

Schema:
节点: Product(ProductName,UnitPrice,UnitsInStock,CategoryName,SupplierName,QuantityPerUnit,UnitsOnOrder,ReorderLevel,Discontinued),
     Category(CategoryName,Description),
     Supplier(CompanyName,ContactName,Phone,Country),
     Customer(customerId,CompanyName,ContactName,ContactTitle,Address,City,Region,Country,Phone),
     Order(orderId,OrderDate,RequiredDate,ShippedDate,Freight,ShipName,ShipAddress,ShipCity,ShipCountry),
     Review(reviewId,CustomerName,Rating,ReviewText,ReviewDate),
     Employee(employeeId,FirstName,LastName,Title,HireDate),
     Shipper(shipperId,CompanyName,Phone)
关系: (Product)-[:BELONGS_TO]->(Category), (Product)-[:SUPPLIED_BY]->(Supplier),
     (Customer)-[:PLACED]->(Order), (Customer)-[:WROTE]->(Review),
     (Order)-[:CONTAINS]->(Product), (Order)-[:SHIPPED_VIA]->(Shipper),
     (Employee)-[:PROCESSED]->(Order), (Employee)-[:REPORTS_TO]->(Employee),
     (Review)-[:ABOUT]->(Product)

Few-shot 示例:
{FEWSHOT}

规则: 1)只生成 SELECT/MATCH 2)用 $param 参数化 3)价格用 toFloat() 4)只输出 Cypher，不要解释"""),
    ("human", "{question}\n\nCypher:"),
])


def create_cypher_query_node(llm: BaseChatModel, graph: Neo4jGraph, max_retries: int = 1) -> Callable:
    """创建 Text2Cypher 查询节点"""
    gen_chain = GEN_PROMPT | llm | StrOutputParser()

    async def cypher_query(state: Dict[str, Any]) -> Dict[str, Any]:
        task = state.get("task", "") or state.get("question", "")
        errors, records, statement = [], [], ""

        for attempt in range(max_retries + 1):
            raw = await gen_chain.ainvoke({"question": task})
            statement = raw.strip().removesuffix(";").strip()
            if statement.startswith("```"):
                lines = statement.split("\n")
                statement = "\n".join(lines[1:]) if lines[0].startswith("```") else statement
                if statement.endswith("```"):
                    statement = statement[:-3]
            statement = statement.strip()

            # 语法校验 — 用 EXPLAIN 检查
            try:
                graph.query(f"EXPLAIN {statement}")
                result = graph.query(statement)
                records = result if result else []
                break
            except Exception as e:
                errors.append(str(e))
                if attempt < max_retries:
                    task = f"原始问题: {task}\n上一次查询 '{statement}' 失败: {str(e)[:200]}\n请修正后重新生成。"
                else:
                    records = []

        return {
            "cyphers": [CypherOutputState(
                task=task, statement=statement, parameters={},
                errors=errors, records=records if records else [],
                steps=["cypher_query"]
            )],
            "steps": ["cypher_query"],
        }

    return cypher_query
