import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

// 定义名为 'auth' 的 store
export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(JSON.parse(localStorage.getItem('user')) || null)
  const router = useRouter()

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const username = computed(() => user.value?.username)

  // Actions
  const login = (userData) => {
    token.value = userData.token
    user.value = { id: userData.id, username: userData.username }

    localStorage.setItem('token', token.value)
    localStorage.setItem('user', JSON.stringify(user.value))

    router.push('/')
  }

  const logout = (redirect = true) => {
    token.value = null
    user.value = null

    localStorage.removeItem('token')
    localStorage.removeItem('user')

    if (redirect) {
      router.push('/login')
    }
  }

  return { token, user, isAuthenticated, username, login, logout }
})
