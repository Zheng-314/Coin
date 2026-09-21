<script setup>
import { ref, onMounted, nextTick } from 'vue'
import http from '@/config/http'

const props = defineProps({ embedded: { type: Boolean, default: false } })
const loading = ref(true)
const nodes = ref([])
const edges = ref([])
const keyword = ref('')
const selected = ref(null)
const related = ref([])
let network = null

onMounted(async () => {
  try {
    const resp = await http.get('/api/kg/graph?limit=60&min_rank=5')
    nodes.value = resp.data.nodes || []
    edges.value = resp.data.edges || []
    // 先让 v-else 的 canvas 挂载，再初始化 vis-network
    loading.value = false
    await nextTick()
    await renderGraph()
  } catch { /* 留空态 */ }
  finally { loading.value = false }
})

// 按需加载 vis-network（600KB，只在图谱页加载）
async function renderGraph() {
  const vis = await import('vis-network/standalone')
  const container = document.getElementById('kg-canvas')
  if (!container || !nodes.value.length) return

  const data = {
    nodes: nodes.value.map(n => ({
      id: n.id,
      label: n.label,
      value: n.degree || 1,
      title: n.description?.slice(0, 60) || n.label,
    })),
    edges: edges.value.map(e => ({ from: e.from, to: e.to, title: e.description?.slice(0, 80) || '' })),
  }
  const options = {
    layout: { improvedLayout: true },
    physics: { enabled: true, stabilization: { iterations: 120, fit: true } },
    interaction: { hover: true, dragNodes: true, zoomView: true },
    nodes: {
      shape: 'dot', font: { size: 12, color: '#2B2420' },
      borderWidth: 1.5, color: { background: '#F3E3C8', border: '#8C4A2F', highlight: { background: '#C9A227', border: '#8C4A2F' } },
      scaling: { min: 8, max: 26 },
    },
    edges: { color: { color: '#D8CCBB', highlight: '#8C4A2F' }, smooth: { enabled: false }, selectionWidth: 2 },
  }
  network = new vis.Network(container, data, options)
  network.on('click', (params) => {
    if (params.nodes.length) selectNode(params.nodes[0])
    else { selected.value = null; related.value = [] }
  })
}

function selectNode(id) {
  const n = nodes.value.find(x => x.id === id)
  if (!n) return
  selected.value = n
  related.value = edges.value
    .filter(e => e.from === id || e.to === id)
    .map(e => ({
      label: e.label,
      desc: e.description?.slice(0, 80) || '',
      other: e.from === id ? e.to : e.from,
    }))
    .slice(0, 6)
  const otherNames = related.value.map(r => nodes.value.find(x => x.id === r.other)?.label).filter(Boolean)
  selected.value._related_names = otherNames
}

function search() {
  const kw = keyword.value.trim()
  if (!kw || !network) return
  const hit = nodes.value.find(n => n.label.includes(kw))
  if (hit) { network.selectNodes([hit.id]); network.focus(hit.id, { scale: 1.2, animation: true }); selectNode(hit.id) }
}
</script>

<template>
  <div class="page">
    <div v-if="!props.embedded" class="topbar">
      <div><h1>知识图谱</h1><div class="sub">拖动探索 · 点选查看关联</div></div>
    </div>

    <div class="search-bar">
      <input v-model="keyword" class="input" placeholder="搜索实体，如：光绪元宝" @keyup.enter="search" />
      <button class="btn ghost search-btn" @click="search">搜索</button>
    </div>

    <div class="card canvas-card">
      <div v-if="loading" class="loading-dots"><span></span><span></span><span></span></div>
      <div v-else-if="!nodes.length" class="empty">图谱数据加载失败<br/>请检查网络或服务地址</div>
      <div v-else id="kg-canvas" class="canvas"></div>
    </div>

    <!-- 选中节点详情 -->
    <div v-if="selected" class="card">
      <div class="sel-head">
        <div class="sel-name">{{ selected.label }}</div>
        <span class="tag">{{ selected.type }}</span>
      </div>
      <p v-if="selected.description" class="sel-desc">{{ selected.description.slice(0, 120) }}</p>
      <div v-if="selected._related_names?.length" class="rel">
        <div class="rel-title">关联实体</div>
        <div class="rel-tags">
          <span v-for="(r, i) in selected._related_names" :key="i" class="tag">{{ r }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.search-btn { width: 88px; min-height: 48px; }
.canvas-card { padding: 8px; }
.canvas { width: 100%; height: 52vh; border-radius: 12px; background: #FBFAF7; }
.sel-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.sel-name { font-size: 17px; font-weight: 700; }
.sel-desc { font-size: 13px; color: var(--text-2); line-height: 1.6; }
.rel-title { font-size: 12px; color: var(--text-2); margin: 10px 0 6px; }
.rel-tags { display: flex; flex-wrap: wrap; gap: 6px; }
</style>
