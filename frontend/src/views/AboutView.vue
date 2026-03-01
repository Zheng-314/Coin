<template>
  <div class="about-page">
    <section class="hero coin-panel">
      <div>
        <h1><span>缘起与使命</span></h1>
        <p>连接传统金石文化与现代人工智能，帮助更多用户理解钱币背后的历史价值、艺术价值与收藏价值。</p>
      </div>
      <div class="hero-meta coin-panel">
        <h3>版本信息</h3>
        <ul>
          <li><b>系统版本</b><span>v1.0.0</span></li>
          <li><b>数据覆盖</b><span>清代 / 民国 / 古钱</span></li>
          <li><b>核心能力</b><span>鉴别 + 问答 + 估值</span></li>
        </ul>
      </div>
    </section>

    <section class="content-grid">
      <div class="main-block coin-panel">
        <h2>系统简介</h2>
        <p class="intro">
          本平台融合计算机视觉、知识图谱与语言模型能力，围绕“识别真伪、理解历史、辅助收藏”三个目标构建。
          通过标准化拍摄和结构化分析流程，系统可辅助完成钱币的双面识别、版式判断、估值参考与知识解读。
        </p>

        <h2>核心技术</h2>
        <div class="feature-grid">
          <article class="feature-card">
            <h4>深度鉴伪</h4>
            <p>基于双面图像匹配与目标检测，识别关键细节与伪造风险。</p>
          </article>
          <article class="feature-card">
            <h4>版式匹配</h4>
            <p>对关键纹理与文字结构进行比对，输出版式候选与置信度。</p>
          </article>
          <article class="feature-card">
            <h4>估值参考</h4>
            <p>结合等级、稀有度与历史数据，给出可解释的估值区间。</p>
          </article>
          <article class="feature-card">
            <h4>知识问答</h4>
            <p>支持历史背景、铸造故事、收藏文化等内容的智能问答。</p>
          </article>
        </div>

        <h2>鉴赏流程</h2>
        <div class="steps">
          <div class="step"><span>1</span><p>上传正反面高清图片</p></div>
          <div class="step"><span>2</span><p>系统执行鉴别与版式匹配</p></div>
          <div class="step"><span>3</span><p>生成真伪、估值与解释报告</p></div>
          <div class="step"><span>4</span><p>保存个人历史并持续学习</p></div>
        </div>
      </div>

      <aside class="side-block">
        <div class="coin-panel help-card">
          <h3>帮助文档</h3>
          <ul>
            <li>新手入门教程：如何完成首次鉴定</li>
            <li>拍摄技巧指南：提升识别准确率</li>
            <li>常见问题 FAQ：结果解释与使用建议</li>
          </ul>
        </div>

        <div class="coin-panel faq-card">
          <h3>常见问题</h3>
          <details open>
            <summary>系统支持鉴定哪些钱币？</summary>
            <p>目前重点覆盖清末机制币、民国银元及常见古钱币类别。</p>
          </details>
          <details>
            <summary>AI 鉴定结果是否具备法律效力？</summary>
            <p>不具备。系统结果用于学习与参考，重大交易请结合专业机构复核。</p>
          </details>
          <details>
            <summary>图片有什么要求？</summary>
            <p>建议上传光线均匀、角度垂直、背景干净的正反面图片。</p>
          </details>
        </div>

        <div class="disclaimer coin-panel">
          <h3>免责声明</h3>
          <p>本系统基于 AI 模型输出分析结果，仅用于文化学习与收藏参考，不构成投资建议或法律鉴定意见。</p>
        </div>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.about-page {
  display: grid;
  gap: 20px;
}

.hero {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 18px;
  padding: 24px;
  background: linear-gradient(120deg, #fff 0%, #f8f1ea 70%, #f3e7d8 100%);
}

.hero h1 {
  margin: 0;
  color: var(--primary-color);
}

.hero p {
  margin-top: 10px;
  color: var(--text-secondary);
  max-width: 760px;
}

.hero-meta {
  padding: 14px;
}

.hero-meta h3 {
  margin: 0 0 8px;
}

.hero-meta ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.hero-meta li {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px dashed var(--border-color);
  padding: 8px 0;
  font-size: 0.95rem;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 18px;
}

.main-block {
  padding: 22px;
}

.main-block h2 {
  margin: 0 0 12px;
  color: var(--text-main);
  border-left: 4px solid var(--primary-color);
  padding-left: 10px;
}

.intro {
  margin: 0 0 20px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.feature-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px;
  background: #fff;
}

.feature-card h4 {
  margin: 0 0 6px;
  color: var(--primary-color);
}

.feature-card p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.steps {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.step {
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
  text-align: center;
  background: #fff;
}

.step span {
  width: 26px;
  height: 26px;
  display: inline-grid;
  place-items: center;
  border-radius: 999px;
  background: var(--accent-color);
  color: #fff;
  font-weight: 700;
}

.step p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 0.92rem;
}

.side-block {
  display: grid;
  gap: 12px;
}

.help-card,
.faq-card,
.disclaimer {
  padding: 16px;
}

.help-card h3,
.faq-card h3,
.disclaimer h3 {
  margin: 0 0 10px;
  color: var(--primary-color);
}

.help-card ul {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  line-height: 1.7;
}

details {
  border-top: 1px dashed var(--border-color);
  padding: 8px 0;
}

details:first-of-type {
  border-top: none;
  padding-top: 0;
}

summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--text-main);
}

details p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 0.92rem;
}

.disclaimer p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
  font-style: italic;
}

@media (max-width: 1080px) {
  .hero {
    grid-template-columns: 1fr;
  }
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .feature-grid {
    grid-template-columns: 1fr;
  }
  .steps {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
