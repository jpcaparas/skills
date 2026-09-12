import type { PluginAPI } from '@ampcode/plugin'
import { deepStrictEqual, ok as assert } from 'node:assert/strict'
import plugin from '../.amp/plugins/repository-hooks'

type Result = { exitCode: number; stdout: string; stderr: string }
type Handler = (
	event: { status: string; thread: { id: string } },
	ctx: MockContext,
) => Promise<unknown>
type Invocation = { strings: readonly string[]; values: readonly unknown[] }
type MockContext = {
	$: (strings: TemplateStringsArray, ...values: unknown[]) => Promise<Result>
	logger: { log: (...values: unknown[]) => void }
}

const handlers = new Map<string, Handler>()
const amp = {
	on(name: string, handler: Handler) {
		handlers.set(name, handler)
	},
}
// The runtime host fake captures the two registered handlers; it does not claim
// to implement unrelated Amp APIs. Assertions below exercise both callbacks.
plugin(amp as Pick<PluginAPI, 'on'>)

function context(results: Result[]): {
	ctx: MockContext
	calls: Invocation[]
	logs: unknown[][]
} {
	const calls: Invocation[] = []
	const logs: unknown[][] = []
	const ctx: MockContext = {
		$: async (strings, ...values) => {
			calls.push({ strings: [...strings], values })
			const result = results.shift()
			if (!result) throw new Error('unexpected command')
			return result
		},
		logger: { log: (...values) => logs.push(values) },
	}
	return { ctx, calls, logs }
}
const ok = (stdout = ''): Result => ({ exitCode: 0, stdout, stderr: '' })
const bad = (stderr = 'failed'): Result => ({ exitCode: 2, stdout: '', stderr })
const requireHandler = (name: string): Handler => {
	const handler = handlers.get(name)
	if (!handler) throw new Error(`missing ${name}`)
	return handler
}

const start = context([ok('/repo with spaces\n'), ok()])
await requireHandler('session.start')(
	{ status: 'done', thread: { id: 'thread 7' } },
	start.ctx,
)
assert(
	start.calls[1]?.strings
		.join('')
		.includes('/scripts/agent-session-context.sh'),
	'baseline did not call the shared session script',
)
assert(
	start.calls[1]?.values[0] === '/repo with spaces',
	'baseline root was not passed as one interpolation',
)
assert(
	start.calls[1]?.values[1] === 'thread 7',
	'baseline thread was not passed',
)
assert(
	start.calls[1]?.values[2] === '/repo with spaces',
	'baseline script path was not safely interpolated',
)

const success = context([ok('/repo with spaces\n'), ok()])
assert(
	(await requireHandler('agent.end')(
		{ status: 'done', thread: { id: 't' } },
		success.ctx,
	)) === undefined,
	'successful validation continued',
)
assert(
	success.calls[1]?.strings.join('').includes('/scripts/agent-stop-checks.sh'),
	'turn end bypassed the shared stop checker',
)
assert(
	success.calls[1]?.values.at(-1) === '/repo with spaces',
	'validation argument was not safely interpolated',
)

const failure = context([ok('/repo\n'), bad('lint failed')])
const correction = await requireHandler('agent.end')(
	{ status: 'done', thread: { id: 't' } },
	failure.ctx,
)
deepStrictEqual(correction, {
	action: 'continue',
	userMessage:
		'Repository stop checks failed (exit 2). Fix the failure before finishing.\n\nlint failed',
})

for (const status of ['cancelled', 'error']) {
	const skipped = context([])
	assert(
		(await requireHandler('agent.end')(
			{ status, thread: { id: 't' } },
			skipped.ctx,
		)) === undefined,
		`${status} looped`,
	)
	assert(skipped.calls.length === 0, `${status} ran commands`)
}

const noRoot = context([bad('not a worktree')])
const rootCorrection = await requireHandler('agent.end')(
	{ status: 'done', thread: { id: 't' } },
	noRoot.ctx,
)
deepStrictEqual(rootCorrection, {
	action: 'continue',
	userMessage:
		'Repository stop checks could not determine the project root. Restore the Git worktree before finishing.',
})

console.log('repository hook tests passed')
