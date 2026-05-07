"""
批量添加产品到 Neo4j：按品类分布，价格覆盖低中高，关联已有 Supplier 和 Category
"""
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from neo4j import GraphDatabase
from app.core.config import settings

driver = GraphDatabase.driver(settings.NEO4J_URL, auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD))

# 20 个品类 × 每个品类 2-4 个新品
new_products = [
    # 智能空调 (2款新品)
    ("格力 智能空调 Elite", 2899, 120, "智能空调", "格力智能电器"),
    ("美的 智能空调 Standard", 1599, 200, "智能空调", "美的智能科技"),
    # 智能冰箱 (2款)
    ("海尔 智能冰箱 Plus", 4599, 60, "智能冰箱", "海尔智慧家庭"),
    ("美的 智能冰箱 Compact", 1899, 150, "智能冰箱", "美的智能科技"),
    # 智能洗衣机 (3款)
    ("海尔 智能洗衣机 Pro", 2699, 80, "智能洗衣机", "海尔智慧家庭"),
    ("小米 智能洗衣机 Lite", 1299, 180, "智能洗衣机", "小米智能家居"),
    ("三星 智能洗衣机 Standard", 3299, 50, "智能洗衣机", "三星智能家电"),
    # 智能手环 (3款)
    ("华为 智能手环 Pro", 499, 300, "智能手环", "华为智能生活"),
    ("小米 智能手环 Lite", 199, 500, "智能手环", "小米智能家居"),
    ("苹果 智能手环 Elite", 1299, 150, "智能手环", "苹果智能家庭"),
    # 智能门锁 (2款)
    ("华为 智能门锁 Pro", 2499, 100, "智能门锁", "华为智能生活"),
    ("小米 智能门锁 Lite", 899, 250, "智能门锁", "小米智能家居"),
    # 智能插座 (2款)
    ("小米 智能插座 Pro", 79, 600, "智能插座", "小米智能家居"),
    ("华为 智能插座 Standard", 59, 500, "智能插座", "华为智能生活"),
    # 智能摄像头 (2款)
    ("萤石 智能摄像头 Pro", 399, 200, "智能摄像头", "萤石智能安防"),
    ("小米 智能摄像头 Lite", 199, 350, "智能摄像头", "小米智能家居"),
    # 智能空气净化器 (2款)
    ("小米 智能空气净化器 Lite", 799, 200, "智能空气净化器", "小米智能家居"),
    ("飞利浦 智能空气净化器 Pro", 1899, 100, "智能空气净化器", "飞利浦智能照明"),
    # 智能灯具 (3款)
    ("飞利浦 智能吸顶灯 Pro", 599, 200, "智能灯具", "飞利浦智能照明"),
    ("小米 智能台灯 Lite", 149, 400, "智能灯具", "小米智能家居"),
    ("华为 智能灯带 Standard", 99, 300, "智能灯具", "华为智能生活"),
    # 智能音箱 (2款)
    ("小米 智能音箱 Pro", 499, 250, "智能音箱", "小米智能家居"),
    ("苹果 智能音箱 Elite", 2499, 80, "智能音箱", "苹果智能家庭"),
    # 智能电视 (2款)
    ("华为 智能电视 Pro", 4999, 40, "智能电视", "华为智能生活"),
    ("小米 智能电视 Lite", 2499, 100, "智能电视", "小米智能家居"),
    # 智能电饭煲 (2款)
    ("美的 智能电饭煲 Pro", 699, 150, "智能电饭煲", "美的智能科技"),
    ("小米 智能电饭煲 Lite", 299, 300, "智能电饭煲", "小米智能家居"),
    # 智能扫地机器人 (2款)
    ("小米 扫地机器人 Pro", 1999, 120, "智能扫地机器人", "小米智能家居"),
    ("石头 扫地机器人 Lite", 999, 180, "智能扫地机器人", "石头科技"),
    # 智能窗帘 (2款)
    ("小米 智能窗帘 Standard", 499, 150, "智能窗帘", "小米智能家居"),
    ("华为 智能窗帘 Pro", 899, 100, "智能窗帘", "华为智能生活"),
    # 智能门铃 (2款)
    ("小米 智能门铃 Lite", 199, 300, "智能门铃", "小米智能家居"),
    ("华为 智能门铃 Pro", 399, 200, "智能门铃", "华为智能生活"),
    # 智能马桶 (1款)
    ("松下 智能马桶 Pro", 3999, 50, "智能马桶", "松下智能电器"),
    # 智能体重秤 (2款)
    ("小米 智能体重秤 Lite", 99, 400, "智能体重秤", "小米智能家居"),
    ("华为 智能体重秤 Pro", 199, 300, "智能体重秤", "华为智能生活"),
    # 智能净水器 (2款)
    ("小米 智能净水器 Standard", 999, 120, "智能净水器", "小米智能家居"),
    ("美的 智能净水器 Pro", 1699, 80, "智能净水器", "美的智能科技"),
    # 智能加湿器 (2款)
    ("小米 智能加湿器 Lite", 129, 350, "智能加湿器", "小米智能家居"),
    ("飞利浦 智能加湿器 Pro", 499, 180, "智能加湿器", "飞利浦智能照明"),
    # 智能开关 (2款)
    ("小米 智能开关 Standard", 59, 500, "智能开关", "小米智能家居"),
    ("华为 智能开关 Pro", 129, 350, "智能开关", "华为智能生活"),
]

# 适配已有 Supplier（没有的自动创建）
known_suppliers = set()

def run():
    with driver.session(database=settings.NEO4J_DATABASE) as session:
        # 获取已有 supplier
        r = session.run("MATCH (s:Supplier) RETURN s.CompanyName")
        for rec in r:
            known_suppliers.add(rec["s.CompanyName"])

        count = 0
        for name, price, stock, cat, supplier in new_products:
            # 如果 supplier 不存在，创建
            if supplier not in known_suppliers:
                session.run("CREATE (:Supplier {CompanyName: $s, Country: '中国'})", s=supplier)
                known_suppliers.add(supplier)
                print(f"  + 新供应商: {supplier}")

            # 创建产品并关联
            session.run("""
                MATCH (c:Category {CategoryName: $cat})
                MATCH (s:Supplier {CompanyName: $sup})
                CREATE (p:Product {
                    ProductName: $name, UnitPrice: $price,
                    UnitsInStock: $stock, CategoryName: $cat,
                    SupplierName: $sup
                })
                CREATE (p)-[:BELONGS_TO]->(c)
                CREATE (p)-[:SUPPLIED_BY]->(s)
            """, cat=cat, sup=supplier, name=name, price=str(price), stock=str(stock))
            count += 1

        print(f"\nDone: {count} new products added")

        # 验证
        r = session.run("MATCH (p:Product) RETURN count(p) AS total")
        total = r.single()["total"]
        r = session.run("MATCH (p:Product) WHERE toFloat(p.UnitPrice) < 2000 RETURN count(p) AS c")
        cheap = r.single()["c"]
        print(f"Total products: {total}, under 2000: {cheap}")

    driver.close()

if __name__ == "__main__":
    run()
