"use client";

import { useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/api/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/api/ui/tabs";
import { Button } from "@/api/ui/button";
import { useClipboard } from "@/service/hooks/use-clipboard";

// FE-007: copyable snippets matching the playground state.
export function CodeSnippets({ model, prompt }: { model: string; prompt: string }) {
  const { copy, copied } = useClipboard();
  const [tab, setTab] = useState("python");
  const snippets = build(model, prompt);
  const current = snippets[tab as keyof typeof snippets];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Code snippet</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="python">Python</TabsTrigger>
            <TabsTrigger value="js">JS</TabsTrigger>
            <TabsTrigger value="curl">cURL</TabsTrigger>
            <TabsTrigger value="go">Go</TabsTrigger>
          </TabsList>
          {(["python", "js", "curl", "go"] as const).map((k) => (
            <TabsContent key={k} value={k}>
              <pre className="max-h-64 overflow-auto rounded bg-muted p-3 font-mono text-xs">
                {snippets[k]}
              </pre>
            </TabsContent>
          ))}
        </Tabs>
        <Button variant="outline" size="sm" className="mt-2" onClick={() => copy(current)}>
          {copied ? "Copied" : "Copy"}
        </Button>
      </CardContent>
    </Card>
  );
}

function build(model: string, prompt: string) {
  const safe = prompt.replace(/"/g, '\\"').slice(0, 200);
  return {
    python: `from openai import OpenAI

client = OpenAI(
    base_url="https://api.openrouter.example.com/api/v1",
    api_key="$OPENROUTER_API_KEY",
)
resp = client.chat.completions.create(
    model="${model}",
    messages=[{"role": "user", "content": "${safe}"}],
)
print(resp.choices[0].message.content)`,
    js: `import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://api.openrouter.example.com/api/v1",
  apiKey: process.env.OPENROUTER_API_KEY,
});

const resp = await client.chat.completions.create({
  model: "${model}",
  messages: [{ role: "user", content: "${safe}" }],
});
console.log(resp.choices[0].message.content);`,
    curl: `curl https://api.openrouter.example.com/api/v1/chat/completions \\
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"${model}","messages":[{"role":"user","content":"${safe}"}]}'`,
    go: `package main

import (
    "context"
    openai "github.com/sashabaranov/go-openai"
)

func main() {
    cfg := openai.DefaultConfig("OPENROUTER_API_KEY")
    cfg.BaseURL = "https://api.openrouter.example.com/api/v1"
    client := openai.NewClientWithConfig(cfg)
    resp, _ := client.CreateChatCompletion(context.Background(), openai.ChatCompletionRequest{
        Model:    "${model}",
        Messages: []openai.ChatCompletionMessage{{Role: "user", Content: "${safe}"}},
    })
    println(resp.Choices[0].Message.Content)
}`,
  };
}
