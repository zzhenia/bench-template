import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Trim } from '../types'

// The plugin lives at <bench>/actions/recurring/context-trim; sessions inside
// that bench get the band, and its auto-note writes the note.
const SELF = '/actions/recurring/context-trim'
const PYTHON = '/usr/bin/python3'

type Config = {
  threshold_tokens: number
  snooze_tokens: number
  max_attempts: number
  retry_seconds: number
}

const DEFAULTS: Config = { threshold_tokens: 100000, snooze_tokens: 25000, max_attempts: 3, retry_seconds: 30 }
const IDLE: Trim = { phase: 'idle', tokens: 0, limit: DEFAULTS.threshold_tokens, attempt: 0 }

const trim = atom({ plugin: 'context-trim', key: 'trim' } as const, IDLE)

const k = (n: number) => `${Math.round(n / 1000)}K`

let cfg = DEFAULTS

function benchRoot($: EngineInterface) {
  const root = $.plugin.root.replace(/\/+$/, '')
  return root.endsWith(SELF) ? root.slice(0, -SELF.length) : root
}

const autoNote = ($: EngineInterface) => `${benchRoot($)}/actions/recurring/auto-note`

// The note is written by auto-note (same writer as the idle sweep); success is
// its state.json recording a new note for this session.
async function noted($: EngineInterface, sid: string) {
  try {
    const state = JSON.parse(await $.fs.read(`${autoNote($)}/state.json`))
    return state.noted?.[sid] as { topic?: string; file?: string; at?: string } | undefined
  } catch {
    return undefined
  }
}

async function restart($: EngineInterface, topic?: string, file?: string) {
  await update($, trim, (): Trim => ({ ...IDLE, limit: cfg.threshold_tokens }))
  await $.command.run({ command: 'clear' })
  const text = topic
    ? `>>${topic} Context trimmed; continue from ${file ?? "today's note"}.`
    : 'Context trimmed. Read the latest session note and continue.'
  await $.prompt.submit({ text, asUser: true })
}

async function writeNote($: EngineInterface) {
  const sid = await $.session.id()
  const before = (await noted($, sid))?.at

  for (let attempt = 1; attempt <= cfg.max_attempts; attempt++) {
    await update($, trim, (t): Trim => ({ ...t, phase: 'working', attempt }))
    try {
      await $.process.run([PYTHON, `${autoNote($)}/auto_note.py`, '--force', sid], {
        cwd: autoNote($),
        timeoutMs: 300000,
      })
    } catch {
      // Counted as a failed attempt below.
    }
    const after = await noted($, sid)
    if (after?.at && after.at !== before) {
      await restart($, after.topic, after.file)
      return
    }
    if (attempt < cfg.max_attempts) await $.clock.sleep(cfg.retry_seconds * 1000)
  }
  // One message after the last attempt, never one per retry.
  await update($, trim, (t): Trim => ({ ...t, phase: 'failed' }))
}

// A restart clears the conversation, which kills this session's background
// shells and subagents. "When idle" waits for the main turn to end with none
// of them left running.
let turnActive = false
const shells = new Set<string>()
const BUSY = ['pending', 'running', 'waiting']

async function idle($: EngineInterface) {
  if (turnActive || shells.size) return false
  return !(await $.agent.list()).some(a => BUSY.includes(a.status))
}

async function busyLabel($: EngineInterface) {
  const agents = (await $.agent.list()).filter(a => BUSY.includes(a.status)).length
  const parts = [
    turnActive ? 'this turn' : '',
    shells.size ? `${shells.size} background command${shells.size > 1 ? 's' : ''}` : '',
    agents ? `${agents} agent${agents > 1 ? 's' : ''}` : '',
  ].filter(Boolean)
  return parts.join(', ') || 'the next turn'
}

async function whenIdle($: EngineInterface) {
  if (await idle($)) return writeNote($)
  await update($, trim, (t): Trim => ({ ...t, phase: 'queued' }))
}

