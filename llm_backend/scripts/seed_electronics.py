"""
一键生成电子产品客服 Demo 数据 — Neo4j + Milvus
用法: python scripts/seed_electronics.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from pymilvus import MilvusClient, DataType, FieldSchema, CollectionSchema
from app.core.config import settings

URI = settings.NEO4J_URL
USER = settings.NEO4J_USERNAME
PASSWORD = settings.NEO4J_PASSWORD
DATABASE = settings.NEO4J_DATABASE

MILVUS_HOST = settings.MILVUS_HOST
MILVUS_PORT = settings.MILVUS_PORT
OLLAMA_URL = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embed"
OLLAMA_MODEL = settings.OLLAMA_EMBEDDING_MODEL

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# ═══════════════════════════════════════════════════════════════════════════
# 产品数据 — 5 个品类，28 款产品
# ═══════════════════════════════════════════════════════════════════════════

PRODUCTS = [
    # ── 智能手机 (6) ──
    ("小米 14 Ultra", 5999, 85, "智能手机", "小米",
     "徕卡光学镜头，骁龙8Gen3，5300mAh大电池，支持90W有线+80W无线快充，IP68防水",
     "屏幕:6.73\"AMOLED 2K 120Hz, 存储:12+256GB, 相机:50MP徕卡四摄, 重量:224g"),
    ("华为 Mate 70 Pro", 6999, 40, "智能手机", "华为",
     "麒麟9000S芯片，XMAGE影像，北斗卫星消息，4750mAh电池，HarmonyOS",
     "屏幕:6.82\"OLED 120Hz, 存储:12+512GB, 相机:50MP可变光圈, 重量:225g"),
    ("iPhone 16 Pro", 7999, 60, "智能手机", "苹果",
     "A18 Pro芯片，钛金属机身，4800万像素融合式相机，支持Apple Intelligence",
     "屏幕:6.3\"OLED 120Hz, 存储:8+256GB, 相机:48MP三摄, 重量:199g"),
    ("OPPO Find X7 Ultra", 4999, 100, "智能手机", "OPPO",
     "骁龙8Gen3，双潜望长焦，5000mAh电池，100W超级闪充，哈苏人像",
     "屏幕:6.82\"AMOLED 120Hz, 存储:12+256GB, 相机:50MP哈苏四摄, 重量:221g"),
    ("vivo X100 Pro", 4499, 120, "智能手机", "vivo",
     "天玑9300芯片，蔡司APO长焦，5400mAh蓝海电池，100W闪充，IP68",
     "屏幕:6.78\"AMOLED 120Hz, 存储:12+256GB, 相机:50MP蔡司三摄, 重量:225g"),
    ("荣耀 Magic6 Pro", 4699, 75, "智能手机", "荣耀",
     "骁龙8Gen3，5600mAh青海湖电池，卫星通信，80W快充，IP68",
     "屏幕:6.8\"OLED 120Hz, 存储:12+256GB, 相机:50MP三摄, 重量:229g"),

    # ── 笔记本 (6) ──
    ("MacBook Pro 14 M4", 12999, 30, "笔记本", "苹果",
     "M4 Pro芯片，Liquid Retina XDR屏，18小时续航，雷雳5接口",
     "屏幕:14.2\" 3024x1964, 存储:18+512GB SSD, 重量:1.6kg, 厚度:15.5mm"),
    ("ThinkPad X1 Carbon Gen12", 10999, 25, "笔记本", "联想",
     "酷睿Ultra 7，14英寸2.8K OLED，32GB内存，碳纤维机身仅1.09kg",
     "屏幕:14\" 2.8K OLED, 存储:32+1TB SSD, 重量:1.09kg, 接口:2×USB-C+HDMI"),
    ("华为 MateBook X Pro", 8999, 45, "笔记本", "华为",
     "酷睿Ultra 9，14.2英寸OLED触控屏，超级终端多屏协同，1.26kg",
     "屏幕:14.2\" 3.1K OLED触控, 存储:16+1TB SSD, 重量:1.26kg, 快充:90W"),
    ("ROG 幻16 Air", 11999, 20, "笔记本", "ROG",
     "酷睿Ultra 9+RTX4060，16英寸2.5K 240Hz，轻薄高性能，六扬声器",
     "屏幕:16\" 2.5K 240Hz, 存储:16+1TB SSD, GPU:RTX4060, 重量:1.85kg"),
    ("小米 RedmiBook Pro 16", 4999, 80, "笔记本", "小米",
     "酷睿Ultra 5，16英寸2.5K 120Hz，72Wh电池，澎湃智联",
     "屏幕:16\" 2.5K 120Hz, 存储:16+512GB SSD, 重量:1.88kg, 快充:100W"),
    ("戴尔 XPS 14", 9999, 35, "笔记本", "戴尔",
     "酷睿Ultra 7，14英寸3.2K OLED触控，无边框设计，CNC铝合金机身",
     "屏幕:14\" 3.2K OLED触控, 存储:16+512GB SSD, 重量:1.68kg, 接口:3×USB-C"),

    # ── 真无线耳机 (5) ──
    ("AirPods Pro 3", 1899, 150, "真无线耳机", "苹果",
     "H3芯片，自适应降噪，通透模式，6小时续航+30小时总续航，USB-C充电盒",
     "驱动单元:定制高振幅, 降噪:自适应主动降噪, 防水:IP54, 重量:5.3g/只"),
    ("华为 FreeBuds Pro 4", 1199, 120, "真无线耳机", "华为",
     "麒麟A2芯片，智慧动态降噪，空间音频，Hi-Res认证，星闪连接",
     "降噪:智慧动态降噪3.0, 续航:6.5h+30h总, 防水:IP54, 充电:无线+有线"),
    ("索尼 WF-1000XM6", 1699, 90, "真无线耳机", "索尼",
     "集成处理器V2+QN2e降噪，LDAC高解析，Hi-Res，8h续航+24h总",
     "降噪:双芯片降噪, 续航:8h+24h总, 防水:IPX4, 音频:LDAC/SBC/AAC"),
    ("小米 Buds 5 Pro", 699, 200, "真无线耳机", "小米",
     "HiFi双单元，52dB主动降噪，空间音频，38h超长续航",
     "降噪:52dB ANC, 续航:10h+38h总, 防水:IP55, 快充:5分钟=2小时"),
    ("OPPO Enco Free4", 499, 180, "真无线耳机", "OPPO",
     "丹拿联合调音，LDAC高清传输，49dB降噪，空间音效",
     "降噪:49dB ANC, 续航:7h+28h总, 防水:IP55, 蓝牙:5.4"),

    # ── 平板电脑 (4) ──
    ("iPad Pro M4 11\"", 6799, 40, "平板电脑", "苹果",
     "M4芯片，Ultra Retina XDR屏，5.1mm超薄机身，支持Apple Pencil Pro",
     "屏幕:11\" Tandem OLED, 存储:8+256GB, 重量:444g, 接口:USB-C 4.0"),
    ("华为 MatePad Pro 13.2", 5499, 35, "平板电脑", "华为",
     "麒麟9000S，13.2英寸OLED柔性屏，天生会画，PC级WPS办公",
     "屏幕:13.2\" 2.8K OLED 144Hz, 存储:12+512GB, 重量:580g, 快充:88W"),
    ("小米平板 7 Pro", 2999, 70, "平板电脑", "小米",
     "骁龙8Gen2，12.4英寸3K 144Hz屏，澎湃OS，磁吸键盘+触控笔",
     "屏幕:12.4\" 3K 144Hz, 存储:8+256GB, 电池:10000mAh, 快充:120W"),
    ("三星 Tab S10 Ultra", 8999, 20, "平板电脑", "三星",
     "天玑9300+，14.6英寸Dynamic AMOLED，S Pen，Galaxy AI",
     "屏幕:14.6\" AMOLED 120Hz, 存储:12+512GB, 重量:718g, 防水:IP68"),

    # ── 智能手表 (5) ──
    ("Apple Watch Ultra 3", 6499, 45, "智能手表", "苹果",
     "S9芯片，49mm钛合金表壳，精确双频GPS，100米防水，36h续航",
     "屏幕:49mm OLED 2000nit, 防水:100m WR100, 传感器:心率+血氧+体温+深度计"),
    ("华为 Watch GT 5 Pro", 2699, 80, "智能手表", "华为",
     "钛合金表圈，AMOLED高清屏，14天续航，高尔夫模式，IP69K",
     "屏幕:1.43\" AMOLED 466x466, 续航:14天, 防水:5ATM, 卫星定位"),
    ("小米 Watch S4", 1099, 120, "智能手表", "小米",
     "1.43\"AMOLED，15天续航，eSIM独立通话，150+运动模式，澎湃OS",
     "屏幕:1.43\" AMOLED 466x466, 续航:15天, 防水:5ATM, eSIM:支持"),
    ("OPPO Watch 5 Pro", 1999, 60, "智能手表", "OPPO",
     "骁龙W5 Gen2，双曲面AMOLED，独立eSIM，80+运动模式，VOOC闪充",
     "屏幕:1.91\" AMOLED 378x496, 续航:5天(全智能), 防水:5ATM"),
    ("三星 Galaxy Watch7", 2399, 55, "智能手表", "三星",
     "Exynos W1000，3nm芯片，BioActive传感器，Wear OS 5，40h续航",
     "屏幕:1.5\" Super AMOLED 480x480, 续航:40h, 防水:5ATM+IP68"),

    # ── 充电配件 (4) ──
    ("Anker 氮化镓充电器 65W", 129, 300, "充电配件", "Anker",
     "GaN氮化镓技术，65W大功率，三口输出，支持PD/QC快充协议",
     "功率:65W(max), 接口:2×USB-C+1×USB-A, 协议:PD3.0/QC4+, 重量:105g"),
    ("小米 磁吸无线充电宝", 199, 200, "充电配件", "小米",
     "MagSafe磁吸，5000mAh，15W无线+20W有线，LED电量显示",
     "容量:5000mAh, 无线:15W, 有线:20W, 接口:USB-C, 重量:130g"),
    ("绿联 Type-C 扩展坞 12合1", 399, 90, "充电配件", "绿联",
     "12合1全能扩展，HDMI 4K@60Hz，千兆网口，SD/TF读卡，PD100W",
     "接口:HDMI+DP+VGA+USB-A×4+USB-C PD+千兆网口+SD+TF+3.5mm"),
    ("贝尔金 无线充电座 3合1", 349, 70, "充电配件", "贝尔金",
     "iPhone+Apple Watch+AirPods三合一，MagSafe认证，15W快充",
     "充电:iPhone 15W+Watch 5W+AirPods 5W, 输入:USB-C, 重量:480g"),
]

# ═══════════════════════════════════════════════════════════════════════════
# 评价数据
# ═══════════════════════════════════════════════════════════════════════════

REVIEWS = [
    ("小米 14 Ultra", "张先生", 5, "拍照真的绝了，徕卡调色很舒服，长焦拍演唱会无敌，续航也顶", "2025-03-15"),
    ("小米 14 Ultra", "李女士", 4, "手感比上代好很多，系统流畅，就是价格涨了不少", "2025-02-20"),
    ("小米 14 Ultra", "王同学", 5, "打原神全高画质稳60帧不发烫，徕卡影调拍照很出片", "2025-04-01"),
    ("华为 Mate 70 Pro", "陈先生", 5, "麒麟回归！HarmonyOS太流畅了，卫星消息户外很实用", "2025-01-10"),
    ("华为 Mate 70 Pro", "刘女士", 4, "信号是真的强，地下室都有信号。拍照色彩偏真实", "2025-02-28"),
    ("iPhone 16 Pro", "赵先生", 5, "A18 Pro性能怪兽，钛金属手感绝了，就是贵", "2025-03-20"),
    ("iPhone 16 Pro", "孙女士", 3, "升级不大，跟15 Pro区别不明显，灵动岛还是一样", "2025-04-05"),
    ("OPPO Find X7 Ultra", "周先生", 5, "双潜望长焦太实用了，3倍6倍切换丝滑，哈苏人像绝", "2025-02-15"),
    ("MacBook Pro 14 M4", "吴先生", 5, "M4 Pro性能炸裂，剪4K视频丝滑，XDR屏色准无敌", "2025-01-25"),
    ("MacBook Pro 14 M4", "郑女士", 4, "续航真的18小时，一天不用充电。就是接口还是太少", "2025-03-10"),
    ("ThinkPad X1 Carbon Gen12", "冯先生", 5, "1.09kg背着上班太爽了，键盘手感依然是ThinkPad水准", "2025-02-01"),
    ("华为 MateBook X Pro", "褚先生", 5, "超级终端联动手机太方便了，触控屏拖拽文件效率拉满", "2025-03-05"),
    ("ROG 幻16 Air", "卫先生", 4, "轻薄又能打游戏，240Hz刷新玩CS2丝滑，就是风扇声大", "2025-01-18"),
    ("小米 RedmiBook Pro 16", "蒋同学", 5, "4999买到16寸2.5K屏太值了，学生党福音", "2025-04-02"),
    ("AirPods Pro 3", "韩先生", 5, "降噪比上代更强了，地铁里几乎听不到杂音，佩戴舒服", "2025-02-10"),
    ("华为 FreeBuds Pro 4", "杨女士", 5, "星闪连接稳定性吊打蓝牙，耳机盒能当遥控器用太秀了", "2025-03-22"),
    ("索尼 WF-1000XM6", "朱先生", 5, "音质TWS天花板，LDAC听无损爽，降噪也顶", "2025-01-30"),
    ("小米 Buds 5 Pro", "秦同学", 5, "699做到52dB降噪+HIFI音质，性价比炸裂", "2025-04-08"),
    ("iPad Pro M4 11\"", "许先生", 5, "M4跑达芬奇调色丝滑，Tandem OLED黑位纯黑，画画神器", "2025-02-18"),
    ("华为 MatePad Pro 13.2", "何女士", 5, "13.2寸看电影办公都很爽，天生会画APP比Procreate还好用", "2025-03-28"),
    ("小米平板 7 Pro", "吕同学", 4, "性价比高，看网课做笔记够用，就是手写笔延迟比iPad大一点", "2025-04-10"),
    ("Apple Watch Ultra 3", "施先生", 5, "潜水深度计准确，双频GPS越野跑轨迹精准，钛合金很耐刮", "2025-01-08"),
    ("华为 Watch GT 5 Pro", "张先生", 5, "高尔夫模式太专业了，14天续航服气，蓝宝石表镜防刮", "2025-03-12"),
    ("小米 Watch S4", "王同学", 5, "千元就能eSIM独立通话，跑步不用带手机，续航15天", "2025-02-25"),
    ("Anker 氮化镓充电器 65W", "李女士", 5, "出差只带这一个就够了，电脑手机耳机一起充，体积小", "2025-03-01"),
    ("小米 磁吸无线充电宝", "刘先生", 4, "磁吸牢固甩不掉，无线15W够用，就是容量小了点", "2025-04-05"),
]

# ═══════════════════════════════════════════════════════════════════════════
# FAQ 数据
# ═══════════════════════════════════════════════════════════════════════════

FAQS = [
    ("下单配送", "下单后多久发货？", "现货产品下单后24小时内发货，预定产品以页面标注时间为准。发货后会短信通知运单号。"),
    ("下单配送", "配送需要多久？", "标准配送2-5天，加急配送次日达或隔日达（额外收费）。具体以收货地址和物流为准。"),
    ("退换货", "支持7天无理由退货吗？", "支持。自签收之日起7天内，商品完好、配件齐全、包装完整可申请退货。已拆封的耳机/手表等个人健康类产品需经检测确认。"),
    ("退换货", "退货流程怎么操作？", "APP内发起退货→选择原因→审核（1-2小时）→自行寄回或上门取件→仓库验收→1-3个工作日退款。"),
    ("退换货", "收到货有质量问题怎么办？", "签收24小时内联系客服，上传照片/视频。确认质量问题后免费换新，旧件由快递员上门取回。"),
    ("保修售后", "保修期多久？", "手机/笔记本保修1年，耳机/手表/平板保修1年，配件保修6个月。保修期内非人为损坏免费维修。"),
    ("保修售后", "如何申请保修？", "联系在线客服或拨打400售后热线，提供订单号和故障描述。客服安排就近维修点或寄修服务。"),
    ("保修售后", "保修需要什么凭证？", "电子发票或订单号即可。无需纸质发票，系统会自动关联您的购买记录。"),
    ("价格活动", "价格保护政策", "签收7天内如商品降价，可申请退还差价。限官方自营商品，不包含秒杀/限时抢购。"),
    ("价格活动", "以旧换新怎么操作？", "APP选择以旧换新→在线估价→寄出旧机→质检确认→差价购买新机。部分机型支持上门回收。"),
    ("支付方式", "支持哪些支付方式？", "微信支付、支付宝、银行卡、信用卡分期（3/6/12期）、花呗分期。大额订单可对公转账。"),
    ("支付方式", "如何开发票？", "下单时可选择电子发票或纸质发票。电子发票确认收货后自动发送到邮箱，纸质发票随货寄出。"),
    ("账号会员", "会员有什么权益？", "银卡会员98折、金卡会员95折、钻石会员92折。积分可抵扣现金，100积分=1元。"),
    ("账号会员", "积分怎么获得？", "消费1元=1积分，写评价奖励50-200积分，签到奖励每日5积分。积分有效期1年。"),
]

# ═══════════════════════════════════════════════════════════════════════════
# 售后政策
# ═══════════════════════════════════════════════════════════════════════════

POLICIES = [
    ("退换货政策", """
