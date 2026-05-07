"""预定义查询的描述（用于向量匹配）"""
QUERY_DESCRIPTIONS = {
    # 产品
    "product_by_name": "查询特定名称的产品信息，包括价格、库存、类别和供应商",
    "product_by_category": "查询特定类别下的所有产品",
    "products_low_stock": "查询库存不足的产品（低于10个）",
    "products_popular": "查询最受欢迎的产品（基于评论数量）",
    "top_rated_products": "查询评分最高的产品",
    # 产品扩展
    "products_price_range": "查询指定价格区间内的产品 价格筛选 1000到5000 多少钱 预算 价位 价格范围 价格在多少之间",
    "products_by_supplier": "查询特定供应商提供的所有产品",
    "expensive_products": "查询价格最高的前10个产品",
    "products_discontinued": "查询已停产的产品",
    "products_needing_reorder": "查询需要补货的产品（库存低于再订货水平）",
    # 类别
    "all_categories": "查询所有产品类别",
    "category_products": "查询特定类别下的产品",
    "category_product_count": "查询每个类别包含的产品数量",
    # 智能家居
    "smart_home_products": "查询所有智能家居产品 智能空调 智能冰箱 智能洗衣机 智能灯具 智能门锁 智能摄像头 各类智能电子产品列表 有哪些智能产品 列出产品信息",
    "cheap_products": "查询低于指定价格的产品",
    # 订单
    "order_by_id": "查询特定订单的完整信息（日期、运费、包含的产品）",
    "order_details": "查询订单包含的产品明细（数量、单价、折扣）",
    "recent_orders": "查询最近10个订单",
    "pending_orders": "查询尚未发货的订单",
    "orders_by_date_range": "查询指定日期范围内的订单",
    "orders_by_country": "查询发往特定国家的订单",
    "high_freight_orders": "查询运费高于指定金额的订单",
    "customer_search_orders": "按客户名称查询订单",
    # 客户
    "customer_by_name": "通过名称查询客户信息",
    "customer_orders": "查询特定客户的订单历史",
    "customers_by_country": "查询特定国家的客户",
    "customers_by_city": "查询特定城市的客户",
    "all_customers": "查询所有客户列表",
    # 供应商
    "supplier_products": "查询特定供应商提供的产品",
    "all_suppliers": "查询所有供应商列表",
    "suppliers_by_country": "查询特定国家的供应商",
    # 物流
    "order_shipping": "查询订单的物流公司信息",
    "shipper_list": "查询所有物流公司",
    "shipper_orders": "查询物流公司承运的所有订单",
    # 评价
    "product_reviews": "查询特定产品的用户评价",
    "customer_reviews": "查询特定客户的评价历史",
    "low_rated_reviews": "查询低评分评价（低于指定分数）",
    "recent_reviews": "查询最新评价",
    # 销售分析
    "category_sales": "查询各类别的销售总额",
    "product_sales": "查询产品销量排行榜",
    "customer_total_spending": "查询特定客户的累计消费金额和订单数",
    "sales_trend": "查询指定日期范围内的每日销售趋势",
    # 员工
    "employee_list": "查询所有员工信息",
    "employee_orders": "查询特定员工处理的订单",
    "employee_subordinates": "查询某位员工的下属",
    "employees_by_title": "按职位查询员工",
    "employee_details": "查询特定员工的详细信息（住址、电话、生日等）",
    # 数据总览
    "employee_sales_performance": "查询员工的销售业绩排名",
    "inventory_summary": "查询库存总览（总库存、在途、均价）",

    # 产品详情
    "product_detail": "查询产品的详细卖点、规格参数、适用场景和功能介绍",
    "product_specs": "查询产品的技术规格和参数",
    "product_features": "查询产品的主要卖点和功能介绍",
    # FAQ
    "faq_search": "搜索常见问题和答案 退换货 保修 配送 支付 使用说明",
    "faq_by_category": "查询特定类别的常见问题 下单配送 退换货 保修售后 产品使用 支付开票",
    "all_faqs": "查询所有常见问题列表",
    # 售后政策
    "after_sales_policy": "查询售后政策 退换货 保修 配送说明",
    "return_policy": "查询退换货政策和退货流程",
    "warranty_policy": "查询产品保修政策和保修期限",
    "shipping_policy": "查询配送说明和发货时效",

    # 关联推荐
    "also_bought": "查询购买某产品的客户还买了什么",
}
