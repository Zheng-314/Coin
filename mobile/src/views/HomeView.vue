<script setup>
import { ref, onMounted } from 'vue'
import http from '@/config/http'

const stats = ref({ coins: 0, classes: 0 })
const capability = ref({ ready: true })

onMounted(async () => {
  try {
    const [a, c] = await Promise.allSettled([
      http.get('/api/artifacts/searchItems?page=1&limit=1'),
      http.get('/api/predict/capabilities'),
    ])
    if (a.status === 'fulfilled') stats.value.coins = a.value.data?.total ?? 0
    if (c.status === 'fulfilled') capability.value = c.value.data
  } catch { /* 离线也能看首页 */ }
})

const actions = [
  { to: '/identify', title: '拍照鉴定', desc: '拍钱币正反面，AI 智能识别', emoji: '📷', primary: true },
  { to: '/database', title: '钱币数据库', desc: '搜索馆藏钱币与版别资料', emoji: '🪙' },
  { to: '/knowledge', title: '知识中心', desc: '图谱浏览与智能问答', emoji: '🕸' },
]
</script>

<template>
  <div class="page">
    <div class="topbar">
      <div>
        <h1>鉴泉识珍</h1>
        <div class="sub">古钱币智能鉴定 · 知识图谱问答</div>
      </div>
      <span class="tag" v-if="capability.ready">AI 就绪</span>
    </div>

    <!-- 主推：拍照鉴定 -->
    <router-link to="/identify" class="hero card">
      <div class="hero-left">
        <div class="hero-title">拍照鉴定</div>
        <div class="hero-desc">对准钱币正反面各拍一张<br/>输出 Top-3 分类与置信度</div>
        <div class="hero-btn">立即鉴定 →</div>
      </div>
      <div class="hero-coin">🪙</div>
    </router-link>

    <div class="grid">
      <router-link v-for="a in actions.slice(1)" :key="a.to" :to="a.to" class="card grid-item">
        <div class="grid-emoji">{{ a.emoji }}</div>
        <div class="grid-title">{{ a.title }}</div>
        <div class="grid-desc">{{ a.desc }}</div>
      </router-link>
    </div>

    <div class="card stat-bar">
      <div class="stat"><b>{{ stats.coins || '—' }}</b><span>馆藏钱币</span></div>
      <div class="stat"><b>92</b><span>分类体系</span></div>
      <div class="stat"><b>3</b><span>检索模式</span></div>
    </div>
  </div>
</template>

<style scoped>
.hero { display: flex; align-items: center; justify-content: space-between; padding: 20px; text-decoration: none; color: var(--text); background: linear-gradient(135deg, #FFF9F0, #FDF1E3); border: 1px solid #F0E2CE; }
.hero-title { font-size: 20px; font-weight: 800; margin-bottom: 6px; }
.hero-desc { font-size: 13px; color: var(--text-2); line-height: 1.6; }
.hero-btn { margin-top: 12px; color: var(--primary); font-weight: 700; font-size: 14px; }
.hero-coin { font-size: 56px; filter: drop-shadow(0 4px 8px rgba(201,162,39,0.4)); }

.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.grid-item { text-decoration: none; color: var(--text); }
.grid-emoji { font-size: 30px; margin-bottom: 8px; }
.grid-title { font-weight: 700; font-size: 16px; margin-bottom: 4px; }
.grid-desc { font-size: 12px; color: var(--text-2); }

.stat-bar { display: flex; justify-content: space-around; padding: 14px; }
.stat { text-align: center; }
.stat b { display: block; font-size: 20px; color: var(--primary); }
.stat span { font-size: 12px; color: var(--text-2); }
</style>
