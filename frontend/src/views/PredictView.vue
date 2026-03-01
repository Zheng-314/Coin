<template>
    <div id="app-container">
      <h1>钱币智能鉴定</h1>
      <p class="model-status" :class="{ ok: capability.ready, bad: !capability.ready }">
        {{ capability.ready ? '模型状态：可用' : '模型状态：未就绪' }}
      </p>
      <p v-if="!capability.ready && capability.message" class="status-tip">{{ capability.message }}</p>

      <div class="upload-area">
        <div class="upload-container">
          <h4>价值面 (一般显示为壹元或宝钱)<span class="example-label" @mouseenter="showValueExample = true" @mouseleave="showValueExample = false">示例</span>
            <div v-if="showValueExample && !previewUrl1" class="example-images">
              <img src="/value-face-sample.png" class="example-img" alt="价值面示例">
            </div>
          </h4>
          <div class="upload-box" @click="fileInput1?.click()">
            <input type="file" ref="fileInput1" @change="handleFileChange($event, 1)" accept="image/*">
            <img v-if="previewUrl1" :src="previewUrl1" class="preview-img" alt="预览图1">
            <div v-else class="upload-prompt">
              <svg width="50" height="50" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21.2 15c.7-1.2 1-2.5.7-3.9-.6-2.8-3.3-4.9-6.3-4.9h-1.3c-.3-1.3-.9-2.5-1.9-3.4C10.7 1.5 9 1 7.1 1.5c-2 .5-3.5 2.2-3.8 4.4-.3 1.3 0 2.6.7 3.8m0 0H3v5.6c0 1.5 1.2 2.7 2.7 2.7h12.6c1.5 0 2.7-1.2 2.7-2.7V15h-1.2Z" />
                <path d="m9 12 3-3 3 3M12 9v9" />
              </svg>
              <p>点击上传</p>
            </div>
          </div>
        </div>

        <div class="upload-container">
          <h4>图案面 (通常是人像或动植物)<span class="example-label" @mouseenter="showPortraitExample = true" @mouseleave="showPortraitExample = false">示例</span>
            <div v-if="showPortraitExample && !previewUrl2" class="example-images">
              <img src="/portrait-face-sample.png" class="example-img" alt="图案面示例">
            </div>
          </h4>
          <div class="upload-box" @click="fileInput2?.click()">
            <input type="file" ref="fileInput2" @change="handleFileChange($event, 2)" accept="image/*">
            <img v-if="previewUrl2" :src="previewUrl2" class="preview-img" alt="预览图2">
            <div v-else class="upload-prompt">
              <svg width="50" height="50" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21.2 15c.7-1.2 1-2.5.7-3.9-.6-2.8-3.3-4.9-6.3-4.9h-1.3c-.3-1.3-.9-2.5-1.9-3.4C10.7 1.5 9 1 7.1 1.5c-2 .5-3.5 2.2-3.8 4.4-.3 1.3 0 2.6.7 3.8m0 0H3v5.6c0 1.5 1.2 2.7 2.7 2.7h12.6c1.5 0 2.7-1.2 2.7-2.7V15h-1.2Z" />
                <path d="m9 12 3-3 3 3M12 9v9" />
              </svg>
              <p>点击上传</p>
            </div>
          </div>
        </div>
      </div>

      <button @click="uploadAndPredict" :disabled="!file1 || !file2 || isLoading" class="identify-btn">
        <span v-if="!isLoading">开始鉴定</span>
        <span v-else>鉴定中...</span>
      </button>

      <div id="result">
        <div v-if="isLoading" class="loader"></div>
        <div v-else-if="predictionResult && predictionResult.predictions">
          <ul class="prediction-list">
            <li v-for="(pred, index) in predictionResult.predictions" :key="index"
                :class="{'prediction-item': true, 'top-prediction': index === 0}">
              <span><strong>类别:</strong> {{ pred.name || `类别 #${pred.class}` }}</span>
              <span><strong>置信度:</strong> {{ (pred.confidence * 100).toFixed(2) }}%</span>
            </li>
          </ul>
          <div class="valuation-actions">
            <button class="valuation-btn" @click="goToValuation">基于本次识别去估值</button>
          </div>
        </div>
        <div v-else-if="error">
          <p style="color: red;"><strong>错误:</strong> {{ error }}</p>
        </div>
         <div v-else>
          <p>请上传两张图片后点击"开始鉴定"。</p>
        </div>
      </div>
    </div>
  </template>

  <script setup>
  import { ref, onMounted } from 'vue';
  import { useRouter } from 'vue-router';
  import axios from 'axios';
  import { apiUrl } from '@/config/api';

