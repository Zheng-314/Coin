import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import ArtifactDetailView from '../views/ArtifactDetailView.vue'
import PredictView from '@/views/PredictView.vue'
import AboutView from '../views/AboutView.vue'
import LandingView from '../views/LandingView.vue'
import ValuationView from '../views/ValuationView.vue'

// 需要登录的路由
const protectedRoutes = ['/profile', '/tools', '/valuation']

const routes = [
  {
    path: '/',
    name: 'home',
    component: LandingView,
  },
  {
    path: '/home',
    redirect: '/'
  },
  {
    path: '/database',
    name: 'database',
    component: HomeView,
  },
  { 
    path:'/login',
    name:'login',
    component:LoginView
  },
  {
    path:'/register',
    name:'register',
    component:RegisterView
  },
  {
    path: '/profile',
    component: () => import('@/views/ProfileView.vue'),
    children: [
      {
        path: '',   // 默认显示我的收藏页面
        name: 'ProfileFavorites',
        component: () => import('@/components/ProfileFavorites.vue')
      },
      {
        path: 'account',
        name: 'ProfileAccount',
        component: () => import('@/components/ProfileAccount.vue')
      }
    ]
  },

  {
    path: '/kgqa',
    component: () => import('@/views/KnowledgeEntry.vue'),
    children: [
      {
        path: '',   // 默认显示知识图谱
        name: 'KG',
        component: () => import('@/components/KG.vue')
      },
      {
        path: 'qa',
        name: 'QA',
        component: () => import('@/components/QA.vue')
      }
    ]
  },

  {
    path: '/artifact/:id',
    name: 'artifactDetail',
    component: ArtifactDetailView
  },

  {
    path: '/predict',
    name: 'predict',
    component: PredictView
  },
  {
    path: '/valuation',
    name: 'valuation',
    component: ValuationView
  },

  {
    path: '/about',
    name: 'about',
    component: AboutView
  },
  {
    path: '/tools',
    name: 'tools',
    component: () => import('@/views/ToolsView.vue')
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to, _from, next) => {
  if (protectedRoutes.some(p => to.path.startsWith(p))) {
    const token = localStorage.getItem('token')
    if (!token) {
      return next({ name: 'login', query: { redirect: to.fullPath } })
    }
  }
  next()
})

export default router

