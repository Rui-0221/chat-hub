import { useState } from "react";
import { CloseIcon, MoreIcon, PlusIcon, SparkIcon } from "@/components/icons";
import type { AgentInfo, StoredSession } from "@/types/chat";
import styles from "@/app/page.module.css";

interface Props { agents: AgentInfo[]; selectedId: string; sessions: StoredSession[]; activeSessionId: string; open: boolean; loading: boolean; onSelect: (id: string) => void; onSelectSession: (id: string) => void; onRenameSession: (id: string, title: string) => void; onDeleteSession: (id: string) => void; onNewChat: () => void; onClose: () => void }

function sessionTime(value: string): string {
  const date = new Date(value);
  const today = new Date();
  const sameDay = date.getFullYear() === today.getFullYear()
    && date.getMonth() === today.getMonth()
    && date.getDate() === today.getDate();
  return sameDay
    ? new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }).format(date)
    : new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(date);
}

export function Sidebar({ agents, selectedId, sessions, activeSessionId, open, loading, onSelect, onSelectSession, onRenameSession, onDeleteSession, onNewChat, onClose }: Props) {
  const [menuSessionId, setMenuSessionId] = useState<string | null>(null);
  return <aside className={`${styles.sidebar} ${open ? styles.sidebarOpen : ""}`} aria-label="对话与智能体导航" onKeyDown={(event) => { if (event.key === "Escape") { if (menuSessionId) setMenuSessionId(null); else onClose(); } }}>
    <div className={styles.brandRow}><div className={styles.brandMark}><SparkIcon /></div><div><strong>Chat Hub</strong><span>Enterprise AI</span></div><button className={styles.closeSidebar} onClick={onClose} aria-label="关闭智能体导航"><CloseIcon /></button></div>
    <button className={styles.newChat} onClick={onNewChat}><PlusIcon />新对话</button>
    <div className={styles.sidebarScroll}>
      <div className={styles.agentHeading}><span>智能体</span><span>{agents.length || "—"}</span></div>
      <div className={styles.agentList} aria-busy={loading}>
        {loading && <p className={styles.muted}>正在连接工作空间…</p>}
        {!loading && agents.length === 0 && <p className={styles.muted}>暂无可用智能体</p>}
        {agents.map((agent) => <button key={agent.key} className={`${styles.agentCard} ${agent.key === selectedId ? styles.agentActive : ""}`} onClick={() => onSelect(agent.key)} aria-pressed={agent.key === selectedId}><span className={styles.agentAvatar}>{agent.name.slice(0, 1).toUpperCase()}</span><span><strong>{agent.name}</strong><small>{agent.description}</small></span></button>)}
      </div>
      <div className={styles.agentHeading}><span>最近对话</span><span>{sessions.length}</span></div>
      <div className={styles.historyList}>
        {sessions.map((session) => {
          const active = session.id === activeSessionId;
          const menuOpen = session.id === menuSessionId;
          return <div key={session.id} className={`${styles.historyItem} ${active ? styles.historyActive : ""}`}>
            <button className={styles.historySelect} onClick={() => { setMenuSessionId(null); onSelectSession(session.id); }} aria-current={active ? "page" : undefined}>
              <strong>{session.title}</strong>
              <time dateTime={session.updatedAt} title={new Date(session.updatedAt).toLocaleString("zh-CN")}>{sessionTime(session.updatedAt)}</time>
            </button>
            <button className={styles.historyMenuButton} onClick={() => setMenuSessionId(menuOpen ? null : session.id)} aria-label={`管理对话：${session.title}`} aria-expanded={menuOpen} aria-haspopup="menu"><MoreIcon /></button>
            {menuOpen && <div className={styles.historyMenu} role="menu" aria-label={`对话操作：${session.title}`}>
              <button role="menuitem" onClick={() => { setMenuSessionId(null); const title = window.prompt("重命名对话", session.title); if (title?.trim()) onRenameSession(session.id, title); }}>重命名</button>
              <button role="menuitem" onClick={() => { setMenuSessionId(null); if (window.confirm(`确定删除“${session.title}”吗？此操作无法撤销。`)) onDeleteSession(session.id); }}>删除</button>
            </div>}
          </div>;
        })}
      </div>
      <p className={styles.storageNotice}>对话仅保存在此浏览器。后端重启后，旧 threadId 的上下文可能无法继续。</p>
    </div>
    <div className={styles.sidebarFooter}><span className={`${styles.statusDot} ${!loading && agents.length === 0 ? styles.statusDotOffline : ""}`} />{loading ? "正在连接服务" : agents.length ? "服务已连接" : "服务暂不可用"}</div>
  </aside>;
}
