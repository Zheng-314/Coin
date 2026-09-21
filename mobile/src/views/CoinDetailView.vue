<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '@/config/http'

const route = useRoute()
const router = useRouter()
const coinName = decodeURIComponent(route.params.name || '')
const loading = ref(true)
const notFound = ref(false)
const info = ref(null)
const list = ref([])

onMounted(async () => {
  try {
    // 数据库模糊检索同名钱币
    const resp = await http.get('/api/artifacts/searchItems', {
      params: { page: 1, limit: 20, q: coinName.split('>')[0]?.trim() || coinName },
    })
    list.value = resp.data?.items || []
    if (list.value.length) info.value = list.value[0]
    else notFound.value = true
  } catch { notFound.value = true }
  finally { loading.value = false }
})

function openCoin(item) {
  if (item?.url) window.open(item.url, '_blank')
}
</script>

<template>
  <div class="page">
    <div class="topbar">
      <button class="back" @click="router.back()">‹ 返回</button>
    </div>

    <div v-if="loading" class="loading-dots"><span></span><span></span><span></span></div>

    <template v-else>
      <div class="card">
        <div class="title">{{ coinName }}</div>
        <div v-if="notFound" class="empty">知识库暂无该钱币的详细条目</div>
        <template v-else-if="info">
          <img v-if="info.url" :src="info.url" class="pic" />
        </template>
      </div>

      <div v-if="list.length" class="card">
        <div class="list-title">相关馆藏（{{ list.length }}）</div>
        <div v-for="(item, i) in list" :key="i" class="item" @click="openCoin(item)">
          <img v-if="item.url" :src="item.url" class="thumb" />
          <div class="item-info">
            <div class="item-title">{{ item.title || item.pid }}</div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back { background: none; border: none; color: var(--primary); font-size: 16px; padding: 4px 0; }
.title { font-size: 18px; font-weight: 700; line-height: 1.5; }
.pic { width: 100%; border-radius: 10px; margin-top: 12px; }
.list-title { font-size: 14px; color: var(--text-2); margin-bottom: 10px; }
.item { display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--line); }
.item:last-child { border-bottom: none; }
.thumb { width: 56px; height: 56px; object-fit: cover; border-radius: 8px; background: var(--bg); }
.item-title { font-size: 14px; line-height: 1.5; }
</style>
