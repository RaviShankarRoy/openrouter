// CLI-004 — `usage` shows totals + a per-day cost sparkline for the current billing period.
import type { Command } from 'commander';
import asciichart from 'asciichart';
import { ApiClient, type UsageResponse } from '../repository/api-client.js';
import { pickRenderer } from './output.js';
import { ValidationError, exitWithError } from '../shared/errors.js';
import type { GlobalOptions } from '../cli.js';

const VALID_PERIODS = ['day', 'week', 'month'] as const;
type Period = (typeof VALID_PERIODS)[number];

export interface UsageOptions extends GlobalOptions {
  period?: string;
}

export function registerUsage(program: Command): void {
  program
    .command('usage')
    .description('Display usage stats for the current billing period (CLI-004)')
    .option('--period <period>', `day|week|month (default: month)`, 'month')
    .action(async (opts: UsageOptions, cmd: Command) => {
      const globals = cmd.optsWithGlobals<UsageOptions>();
      try {
        await runUsage({ ...globals, ...opts });
      } catch (err) {
        exitWithError(err);
      }
    });
}

export async function runUsage(opts: UsageOptions, apiOverride?: ApiClient): Promise<void> {
  const r = pickRenderer({ json: opts.json, color: opts.color });
  const period = (opts.period ?? 'month') as Period;
  if (!VALID_PERIODS.includes(period)) {
    throw new ValidationError(`invalid --period: ${opts.period ?? ''}`);
  }

  const api = apiOverride ?? (await ApiClient.create({ ...(opts.baseUrl ? { baseUrl: opts.baseUrl } : {}) }));
  const spinner = r.spinner('Loading usage...').start();
  let usage: UsageResponse;
  try {
    usage = await api.getUsage(period);
  } catch (err) {
    spinner.fail('Failed to load usage.');
    throw err;
  }
  spinner.stop();

  if (opts.json === true) {
    r.json(usage);
    return;
  }

  r.text(r.color.bold(`Usage — ${usage.period} (${usage.start} → ${usage.end})`));
  r.text('');
  r.table(
    ['REQUESTS', 'PROMPT TOK', 'COMPLETION TOK', 'COST USD'],
    [[
      usage.totals.requests.toLocaleString(),
      usage.totals.prompt_tokens.toLocaleString(),
      usage.totals.completion_tokens.toLocaleString(),
      formatUsd(usage.totals.cost_usd),
    ]],
  );

  if (usage.series.length === 0) {
    r.text(r.color.dim('No daily breakdown available.'));
    return;
  }

  const series = usage.series.map((p) => p.cost_usd);
  const chart = asciichart.plot(series, { height: 8 });
  r.text('');
  r.text(r.color.bold('Daily cost (USD)'));
  r.text(chart);
  r.text(
    r.color.dim(
      `${usage.series[0]?.date ?? ''} ${' '.repeat(Math.max(0, chart.split('\n')[0]?.length ?? 0))} ${usage.series[usage.series.length - 1]?.date ?? ''}`,
    ),
  );
}

function formatUsd(n: number): string {
  return `$${n.toFixed(2)}`;
}
