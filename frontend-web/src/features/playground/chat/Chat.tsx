"use client";

import { useChat } from "ai/react";
import { useState } from "react";

import { ModelPicker } from "@/features/playground/model-picker/ModelPicker";
import { CodeSnippets } from "@/features/playground/code-snippets/CodeSnippets";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Card } from "@/shared/ui/card";

// FE-003 + FE-007: streaming chat with model picker and snippet generator.
// useChat hits /api/proxy/v1/chat/completions which forwards to the gateway.
export function Chat() {
  const [model, setModel] = useState("anthropic/claude-sonnet-4-20250514");

  const { messages, input, handleInputChange, handleSubmit, isLoading, stop } = useChat({
    api: "/api/proxy/v1/chat/completions",
    body: { model },
  });

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <Card className="flex h-[calc(100dvh-220px)] flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Send a message to start. Streaming output appears here.
            </p>
          )}
          {messages.map((m) => (
            <div key={m.id} className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {m.role}
              </p>
              <pre className="whitespace-pre-wrap text-sm leading-relaxed">{m.content}</pre>
            </div>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2 border-t p-4">
          <Input
            value={input}
            onChange={handleInputChange}
            placeholder="Ask anything…"
            aria-label="Message"
          />
          {isLoading ? (
            <Button type="button" variant="outline" onClick={() => stop()}>
              Stop
            </Button>
          ) : (
            <Button type="submit" disabled={!input.trim()}>
              Send
            </Button>
          )}
        </form>
      </Card>

      <aside className="space-y-4">
        <ModelPicker value={model} onChange={setModel} />
        <CodeSnippets model={model} prompt={messages.at(-2)?.content ?? "Hello"} />
      </aside>
    </div>
  );
}
