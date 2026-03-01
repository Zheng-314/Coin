<script setup>
import { ref, computed } from 'vue';
import { RouterLink, RouterView } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

const authStore = useAuthStore();
const router = useRouter();
const showUserMenu = ref(false);

const userInitials = computed(() => {
  const username = authStore.user?.username || '';
  return username ? username.charAt(0).toUpperCase() : '?';
});

const handleLogout = () => {
  authStore.logout(false);
  showUserMenu.value = false;
  router.push('/');
};

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value;
};

const goToProfile = () => {
  showUserMenu.value = false;
  router.push('/profile');
};

// 点击外部关闭菜单
document.addEventListener('click', (e) => {
  const userMenu = document.querySelector('.user-menu');
  const userAvatar = document.querySelector('.user-avatar');
  if (userMenu && !userMenu.contains(e.target) && !userAvatar.contains(e.target)) {
    showUserMenu.value = false;
  }
});
</script>

<template>
  <header class="top-nav">
    <div class="page-shell nav-inner">
      <RouterLink to="/" class="brand">鉴泉识珍</RouterLink>
      <nav class="nav-links">
        <RouterLink to="/" class="nav-item" active-class="active" exact-active-class="active">首页</RouterLink>
        <RouterLink to="/database" class="nav-item" active-class="active" exact-active-class="active">钱币数据库</RouterLink>
        <RouterLink to="/predict" class="nav-item" active-class="active">智能鉴别</RouterLink>
        <RouterLink to="/valuation" class="nav-item" active-class="active">估值报告</RouterLink>
        <RouterLink to="/kgqa" class="nav-item" active-class="active">知识问答</RouterLink>
        <RouterLink to="/about" class="nav-item" active-class="active">关于我们</RouterLink>
      </nav>
      <div class="user-section">
        <div v-if="authStore.isAuthenticated" class="user-dropdown">
          <div class="user-avatar" @click="toggleUserMenu">
            {{ userInitials }}
          </div>
          <div v-if="showUserMenu" class="user-menu">
            <div class="user-info">
              <div class="user-name">{{ authStore.user?.username }}</div>
            </div>
            <div class="menu-divider"></div>
            <div class="menu-item" @click="goToProfile">
              <span class="menu-icon">👤</span>
              <span>个人中心</span>
            </div>
            <div class="menu-item" @click="handleLogout">
              <span class="menu-icon">🚪</span>
              <span>退出登录</span>
            </div>
          </div>
        </div>
        <RouterLink v-else to="/login" class="login-btn">登录</RouterLink>
      </div>
    </div>
  </header>

  <main class="main-content page-shell">
    <RouterView v-slot="{ Component }">
      <KeepAlive include="HomeView,LandingView">
        <component :is="Component" />
      </KeepAlive>
    </RouterView>
  </main>

  <footer class="site-footer">
    <div class="page-shell">
      <p>古钱币智能鉴定与知识服务平台</p>
    </div>
  </footer>
</template>

<style scoped>
.top-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border-bottom: 2px solid var(--accent-color);
}

.nav-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 70px;
}

.brand {
  font-size: 1.5rem;
  text-decoration: none;
  color: var(--primary-color);
  font-weight: 700;
  letter-spacing: 1px;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-item {
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: var(--text-main);
  transition: all 0.2s ease;
}

.nav-item:hover {
  background: #f4ece5;
  color: var(--primary-color);
}

.nav-item.active {
  background: var(--primary-color);
  color: #fff;
}

.user-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-dropdown {
  position: relative;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(139, 58, 58, 0.2);
}

.user-avatar:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(139, 58, 58, 0.3);
}

.user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: white;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  min-width: 180px;
  z-index: 1001;
  overflow: hidden;
}

.user-info {
  padding: 16px;
  background: var(--bg-color);
}

.user-name {
  font-weight: 600;
  color: var(--text-main);
  font-size: 0.95rem;
}

.menu-divider {
  height: 1px;
  background: var(--border-color);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s ease;
  color: var(--text-main);
  font-size: 0.9rem;
}

.menu-item:hover {
  background: #f8f6f2;
  color: var(--primary-color);
}

.menu-icon {
  font-size: 1.1rem;
}

.login-btn {
  padding: 8px 20px;
  border-radius: 20px;
  text-decoration: none;
  color: white;
  background: var(--primary-color);
  font-weight: 500;
  transition: all 0.2s ease;
}

.login-btn:hover {
  background: var(--primary-hover);
  transform: translateY(-1px);
}

.main-content {
  min-height: calc(100vh - 140px);
  padding: 24px 0 48px;
}

.site-footer {
  border-top: 1px solid var(--border-color);
  padding: 18px 0 26px;
  color: var(--text-secondary);
  text-align: center;
  font-size: 0.95rem;
}

@media (max-width: 920px) {
  .nav-inner {
    flex-direction: column;
    justify-content: center;
    gap: 10px;
    padding: 10px 0;
  }

  .nav-links {
    flex-wrap: wrap;
    justify-content: center;
  }

  .user-section {
    margin-top: 10px;
  }
}
</style>
