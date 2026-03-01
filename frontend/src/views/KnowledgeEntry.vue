<template>
  <div class="kgqa-page">
    <section class="kgqa-header coin-panel">
      <div>
        <h1>知识中心</h1>
        <p>图谱浏览与智能问答双引擎，辅助你理解钱币背景与收藏线索。</p>
      </div>
      <div class="tab-group">
        <button
          class="kgqa-tab"
          :class="{ active: $route.path === '/kgqa' }"
          @click="goKG"
          :disabled="$route.path === '/kgqa'"
        >知识图谱</button>
        <button
          class="kgqa-tab"
          :class="{ active: $route.path === '/kgqa/qa' }"
          @click="goQA"
          :disabled="$route.path === '/kgqa/qa'"
        >知识问答</button>
      </div>
    </section>
    <router-view />
  </div>
</template>

  <script setup>
  import { useRouter, useRoute } from 'vue-router'
  const router = useRouter()
  const route = useRoute()

  const goKG = () => {
    if (route.path !== '/kgqa') {
      router.push('/kgqa')
    }
  }
  const goQA = () => {
    if (route.path !== '/kgqa/qa') {
      router.push('/kgqa/qa')
    }
  }
  </script>

<style scoped>
.kgqa-page {
  display: grid;
  gap: 14px;
}

.kgqa-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  background: linear-gradient(120deg, #fff 0%, #f8f1ea 70%, #f3e7d8 100%);
}

.kgqa-header h1 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.3rem;
}

.kgqa-header p {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: 0.92rem;
}

.tab-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.kgqa-tab {
  font-size: 0.94rem;
  color: var(--primary-color);
  background: #fff;
  border: 1px solid var(--primary-color);
  cursor: pointer;
  padding: 8px 14px;
  border-radius: 999px;
  transition: all 0.2s ease;
}

.kgqa-tab.active,
.kgqa-tab:disabled {
  color: #fff;
  background: var(--primary-color);
  border-color: var(--primary-color);
  cursor: default;
}

.kgqa-tab:not(.active):hover {
  background: #f7ece6;
}

@media (max-width: 860px) {
  .kgqa-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
