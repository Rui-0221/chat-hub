import { createId } from "@/lib/ids";
import type { ChatMessage, SessionHistory, StoredSession } from "@/types/chat";

const LEGACY_SESSION_KEY = "chat-hub-session";
const SESSION_HISTORY_KEY = "chat-hub-session-history";
const SESSION_HISTORY_VERSION = 1;
export const DEFAULT_AGENT_ID = "oa-assistant";
const DEFAULT_TITLE = "新对话";

export type SessionHistoryAction =
  | { type: "create"; agentId: string }
  | { type: "activate"; sessionId: string }
  | { type: "update"; sessionId: string; agentId?: string; messages?: ChatMessage[] }
  | { type: "rename"; sessionId: string; title: string }
  | { type: "delete"; sessionId: string; fallbackAgentId: string };

function normalizeMessages(value: unknown): ChatMessage[] {
  if (!Array.isArray(value)) return [];

  return value.flatMap((item): ChatMessage[] => {
    if (!item || typeof item !== "object") return [];
    const message = item as Record<string, unknown>;
    const role = message.role === "ai" ? "assistant" : message.role;
    if ((role !== "user" && role !== "assistant") || typeof message.content !== "string") return [];
    if (role === "assistant" && !message.content.trim()) return [];
    // 只保留 id/role/content/steps；reasoning（思考过程）不落入本地历史。
    const steps = Array.isArray(message.steps) ? message.steps.flatMap((item): { agent: string; result?: string }[] => {
      if (!item || typeof item !== "object") return [];
      const step = item as Record<string, unknown>;
      if (typeof step.agent !== "string" || !step.agent) return [];
      return [{
        agent: step.agent,
        result: typeof step.result === "string" ? step.result : undefined,
      }];
    }) : undefined;
    return [{
      id: typeof message.id === "string" ? message.id : createId("restored"),
      role,
      content: message.content,
      ...(steps?.length ? { steps } : {}),
    }];
  });
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function date(value: unknown, fallback: string): string {
  if (typeof value !== "string" || Number.isNaN(Date.parse(value))) return fallback;
  return new Date(value).toISOString();
}

function titleFromMessages(messages: ChatMessage[]): string {
  const firstPrompt = messages.find((message) => message.role === "user" && message.content.trim());
  if (!firstPrompt) return DEFAULT_TITLE;
  const compact = firstPrompt.content.trim().replace(/\s+/g, " ");
  return compact.length > 36 ? `${compact.slice(0, 36)}…` : compact;
}

function newSession(agentId: string): StoredSession {
  const now = new Date().toISOString();
  return {
    id: createId("session"),
    threadId: createId("thread"),
    agentId: text(agentId) ?? DEFAULT_AGENT_ID,
    title: DEFAULT_TITLE,
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

function normalizeSession(value: unknown, fallbackTime: string): StoredSession | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Record<string, unknown>;
  const threadId = text(item.threadId) ?? text(item.thread_id);
  if (!threadId) return null;
  const messages = normalizeMessages(item.messages);
  const createdAt = date(item.createdAt, fallbackTime);
  const updatedAt = date(item.updatedAt, createdAt);
  return {
    id: text(item.id) ?? createId("session"),
    threadId,
    agentId: text(item.agentId) ?? text(item.agent_id) ?? DEFAULT_AGENT_ID,
    title: text(item.title) ?? titleFromMessages(messages),
    messages,
    createdAt,
    updatedAt,
  };
}

function normalizeHistory(value: unknown): SessionHistory | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Record<string, unknown>;
  if (!Array.isArray(item.sessions)) return null;
  const now = new Date().toISOString();
  const seen = new Set<string>();
  const sessions = item.sessions
    .flatMap((session) => {
      const normalized = normalizeSession(session, now);
      if (!normalized || seen.has(normalized.id)) return [];
      seen.add(normalized.id);
      return [normalized];
    })
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
  if (!sessions.length) return null;
  const requestedActiveId = text(item.activeSessionId);
  return {
    activeSessionId: sessions.some((session) => session.id === requestedActiveId)
      ? requestedActiveId as string
      : sessions[0].id,
    sessions,
  };
}

function persist(history: SessionHistory): boolean {
  try {
    const normalized = normalizeHistory(history);
    if (!normalized) return false;
    localStorage.setItem(SESSION_HISTORY_KEY, JSON.stringify({
      version: SESSION_HISTORY_VERSION,
      ...normalized,
    }));
    return true;
  } catch {
    return false;
  }
}

export function loadSessionHistory(): SessionHistory {
  try {
    const current = localStorage.getItem(SESSION_HISTORY_KEY);
    if (current) {
      const restored = normalizeHistory(JSON.parse(current));
      if (restored) return restored;
    }

    const legacy = localStorage.getItem(LEGACY_SESSION_KEY);
    if (legacy) {
      const migrated = normalizeSession(JSON.parse(legacy), new Date().toISOString());
      if (migrated) {
        const history = { activeSessionId: migrated.id, sessions: [migrated] };
        if (persist(history)) localStorage.removeItem(LEGACY_SESSION_KEY);
        return history;
      }
    }
  } catch {
    // Corrupt or unavailable browser storage falls back to a fresh in-memory session.
  }

  const session = newSession(DEFAULT_AGENT_ID);
  return { activeSessionId: session.id, sessions: [session] };
}

export function saveSessionHistory(history: SessionHistory): boolean {
  return persist(history);
}

export function reduceSessionHistory(history: SessionHistory, action: SessionHistoryAction): SessionHistory {
  if (action.type === "create") {
    const current = history.sessions.find((session) => session.id === history.activeSessionId);
    if (current && current.messages.length === 0) {
      if (current.agentId === action.agentId) return history;
      const now = new Date().toISOString();
      return {
        ...history,
        sessions: history.sessions.map((session) => session.id === current.id
          ? { ...session, agentId: text(action.agentId) ?? session.agentId, updatedAt: now }
          : session),
      };
    }
    const session = newSession(action.agentId);
    return { activeSessionId: session.id, sessions: [session, ...history.sessions] };
  }

  if (action.type === "activate") {
    return history.sessions.some((session) => session.id === action.sessionId)
      ? { ...history, activeSessionId: action.sessionId }
      : history;
  }

  if (action.type === "delete") {
    const sessions = history.sessions.filter((session) => session.id !== action.sessionId);
    if (!sessions.length) {
      const session = newSession(action.fallbackAgentId);
      return { activeSessionId: session.id, sessions: [session] };
    }
    return {
      activeSessionId: history.activeSessionId === action.sessionId ? sessions[0].id : history.activeSessionId,
      sessions,
    };
  }

  const now = new Date().toISOString();
  const sessions = history.sessions.map((session) => {
    if (session.id !== action.sessionId) return session;
    if (action.type === "rename") {
      return { ...session, title: text(action.title) ?? session.title, updatedAt: now };
    }
    const messages = action.messages ?? session.messages;
    const alreadyTitled = session.messages.some((message) => message.role === "user" && message.content.trim());
    return {
      ...session,
      agentId: text(action.agentId) ?? session.agentId,
      messages,
      title: session.title === DEFAULT_TITLE && !alreadyTitled ? titleFromMessages(messages) : session.title,
      updatedAt: now,
    };
  }).sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
  return { ...history, sessions };
}
