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

  // ⑤ 发送处理函数:发请求 → 读流 → 逐字渲染
  async function handleSend() {
    if (!input.trim() || isStreaming) return // 空输入或正在流式时,直接返回

    const userMessage: ChatMessage = { role: "user", content: input }
    const aiMessage: ChatMessage = { role: "ai", content: "" } // AI 消息先空着
    setMessages([...messages, userMessage, aiMessage]) // 用户+AI 两条一起上屏
    setInput("")
    setIsStreaming(true)

    try {
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage.content, thread_id: null, stream_tokens: true }),
      })
      const reader = resp.body?.getReader()
      const decoder = new TextDecoder() // ⑥ 流式解码器

      while (reader) { // ⑦ 循环读取流
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value, { stream: true }) // ⑥ 流式解码
        for (const part of text.split("\n\n")) {
          if (!part.startsWith("data:")) continue
          const data = JSON.parse(part.slice(6))
          if (data.type === "token") {
            setMessages(prev => {
              // 函数式更新:追加到 AI 消息
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
    } catch (err) {
      console.error(err)
      setIsStreaming(false)
    }
  }

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: 20 }}>
      <h1>AI Chat</h1>
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
