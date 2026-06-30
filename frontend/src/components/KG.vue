<template>
  <div class="knowledge-graph">
    <div class="kg-header">
      <div class="kg-title">
        <h2>🕸️ 知识图谱</h2>
        <p class="kg-desc">探索钱币实体之间的关系网络</p>
      </div>
      <div class="kg-controls">
        <div class="search-box">
          <input
            v-model="searchQuery"
            placeholder="搜索节点..."
            @input="highlightSearch"
          />
        </div>
        <button class="ctrl-btn" @click="togglePhysics">
          {{ physicsEnabled ? '⏸️ 暂停' : '▶️ 启动' }}
        </button>
        <button class="ctrl-btn" @click="stabilize">🔄 重新布局</button>
        <button class="ctrl-btn" @click="fitView">📐 适配视图</button>
      </div>
    </div>

    <div class="kg-legend">
      <div v-for="(color, type) in nodeColors" :key="type" class="legend-item" @click="filterByType(type)">
        <span
          class="color-dot"
          :style="{ backgroundColor: color.background, borderColor: color.border }"
        ></span>
        <span class="legend-label">{{ typeAlias[type] || type }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>加载知识图谱中...</p>
    </div>

    <div v-if="selectedNode" class="node-detail">
      <div class="detail-header">
        <span class="detail-type" :style="{ backgroundColor: selectedNode.color }">{{ selectedNode.type }}</span>
        <button class="close-btn" @click="selectedNode = null">×</button>
      </div>
      <h3>{{ selectedNode.label }}</h3>
      <p v-if="selectedNode.description" class="detail-desc">{{ selectedNode.description }}</p>
      <div v-if="selectedNode.connections.length" class="detail-connections">
        <p class="conn-title">关联节点 ({{ selectedNode.connections.length }})</p>
        <div v-for="conn in selectedNode.connections.slice(0, 10)" :key="conn.id" class="conn-item">
          <span class="conn-dot" :style="{ backgroundColor: conn.color }"></span>
          <span>{{ conn.label }}</span>
          <span class="conn-edge">{{ conn.edge }}</span>
        </div>
      </div>
    </div>

    <div class="kg-stats">
      <span>节点: {{ nodeCount }}</span>
      <span>关系: {{ edgeCount }}</span>
    </div>

    <div id="graph-container" ref="graphContainer"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import http from '@/config/http';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data/standalone';

const network = ref(null);
const physicsEnabled = ref(true);
const graphContainer = ref(null);
const loading = ref(true);
const searchQuery = ref('');
const selectedNode = ref(null);
const nodeCount = ref(0);
const edgeCount = ref(0);
const allNodes = ref([]);

const nodeColors = {
  EVENT: { background: '#FFE5B5', border: '#FFB86B' },
  ORGANIZATION: { background: '#B5D8FF', border: '#6B9FFF' },
  PERSON: { background: '#FFB5E5', border: '#FF6BB8' },
  GEO: { background: '#B5FFE5', border: '#6BFFB8' },
  COIN: { background: '#FFB5B5', border: '#FF6B6B' },
  PRICE: { background: '#B5D8FF', border: '#6B9FFF' },
  APPEARANCE: { background: '#FFE5B5', border: '#FFB86B' },
  AUCTION: { background: '#B5FFB5', border: '#6BFF6B' },
  MINT: { background: '#E5B5FF', border: '#B86BFF' },
  YEAR: { background: '#B5FFE5', border: '#6BFFB8' },
  default: { background: '#E6E6E6', border: '#A9A9A9' }
};

const typeAlias = {
  EVENT: '事件',
  ORGANIZATION: '机构',
  PERSON: '人物',
  GEO: '地理',
  COIN: '钱币',
  PRICE: '价格',
  APPEARANCE: '外观',
  AUCTION: '拍卖',
  MINT: '铸币厂',
  YEAR: '年份'
};

const nodeTypeAlias = {
  coin: 'COIN', price: 'PRICE', appearance: 'APPEARANCE',
  auction: 'AUCTION', mint: 'MINT', person: 'PERSON',
  year: 'YEAR', event: 'EVENT', organization: 'ORGANIZATION', geo: 'GEO'
};

const resolveNodeType = (rawType) => {
  if (!rawType) return 'default';
  const upper = String(rawType).trim().toUpperCase();
  if (nodeColors[upper]) return upper;
  const alias = nodeTypeAlias[String(rawType).trim().toLowerCase()];
  return alias && nodeColors[alias] ? alias : 'default';
};

const loadGraphData = async () => {
  try {
    const response = await http.get('/api/kg/graph?limit=320');
    const graphData = response.data || { nodes: [], edges: [] };

    const nodes = new DataSet();
    const edges = new DataSet();
    const nodesList = [];

    graphData.nodes.forEach((node) => {
      const nodeType = resolveNodeType(node.type);
      const color = nodeColors[nodeType] || nodeColors.default;
      nodes.add({
        id: node.id,
        label: node.label || node.id,
        title: `${nodeType}: ${node.label || node.id}${node.description ? '\n' + node.description : ''}`,
        color: { background: color.background, border: color.border, highlight: { background: color.border, border: color.background } },
        shape: 'dot',
        size: 20,
        font: { size: 12, color: '#333', face: 'Microsoft YaHei' },
        borderWidth: 2,
        shadow: { enabled: true, size: 3, x: 1, y: 1 }
      });
      nodesList.push({ id: node.id, label: node.label, type: nodeType, color: color.background, description: node.description });
    });

    graphData.edges.forEach((edge) => {
      edges.add({
        from: edge.from,
        to: edge.to,
        label: edge.label || '',
        arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        color: { color: '#999', highlight: '#8b3a3a', hover: '#666' },
        font: { size: 10, color: '#999', strokeWidth: 0 },
        smooth: { type: 'continuous' }
      });
    });

    nodeCount.value = graphData.nodes.length;
    edgeCount.value = graphData.edges.length;
    allNodes.value = nodesList;

    const options = {
      layout: { improvedLayout: true, randomSeed: 42 },
      nodes: { shape: 'dot', size: 20, font: { size: 12 } },
      edges: { smooth: { type: 'continuous' }, length: 200 },
      physics: {
        enabled: physicsEnabled.value,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: { gravitationalConstant: -80, centralGravity: 0.01, springLength: 150, springConstant: 0.04, damping: 0.4 },
        stabilization: { enabled: true, iterations: 1000, updateInterval: 50 },
        maxVelocity: 30,
        minVelocity: 0.5
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        hideEdgesOnDrag: true,
        dragNodes: true,
        dragView: true,
        zoomView: true,
        navigationButtons: false,
        keyboard: { enabled: true }
      }
    };

    network.value = new Network(graphContainer.value, { nodes, edges }, options);

    // 节点点击事件
    network.value.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const nodeData = nodesList.find(n => n.id === nodeId);
        if (nodeData) {
          // 获取关联节点
          const connectedEdges = graphData.edges.filter(e => e.from === nodeId || e.to === nodeId);
          const connections = connectedEdges.map(e => {
            const connId = e.from === nodeId ? e.to : e.from;
            const connNode = nodesList.find(n => n.id === connId);
            return connNode ? { ...connNode, edge: e.label || 'RELATED' } : null;
          }).filter(Boolean);

          selectedNode.value = { ...nodeData, connections };
        }
      } else {
        selectedNode.value = null;
      }
    });

    // 稳定后适配视野
    network.value.on('stabilizationIterationsDone', () => {
      network.value.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
    });

    loading.value = false;
  } catch (error) {
    console.error('加载图谱失败:', error);
    loading.value = false;
  }
};

