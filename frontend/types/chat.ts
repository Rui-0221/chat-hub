export interface AgentInfo {
  key: string;
  name: string;
  description: string;
  capabilities: string[];
}

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
}

export interface StoredSession {
  id: string;
  threadId: string;
  agentId: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface SessionHistory {
  activeSessionId: string;
  sessions: StoredSession[];
}

export type ChatStreamEvent =
  | { type: "token"; content: string }
  | { type: "error"; content?: string; message?: string }
  | { type: "end" };
