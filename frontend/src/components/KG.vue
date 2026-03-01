<template>
  <div class="knowledge-graph">
    <h1>知识图谱</h1>
    <div class="controls">
      <el-button @click="togglePhysics" size="small">
        {{ physicsEnabled ? '关闭物理引擎' : '开启物理引擎' }}
      </el-button>
      <el-button @click="stabilize" size="small">稳定布局</el-button>
    </div>
    <div class="legend">
      <div v-for="(color, type) in nodeColors" :key="type" class="legend-item">
        <span
          class="color-box"
          :style="{
            backgroundColor: color.background,
            borderColor: color.border
          }"
        ></span>
        <span>{{ type }}</span>
      </div>
    </div>
    <div id="graph-container" ref="graphContainer" style="height: 600px; border: 1px solid #ccc;"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import axios from 'axios';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data/standalone';
import { apiUrl } from '@/config/api';


// 状态变量
const network = ref(null);
const physicsEnabled = ref(true); // 默认为 true 以匹配 options
const graphContainer = ref(null); // 用于引用 DOM 元素

// 静态数据
const nodeColors = {
  // 新图谱返回的主类型（后端当前使用）
  EVENT: { background: '#FFE5B5', border: '#FFB86B' },         // 橙
  ORGANIZATION: { background: '#B5D8FF', border: '#6B9FFF' },  // 蓝
  PERSON: { background: '#FFB5E5', border: '#FF6BB8' },        // 玫红
  GEO: { background: '#B5FFE5', border: '#6BFFB8' },           // 薄荷绿

  // 兼容旧类型（避免历史数据全灰）
  COIN: { background: '#FFB5B5', border: '#FF6B6B' },
  PRICE: { background: '#B5D8FF', border: '#6B9FFF' },
  APPEARANCE: { background: '#FFE5B5', border: '#FFB86B' },
  AUCTION: { background: '#B5FFB5', border: '#6BFF6B' },
  MINT: { background: '#E5B5FF', border: '#B86BFF' },
  YEAR: { background: '#B5FFE5', border: '#6BFFB8' },

  default: { background: '#E6E6E6', border: '#A9A9A9' }        // 默认灰
};

const nodeTypeAlias = {
  coin: 'COIN',
  price: 'PRICE',
  appearance: 'APPEARANCE',
  auction: 'AUCTION',
  mint: 'MINT',
  person: 'PERSON',
  year: 'YEAR',
  event: 'EVENT',
  organization: 'ORGANIZATION',
  geo: 'GEO'
};

const resolveNodeType = (rawType) => {
  if (!rawType) return 'default';
  const normalized = String(rawType).trim();
  if (!normalized) return 'default';
  const upper = normalized.toUpperCase();
  if (nodeColors[upper]) return upper;
  const alias = nodeTypeAlias[normalized.toLowerCase()];
  return alias && nodeColors[alias] ? alias : 'default';
};

// 方法定义
const loadGraphData = async () => {
  try {
    // 中间方案：加载更完整的子图，兼顾整体连通观感
    const response = await axios.get(apiUrl('/api/kg/graph?limit=320'));
    const graphData = response.data || { nodes: [], edges: [] };

    const nodes = new DataSet();
    const edges = new DataSet();
    graphData.nodes.forEach((node) => {
      const nodeType = resolveNodeType(node.type);
      nodes.add({
        id: node.id,
        label: node.label || node.id,
        title: node.description || node.label || node.id,
        color: nodeColors[nodeType] || nodeColors.default,
        shape: 'box',
        font: { size: 14, color: '#333333' },
        borderWidth: 2,
        shadow: true
      });
    });

    graphData.edges.forEach((edge) => {
      edges.add({
        from: edge.from,
        to: edge.to,
        label: edge.label || 'RELATED_TO',
        arrows: 'to'
      });
    });

    const options = {
      layout: {
        improvedLayout: true,
        randomSeed: 42
      },
      nodes: {
        shape: 'box',
        size: 25,
        font: { size: 14 },
        fixed: { x: false, y: false }
      },
      edges: {
        smooth: false,
        length: 280
      },
      physics: {
        enabled: physicsEnabled.value,
        solver: 'barnesHut',
        barnesHut: {
          gravitationalConstant: -9000,
          centralGravity: 0.06,
          springLength: 180,
          springConstant: 0.03,
          damping: 0.28,
          avoidOverlap: 0.45
        },
        stabilization: {
          enabled: true,
          iterations: 1500,
          updateInterval: 50
        },
        maxVelocity: 50,
        minVelocity: 0.1,
        timestep: 0.5
      },
      interaction: {
        hideEdgesOnDrag: true,
        hideNodesOnDrag: false,
        dragNodes: true,
        dragView: true,
        zoomView: true
      }
    };

    // 使用 graphContainer.value 访问 DOM 元素
    network.value = new Network(graphContainer.value, { nodes, edges }, options);

    network.value.on('stabilizationProgress', (params) => {
      console.log('Stabilization progress:', params.iterations, '/', params.total);
    });

    network.value.on('stabilizationIterationsDone', () => {
      console.log('Stabilization finished');
      // 稳定后自动适配视野，减少“初次打开一坨”的观感
      network.value.fit({
        animation: {
          duration: 500,
          easingFunction: 'easeInOutQuad'
        }
      });
    });

  } catch (error) {
    console.error('Failed to load graph data:', error);
  }
};

const togglePhysics = () => {
  physicsEnabled.value = !physicsEnabled.value;
  network.value.setOptions({ physics: { enabled: physicsEnabled.value } });
};

const stabilize = () => {
  network.value.stabilize(100);
};


// 生命周期钩子
onMounted(async () => {
  await loadGraphData();
});

onBeforeUnmount(() => {
  if (network.value) {
    network.value.destroy();
  }
});
</script>

<style scoped>
/* [!code ++] 新增和修改的样式 */
.knowledge-graph {
  display: flex;
  flex-direction: column; /* 垂直排列子元素 */
  /* 设置高度为视口高度减去上下内边距，确保不超出页面 */
  height: calc(100vh - 40px); 
  padding: 20px;
  box-sizing: border-box; /* 让 padding 包含在 height 内 */
}

/* [!code ++] 为图谱容器设置样式 */
#graph-container {
  width: 100%;
  flex-grow: 0.8; /* 核心：让此元素填满所有剩余的垂直空间 */
  border: 1px solid #ccc;
  min-height: 0; /* 在 flex 布局中防止内容溢出的重要技巧 */
}

.controls {
  margin-bottom: 15px;
  flex-shrink: 0; /* 防止控件区域被压缩 */
}

.legend {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  flex-wrap: wrap;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 4px;
  flex-shrink: 0; /* 防止图例区域被压缩 */
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.color-box {
  width: 16px;
  height: 16px;
  border: 2px solid;
  border-radius: 4px;
}
</style>
