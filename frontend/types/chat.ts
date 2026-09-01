export interface AgentInfo {
  key: string;
  name: string;
  description: string;
  capabilities: string[];
}

export type MessageRole = "user" | "assistant";

/** 多智能体执行中的一个步骤：进入子 agent，以及它最终给出的结论。 */
export interface AgentStep {
  agent: string;
  result?: string;
  /** 该子 agent 的思考过程（流式期间累积，不写入历史）。 */
  thinking?: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  /** 主管/单智能体模型的思考过程（deepseek thinking mode），仅在当次流式期间存在，不写入历史；子 agent 的思考挂在其 steps[].thinking。 */
  reasoning?: string;
  /** 多智能体中间步骤（进入哪个子 agent + 它的结论）。 */
  steps?: AgentStep[];
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
  | { type: "reasoning"; content: string; agent?: string }
  | { type: "step"; agent: string }
  | { type: "agent_result"; agent: string; content: string }
  | { type: "error"; content?: string; message?: string }
  | { type: "end" };
