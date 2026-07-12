import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    reporters: process.env['CI'] ? ['default', 'junit'] : ['default'],
    outputFile: { junit: 'coverage/junit.xml' },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      include: ['src/**/*.ts'],
      exclude: ['src/cli.ts', 'src/**/index.ts'],
      thresholds: {
        lines: 70,
        functions: 70,
        statements: 70,
        branches: 60,
      },
    },
    globals: false,
    clearMocks: true,
    restoreMocks: true,
  },
});