// --- 状态定义 ---
const file1 = ref(null);
const file2 = ref(null);
const previewUrl1 = ref(null);
const previewUrl2 = ref(null);
const predictionResult = ref(null);
const isLoading = ref(false);
const error = ref(null);
const capability = ref({ ready: true, message: '' });
const router = useRouter();
const showValueExample = ref(false);
const showPortraitExample = ref(false);

  // --- DOM 引用 ---
  // 用于在脚本中访问 <input type="file"> 元素
  const fileInput1 = ref(null);
  const fileInput2 = ref(null);

  // --- 后端配置 ---
  // 【重要】请确保这里的IP地址是您后端的正确地址
  const backendUrl = apiUrl('/predict');

  const loadCapability = async () => {
    try {
      const response = await axios.get(apiUrl('/api/predict/capabilities'));
      const data = response.data || {};
      capability.value.ready = !!data.ready;
      capability.value.message = Array.isArray(data.errors) ? data.errors.join('；') : '';
    } catch {
      capability.value.ready = false;
      capability.value.message = '无法读取模型状态，请确认后端服务已启动。';
    }
  };

  // --- 方法定义 ---
  const handleFileChange = (event, boxNumber) => {
  const file = event.target.files[0];
  if (!file) return;

  // 验证文件类型
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp'];
  if (!allowedTypes.includes(file.type)) {
    error.value = '不支持的文件格式,请上传 JPG、PNG、WebP 或 BMP 图片';
    return;
  }

  // 验证文件大小 (10MB)
  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    error.value = '图片文件过大,请上传 10MB 以内的图片';
    return;
  }

  // 清除之前的错误
  error.value = null;

  // 创建本地预览URL
  const previewUrl = URL.createObjectURL(file);
  if (boxNumber === 1) {
    file1.value = file;
    previewUrl1.value = previewUrl;
  } else {
    file2.value = file;
    previewUrl2.value = previewUrl;
  }
};

  const uploadAndPredict = async () => {
    if (!capability.value.ready) {
      error.value = capability.value.message || '模型未就绪，暂时无法推理。';
      return;
    }

    isLoading.value = true;
    predictionResult.value = null;
    error.value = null;

    const formData = new FormData();
    formData.append('image1', file1.value);
    formData.append('image2', file2.value);

    console.log("准备发送请求到:", backendUrl);

    try {
      const response = await axios.post(backendUrl, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      console.log("请求成功:", response.data);
      predictionResult.value = response.data;
    } catch (err) {
      console.error("推理请求失败!", err);
      console.error("错误详情:", {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status
      });
      if (err.response) {
        error.value = err.response.data.error || '服务器返回了一个错误。';
      } else if (err.request) {
        error.value = '无法连接到后端服务器，请检查IP地址和后端服务状态。';
      } else {
        error.value = `请求设置时出错: ${err.message}`;
      }
    } finally {
      isLoading.value = false;
    }
  };

  const goToValuation = () => {
    const topPred = predictionResult.value?.predictions?.[0];
    const classValue = topPred?.class;
    const confidence = topPred?.confidence;

    const guessedName =
      classValue === undefined || classValue === null
        ? ''
        : `模型识别类别 #${classValue}`;

    const gradeHint =
      typeof confidence === 'number'
        ? `待确认（识别置信度 ${(confidence * 100).toFixed(1)}%）`
        : '';

    router.push({
      path: '/valuation',
      query: {
        coinName: guessedName,
        coinGrade: gradeHint
      }
    });
  };

  onMounted(() => {
    loadCapability();
  });
  </script>

  <style scoped>
  /* 您的所有CSS样式都复制到这里，并添加了scoped属性 */
  /* 这可以确保这些样式只作用于当前组件，不会污染其他页面 */
  #app-container {
    background: white;
    padding: 40px;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    text-align: center;
    width: 90%;
    max-width: 800px;
    margin: 20px auto;
    position: relative;
  }

  .example-label {
    background: var(--primary-color);
    color: white;
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 10px;
    margin-left: 8px;
    vertical-align: middle;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .example-label:hover {
    background: var(--primary-hover);
    transform: scale(1.05);
  }

  .example-images {
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    margin-bottom: 8px;
    z-index: 10;
  }

  .example-img {
    width: 200px;
    height: 200px;
    object-fit: contain;
    border-radius: 12px;
    border: 3px solid white;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    cursor: pointer;
    background: white;
  }

  .identify-btn {
    background-color: var(--primary-color);
  }

  .identify-btn:hover {
    background-color: var(--primary-hover);
  }

  h1 {
    color: #333;
    margin-bottom: 10px;
  }

  .model-status {
    margin: 0;
    font-size: 14px;
  }

  .model-status.ok {
    color: #1f7a49;
  }

  .model-status.bad {
    color: #c0392b;
  }

  .status-tip {
    margin-top: 6px;
    color: #666;
    font-size: 13px;
  }

  .upload-area {
    display: flex;
    justify-content: space-around;
    margin-bottom: 30px;
    gap: 30px;
  }

  .upload-container {
    flex: 1;
    text-align: center;
  }

  .upload-container h4 {
    color: #555;
    font-weight: 600;
    margin-bottom: 15px;
    height: 40px;
    position: relative;
    z-index: 5;
  }

  .upload-box {
    border: 2px dashed #ccc;
    border-radius: 8px;
    width: 100%;
    min-height: 250px;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    transition: border-color 0.3s, background-color 0.3s;
    position: relative;
    background-color: #fafafa;
    overflow: hidden; /* 防止图片溢出圆角 */
  }

  .upload-box:hover {
    border-color: #007bff;
    background-color: #f0f8ff;
  }

  .upload-box input[type="file"] {
    display: none;
  }

  .upload-prompt {
    color: #888;
  }

  .preview-img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    padding: 5px;
    box-sizing: border-box;
  }

  button {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 12px 25px;
    border-radius: 6px;
    font-size: 16px;
    cursor: pointer;
    transition: background-color 0.3s;
    margin-top: 10px;
  }

  button:hover {
    background-color: #0056b3;
  }

  button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }

  #result {
    margin-top: 30px;
    font-size: 18px;
    color: #333;
    min-height: 50px;
    padding: 15px;
    background: #e9f5ff;
    border-radius: 8px;
    border: 1px solid #b3d7ff;
    text-align: left;
  }

  .prediction-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .prediction-item {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #ddd;
  }

  .prediction-item:last-child {
    border-bottom: none;
  }

  .prediction-item.top-prediction {
    font-weight: bold;
    color: #0056b3;
    font-size: 20px;
  }

  .valuation-actions {
    margin-top: 14px;
    display: flex;
    justify-content: flex-end;
  }

  .valuation-btn {
    background-color: #8b3a3a;
  }

  .valuation-btn:hover {
    background-color: #7a2f2f;
  }

  .loader {
    border: 4px solid #f3f3f3;
    border-radius: 50%;
    border-top: 4px solid #3498db;
    width: 30px;
    height: 30px;
    animation: spin 1s linear infinite; /* 动画加速 */
    margin: auto;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  </style>
