import { readSseStream } from "@/lib/sse";
import type { AgentInfo, ChatStreamEvent } from "@/types/chat";

const AGENTS_ENDPOINT = "/api/v1/agents";
const CHAT_ENDPOINT = "/api/v1/chat";

async function responseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown; message?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (typeof body.message === "string") return body.message;
  } catch {
    // The HTTP status below remains useful when the response is not JSON.
  }
  return `请求失败（HTTP ${response.status}）`;
}

export async function fetchAgents(signal?: AbortSignal): Promise<AgentInfo[]> {
  const response = await fetch(AGENTS_ENDPOINT, { signal, cache: "no-store" });
  if (!response.ok) throw new Error(await responseError(response));

  const data: unknown = await response.json();
  if (!Array.isArray(data)) throw new Error("智能体列表格式不正确");

  return data.flatMap((item): AgentInfo[] => {
    if (!item || typeof item !== "object") return [];
    const value = item as Record<string, unknown>;
    if (typeof value.key !== "string") return [];
    return [{
      key: value.key,
      name: typeof value.name === "string" ? value.name : value.key,
      description: typeof value.description === "string" ? value.description : "企业智能助理",
      capabilities: Array.isArray(value.capabilities)
        ? value.capabilities.filter((capability): capability is string => typeof capability === "string")
        : [],
    }];
  });
}

interface StreamChatOptions {
  message: string;
  threadId: string;
  agentId: string;
  signal: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
}

export async function streamChat(options: StreamChatOptions): Promise<void> {
  const response = await fetch(CHAT_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({
      message: options.message,
      thread_id: options.threadId,
      agent_id: options.agentId,
    }),
    signal: options.signal,
  });

  if (!response.ok) throw new Error(await responseError(response));
  if (!response.body) throw new Error("浏览器未收到可读取的响应流");
  await readSseStream(response.body, options.onEvent);
}
