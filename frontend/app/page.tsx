'use client' // ① 必须有:启用 useState 的组件必须是"客户端组件"

import { useState } from "react" // ② useState = 状态钩子

// ③ 定义一条消息的形状(类型)
interface ChatMessage {
  role: "user" | "ai"
  content: string
}

export default function Home() {
  // ④ 三个状态:消息列表 / 输入框内容 / 是否正在流式
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  const [threadId, setThreadId] = useState(() => crypto.randomUUID()) // 会话号：换了号就是换了一个"抽屉"

  // ⑤ 发送处理函数:发请求 → 读流 → 逐字渲染
  async function handleSend() {
    if (!input.trim() || isStreaming) return // 空输入或正在流式时,直接返回

    const userMessage: ChatMessage = { role: "user", content: input }
    const aiMessage: ChatMessage = { role: "ai", content: "" } // AI 消息先空着
    setMessages([...messages, userMessage, aiMessage]) // 用户+AI 两条一起上屏
    setInput("")
    setIsStreaming(true)

    try {
      const resp = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage.content, thread_id: threadId, stream_tokens: true }),
      })
      const reader = resp.body?.getReader()
      const decoder = new TextDecoder() // ⑥ 流式解码器

      let buffer = ""                      // 积压货物：跨块残留的数据先存这里
      while (reader) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // 不断从 buffer 里切出"完整的一条事件"（空行分隔），切不走的部分留着下次拼
        let idx
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const rawEvent = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)   // 丢弃已取走的

          // 一条事件内部可能是多行（暂用不到 descriptions，防御性拆行）
          for (const line of rawEvent.split("\n")) {
            if (!line.startsWith("data:")) continue
            const payload = line.slice(5).trim()  // 5 不是 6：兼容 "data:" 和 "data: " 两种写法
            if (!payload) continue
            const data = JSON.parse(payload)
            if (data.type === "token") {
              setMessages(prev => {
                const newMsgs = [...prev]
                const last = newMsgs[newMsgs.length - 1]
                newMsgs[newMsgs.length - 1] = { ...last, content: last.content + data.content }
                return newMsgs
              })
            }
            if (data.type === "end") {
              setIsStreaming(false)
            }
          }
        }
      }

    } catch (err) {
      console.error(err)
      setIsStreaming(false)
    }
  }

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: 20 }}>
      <h1>AI Chat <button onClick={() => { setMessages([]); setThreadId(crypto.randomUUID()) }}>新对话</button></h1>
      <div style={{ minHeight: 300, border: "1px solid #ddd", padding: 10, marginBottom: 10 }}>
        {messages.map((m, i) => (
          <div key={i}>
            <b>{m.role === "user" ? "我" : "AI"}: </b>
            {m.content}
          </div>
        ))}
      </div>
      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        placeholder="输入消息,回车或点发送"
        style={{ width: "80%", padding: 8 }}
      />
      <button onClick={handleSend} disabled={isStreaming} style={{ padding: 8 }}>
        {isStreaming ? "生成中..." : "发送"}
      </button>
    </div>
  )
}
