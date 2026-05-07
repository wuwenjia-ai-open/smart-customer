"""预定义 Cypher 查询集合（对齐 Northwind 新数据）"""
from typing import Dict

predefined_cypher_dict: Dict[str, str] = {
    # === 产品（5条）===
    "product_by_name": "MATCH (p:Product) WHERE p.ProductName CONTAINS $product_name RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, p.CategoryName, p.SupplierName",
    "product_by_category": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE c.CategoryName = $category_name RETURN p.ProductName, p.UnitPrice, p.UnitsInStock",
    "products_low_stock": "MATCH (p:Product) WHERE toInteger(p.UnitsInStock) < 10 RETURN p.ProductName, p.UnitsInStock, p.CategoryName ORDER BY toInteger(p.UnitsInStock)",
    "products_popular": "MATCH (p:Product)<-[:ABOUT]-(r:Review) RETURN p.ProductName, count(r) as ReviewCount, avg(toFloat(r.Rating)) as AvgRating ORDER BY ReviewCount DESC LIMIT 10",
    "top_rated_products": "MATCH (p:Product)<-[:ABOUT]-(r:Review) WITH p.ProductName as ProductName, avg(toFloat(r.Rating)) as AvgRating, count(r) as ReviewCount WHERE ReviewCount > 3 RETURN ProductName, AvgRating, ReviewCount ORDER BY AvgRating DESC LIMIT 10",

    # === 产品扩展（5条）===
    "products_price_range": "MATCH (p:Product) WHERE toFloat(p.UnitPrice) >= $min_price AND toFloat(p.UnitPrice) <= $max_price RETURN p.ProductName, p.UnitPrice, p.CategoryName, p.SupplierName ORDER BY toFloat(p.UnitPrice)",
    "products_by_supplier": "MATCH (p:Product) WHERE p.SupplierName CONTAINS $supplier_name RETURN p.ProductName, p.UnitPrice, p.CategoryName",
    "expensive_products": "MATCH (p:Product) RETURN p.ProductName, p.UnitPrice, p.CategoryName ORDER BY toFloat(p.UnitPrice) DESC LIMIT 10",
    "products_discontinued": "MATCH (p:Product) WHERE p.Discontinued = '1' OR p.Discontinued = 'true' RETURN p.ProductName, p.CategoryName, p.UnitPrice",
    "products_needing_reorder": "MATCH (p:Product) WHERE toInteger(p.UnitsOnOrder) > 0 AND toInteger(p.UnitsInStock) < toInteger(p.ReorderLevel) RETURN p.ProductName, p.UnitsInStock, p.UnitsOnOrder, p.ReorderLevel, p.SupplierName",

    # === 类别（3条）===
    "all_categories": "MATCH (c:Category) RETURN c.CategoryName, c.Description",
    "category_products": "MATCH (c:Category)<-[:BELONGS_TO]-(p:Product) WHERE c.CategoryName = $category_name RETURN p.ProductName, p.UnitPrice, p.UnitsInStock",
    "category_product_count": "MATCH (c:Category)<-[:BELONGS_TO]-(p:Product) RETURN c.CategoryName, count(p) as ProductCount ORDER BY ProductCount DESC",

    # === 智能家居过滤（4条）===
    "smart_home_products": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE c.CategoryName CONTAINS '智能' RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, c.CategoryName",
    "cheap_products": "MATCH (p:Product) WHERE toFloat(p.UnitPrice) < $max_price RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, p.CategoryName ORDER BY toFloat(p.UnitPrice)",

    # === 订单（8条）===
    "order_by_id": "MATCH (o:Order) WHERE o.orderId = $order_id OPTIONAL MATCH (o)-[c:CONTAINS]->(p:Product) RETURN o.orderId, o.OrderDate, o.RequiredDate, o.ShippedDate, o.Freight, p.ProductName, c.Quantity, c.UnitPrice",
    "order_details": "MATCH (o:Order)-[c:CONTAINS]->(p:Product) WHERE o.orderId = $order_id RETURN p.ProductName, c.Quantity, c.UnitPrice, c.Discount",
    "recent_orders": "MATCH (o:Order) RETURN o.orderId, o.OrderDate, o.ShippedDate, o.Freight ORDER BY o.OrderDate DESC LIMIT 10",
    "pending_orders": "MATCH (o:Order) WHERE o.ShippedDate IS NULL RETURN o.orderId, o.OrderDate, o.RequiredDate, o.Freight ORDER BY o.OrderDate",
    "orders_by_date_range": "MATCH (o:Order) WHERE o.OrderDate >= $start_date AND o.OrderDate <= $end_date RETURN o.orderId, o.OrderDate, o.ShippedDate, o.Freight ORDER BY o.OrderDate",
    "orders_by_country": "MATCH (o:Order) WHERE o.ShipCountry CONTAINS $country RETURN o.orderId, o.OrderDate, o.ShipCity, o.ShipCountry, o.Freight ORDER BY o.OrderDate DESC",
    "high_freight_orders": "MATCH (o:Order) WHERE toFloat(o.Freight) > $min_freight RETURN o.orderId, o.OrderDate, o.Freight, o.ShipCountry ORDER BY toFloat(o.Freight) DESC",
    "customer_search_orders": "MATCH (o:Order) WHERE o.CustomerName CONTAINS $customer_name RETURN o.orderId, o.OrderDate, o.ShippedDate, o.Freight ORDER BY o.OrderDate DESC",

    # === 客户（5条）===
    "customer_by_name": "MATCH (c:Customer) WHERE c.CompanyName CONTAINS $customer_name RETURN c.CompanyName, c.ContactName, c.Phone, c.Country, c.City",
    "customer_orders": "MATCH (c:Customer)-[:PLACED]->(o:Order) WHERE c.CompanyName = $customer_name RETURN o.orderId, o.OrderDate, o.ShippedDate, o.Freight",
    "customers_by_country": "MATCH (c:Customer) WHERE c.Country CONTAINS $country RETURN c.CompanyName, c.ContactName, c.City, c.Phone ORDER BY c.City",
    "customers_by_city": "MATCH (c:Customer) WHERE c.City CONTAINS $city RETURN c.CompanyName, c.ContactName, c.Phone, c.Country",
    "all_customers": "MATCH (c:Customer) RETURN c.CompanyName, c.ContactName, c.City, c.Country, c.Phone ORDER BY c.CompanyName",

    # === 供应商（3条）===
    "supplier_products": "MATCH (p:Product)-[:SUPPLIED_BY]->(s:Supplier) WHERE s.CompanyName CONTAINS $supplier_name RETURN p.ProductName, p.UnitPrice, p.UnitsInStock",
    "all_suppliers": "MATCH (s:Supplier) RETURN s.CompanyName, s.ContactName, s.City, s.Country, s.Phone ORDER BY s.CompanyName",
    "suppliers_by_country": "MATCH (s:Supplier) WHERE s.Country CONTAINS $country RETURN s.CompanyName, s.ContactName, s.City, s.Phone",

    # === 物流（3条）===
    "order_shipping": "MATCH (o:Order)-[:SHIPPED_VIA]->(s:Shipper) WHERE o.orderId = $order_id RETURN s.CompanyName, s.Phone, s.shipperId",
    "shipper_list": "MATCH (s:Shipper) RETURN s.shipperId, s.CompanyName, s.Phone",
    "shipper_orders": "MATCH (s:Shipper)<-[:SHIPPED_VIA]-(o:Order) WHERE s.CompanyName = $shipper_name RETURN o.orderId, o.OrderDate, o.ShippedDate ORDER BY o.OrderDate DESC",

    # === 评价（4条）===
    "product_reviews": "MATCH (p:Product)<-[:ABOUT]-(r:Review) WHERE p.ProductName = $product_name RETURN r.CustomerName, r.Rating, r.ReviewText, r.ReviewDate ORDER BY r.ReviewDate DESC",
    "customer_reviews": "MATCH (c:Customer)-[:WROTE]->(r:Review)-[:ABOUT]->(p:Product) WHERE c.CompanyName = $customer_name RETURN p.ProductName, r.Rating, r.ReviewText, r.ReviewDate ORDER BY r.ReviewDate DESC",
    "low_rated_reviews": "MATCH (r:Review)-[:ABOUT]->(p:Product) WHERE toFloat(r.Rating) < $max_rating RETURN p.ProductName, r.CustomerName, r.Rating, r.ReviewText, r.ReviewDate ORDER BY toFloat(r.Rating)",
    "recent_reviews": "MATCH (r:Review)-[:ABOUT]->(p:Product) RETURN p.ProductName, r.CustomerName, r.Rating, r.ReviewText, r.ReviewDate ORDER BY r.ReviewDate DESC LIMIT 10",

    # === 销售分析（4条）===
    "category_sales": "MATCH (o:Order)-[c:CONTAINS]->(p:Product)-[:BELONGS_TO]->(cat:Category) RETURN cat.CategoryName, sum(toFloat(c.Quantity) * toFloat(c.UnitPrice)) as TotalSales ORDER BY TotalSales DESC",
    "product_sales": "MATCH (o:Order)-[c:CONTAINS]->(p:Product) RETURN p.ProductName, sum(toFloat(c.Quantity)) as TotalQuantity, sum(toFloat(c.Quantity) * toFloat(c.UnitPrice)) as TotalRevenue ORDER BY TotalRevenue DESC LIMIT 10",
    "customer_total_spending": "MATCH (c:Customer)-[:PLACED]->(o:Order)-[ct:CONTAINS]->(p:Product) WHERE c.CompanyName CONTAINS $customer_name RETURN c.CompanyName, count(DISTINCT o) as OrderCount, sum(toFloat(ct.Quantity) * toFloat(ct.UnitPrice)) as TotalSpent",
    "sales_trend": "MATCH (o:Order)-[ct:CONTAINS]->(p:Product) WHERE o.OrderDate >= $start_date AND o.OrderDate <= $end_date RETURN o.OrderDate, sum(toFloat(ct.Quantity) * toFloat(ct.UnitPrice)) as DailyRevenue ORDER BY o.OrderDate",

    # === 员工（5条）===
    "employee_list": "MATCH (e:Employee) RETURN e.FirstName, e.LastName, e.Title, e.HireDate",
    "employee_orders": "MATCH (e:Employee)-[:PROCESSED]->(o:Order) WHERE e.LastName = $last_name RETURN o.orderId, o.OrderDate, o.ShippedDate",
    "employee_subordinates": "MATCH (e1:Employee)-[:REPORTS_TO]->(e2:Employee) WHERE e2.LastName = $last_name RETURN e1.FirstName, e1.LastName, e1.Title",
    "employees_by_title": "MATCH (e:Employee) WHERE e.Title CONTAINS $title RETURN e.FirstName, e.LastName, e.Title, e.HireDate, e.City",
    "employee_details": "MATCH (e:Employee) WHERE e.LastName = $last_name RETURN e.FirstName, e.LastName, e.Title, e.HireDate, e.BirthDate, e.Address, e.City, e.Country, e.HomePhone",

    # === 数据总览（3条）===
    "employee_sales_performance": "MATCH (e:Employee)-[:PROCESSED]->(o:Order)-[ct:CONTAINS]->(p:Product) RETURN e.FirstName, e.LastName, count(DISTINCT o) as OrderCount, sum(toFloat(ct.Quantity) * toFloat(ct.UnitPrice)) as TotalRevenue ORDER BY TotalRevenue DESC",
    "inventory_summary": "MATCH (p:Product) RETURN sum(toInteger(p.UnitsInStock)) as TotalStock, sum(toInteger(p.UnitsOnOrder)) as TotalOnOrder, avg(toFloat(p.UnitPrice)) as AvgPrice",


    # === 产品详情（消费者向）===
    "product_detail": "MATCH (p:Product)-[:HAS_DETAIL]->(d:ProductDetail) WHERE p.ProductName CONTAINS $product_name RETURN p.ProductName, p.UnitPrice, d.KeyFeatures, d.Specifications, d.SuitableFor, d.Description",
    "product_specs": "MATCH (p:Product)-[:HAS_DETAIL]->(d:ProductDetail) WHERE p.ProductName CONTAINS $product_name RETURN p.ProductName, d.Specifications",
    "product_features": "MATCH (p:Product)-[:HAS_DETAIL]->(d:ProductDetail) WHERE p.ProductName CONTAINS $product_name RETURN p.ProductName, d.KeyFeatures, d.Description",

    # === 常见问题 FAQ ===
    "faq_search": "MATCH (f:FAQ) WHERE f.question CONTAINS $keyword OR f.category CONTAINS $keyword RETURN f.category, f.question, f.answer",
    "faq_by_category": "MATCH (f:FAQ) WHERE f.category = $category RETURN f.question, f.answer",
    "all_faqs": "MATCH (f:FAQ) RETURN f.category, f.question, f.answer ORDER BY f.category",

    # === 售后政策 ===
    "after_sales_policy": "MATCH (p:AfterSalesPolicy) WHERE p.policyType CONTAINS $keyword RETURN p.policyType, p.content",
    "return_policy": "MATCH (p:AfterSalesPolicy) WHERE p.policyType = '退换货政策' RETURN p.policyType, p.content",
    "warranty_policy": "MATCH (p:AfterSalesPolicy) WHERE p.policyType = '保修政策' RETURN p.policyType, p.content",
    "shipping_policy": "MATCH (p:AfterSalesPolicy) WHERE p.policyType = '配送说明' RETURN p.policyType, p.content",

    # === 关联推荐（1条）===
    "also_bought": "MATCH (p1:Product)<-[:CONTAINS]-(o:Order)-[:CONTAINS]->(p2:Product) WHERE p1.ProductName CONTAINS $product_name AND p1 <> p2 RETURN p2.ProductName, count(*) as cnt ORDER BY cnt DESC LIMIT 5",
}
