# 鉴泉识珍 — 0 元公网访问指南（Cloudflare Quick Tunnel）

> 当前可用的完全免费方案：**电脑作为 AI 推理服务器 + Cloudflare 官方免费隧道提供公网 HTTPS 地址**。
> 无需腾讯云、无需信用卡、无需 Hugging Face / Vercel 付费账号。

---

## 你现在就能分享的公网地址

当前隧道地址：

```
https://discharge-finger-incidents-descriptions.trycloudflare.com
```

已实际验证：
- 网页首页：HTTP 200
- 健康检查：HTTP 200
- 知识图谱：HTTP 200
- 图片双面鉴定：HTTP 200
- 问答能力接口：HTTP 200

把上面地址发给任何人，对方在浏览器打开就能进入鉴泉识珍。

---

## 重要限制（必须知道）

这是 **Quick Tunnel 演示方案**，适合大创答辩、内测和小规模试用：

1. 你的电脑必须开机、联网，后端服务与隧道进程必须持续运行。
2. 电脑重启或隧道停止后，当前随机网址失效；重新开隧道会得到一个新网址。
3. 官方 Quick Tunnel 无 SLA、最多约 200 并发请求；不适合正式商业生产。
4. 图片鉴定约需 1–2 分钟（本地 YOLO + ONNX 推理与公网传输）。
5. 流式问答可能因 Quick Tunnel 对 SSE 的限制而出现延迟；普通鉴定、知识图谱、数据库功能不受影响。

---

## 以后如何一键重新开启

双击项目根目录：

```
D:/my_project/code/start_public.bat
```

它会自动：
1. 启动 `backend/server.py`（API + Web 前端同源伺服）
2. 等待 AI 模型加载
3. 启动 Cloudflare 隧道
4. 把新公网地址写入 `cloudflared.err.log`

打开 `D:/my_project/code/cloudflared.err.log`，找这一行：

```
Visit it at: https://xxxxx.trycloudflare.com
```

将新地址分享给其他人即可。

---

## App 如何连接公网后端

移动版 App 不需要重新打包：

1. 打开 App → 底部 **我的**
2. 点 **服务器地址**
3. 输入当前 `https://xxxxx.trycloudflare.com`
4. 点 **保存并刷新**

App 随即连接到你的公网后端；其他人安装 APK 后也按这一方式填地址。

---

## 为什么不走 Hugging Face / Vercel

- **Hugging Face**：2026 年已将 Docker、Gradio SDK 等可运行完整 Python 服务的 Space 类型锁到付费计划；你在页面看到付费要求是正常现象。
- **Vercel**：Web 静态页面有免费档，但它不能运行本项目 175MB ONNX + YOLO + GraphRAG 后端；单独上 Vercel 不能解决“所有人能鉴定”的关键问题。
- 当前方案将 Web 构建产物放到 `D:/my_project/code/web/`，由 Flask 同时提供网页与 API，因此不需要 Vercel，也没有跨域问题。

---

## 未来要长期稳定上线怎么办

需要一个持续运行的计算节点；这类 AI 后端（模型 186MB、运行内存约 GB 级）没有可靠的永久免费托管。可选升级：

| 方案 | 适合情况 | 成本 |
|---|---|---|
| Cloudflare Named Tunnel + 自己电脑 | 继续用电脑，但要固定域名 | Cloudflare Tunnel 免费；域名通常需付费 |
| Oracle Cloud Always Free | 有国际信用卡、愿意维护 Linux 服务器 | 理论免费 |
| Render / Railway / Zeabur | 想少运维、项目正式对外 | 通常每月数美元起 |

在大创比赛阶段，Quick Tunnel 已足够做公开演示与真实用户试用。

---

## 安全说明

公开后端已对 `/api/ask` 加入限流：**每 IP 每分钟 3 次、每小时 30 次**，避免他人刷你的 DeepSeek/Qwen/Tavily API 额度。图片鉴定接口原本也有每分钟 20 次限流。
