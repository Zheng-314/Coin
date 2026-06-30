<template>
  <div class="qa">
    <div class="chat-container coin-panel">
      <div class="chat-head">
        <h2>钱币知识问答</h2>
        <p>支持文字提问或上传图片鉴定，可切换本地/全局/联网搜索。</p>
        <div class="capability-row">
          <span class="capability-tag" :class="{ ok: capabilities.global.available }">
            全局: {{ capabilities.global.available ? '可用' : '降级' }}
          </span>
          <span class="capability-tag" :class="{ ok: capabilities.local.available }">
            本地: {{ capabilities.local.available ? '可用' : '降级' }}
          </span>
          <span class="capability-tag" :class="{ ok: capabilities.web.available }">
            联网: {{ capabilities.web.available ? '可用' : '不可用' }}
          </span>
          <span class="capability-tag ok" v-if="capabilities.multimodal?.available">
            📷 多模态
          </span>
        </div>
      </div>

      <div class="messages" ref="messagesContainer">
        <div v-for="message in messages" :key="message.id" :class="['message', message.type]">
          <img :src="message.type === 'user' ? userAvatar : botAvatar" class="avatar" />
          <div class="bubble">
            <!-- 用户消息：显示图片+文字 -->
            <div v-if="message.type === 'user'">
              <div v-if="message.images && message.images.length" class="user-images">
                <img v-for="(img, idx) in message.images" :key="idx" :src="img" class="user-thumb" />
              </div>
              <div>{{ message.text }}</div>
            </div>
            <!-- Bot消息：Markdown渲染 -->
            <div v-else v-html="md.render(message.text)" />
            <!-- 来源 -->
            <div v-if="message.type === 'bot' && message.sources && message.sources.length" class="source-box">
              <p>参考来源</p>
              <ul>
                <li v-for="(s, i) in message.sources" :key="`${i}-${s.pid || s.name || 'src'}`">
                  <span v-if="s.type === 'identification'" class="id-result">
                    🔍 {{ s.results?.map(r => `${r.name}(${r.confidence}%)`).join('、') }}
                  </span>
                  <a v-else-if="s.pid" :href="`/artifact/${s.pid}`" target="_blank" rel="noopener noreferrer">
                    {{ s.title || `文物 #${s.pid}` }}
                  </a>
                  <span v-else>{{ s.name || s.title || '系统来源' }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- 上传错误提示 -->
      <div v-if="uploadError" class="upload-error">{{ uploadError }} <button @click="uploadError = null" style="background:none;border:none;color:inherit;cursor:pointer;font-size:1rem;">✕</button></div>

      <!-- 图片预览区 -->
      <div v-if="imagePreviews.length" class="image-preview-bar">
        <div v-for="(img, idx) in imagePreviews" :key="idx" class="preview-item">
          <img :src="img" />
          <button class="remove-btn" @click="removeImage(idx)">×</button>
        </div>
        <span class="preview-hint">已选 {{ imagePreviews.length }} 张图片</span>
      </div>

      <div class="input-container">
        <button class="attach-btn" @click="triggerFileInput" title="上传图片">
          📷
        </button>
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          multiple
          style="display: none"
          @change="handleFileSelect"
        />
        <input
          v-model="question"
          placeholder="输入问题或上传图片鉴定，如：这个值多少钱？"
          @keyup.enter="askQuestion"
        />
        <el-select v-model="searchType" placeholder="搜索类型" class="type-select">
          <el-option
            v-for="item in searchOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
            :disabled="item.disabled"
          ></el-option>
        </el-select>
        <el-button class="send-btn" @click="askQuestion" :disabled="loading || (!question.trim() && !selectedImages.length)">
          {{ loading ? '回答中...' : '发送' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, computed } from 'vue';
import http from '@/config/http';
import MarkdownIt from 'markdown-it';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router'
import userAvatar from '@/assets/image/people.jpg';
import botAvatar from '@/assets/image/robot.png';
import { apiUrl } from '@/config/api';

const md = new MarkdownIt({ html: false });
const authStore = useAuthStore();
const router = useRouter();

const question = ref('');
const messages = ref([]);
const loading = ref(false);
const searchType = ref('global');
const messagesContainer = ref(null);
const fileInput = ref(null);
const selectedImages = ref([]);
const imagePreviews = ref([]);
const uploadError = ref(null);
const capabilities = ref({
  global: { available: true, reason: '' },
  local: { available: true, reason: '' },
  web: { available: false, reason: '' },
  multimodal: { available: true }
});

const searchOptions = computed(() => [
  {
    label: capabilities.value.global.available ? '全局搜索' : '全局搜索（降级）',
    value: 'global',
    disabled: false
  },
  {
    label: capabilities.value.local.available ? '本地搜索' : '本地搜索（降级）',
    value: 'local',
    disabled: false
  },
  {
    label: capabilities.value.web.available ? '联网搜索' : '联网搜索（不可用）',
    value: 'web',
    disabled: !capabilities.value.web.available
  }
]);

const loadCapabilities = async () => {
  try {
    const response = await http.get('/api/ask/capabilities');
    capabilities.value = response.data || capabilities.value;
    if (searchType.value === 'web' && !capabilities.value.web.available) {
      searchType.value = capabilities.value.global.available ? 'global' : 'local';
    }
  } catch (error) {
    console.error('加载问答能力状态失败:', error);
  }
};

onMounted(async () => {
  await loadCapabilities();

  if (authStore.isAuthenticated) {
    try {
      const response = await http.get('/api/chat/history');
      if (response.data && response.data.length > 0) {
        messages.value = response.data.map(msg => ({
          ...msg,
          id: generateId(),
          type: msg.type || 'bot'
        }));
      } else {
        messages.value.push({
          id: generateId(),
          type: 'bot',
          text: '你好！我是钱币知识问答助手，支持：\n\n- 💬 **文字提问**：输入钱币相关问题\n- 📷 **图片鉴定**：上传正反面照片识别钱币\n- 🔍 **智能搜索**：本地/全局/联网三种模式\n\n有什么可以帮您？'
        });
      }
    } catch (error) {
      console.error("加载聊天记录失败:", error);
      messages.value.push({
        id: generateId(),
        type: 'bot',
        text: '你好！我是钱币知识问答助手，有什么可以帮您？'
      });
    } finally {
      loading.value = false;
    }
  } else {
    messages.value.push({
      id: generateId(),
      type: 'bot',
      text: '你好！我是钱币知识问答助手，登录后可以保存聊天记录。'
    });
    loading.value = false;
  }
});

const generateId = () => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
};

const saveMessageToDb = async (message) => {
  if (!authStore.isAuthenticated) return;
  try {
    await http.post('/api/chat/history', {
      type: message.type,
      text: message.text,
      sources: message.sources
    });
  } catch (error) {
    console.error("保存消息到数据库失败:", error);
  }
};

// 图片处理
const triggerFileInput = () => {
  fileInput.value?.click();
};

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files);
  for (const file of files) {
    if (file.size > 10 * 1024 * 1024) {
      uploadError.value = `${file.name} 超过10MB限制`;
      continue;
    }
    if (!file.type.startsWith('image/')) continue;

    selectedImages.value.push(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      imagePreviews.value.push(e.target.result);
    };
    reader.readAsDataURL(file);
  }
  // 清空input
  if (fileInput.value) fileInput.value.value = '';
};

