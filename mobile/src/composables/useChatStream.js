import { ref } from "vue";
import { apiUrl } from "@/config/http";

/** SSE 流式问答 composable */
export function useChatStream() {
  const streaming = ref(false);
  const error = ref(null);

  /**
   * 发送流式问答请求
   * @param {{question, searchType, history, images}} params
   * @param {(delta: string) => void} onDelta - 每个增量文本回调
   * @param {(sources: array) => void} onDone - 完成回调
   */
  async function streamAsk(params, onDelta, onDone) {
    streaming.value = true;
    error.value = null;

    try {
      const { question, searchType, history, images = [] } = params;
      const hasImages = images.length > 0;
      const token = localStorage.getItem("token");

      let response;
      if (hasImages) {
        const formData = new FormData();
        formData.append("question", question);
        formData.append("searchType", searchType);
        formData.append("history", JSON.stringify(history));
        formData.append("stream", "true");
        for (const img of images) formData.append("images", img);
        response = await fetch(apiUrl("/api/ask"), {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });
      } else {
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;
        response = await fetch(apiUrl("/api/ask"), {
          method: "POST",
          headers,
          body: JSON.stringify({ question, searchType, history, stream: true }),
        });
      }

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const payload = JSON.parse(line.slice(6));
            if (payload.delta !== undefined) {
              onDelta(payload.delta);
            } else if (payload.done) {
              onDone(payload.sources || []);
            } else if (payload.error) {
              onDelta(payload.answer || "发生错误，请重试。");
            }
          } catch {
            /* ignore parse errors */
          }
        }
      }
    } catch (e) {
      error.value = e.message;
      onDelta("网络请求失败，请重试。");
    } finally {
      streaming.value = false;
    }
  }

  return { streaming, error, streamAsk };
}