function snooze($: EngineInterface) {
  return update($, trim, (t): Trim => ({ ...IDLE, tokens: t.tokens, limit: t.tokens + cfg.snooze_tokens }))
}

export const register: Register = on => {
  let isBench = false

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    const bench = benchRoot($)
    const cwd = await $.session.cwd()
    isBench = cwd === bench || cwd.startsWith(`${bench}/`)
    try {
      cfg = { ...DEFAULTS, ...JSON.parse(await $.fs.read(`${$.plugin.root}/config.json`)) }
    } catch {
      cfg = DEFAULTS
    }
    await update($, trim, (t): Trim => (t.phase === 'idle' ? { ...t, limit: cfg.threshold_tokens } : t))
    return result
  })

  on('turn.start', ($, e, next) => {
    if (e.agentId === undefined) turnActive = true
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const r = await next(e)
    const out = (r as { result?: { backgroundTaskId?: string; task_id?: string } }).result
    if (e.tool === 'Bash' && out?.backgroundTaskId) shells.add(out.backgroundTaskId)
    if (e.tool === 'TaskStop' && out?.task_id) shells.delete(out.task_id)
    return r
  })

  // A background command's end arrives as a task notification naming its id.
  on('prompt.submit', ($, e, next) => {
    for (const m of e.text.matchAll(/<task-id>([^<]+)<\/task-id>/g)) shells.delete(m[1])
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId === undefined) turnActive = false
    if (!isBench || e.agentId !== undefined) return result

    const { context } = await $.session.usage()
    const tokens = context.tokens ?? 0
    await update($, trim, (t): Trim => {
      if (t.phase !== 'idle') return { ...t, tokens }
      return tokens >= t.limit ? { ...t, phase: 'warn', tokens } : t
    })
    if ((await read($, trim)).phase === 'queued' && (await idle($))) void writeNote($)
    return result
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const t = await read($, trim)
    if (e.props.hasSurvey || t.phase === 'idle') return next(e)

    const { Box, Button, Text } = $.ui.resolve(e)

    if (t.phase === 'working') {
      return (
        <Box>
          <Text dimColor>
            Writing the session note before restarting{t.attempt > 1 ? ` (try ${t.attempt} of ${cfg.max_attempts})` : ''}…
          </Text>
        </Box>
      )
    }

    if (t.phase === 'queued') {
      const label = await busyLabel($)
      return (
        <Box flexDirection="column">
          <Text color="yellow">Restart queued: waiting for {label} to finish ({k(t.tokens)}).</Text>
          <Box gap={3}>
            <Button key="restart" hotkey="1" plain onPress={() => void writeNote($)}>Restart now</Button>
            <Button key="later" hotkey="2" plain onPress={() => snooze($)}>Cancel (ask again at {k(t.tokens + cfg.snooze_tokens)})</Button>
          </Box>
        </Box>
      )
    }

    if (t.phase === 'failed') {
      return (
        <Box flexDirection="column">
          <Text color="red">
            Session note failed {cfg.max_attempts} times (log: actions/recurring/auto-note/auto-note.log).
          </Text>
          <Box gap={3}>
            <Button key="restart" hotkey="1" plain onPress={() => restart($)}>Restart without a note</Button>
            <Button key="later" hotkey="2" plain onPress={() => snooze($)}>Keep going</Button>
          </Box>
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        <Text color="yellow">
          This conversation reached its token limit ({k(t.tokens)} of {k(t.limit)}).
        </Text>
        <Box gap={3}>
          <Button key="restart" hotkey="1" plain onPress={() => void writeNote($)}>Write note and restart</Button>
          <Button key="later" hotkey="2" plain onPress={() => snooze($)}>Not now (ask again at {k(t.tokens + cfg.snooze_tokens)})</Button>
          <Button key="idle" hotkey="3" plain onPress={() => void whenIdle($)}>Restart when idle</Button>
        </Box>
      </Box>
    )
  })
}