const removeImage = (idx) => {
  selectedImages.value.splice(idx, 1);
  imagePreviews.value.splice(idx, 1);
};

const askQuestion = async () => {
  if ((!question.value.trim() && !selectedImages.value.length) || loading.value) return;

  if (searchType.value === 'web' && !capabilities.value.web.available) {
    const availableType = capabilities.value.global.available ? 'global' : 'local';
    searchType.value = availableType;
    const errorMessage = {
      id: generateId(),
      type: 'bot',
      text: capabilities.value.web.reason || `联网搜索当前不可用，已自动切换为${availableType === 'global' ? '全局' : '本地'}搜索。`
    };
    messages.value.push(errorMessage);
    await saveMessageToDb(errorMessage);
    return;
  }

  const userQuestionText = question.value.trim() || '请帮我看看这是什么钱币。';
  const hasImages = selectedImages.value.length > 0;
  const historyForApi = JSON.parse(JSON.stringify(messages.value));

  // 添加用户消息（带图片预览）
  const userMessage = {
    id: generateId(),
    type: 'user',
    text: userQuestionText,
    images: hasImages ? [...imagePreviews.value] : []
  };
  messages.value.push(userMessage);
  await saveMessageToDb(userMessage);

  loading.value = true;
  question.value = '';
  const currentImages = [...selectedImages.value];
  imagePreviews.value = [];
  selectedImages.value = [];

  // 插入空bot消息
  const botMessage = { id: generateId(), type: 'bot', text: '', sources: [] };
  messages.value.push(botMessage);
  const botIndex = messages.value.length - 1;

  try {
    const formattedHistory = historyForApi.map(msg => msg.text);
    let response;

    if (hasImages) {
      // 多模态：multipart/form-data
      const formData = new FormData();
      formData.append('question', userQuestionText);
      formData.append('searchType', searchType.value);
      formData.append('history', JSON.stringify(formattedHistory));
      formData.append('stream', 'true');
      for (const img of currentImages) {
        formData.append('images', img);
      }

      const token = localStorage.getItem('token');
      const reqHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
      response = await fetch(apiUrl('/api/ask'), {
        method: 'POST',
        headers: reqHeaders,
        body: formData
      });
    } else {
      // 纯文字：JSON
      const token = localStorage.getItem('token');
      const reqHeaders = { 'Content-Type': 'application/json' };
      if (token) reqHeaders['Authorization'] = `Bearer ${token}`;
      response = await fetch(apiUrl('/api/ask'), {
        method: 'POST',
        headers: reqHeaders,
        body: JSON.stringify({
          question: userQuestionText,
          searchType: searchType.value,
          history: formattedHistory,
          stream: true
        })
      });
    }

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const payload = JSON.parse(line.slice(6));
          if (payload.delta !== undefined) {
            messages.value[botIndex].text += payload.delta;
          } else if (payload.done) {
            messages.value[botIndex].sources = payload.sources || [];
          } else if (payload.error) {
            messages.value[botIndex].text = payload.answer || '发生错误，请重试。';
          }
        } catch (_) { /* 忽略解析错误 */ }
      }
    }

    await saveMessageToDb(messages.value[botIndex]);
  } catch (error) {
    console.error('Error:', error);
    let errorText = '与服务器通信时出错，请稍后重试。';
    if (error.request) errorText = '服务器无响应，请检查网络连接。';
    messages.value[botIndex].text = errorText;
    await saveMessageToDb(messages.value[botIndex]);
  } finally {
    loading.value = false;
  }
};

