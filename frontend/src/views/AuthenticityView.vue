<template>
  <div class="auth-page">
    <div class="page-shell">
      <header class="head">
        <h1>真伪初筛</h1>
        <p class="sub">上传钱币正反面，系统提示应当核查的部位与特征</p>
        <p class="notice">
          本功能只做初筛提示，<strong>不构成真伪结论</strong>。高价值藏品请送专业评级机构出具正式结论。
        </p>
      </header>

      <div class="status-bar" :class="modelReady ? 'ok' : 'warn'">
        <span class="dot"></span>
        <span v-if="modelReady">真伪模型已接入，可给出风险等级</span>
        <span v-else>真伪模型尚未接入，当前提供部位级提示（可正常使用）</span>
      </div>

      <div class="upload-row">
        <div class="upload-card" @click="fileInput1?.click()" @dragover.prevent @drop.prevent="onDrop($event, 1)">
          <input type="file" ref="fileInput1" accept="image/*" @change="onPick($event, 1)" />
          <img v-if="preview1" :src="preview1" alt="正面" />
          <div v-else class="ph"><span>＋</span><p>正面（价值面）</p></div>
        </div>
        <div class="upload-card" @click="fileInput2?.click()" @dragover.prevent @drop.prevent="onDrop($event, 2)">
          <input type="file" ref="fileInput2" accept="image/*" @change="onPick($event, 2)" />
          <img v-if="preview2" :src="preview2" alt="反面" />
          <div v-else class="ph"><span>＋</span><p>反面（图案面）</p></div>
        </div>
      </div>

      <div class="form-row">
        <label for="variety">版式（可选，填了会优先展示相关特征）</label>
        <input id="variety" v-model="variety" placeholder="例如：机制银币 > 地方省造 > 北洋造 > 光绪34年 > 七钱二分 > 开云" />
      </div>

      <button class="submit" :disabled="!file1 || !file2 || loading" @click="submit">
        {{ loading ? '分析中…' : '开始初筛' }}
      </button>
      <p v-if="error" class="err">{{ error }}</p>

      <section v-if="result" class="result">
        <div class="verdict" :class="riskClass">
          <div class="verdict-main">
            <span class="label">风险等级</span>
            <span class="value">{{ riskText }}</span>
          </div>
          <p class="verdict-msg">{{ result.message }}</p>
        </div>

        <h2>应当核查的部位</h2>
        <p class="hint-sub">对照实物逐项查看；提示内容来自知识库原文，未作改写。</p>

        <div class="checks">
          <div v-for="chk in result.checks" :key="chk.part" class="check" :class="{ empty: !chk.hints.length }">
            <div class="check-head">
              <span class="part">{{ chk.part }}</span>
              <span class="state">{{ chk.hints.length ? chk.result : '暂无资料' }}</span>
            </div>
            <ul v-if="chk.hints.length">
              <li v-for="(h, i) in chk.hints" :key="i">
                {{ h.text }}
                <span v-if="h.judged" class="tag">含判断</span>
              </li>
            </ul>
            <p v-else class="none">知识库暂无该部位的鉴别资料</p>
          </div>
        </div>

        <p class="disclaimer">{{ result.disclaimer }}</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:5001'

const fileInput1 = ref(null)
const fileInput2 = ref(null)
const file1 = ref(null)
const file2 = ref(null)
const preview1 = ref('')
const preview2 = ref('')
const variety = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)
const caps = ref(null)

const modelReady = computed(() => Boolean(caps.value?.model?.ready))

const riskText = computed(() => {
  const r = result.value?.risk_level
  if (!result.value || result.value.status !== 'ok') return '未评级'
  if (r === '高') return '偏高风险'
  if (r === '中') return '需重点核查'
  return '未见明显疑点'
})

const riskClass = computed(() => {
  const r = result.value?.risk_level
  if (!result.value || result.value.status !== 'ok') return 'unknown'
  return r === '高' ? 'high' : r === '中' ? 'mid' : 'low'
})

onMounted(async () => {
  try {
    const { data } = await axios.get(`${API_BASE_URL}/api/authenticity/capabilities`)
    caps.value = data
  } catch (e) {
    // 能力查询失败不阻塞页面
  }
})

function setFile(n, file) {
  if (!file || !file.type?.startsWith('image/')) {
    error.value = '请选择图片文件'
    return
  }
  error.value = ''
  const reader = new FileReader()
  reader.onload = (ev) => {
    if (n === 1) { file1.value = file; preview1.value = ev.target.result }
    else { file2.value = file; preview2.value = ev.target.result }
  }
  reader.readAsDataURL(file)
}

