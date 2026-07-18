# Oneshot Artifact Catalogue Curator

Index completed experiment runs without rewriting their artifacts.

1. Discover `run.json` and `worker-report.json` files under the model/harness/experiment/run namespace.
2. Confirm successful runs contain the exact-case `artifact/PROMPT.md` and a built exact-case root `artifact/index.html`.
3. Preserve partial, blocked, and failed runs with honest statuses.
4. Build the root `index.html` with links to each prompt and website.
5. Run `scripts/validate_catalog.py` and report provenance failures separately from artifact-quality observations.

A separately repaired or regenerated result is a new run, never an overwrite of the original.
