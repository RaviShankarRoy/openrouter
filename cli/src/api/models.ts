// CLI-002 — `models list` with optional modality filter, table or JSON output.
import type { Command } from 'commander';
import { ApiClient, type Model } from '../repository/api-client.js';
import { pickRenderer } from './output.js';
import { ValidationError, exitWithError } from '../shared/errors.js';
import type { GlobalOptions } from '../cli.js';

const VALID_MODALITIES = ['text', 'image', 'video', 'audio'] as const;
type Modality = (typeof VALID_MODALITIES)[number];

export interface ModelsListOptions extends GlobalOptions {
  modality?: string;
}

export function registerModels(program: Command): void {
  const cmd = program
    .command('models')
    .description('Browse the model catalog (CLI-002)');

  cmd
    .command('list')
    .description('List models with pricing')
    .option('--modality <modality>', `filter by modality: ${VALID_MODALITIES.join('|')}`)
    .action(async (opts: ModelsListOptions, sub: Command) => {
      const globals = sub.optsWithGlobals<ModelsListOptions>();
      try {
        await runModelsList({ ...globals, ...opts });
      } catch (err) {
        exitWithError(err);
      }
    });
}

export async function runModelsList(
  opts: ModelsListOptions,
  apiOverride?: ApiClient,
): Promise<void> {
  const r = pickRenderer({ json: opts.json, color: opts.color });
  if (opts.modality !== undefined && !VALID_MODALITIES.includes(opts.modality as Modality)) {
    throw new ValidationError(`invalid modality: ${opts.modality}`);
  }

  const api = apiOverride ?? (await ApiClient.create({ ...(opts.baseUrl ? { baseUrl: opts.baseUrl } : {}) }));
  const spinner = r.spinner('Fetching models...').start();
  let models: Model[];
  try {
    models = await api.listModels(opts.modality);
  } catch (err) {
    spinner.fail('Failed to fetch models.');
    throw err;
  }
  spinner.stop();

  if (opts.json === true) {
    r.json(models);
    return;
  }

  const headers = ['ID', 'PROVIDER', 'MODALITIES', 'CTX', 'IN $/M', 'OUT $/M'];
  const rows = models.map((m): readonly string[] => [
    m.id,
    m.provider,
    m.modalities.join(','),
    m.context_window?.toLocaleString() ?? '-',
    formatPrice(m.pricing.input_per_million),
    formatPrice(m.pricing.output_per_million),
  ]);
  r.table(headers, rows);
  r.text(r.color.dim(`${models.length} model(s).`));
}

function formatPrice(p: number | undefined): string {
  if (p === undefined) return '-';
  return p.toFixed(2);
}