function onPick(e, n) { setFile(n, e.target.files?.[0]) }
function onDrop(e, n) { setFile(n, e.dataTransfer.files?.[0]) }

async function submit() {
  if (!file1.value || !file2.value) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const fd = new FormData()
    fd.append('image1', file1.value)
    fd.append('image2', file2.value)
    if (variety.value.trim()) fd.append('variety', variety.value.trim())

    const { data } = await axios.post(`${API_BASE_URL}/api/authenticity/check`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
    result.value = data
  } catch (e) {
    error.value = e.response?.data?.message || '分析失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page { padding: 32px 0 64px; }
.head h1 { font-size: 26px; margin: 0 0 6px; }
.head .sub { color: #666; margin: 0 0 10px; }
.notice {
  background: #fff8e6; border: 1px solid #ffe1a8; color: #7a5c00;
  padding: 10px 12px; border-radius: 8px; font-size: 13px; margin: 0 0 18px;
}
.status-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-radius: 8px; font-size: 13px; margin-bottom: 18px;
}
.status-bar.ok { background: #eaf7ee; color: #1d6b35; border: 1px solid #bfe5cb; }
.status-bar.warn { background: #f2f4f7; color: #555; border: 1px solid #dde1e6; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.upload-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.upload-card {
  position: relative; aspect-ratio: 1 / 1; border: 1px dashed #c8cdd4; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  background: #fafbfc; overflow: hidden;
}
.upload-card:hover { border-color: #8a94a3; }
.upload-card input { display: none; }
.upload-card img { width: 100%; height: 100%; object-fit: cover; }
.ph { text-align: center; color: #9099a5; }
.ph span { font-size: 30px; line-height: 1; }
.ph p { margin: 8px 0 0; font-size: 13px; }
.form-row { margin: 18px 0 6px; }
.form-row label { display: block; font-size: 13px; color: #555; margin-bottom: 6px; }
.form-row input {
  width: 100%; padding: 10px 12px; border: 1px solid #d8dde4; border-radius: 8px; font-size: 13px;
}
.submit {
  margin-top: 14px; width: 100%; padding: 13px; border: none; border-radius: 10px;
  background: #1f3864; color: #fff; font-size: 15px; cursor: pointer;
}
.submit:disabled { background: #b9c0cb; cursor: not-allowed; }
.err { color: #c0392b; font-size: 13px; margin-top: 10px; }
.result { margin-top: 28px; }
.verdict { padding: 14px 16px; border-radius: 10px; border: 1px solid #e2e6ec; background: #fafbfc; }
.verdict-main { display: flex; align-items: baseline; gap: 10px; }
.verdict-main .label { font-size: 12px; color: #6b7480; }
.verdict-main .value { font-size: 22px; font-weight: 700; }
.verdict.high .value { color: #b03030; }
.verdict.mid .value { color: #a86a00; }
.verdict.low .value { color: #1d6b35; }
.verdict.unknown .value { color: #6b7480; font-size: 17px; }
.verdict-msg { margin: 8px 0 0; font-size: 13px; color: #555; }
.result h2 { font-size: 17px; margin: 26px 0 4px; }
.hint-sub { font-size: 12px; color: #8a9099; margin: 0 0 14px; }
.checks { display: grid; gap: 12px; }
.check { border: 1px solid #e6e9ee; border-radius: 10px; padding: 12px 14px; background: #fff; }
.check.empty { background: #fafafa; }
.check-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.part { font-weight: 700; font-size: 14px; }
.state { font-size: 12px; color: #8a9099; }
.check ul { margin: 0; padding-left: 18px; }
.check li { font-size: 13px; line-height: 1.6; margin-bottom: 6px; color: #333; }
.tag {
  display: inline-block; margin-left: 6px; padding: 0 6px; border-radius: 4px;
  background: #eef3ff; color: #3557a8; font-size: 11px;
}
.none { margin: 0; font-size: 12px; color: #a0a6ae; }
.disclaimer {
  margin-top: 22px; padding: 12px 14px; background: #f7f8fa; border-radius: 8px;
  font-size: 12px; color: #6b7480; line-height: 1.6;
}
@media (max-width: 640px) {
  .upload-row { grid-template-columns: 1fr; }
}
</style>
