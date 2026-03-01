<template>
  <div class="account-container coin-panel">
    <h2>账户信息</h2>

    <div v-if="!authStore.isAuthenticated" class="guest-box">
      <p>当前未登录，登录后可同步收藏和问答记录。</p>
      <div class="btn-row">
        <button class="account-btn" @click="goLogin">立即登录</button>
        <button class="account-btn ghost" @click="goRegister">注册账号</button>
      </div>
    </div>

    <div v-else class="user-box">
      <div class="row-item">
        <span>用户名</span>
        <strong>{{ authStore.username }}</strong>
      </div>
      <div class="row-item">
        <span>登录状态</span>
        <strong class="status-ok">正常</strong>
      </div>
      <div class="row-item">
        <span>身份标识</span>
        <strong>普通用户</strong>
      </div>
      <button class="account-btn logout" @click="logout">退出登录</button>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

const authStore = useAuthStore();
const router = useRouter();

const goLogin = () => router.push('/login');
const goRegister = () => router.push('/register');
const logout = () => {
  authStore.logout();
  router.push('/login');
};
</script>

<style scoped>
.account-container {
  padding: 16px;
}

h2 {
  margin: 0 0 12px;
  color: var(--primary-color);
  font-size: 1.2rem;
}

.guest-box p {
  margin: 0 0 10px;
  color: var(--text-secondary);
}

.btn-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.account-btn {
  padding: 9px 14px;
  border: none;
  border-radius: 8px;
  background: var(--primary-color);
  color: #fff;
  font-size: 0.92rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.account-btn:hover {
  background: var(--primary-hover);
}

.account-btn.ghost {
  background: #fff;
  color: var(--primary-color);
  border: 1px solid var(--primary-color);
}

.account-btn.logout {
  margin-top: 10px;
  background: #b4474a;
}

.user-box {
  display: grid;
  gap: 8px;
}

.row-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f7f2ea;
}

.row-item span {
  color: var(--text-secondary);
}

.row-item strong {
  color: var(--text-main);
}

.status-ok {
  color: #2d6c4f;
}
</style>
