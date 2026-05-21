export const CATEGORIES = ['全部', '手机', '笔记本', '耳机', '平板', '手表']

export const PRODUCTS = [
  // ── 手机 ───────────────────────────────────────────────────
  {
    id: 1, name: 'iPhone 16 Pro Max', category: '手机', price: 9999, originalPrice: 10999,
    rating: 4.9, reviews: 2341, icon: '📱', badge: '热销',
    image: '/products/iphone-16-pro-max.jpg',
    imagePos: '70% center',
    gradient: 'linear-gradient(135deg, #1a1410 0%, #2a1f15 100%)',
    accent: '#D4B896', specs: 'A18 Pro 芯片 · 钛金属设计 · 4800 万 Pro 级摄像头 · 6.9 寸超视网膜 XDR 显示屏',
    tagline: '钛金属机身 · 专业摄影旗舰',
  },
  {
    id: 2, name: 'iPhone 16', category: '手机', price: 5999, originalPrice: null,
    rating: 4.7, reviews: 1823, icon: '📱', badge: '新品',
    gradient: 'linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%)',
    accent: '#E8B4A8', specs: 'A18 · 6.1寸 · 双摄 · 动态岛',
  },
  {
    id: 3, name: '小米 15 Ultra', category: '手机', price: 6499, originalPrice: 6999,
    rating: 4.8, reviews: 1456, icon: '📱', badge: '推荐',
    gradient: 'linear-gradient(135deg, #1a0a00 0%, #2d1200 100%)',
    accent: '#E8B4A8', specs: '骁龙 8 Gen 4 · 徕卡四摄 · 5410mAh',
  },
  {
    id: 4, name: '华为 Mate 70 Pro', category: '手机', price: 6999, originalPrice: null,
    rating: 4.8, reviews: 987, icon: '📱', badge: null,
    gradient: 'linear-gradient(135deg, #001a12 0%, #002a1c 100%)',
    accent: '#A8D8C8', specs: '麒麟 9020 · 卫星通话 · 可变光圈',
  },
  {
    id: 5, name: 'OPPO Find X8 Pro', category: '手机', price: 5999, originalPrice: null,
    rating: 4.7, reviews: 756, icon: '📱', badge: null,
    gradient: 'linear-gradient(135deg, #001a1a 0%, #002828 100%)',
    accent: '#A8D8C8', specs: '骁龙 8 Gen 4 · 哈苏相机 · IP69',
  },
  {
    id: 6, name: 'vivo X200 Pro', category: '手机', price: 4999, originalPrice: null,
    rating: 4.6, reviews: 634, icon: '📱', badge: null,
    gradient: 'linear-gradient(135deg, #0d001a 0%, #1a0033 100%)',
    accent: '#C8C5E0', specs: '骁龙 8 Gen 4 · 蔡司镜头 · 6000mAh',
  },
  // ── 笔记本 ──────────────────────────────────────────────────
  {
    id: 7, name: 'MacBook Pro 14 M4', category: '笔记本', price: 14999, originalPrice: 15999,
    rating: 4.9, reviews: 892, icon: '💻', badge: '旗舰',
    image: '/products/macbook-pro-m4.jpg',
    imagePos: '75% center',
    gradient: 'linear-gradient(135deg, #060606 0%, #181818 100%)',
    accent: '#A6A6AA', specs: 'M4 芯片 · Liquid 视网膜 XDR · 最长 24 小时续航 · 12MP Center Stage 摄像头',
    tagline: 'M4 芯片加持 · 全天候续航',
  },
  {
    id: 21, name: 'MacBook X Pro M4 Max', category: '笔记本', price: 24999, originalPrice: 26999,
    rating: 4.9, reviews: 423, icon: '💻', badge: '新品',
    image: '/products/macbook-x-pro.jpg',
    imagePos: '70% center',
    gradient: 'linear-gradient(135deg, #06070D 0%, #12141C 100%)',
    accent: '#C8C5E0', specs: 'M4 Max 芯片 · 16.2 寸 Liquid XDR · 最长 22 小时续航 · 六扬声器沉浸音响',
    tagline: 'M4 Max 性能巅峰 · 创作者首选',
  },
  {
    id: 8, name: 'MacBook Air M3', category: '笔记本', price: 9999, originalPrice: null,
    rating: 4.8, reviews: 1234, icon: '💻', badge: null,
    gradient: 'linear-gradient(135deg, #0a1628 0%, #0c1f3d 100%)',
    accent: '#E8B4A8', specs: 'M3 · 16GB · 18小时续航 · 1.24kg',
  },
  {
    id: 9, name: '联想拯救者 Y7000P', category: '笔记本', price: 4999, originalPrice: 5499,
    rating: 4.8, reviews: 2341, icon: '💻', badge: '性价比',
    gradient: 'linear-gradient(135deg, #1a0000 0%, #330000 100%)',
    accent: '#E8B4A8', specs: 'i7-13620H · RTX 4060 · 16GB · 165Hz',
  },
  {
    id: 10, name: 'ROG 幻 16', category: '笔记本', price: 13999, originalPrice: 14999,
    rating: 4.8, reviews: 1287, icon: '💻', badge: '游戏旗舰',
    image: '/products/rog-16.jpg',
    imagePos: '65% center',
    gradient: 'linear-gradient(135deg, #0a0612 0%, #1a0d28 100%)',
    accent: '#C8C5E0', specs: 'Intel Core Ultra 9 · RTX 4070 · 2.5K 240Hz OLED · 32GB LPDDR5X · 1TB SSD',
    tagline: '电竞性能 · 轻薄全能本',
  },
  {
    id: 11, name: 'ThinkPad X1 Carbon', category: '笔记本', price: 9999, originalPrice: null,
    rating: 4.7, reviews: 543, icon: '💻', badge: '商务',
    gradient: 'linear-gradient(135deg, #0a0a0a 0%, #141414 100%)',
    accent: '#E8B4A8', specs: 'i7-1365U · 32GB · 1.12kg · OLED',
  },
  // ── 耳机 ────────────────────────────────────────────────────
  {
    id: 12, name: 'AirPods Pro 2', category: '耳机', price: 1899, originalPrice: 1999,
    rating: 4.8, reviews: 3421, icon: '🎧', badge: '热销',
    gradient: 'linear-gradient(135deg, #0a0a0f 0%, #18181b 100%)',
    accent: '#f4f4f5', specs: 'H2芯片 · 主动降噪 · 6+30h 续航',
  },
  {
    id: 13, name: '索尼 WH-1000XM5', category: '耳机', price: 2499, originalPrice: 2999,
    rating: 4.9, reviews: 2156, icon: '🎧', badge: '推荐',
    gradient: 'linear-gradient(135deg, #0f0f14 0%, #1a1a24 100%)',
    accent: '#94a3b8', specs: '旗舰降噪 · LDAC · 30h 续航',
  },
  {
    id: 14, name: '华为 FreeBuds Pro 3', category: '耳机', price: 999, originalPrice: null,
    rating: 4.6, reviews: 876, icon: '🎧', badge: null,
    gradient: 'linear-gradient(135deg, #001219 0%, #001e29 100%)',
    accent: '#A8D8C8', specs: '双芯降噪 · LDAC · 6.5+31h',
  },
  {
    id: 15, name: '索尼 WF-1000XM5', category: '耳机', price: 1799, originalPrice: null,
    rating: 4.8, reviews: 1432, icon: '🎧', badge: null,
    gradient: 'linear-gradient(135deg, #111118 0%, #1c1c28 100%)',
    accent: '#C8C5E0', specs: 'V2处理器 · 旗舰降噪 · 8+24h',
  },
  // ── 平板 ────────────────────────────────────────────────────
  {
    id: 16, name: 'iPad Pro M4', category: '平板', price: 8999, originalPrice: null,
    rating: 4.9, reviews: 1243, icon: '📱', badge: '旗舰',
    gradient: 'linear-gradient(135deg, #060d1f 0%, #0d1a3d 100%)',
    accent: '#E8B4A8', specs: 'M4 · OLED 2732×2048 · 最薄5.1mm',
  },
  {
    id: 17, name: 'iPad Air M2', category: '平板', price: 4799, originalPrice: null,
    rating: 4.7, reviews: 987, icon: '📱', badge: '推荐',
    gradient: 'linear-gradient(135deg, #0d0a1e 0%, #160f33 100%)',
    accent: '#C8C5E0', specs: 'M2 · 11寸 · WiFi 6E · Apple Pencil Pro',
  },
  {
    id: 18, name: '华为 MatePad Pro 13.2', category: '平板', price: 4499, originalPrice: 4999,
    rating: 4.6, reviews: 654, icon: '📱', badge: null,
    gradient: 'linear-gradient(135deg, #001a12 0%, #002818 100%)',
    accent: '#A8D8C8', specs: '麒麟 9000S · 2.8K OLED · 磁吸键盘',
  },
  // ── 手表 ────────────────────────────────────────────────────
  {
    id: 19, name: 'Apple Watch Series 10', category: '手表', price: 2999, originalPrice: null,
    rating: 4.8, reviews: 1876, icon: '⌚', badge: '新品',
    gradient: 'linear-gradient(135deg, #0a0a14 0%, #14141e 100%)',
    accent: '#e2e8f0', specs: 'S10芯片 · 46mm · 18h · 血氧心率',
  },
  {
    id: 20, name: '华为 Watch GT 5 Pro', category: '手表', price: 1799, originalPrice: 1999,
    rating: 4.7, reviews: 1123, icon: '⌚', badge: null,
    gradient: 'linear-gradient(135deg, #001a0d 0%, #00291a 100%)',
    accent: '#A8D8C8', specs: '14天续航 · 运动健康 · 北斗GPS',
  },
]
