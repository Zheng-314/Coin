// ==============================================================================
// 移动版 HTTP 客户端 — 运行时可配置 API 地址（设置页可改，默认云端）
// ==============================================================================
import axios from 'axios'

// 默认指向云端后端（部署后替换为真实地址）；本地调试可改为局域网 IP
export const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://192.168.31.185:5001'

export function getApiBase() {
  return localStorage.getItem('api_base_url') || DEFAULT_API_BASE
}

export function setApiBase(url) {
  localStorage.setItem('api_base_url', url.replace(/\/+$/, ''))
}

const http = axios.create({
  baseURL: getApiBase(),
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 每次请求都读取最新配置（支持设置页热切换）
http.interceptors.request.use((config) => {
  config.baseURL = getApiBase()
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
    return Promise.reject(error)
  }
)

export const apiUrl = (path) => `${getApiBase()}${path}`

export default http
