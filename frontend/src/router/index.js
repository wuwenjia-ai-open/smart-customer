import { createRouter, createWebHistory } from 'vue-router'
import Shop from '@/views/Shop.vue'
import Chat from '@/views/Chat.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'shop', component: Shop },
    { path: '/chat', name: 'chat', component: Chat },
  ],
})
