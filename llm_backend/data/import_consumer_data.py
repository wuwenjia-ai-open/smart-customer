"""
导入消费者向数据：ProductDetail、FAQ、AfterSalesPolicy
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from neo4j import GraphDatabase
from app.core.config import settings

URI = settings.NEO4J_URL
USER = settings.NEO4J_USERNAME
PASSWORD = settings.NEO4J_PASSWORD
DATABASE = settings.NEO4J_DATABASE

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def import_product_details():
    """为每款产品添加详细卖点"""
    details = [
        ("谷歌 智能空调 Basic", "冷暖变频",
         "制冷功率:3500W,制热功率:4000W,适用面积:20-35㎡,能效等级:一级,噪音:22dB",
         "卧室、客厅", "谷歌生态联动，语音控制温度，AI学习你的使用习惯自动调温"),
        ("索尼 智能空气净化器 Advanced", "HEPA H13+活性炭",
         "CADR:500m³/h,适用面积:60㎡,噪音:18-50dB,滤网寿命:12个月,PM2.5检测",
         "新装修房屋、过敏人群、宠物家庭", "索尼独有激光传感器，实时显示空气质量，夜间自动静音模式"),
        ("小米 智能冰箱 Elite", "风冷无霜+变频",
         "容量:450L,冷藏:280L,冷冻:170L,能效:一级,智联米家APP,门板触控屏",
         "3-5人家庭", "手机远程调温，食材过期提醒，AI菜谱推荐，门板看菜谱/听歌"),
        ("西门子 智能冰箱 Elite", "混冷双循环",
         "容量:502L,零度保鲜:105L,能效:一级,噪音:38dB,iSensoric智感",
         "4-6人家庭、对食材保鲜要求高", "德国精工，零度生物保鲜蔬菜两周不蔫，独立双循环不串味"),
        ("博世 智能手环 Ultra", "AMOLED屏+血氧+GPS",
         "屏幕:1.47\"AMOLED,续航:14天,防水:5ATM,传感器:心率+血氧+加速度",
         "运动健身、健康监测", "109种运动模式，睡眠阶段分析，压力监测，女性健康管理"),
        ("松下 智能手环 Advanced", "1.1\"TFT+心率",
         "屏幕:1.1\"彩色TFT,续航:7天,防水:IP67,传感器:心率+加速度",
         "日常计步、基础健康监测", "入门款手环，消息通知不漏接，超轻14g佩戴无感"),
        ("谷歌 智能门锁 Standard", "指纹+密码+APP六合一",
         "开锁方式:指纹/密码/APP/钥匙/NFC/临时密码,指纹容量:100枚,适用门厚:40-120mm",
         "家庭防盗门、出租房管理", "谷歌安全芯片加密，虚位密码防偷窥，APP实时开锁记录，电池用1年"),
        ("索尼 智能插座 Standard", "WiFi+电量统计",
         "最大功率:2500W,电压:220V,WiFi:2.4GHz,定时/倒计时/循环",
         "远程控制家电、定时充电、省电", "App远程开关，电量统计看设备耗电，语音控制，过载自动断电保护"),
        ("亚马逊 智能空气净化器 Pro", "三合一滤网+负离子",
         "CADR:450m³/h,适用面积:50㎡,噪音:20-52dB,负离子:500万/cm³",
         "卧室、办公室、母婴房", "亚马逊Alexa语音控制，睡眠模式显示屏自动熄灭，滤网更换提醒"),
        ("松下 智能洗衣机 Elite", "变频直驱+蒸汽除菌",
         "容量:10kg,转速:1400转,能效:一级,功能:蒸汽洗/除菌/除螨/快洗/羊毛",
         "家庭日常洗衣、母婴衣物", "松下泡沫发生技术，洗净比1.08，蒸汽除菌99.9%，APP远程预约洗衣"),
    ]

    with driver.session(database=DATABASE) as session:
        for product_name, features, specs, scene, desc in details:
            session.run("""
                MATCH (p:Product {ProductName: $name})
                CREATE (d:ProductDetail {
                    KeyFeatures: $features,
                    Specifications: $specs,
                    SuitableFor: $scene,
                    Description: $desc
                })
                CREATE (p)-[:HAS_DETAIL]->(d)
            """, name=product_name, features=features, specs=specs, scene=scene, desc=desc)
        print(f"  Imported {len(details)} ProductDetail nodes")


def import_faq():
    """常见消费者问题"""
    faqs = [
        ("下单配送", "下单后多久能发货？", "一般情况下，下单后24小时内安排发货。定制产品或大型家电发货时间为3-5个工作日。发货后会短信通知您快递单号。"),
        ("下单配送", "支持哪些配送方式？", "我们与顺丰速运、圆通速递等多家物流公司合作，支持标准快递和加急配送。标准配送3-7天到达，加急配送1-3天。"),
        ("下单配送", "可以配送到哪些地区？", "目前覆盖全国主要城市。偏远地区可能需要额外3-5天。下单时系统会自动计算是否支持配送。"),
        ("退换货", "退货政策是什么？", "支持7天无理由退货。要求商品完好、配件齐全、包装完整。定制产品和已拆封的个人护理产品不支持无理由退货。"),
        ("退换货", "退货流程怎么操作？", "在APP/网站发起退货申请→审核通过→自行寄回或上门取件→仓库验收→退款到账。整个过程3-7个工作日。"),
        ("退换货", "换货怎么处理？", "收到货后如发现质量问题请联系客服，拍照片上传。确认质量问题后免费换新，旧件由快递员上门取回。"),
        ("保修售后", "产品保修期多久？", "大部分产品保修1年，大家电（冰箱/空调/洗衣机）保修3年。保修期内非人为损坏免费维修。"),
        ("保修售后", "如何申请保修？", "联系在线客服或拨打售后热线，提供订单号和问题描述。客服会安排就近维修点或上门服务。"),
        ("保修售后", "保修需要什么凭证？", "电子发票或订单记录即可作为保修凭证，无需纸质发票。"),
        ("产品使用", "智能设备怎么连接APP？", "下载对应品牌APP（谷歌Home/小米米家/亚马逊Alexa等），确保手机和设备在同一WiFi下，按照APP引导添加设备即可。"),
        ("产品使用", "智能空调多久清洗一次？", "建议每3个月清洗一次过滤网。用清水冲洗晾干即可。室外机建议每年请专业人员深度清洗一次。"),
        ("产品使用", "智能门锁没电了怎么办？", "门锁低电量时APP会提前提醒。如已耗尽可用充电宝通过USB应急接口供电开锁。建议每半年检查一次电量。"),
        ("支付开票", "支持哪些支付方式？", "支持微信支付、支付宝、银行卡、信用卡分期。大额订单可选择对公转账。"),
        ("支付开票", "如何开发票？", "下单时可选择开具电子发票或纸质发票。电子发票在确认收货后自动发送到邮箱，纸质发票随货寄出。"),
        ("支付开票", "发票内容可以修改吗？", "发票内容默认为购买商品明细。如需开具企业发票，下单时填写公司抬头和税号即可。"),
    ]

    with driver.session(database=DATABASE) as session:
        for i, (cat, q, a) in enumerate(faqs):
            session.run("""
                CREATE (f:FAQ {
                    faqId: $id,
                    category: $cat,
                    question: $q,
                    answer: $a
                })
            """, id=f"FAQ-{i+1:03d}", cat=cat, q=q, a=a)
        print(f"  Imported {len(faqs)} FAQ nodes")


def import_policies():
    """售后政策"""
    policies = [
        ("退换货政策", """
