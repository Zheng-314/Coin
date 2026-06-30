<template>
  <div class="auth-page">
    <div class="auth-card coin-panel">
      <section class="auth-visual">
        <div class="visual-content">
          <p class="visual-kicker">鉴泉识珍</p>
          <h2>欢迎回到藏家档案</h2>
          <p>连接历史与科技，为每一枚古钱币赋予数字新生。</p>
        </div>
      </section>

      <section class="auth-form-panel">
        <h1>欢迎回来</h1>
        <p class="subtitle">请登录账号继续使用鉴定、数据库与问答服务</p>

        <p v-if="errorMessage" class="alert-error">{{ errorMessage }}</p>

        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="username">用户名</label>
            <input id="username" v-model.trim="username" type="text" placeholder="请输入用户名" required />
          </div>
          <div class="form-group">
            <label for="password">密码</label>
            <input id="password" v-model="password" type="password" placeholder="请输入密码" required />
          </div>
          <button type="submit" class="submit-btn" :disabled="isLoading">
            {{ isLoading ? '登录中...' : '立即登录' }}
          </button>
        </form>

        <div class="switch-tip">
          <span>还没有账号？</span>
          <button type="button" class="switch-btn" @click="goRegister">注册新账号</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import http from '@/config/http';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

const username = ref('');
const password = ref('');
const errorMessage = ref('');
const isLoading = ref(false);
const authStore = useAuthStore();
const router = useRouter();

const handleLogin = async () => {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const response = await http.post('/api/users/login', {
      username: username.value,
      password: password.value
    });

    authStore.login(response.data);

  } catch (error) {
    console.error('登录失败:', error?.response?.data?.message || error.message);
    errorMessage.value = error?.response?.data?.message || '登录失败，请检查后端服务或凭证。';
  }finally{
    isLoading.value = false;
  }
};

const goRegister = () => {
  router.push('/register');
};
</script>

<style scoped>
.auth-page {
  min-height: 78vh;
  display: grid;
  place-items: center;
  padding: 18px 0;
}

.auth-card {
  width: min(960px, 100%);
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  overflow: hidden;
}

.auth-visual {
  position: relative;
  background: linear-gradient(135deg, #2c3e50 0%, #111 100%);
  color: #fff;
  padding: 34px 28px;
  display: flex;
  align-items: flex-end;
}

.auth-visual::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='0.06'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zM36 4V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/svg%3E");
}

.visual-content {
  position: relative;
  z-index: 1;
}

.visual-kicker {
  margin: 0;
  font-size: 0.85rem;
  opacity: 0.75;
}

.visual-content h2 {
  margin: 8px 0 0;
  font-size: 1.7rem;
}

.visual-content p {
  margin: 10px 0 0;
  opacity: 0.85;
  line-height: 1.7;
}

.auth-form-panel {
  background: #fff;
  padding: 30px 30px 24px;
}

.auth-form-panel h1 {
  margin: 0;
  color: var(--text-main);
  font-size: 1.7rem;
}

.subtitle {
  margin: 8px 0 14px;
  color: var(--text-secondary);
  font-size: 0.93rem;
}

.alert-error {
  margin: 0 0 12px;
  border-left: 4px solid #c0392b;
  background: #fff4f2;
  color: #c0392b;
  padding: 10px;
  border-radius: 6px;
  font-size: 0.9rem;
}

.form-group {
  margin-bottom: 12px;
}

label {
  display: block;
  margin-bottom: 5px;
  color: var(--text-main);
  font-size: 0.9rem;
}

input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  outline: none;
  font-size: 0.95rem;
}

input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px rgba(197, 160, 101, 0.15);
}

.submit-btn {
  width: 100%;
  margin-top: 6px;
  border: none;
  background: var(--primary-color);
  color: #fff;
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: background 0.2s;
}

.submit-btn:hover {
  background: var(--primary-hover);
}

.submit-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.switch-tip {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.switch-btn {
  border: none;
  background: transparent;
  color: var(--primary-color);
  font-weight: 600;
  cursor: pointer;
}

.switch-btn:hover {
  text-decoration: underline;
}

@media (max-width: 900px) {
  .auth-card {
    grid-template-columns: 1fr;
  }
  .auth-visual {
    min-height: 150px;
    align-items: center;
  }
}
</style>
