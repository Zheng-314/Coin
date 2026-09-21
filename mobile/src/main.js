import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { Capacitor } from '@capacitor/core'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')

// Android 15+ 默认边到边显示会让页面盖住状态栏；原生层明确关闭覆盖。
if (Capacitor.isNativePlatform()) {
  import('@capacitor/status-bar').then(({ StatusBar, Style }) => {
    StatusBar.setOverlaysWebView({ overlay: false })
    StatusBar.setStyle({ style: Style.Light })
    StatusBar.setBackgroundColor({ color: '#F7F4EF' })
  }).catch(() => {})
}
