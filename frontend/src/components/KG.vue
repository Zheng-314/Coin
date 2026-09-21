<template>
  <div class="knowledge-graph">
    <div class="kg-header">
      <div class="kg-title">
        <h2>🕸️ 知识图谱</h2>
        <p class="kg-desc">探索钱币实体之间的关系网络 · 节点越大越核心，连线越粗关系越强</p>
      </div>
      <div class="kg-controls">
        <div class="search-box">
          <input
            v-model="searchQuery"
            placeholder="搜索节点..."
            @input="highlightSearch"
          />
        </div>
        <div class="rank-filter">
          <label>关系质量 ≥</label>
          <select v-model="minRankFilter" @change="reloadGraph">
            <option :value="0">全部关系</option>
            <option :value="5">较重要 (rank≥5)</option>
            <option :value="10">重要 (rank≥10)</option>
            <option :value="20">核心关系 (rank≥20)</option>
          </select>
        </div>
        <button class="ctrl-btn" @click="togglePhysics">
          {{ physicsEnabled ? '⏸️ 暂停' : '▶️ 启动' }}
        </button>
        <button class="ctrl-btn" @click="stabilize">🔄 重新布局</button>
        <button class="ctrl-btn" @click="fitView">📐 适配视图</button>
      </div>
    </div>

    <div class="kg-legend">
      <div v-for="(info, type) in legendInfo" :key="type" class="legend-item" @click="filterByType(type)">
        <span
          class="color-dot"
          :style="{ backgroundColor: info.bg, borderColor: info.border }"
        ></span>
        <span class="legend-label">{{ info.alias }}</span>
        <span class="legend-count">{{ info.count }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>加载知识图谱中...</p>
    </div>

    <div v-if="graphError && !loading" class="error-overlay">
      <p>⚠️ 知识图谱加载失败</p>
      <button @click="loadGraphData" class="retry-btn">重新加载</button>
    </div>

    <!-- 节点详情弹窗 -->
    <div v-if="selectedNode" class="node-detail" @click.stop>
      <div class="detail-header">
        <span class="detail-type" :style="{ backgroundColor: selectedNode.color }">{{ selectedNode.type }}</span>
        <button class="close-btn" @click="selectedNode = null">×</button>
      </div>
      <h3>{{ selectedNode.label }}</h3>
      <p v-if="selectedNode.description" class="detail-desc">{{ selectedNode.description }}</p>
      <div class="detail-meta">
        <span v-if="selectedNode.degree" class="meta-item">🔗 {{ selectedNode.degree }} 个关联</span>
      </div>
      <div v-if="selectedNode.connections.length" class="detail-connections">
        <p class="conn-title">关联节点 ({{ selectedNode.connections.length }})</p>
        <div
          v-for="conn in selectedNode.connections.slice(0, 15)"
          :key="conn.id"
          class="conn-item"
          :title="conn.edgeDesc || ''"
        >
          <span class="conn-dot" :style="{ backgroundColor: conn.color }"></span>
          <span class="conn-name">{{ conn.label }}</span>
          <span class="conn-edge">{{ conn.edge }}</span>
        </div>
      </div>
      <!-- 优化4：一键跳转问答 -->
      <button class="ask-ai-btn" @click="askAI(selectedNode)">
        💬 问 AI 关于「{{ selectedNode.label }}」
      </button>
    </div>

    <div class="kg-stats">
      <span>节点: {{ nodeCount }}</span>
      <span>关系: {{ edgeCount }}</span>
      <span v-if="minRankFilter > 0" class="filter-badge">筛选: rank≥{{ minRankFilter }}</span>
    </div>

    <div id="graph-container" ref="graphContainer"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { useRouter } from 'vue-router';
import http from '@/config/http';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data/standalone';

const router = useRouter();
const network = ref(null);
const physicsEnabled = ref(true);
const graphContainer = ref(null);
const loading = ref(true);
const graphError = ref(false);
const searchQuery = ref('');
const selectedNode = ref(null);
const nodeCount = ref(0);
const edgeCount = ref(0);
const allNodes = ref([]);
const allEdges = ref([]);
const minRankFilter = ref(5);   // 默认只显示 rank≥5 的关系（产品逻辑：避免毛线团）

// ========================== 颜色配置 ==========================
// 产品逻辑：按 GraphRAG 实体类型区分颜色，而非自己猜类型
const nodeColors = {
  EVENT:        { bg: '#FFE5B5', border: '#FFB86B' },
  ORGANIZATION: { bg: '#B5D8FF', border: '#6B9FFF' },
  PERSON:       { bg: '#FFB5E5', border: '#FF6BB8' },
  GEO:          { bg: '#B5FFE5', border: '#6BFFB8' },
  COIN:         { bg: '#FFF0E5', border: '#D4885C' },
  Entity:       { bg: '#E8E8E8', border: '#A0A0A0' },
};

const typeAlias = {
  EVENT: '事件', ORGANIZATION: '机构', PERSON: '人物', GEO: '地理',
  COIN: '钱币', Entity: '通用实体',
};

// 动态图例（含每类数量）
const legendInfo = computed(() => {
  const info = {};
  const counts = {};
  allNodes.value.forEach(n => {
    const t = n.type || 'Entity';
    counts[t] = (counts[t] || 0) + 1;
  });
  for (const [type, cfg] of Object.entries(nodeColors)) {
    if (counts[type] && counts[type] > 0) {
      info[type] = { bg: cfg.bg, border: cfg.border, alias: typeAlias[type] || type, count: counts[type] };
    }
  }
  return info;
});

// ========================== 节点大小映射 ==========================
// 产品逻辑：degree 越高 = 节点越核心 = 视觉上越大
// 公式：最小 12px，最大 35px，线性映射
const calcNodeSize = (degree) => {
  const d = degree || 1;
  const sizes = [12, 16, 20, 25, 30, 35];
  if (d <= 1) return sizes[0];
  if (d >= 6) return sizes[5];
  return sizes[d - 1] || 18;
};

// ========================== 边粗细映射 ==========================
const calcEdgeWidth = (weight) => {
  const w = weight || 1.0;
  if (w >= 2.0) return 3;
  if (w >= 1.5) return 2;
  return 1;
};

// ========================== 数据加载 ==========================
const loadGraphData = async () => {
  graphError.value = false;
  loading.value = true;
  try {
    const params = { limit: 500 };
    if (minRankFilter.value > 0) {
      params.min_rank = minRankFilter.value;
    }
    const response = await http.get('/api/kg/graph', { params });
    const graphData = response.data || { nodes: [], edges: [] };

    const nodes = new DataSet();
    const edges = new DataSet();
    const nodesList = [];

    // 处理节点
    graphData.nodes.forEach((node) => {
      const nodeType = node.type || 'Entity';
      const color = nodeColors[nodeType] || nodeColors.Entity;
      const degreeVal = node.degree || 1;
      const nodeSize = calcNodeSize(degreeVal);

      nodes.add({
        id: node.id,
        label: node.label || node.id,
        title: _buildTooltip(node),
        color: {
          background: color.bg,
          border: color.border,
          highlight: { background: color.border, border: color.bg }
        },
        shape: 'dot',
        size: nodeSize,
        font: {
          size: nodeSize >= 20 ? 13 : 11,
          color: '#333',
          face: 'Microsoft YaHei',
          bold: nodeSize >= 25 ? { size: 13 } : undefined,
        },
        borderWidth: nodeSize >= 25 ? 3 : 2,
        shadow: { enabled: true, size: nodeSize >= 20 ? 4 : 2, x: 1, y: 1 },
      });

      nodesList.push({
        id: node.id,
        label: node.label || node.id,
        type: nodeType,
        color: color.bg,
        description: node.description || '',
        degree: degreeVal,
        communities: node.communities || '[]',
      });
    });

    // 处理边
    graphData.edges.forEach((edge) => {
      const edgeWeight = edge.weight || 1.0;
      edges.add({
        from: edge.from,
        to: edge.to,
        label: edge.label || '',
        title: edge.description || edge.label || '',
        arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        color: {
          color: edgeWeight >= 2 ? '#B86B4A' : '#C0C0C0',
          highlight: '#8b3a3a',
          hover: '#666'
        },
        width: calcEdgeWidth(edgeWeight),
        font: { size: 9, color: '#999', strokeWidth: 2, background: 'white' },
        smooth: { type: 'continuous' },
      });
    });

    nodeCount.value = graphData.nodes.length;
    edgeCount.value = graphData.edges.length;
    allNodes.value = nodesList;
    allEdges.value = graphData.edges;

    const options = {
      layout: { improvedLayout: true, randomSeed: 42 },
      nodes: { shape: 'dot', font: { size: 12 } },
      edges: {
        smooth: { type: 'continuous' },
        length: 200,
        scaling: {
          min: 1,
          max: 5,
          label: {
            enabled: true,
            min: 14,
            max: 30,
            maxVisible: 20,
            drawThreshold: 8,
          },
        },
      },
      physics: {
        enabled: physicsEnabled.value,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -80,
          centralGravity: 0.01,
          springLength: 150,
          springConstant: 0.04,
          damping: 0.4,
        },
        stabilization: { enabled: true, iterations: 1000, updateInterval: 50 },
        maxVelocity: 30,
        minVelocity: 0.5,
      },
      interaction: {
        hover: true,
        tooltipDelay: 150,
        hideEdgesOnDrag: true,
        dragNodes: true,
        dragView: true,
        zoomView: true,
        navigationButtons: false,
        keyboard: { enabled: true },
      },
    };

    network.value = new Network(graphContainer.value, { nodes, edges }, options);

    // 节点点击事件
    network.value.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const nodeData = nodesList.find(n => n.id === nodeId);
        if (nodeData) {
          const connectedEdges = graphData.edges.filter(e => e.from === nodeId || e.to === nodeId);
          const connections = connectedEdges.map(e => {
            const connId = e.from === nodeId ? e.to : e.from;
            const connNode = nodesList.find(n => n.id === connId);
            return connNode ? {
              ...connNode,
              edge: e.label || '关联',
              edgeDesc: e.description || '',
            } : null;
          }).filter(Boolean);

          selectedNode.value = { ...nodeData, connections };
        }
      } else {
        selectedNode.value = null;
      }
    });

    network.value.on('stabilizationIterationsDone', () => {
      network.value.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
    });

    loading.value = false;
  } catch (error) {
    console.error('加载图谱失败:', error);
    graphError.value = true;
    loading.value = false;
  }
};

