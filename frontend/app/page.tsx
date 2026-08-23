'use client' // ① 必须有:启用 useState 的组件必须是"客户端组件"

import { useEffect, useRef, useState } from "react" // ② useState/useEffect/useRef = 状态/副作用/盒子引用钩子
import styles from "./page.module.css" // ③ 排版样式(CSS Module, 类名自动局部化)

// ④ 定义一条消息的形状(类型)
interface ChatMessage {
  role: "user" | "ai"
  content: string
}

export default function Home() {
  // ⑤ 状态区: 消息列表 / 输入框内容 / 是否流式中 / 会话号 / 智能体名录与当前选择
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  const [threadId, setThreadId] = useState(() => crypto.randomUUID()) // 会话号：换了号就是换了一个"抽屉"
  const [agents, setAgents] = useState<{ key: string; description: string }[]>([]) // 智能体名录
  const [agentId, setAgentId] = useState("oa-assistant") // 当前选择的智能体

  // ⑤ 页面加载时去前台(后端)拿"名片"列表
  useEffect(() => {
    fetch("/api/agents")
      .then(r => r.json())
      .then(data => setAgents(data))
      .catch(() => {}) // 名录拿不到不阻塞聊天, 默认用 oa-assistant
  }, [])

  // ⑤' 页面加载: 把上次会话从 localStorage 恢复(刷新不丢档)
  //    注意: 只能写在 useEffect 里(客户端才执行), 不能写在 useState 初值里 ——
  //    首屏渲染时服务器也会跑一次, 服务器上没有 localStorage, 会直接崩
  const [loaded, setLoaded] = useState(false)   // 标记"恢复完成", 防止空档期用空数据覆盖存档
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("chat-hub-session") || "{}")
      if (saved?.threadId && Array.isArray(saved.messages)) {
        setThreadId(saved.threadId)          // 会话号也恢复: 服务器记忆抽屉还是同一个!
        setAgentId(saved.agentId || "oa-assistant")
        setMessages(saved.messages)
      }
    } catch {} // 存档损坏就按新会话处理
    setLoaded(true)
  }, [])

  // ⑤'' 状态一变就存盘: 刷新/关页都不丢
  useEffect(() => {
    if (!loaded) return
    localStorage.setItem("chat-hub-session", JSON.stringify({ threadId, agentId, messages }))
  }, [messages, threadId, agentId, loaded])

  // ⑤''' 滚动跟随: 有新消息就滚到底(消息区内部滚动)
  const msgBoxRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    msgBoxRef.current?.scrollTo({ top: msgBoxRef.current.scrollHeight, behavior: "smooth" })
  }, [messages])

  // ⑥ 发送处理函数:发请求 → 读流 → 逐字渲染
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
        body: JSON.stringify({ message: userMessage.content, thread_id: threadId, stream_tokens: true, agent_id: agentId }),
      })
      const reader = resp.body?.getReader()
      const decoder = new TextDecoder() // ⑦ 流式解码器

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
    <div className={styles.page}>
      <div className={styles.card}>
        {/* 顶栏: 品牌 + 智能体切换 + 新对话 */}
        <header className={styles.header}>
          <div className={styles.brand}>
            <span className={styles.logo}>🤖</span>
            <div>
              <h1 className={styles.title}>AI Chat Hub</h1>
              <p className={styles.subtitle}>多智能体对话平台</p>
            </div>
          </div>
          <div className={styles.controls}>
            <select
              className={styles.select}
              value={agentId}
              onChange={e => {
                setAgentId(e.target.value)
                setMessages([])                 // 换医生=重挂新号: 清空对话 + 换新会话号
                setThreadId(crypto.randomUUID())
              }}
            >
              {agents.map(a => (
                <option key={a.key} value={a.key}>{a.description}</option>
              ))}
            </select>
            <button
              className={styles.newChatBtn}
              onClick={() => { setMessages([]); setThreadId(crypto.randomUUID()) }}
            >
              + 新对话
            </button>
          </div>
        </header>

        {/* 消息区 */}
        <main ref={msgBoxRef} className={styles.chatBox}>
          {messages.length === 0 ? (
            <div className={styles.empty}>
              <span className={styles.emptyIcon}>💬</span>
              <span>你好！我是 AI Chat Hub，选择上方智能体开始对话吧</span>
            </div>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`${styles.row} ${m.role === "user" ? styles.rowUser : styles.rowAi}`}>
                <span className={`${styles.avatar} ${m.role === "user" ? styles.avatarUser : styles.avatarAi}`}>
                  {m.role === "user" ? "我" : "AI"}
                </span>
                <div className={`${styles.bubble} ${m.role === "user" ? styles.bubbleUser : styles.bubbleAi}`}>
                  {m.role === "ai" && m.content === "" && i === messages.length - 1 && isStreaming ? (
                    <span className={styles.typing}><i /><i /><i /></span>
                  ) : (
                    m.content
                  )}
                </div>
              </div>
            ))
          )}
        </main>

        {/* 输入区 */}
        <footer className={styles.inputRow}>
          <input
            className={styles.input}
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="输入消息,回车或点发送"
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault() // 防止回车触发表单提交
                handleSend()
              }
            }}
          />
          <button className={styles.sendBtn} onClick={handleSend} disabled={isStreaming}>
            {isStreaming ? "生成中..." : "发送"}
          </button>
        </footer>
      </div>
    </div>
  )
}
