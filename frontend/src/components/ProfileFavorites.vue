<template>
  <div class="favorites-container coin-panel">
    <div class="fav-head">
      <h2>我的收藏</h2>
      <span class="fav-count">共 {{ favorites.length }} 条</span>
    </div>

    <p v-if="loading" class="state-text">正在加载收藏列表...</p>

    <div v-else-if="error" class="error-wrap">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="loadFavorites">重试</button>
    </div>

    <div v-else-if="favorites.length > 0" class="fav-grid">
      <router-link
        v-for="item in favorites"
        :key="item.pid"
        :to="`/artifact/${item.pid}`"
        class="fav-card"
      >
        <div class="fav-title">{{ item.title || '未命名钱币' }}</div>
        <div class="fav-meta">
          <span>收藏编号</span>
          <b>#{{ item.pid }}</b>
        </div>
      </router-link>
    </div>

    <div v-else class="empty-wrap">
      <p>你还没有收藏任何钱币。</p>
      <router-link to="/" class="empty-link">去钱币数据库挑选</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import http from '@/config/http';
import { useAuthStore } from '@/stores/auth';

const favorites = ref([]);
const loading = ref(false);
const error = ref(null);
const authStore = useAuthStore();

const loadFavorites = async () => {
  if (!authStore.isAuthenticated) return;
  loading.value = true;
  error.value = null;
  try {
    const response = await http.get('/api/user-actions/favorite');
    favorites.value = Array.isArray(response.data) ? response.data : [];
  } catch (e) {
    console.error('获取收藏列表失败:', e);
    error.value = '获取收藏列表失败，请稍后重试。';
  } finally {
    loading.value = false;
  }
};

onMounted(loadFavorites);
</script>

<style scoped>
.favorites-container {
  padding: 16px;
}

.fav-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}

.fav-head h2 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.2rem;
}

.fav-count {
  padding: 4px 10px;
  border-radius: 999px;
  background: #f5ece5;
  color: #7d4c3b;
  font-size: 0.8rem;
}

.state-text {
  color: var(--text-secondary);
  margin: 0;
}

.fav-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.fav-card {
  text-decoration: none;
  color: inherit;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px;
  background: linear-gradient(180deg, #fff 0%, #fbf6ef 100%);
  transition: all 0.2s ease;
}

.fav-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent-color);
  box-shadow: var(--shadow-sm);
}

.fav-title {
  color: var(--text-main);
  font-weight: 600;
  line-height: 1.5;
  min-height: 44px;
}

.fav-meta {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  color: var(--text-secondary);
  font-size: 0.84rem;
}

.fav-meta b {
  color: var(--primary-color);
}

.empty-wrap {
  padding: 16px;
  text-align: center;
  color: var(--text-secondary);
  border: 1px dashed var(--border-color);
  border-radius: 10px;
}

.empty-wrap p {
  margin: 0;
}

.error-wrap {
  padding: 16px;
  text-align: center;
  color: #b33939;
  border: 1px solid #f5c6cb;
  border-radius: 10px;
  background: #fdecea;
}

.error-wrap p {
  margin: 0 0 8px;
}

.retry-btn {
  padding: 6px 16px;
  border: 1px solid #b33939;
  background: #fff;
  color: #b33939;
  border-radius: 999px;
  cursor: pointer;
  font-size: 0.85rem;
}

.retry-btn:hover {
  background: #b33939;
  color: #fff;
}

.empty-link {
  margin-top: 8px;
  display: inline-block;
  color: var(--primary-color);
  text-decoration: none;
  font-weight: 600;
}

@media (max-width: 760px) {
  .fav-grid {
    grid-template-columns: 1fr;
  }
}
</style>
