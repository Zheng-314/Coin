<script setup>
import { ref, nextTick, onMounted } from 'vue'
import MarkdownIt from 'markdown-it'
import { useChatStream } from '@/composables/useChatStream'
import { useImageUpload } from '@/composables/useImageUpload'

const props = defineProps({ embedded: { type: Boolean, default: false } })
const md = new MarkdownIt({ breaks: true, linkify: true })
const { streaming, streamAsk } = useChatStream()
const { selectedImages, imagePreviews, handleFiles, clearImages } = useImageUpload(3, 10)

const messages = ref([])
const question = ref('')
const searchType = ref('local')
const listEl = ref(null)
const inputEl = ref(null)

onMounted(() => {
  messages.value.push({ type: 'bot', text: '你好，我是鉴泉识珍问答助手 🪙\n可以问我任何钱币知识，也可以上传钱币照片让我识别。' })
})

function scrollBottom() {
  nextTick(() => { listEl.value?.scrollTo({ top: listEl.value.scrollHeight, behavior: 'smooth' }) })
}

async function send() {
  const q = question.value.trim()
  const imgs = [...selectedImages.value]
  if ((!q && !imgs.length) || streaming.value) return

  messages.value.push({ type: 'user', text: q || '（图片）', images: imgs.length ? [...imagePreviews.value] : [] })
  question.value = ''
  const history = messages.value.slice(-8).map(m => m.text)
  clearImages()
  scrollBottom()

  const bot = { type: 'bot', text: '' }
  messages.value.push(bot)
  scrollBottom()

  await streamAsk(
    { question: q, searchType: searchType.value, history, images: imgs },
    (delta) => { bot.text += delta; scrollBottom() },
    () => {}
  )
  if (!bot.text) bot.text = '（回答生成失败，请重试）'
  scrollBottom()
}

function pickImages() { inputEl.value?.click() }
function onFiles(e) { handleFiles(e.target.files); e.target.value = '' }
</script>

<template>
  <div class="page chat-page">
    <div v-if="!props.embedded" class="topbar">
      <div><h1>智能问答</h1><div class="sub">本地知识库 · 全局图谱 · 联网搜索</div></div>
    </div>

    <!-- 模式切换 -->
    <div class="modes">
      <button v-for="m in [{k:'local',t:'本地'},{k:'global',t:'全局'},{k:'web',t:'联网'}]" :key="m.k"
        class="mode" :class="{ on: searchType === m.k }" @click="searchType = m.k">{{ m.t }}</button>
    </div>

    <!-- 消息列表 -->
    <div class="chat-list" ref="listEl">
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.type">
        <div v-if="m.images?.length" class="msg-imgs">
          <img v-for="(img, j) in m.images" :key="j" :src="img" />
        </div>
        <div v-if="m.type === 'user'" class="bubble user-bubble">{{ m.text }}</div>
        <div v-else class="bubble bot-bubble md" v-html="md.render(m.text || '…')"></div>
      </div>
      <div v-if="streaming" class="typing">思考中<span>.</span><span>.</span><span>.</span></div>
    </div>

    <!-- 图片预览 -->
    <div v-if="imagePreviews.length" class="preview-bar">
      <img v-for="(p, i) in imagePreviews" :key="i" :src="p" />
    </div>

    <!-- 输入区 -->
    <div class="input-bar">
      <button class="icon-btn" @click="pickImages">
        <svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="12" cy="12" r="4"/><path d="M17 2l4 4"/></svg>
      </button>
      <input v-model="question" class="input" placeholder="问点什么，如：光绪元宝有哪些版别？" @keyup.enter="send" />
      <button class="send-btn" :disabled="streaming || (!question.trim() && !selectedImages.length)" @click="send">↑</button>
      <input ref="inputEl" type="file" accept="image/*" multiple hidden @change="onFiles" />
    </div>
  </div>
</template>

<style scoped>
.chat-page { display: flex; flex-direction: column; min-height: calc(100vh - var(--nav-h)); padding-bottom: 8px; }
.modes { display: flex; gap: 8px; margin-bottom: 10px; }
.mode { flex: 1; min-height: 36px; border: 1.5px solid var(--line); border-radius: 10px; background: #fff; color: var(--text-2); font-size: 14px; }
.mode.on { border-color: var(--primary); color: var(--primary); background: rgba(140,74,47,0.06); font-weight: 700; }

.chat-list { flex: 1; overflow-y: auto; padding: 6px 0 12px; }
.msg { display: flex; margin-bottom: 12px; }
.msg.user { justify-content: flex-end; }
.msg-imgs { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px; justify-content: flex-end; }
.msg-imgs img { width: 72px; height: 72px; object-fit: cover; border-radius: 10px; }
.bubble { max-width: 82%; padding: 10px 14px; border-radius: 16px; font-size: 15px; line-height: 1.6; }
.user-bubble { background: var(--primary); color: #fff; border-bottom-right-radius: 4px; white-space: pre-wrap; }
.bot-bubble { background: #fff; box-shadow: var(--shadow); border-bottom-left-radius: 4px; }
.typing { color: var(--text-2); font-size: 13px; padding: 4px 10px; }
.typing span { animation: blink 1.2s infinite; }
.typing span:nth-child(2) { animation-delay: .2s } .typing span:nth-child(3) { animation-delay: .4s }
@keyframes blink { 0%,100%{opacity:.2} 50%{opacity:1} }

.preview-bar { display: flex; gap: 8px; padding: 8px 0; }
.preview-bar img { width: 56px; height: 56px; object-fit: cover; border-radius: 8px; }

.input-bar { display: flex; gap: 8px; align-items: center; padding: 8px 0 12px; }
.icon-btn { width: 44px; height: 44px; border-radius: 12px; border: 1.5px solid var(--line); background: #fff; flex-shrink: 0; }
.icon-btn svg { width: 22px; height: 22px; fill: none; stroke: var(--text-2); stroke-width: 1.6; margin-top: 1px; }
.send-btn {
  width: 44px; height: 44px; border-radius: 50%; border: none; flex-shrink: 0;
  background: linear-gradient(135deg, var(--primary), var(--primary-light)); color: #fff; font-size: 20px; font-weight: 700;
}
.send-btn:disabled { opacity: 0.4; }
</style>
