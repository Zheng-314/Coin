<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Capacitor } from '@capacitor/core'

const route = useRoute()
const transition = ref('slide')

watch(() => route.path, (to, from) => {
  transition.value = to.length > (from?.length || 0) ? 'slide' : 'slide-back'
})

const tabs = [
  { path: '/', label: '首页', icon: 'home' },
  { path: '/database', label: '钱币库', icon: 'database' },
  { path: '/identify', label: '鉴定', icon: 'coin' },
  { path: '/knowledge', label: '知识', icon: 'graph' },
  { path: '/me', label: '我的', icon: 'user' },
]
</script>

<template>
  <div class="app-shell">
    <main class="app-body">
      <router-view v-slot="{ Component }">
        <transition :name="transition" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>

    <!-- 底部导航 -->
    <nav class="tabbar">
      <router-link
        v-for="t in tabs"
        :key="t.path"
        :to="t.path"
        class="tab"
        :class="{ active: route.path === t.path }"
      >
        <svg viewBox="0 0 24 24" class="tab-icon">
          <!-- 首页 -->
          <template v-if="t.icon === 'home'">
            <path d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z" />
          </template>
          <!-- 钱币数据库 -->
          <template v-else-if="t.icon === 'database'">
            <ellipse cx="12" cy="5.5" rx="7" ry="3" /><path d="M5 5.5v12c0 1.7 3.1 3 7 3s7-1.3 7-3v-12" /><path d="M5 11.5c0 1.7 3.1 3 7 3s7-1.3 7-3" />
          </template>
          <!-- 钱币 -->
          <template v-else-if="t.icon === 'coin'">
            <circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><path d="M12 9v6M10 10.5h4" />
          </template>
          <!-- 问答 -->
          <template v-else-if="t.icon === 'chat'">
            <path d="M4 5h16v11H8l-4 4z" /><path d="M8 9h8M8 12h5" />
          </template>
          <!-- 图谱 -->
          <template v-else-if="t.icon === 'graph'">
            <circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="8" r="2.5" /><circle cx="10" cy="18" r="2.5" />
            <path d="M8.2 7l7.5 1M7 8.4l2.2 7.2M16.6 10.2l-5 6.3" />
          </template>
          <!-- 我的 -->
          <template v-else>
            <circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 5-5.5 8-5.5s6.5 1.5 8 5.5" />
          </template>
        </svg>
        <span>{{ t.label }}</span>
      </router-link>
    </nav>
  </div>
</template>

<style scoped>
.app-shell { height: 100%; display: flex; flex-direction: column; }
.app-body { flex: 1; overflow-y: auto; }

.tabbar {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  display: flex;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--line);
  height: calc(var(--nav-h) + env(safe-area-inset-bottom, 0px));
  padding-bottom: env(safe-area-inset-bottom, 0px);
  z-index: 100;
}
.tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  text-decoration: none;
  color: var(--text-2);
  font-size: 11px;
  transition: color 0.2s;
}
.tab.active { color: var(--primary); }
.tab-icon { width: 24px; height: 24px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.tab.active .tab-icon { fill: rgba(140,74,47,0.12); }

/* 页面转场 */
.slide-enter-active, .slide-leave-active, .slide-back-enter-active, .slide-back-leave-active { transition: all 0.22s ease; }
.slide-enter-from { opacity: 0; transform: translateX(24px); }
.slide-leave-to { opacity: 0; transform: translateX(-24px); }
.slide-back-enter-from { opacity: 0; transform: translateX(-24px); }
.slide-back-leave-to { opacity: 0; transform: translateX(24px); }
</style>
