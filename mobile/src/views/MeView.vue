<script setup>
import { ref, computed } from 'vue'
import http, { getApiBase, setApiBase, DEFAULT_API_BASE } from '@/config/http'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const loginMode = ref(!auth.isAuthenticated)
const logging = ref(false)
const loginErr = ref('')

// 服务器地址设置
const showServer = ref(false)
const serverUrl = ref(getApiBase())
const serverSaved = ref(false)

async function login() {
  if (!username.value || !password.value) return
  logging.value = true
  loginErr.value = ''
  try {
    const resp = await http.post('/api/users/login', {
      username: username.value, password: password.value,
    })
    const data = resp.data
    localStorage.setItem('token', data.token)
    localStorage.setItem('user', JSON.stringify({ id: data.id, username: data.username }))
    auth.token = data.token
    auth.user = { id: data.id, username: data.username }
    loginMode.value = false
  } catch (e) {
    loginErr.value = e.response?.data?.error || e.response?.data?.message || '登录失败，请检查服务器地址'
  } finally { logging.value = false }
}

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  auth.token = null
  auth.user = null
  username.value = ''
  password.value = ''
  loginMode.value = true
}

function saveServer() {
  const u = serverUrl.value.trim().replace(/\/+$/, '')
  if (!/^https?:\/\//.test(u)) { loginErr.value = '地址需以 http:// 或 https:// 开头'; return }
  setApiBase(u)
  serverSaved.value = true
  setTimeout(() => { serverSaved.value = false }, 1500)
}
</script>

<template>
  <div class="page">
    <div class="topbar"><div><h1>我的</h1></div></div>

    <!-- 用户卡片 -->
    <div class="card user-card">
      <template v-if="!loginMode">
        <div class="avatar">{{ auth.user?.username?.[0]?.toUpperCase() || '👤' }}</div>
        <div class="uinfo">
          <div class="uname">{{ auth.user?.username }}</div>
          <div class="usub">已登录 · 收藏与记录已同步</div>
        </div>
        <button class="btn ghost logout" @click="logout">退出</button>
      </template>
      <template v-else>
        <div class="avatar ghost-avatar">👤</div>
        <div class="uinfo">
          <div class="uname">未登录</div>
          <div class="usub">登录后可收藏钱币、保存鉴定记录</div>
        </div>
      </template>
    </div>

    <!-- 登录表单 -->
    <div v-if="loginMode" class="card">
      <div class="form-title">账号登录</div>
      <input v-model="username" class="input" placeholder="用户名" autocomplete="username" />
      <input v-model="password" class="input" type="password" placeholder="密码" autocomplete="current-password" style="margin-top:10px" @keyup.enter="login" />
      <div v-if="loginErr" class="err">{{ loginErr }}</div>
      <button class="btn" style="margin-top:14px" :disabled="logging" @click="login">
        {{ logging ? '登录中…' : '登录' }}
      </button>
    </div>

    <!-- 服务器设置 -->
    <div class="card">
      <div class="row" @click="showServer = !showServer">
        <span>🌐 服务器地址</span>
        <span class="row-right">{{ serverUrl.replace(/^https?:\/\//, '').slice(0, 24) }} {{ showServer ? '▲' : '▼' }}</span>
      </div>
      <div v-if="showServer" class="server-edit">
        <input v-model="serverUrl" class="input" placeholder="http://192.168.x.x:5001" />
        <button class="btn" style="margin-top:10px" @click="saveServer">{{ serverSaved ? '✓ 已保存' : '保存并刷新' }}</button>
        <button class="btn ghost" style="margin-top:8px" @click="serverUrl = DEFAULT_API_BASE; saveServer()">恢复默认</button>
        <p class="tip">默认地址不可用时，可改为局域网 IP（需与电脑同 Wi-Fi）。修改后自动刷新生效。</p>
      </div>
    </div>

    <!-- 关于 -->
    <div class="card">
      <div class="row"><span>ℹ️ 版本</span><span class="row-right">v1.0.0 mobile</span></div>
      <div class="row"><span>🧠 模型</span><span class="row-right">YOLO ×2 + ONNX</span></div>
      <div class="row"><span>📚 知识库</span><span class="row-right">GraphRAG</span></div>
    </div>
  </div>
</template>

<style scoped>
.user-card { display: flex; align-items: center; gap: 14px; padding: 18px 16px; }
.avatar { width: 52px; height: 52px; border-radius: 50%; background: linear-gradient(135deg, var(--primary), var(--primary-light)); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 700; }
.ghost-avatar { background: var(--line); color: #fff; }
.uinfo { flex: 1; }
.uname { font-size: 17px; font-weight: 700; }
.usub { font-size: 12px; color: var(--text-2); margin-top: 2px; }
.logout { width: 72px; min-height: 38px; font-size: 14px; }

.form-title { font-weight: 700; margin-bottom: 12px; }
.err { color: var(--danger); font-size: 13px; margin-top: 8px; }

.row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--line); font-size: 15px; }
.row:last-child { border-bottom: none; }
.row-right { color: var(--text-2); font-size: 13px; }
.server-edit { padding-top: 10px; }
.tip { font-size: 12px; color: var(--text-2); margin-top: 10px; line-height: 1.6; }
</style>
