import { expect, test } from 'claude-code/testing'

const BAND = {
  plugin: 'context-trim',
  component: 'AbovePrompt',
  surface: 'terminal',
  props: { hasSurvey: false },
} as const

// The bench this plugin sits in (<bench>/actions/recurring/context-trim/tests)
const CWD = new URL('../../../..', import.meta.url).pathname.replace(/\/$/, '')

function engine(on: any, tokens: { n: number }, state: { json: string }, calls: string[], cwd = CWD) {
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  on('session.cwd', () => ({ value: cwd }))
  on('session.id', () => ({ value: 'sid-1' }))
  on('session.usage', () => ({ value: { startedAt: 0, context: { tokens: tokens.n, window: 200000 }, rateLimits: [] } }))
  on('fs.read', (_: any, e: any) => {
    if (String(e.path).endsWith('state.json')) return { value: state.json }
    return { value: '{"threshold_tokens": 100000}' }
  })
  on('process.run', () => {
    calls.push('note')
    state.json = JSON.stringify({ noted: { 'sid-1': { topic: 'general', file: 'convos/general/261020-x.md', at: 'later' } } })
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
    '>>general Context trimmed; continue from convos/general/261020-x.md.'])
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
    'Session note failed 3 times (log: actions/recurring/auto-note/auto-note.log).')
  await ui.unmount()
})

test('silent outside the bench', async ($, on) => {
  engine(on, { n: 150000 }, { json: '{"noted":{}}' }, [], '/tmp/elsewhere')
  await $.session.start({ cwd: '/tmp/elsewhere', surface: 'terminal', isInteractive: true })
  await $.turn.complete({ turnId: 't1', answer: '' } as any)
  const ui = await $.ui.mount(BAND as any)
  expect(await ui.find({ type: 'Text', text: /token limit/ })).toBe(undefined)
  await ui.unmount()
})

test('3 waits for background work, then writes the note and restarts', async ($, on) => {
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
  await $.prompt.submit({ text: '<task-notification><task-id>b1</task-id></task-notification>' } as any)
  calls.length = 0
  await $.turn.complete({ turnId: 't2', answer: '' } as any)
  for (let i = 0; i < 50 && calls.length < 3; i++) await new Promise(r => setTimeout(r, 1))
  expect(calls).toEqual(['note', '/clear',
    '>>general Context trimmed; continue from convos/general/261020-x.md.'])
  await ui.unmount()
})
