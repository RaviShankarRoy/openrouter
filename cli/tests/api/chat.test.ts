import { describe, it, expect } from 'vitest';
import { Readable } from 'node:stream';
import { parseSseChunks, type ChatCompletionChunk } from '../../src/repository/api-client.js';
import { renderAssistant } from '../../src/api/chat.js';
import { pickRenderer } from '../../src/api/output.js';

function streamFrom(strings: string[]): NodeJS.ReadableStream {
  return Readable.from(strings.map((s) => Buffer.from(s, 'utf-8')));
}

describe('SSE streaming parser', () => {
  it('parses a single complete event', async () => {
    const stream = streamFrom([
      'data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m","choices":[{"index":0,"delta":{"content":"hi"},"finish_reason":null}]}\n\n',
    ]);
    const chunks: ChatCompletionChunk[] = [];
    for await (const c of parseSseChunks(stream)) chunks.push(c);
    expect(chunks).toHaveLength(1);
    expect(chunks[0]?.choices[0]?.delta.content).toBe('hi');
  });

  it('joins events split across chunks', async () => {
    const stream = streamFrom([
      'data: {"id":"1","object":"chat.completion.chunk","crea',
      'ted":1,"model":"m","choices":[{"index":0,"delta":{"content":"world"},"finish_reason":null}]}',
      '\n\n',
    ]);
    const chunks: ChatCompletionChunk[] = [];
    for await (const c of parseSseChunks(stream)) chunks.push(c);
    expect(chunks).toHaveLength(1);
    expect(chunks[0]?.choices[0]?.delta.content).toBe('world');
  });

  it('terminates on [DONE] and ignores subsequent payload', async () => {
    const stream = streamFrom([
      'data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m","choices":[{"index":0,"delta":{"content":"a"},"finish_reason":null}]}\n\n',
      'data: [DONE]\n\n',
      'data: {"id":"2","object":"chat.completion.chunk","created":2,"model":"m","choices":[{"index":0,"delta":{"content":"b"},"finish_reason":null}]}\n\n',
    ]);
    const chunks: ChatCompletionChunk[] = [];
    for await (const c of parseSseChunks(stream)) chunks.push(c);
    expect(chunks).toHaveLength(1);
    expect(chunks[0]?.choices[0]?.delta.content).toBe('a');
  });

  it('skips comments and unknown fields', async () => {
    const stream = streamFrom([
      ': keepalive\n\n',
      'event: ping\ndata: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m","choices":[{"index":0,"delta":{"content":"ok"},"finish_reason":null}]}\n\n',
    ]);
    const chunks: ChatCompletionChunk[] = [];
    for await (const c of parseSseChunks(stream)) chunks.push(c);
    expect(chunks).toHaveLength(1);
    expect(chunks[0]?.choices[0]?.delta.content).toBe('ok');
  });

  it('tolerates malformed JSON without throwing', async () => {
    const stream = streamFrom([
      'data: {bad json\n\n',
      'data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m","choices":[{"index":0,"delta":{"content":"k"},"finish_reason":null}]}\n\n',
    ]);
    const chunks: ChatCompletionChunk[] = [];
    for await (const c of parseSseChunks(stream)) chunks.push(c);
    expect(chunks).toHaveLength(1);
  });

  it('handles \\r\\n line endings', async () => {
    const stream = streamFrom([
      'data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m","choices":[{"index":0,"delta":{"content":"x"},"finish_reason":null}]}\r\n\r\n',
    ]);
    const chunks: ChatCompletionChunk[] = [];
    for await (const c of parseSseChunks(stream)) chunks.push(c);
    expect(chunks).toHaveLength(1);
  });
});

describe('renderAssistant', () => {
  it('returns input unchanged when color is disabled', () => {
    const r = pickRenderer({ json: false, color: false });
    const text = '```js\nconst a = 1;\n```';
    expect(renderAssistant(text, r)).toBe(text);
  });

  it('returns input unchanged when there are no fenced blocks', () => {
    const r = pickRenderer({ json: false, color: true });
    const text = 'plain prose';
    expect(renderAssistant(text, r)).toBe(text);
  });
});
