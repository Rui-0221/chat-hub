import { SparkIcon, UserIcon } from "@/components/icons";
import type { ChatMessage } from "@/types/chat";
import styles from "@/app/page.module.css";

export function MessageList({ messages, streamingId }: { messages: ChatMessage[]; streamingId: string | null }) {
  return <div className={styles.messageList}>{messages.map((message) => <article key={message.id} className={`${styles.message} ${message.role === "user" ? styles.userMessage : ""}`}><div className={styles.messageAvatar}>{message.role === "user" ? <UserIcon /> : <SparkIcon />}</div><div className={styles.messageBody}><strong>{message.role === "user" ? "你" : "AI 助理"}</strong>{message.content ? <p>{message.content}</p> : message.id === streamingId ? <span className={styles.typing} aria-label="正在生成"><i /><i /><i /></span> : <p className={styles.muted}>未生成内容</p>}</div></article>)}</div>;
}
