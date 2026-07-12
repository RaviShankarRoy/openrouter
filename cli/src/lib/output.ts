// Output strategies (Strategy pattern). Each Renderer turns domain objects into
// either a human-friendly table+chalk view or a single JSON document.
//
// All output goes to stdout. Spinners and progress live on stderr so that
// `--json` pipes stay parseable without setup.
import chalk, { type ChalkInstance } from 'chalk';
import CliTable from 'cli-table3';
import ora, { type Ora } from 'ora';

export type RendererKind = 'table' | 'json';

export interface Renderer {
  readonly kind: RendererKind;
  table(headers: readonly string[], rows: ReadonlyArray<ReadonlyArray<string>>): void;
  json(value: unknown): void;
  text(line: string): void;
  spinner(text: string): Spinner;
  color: Colors;
}

export interface Spinner {
  start(): Spinner;
  succeed(text?: string): void;
  fail(text?: string): void;
  warn(text?: string): void;
  info(text?: string): void;
  stop(): void;
  setText(text: string): void;
}

export interface Colors {
  enabled: boolean;
  primary: (s: string) => string;
  success: (s: string) => string;
  warn: (s: string) => string;
  error: (s: string) => string;
  dim: (s: string) => string;
  bold: (s: string) => string;
}

function colorsFor(enabled: boolean): Colors {
  if (!enabled) {
    const id = (s: string): string => s;
    return { enabled: false, primary: id, success: id, warn: id, error: id, dim: id, bold: id };
  }
  const c: ChalkInstance = chalk;
  return {
    enabled: true,
    primary: (s) => c.cyan(s),
    success: (s) => c.green(s),
    warn: (s) => c.yellow(s),
    error: (s) => c.red(s),
    dim: (s) => c.dim(s),
    bold: (s) => c.bold(s),
  };
}

class NullSpinner implements Spinner {
  start(): Spinner { return this; }
  succeed(_text?: string): void { /* no-op */ }
  fail(_text?: string): void { /* no-op */ }
  warn(_text?: string): void { /* no-op */ }
  info(_text?: string): void { /* no-op */ }
  stop(): void { /* no-op */ }
  setText(_text: string): void { /* no-op */ }
}

class OraSpinner implements Spinner {
  private readonly inner: Ora;
  constructor(text: string) {
    this.inner = ora({ text, stream: process.stderr });
  }
  start(): Spinner {
    this.inner.start();
    return this;
  }
  succeed(text?: string): void {
    if (text !== undefined) this.inner.succeed(text);
    else this.inner.succeed();
  }
  fail(text?: string): void {
    if (text !== undefined) this.inner.fail(text);
    else this.inner.fail();
  }
  warn(text?: string): void {
    if (text !== undefined) this.inner.warn(text);
    else this.inner.warn();
  }
  info(text?: string): void {
    if (text !== undefined) this.inner.info(text);
    else this.inner.info();
  }
  stop(): void { this.inner.stop(); }
  setText(text: string): void { this.inner.text = text; }
}

class TableRenderer implements Renderer {
  readonly kind = 'table' as const;
  readonly color: Colors;
  private readonly canAnimate: boolean;

  constructor(color: boolean) {
    this.color = colorsFor(color);
    this.canAnimate = process.stderr.isTTY === true;
  }

  table(headers: readonly string[], rows: ReadonlyArray<ReadonlyArray<string>>): void {
    const t = new CliTable({
      head: headers.map((h) => this.color.bold(h)),
      style: { head: [], border: [] },
    });
    for (const row of rows) t.push([...row]);
    process.stdout.write(t.toString() + '\n');
  }

  json(value: unknown): void {
    process.stdout.write(JSON.stringify(value, null, 2) + '\n');
  }

  text(line: string): void {
    process.stdout.write(line + '\n');
  }

  spinner(text: string): Spinner {
    return this.canAnimate ? new OraSpinner(text) : new NullSpinner();
  }
}

class JsonRenderer implements Renderer {
  readonly kind = 'json' as const;
  readonly color: Colors = colorsFor(false);

  table(headers: readonly string[], rows: ReadonlyArray<ReadonlyArray<string>>): void {
    const out = rows.map((r) => Object.fromEntries(headers.map((h, i) => [h, r[i] ?? ''])));
    this.json(out);
  }
  json(value: unknown): void {
    process.stdout.write(JSON.stringify(value) + '\n');
  }
  text(_line: string): void { /* JSON mode intentionally swallows free text */ }
  spinner(_text: string): Spinner { return new NullSpinner(); }
}

export interface PickRendererOpts {
  json?: boolean;
  color?: boolean;
}

export function pickRenderer(opts: PickRendererOpts): Renderer {
  if (opts.json === true) return new JsonRenderer();
  // commander sets opts.color = false when --no-color or NO_COLOR is set.
  // chalk also reads NO_COLOR itself, so we just align the explicit flag.
  const color =
    opts.color !== false &&
    (process.env['NO_COLOR'] === undefined || process.env['NO_COLOR'] === '');
  return new TableRenderer(color);
}
