import type { PluginAPI } from '@ampcode/plugin'

export const description =
	'Runs this repository’s validation before an Amp turn finishes.'

// Amp has no stop hook. Returning `continue` from agent.end sends the agent
// back to work, which lets this adapter reuse the gate the other harnesses run.
// https://ampcode.com/docs/plugin-api
export default function (amp: Pick<PluginAPI, 'on'>): void {
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
			await ctx.$`bash ${repoRoot}/scripts/agent-stop-checks.sh amp`
		if (result.exitCode === 0) return

		const stderr = result.stderr.trim()
		const details = stderr.length > 0 ? stderr : result.stdout.trim()
		return {
			action: 'continue',
			userMessage: `Repository stop checks failed (exit ${result.exitCode}). Fix the failure before finishing.\n\n${details}`,
		}
	})
}