1. 7天无理由退货：自签收之日起7天内，商品完好、配件齐全、包装完整可申请退货。
2. 以下商品不支持无理由退货：已拆封的耳机/手表/手环等个人健康类产品。
3. 15天内质量问题换货：签收15天内出现非人为质量问题的，可申请换新。
4. 退回运费：质量问题由商家承担，无理由退货由买家承担。
5. 退款时效：仓库验收后1-3个工作日原路退回。
6. 换货时效：收到退回商品后1-2个工作日发出新货。
    """),
    ("保修政策", """
1. 手机/笔记本：保修1年。
2. 平板/耳机/手表：保修1年。
3. 充电配件：保修6个月。
4. Apple产品：全国联保，直营店和授权服务商均可维修。
5. 保修范围：非人为因素导致的产品故障。
6. 不保修范围：人为损坏、私自拆卸、进水、自然灾害、正常磨损。
7. 保修方式：线上申请→客服确认→寄修或到店维修。
    """),
    ("配送说明", """
1. 发货时间：工作日15:00前下单当天发货，之后次日发货。周末订单周一发货。
2. 配送时效：标准快递2-5天，加急1-2天（额外收费）。
3. 物流追踪：发货后短信通知运单号，APP可实时查看物流状态。
4. 签收须知：当面验收，发现包装破损/商品损坏请拒收并联系客服。
5. 运费标准：满99元包邮，不满99元运费8元起。
    """),
    ("价格保护", """
