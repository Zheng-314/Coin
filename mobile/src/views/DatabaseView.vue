<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import http from '@/config/http'

const coins = ref([])
const loading = ref(false)
const error = ref('')
const page = ref(1)
const hasMore = ref(true)
const keyword = ref('')
const activeCategory = ref('')
const categories = ref([{ value: '', label: '全部' }])
const filtersOpen = ref(false)
const filters = ref({ dynasty: '', province: '', grade: '' })
const options = ref({ dynasties: [], provinces: [], grades: [] })

async function load(reset = false) {
  if (loading.value || (!hasMore.value && !reset)) return
  if (reset) { coins.value = []; page.value = 1; hasMore.value = true }
  loading.value = true; error.value = ''
  try {
    const params = { page: page.value, limit: 16 }
    if (keyword.value.trim()) params.q = keyword.value.trim()
    if (activeCategory.value) params.c0 = activeCategory.value
    if (filters.value.dynasty) params.dynasty = filters.value.dynasty
    if (filters.value.province) params.province = filters.value.province
    if (filters.value.grade) params.grade = filters.value.grade
    const { data } = await http.get('/api/artifacts/searchItems', { params })
    const rows = Array.isArray(data) ? data : (data.items || [])
    coins.value.push(...rows)
    page.value++
    if (rows.length < 16) hasMore.value = false
  } catch (e) { error.value = '钱币库加载失败，请检查网络后重试' }
  finally { loading.value = false }
}

async function init() {
  try {
    const [c, f] = await Promise.allSettled([
      http.get('/api/artifacts/classification'),
      http.get('/api/artifacts/filters'),
    ])
    if (c.status === 'fulfilled') {
      const raw = c.value.data || {}
      categories.value = [{ value: '', label: '全部' }, ...Object.values(raw).map(x => ({ value: x.c0 || '', label: x.unicode || x.c0 })).filter(x => x.value)]
    }
    if (f.status === 'fulfilled') {
      const x = f.value.data || {}
      options.value = { dynasties: x.dynasties || [], provinces: x.provinces || [], grades: x.grades || [] }
    }
  } finally { load(true) }
}

function chooseCategory(v) { activeCategory.value = v; load(true) }
function resetFilters() { filters.value = { dynasty: '', province: '', grade: '' }; load(true) }
function scrollLoad() {
  if (window.innerHeight + window.scrollY > document.documentElement.scrollHeight - 300) load()
}

onMounted(() => { init(); window.addEventListener('scroll', scrollLoad, { passive: true }) })
onUnmounted(() => window.removeEventListener('scroll', scrollLoad))
</script>

<template>
  <div class="page">
    <div class="topbar"><div><h1>钱币数据库</h1><div class="sub">馆藏钱币 · 分类检索 · 详情浏览</div></div></div>

    <div class="search-row">
      <input v-model="keyword" class="input" placeholder="搜索钱币名称、朝代、版别" @keyup.enter="load(true)" />
      <button class="search" @click="load(true)">搜索</button>
    </div>

    <div class="chips">
      <button v-for="c in categories" :key="c.value" class="chip" :class="{on:activeCategory===c.value}" @click="chooseCategory(c.value)">{{ c.label }}</button>
    </div>

    <button class="filter-toggle" @click="filtersOpen=!filtersOpen">⚙ 筛选条件 {{ filtersOpen ? '收起' : '展开' }}</button>
    <div v-if="filtersOpen" class="card filters">
      <select v-model="filters.dynasty" class="input" @change="load(true)"><option value="">全部朝代</option><option v-for="x in options.dynasties" :key="x" :value="x">{{x}}</option></select>
      <select v-model="filters.province" class="input" @change="load(true)"><option value="">全部省份</option><option v-for="x in options.provinces" :key="x" :value="x">{{x}}</option></select>
      <select v-model="filters.grade" class="input" @change="load(true)"><option value="">全部评级</option><option v-for="x in options.grades" :key="x" :value="x">{{x}}</option></select>
      <button class="btn ghost" @click="resetFilters">重置筛选</button>
    </div>

    <div v-if="error" class="error">{{error}}</div>
    <div v-if="!coins.length && loading" class="loading-dots"><span></span><span></span><span></span></div>
    <div v-if="!coins.length && !loading" class="empty">没有找到匹配的钱币</div>

    <div class="coin-grid">
      <article v-for="coin in coins" :key="coin.pid" class="coin-card card">
        <img v-if="coin.url" :src="coin.url" :alt="coin.title" loading="lazy" />
        <div v-else class="no-image">🪙</div>
        <div class="coin-title">{{ coin.title || coin.text_data?.title || `钱币 #${coin.pid}` }}</div>
        <div class="coin-meta"><span v-if="coin.dynasty">{{coin.dynasty}}</span><span v-if="coin.province">{{coin.province}}</span><span v-if="coin.grade">{{coin.grade}}</span></div>
      </article>
    </div>
    <div v-if="loading" class="loading-dots"><span></span><span></span><span></span></div>
    <div v-else-if="coins.length && !hasMore" class="end">— 已加载全部结果 —</div>
  </div>
</template>

<style scoped>
.search-row { display:flex; gap:8px; margin-bottom:10px; }
.search { min-width:64px; border:0; border-radius:12px; background:var(--primary); color:#fff; font-size:14px; font-weight:600; }
.chips { display:flex; overflow-x:auto; gap:8px; padding:2px 0 12px; scrollbar-width:none; }
.chip { white-space:nowrap; border:1px solid var(--line); border-radius:999px; background:#fff; padding:7px 12px; color:var(--text-2); font-size:13px; }
.chip.on { color:#fff; border-color:var(--primary); background:var(--primary); }
.filter-toggle { border:0; background:none; color:var(--primary); font-size:13px; padding:4px 0 10px; }
.filters { display:grid; gap:9px; }
.filters select { appearance:auto; }
.filters .btn { min-height:42px; }
.error { padding:10px; border-radius:10px; background:#FDECEA; color:var(--danger); font-size:13px; margin-bottom:10px; }
.coin-grid { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:11px; }
.coin-card { margin:0; padding:8px; box-shadow:0 1px 8px rgba(60,42,24,.07); overflow:hidden; }
.coin-card img,.no-image { width:100%; aspect-ratio:1; object-fit:contain; background:#F7F4EF; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:34px; }
.coin-title { font-size:13px; font-weight:650; line-height:1.4; margin:8px 2px 4px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.coin-meta { display:flex; gap:4px; flex-wrap:wrap; margin:0 2px 2px; }
.coin-meta span { font-size:10px; color:var(--primary); background:rgba(140,74,47,.08); padding:2px 5px; border-radius:4px; }
.end { text-align:center; color:var(--text-2); font-size:12px; padding:18px 0; }
</style>
