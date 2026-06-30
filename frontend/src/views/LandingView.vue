<template>
  <main class="landing-page">
    <section class="hero coin-panel">
      <div class="hero-main">
        <p class="hero-tag">古币智能平台</p>
        <h1>鉴泉识珍 · 钱币文化智能鉴定平台</h1>
        <p class="hero-desc">
          聚合钱币数据库、图像鉴定与知识问答，服务于学习研究、收藏入门与日常检索。
        </p>
        <div class="quick-actions">
          <RouterLink to="/predict" class="quick-btn primary">进入智能鉴定</RouterLink>
        </div>
      </div>
      <div class="hero-side coin-panel">
        <h3>您可以在这里做到：</h3>
        <ul>
          <li><b>智能鉴定</b><span>上传双面图片，快速识别</span></li>
          <li><b>钱币数据库</b><span>按朝代/年份/省份筛选</span></li>
          <li><b>知识问答</b><span>支持本地与联网检索</span></li>
        </ul>
      </div>
    </section>

    <section class="entry-grid">
      <RouterLink to="/predict" class="entry-card coin-panel">
        <h3>核心鉴定</h3>
        <p>对钱币正反面图像进行识别，输出分类结果与置信度。</p>
      </RouterLink>
      <RouterLink to="/kgqa/qa" class="entry-card coin-panel">
        <h3>问答助手</h3>
        <p>面向钱币历史与收藏问题的问答助手，支持多种搜索模式。</p>
      </RouterLink>
      <RouterLink to="/database" class="entry-card coin-panel">
        <h3>钱币数据库</h3>
        <p>检索主库藏品，按关键词、朝代、年份、省份、级别快速过滤。</p>
      </RouterLink>
      <RouterLink to="/valuation" class="entry-card coin-panel">
        <h3>估值报告</h3>
        <p>输入钱币名称与品相，生成知识库 + 联网行情结合的估值参考。</p>
      </RouterLink>
      <RouterLink to="/profile" class="entry-card coin-panel">
        <h3>个人中心</h3>
        <p>查看收藏、账户信息与问答记录，管理你的鉴藏足迹。</p>
      </RouterLink>
      <RouterLink to="/about" class="entry-card coin-panel">
        <h3>关于我们</h3>
        <p>了解平台定位、能力边界与使用建议。</p>
      </RouterLink>
    </section>
  </main>
</template>

<script setup>
defineOptions({
  name: 'LandingView'
});
</script>

<style scoped>
.landing-page {
  display: grid;
  gap: 20px;
}

.hero {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 16px;
  padding: 24px;
  background: linear-gradient(120deg, #fff 0%, #f8f1ea 70%, #f2e2cf 100%);
}

.hero-main h1 {
  margin: 8px 0 0;
  color: var(--primary-color);
  font-size: clamp(1.6rem, 3vw, 2.2rem);
}

.hero-tag {
  margin: 0;
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: #efe1d2;
  color: #6a392e;
  font-size: 0.82rem;
}

.hero-desc {
  margin: 12px 0 0;
  color: var(--text-secondary);
  max-width: 760px;
}

.quick-actions {
  margin-top: 18px;
  display: flex;
}

.quick-btn {
  text-decoration: none;
  padding: 13px 26px;
  border: 1px solid var(--primary-color);
  border-radius: 999px;
  background: var(--primary-color);
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  transition: all 0.2s ease;
}

.quick-btn:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

.hero-side {
  padding: 14px;
  background: rgba(255, 255, 255, 0.92);
}

.hero-side h3 {
  margin: 0 0 8px;
  color: var(--primary-color);
}

.hero-side ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.hero-side li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--border-color);
}

.hero-side li:last-child {
  border-bottom: none;
}

.hero-side span {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.entry-card {
  text-decoration: none;
  color: inherit;
  padding: 18px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.entry-card:hover {
  transform: translateY(-3px);
  border-color: var(--accent-color);
  box-shadow: var(--shadow-md);
}

.entry-card h3 {
  margin: 0;
  color: var(--primary-color);
}

.entry-card p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

@media (max-width: 980px) {
  .hero {
    grid-template-columns: 1fr;
  }
  .entry-grid {
    grid-template-columns: 1fr;
  }
}
</style>