// ========================== 节点 Tooltip ==========================
// 产品逻辑：hover 时显示完整信息，不只是名字
const _buildTooltip = (node) => {
  const parts = [`<b>${node.label || node.id}</b>`];
  if (node.type) parts.push(`类型: ${node.type}`);
  if (node.degree) parts.push(`关联数: ${node.degree}`);
  if (node.description) parts.push(`<br/><i>${node.description.substring(0, 120)}</i>`);
  return parts.join('<br/>');
};

// ========================== 图谱控制 ==========================
const reloadGraph = () => {
  if (network.value) network.value.destroy();
  loadGraphData();
};

const togglePhysics = () => {
  physicsEnabled.value = !physicsEnabled.value;
  if (network.value) {
    network.value.setOptions({ physics: { enabled: physicsEnabled.value } });
  }
};

const stabilize = () => {
  if (network.value) network.value.stabilize(100);
};

const fitView = () => {
  if (network.value) {
    network.value.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
  }
};

const highlightSearch = () => {
  if (!network.value || !searchQuery.value.trim()) {
    allNodes.value.forEach(n => {
      try { network.value.body.data.nodes.update({ id: n.id, opacity: 1 }); } catch (e) { /* ignore */ }
    });
    return;
  }
  const query = searchQuery.value.trim().toLowerCase();
  const matchedIds = allNodes.value
    .filter(n => n.label.toLowerCase().includes(query) || (n.type || '').toLowerCase().includes(query))
    .map(n => n.id);

  allNodes.value.forEach(n => {
    const opacity = matchedIds.includes(n.id) ? 1 : 0.15;
    try {
      network.value.body.data.nodes.update({ id: n.id, opacity });
    } catch (e) { /* ignore */ }
  });
};

