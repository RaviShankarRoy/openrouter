import { defineConfig } from 'tsup';

// Bundles ESM CLI to dist/cli.js with shebang. Native deps (keytar) stay external
// so npm/yarn pull the platform-specific prebuilt binaries on install.
export default defineConfig({
  entry: { cli: 'src/cli.ts' },
  format: ['esm'],
  target: 'node20',
  platform: 'node',
  outDir: 'dist',
  clean: true,
  dts: true,
  sourcemap: true,
  splitting: false,
  treeshake: true,
  minify: false,
  shims: false,
  banner: { js: '#!/usr/bin/env node' },
  external: [
    'keytar',
  ],
  esbuildOptions(options) {
    options.legalComments = 'inline';
    options.charset = 'utf8';
  },
  onSuccess: async () => {
    const { chmod } = await import('node:fs/promises');
    await chmod('dist/cli.js', 0o755);
  },
});
