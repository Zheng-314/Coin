<template>
  <div class="qa">
    <div class="chat-container coin-panel">
      <div class="chat-head">
        <h2>钱币知识问答</h2>
        <p>可切换本地/全局/联网搜索，回答将自动保存到个人历史。</p>
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
        </div>
      </div>

      <div class="messages" ref="messagesContainer">
        <div v-for="message in messages" :key="message.id" :class="['message', message.type]">
          <img :src="message.type === 'user' ? userAvatar : botAvatar" class="avatar" />
          <div class="bubble">
            <div v-if="message.type === 'bot'" v-html="md.render(message.text)" />
            <div v-else>{{ message.text }}</div>
            <div v-if="message.type === 'bot' && message.sources && message.sources.length" class="source-box">
              <p>参考来源</p>
              <ul>
                <li v-for="(s, i) in message.sources" :key="`${i}-${s.pid || s.name || 'src'}`">
                  <a v-if="s.pid" :href="`/artifact/${s.pid}`" target="_blank" rel="noopener noreferrer">
                    {{ s.title || `文物 #${s.pid}` }}
                  </a>
                  <span v-else>{{ s.name || s.title || '系统来源' }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      <div class="input-container">
        <input v-model="question" placeholder="请输入你的问题，如：袁大头九年精发有什么特征？" @keyup.enter="askQuestion" />
        <el-select v-model="searchType" placeholder="搜索类型" class="type-select">
          <el-option
            v-for="item in searchOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
            :disabled="item.disabled"
          ></el-option>
        </el-select>
        <el-button class="send-btn" @click="askQuestion" :disabled="loading || !question">
          {{ loading ? '发送中...' : '发送' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, computed } from 'vue';
import axios from 'axios';
import MarkdownIt from 'markdown-it';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router'
import userAvatar from '@/assets/image/people.jpg';
import botAvatar from '@/assets/image/robot.png';
import { apiUrl } from '@/config/api';

const md = new MarkdownIt();
const authStore = useAuthStore();
const router = useRouter();

const question = ref('');
const messages = ref([]);
const loading = ref(false);
const searchType = ref('global'); // 默认搜索类型
const messagesContainer = ref(null);
const capabilities = ref({
  global: { available: true, reason: '' },
  local: { available: true, reason: '' },
  web: { available: false, reason: '' }
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

const authHeaders = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: token } : {};
};

const loadCapabilities = async () => {
  try {
    const response = await axios.get(apiUrl('/api/ask/capabilities'));
    capabilities.value = response.data || capabilities.value;

    if (searchType.value === 'web' && !capabilities.value.web.available) {
      searchType.value = capabilities.value.global.available ? 'global' : 'local';
    }
  } catch (error) {
    console.error('加载问答能力状态失败:', error);
  }
};

onMounted(async () => {
  // 加载问答能力状态
  await loadCapabilities();

  // 加载历史聊天记录（仅当用户登录时）
  if (authStore.isAuthenticated) {
    try {
      const response = await axios.get(apiUrl('/api/chat/history'), { headers: authHeaders() });
      if (response.data && response.data.length > 0) {
        // 为从服务器加载的消息添加唯一ID
        messages.value = response.data.map(msg => ({
          ...msg,
          id: generateId(),
          // 确保消息类型正确
          type: msg.type || 'bot'
        }));
      } else {
        // 如果没有历史记录，显示欢迎语
        messages.value.push({
          id: generateId(),
          type: 'bot',
          text: '我是一个基于OPEN-AI并专注于中国近代银币的Agent，有有关中国近代银币的问题都可以问我~'
        });
      }
    } catch (error) {
      console.error("加载聊天记录失败:", error);
      // 即使加载失败，也显示欢迎语
      messages.value.push({
        id: generateId(),
        type: 'bot',
        text: '我是一个专注于中国近代银币的Agent，有什么可以帮您？'
      });
    } finally {
      loading.value = false;
    }
  } else {
    // 未登录时显示欢迎语
    messages.value.push({
      id: generateId(),
      type: 'bot',
      text: '我是一个专注于中国近代银币的Agent，登录后可以保存聊天记录。'
    });
    loading.value = false;
  }
});

// 生成唯一ID
const generateId = () => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
};

  // 保存单条消息到数据库
const saveMessageToDb = async (message) => {
  if (!authStore.isAuthenticated) return; // 未登录则不保存
  try {
    await axios.post(
      apiUrl('/api/chat/history'),
      { 
        type: message.type, 
        text: message.text,
        sources: message.sources // 保存sources字段
      },
      { headers: authHeaders() }
    );
  } catch (error) {
    console.error("保存消息到数据库失败:", error);
  }
};

const askQuestion = async () => {
  if (!question.value.trim() || loading.value) return;
  if (searchType.value === 'web' && !capabilities.value.web.available) {
    // 自动切换到可用的搜索类型
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

  const userQuestionText = question.value.trim();

  // [!code ++] 在发送请求前，准备好当前的历史记录
  // 这份历史记录不包含用户当前输入的问题
  const historyForApi = JSON.parse(JSON.stringify(messages.value));

  // 1. 将用户的问题添加到UI
  const userMessage = {
    id: generateId(),
    type: 'user',
    text: userQuestionText
  };
  messages.value.push(userMessage);

  // 2. 将用户的问题保存到数据库
  await saveMessageToDb(userMessage);

  loading.value = true;
  question.value = ''; // 清空输入框

  try {
    // 3. 发送请求到后端，包含问题、搜索类型和历史记录
    // 处理历史记录格式，只传递文本内容
    const formattedHistory = historyForApi.map(msg => msg.text);
    const response = await axios.post(apiUrl('/api/ask'), {
      question: userQuestionText,
      searchType: searchType.value,
      history: formattedHistory
    });

    const answer = response.data.answer || '服务器没有返回信息。';
    const sources = Array.isArray(response.data.sources) ? response.data.sources : [];

    // 4. 将机器人的回答添加到UI
    const botMessage = {
      id: generateId(),
      type: 'bot',
      text: answer,
      sources
    };
    messages.value.push(botMessage);

    // 5. 将机器人的回答保存到数据库
    await saveMessageToDb(botMessage);

  } catch (error) {
    console.error('Error:', error);
    let errorMessageText = '与服务器通信时出错，请稍后重试。';
    
    if (error.response) {
      // 服务器返回错误
      errorMessageText = error.response.data?.answer || errorMessageText;
    } else if (error.request) {
      // 请求已发送但没有收到响应
      errorMessageText = '服务器无响应，请检查网络连接。';
    }
    
    const errorMessage = {
      id: generateId(),
      type: 'bot',
      text: errorMessageText
    };
    messages.value.push(errorMessage);
    await saveMessageToDb(errorMessage); // 错误信息也保存
  } finally {
    loading.value = false;
  }
};

// 监听消息数组的变化，自动滚动到底部
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


.input-container {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--border-color);
  background-color: #fff;
  align-items: center;
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