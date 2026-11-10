import type { PluginAPI } from '@ampcode/plugin'
import { deepStrictEqual, ok as assert } from 'node:assert/strict'
import plugin from '../.amp/plugins/repository-hooks'

type Result = { exitCode: number; stdout: string; stderr: string }
type MockContext = {
	$: (strings: TemplateStringsArray, ...values: unknown[]) => Promise<Result>
}
type Handler = (
	event: { status: string; thread: { id: string } },
	ctx: MockContext,
) => Promise<unknown>
type Invocation = { strings: readonly string[]; values: readonly unknown[] }

const handlers = new Map<string, Handler>()
const amp = {
	on(name: string, handler: Handler) {
		handlers.set(name, handler)
	},
}
// The host fake only captures registered handlers; it does not claim to
// implement the rest of the Amp plugin API.
plugin(amp as Pick<PluginAPI, 'on'>)

function context(results: Result[]): {
	ctx: MockContext
	calls: Invocation[]
} {
	const calls: Invocation[] = []
	const ctx: MockContext = {
		$: async (strings, ...values) => {
			calls.push({ strings: [...strings], values })
			const result = results.shift()
			if (!result) throw new Error('unexpected command')
			return result
		},
	}
	return { ctx, calls }
}
const ok = (stdout = ''): Result => ({ exitCode: 0, stdout, stderr: '' })
const bad = (stderr = 'failed'): Result => ({ exitCode: 2, stdout: '', stderr })
const agentEnd = (status: string, ctx: MockContext): Promise<unknown> => {
	const handler = handlers.get('agent.end')
	if (!handler) throw new Error('missing agent.end')
	return handler({ status, thread: { id: 't' } }, ctx)
}

deepStrictEqual([...handlers.keys()], ['agent.end'])

const success = context([ok('/repo with spaces\n'), ok()])
assert(
	(await agentEnd('done', success.ctx)) === undefined,
	'successful validation continued',
)
assert(
	success.calls[1]?.strings
		.join('')
		.endsWith('/scripts/agent-stop-checks.sh amp'),
	'turn end did not run the shared stop gate as the amp harness',
)
deepStrictEqual(
	success.calls[1]?.values,
	['/repo with spaces'],
	'repository root was not passed as one interpolation',
)

const failure = context([ok('/repo\n'), bad('lint failed')])
deepStrictEqual(await agentEnd('done', failure.ctx), {
	action: 'continue',
	userMessage:
		'Repository stop checks failed (exit 2). Fix the failure before finishing.\n\nlint failed',
})

for (const status of ['cancelled', 'error']) {
	const skipped = context([])
	assert(
		(await agentEnd(status, skipped.ctx)) === undefined,
		`${status} looped`,
	)
	assert(skipped.calls.length === 0, `${status} ran commands`)
}

const noRoot = context([bad('not a worktree')])
deepStrictEqual(await agentEnd('done', noRoot.ctx), {
	action: 'continue',
	userMessage:
		'Repository stop checks could not determine the project root. Restore the Git worktree before finishing.',
})

console.log('repository hook tests passed')
