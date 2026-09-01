"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Composer } from "@/components/Composer";
import { EmptyState } from "@/components/EmptyState";
import { MenuIcon, PlusIcon } from "@/components/icons";
import { MessageList } from "@/components/MessageList";
import { Sidebar } from "@/components/Sidebar";
import { fetchAgents, streamChat } from "@/lib/api";
import { createId } from "@/lib/ids";
import { DEFAULT_AGENT_ID, loadSessionHistory, reduceSessionHistory, saveSessionHistory } from "@/lib/session";
import type { AgentInfo, ChatMessage, SessionHistory } from "@/types/chat";
import styles from "./page.module.css";

export default function Home() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [history, setHistory] = useState<SessionHistory>({ activeSessionId: "", sessions: [] });
  const [input, setInput] = useState("");
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [focusToken, setFocusToken] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const followLatestRef = useRef(true);
  const requestRef = useRef<{ id: string; sessionId: string; assistantId: string; controller: AbortController } | null>(null);
  const saveErrorShownRef = useRef(false);
  const loadedRef = useRef(false);
  const historyRef = useRef(history);
  const lastSaveAtRef = useRef(0);
  historyRef.current = history;
  const activeSession = useMemo(() => history.sessions.find((session) => session.id === history.activeSessionId), [history]);
  const selectedAgent = useMemo(() => agents.find((agent) => agent.key === activeSession?.agentId), [activeSession?.agentId, agents]);
  const messages = activeSession?.messages ?? [];

  useEffect(() => {
    const restored = loadSessionHistory();
    historyRef.current = restored;
    loadedRef.current = true;
    setHistory(restored);
    setLoaded(true);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    fetchAgents(controller.signal).then(setAgents).catch((cause: unknown) => { if (!(cause instanceof DOMException && cause.name === "AbortError")) setError(cause instanceof Error ? cause.message : "无法加载智能体"); }).finally(() => setLoadingAgents(false));
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!loaded || !history.activeSessionId) return;
    const wait = Math.max(0, 250 - (Date.now() - lastSaveAtRef.current));
    const timer = window.setTimeout(() => {
      if (saveSessionHistory(historyRef.current)) {
        lastSaveAtRef.current = Date.now();
        saveErrorShownRef.current = false;
      } else if (!saveErrorShownRef.current) {
        saveErrorShownRef.current = true;
        setError("无法保存本地会话，刷新后内容可能丢失");
      }
    }, wait);
    return () => window.clearTimeout(timer);
  }, [history, loaded]);
  useEffect(() => {
    const flushHistory = () => {
      const current = historyRef.current;
      if (!loadedRef.current || !current.activeSessionId) return;
      if (saveSessionHistory(current)) {
        lastSaveAtRef.current = Date.now();
        saveErrorShownRef.current = false;
      }
    };
    window.addEventListener("pagehide", flushHistory);
    return () => window.removeEventListener("pagehide", flushHistory);
  }, []);
  useEffect(() => {
    const scroller = scrollRef.current;
    if (scroller && followLatestRef.current) scroller.scrollTo({ top: scroller.scrollHeight, behavior: streamingId ? "auto" : "smooth" });
  }, [messages, streamingId]);
  useEffect(() => () => { const request = requestRef.current; requestRef.current = null; request?.controller.abort(); }, []);

  const updateMessages = useCallback((sessionId: string, update: (messages: ChatMessage[]) => ChatMessage[]) => {
    setHistory((current) => {
      const session = current.sessions.find((item) => item.id === sessionId);
      return session
        ? reduceSessionHistory(current, { type: "update", sessionId, messages: update(session.messages) })
        : current;
    });
  }, []);

  const cancelRequest = useCallback(() => {
    const request = requestRef.current;
    if (!request) return;
    requestRef.current = null;
    setStreamingId(null);
    updateMessages(request.sessionId, (current) => current.filter((message) => message.id !== request.assistantId || Boolean(message.content.trim())));
    request.controller.abort();
  }, [updateMessages]);

  const prepareSession = useCallback(() => {
    followLatestRef.current = true;
    setInput("");
    setError("");
    setSidebarOpen(false);
    setFocusToken(createId("focus"));
  }, []);

  const newChat = useCallback(() => {
    cancelRequest();
    setHistory((current) => reduceSessionHistory(current, { type: "create", agentId: activeSession?.agentId ?? DEFAULT_AGENT_ID }));
    prepareSession();
  }, [activeSession?.agentId, cancelRequest, prepareSession]);

  const selectAgent = useCallback((id: string) => {
    if (id === activeSession?.agentId) { setSidebarOpen(false); return; }
    cancelRequest();
    setHistory((current) => reduceSessionHistory(current, { type: "create", agentId: id }));
    prepareSession();
  }, [activeSession?.agentId, cancelRequest, prepareSession]);

  const selectSession = useCallback((sessionId: string) => {
    if (sessionId === history.activeSessionId) { setSidebarOpen(false); return; }
    cancelRequest();
    setHistory((current) => reduceSessionHistory(current, { type: "activate", sessionId }));
    prepareSession();
  }, [cancelRequest, history.activeSessionId, prepareSession]);

  const deleteSession = useCallback((sessionId: string) => {
    if (sessionId === history.activeSessionId) cancelRequest();
    setHistory((current) => reduceSessionHistory(current, { type: "delete", sessionId, fallbackAgentId: activeSession?.agentId ?? DEFAULT_AGENT_ID }));
    if (sessionId === history.activeSessionId) prepareSession();
  }, [activeSession?.agentId, cancelRequest, history.activeSessionId, prepareSession]);

  const renameSession = useCallback((sessionId: string, title: string) => {
    setHistory((current) => reduceSessionHistory(current, { type: "rename", sessionId, title }));
  }, []);

  const send = useCallback(async () => {
    const content = input.trim();
    if (!content || streamingId || !activeSession || !selectedAgent) return;
    const sessionId = activeSession.id;
    const userMessage: ChatMessage = { id: createId("user"), role: "user", content };
    const assistantId = createId("assistant");
    const controller = new AbortController();
    const requestId = createId("request");
    requestRef.current = { id: requestId, sessionId, assistantId, controller };
    followLatestRef.current = true;
    updateMessages(sessionId, (current) => [...current, userMessage, { id: assistantId, role: "assistant", content: "" }]); setInput(""); setError(""); setStreamingId(assistantId);
    try {
      await streamChat({ message: content, threadId: activeSession.threadId, agentId: selectedAgent.key, signal: controller.signal, onEvent: (event) => {
        if (requestRef.current?.id !== requestId) return;
        if (event.type === "token") updateMessages(sessionId, (current) => current.map((message) => message.id === assistantId ? { ...message, content: message.content + event.content } : message));
        if (event.type === "reasoning") updateMessages(sessionId, (current) => current.map((message) => {
          if (message.id !== assistantId) return message;
          // 带 agent 归属的事件是子 agent 的思考：挂到对应步骤；否则是主管思考。
          if (!event.agent) return { ...message, reasoning: (message.reasoning ?? "") + event.content };
          const steps = [...(message.steps ?? [])];
          for (let index = steps.length - 1; index >= 0; index -= 1) {
            if (steps[index].agent === event.agent) {
              steps[index] = { ...steps[index], thinking: (steps[index].thinking ?? "") + event.content };
              return { ...message, steps };
            }
          }
          return { ...message, steps: [...steps, { agent: event.agent, thinking: event.content }] };
        }));
        if (event.type === "step") updateMessages(sessionId, (current) => current.map((message) => message.id === assistantId ? { ...message, steps: [...(message.steps ?? []), { agent: event.agent }] } : message));
        if (event.type === "agent_result") updateMessages(sessionId, (current) => current.map((message) => {
          if (message.id !== assistantId) return message;
          const steps = [...(message.steps ?? [])];
          for (let index = steps.length - 1; index >= 0; index -= 1) {
            if (steps[index].agent === event.agent && steps[index].result === undefined) {
              steps[index] = { ...steps[index], result: event.content };
              return { ...message, steps };
            }
          }
          return { ...message, steps: [...steps, { agent: event.agent, result: event.content }] };
        }));
        if (event.type === "error") throw new Error(event.message ?? event.content ?? "智能体生成失败");
      }});
    } catch (cause: unknown) {
      if (requestRef.current?.id !== requestId) return;
      updateMessages(sessionId, (current) => current.filter((message) => message.id !== assistantId || Boolean(message.content.trim())));
      if (!(cause instanceof DOMException && cause.name === "AbortError")) setError(cause instanceof Error ? cause.message : "消息发送失败，请稍后重试");
    } finally {
      if (requestRef.current?.id === requestId) {
        updateMessages(sessionId, (current) => current.filter((message) => message.id !== assistantId || Boolean(message.content.trim())));
        requestRef.current = null;
        setStreamingId(null);
      }
    }
  }, [activeSession, input, selectedAgent, streamingId, updateMessages]);

  return <div className={styles.shell}>
    <Sidebar agents={agents} selectedId={activeSession?.agentId ?? ""} sessions={history.sessions} activeSessionId={history.activeSessionId} open={sidebarOpen} loading={loadingAgents} onSelect={selectAgent} onSelectSession={selectSession} onRenameSession={renameSession} onDeleteSession={deleteSession} onNewChat={newChat} onClose={() => setSidebarOpen(false)} />
    {sidebarOpen && <button className={styles.scrim} onClick={() => setSidebarOpen(false)} aria-label="关闭导航" />}
    <section className={styles.workspace}>
      <header className={styles.topbar}><button className={styles.menuButton} onClick={() => setSidebarOpen(true)} aria-label="打开智能体导航"><MenuIcon /></button><div><span>当前智能体</span><h1>{selectedAgent?.name ?? (loadingAgents ? "AI 工作台" : "智能体不可用")}</h1></div><button className={styles.topNewChat} onClick={newChat}><PlusIcon /><span>新对话</span></button></header>
      <main className={styles.chat} ref={scrollRef} onScroll={() => { const scroller = scrollRef.current; if (scroller) followLatestRef.current = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 96; }}>{messages.length === 0 ? <EmptyState agent={selectedAgent} onPrompt={(prompt) => { setInput(prompt); setFocusToken(createId("focus")); }} /> : <MessageList messages={messages} streamingId={streamingId} />}</main>
      <div className={styles.liveRegion} aria-live="polite" aria-atomic="true">{error || (streamingId ? "智能体正在生成回复" : "")}</div>
      {error && <div className={styles.errorBanner} role="alert">{error}<button onClick={() => setError("")} aria-label="关闭错误提示">×</button></div>}
      <Composer value={input} streaming={Boolean(streamingId)} disabled={!selectedAgent || loadingAgents} onChange={setInput} onSend={send} onStop={cancelRequest} focusToken={focusToken} />
    </section>
  </div>;
}
