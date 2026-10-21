export type Trim = {
  phase: 'idle' | 'warn' | 'working' | 'failed'
  tokens: number
  limit: number
  attempt: number
}

declare module 'claude-code' {
  interface PluginState {
    'context-trim': {
      trim: Trim
    }
  }
}
