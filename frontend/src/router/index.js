import { createRouter, createWebHistory } from 'vue-router'
import Shop from '@/views/Shop.vue'
import Chat from '@/views/Chat.vue'
import Login from '@/views/Login.vue'
import { useAuth } from '@/composables/useAuth.js'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: Login, meta: { public: true } },
    { path: '/', name: 'shop', component: Shop },
    { path: '/chat', name: 'chat', component: Chat },
  ],
})

// 全局路由守卫:未登录访问受保护路由 → 重定向到 /login
router.beforeEach(async (to) => {
  const { isAuthed, validate } = useAuth()
  if (to.meta.public) return true

  if (!isAuthed.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 已登录则在导航时静默校验 token (失效会触发 logout)
  validate()
  return true
})

export default router
