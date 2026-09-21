<script setup>
import { ref } from 'vue'
import http from '@/config/http'
import { Capacitor } from '@capacitor/core'

const photos = ref([null, null])       // 两个 dataUrl
const files = ref([null, null])        // 两个 File
const labels = ['价值面（壹元/宝钱）', '图案面（人像/龙纹）']
const loading = ref(false)
const result = ref(null)
const error = ref('')

async function takePhoto(slot) {
  error.value = ''
  try {
    if (Capacitor.isNativePlatform()) {
      const { Camera, CameraResultType, CameraSource } = await import('@capacitor/camera')
      const photo = await Camera.getPhoto({
        quality: 82,
        resultType: CameraResultType.DataUrl,
        source: CameraSource.Prompt,      // 弹窗让用户选 拍照 / 相册
        width: 1280,
        correctOrientation: true,
      })
      setPhoto(slot, photo.dataUrl)
    } else {
      // 浏览器调试：走文件选择（移动端浏览器会弹出相机选项）
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = 'image/*'
      input.capture = 'environment'
      input.onchange = () => {
        const f = input.files?.[0]
        if (!f) return
        const reader = new FileReader()
        reader.onload = (e) => setPhoto(slot, e.target.result)
        reader.readAsDataURL(f)
      }
      input.click()
    }
  } catch (e) {
    if (e?.message !== 'User cancelled') error.value = '未能获取照片，请重试'
  }
}

function setPhoto(slot, dataUrl) {
  photos.value[slot] = dataUrl
  files.value[slot] = dataUrlToFile(dataUrl, `coin_${slot}.jpg`)
}

function dataUrlToFile(dataUrl, name) {
  const [head, b64] = dataUrl.split(',')
  const mime = head.match(/:(.*?);/)?.[1] || 'image/jpeg'
  const bin = atob(b64)
  const arr = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i)
  return new File([arr], name, { type: mime })
}

function removePhoto(slot) {
  photos.value[slot] = null
  files.value[slot] = null
}

async function identify() {
  if (!files.value[0] || !files.value[1]) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const fd = new FormData()
    fd.append('image1', files.value[0])
    fd.append('image2', files.value[1])
    const resp = await http.post('/predict', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      // 公网隧道 + 本地 YOLO/ONNX 首次推理可能超过两分钟
      timeout: 180000,
    })
    result.value = resp.data
  } catch (e) {
    const msg = e.response?.data?.message || e.response?.data?.error
    error.value = msg || '鉴定失败，请检查网络后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="topbar">
      <div><h1>拍照鉴定</h1><div class="sub">两面各一张，识别更精准</div></div>
    </div>

    <!-- 两个拍照位 -->
    <div class="slots">
      <div v-for="(label, i) in labels" :key="i" class="slot card">
        <div class="slot-label">{{ label }}</div>
        <div v-if="photos[i]" class="slot-preview" @click="takePhoto(i)">
          <img :src="photos[i]" />
          <button class="slot-x" @click.stop="removePhoto(i)">✕</button>
        </div>
        <button v-else class="slot-empty" @click="takePhoto(i)">
          <svg viewBox="0 0 24 24"><path d="M4 7h3l2-2.5h6L17 7h3a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z" /><circle cx="12" cy="13" r="4" /></svg>
          <span>拍照 / 相册</span>
        </button>
      </div>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>

    <button class="btn" :disabled="!files[0] || !files[1] || loading" @click="identify">
      <span v-if="loading">鉴定中…</span>
      <span v-else>开始鉴定</span>
    </button>

    <div v-if="loading" class="loading-dots"><span></span><span></span><span></span></div>

    <!-- 结果卡片 -->
    <div v-if="result?.predictions?.length" class="results">
      <div class="card result-top">
        <div class="result-tag">最可能</div>
        <div class="result-name">{{ result.predictions[0].name }}</div>
        <div class="result-conf">{{ (result.predictions[0].confidence * 100).toFixed(1) }}%</div>
        <div class="conf-bar"><div :style="{ width: Math.min(result.predictions[0].confidence * 100, 100) + '%' }" /></div>
      </div>

      <div v-if="result.predictions.length > 1" class="card result-more">
        <div class="more-title">其他候选</div>
        <div v-for="(p, i) in result.predictions.slice(1)" :key="i" class="more-row">
          <span class="more-name">{{ p.name }}</span>
          <span class="more-conf">{{ (p.confidence * 100).toFixed(1) }}%</span>
        </div>
      </div>

      <div class="card shots">
        <div class="more-title">入模图像</div>
        <div class="shots-imgs">
          <img v-if="result.processedImage1" :src="result.processedImage1" />
          <img v-if="result.processedImage2" :src="result.processedImage2" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.slots { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.slot-label { font-size: 12px; color: var(--text-2); margin-bottom: 8px; text-align: center; }
.slot-empty {
  width: 100%; aspect-ratio: 1; border: 2px dashed var(--line); border-radius: 12px;
  background: #FBFAF7; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  color: var(--text-2); font-size: 12px;
}
.slot-empty svg { width: 34px; height: 34px; fill: none; stroke: currentColor; stroke-width: 1.5; }
.slot-preview { position: relative; border-radius: 12px; overflow: hidden; aspect-ratio: 1; }
.slot-preview img { width: 100%; height: 100%; object-fit: cover; display: block; }
.slot-x {
  position: absolute; top: 6px; right: 6px; width: 26px; height: 26px; border-radius: 50%;
  background: rgba(0,0,0,0.55); color: #fff; border: none; font-size: 13px;
}
.error-box { background: #FDECEA; color: var(--danger); padding: 10px 14px; border-radius: 10px; font-size: 14px; margin-bottom: 12px; }

.results { margin-top: 18px; }
.result-top { text-align: center; padding: 20px 16px; background: linear-gradient(160deg, #FFF, #FDF6EC); }
.result-tag { font-size: 12px; color: var(--accent); font-weight: 700; letter-spacing: 3px; margin-bottom: 6px; }
.result-name { font-size: 17px; font-weight: 700; line-height: 1.5; }
.result-conf { font-size: 34px; font-weight: 800; color: var(--primary); margin: 8px 0 6px; }
.conf-bar { height: 8px; border-radius: 4px; background: var(--line); overflow: hidden; }
.conf-bar div { height: 100%; background: linear-gradient(90deg, var(--accent), var(--primary)); border-radius: 4px; }

.more-title { font-size: 13px; color: var(--text-2); margin-bottom: 10px; }
.more-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--line); font-size: 14px; }
.more-row:last-child { border-bottom: none; }
.more-name { color: var(--text); }
.more-conf { color: var(--primary); font-weight: 600; }

.shots-imgs { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.shots-imgs img { width: 100%; border-radius: 10px; display: block; }
</style>
