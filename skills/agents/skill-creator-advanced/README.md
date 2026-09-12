# Skill Creator Advanced

Repository-agnostic creator and curator for production-grade skills and skill libraries.

## What It Adds

- Progressive disclosure and blueprint-driven skill design
- Branch ownership, invocation design, lifecycle promotion, rename, and deprecation gates
- Draft-vs-release validation, behavioral eval design, and safe verification ladders
- Evidence-backed pruning for duplication, no-ops, sediment, and stale publication surfaces
- Cross-harness compatibility guidance
- Destination inference so new skills land in the right repo-local or global skills directory

## Key Files

- `SKILL.md` — authoritative instructions
- `references/placement.md` — destination selection heuristics
- `references/curation.md` — skill ownership, lifecycle, publication surfaces, and pruning
- `scripts/infer_destination.py` — placement recommendation helper
- `scripts/test_infer_destination.py` — isolated placement regression suite
- `scripts/scaffold.sh` — scaffold a new skill into the recommended root
- `scripts/validate.py` — structural validation
- `scripts/test_skill.py` — eval and cross-reference checks

## Optional Tooling Requirements

The canonical instructions are runtime-neutral. The bundled Python helpers require Python 3.10 or newer; strict validation of extended YAML frontmatter or live YAML manifests also requires PyYAML or target-native schema tooling. `scripts/scaffold.sh` additionally requires Bash, common POSIX utilities, and host/filesystem support for atomic no-replace directory publication. Environments without those capabilities can create the earned files through repository-native tooling and apply the same documented gates.
