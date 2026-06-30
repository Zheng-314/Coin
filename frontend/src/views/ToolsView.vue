<template>
  <div class="tools-page">
    <div v-if="toast.show" :class="['toast', toast.type]">{{ toast.message }}</div>
    <div class="tabs">
      <button :class="{ active: tab === 'batch' }" @click="tab = 'batch'">📦 批量鉴定</button>
      <button :class="{ active: tab === 'history' }" @click="tab = 'history'">📈 历史行情</button>
    </div>

    <!-- 批量鉴定 -->
    <div v-if="tab === 'batch'" class="tab-content coin-panel">
      <h2>批量鉴定</h2>
      <p class="desc">上传多组钱币正反面图片，一次性获取所有鉴定结果。</p>

      <div class="batch-upload">
        <div v-for="(group, idx) in batchGroups" :key="idx" class="batch-group">
          <span class="group-label">第{{ idx + 1 }}组</span>
          <label class="file-label">
            <input type="file" accept="image/*" @change="handleBatchFile($event, idx, 1)" />
            {{ group.file1 ? '✅ 正面' : '📷 正面' }}
          </label>
          <label class="file-label">
            <input type="file" accept="image/*" @change="handleBatchFile($event, idx, 2)" />
            {{ group.file2 ? '✅ 反面' : '📷 反面' }}
          </label>
          <button class="remove-btn" @click="removeGroup(idx)" v-if="batchGroups.length > 1">×</button>
        </div>
        <button class="add-btn" @click="addGroup">+ 添加一组</button>
      </div>

      <button class="submit-btn" @click="submitBatch" :disabled="batchLoading">
        {{ batchLoading ? '鉴定中...' : '开始批量鉴定' }}
      </button>

      <div v-if="batchResults.length" class="batch-results">
        <h3>鉴定结果</h3>
        <table>
          <tr><th>序号</th><th>鉴定结果</th><th>置信度</th><th>状态</th></tr>
          <tr v-for="r in batchResults" :key="r.index">
            <td>{{ r.index + 1 }}</td>
            <td>{{ r.top1?.name || '-' }}</td>
            <td>{{ r.top1 ? r.top1.confidence + '%' : '-' }}</td>
            <td :class="{ error: r.error }">{{ r.error || '成功' }}</td>
          </tr>
        </table>
        <button class="export-btn" @click="exportBatchCSV">导出CSV</button>
      </div>
    </div>

    <!-- 历史行情 -->
    <div v-if="tab === 'history'" class="tab-content coin-panel">
      <h2>历史行情追踪</h2>
      <p class="desc">记录钱币价格变化，追踪市场行情。</p>

      <div class="add-record">
        <input v-model="newRecord.coinName" placeholder="钱币名称" />
        <input v-model="newRecord.grade" placeholder="品相（如AU、VF）" />
        <input v-model.number="newRecord.price" type="number" placeholder="价格（元）" />
        <input v-model="newRecord.note" placeholder="备注" />
        <button @click="addPriceRecord" :disabled="!newRecord.coinName">记录</button>
      </div>

      <div v-if="priceHistory.length" class="history-list">
        <table>
          <tr><th>时间</th><th>钱币</th><th>品相</th><th>价格</th><th>备注</th><th>操作</th></tr>
          <tr v-for="r in priceHistory" :key="r.id">
            <td>{{ formatDate(r.timestamp) }}</td>
            <td>{{ r.coinName }}</td>
            <td>{{ r.grade || '-' }}</td>
            <td>¥{{ r.price || '-' }}</td>
            <td>{{ r.note || '-' }}</td>
            <td><button class="del-btn" @click="deletePriceRecord(r.id)">删除</button></td>
          </tr>
        </table>
      </div>
      <p v-else class="empty">暂无记录，添加第一条价格记录吧。</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import http from '@/config/http'

const tab = ref('batch')

// ========== Toast 通知 ==========
const toast = ref({ show: false, message: '', type: 'info' })
let toastTimer = null
const showToast = (message, type = 'info') => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, message, type }
  toastTimer = setTimeout(() => { toast.value.show = false }, 3000)
}

// ========== 批量鉴定 ==========
const batchGroups = ref([{ file1: null, file2: null }])
const batchLoading = ref(false)
const batchResults = ref([])

const addGroup = () => {
  batchGroups.value.push({ file1: null, file2: null })
}

const removeGroup = (idx) => {
  batchGroups.value.splice(idx, 1)
}

const handleBatchFile = (event, groupIdx, slot) => {
  const file = event.target.files[0]
  if (!file) return
  if (slot === 1) batchGroups.value[groupIdx].file1 = file
  else batchGroups.value[groupIdx].file2 = file
}

