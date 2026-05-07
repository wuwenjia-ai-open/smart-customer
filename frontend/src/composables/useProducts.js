import { ref, computed } from 'vue'

const PRODUCTS = [
  {cat:'智能照明',name:'华为智选智能灯泡 E27',price:49.9,stock:200,desc:'语音控制，亮度色温可调，E27 标准接口即装即用',w:'1年寄修'},
  {cat:'智能照明',name:'小米米家 LED 智能灯带',price:79,stock:150,desc:'1600 万色可选，APP 分组控制，背面自带 3M 胶',w:'1年寄修'},
  {cat:'智能照明',name:'天猫精灵智能吸顶灯',price:299,stock:80,desc:'语音调光调色，简约圆形设计，适用 15-20㎡ 卧室客厅',w:'2年寄修'},
  {cat:'智能照明',name:'小度智能台灯 Pro',price:159,stock:120,desc:'国 AA 级护眼认证，智能调光，学生阅读首选',w:'1年寄修'},
  {cat:'智能安防',name:'萤石 C6C 智能摄像头',price:299,stock:100,desc:'2K 超清画质，AI 人形检测，双向语音通话，云台旋转',w:'2年上门'},
  {cat:'智能安防',name:'小米智能门锁 Pro',price:1299,stock:60,desc:'指纹+密码+APP+NFC，七种开锁方式，C 级锁芯',w:'3年上门'},
  {cat:'智能安防',name:'华为智选门窗传感器',price:69,stock:300,desc:'小巧灵敏，开门即亮灯，支持全屋智能场景联动',w:'1年寄修'},
  {cat:'智能安防',name:'萤石智能门铃',price:399,stock:85,desc:'2K 可视对讲，移动侦测告警，远程实时通话',w:'2年上门'},
  {cat:'智能音箱',name:'天猫精灵 X5 智能音箱',price:499,stock:120,desc:'Hi-Fi 级音质，全屋智能设备语音控制中枢，支持 200+ 品牌',w:'2年寄修'},
  {cat:'智能音箱',name:'小度智能屏 Air',price:699,stock:90,desc:'8 英寸高清触屏，视频通话、追剧、智能家居三合一',w:'2年寄修'},
  {cat:'智能音箱',name:'小米小爱音箱 Pro',price:299,stock:200,desc:'DTS 专业调音，全屋设备控制流畅，性价比之王',w:'1年寄修'},
  {cat:'智能音箱',name:'华为 Sound X 智能音箱',price:899,stock:50,desc:'帝瓦雷联合调音，Hi-Res 认证，高端旗舰音质',w:'2年寄修'},
  {cat:'智能厨电',name:'小米米家智能电饭煲 4L',price:399,stock:100,desc:'IH 电磁加热，APP 预约煮饭，24 小时定时保温',w:'2年寄修'},
  {cat:'智能厨电',name:'华为智选智能洗碗机',price:2999,stock:30,desc:'高温除菌洗，节能静音，13 套大容量嵌入式安装',w:'3年上门'},
  {cat:'智能厨电',name:'天猫精灵智能烤箱 30L',price:599,stock:70,desc:'智能菜谱一键操作，上下独立控温，烘焙新手福音',w:'2年寄修'},
  {cat:'智能清洁',name:'石头 G20 扫地机器人',price:3999,stock:40,desc:'AI 结构光避障，5500Pa 飓风吸力，自动洗烘拖布',w:'3年上门'},
  {cat:'智能清洁',name:'小米米家扫拖机器人 2',price:1699,stock:80,desc:'LDS 激光导航，扫拖一体，5200mAh 超长续航',w:'2年寄修'},
  {cat:'智能清洁',name:'石头 P10 Pro 扫地机',price:2999,stock:55,desc:'自动集尘 60 天不倒垃圾，全链路自清洁，APP 远程控制',w:'3年上门'},
  {cat:'智能温控',name:'小米米家智能温控器',price:199,stock:150,desc:'精准控温 ±0.5°C，联动空调地暖新风，节能 30%',w:'1年寄修'},
  {cat:'智能温控',name:'华为智选智能空调伴侣',price:89,stock:200,desc:'让传统空调秒变智能，远程开关+语音控制+定时',w:'1年寄修'},
]

const CATS = [...new Set(PRODUCTS.map(p => p.cat))]

const selectedCategory = ref('')

const filteredProducts = computed(() =>
  selectedCategory.value ? PRODUCTS.filter(p => p.cat === selectedCategory.value) : PRODUCTS
)

function selectCategory(cat) {
  selectedCategory.value = selectedCategory.value === cat ? '' : cat
}

export function useProducts() {
  return { PRODUCTS, CATS, selectedCategory, filteredProducts, selectCategory }
}
