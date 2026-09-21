<script setup>
import { ref } from 'vue'
import GraphView from './GraphView.vue'
import QAView from './QAView.vue'
const tab = ref('graph')
</script>

<template>
  <div class="knowledge-page">
    <div class="page head">
      <div class="topbar"><div><h1>知识中心</h1><div class="sub">图谱浏览与智能问答双引擎</div></div></div>
      <div class="switcher">
        <button :class="{on:tab==='graph'}" @click="tab='graph'">知识图谱</button>
        <button :class="{on:tab==='qa'}" @click="tab='qa'">知识问答</button>
      </div>
    </div>
    <GraphView v-if="tab==='graph'" embedded />
    <QAView v-else embedded />
  </div>
</template>

<style scoped>
.head { padding-bottom:0; min-height:0; }
.switcher { display:flex; border:1px solid var(--line); border-radius:12px; overflow:hidden; background:#fff; }
.switcher button { flex:1; border:0; background:transparent; min-height:42px; color:var(--text-2); font-size:14px; }
.switcher button.on { background:var(--primary); color:#fff; font-weight:700; }
.knowledge-page :deep(.page) { padding-top:8px; }
</style>
