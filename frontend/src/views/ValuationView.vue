<template>
  <main class="valuation-page">
    <section class="hero coin-panel">
      <h1>钱币估值报告</h1>
      <p>建议先在“智能鉴别”上传两张图识别，再到这里确认名称与品相后生成估值。</p>
    </section>

    <section class="form-wrap coin-panel">
      <div class="form-grid">
        <div class="field">
          <label for="coinName">钱币名称</label>
          <input
            id="coinName"
            v-model.trim="coinName"
            type="text"
            placeholder="例如：袁大头三年"
            @keyup.enter="submitValuation"
          />
        </div>

        <div class="field">
          <label for="coinGrade">品相等级</label>
          <input
            id="coinGrade"
            v-model.trim="coinGrade"
            type="text"
            placeholder="例如：PCGS XF45"
            @keyup.enter="submitValuation"
          />
        </div>
      </div>

      <button class="submit-btn" :disabled="loading || !coinName || !coinGrade" @click="submitValuation">
        {{ loading ? '生成中...' : '生成估值报告' }}
      </button>
    </section>

    <section class="result-wrap coin-panel">
      <h2>报告结果</h2>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div v-else-if="reportHtml" class="markdown-body" v-html="reportHtml"></div>
      <p v-else class="empty-text">提交后将在这里展示估值报告。</p>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import http from '@/config/http';
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt({ html: false });
const route = useRoute();

const coinName = ref(String(route.query.coinName || ''));
const coinGrade = ref(String(route.query.coinGrade || ''));
const loading = ref(false);
const error = ref('');
const reportMarkdown = ref('');

const reportHtml = computed(() => (reportMarkdown.value ? md.render(reportMarkdown.value) : ''));

const submitValuation = async () => {
  if (!coinName.value || !coinGrade.value || loading.value) return;

  loading.value = true;
  error.value = '';
  reportMarkdown.value = '';

  try {
    const response = await http.post('/api/valuation', {
      coinName: coinName.value,
      coinGrade: coinGrade.value
    });

    reportMarkdown.value = response.data?.valuation || '未返回估值内容。';
  } catch (err) {
    error.value = err.response?.data?.error || '估值请求失败，请检查后端服务状态。';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.valuation-page {
  display: grid;
  gap: 16px;
}

.hero {
  padding: 20px;
  background: linear-gradient(120deg, #fff 0%, #f8f1ea 70%, #f3e7d8 100%);
}

.hero h1 {
  margin: 0;
  color: var(--primary-color);
}

.hero p {
  margin: 8px 0 0;
  color: var(--text-secondary);
}

.form-wrap {
  padding: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 6px;
}

.field label {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.field input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  font-size: 0.95rem;
  outline: none;
}

.field input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(139, 58, 58, 0.1);
}

.submit-btn {
  margin-top: 12px;
  border: none;
  background: var(--primary-color);
  color: #fff;
  padding: 10px 16px;
  border-radius: 999px;
  cursor: pointer;
}

.submit-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.result-wrap {
  padding: 16px;
}

.result-wrap h2 {
  margin: 0;
  color: var(--primary-color);
}

.empty-text {
  margin: 12px 0 0;
  color: var(--text-secondary);
}

.error-text {
  margin: 12px 0 0;
  color: #b33939;
}

.markdown-body {
  margin-top: 12px;
  line-height: 1.7;
}

@media (max-width: 760px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
