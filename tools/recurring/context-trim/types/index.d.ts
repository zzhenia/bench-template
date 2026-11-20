export type Trim = {
  phase: 'idle' | 'warn' | 'queued' | 'working' | 'failed'
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