const submitBatch = async () => {
  batchLoading.value = true
  batchResults.value = []

  const formData = new FormData()
  batchGroups.value.forEach((g, idx) => {
    if (g.file1) formData.append(`image1_${idx}`, g.file1)
    if (g.file2) formData.append(`image2_${idx}`, g.file2)
  })

  try {
    const resp = await http.post('/api/predict/batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    batchResults.value = resp.data.results || []
  } catch (err) {
    showToast('批量鉴定失败: ' + (err.response?.data?.error || err.message), 'error')
  } finally {
    batchLoading.value = false
  }
}

const exportBatchCSV = () => {
  if (!batchResults.value.length) return
  let csv = '序号,鉴定结果,置信度,状态\n'
  batchResults.value.forEach(r => {
    csv += `${r.index + 1},"${r.top1?.name || '-'}",${r.top1?.confidence || '-'},"${r.error || '成功'}"\n`
  })
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `批量鉴定结果_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
  showToast('导出成功', 'success')
}

// ========== 历史行情 ==========
const priceHistory = ref([])
const newRecord = ref({ coinName: '', grade: '', price: null, note: '' })

const loadPriceHistory = async () => {
  try {
    const resp = await http.get('/api/price-history')
    priceHistory.value = resp.data || []
  } catch (err) {
    console.error('加载价格历史失败:', err)
  }
}

const addPriceRecord = async () => {
  if (!newRecord.value.coinName) return
  try {
    await http.post('/api/price-history', newRecord.value)
    newRecord.value = { coinName: '', grade: '', price: null, note: '' }
    await loadPriceHistory()
    showToast('记录成功', 'success')
  } catch (err) {
    showToast('记录失败: ' + (err.response?.data?.error || err.message), 'error')
  }
}

const deletePriceRecord = async (id) => {
  if (!confirm('确定要删除这条记录吗？')) return
  try {
    await http.delete(`/api/price-history/${id}`)
    await loadPriceHistory()
  } catch (err) {
    showToast('删除失败', 'error')
  }
}

const formatDate = (ts) => {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

onMounted(() => {
  loadPriceHistory()
})
</script>

<style scoped>
.tools-page {
  max-width: 900px;
  margin: 20px auto;
  padding: 0 16px;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tabs button {
  padding: 10px 20px;
  border: 1px solid var(--border-color);
  background: white;
  border-radius: 999px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.tabs button.active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.tab-content {
  padding: 24px;
}

.tab-content h2 {
  color: var(--primary-color);
  margin: 0 0 8px;
}

.desc {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 20px;
}

.batch-upload {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}

.batch-group {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: #f9f5f0;
  border-radius: 8px;
}

.group-label {
  font-weight: bold;
  min-width: 50px;
}

.file-label {
  padding: 6px 12px;
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.file-label:hover {
  border-color: var(--primary-color);
  background: #fdf5f5;
}

.file-label input {
  display: none;
}

.remove-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: #e74c3c;
  color: white;
  cursor: pointer;
  font-size: 16px;
}

.add-btn {
  padding: 8px;
  border: 2px dashed var(--border-color);
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.add-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.submit-btn, .export-btn {
  padding: 12px 24px;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  font-size: 15px;
  transition: all 0.2s;
}

.submit-btn:hover, .export-btn:hover {
  background: var(--primary-hover);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.batch-results {
  margin-top: 20px;
}

.batch-results table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 12px;
}

.batch-results th, .batch-results td {
  padding: 10px;
  border: 1px solid #eee;
  text-align: left;
  font-size: 14px;
}

.batch-results th {
  background: #f5f0e8;
  font-weight: bold;
}

.batch-results .error {
  color: #e74c3c;
}

/* 历史行情 */
.add-record {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.add-record input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 14px;
  flex: 1;
  min-width: 120px;
}

.add-record button {
  padding: 8px 20px;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.history-list table {
  width: 100%;
  border-collapse: collapse;
}

.history-list th, .history-list td {
  padding: 10px;
  border: 1px solid #eee;
  text-align: left;
  font-size: 14px;
}

.history-list th {
  background: #f5f0e8;
  font-weight: bold;
}

.del-btn {
  padding: 4px 10px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.empty {
  color: var(--text-secondary);
  text-align: center;
  padding: 40px;
}

/* Toast 通知 */
.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 12px 20px;
  border-radius: 8px;
  z-index: 9999;
  animation: fadeIn 0.3s;
}
.toast.success { background: #27ae60; color: white; }
.toast.error { background: #e74c3c; color: white; }
.toast.info { background: #3498db; color: white; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 响应式 */
@media (max-width: 600px) {
  .batch-group { flex-wrap: wrap; }
}
</style>
