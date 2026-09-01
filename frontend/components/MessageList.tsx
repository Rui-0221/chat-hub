import { useState } from "react";
import { SparkIcon, UserIcon } from "@/components/icons";
import type { ChatMessage } from "@/types/chat";
import styles from "@/app/page.module.css";

function ThinkingBlock({ reasoning, live }: { reasoning: string; live: boolean }) {
  const [open, setOpen] = useState(false);
  const expanded = open || live;
  return (
    <div className={styles.thinkingBlock}>
      <button type="button" className={styles.thinkingToggle} onClick={() => setOpen((value) => !value)} aria-expanded={expanded}>
        <span className={styles.thinkingDot} aria-hidden="true" />
        {expanded ? "收起思考" : "查看思考"}
      </button>
      {expanded && <p className={styles.thinkingText}>{reasoning}</p>}
    </div>
  );
}

export function MessageList({ messages, streamingId }: { messages: ChatMessage[]; streamingId: string | null }) {
  return <div className={styles.messageList}>{messages.map((message) => <article key={message.id} className={`${styles.message} ${message.role === "user" ? styles.userMessage : ""}`}><div className={styles.messageAvatar}>{message.role === "user" ? <UserIcon /> : <SparkIcon />}</div><div className={styles.messageBody}><strong>{message.role === "user" ? "你" : "AI 助理"}</strong>{message.role === "assistant" && message.reasoning ? <ThinkingBlock reasoning={message.reasoning} live={streamingId === message.id} /> : null}{message.steps && message.steps.length > 0 ? <div className={styles.stepList}>{message.steps.map((step, index) => <div key={`${step.agent}-${index}`} className={styles.agentStep}><span className={styles.stepBadge}>→ {step.agent}</span>{step.thinking ? <ThinkingBlock reasoning={step.thinking} live={streamingId === message.id} /> : null}{step.result !== undefined ? <details className={styles.agentResult}><summary>该 agent 的结论</summary><p>{step.result}</p></details> : <span className={styles.stepPending}>处理中…</span>}</div>)}</div> : null}{message.content ? <p>{message.content}</p> : message.id === streamingId ? <span className={styles.typing} aria-label="正在生成"><i /><i /><i /></span> : <p className={styles.muted}>未生成内容</p>}</div></article>)}</div>;
}
