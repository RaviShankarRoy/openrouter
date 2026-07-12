// Re-exports so callers (and tests) have a single import surface.
export { registerLogin, runLogin, type LoginOptions } from './login.js';
export { registerLogout, runLogout } from './logout.js';
export { registerModels, runModelsList, type ModelsListOptions } from './models.js';
export { registerChat, runChat, renderAssistant, type ChatOptions } from './chat.js';
export { registerUsage, runUsage, type UsageOptions } from './usage.js';
export {
  registerKeys,
  runKeysCreate,
  runKeysList,
  runKeysRevoke,
  type KeysCreateOptions,
  type KeysListOptions,
  type KeysRevokeOptions,
} from './keys.js';
