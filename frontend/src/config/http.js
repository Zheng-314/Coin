// ==============================================================================
// 统一 HTTP 客户端（axios 实例 + 全局拦截器）
// ==============================================================================
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5001'

// 创建 axios 实例
const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：自动附加 Authorization header
http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：统一错误处理
http.interceptors.response.use(
  (response) => response,
  (error) => {
    // 401 = token过期或无效，自动登出
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
    }

    // 统一打印错误到控制台（生产环境可替换为上报）
    if (error.response) {
      console.error(`[HTTP ${error.response.status}] ${error.config?.url}:`, error.response.data)
    } else if (error.request) {
      console.error('[HTTP] 网络错误:', error.message)
    }

    return Promise.reject(error)
  }
)

// 导出 apiUrl 工具函数（兼容旧代码）
export const apiUrl = (path) => `${API_BASE_URL}${path}`

export default http