// 自动滚动
watch(messages, async () => {
  await nextTick();
  const container = messagesContainer.value;
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}, { deep: true });

</script>

<style scoped>
.qa {
  padding: 0;
}

.chat-container {
  max-width: 980px;
  height: 720px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-head {
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(120deg, #fff 0%, #f8f1ea 70%, #f3e7d8 100%);
}

.chat-head h2 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.15rem;
}

.chat-head p {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: 0.88rem;
}

.capability-row {
  margin-top: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.capability-tag {
  display: inline-block;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 0.76rem;
  background: #f3e5e5;
  color: #9f5757;
}

.capability-tag.ok {
  background: #e8f4ec;
  color: #2f7a50;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  background: linear-gradient(180deg, #fbf8f3 0%, #f6efe5 100%);
}

.message {
  display: flex;
  align-items: flex-start;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.bot {
  align-self: flex-start;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  margin: 0 8px;
  flex-shrink: 0;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.bubble {
  padding: 10px 13px;
  border-radius: 12px;
  color: var(--text-main);
  font-size: 14px;
  text-align: left;
  line-height: 1.6;
  word-wrap: break-word;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.message.user .bubble {
  background-color: var(--primary-color);
  color: white;
  border-top-right-radius: 4px;
  border-color: rgba(0, 0, 0, 0.1);
}

.message.bot .bubble {
  background-color: #fff;
  border-top-left-radius: 4px;
}

.message.bot .bubble :deep(p) {
  margin: 0 0 8px 0;
}
.message.bot .bubble :deep(p):last-child {
  margin-bottom: 0;
}
.message.bot .bubble :deep(ul),
.message.bot .bubble :deep(ol) {
  padding-left: 20px;
}

/* 用户图片 */
.user-images {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.user-thumb {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 8px;
  border: 2px solid rgba(255, 255, 255, 0.3);
}

/* 图片预览栏 */
.image-preview-bar {
  display: flex;
  gap: 8px;
  padding: 8px 16px;
  background: #fff;
  border-top: 1px solid var(--border-color);
  align-items: center;
  overflow-x: auto;
}

.preview-item {
  position: relative;
  flex-shrink: 0;
}

.preview-item img {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.remove-btn {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #e74c3c;
  color: white;
  border: none;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.preview-hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.upload-error {
  background: #fdecea;
  color: #b33939;
  padding: 8px 16px;
  font-size: 0.85rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.source-box {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed rgba(0, 0, 0, 0.14);
}

.source-box p {
  margin: 0;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.source-box ul {
  margin: 4px 0 0;
  padding-left: 16px;
}

.source-box li {
  font-size: 0.8rem;
  line-height: 1.55;
}

.source-box a {
  color: var(--primary-color);
  text-decoration: none;
}

.source-box a:hover {
  text-decoration: underline;
}

.id-result {
  color: #2f7a50;
  font-weight: 500;
}

.input-container {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--border-color);
  background-color: #fff;
  align-items: center;
}

.attach-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--border-color);
  background: #fff;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.attach-btn:hover {
  border-color: var(--primary-color);
  background: #fdf5f5;
}

input {
  flex: 1;
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  outline: none;
  transition: border-color 0.3s;
}
input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(139, 58, 58, 0.12);
}

:deep(.type-select) {
  width: 132px;
}

:deep(.el-select .el-input__wrapper) {
  border-radius: 999px !important;
  box-shadow: 0 0 0 1px var(--border-color) inset !important;
  min-height: 40px;
}

:deep(.el-select .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--primary-color) inset !important;
}

:deep(.send-btn.el-button) {
  border-radius: 999px !important;
  background: var(--primary-color);
  border-color: var(--primary-color);
  min-height: 40px;
  padding: 0 16px;
}

:deep(.send-btn.el-button:hover) {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

@media (max-width: 840px) {
  .chat-container {
    height: 78vh;
  }
  .input-container {
    flex-wrap: wrap;
  }
  :deep(.type-select) {
    width: 100%;
  }
  :deep(.send-btn.el-button) {
    width: 100%;
  }
}
</style>
