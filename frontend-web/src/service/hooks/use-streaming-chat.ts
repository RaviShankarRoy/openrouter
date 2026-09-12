"use client";

import { useChat } from "@ai-sdk/react";
import { useCallback, useMemo } from "react";

// Thin wrapper over Vercel AI SDK's useChat (FE-003).
// We default the API path to the BFF, surface a typed `status`, and expose a
// `regenerate` helper that pops the last assistant message before re-submitting.
export type StreamingChatOptions = {
  api?: string;
  modelId: string;
  systemPrompt?: string;
  temperature?: number;
};

export function useStreamingChat(options: StreamingChatOptions) {
  const { api = "/api/proxy/chat/completions", modelId, systemPrompt, temperature } = options;

  const initialMessages = useMemo(
    () =>
      systemPrompt
        ? [{ id: "system-0", role: "system" as const, content: systemPrompt }]
        : [],
    [systemPrompt],
  );

  const chat = useChat({
    api,
    initialMessages,
    body: { model: modelId, temperature },
    streamProtocol: "text",
  });

  const regenerate = useCallback(async () => {
    if (chat.messages.length === 0) return;
    const last = chat.messages[chat.messages.length - 1];
    if (last?.role === "assistant") {
      chat.setMessages(chat.messages.slice(0, -1));
    }
    await chat.reload();
  }, [chat]);

  return { ...chat, regenerate };
}
