<template>
  <div class="profile-page">
    <section class="profile-hero coin-panel">
      <div class="hero-content">
        <div class="avatar-circle">{{ avatarText }}</div>
        <div class="hero-text">
          <h1>{{ displayName }}</h1>
          <div class="meta-row">
            <span class="member-badge">{{ levelName }}</span>
            <span class="meta-tip">积分 {{ score }}</span>
          </div>
          <p class="meta-tip">欢迎回来，继续完善你的钱币鉴藏档案。</p>
        </div>
      </div>
      <div class="hero-actions">
        <button class="hero-btn" @click="goFavorites">查看收藏</button>
        <button class="hero-btn ghost" @click="goAccount">账户设置</button>
      </div>
    </section>

    <section class="profile-overview">
      <article class="overview-card coin-panel">
        <p>收藏数量</p>
        <h3>{{ favoritesCount }}</h3>
      </article>
      <article class="overview-card coin-panel">
        <p>问答条数</p>
        <h3>{{ chatCount }}</h3>
      </article>
      <article class="overview-card coin-panel">
        <p>账户状态</p>
        <h3>{{ authStore.isAuthenticated ? '已登录' : '未登录' }}</h3>
      </article>
    </section>

    <section class="profile-main">
      <div class="profile-left">
        <div class="profile-nav coin-panel">
          <button
            class="profile-tab"
            :class="{ active: $route.path === '/profile' || $route.path === '/profile/' }"
            @click="goFavorites"
            :disabled="$route.path === '/profile' || $route.path === '/profile/'"
          >我的收藏</button>
          <button
            class="profile-tab"
            :class="{ active: $route.path === '/profile/account' }"
            @click="goAccount"
            :disabled="$route.path === '/profile/account'"
          >账户信息</button>
        </div>
        <router-view />
      </div>

      <aside class="profile-right coin-panel">
        <h3>我的成就</h3>
        <p class="achv-level">{{ levelName }}</p>
        <div class="progress-track">
          <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
        </div>
        <p class="achv-tip">距离下一等级还需 {{ pointsToNext }} 积分</p>

        <div class="badge-grid">
          <div class="badge-item" :class="{ on: favoritesCount >= 3 }">收藏新星</div>
          <div class="badge-item" :class="{ on: chatCount >= 10 }">问答达人</div>
          <div class="badge-item" :class="{ on: score >= 300 }">资深藏家</div>
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import axios from 'axios';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { apiUrl } from '@/config/api';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const favoritesCount = ref(0);
const chatCount = ref(0);

const displayName = computed(() => authStore.username || '游客');
const avatarText = computed(() => (displayName.value || '游').slice(0, 1).toUpperCase());
const score = computed(() => favoritesCount.value * 20 + chatCount.value * 2);

const levelName = computed(() => {
  if (score.value >= 600) return '大师藏家';
  if (score.value >= 300) return '资深藏家';
  if (score.value >= 120) return '进阶鉴赏家';
  return '初级鉴赏家';
});

const nextLevelScore = computed(() => {
  if (score.value < 120) return 120;
  if (score.value < 300) return 300;
  if (score.value < 600) return 600;
  return 600;
});

const pointsToNext = computed(() => Math.max(0, nextLevelScore.value - score.value));
const progress = computed(() => {
  if (score.value < 120) return Math.round((score.value / 120) * 100);
  if (score.value < 300) return Math.round(((score.value - 120) / 180) * 100);
  if (score.value < 600) return Math.round(((score.value - 300) / 300) * 100);
  return 100;
});

const goFavorites = () => {
  if (route.path !== '/profile' && route.path !== '/profile/') router.push('/profile');
};

const goAccount = () => {
  if (route.path !== '/profile/account') router.push('/profile/account');
};

onMounted(async () => {
  if (!authStore.isAuthenticated) return;
  const token = localStorage.getItem('token');
  try {
    const [favRes, chatRes] = await Promise.all([
      axios.get(apiUrl('/api/user-actions/favorite'), { headers: { Authorization: token } }),
      axios.get(apiUrl('/api/chat/history'), { headers: { Authorization: token } })
    ]);
    favoritesCount.value = Array.isArray(favRes.data) ? favRes.data.length : 0;
    chatCount.value = Array.isArray(chatRes.data) ? chatRes.data.length : 0;
  } catch (error) {
    console.error('加载个人中心概览失败:', error);
  }
});
</script>

<style scoped>
.profile-page {
  display: grid;
  gap: 16px;
}

.profile-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: linear-gradient(135deg, #2f3947 0%, #59697a 100%);
  color: #fff;
  border: none;
}

.hero-content {
  display: flex;
  align-items: center;
  gap: 14px;
}

.avatar-circle {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--accent-color);
  color: #fff;
  font-size: 1.8rem;
  font-weight: 700;
  border: 3px solid rgba(255, 255, 255, 0.3);
}

.hero-text h1 {
  margin: 0;
  font-size: 1.4rem;
}

.meta-row {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.member-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
  font-size: 0.82rem;
}

.meta-tip {
  margin: 6px 0 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.88rem;
}

.hero-actions {
  display: grid;
  gap: 8px;
}

.hero-btn {
  border: none;
  border-radius: 10px;
  background: #fff;
  color: #2f3947;
  padding: 9px 14px;
  cursor: pointer;
  font-weight: 600;
}

.hero-btn.ghost {
  background: transparent;
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.45);
}

.profile-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.overview-card {
  padding: 14px 16px;
}

.overview-card p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.88rem;
}

.overview-card h3 {
  margin: 6px 0 0;
  color: var(--primary-color);
  font-size: 1.5rem;
}

.profile-main {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 12px;
}

.profile-left {
  display: grid;
  gap: 12px;
}

.profile-nav {
  display: flex;
  gap: 10px;
  padding: 10px;
}

.profile-tab {
  font-size: 0.95rem;
  color: var(--primary-color);
  background: none;
  border: 1px solid var(--primary-color);
  cursor: pointer;
  padding: 7px 14px;
  border-radius: 999px;
  transition: all 0.2s;
}

.profile-tab.active,
.profile-tab:disabled {
  color: #fff;
  background: var(--primary-color);
  border-color: var(--primary-color);
  cursor: default;
}

.profile-tab:not(.active):hover {
  background: #f7ece6;
}

.profile-right {
  padding: 16px;
  align-self: start;
}

.profile-right h3 {
  margin: 0;
  color: var(--primary-color);
}

.achv-level {
  margin: 8px 0 0;
  font-weight: 700;
}

.progress-track {
  margin-top: 10px;
  height: 8px;
  border-radius: 999px;
  background: #efe6d9;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-color), var(--primary-color));
}

.achv-tip {
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.badge-grid {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}

.badge-item {
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 0.86rem;
  background: #f5f1ea;
  color: #9a8f7f;
}

.badge-item.on {
  background: #f8edd9;
  color: #7a5414;
}

@media (max-width: 960px) {
  .profile-overview {
    grid-template-columns: 1fr;
  }
  .profile-main {
    grid-template-columns: 1fr;
  }
  .profile-hero {
    flex-direction: column;
    align-items: flex-start;
  }
  .hero-actions {
    width: 100%;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