const filterByType = (type) => {
  if (!network.value) return;
  const typeNodes = allNodes.value.filter(n => n.type === type);
  if (typeNodes.length > 0) {
    network.value.selectNodes(typeNodes.map(n => n.id));
    network.value.fit({ nodes: typeNodes.map(n => n.id), animation: { duration: 500 } });
  }
};

// ========================== 优化4：图谱 → 问答 ==========================
// 产品逻辑：节点详情面板的"问AI"按钮，一键跳转问答页并自动提问
const askAI = (node) => {
  const question = `请介绍一下「${node.label}」`;
  router.push({ path: '/kgqa/qa', query: { q: question } });
};

onMounted(() => { loadGraphData(); });
onBeforeUnmount(() => { if (network.value) network.value.destroy(); });
</script>

<style scoped>
.knowledge-graph {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 180px);
  min-height: 500px;
  position: relative;
}

.kg-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 12px;
}

.kg-title h2 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.3rem;
}

.kg-desc {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.kg-controls {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.search-box input {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  font-size: 13px;
  width: 150px;
  outline: none;
  transition: all 0.2s;
}
.search-box input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(139, 58, 58, 0.1);
}

.rank-filter {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
}
.rank-filter select {
  padding: 5px 8px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  font-size: 12px;
  outline: none;
  background: white;
  cursor: pointer;
}

.ctrl-btn {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  background: white;
  border-radius: 999px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.ctrl-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: #fdf5f5;
}

.kg-legend {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 14px;
  background: #f9f5f0;
  border-radius: 10px;
  margin-bottom: 12px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
  transition: background 0.2s;
}
.legend-item:hover { background: rgba(139, 58, 58, 0.08); }
.color-dot {
  width: 12px; height: 12px;
  border: 2px solid;
  border-radius: 50%;
  flex-shrink: 0;
}
.legend-label { font-size: 12px; color: #555; }
.legend-count { font-size: 11px; color: #999; }

.loading-overlay {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  text-align: center; z-index: 10;
}
.spinner {
  width: 40px; height: 40px;
  border: 3px solid #eee;
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}
@keyframes spin { to { transform: rotate(360deg); } }

.error-overlay {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  text-align: center; z-index: 10;
  background: white; padding: 24px; border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
.retry-btn {
  margin-top: 8px;
  padding: 6px 16px;
  border: 1px solid var(--primary-color);
  background: white; color: var(--primary-color);
  border-radius: 999px; cursor: pointer;
}
.retry-btn:hover { background: #fdf5f5; }

.kg-stats {
  display: flex; gap: 16px;
  font-size: 12px; color: var(--text-secondary);
  margin-bottom: 8px; align-items: center;
}
.filter-badge {
  background: #fdf5f5; color: var(--primary-color);
  padding: 1px 8px; border-radius: 999px; font-size: 11px;
}

/* 节点详情面板 */
.node-detail {
  position: absolute; top: 130px; right: 20px;
  width: 280px; background: white;
  border: 1px solid var(--border-color);
  border-radius: 12px; padding: 16px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  z-index: 20; max-height: 480px; overflow-y: auto;
}
.detail-header {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 8px;
}
.detail-type {
  font-size: 11px; padding: 2px 8px;
  border-radius: 999px; color: #333; font-weight: bold;
}
.close-btn {
  width: 24px; height: 24px;
  border: none; background: #f0f0f0;
  border-radius: 50%; cursor: pointer;
  font-size: 16px;
  display: flex; align-items: center; justify-content: center;
}
.close-btn:hover { background: #e0e0e0; }

.node-detail h3 { margin: 0 0 8px; font-size: 15px; color: #333; }
.detail-desc { font-size: 13px; color: #666; line-height: 1.5; margin: 0 0 8px; }
.detail-meta { margin-bottom: 8px; }
.meta-item { font-size: 12px; color: #999; }

.conn-title { font-size: 12px; color: #999; margin: 0 0 8px; font-weight: bold; }
.conn-item {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 0; font-size: 12px; color: #555;
  cursor: default;
}
.conn-dot {
  width: 8px; height: 8px;
  border-radius: 50%; flex-shrink: 0;
}
.conn-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conn-edge {
  font-size: 10px; color: #999;
  background: #f5f5f5; padding: 1px 6px;
  border-radius: 4px; flex-shrink: 0;
}

/* 优化4：问答跳转按钮 */
.ask-ai-btn {
  display: block; width: 100%; margin-top: 14px;
  padding: 10px 0;
  background: linear-gradient(135deg, #8b3a3a, #a0523d);
  color: white; border: none;
  border-radius: 8px; font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.ask-ai-btn:hover {
  background: linear-gradient(135deg, #6b2a2a, #8b3a3a);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(139, 58, 58, 0.3);
}

#graph-container {
  flex: 1;
  border: 1px solid #e0d5c5;
  border-radius: 12px;
  background: linear-gradient(135deg, #faf8f5 0%, #f5f0e8 100%);
  min-height: 0;
}

@media (max-width: 760px) {
  .kg-header { flex-direction: column; }
  .kg-controls { width: 100%; }
  .search-box input { width: 100%; }
  .node-detail { position: static; width: 100%; margin-top: 12px; }
}
</style>
