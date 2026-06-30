<template>
  <div class="not-found-page">
    <div class="not-found-card coin-panel">
      <h1 class="error-code">404</h1>
      <p class="error-msg">页面不存在</p>
      <RouterLink to="/" class="back-button">返回首页</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.not-found-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.not-found-card {
  text-align: center;
  padding: 60px 80px;
}

.error-code {
  font-size: 6rem;
  font-weight: 800;
  color: var(--primary-color);
  margin: 0 0 10px;
  line-height: 1;
}

.error-msg {
  font-size: 1.2rem;
  color: var(--text-secondary);
  margin: 0 0 28px;
}

.back-button {
  display: inline-block;
  padding: 10px 32px;
  background: var(--primary-color);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  text-decoration: none;
  font-size: 1rem;
  cursor: pointer;
  transition: opacity 0.2s;
}

.back-button:hover {
  opacity: 0.85;
}
</style>
