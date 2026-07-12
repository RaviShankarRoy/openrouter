// pino with pino-pretty when stderr is a TTY; suppressed (silent) otherwise so
// pipelines stay clean. Set OPENROUTER_LOG=debug to elevate level.
import { pino, type Logger } from 'pino';

const level = process.env['OPENROUTER_LOG'] ?? (process.env['DEBUG'] ? 'debug' : 'info');
const isTty = process.stderr.isTTY === true;

function build(): Logger {
  if (!isTty) {
    return pino({ level: 'silent' });
  }
  return pino({
    level,
    transport: {
      target: 'pino-pretty',
      options: {
        destination: 2,
        colorize: process.env['NO_COLOR'] === undefined || process.env['NO_COLOR'] === '',
        translateTime: 'SYS:HH:MM:ss.l',
        ignore: 'pid,hostname',
      },
    },
  });
}

export const logger: Logger = build();
