import { useEffect, useRef } from "react";
import { SendIcon, StopIcon } from "@/components/icons";
import styles from "@/app/page.module.css";

interface Props { value: string; streaming: boolean; disabled: boolean; onChange: (value: string) => void; onSend: () => void; onStop: () => void; focusToken: string }

export function Composer({ value, streaming, disabled, onChange, onSend, onStop, focusToken }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { ref.current?.focus(); }, [focusToken]);
  useEffect(() => { const el = ref.current; if (el) { el.style.height = "auto"; el.style.height = `${Math.min(el.scrollHeight, 160)}px`; } }, [value]);
  return <div className={styles.composerWrap}><form className={styles.composer} onSubmit={(event) => { event.preventDefault(); if (!streaming) onSend(); }}>
    <textarea ref={ref} rows={1} value={value} onChange={(event) => onChange(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); onSend(); } }} placeholder="向智能体提问…" aria-label="消息内容" disabled={disabled} />
    <button type={streaming ? "button" : "submit"} className={streaming ? styles.stopButton : styles.sendButton} onClick={streaming ? onStop : undefined} disabled={!streaming && (disabled || !value.trim())} aria-label={streaming ? "停止生成" : "发送消息"}>{streaming ? <StopIcon /> : <SendIcon />}</button>
  </form><p>Enter 发送 · Shift + Enter 换行 · AI 生成内容仅供参考</p></div>;
}
