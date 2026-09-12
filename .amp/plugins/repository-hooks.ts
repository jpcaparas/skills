import type { PluginAPI } from '@ampcode/plugin'

export const description =
	'Runs this repository’s existing session and stop checks for Amp turns.'

// Amp has no SessionEnd hook. Its supported turn-end continuation protocol lets
// this adapter reuse the same fail-closed checker as the other harnesses.
// https://ampcode.com/docs/plugin-api
export default function (amp: Pick<PluginAPI, 'on'>): void {
	amp.on('session.start', async (event, ctx) => {
		const root = await ctx.$`git rev-parse --show-toplevel`
		if (root.exitCode !== 0) return

		const repoRoot = root.stdout.trim()
		const result =
			await ctx.$`env AGENT_HOOK_HARNESS=amp AGENT_HOOK_PROJECT_ROOT=${repoRoot} AGENT_HOOK_SESSION_ID=${event.thread.id} bash ${repoRoot}/scripts/agent-session-context.sh`
		if (result.exitCode !== 0) {
			ctx.logger.log('Amp session baseline failed', result.stderr)
		}
	})

	amp.on('agent.end', async (event, ctx) => {
		if (event.status !== 'done') return

		const root = await ctx.$`git rev-parse --show-toplevel`
		if (root.exitCode !== 0) {
			return {
				action: 'continue',
				userMessage:
					'Repository stop checks could not determine the project root. Restore the Git worktree before finishing.',
			}
		}

		const repoRoot = root.stdout.trim()
		const result =
			await ctx.$`env AGENT_HOOK_HARNESS=amp AGENT_HOOK_PROJECT_ROOT=${repoRoot} AGENT_HOOK_SESSION_ID=${event.thread.id} bash ${repoRoot}/scripts/agent-stop-checks.sh ${repoRoot}`
		if (result.exitCode === 0) return

		const stderr = result.stderr.trim()
		const details = stderr.length > 0 ? stderr : result.stdout.trim()
		return {
			action: 'continue',
			userMessage: `Repository stop checks failed (exit ${result.exitCode}). Fix the failure before finishing.\n\n${details}`,
		}
	})
}