1. 签收7天内如商品降价，可申请退还差价。价保存在我的订单→申请价保。
2. 不适用范围：秒杀、限时抢购、百亿补贴、优惠券折扣。
3. 价保金额以实际支付金额与降价后价格的差额为准。
    """),
]


# ═══════════════════════════════════════════════════════════════════════════

def clear_neo4j():
    """清空 Neo4j 数据库"""
    with driver.session(database=DATABASE) as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("  Neo4j 已清空")


def import_products():
    """导入产品 + ProductDetail 节点"""
    with driver.session(database=DATABASE) as session:
        for name, price, stock, category, brand, desc, specs in PRODUCTS:
            session.run("""
                CREATE (p:Product {
                    ProductName: $name, UnitPrice: $price, UnitsInStock: $stock,
                    CategoryName: $category, BrandName: $brand
                })
                CREATE (d:ProductDetail {
                    KeyFeatures: $desc, Specifications: $specs
                })
                CREATE (p)-[:HAS_DETAIL]->(d)
            """, name=name, price=price, stock=stock, category=category, brand=brand, desc=desc, specs=specs)
    print(f"  导入 {len(PRODUCTS)} 款产品 + ProductDetail")


def import_reviews():
    """导入产品评价"""
    with driver.session(database=DATABASE) as session:
        for product_name, reviewer, rating, text, date in REVIEWS:
            session.run("""
                MATCH (p:Product {ProductName: $name})
                CREATE (r:Review {
                    CustomerName: $reviewer, Rating: $rating,
                    ReviewText: $text, ReviewDate: $date
                })
                CREATE (p)<-[:ABOUT]-(r)
            """, name=product_name, reviewer=reviewer, rating=rating, text=text, date=date)
    print(f"  导入 {len(REVIEWS)} 条评价")


def import_orders():
    """创建几笔示例订单"""
    orders = [
        (1001, "张三", "2025-05-01", "2025-05-03", ["小米 14 Ultra", "Anker 氮化镓充电器 65W"]),
        (1002, "李四", "2025-05-02", None, ["AirPods Pro 3"]),
        (1003, "王五", "2025-05-04", "2025-05-06", ["MacBook Pro 14 M4", "绿联 Type-C 扩展坞 12合1"]),
        (1004, "赵六", "2025-05-05", None, ["华为 FreeBuds Pro 4", "小米 磁吸无线充电宝"]),
        (1005, "孙七", "2025-05-08", "2025-05-10", ["iPad Pro M4 11\"", "Apple Watch Ultra 3"]),
    ]
    with driver.session(database=DATABASE) as session:
        for oid, customer, order_date, shipped_date, product_names in orders:
            shipped = shipped_date if shipped_date else "未发货"
            session.run("""
                CREATE (o:Order {
                    orderId: $oid, CustomerName: $customer,
                    OrderDate: $order_date, ShippedDate: $shipped,
                    ShipName: $customer, ShipAddress: '北京市朝阳区科技园路88号',
                    ShipCity: '北京', ShipCountry: '中国', Freight: 15.0
                })
            """, oid=oid, customer=customer, order_date=order_date, shipped=shipped)
            for pname in product_names:
                session.run("""
                    MATCH (o:Order {orderId: $oid})
                    MATCH (p:Product {ProductName: $pname})
                    CREATE (o)-[:CONTAINS {Quantity: 1, UnitPrice: p.UnitPrice}]->(p)
                """, oid=oid, pname=pname)
    print(f"  导入 {len(orders)} 笔订单")


def import_faq_and_policies():
    """导入 FAQ 和售后政策"""
    with driver.session(database=DATABASE) as session:
        for cat, q, a in FAQS:
            session.run("""
                CREATE (f:FAQ {category: $cat, question: $q, answer: $a})
            """, cat=cat, q=q, a=a)
        for i, (title, content) in enumerate(POLICIES):
            session.run("""
                CREATE (p:AfterSalesPolicy {policyId: $id, policyType: $title, content: $content})
            """, id=f"POL-{i+1:03d}", title=title, content=content)
    print(f"  导入 {len(FAQS)} 条FAQ + {len(POLICIES)} 条政策")


def embed_texts(texts: list[str]) -> list:
    """调用 Ollama 批量向量化"""
    import requests
    r = requests.post(OLLAMA_URL, json={"model": OLLAMA_MODEL, "input": texts})
    r.raise_for_status()
    return r.json()["embeddings"]


def setup_milvus():
    """重建 product_descriptions 集合并导入产品向量"""
    import requests
    milvus = MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}")

    collection = "product_descriptions"
    if milvus.has_collection(collection):
        milvus.drop_collection(collection)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="product_name", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="price", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
    ]
    schema = CollectionSchema(fields=fields, description="电子产品语义搜索")
    milvus.create_collection(
        collection_name=collection, schema=schema,
        dimension=1024, metric_type="COSINE",
    )
    idx_params = milvus.prepare_index_params()
    idx_params.add_index(field_name="vector", index_type="IVF_FLAT", metric_type="COSINE", params={"nlist": 128})
    milvus.create_index(collection_name=collection, index_params=idx_params)
    milvus.load_collection(collection)

    # 向量化产品描述并插入
    texts = [f"{p[0]} {p[6]} {p[3]}" for p in PRODUCTS]  # name + desc + category
    vectors = embed_texts(texts)
    data = []
    for i, (name, price, stock, category, brand, desc, specs) in enumerate(PRODUCTS):
        data.append({
            "product_name": name,
            "description": f"{desc} | {specs}",
            "price": str(price),
            "category": category,
            "vector": vectors[i],
        })
    milvus.insert(collection_name=collection, data=data)
    milvus.flush(collection_name=collection)
    print(f"  Milvus 导入 {len(data)} 条向量到 '{collection}'")


def main():
    print("=== 清空 Neo4j ===")
    clear_neo4j()

    print("\n=== 导入产品 ===")
    import_products()

    print("\n=== 导入评价 ===")
    import_reviews()

    print("\n=== 导入订单 ===")
    import_orders()

    print("\n=== 导入 FAQ + 政策 ===")
    import_faq_and_policies()

    # 统计 Neo4j
    with driver.session(database=DATABASE) as session:
        r = session.run("MATCH (n) RETURN count(n) AS c")
        nc = r.single()["c"]
        r = session.run("MATCH ()-[r]->() RETURN count(r) AS c")
        rc = r.single()["c"]
        print(f"\n=== Neo4j: {nc} 节点, {rc} 关系 ===")
        for label in ["Product", "Review", "Order", "FAQ", "AfterSalesPolicy", "ProductDetail"]:
            r = session.run(f"MATCH (n:{label}) RETURN count(n) AS c")
            print(f"  {label}: {r.single()['c']}")

    print("\n=== 导入 Milvus ===")
    try:
        setup_milvus()
    except Exception as e:
        print(f"  Milvus 导入失败（服务可能未启动）: {e}")

    driver.close()
    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
