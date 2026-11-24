import { expect, test } from 'claude-code/testing'

const BAND = {
  plugin: 'context-trim',
  component: 'AbovePrompt',
  surface: 'terminal',
  props: { hasSurvey: false },
} as const

// The bench this plugin sits in (<bench>/core/tools/context-trim/tests)
const CWD = new URL('../../../..', import.meta.url).pathname.replace(/\/$/, '')

function engine(on: any, tokens: { n: number }, state: { json: string }, calls: string[], gate?: Promise<void>, cwd = CWD) {
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  on('session.cwd', () => ({ value: cwd }))
  on('session.id', () => ({ value: 'sid-1' }))
  on('session.usage', () => ({ value: { startedAt: 0, context: { tokens: tokens.n, window: 200000 }, rateLimits: [] } }))
  on('fs.read', (_: any, e: any) => {
    if (String(e.path).endsWith('state.json')) return { value: state.json }
    return { value: '{"threshold_tokens": 100000}' }
  })
  on('process.run', async () => {
    await gate
    calls.push('note')
    state.json = JSON.stringify({ noted: { 'sid-1': { topic: 'the-bench', file: 'convos/the-bench/261020-x.md', at: 'later' } } })
    return { value: { exitCode: 0, stdout: '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('command.run', (_: any, e: any) => (calls.push(`/${e.command}`), { text: '' }))
  on('prompt.submit', (_: any, e: any) => (calls.push(e.text), { text: e.text }))
  on('turn.complete', () => ({ text: '' }))
  on('ui.render', ($: any, e: any) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
}

test('quiet under the limit, warns past it, 2 snoozes', async ($, on) => {
  const tokens = { n: 50000 }
  engine(on, tokens, { json: '{"noted":{}}' }, [])
  await $.session.start({ cwd: CWD, surface: 'terminal', isInteractive: true })

  await $.turn.complete({ turnId: 't1', answer: '' } as any)
  let ui = await $.ui.mount(BAND as any)
  expect(await ui.find({ type: 'Text', text: /token limit/ })).toBe(undefined)
  await ui.unmount()

  tokens.n = 112000
  await $.turn.complete({ turnId: 't2', answer: '' } as any)
  ui = await $.ui.mount(BAND as any)
  expect((await ui.find({ type: 'Text', text: /token limit/ }))?.text).toBe(
    'This conversation reached its token limit (112K of 100K).')
  await ui.press({ key: 'later' })
  expect(await ui.find({ type: 'Text', text: /token limit/ })).toBe(undefined)
  await ui.unmount()
})

test('1 writes the note, clears and resumes the topic', async ($, on) => {
  const calls: string[] = []
  engine(on, { n: 150000 }, { json: '{"noted":{}}' }, calls)
  await $.session.start({ cwd: CWD, surface: 'terminal', isInteractive: true })
  await $.turn.complete({ turnId: 't1', answer: '' } as any)

  const ui = await $.ui.mount(BAND as any)
  await ui.press({ key: 'restart' })
  expect(calls).toEqual(['note', '/clear',
    '>>the-bench Context trimmed; continue from convos/the-bench/261020-x.md. Read it silently; do not list its open items back.'])
  await ui.unmount()
})

test('a note that keeps failing retries quietly, then shows one message', async ($, on) => {
  let runs = 0
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  on('session.cwd', () => ({ value: CWD }))
  on('session.id', () => ({ value: 'sid-1' }))
  on('session.usage', () => ({ value: { startedAt: 0, context: { tokens: 150000, window: 200000 }, rateLimits: [] } }))
  on('fs.read', (_: any, e: any) => ({
    value: String(e.path).endsWith('state.json') ? '{"noted":{}}' : '{"retry_seconds": 0}',
  }))
  on('process.run', () => (runs++, { value: { exitCode: 1, stdout: '', stderr: 'boom', isStdoutTruncated: false, isStderrTruncated: false } }))
  on('clock.sleep', () => ({ value: undefined }))
  on('turn.complete', () => ({ text: '' }))
  on('ui.render', ($: any, e: any) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })

  await $.session.start({ cwd: CWD, surface: 'terminal', isInteractive: true })
  await $.turn.complete({ turnId: 't1', answer: '' } as any)
  const ui = await $.ui.mount(BAND as any)
  await ui.press({ key: 'restart' })
  expect(runs).toBe(3)
  expect((await ui.find({ type: 'Text', text: /failed/ }))?.text).toBe(
    'Session note failed 3 times (log: state/auto-note/auto-note.log).')
  await ui.unmount()
})

test('silent outside the bench', async ($, on) => {
  engine(on, { n: 150000 }, { json: '{"noted":{}}' }, [], undefined, '/tmp/elsewhere')
  await $.session.start({ cwd: '/tmp/elsewhere', surface: 'terminal', isInteractive: true })
  await $.turn.complete({ turnId: 't1', answer: '' } as any)
  const ui = await $.ui.mount(BAND as any)
  expect(await ui.find({ type: 'Text', text: /token limit/ })).toBe(undefined)
  await ui.unmount()
})

const typed = (text: string) => ({ text, origin: { kind: 'composer' }, wait: false }) as any

test('3 waits for background work, keeps the answer, restarts on the next message', async ($, on) => {
  const calls: string[] = []
  const agents = [{ id: 'a1', description: 'render', type: 'general-purpose', status: 'running' }]
  engine(on, { n: 150000 }, { json: '{"noted":{}}' }, calls)
  on('agent.list', () => ({ value: agents }))
  on('tool.call', () => ({ result: { backgroundTaskId: 'b1' } }))
  await $.session.start({ cwd: CWD, surface: 'terminal', isInteractive: true })
  await $.tool.call({ tool: 'Bash', input: { command: 'render', run_in_background: true } } as any)
  await $.turn.complete({ turnId: 't1', answer: '' } as any)

  const ui = await $.ui.mount(BAND as any)
  await ui.press({ key: 'idle' })
  expect((await ui.find({ type: 'Text', text: /queued/ }))?.text).toBe(
    'Restart queued: waiting for 1 background command, 1 agent to finish (150K).')
  expect(calls).toEqual([])

  agents[0].status = 'completed'
  await $.prompt.submit({ text: '<task-notification><task-id>b1</task-id></task-notification>', origin: { kind: 'plugin', name: 'x' } } as any)
  calls.length = 0
  await $.turn.complete({ turnId: 't2', answer: '' } as any)
  await new Promise(r => setTimeout(r, 10))
  expect(calls).toEqual([])
  expect((await ui.find({ type: 'Text', text: /armed/ }))?.text).toBe(
    'Restart armed: runs on your next message, which carries over (150K).')

  const r = await $.prompt.submit(typed('next question'))
  expect((r as any).drop).toBe('Restarting first; your message carries over.')
  for (let i = 0; i < 50 && calls.length < 3; i++) await new Promise(r => setTimeout(r, 1))
  expect(calls).toEqual(['note', '/clear',
    '>>the-bench Context trimmed; continue from convos/the-bench/261020-x.md. Read it silently; do not list its open items back.\n\nnext question'])
  await ui.unmount()
})

test('3 when already idle arms; a slash command passes without firing', async ($, on) => {
  const calls: string[] = []
  engine(on, { n: 150000 }, { json: '{"noted":{}}' }, calls)
  on('agent.list', () => ({ value: [] }))
  await $.session.start({ cwd: CWD, surface: 'terminal', isInteractive: true })
  await $.turn.complete({ turnId: 't1', answer: '' } as any)

  const ui = await $.ui.mount(BAND as any)
  await ui.press({ key: 'idle' })
  expect(calls).toEqual([])
  const r = await $.prompt.submit({ ...typed('/status'), command: { name: 'status' } })
  expect((r as any).drop).toBe(undefined)
  expect(calls).toEqual(['/status'])
  await ui.press({ key: 'later' })
  expect(await ui.find({ type: 'Text', text: /armed/ })).toBe(undefined)
  await ui.unmount()
})

test('messages typed while the note is written carry over after the clear', async ($, on) => {
  const calls: string[] = []
  let release!: () => void
  const gate = new Promise<void>(r => (release = r))
  const state = { json: '{"noted":{}}' }
  engine(on, { n: 150000 }, state, calls, gate)
  await $.session.start({ cwd: CWD, surface: 'terminal', isInteractive: true })
  await $.turn.complete({ turnId: 't1', answer: '' } as any)

  const ui = await $.ui.mount(BAND as any)
  void ui.press({ key: 'restart' })
  await new Promise(r => setTimeout(r, 5))
  const r1 = await $.prompt.submit(typed('first question'))
  const r2 = await $.prompt.submit(typed('second question'))
  expect((r1 as any).drop).toBe('Held; sent after the restart.')
  expect((r2 as any).drop).toBe('Held; sent after the restart.')
  expect(calls).toEqual([])

  release()
  for (let i = 0; i < 50 && calls.length < 3; i++) await new Promise(r => setTimeout(r, 1))
  expect(calls).toEqual(['note', '/clear',
    '>>the-bench Context trimmed; continue from convos/the-bench/261020-x.md. Read it silently; do not list its open items back.\n\nfirst question\n\nsecond question'])
  await ui.unmount()
})

// The test engine serves no image bytes ($.prompt.media is the engine's own
// read), so this checks the message is held and carried; saving is live-only.
test('a message with an image typed while the note is written carries over', async ($, on) => {
  const calls: string[] = []
  let release!: () => void
  const gate = new Promise<void>(r => (release = r))
  engine(on, { n: 150000 }, { json: '{"noted":{}}' }, calls, gate)
  await $.session.start({ cwd: CWD, surface: 'terminal', isInteractive: true })
  await $.turn.complete({ turnId: 't1', answer: '' } as any)

  const ui = await $.ui.mount(BAND as any)
  void ui.press({ key: 'restart' })
  await new Promise(r => setTimeout(r, 5))
  const r = await $.prompt.submit({ ...typed('[Image #6] grow the input'), attachments: [{ type: 'image', id: 'i6' }] })
  expect((r as any).drop).toBe('Held; sent after the restart.')
  expect(calls).toEqual([])

  release()
  for (let i = 0; i < 50 && calls.length < 3; i++) await new Promise(r => setTimeout(r, 1))
  expect(calls[2]).toMatch(/\n\n\[Image #6\] grow the input\n\[image could not be carried over; ask me to paste it again\]$/)
  await ui.unmount()
})
