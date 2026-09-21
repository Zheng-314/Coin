import { createRouter, createWebHashHistory } from 'vue-router'

// 注意：移动端用 hash 模式，避免 file/https scheme 下 history 路由刷新 404
const routes = [
  { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
  { path: '/database', name: 'database', component: () => import('@/views/DatabaseView.vue') },
  { path: '/identify', name: 'identify', component: () => import('@/views/IdentifyView.vue') },
  { path: '/knowledge', name: 'knowledge', component: () => import('@/views/KnowledgeView.vue') },
  // 保留旧深链，进入统一的知识中心
  { path: '/qa', redirect: '/knowledge' },
  { path: '/graph', redirect: '/knowledge' },
  { path: '/me', name: 'me', component: () => import('@/views/MeView.vue') },
  { path: '/coin/:name', name: 'coinDetail', component: () => import('@/views/CoinDetailView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
