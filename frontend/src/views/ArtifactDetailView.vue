<template>
    <div class="detail-page">
        <!-- 顶部消息提示 -->
        <div v-if="message.text" class="message-toast" :class="message.type">
            {{ message.text }}
        </div>

        <!-- 加载中 -->
        <div v-if="loading" class="loading-prompt">
            <p>正在加载文物信息...</p>
        </div>

        <!-- 加载失败 -->
        <div v-else-if="error" class="error-state coin-panel">
            <p class="error-text">{{ error }}</p>
            <button @click="fetchDetail" class="retry-button">重试</button>
        </div>

        <!-- 加载成功 -->
        <div v-else-if="artifact" class="detail-content coin-panel">
            <h1>
                {{ artifact.title }}
                <button
                    @click="addToFavorites"
                    :disabled="isFavorited || favoriteLoading"
                    class="favorite-button"
                >
                    {{ buttonText }}
                </button>
            </h1>

            <img :src="artifact.url" :alt="artifact.title" class="detail-image"/>
            <h3>详细信息</h3>
            <pre class="description">{{ artifact.describe }}</pre>
            <h3>分类信息</h3>
            <ul>
                <li>种类 (c0): {{ artifact.c0 }}</li>
            </ul>
        </div>
    </div>
</template>


<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router';
import http from '@/config/http'

const route = useRoute();
const router = useRouter();
const artifact = ref(null);
const loading = ref(true);
const error = ref('');
const message = ref({ type: '', text: '' });

const isFavorited = ref(false);
const favoriteLoading = ref(false);

// 消息自动消失
let messageTimer = null;
function showMessage(type, text) {
    if (messageTimer) clearTimeout(messageTimer);
    message.value = { type, text };
    messageTimer = setTimeout(() => { message.value = { type: '', text: '' }; }, 3000);
}

const buttonText = computed(() => {
    if (isFavorited.value) return '已收藏';
    if (favoriteLoading.value) return '收藏中...';
    return '收藏';
});

// 获取文物详情
async function fetchDetail() {
    const artifactId = route.params.id;
    if (!artifactId) return;

    loading.value = true;
    error.value = '';
    artifact.value = null;

    // 1. 先获取文物本身的详细信息
    try {
        const response = await http.get(`/api/artifacts/search?id=${artifactId}`);
        artifact.value = response.data;
    } catch (err) {
        console.error("获取文物详情失败:", err);
        error.value = '获取文物详情失败，请稍后重试。';
        loading.value = false;
        return;
    }

    // 2. 查询此物品的收藏状态
    try {
        const statusResponse = await http.get(`/api/user-actions/favorite/status?pid=${artifactId}`);
        isFavorited.value = statusResponse.data.isFavorited;
    } catch (err) {
        console.error("获取收藏状态失败:", err);
    }

    loading.value = false;
}

onMounted(fetchDetail);

const addToFavorites = async () => {
    if (!artifact.value || favoriteLoading.value) {
        showMessage('error', '文物信息尚未加载完成，无法收藏。');
        return;
    }
    favoriteLoading.value = true;
    try {
        await http.post('/api/user-actions/favorite', { pid: artifact.value.pid });
        isFavorited.value = true;
        showMessage('success', '收藏成功');
    } catch (err) {
        if (err.response && (err.response.status === 401 || err.response.status === 403)) {
            showMessage('error', '登录状态已过期，请重新登录后再收藏。');
            router.push('/login');
        } else {
            showMessage('error', '收藏过程中发生错误，请稍后再试。');
        }
        console.error("收藏请求错误:", err);
    } finally {
        favoriteLoading.value = false;
    }
};
</script>

<style scoped>
.detail-page {
  position: relative;
}

/* 消息提示 */
.message-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  z-index: 1000;
  animation: fadeInDown 0.3s ease;
}
.message-toast.success {
  background: #e6f9ed;
  color: #1a7f37;
  border: 1px solid #a3d9b1;
}
.message-toast.error {
  background: #fde8e8;
  color: #c53030;
  border: 1px solid #f5a3a3;
}

@keyframes fadeInDown {
  from { opacity: 0; transform: translateX(-50%) translateY(-10px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* 加载中 */
.loading-prompt {
  text-align: center;
  margin-top: 50px;
  font-size: 1.2rem;
  color: var(--text-secondary);
}

/* 错误状态 */
.error-state {
  text-align: center;
  margin-top: 50px;
  padding: 40px;
}
.error-text {
  color: #c53030;
  font-size: 1.1rem;
  margin-bottom: 16px;
}
.retry-button {
  padding: 10px 28px;
  background: var(--primary-color);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 1rem;
  transition: opacity 0.2s;
}
.retry-button:hover {
  opacity: 0.85;
}

/* 详情内容 */
.detail-content {
  padding: 24px;
}
.detail-image {
  max-width: 100%;
  width: 500px;
  height: auto;
  display: block;
  margin: 20px auto;
  border-radius: var(--radius-md);
}
.description {
  background-color: var(--bg-color);
  padding: 15px;
  border-radius: var(--radius-md);
  white-space: pre-wrap;
  line-height: 1.6;
  font-family: 'Noto Serif SC', 'PingFang SC', 'Microsoft YaHei', serif;
  color: var(--text-main);
}

h1, h3 {
  color: var(--text-main);
  border-bottom: 2px solid var(--border-color);
  padding-bottom: 10px;
  margin-top: 20px;
  margin-bottom: 15px;
}
.favorite-button {
  margin-left: 15px;
  padding: 8px 15px;
  font-size: 0.9rem;
  border: 1px solid var(--primary-color);
  color: var(--primary-color);
  background-color: white;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 90px;
  text-align: center;
}
.favorite-button:hover:not(:disabled) {
  background-color: var(--primary-color);
  color: white;
}
.favorite-button:disabled {
  border-color: #ccc;
  color: #ccc;
  background-color: #eee;
  cursor: not-allowed;
}
</style>
