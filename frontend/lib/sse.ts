import type { ChatStreamEvent } from "@/types/chat";

function parseEvent(rawEvent: string): ChatStreamEvent | null {
  const data = rawEvent
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).replace(/^ /, ""))
    .join("\n");

  if (!data) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(data);
  } catch {
    throw new Error("服务端返回了无法解析的流式数据");
  }

  if (!parsed || typeof parsed !== "object" || !("type" in parsed)) {
    return null;
  }

  const event = parsed as Record<string, unknown>;
  if (event.type === "token" && typeof event.content === "string") {
    return { type: "token", content: event.content };
  }
  if (event.type === "reasoning" && typeof event.content === "string") {
    return {
      type: "reasoning",
      content: event.content,
      ...(typeof event.agent === "string" ? { agent: event.agent } : {}),
    };
  }
  if (event.type === "step" && typeof event.agent === "string") {
    return { type: "step", agent: event.agent };
  }
  if (
    event.type === "agent_result"
    && typeof event.agent === "string"
    && typeof event.content === "string"
  ) {
    return { type: "agent_result", agent: event.agent, content: event.content };
  }
  if (event.type === "error") {
    return {
      type: "error",
      content: typeof event.content === "string" ? event.content : undefined,
      message: typeof event.message === "string" ? event.message : undefined,
    };
  }
  if (event.type === "end") return { type: "end" };
  return null;
}

export async function readSseStream(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const consumeCompleteEvents = () => {
    let boundary = buffer.search(/\r?\n\r?\n/);
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      const separator = buffer.slice(boundary).match(/^\r?\n\r?\n/)?.[0] ?? "\n\n";
      buffer = buffer.slice(boundary + separator.length);
      const event = parseEvent(rawEvent);
      if (event) onEvent(event);
      boundary = buffer.search(/\r?\n\r?\n/);
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      consumeCompleteEvents();
    }

    buffer += decoder.decode();
    consumeCompleteEvents();

    // Some servers close immediately after the final event without a blank line.
    const tail = buffer.trim();
    if (tail) {
      const event = parseEvent(tail);
      if (event) onEvent(event);
    }
  } finally {
    reader.releaseLock();
  }
}
