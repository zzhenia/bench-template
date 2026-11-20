import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Trim } from '../types'

// The plugin lives at <bench>/core/tools/context-trim. Sessions inside that
// bench (or in `bench_dirs`, benches whose notes this bench's auto-note writes)
// get the band, and the bench's auto-note writes the note.
const SELF = '/core/tools/context-trim'

type Config = {
  threshold_tokens: number
  snooze_tokens: number
  max_attempts: number
  retry_seconds: number
  python: string
  bench_dirs: string[]
}

const DEFAULTS: Config = {
  threshold_tokens: 100000, snooze_tokens: 25000, max_attempts: 3, retry_seconds: 30,
  python: '/usr/bin/python3', bench_dirs: [],
}

let ROOT = ''
const benchRoot = ($: EngineInterface) => {
  const root = $.plugin.root.replace(/\/+$/, '')
  return root.endsWith(SELF) ? root.slice(0, -SELF.length) : root
}
const autoNote = () => `${ROOT}/core/tools/auto-note`
const inside = (cwd: string, dir: string) => cwd === dir || cwd.startsWith(`${dir.replace(/\/+$/, '')}/`)
const IDLE: Trim = { phase: 'idle', tokens: 0, limit: DEFAULTS.threshold_tokens, attempt: 0 }

const trim = atom({ plugin: 'context-trim', key: 'trim' } as const, IDLE)

const k = (n: number) => `${Math.round(n / 1000)}K`

let cfg = DEFAULTS

// Messages typed while a restart is armed, running or failed, carried into the
// new conversation. Anything sent to the old one would be wiped by the clear.
let held: string | undefined
const hold = (text: string) => { held = held ? `${held}\n\n${text}` : text }

// The note is written by auto-note (same writer as the idle sweep); success is
// its state.json recording a new note for this session.
async function noted($: EngineInterface, sid: string) {
  try {
    const state = JSON.parse(await $.fs.read(`${ROOT}/state/auto-note/state.json`))
    return state.noted?.[sid] as { topic?: string; file?: string; at?: string } | undefined
  } catch {
    return undefined
  }
}

async function restart($: EngineInterface, topic?: string, file?: string) {
  // Clear before going idle, so a message typed during the clear is still held.
  await $.command.run({ command: 'clear' })
  await update($, trim, (): Trim => ({ ...IDLE, limit: cfg.threshold_tokens }))
  const resume = topic
    ? `>>${topic} Context trimmed; continue from ${file ?? "today's note"}. Read it silently; do not list its open items back.`
    : 'Context trimmed. Read the latest session note silently and continue; do not list its open items back.'
  const text = held ? `${resume}\n\n${held}` : resume
  held = undefined
  await $.prompt.submit({ text, asUser: true })
}

async function writeNote($: EngineInterface) {
  // Working from the keypress on, so the next typed message is held.
  await update($, trim, (t): Trim => ({ ...t, phase: 'working', attempt: 1 }))
  const sid = await $.session.id()
  const before = (await noted($, sid))?.at

  for (let attempt = 1; attempt <= cfg.max_attempts; attempt++) {
    await update($, trim, (t): Trim => ({ ...t, phase: 'working', attempt }))
    try {
      await $.process.run([cfg.python, `${autoNote()}/auto_note.py`, '--force', sid], {
        cwd: ROOT,
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
// shells and subagents, and wipes the answer on screen. So "on next message"
// first waits for the main turn to end with none of them left running, then
// arms: the restart fires only when the user sends the next message.
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
  const phase = (await idle($)) ? 'armed' : 'queued'
  await update($, trim, (t): Trim => ({ ...t, phase }))
}

async function snooze($: EngineInterface) {
  await update($, trim, (t): Trim => ({ ...IDLE, tokens: t.tokens, limit: t.tokens + cfg.snooze_tokens }))
  const text = held
  held = undefined
  if (text) await $.prompt.submit({ text, asUser: true })
}

export const register: Register = on => {
  let isBench = false

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    ROOT = benchRoot($)
    const load = async (path: string) => {
      try { return JSON.parse(await $.fs.read(path)) as Partial<Config> } catch { return {} }
    }
    // Plugin defaults, then this bench's own config/context-trim.json.
    cfg = { ...DEFAULTS, ...(await load(`${$.plugin.root}/config.json`)), ...(await load(`${ROOT}/config/context-trim.json`)) }
    const cwd = await $.session.cwd()
    isBench = [ROOT, ...cfg.bench_dirs].some(d => inside(cwd, d))
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
  on('prompt.submit', async ($, e, next) => {
    for (const m of e.text.matchAll(/<task-id>([^<]+)<\/task-id>/g)) shells.delete(m[1])
    // Commands and images can't be carried across the clear, so they pass.
    const typed = e.origin.kind === 'composer' && !e.command && !e.isMeta && !e.attachments?.length
    const phase = typed ? (await read($, trim)).phase : 'idle'
    if (phase === 'armed') {
      hold(e.text)
      void writeNote($)
      return { drop: 'Restarting first; your message carries over.' }
    }
    if (phase === 'working' || phase === 'failed') {
      hold(e.text)
      return { drop: 'Held; sent after the restart.' }
    }
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
    if ((await read($, trim)).phase === 'queued' && (await idle($))) {
      await update($, trim, (t): Trim => ({ ...t, phase: 'armed' }))
    }
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
            Writing the session note before restarting{t.attempt > 1 ? ` (try ${t.attempt} of ${cfg.max_attempts})` : ''}… Messages you type now carry over.
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

    if (t.phase === 'armed') {
      return (
        <Box flexDirection="column">
          <Text color="yellow">Restart armed: runs on your next message, which carries over ({k(t.tokens)}).</Text>
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
            Session note failed {cfg.max_attempts} times (log: state/auto-note/auto-note.log).
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
          <Button key="idle" hotkey="3" plain onPress={() => void whenIdle($)}>Restart on next message</Button>
        </Box>
      </Box>
    )
  })
}
