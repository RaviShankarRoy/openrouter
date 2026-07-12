// CLI-003 — Interactive chat REPL with streaming output, model picker, and slash commands.
//
// Slash commands:
//   /clear       reset conversation
//   /save <path> save the conversation as JSON
//   /exit, /quit leave
//
// Streaming uses ApiClient.chatCompletionStream. Code blocks are syntax-highlighted via cli-highlight.
import type { Command } from 'commander';
import { input, select } from '@inquirer/prompts';
import { writeFile } from 'node:fs/promises';
import { highlight, supportsLanguage } from 'cli-highlight';
import { ApiClient, type ChatMessage, type Model } from '../lib/api-client.js';
import { pickRenderer, type Renderer } from '../lib/output.js';
import { exitWithError, ValidationError } from '../lib/errors.js';
import { loadConfig, saveConfig } from '../lib/config.js';
import type { GlobalOptions } from '../cli.js';

export interface ChatOptions extends GlobalOptions {
  model?: string;
  system?: string;
}

export function registerChat(program: Command): void {
  program
    .command('chat')
    .description('Interactive terminal chat with streaming output (CLI-003)')
    .option('--model <id>', 'model id (skip the picker)')
    .option('--system <prompt>', 'system prompt')
    .action(async (opts: ChatOptions, cmd: Command) => {
      const globals = cmd.optsWithGlobals<ChatOptions>();
      try {
        await runChat({ ...globals, ...opts });
      } catch (err) {
        if ((err as { name?: string }).name === 'ExitPromptError') return; // ctrl-c
        exitWithError(err);
      }
    });
}

export async function runChat(opts: ChatOptions, apiOverride?: ApiClient): Promise<void> {
  const r = pickRenderer({ json: opts.json, color: opts.color });
  const cfg = await loadConfig();
  const api = apiOverride ?? (await ApiClient.create({ ...(opts.baseUrl ? { baseUrl: opts.baseUrl } : {}) }));

  let model = opts.model ?? cfg.defaultModel;
  if (opts.model === undefined) {
    model = await pickModel(api, cfg.defaultModel, r);
    if (model !== cfg.defaultModel) {
      await saveConfig({ defaultModel: model });
    }
  }

  const messages: ChatMessage[] = [];
  if (opts.system) messages.push({ role: 'system', content: opts.system });

  if (opts.json !== true) {
    r.text('');
    r.text(r.color.dim(`Model: ${model}. Slash commands: /clear /save <path> /exit`));
    r.text('');
  }

  // eslint-disable-next-line no-constant-condition
  while (true) {
    let line: string;
    try {
      line = await input({ message: r.color.primary('you>') });
    } catch (err) {
      if ((err as { name?: string }).name === 'ExitPromptError') return;
      throw err;
    }
    const trimmed = line.trim();
    if (trimmed.length === 0) continue;

    if (trimmed.startsWith('/')) {
      const handled = await handleSlash(trimmed, messages, r);
      if (handled === 'exit') return;
      continue;
    }

    messages.push({ role: 'user', content: trimmed });

    let assistant = '';
    try {
      if (opts.json !== true) process.stdout.write(r.color.success('ai> '));
      for await (const chunk of api.chatCompletionStream({ model, messages })) {
        const piece = chunk.choices[0]?.delta?.content ?? '';
        if (piece.length === 0) continue;
        assistant += piece;
        if (opts.json !== true) process.stdout.write(piece);
      }
      if (opts.json !== true) {
        process.stdout.write('\n');
        // Repaint with syntax-highlighted fenced code blocks if any were detected.
        const rendered = renderAssistant(assistant, r);
        if (rendered !== assistant) {
          process.stdout.write(rendered + '\n');
        }
        r.text(r.color.dim('—'));
      } else {
        r.json({ role: 'assistant', content: assistant });
      }
    } catch (err) {
      exitWithError(err);
    }

    messages.push({ role: 'assistant', content: assistant });
  }
}

async function pickModel(api: ApiClient, fallback: string, r: Renderer): Promise<string> {
  const spinner = r.spinner('Loading models...').start();
  let models: Model[] = [];
  try {
    models = await api.listModels('text');
    spinner.stop();
  } catch {
    spinner.warn('Could not load models — falling back to default.');
    return fallback;
  }
  if (models.length === 0) return fallback;

  const choices = models.map((m) => ({
    name: `${m.id} ${r.color.dim(`[${m.provider}]`)}`,
    value: m.id,
  }));
  const fallbackOk = models.some((m) => m.id === fallback);
  const defaultValue = fallbackOk ? fallback : (choices[0]?.value ?? fallback);
  return select({
    message: 'Pick a model:',
    choices,
    default: defaultValue,
  });
}

async function handleSlash(
  line: string,
  messages: ChatMessage[],
  r: Renderer,
): Promise<'exit' | 'continue'> {
  const [cmd, ...rest] = line.split(/\s+/);
  switch (cmd) {
    case '/exit':
    case '/quit':
      return 'exit';
    case '/clear':
      messages.length = 0;
      r.text(r.color.dim('Conversation cleared.'));
      return 'continue';
    case '/save': {
      const path = rest.join(' ').trim();
      if (path.length === 0) {
        throw new ValidationError('Usage: /save <path>');
      }
      await writeFile(path, JSON.stringify({ messages }, null, 2));
      r.text(r.color.success(`Saved ${messages.length} message(s) to ${path}.`));
      return 'continue';
    }
    default:
      r.text(r.color.warn(`Unknown command: ${cmd ?? ''}`));
      return 'continue';
  }
}

// Highlight fenced code blocks. Returns the original string if there are no fences.
export function renderAssistant(text: string, r: Renderer): string {
  if (!r.color.enabled) return text;
  const fence = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let out = '';
  let match: RegExpExecArray | null;
  let changed = false;
  while ((match = fence.exec(text)) !== null) {
    out += text.slice(lastIndex, match.index);
    const lang = match[1] ?? '';
    const code = match[2] ?? '';
    try {
      const opts = lang.length > 0 && supportsLanguage(lang) ? { language: lang } : {};
      out += '```' + lang + '\n' + highlight(code, opts) + '```';
      changed = true;
    } catch {
      out += match[0];
    }
    lastIndex = fence.lastIndex;
  }
  out += text.slice(lastIndex);
  return changed ? out : text;
}