const togglePhysics = () => {
  physicsEnabled.value = !physicsEnabled.value;
  if (network.value) {
    network.value.setOptions({ physics: { enabled: physicsEnabled.value } });
  }
};

const stabilize = () => {
  if (network.value) {
    network.value.stabilize(100);
  }
};

const fitView = () => {
  if (network.value) {
    network.value.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
  }
};

const highlightSearch = () => {
  if (!network.value || !searchQuery.value.trim()) {
    // 重置所有节点样式
    allNodes.value.forEach(n => {
      network.value.updateClusteredNode(n.id, { opacity: 1 });
    });
    return;
  }
  const query = searchQuery.value.trim().toLowerCase();
  const matchedIds = allNodes.value
    .filter(n => n.label.toLowerCase().includes(query) || n.type.toLowerCase().includes(query))
    .map(n => n.id);

  // 高亮匹配节点，淡化其他
  allNodes.value.forEach(n => {
    const opacity = matchedIds.includes(n.id) ? 1 : 0.2;
    try {
      network.value.body.data.nodes.update({ id: n.id, opacity });
    } catch (e) { /* ignore */ }
  });
};

const filterByType = (type) => {
  if (!network.value) return;
  const typeNodes = allNodes.value.filter(n => n.type === type);
  if (typeNodes.length > 0) {
    const ids = typeNodes.map(n => n.id);
    network.value.selectNodes(ids);
    network.value.fit({ nodes: ids, animation: { duration: 500 } });
  }
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
  font-size: 0.85rem;
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
  width: 160px;
  outline: none;
  transition: all 0.2s;
}

.search-box input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(139, 58, 58, 0.1);
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

.legend-item:hover {
  background: rgba(139, 58, 58, 0.08);
}

.color-dot {
  width: 12px;
  height: 12px;
  border: 2px solid;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-label {
  font-size: 12px;
  color: #555;
}

.loading-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 10;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #eee;
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

@keyframes spin { to { transform: rotate(360deg); } }

.kg-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

/* 节点详情面板 */
.node-detail {
  position: absolute;
  top: 120px;
  right: 20px;
  width: 260px;
  background: white;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  z-index: 20;
  max-height: 400px;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.detail-type {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  color: #333;
  font-weight: bold;
}

.close-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: #f0f0f0;
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: #e0e0e0;
}

.node-detail h3 {
  margin: 0 0 8px;
  font-size: 15px;
  color: #333;
}

.detail-desc {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  margin: 0 0 12px;
}

.conn-title {
  font-size: 12px;
  color: #999;
  margin: 0 0 8px;
  font-weight: bold;
}

.conn-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  font-size: 12px;
  color: #555;
}

.conn-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.conn-edge {
  margin-left: auto;
  font-size: 10px;
  color: #999;
  background: #f5f5f5;
  padding: 1px 6px;
  border-radius: 4px;
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