1. 7天无理由退货：自签收之日起7天内，商品完好、不影响二次销售可申请退货。
2. 15天内质量问题换货：签收15天内出现非人为质量问题的，可申请换货。
3. 以下商品不支持无理由退货：已拆封的个人护理产品、定制产品、已激活的软件。
4. 退回运费：质量问题由商家承担，无理由退货由买家承担。
5. 退款时效：仓库验收后1-3个工作日原路退回。
        """),
        ("保修政策", """
1. 智能小家电（手环、插座、门锁等）：保修1年。
2. 大家电（空调、冰箱、洗衣机）：保修3年，压缩机保修5年。
3. 保修范围：非人为因素导致的产品故障。
4. 不保修范围：人为损坏、私自拆卸、自然灾害、正常磨损。
5. 保修方式：线上申请→客服确认→就近维修点或上门服务。
        """),
        ("配送说明", """
1. 发货时间：工作日订单当天或次日发货，周末订单周一发货。
2. 配送时效：标准快递3-7天，加急1-3天（额外收费）。
3. 物流追踪：发货后短信通知运单号，可在APP实时查看物流状态。
4. 签收须知：务必当面验收，发现损坏请拒收并联系客服。
5. 运费标准：满99元包邮，不满99元运费10元起。
        """),
    ]

    with driver.session(database=DATABASE) as session:
        for i, (title, content) in enumerate(policies):
            session.run("""
                CREATE (p:AfterSalesPolicy {
                    policyId: $id,
                    policyType: $title,
                    content: $content
                })
            """, id=f"POL-{i+1:03d}", title=title, content=content)
        print(f"  Imported {len(policies)} AfterSalesPolicy nodes")


def main():
    print("=== Importing consumer-facing data ===")
    print("\n1. Product Details:")
    import_product_details()

    print("\n2. FAQ:")
    import_faq()

    print("\n3. After-Sales Policy:")
    import_policies()

    # Verify
    with driver.session(database=DATABASE) as session:
        for label in ["ProductDetail", "FAQ", "AfterSalesPolicy"]:
            r = session.run(f"MATCH (n:{label}) RETURN count(n) AS c")
            print(f"  {label}: {r.single()['c']}")

    driver.close()
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
