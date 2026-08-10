#!/usr/bin/env python3
"""Validate the oneshot-websites skill package and its prompt catalogue."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Match, Optional, Pattern, Set, Tuple

from runtime_contract import parse_json_bounded


REQUIRED_DIRS = ("agents", "assets", "evals", "references", "scripts", "templates")
REQUIRED_FILES = (
    "AGENTS.md",
    "README.md",
    "SKILL.md",
    "metadata.json",
    "agents/catalog-curator.md",
    "agents/oneshot-critic.md",
    "agents/oneshot-lead.md",
    "assets/prompt-catalogue.json",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "references/README.md",
    "references/catalog-index.md",
    "references/catalogue-authoring.md",
    "references/execution-protocol.md",
    "references/research-notes.md",
    "references/wasm-selection.md",
    "scripts/build_catalog_index.py",
    "scripts/list_prompts.py",
    "scripts/prepare_run.py",
    "scripts/runtime_contract.py",
    "scripts/test_skill.py",
    "scripts/validate.py",
    "scripts/validate_catalog.py",
    "templates/run.json",
    "templates/worker-dispatch.md",
)

LOCAL_REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])((?:agents|assets|evals|references|scripts|templates)/[A-Za-z0-9_./-]+)"
)
PROMPT_ID_RE = re.compile(r"^ow-[0-9]{3,}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FROZEN_CATALOGUE_PREFIX_COUNT = 100
FROZEN_CATALOGUE_PREFIX_SHA256 = "893ce63f63f0dfb7bac7d4a0f0c22785f5433b04d7d8042fbd556674b445e3a0"
CANONICAL_EXPERIENCE_DIRECTION_SHA256 = "3a1ea9312d003857de83dce0dbe551641b0fba412efe86b1f585de4e5a629a3a"
CANONICAL_COMPLETION_MANDATE_SHA256 = "48abbf161b35327af91d0761ed3cda54abc61ce68a91be32e5f598fb185bdd79"
PACKAGE_VERSION = "2.13.0"

# These checks deliberately target unambiguous implementation prescriptions. A
# template may name a technology as its subject, but it must not prescribe a
# stack, version, file layout, resource budget, or workflow recipe.
IMPLEMENTATION_CONSTRAINTS = (
    ("version pin", re.compile(r"\b(?:react|vue|svelte|angular|node(?:\.js)?|python)\s*(?:v)?\d+(?:\.\d+){0,2}\b", re.I)),
    ("single-file recipe", re.compile(r"\b(?:single[- ]file|one[- ]file|one\s+html\s+file|all[- ]in[- ]one\s+html)\b", re.I)),
    (
        "named implementation recipe",
        re.compile(
            r"\b(?:use|using|built\s+with|build\s+(?:it\s+)?with|implement\s+(?:it\s+)?with)\s+"
            r"(?:only\s+)?(?:react|next(?:\.js)?|vue|nuxt|svelte|angular|solid(?:js)?|astro|tailwind(?:\s*css)?|"
            r"three(?:\.js)?|bootstrap|jquery|d3(?:\.js)?)\b",
            re.I,
        ),
    ),
    (
        "dependency or asset ban",
        re.compile(r"\b(?:no|without)\s+(?:any\s+)?(?:external\s+)?(?:dependencies|libraries|packages|assets)\b", re.I),
    ),
    (
        "resource budget",
        re.compile(
            r"\b(?:within|in)\s+\d+\s+(?:seconds?|minutes?|hours?)\b|"
            r"\b(?:exactly|at\s+most|no\s+more\s+than)\s+\d+\s+"
            r"(?:steps?|tool[- ]?calls?|files?|tokens?|minutes?|hours?)\b",
            re.I,
        ),
    ),
    (
        "goal-mode requirement",
        re.compile(r"\b(?:must|required\s+to|have\s+to)\s+(?:use|enable|enter)\s+goal[ -]?mode\b", re.I),
    ),
)

RUNTIME_CONTRACTS = (
    (
        "catalogue-first no-argument response",
        re.compile(
            r"No brief or arguments.*?first substantive response.*?grouped by namespace.*?one-line description",
            re.I | re.S,
        ),
    ),
    (
        "unbounded full-depth custom prompt refinement",
        re.compile(
            r"^- \*\*Custom brief:\*\*.*?refine.*?fully developed.*?"
            r"no skill-imposed paragraph or token budget.*?completionMandate.*?"
            r"forbids any appended text.*?stop before dispatch.*?never silently omit the mandate.*?$",
            re.I | re.M,
        ),
    ),
    (
        "silent shared catalogue direction",
        re.compile(
            r"Selected catalogue entry.*?craft.*?fully developed actual prompt.*?"
            r"experienceDirection.*?coordinator-only.*?never.*?(?:lead dispatch|PROMPT\.md)",
            re.I | re.S,
        ),
    ),
    (
        "subject-adapted lead-facing completion mandate",
        re.compile(
            r"^The catalogue’s top-level `completionMandate` is different:.*?"
            r"every prepared actual prompt.*?shortcuts.*?cookie-cutter.*?no token budget limit.*?"
            r"complete subject-specific depth.*?For a replica, clone, or emulator, require.*?"
            r"smallest meaningful interactions.*?For an original experience, demand equivalent depth.*?$",
            re.I | re.M,
        ),
    ),
    ("exact prompt preservation", re.compile(r"(?:byte-for-byte|exact\s+(?:UTF-8\s+)?bytes|verbatim).*?(?:prompt|PROMPT\.md)", re.I | re.S)),
    (
        "Unicode prompt integrity",
        re.compile(
            r"Before sealing the actual prompt.*?Unicode.*?UTF-8.*?special characters.*?"
            r"mojibake.*?prepare_run\.py.*?correct the prepared prompt at its source.*?"
            r"sealed `artifact/PROMPT\.md`.*?strictly decode.*?UTF-8.*?exact string.*?lead dispatch",
            re.I | re.S,
        ),
    ),
    ("coordinator prompt receipt", re.compile(r"(?:coordinator-owned|pre-dispatch).*?(?:receipt|provenance).*?(?:outside|worker-owned)|\.oneshot-provenance", re.I | re.S)),
    ("one fresh lead per experiment", re.compile(r"(?:one|each|every)\s+(?:fresh\s+)?lead.*?(?:each|every|one).*?experiment|fresh\s+lead\s+subagent", re.I | re.S)),
    (
        "explicit outer experiment fan-out",
        re.compile(
            r"multiple lead subagents.*?multiple workspaces.*?multiple replicas.*?top-level experiment fan-out.*?"
            r"stated count.*?authoritative.*?only “multiple,” create two.*?fresh lead.*?separate run directory.*?"
            r"Do not reinterpret.*?descendants inside one lead.*?folders inside one run",
            re.I | re.S,
        ),
    ),
    (
        "same-run reconnect and steering default",
        re.compile(
            r"Reconnects, steering, and side comments.*?timeout.*?environment interruption.*?"
            r"side comment.*?continuation by default.*?Reattach to the matching existing task.*?"
            r"lead.*?run directory.*?workspace.*?namespace instead of preparing another run.*?"
            r"Only an explicit request for a fresh workspace.*?new independent attempt.*?"
            r"additional replica.*?rerun changes that default",
            re.I | re.S,
        ),
    ),
    (
        "identity-gated recovery without guessing",
        re.compile(
            r"Reuse only a candidate whose identity is proven.*?coordinator receipt.*?`\.commit` marker.*?"
            r"run ID.*?exact run path.*?classification.*?experiment identity.*?prompt SHA-256 digest.*?"
            r"byte count.*?artifact/PROMPT\.md.*?active task.*?\.tmp/.*?workspace/.*?artifact/.*?"
            r"do not guess.*?silently reserve a replacement.*?RECOVERY_UNAVAILABLE.*?RECOVERY_AMBIGUOUS",
            re.I | re.S,
        ),
    ),
    (
        "single-owner same-run recovery",
        re.compile(
            r"For a proven continuation, resume the same harness task and owning lead first.*?"
            r"identical run ID.*?workspace.*?Deliver steering and side comments to that existing lead namespace.*?"
            r"prior owning lead has terminated and cannot be resumed.*?fresh no-history recovery lead.*?same run.*?"
            r"inspect and continue the current workspace.*?Never start a replacement while the prior owner may still be active.*?"
            r"exactly one active lead writer at a time",
            re.I | re.S,
        ),
    ),
    (
        "byte-identical replica prompts",
        re.compile(
            r"multiple replicas of the same brief.*?repeated single-brief fan-out.*?craft and seal.*?once.*?same prompt file.*?"
            r"digests and byte counts match.*?exact same decoded string.*?(?:do not add|without) replica labels.*?"
            r"autonomous-one-shot.*?priorRun: null.*?not reruns",
            re.I | re.S,
        ),
    ),
    ("no inherited coordinator history", re.compile(r"no-history.*?fork_turns.*?none|fork_turns.*?none.*?(?:coordinator|history|conversation)", re.I | re.S)),
    ("recursive subagent delegation", re.compile(r"recursive\s+(?:subagent\s+)?delegation|(?:lead|subagents?).*?create.*?subagents", re.I | re.S)),
    (
        "unbounded recursive descendant teams",
        re.compile(
            r"Every descendant may create and coordinate any number of further descendants.*?"
            r"permission continues at every generation.*?no skill-imposed per-parent count.*?"
            r"total descendant count.*?recursion-depth ceiling.*?"
            r"current concurrency or slot availability only as scheduling state.*?"
            r"never converts.*?temporary slot count.*?total-team.*?hierarchy-depth.*?capability budget",
            re.I | re.S,
        ),
    ),
    (
        "unrestricted build-agent capability allocation",
        re.compile(
            r"On the lead’s work and every build-related descendant.*?"
            r"Protect the lead and build-related descendants from arbitrary economy settings.*?"
            r"do not disable, downgrade, or withhold model or harness capabilities.*?"
            r"do not introduce local caps on their reasoning.*?context.*?turns.*?tools.*?"
            r"delegation.*?recursion.*?Critic descendants follow the adaptive allocation policy.*?"
            r"system.*?user.*?security.*?legal.*?"
            r"actual environment constraints remain authoritative",
            re.I | re.S,
        ),
    ),
    (
        "clean recursive-team orchestration and monitoring",
        re.compile(
            r"owns the orchestration and monitoring of its entire recursive team.*?"
            r"task, owner, deliverable, dependencies, allowed write scope, and completion evidence.*?"
            r"Track queued, active, completed, blocked, retried, and replaced work.*?"
            r"account for every outcome-relevant branch.*?"
            r"integration and consistency pass across the whole artifact",
            re.I | re.S,
        ),
    ),
    (
        "earned WebAssembly selection",
        re.compile(
            r"Keep implementation-selection guidance outside.*?do not add WebAssembly.*?artifact/PROMPT\.md.*?"
            r"Treat WebAssembly as an earned implementation choice.*?bounded spike.*?"
            r"DOM work.*?normal web stack.*?words.*?fast.*?3D.*?complex.*?written in Rust.*?"
            r"When WASM is selected.*?main thread.*?fallbacks.*?portable static-handoff.*?"
            r"references/wasm-selection\.md",
            re.I | re.S,
        ),
    ),
    (
        "inspectable quality bar",
        re.compile(
            r"concrete, inspectable quality bar.*?supplied reference.*?"
            r"no direct reference.*?(?:researches suitable category examples|measurable, subject-specific acceptance evidence).*?"
            r"Generic aspirations.*?not a bar",
            re.I | re.S,
        ),
    ),
    (
        "independently validated quality bar",
        re.compile(
            r"fresh critic checks.*?relevant.*?available.*?comparable.*?at least as demanding.*?"
            r"rejects.*?materially weaker proxy.*?Freeze the accepted bar.*?"
            r"record the prior bar, revised bar, and reason",
            re.I | re.S,
        ),
    ),
    (
        "coupling-aware decomposition",
        re.compile(
            r"decompos(?:e|es) work only along concerns.*?improved and judged independently.*?"
            r"parallelize truly independent concerns.*?tightly coupled.*?sequential owner.*?"
            r"integration and consistency pass",
            re.I | re.S,
        ),
    ),
    (
        "fresh real-artifact critic",
        re.compile(
            r"fresh recursive subagents.*?separate critic pass.*?empty inherited builder history.*?"
            r"actual prompt.*?quality bar.*?built artifact.*?"
            r"Do not give it the builder’s rationale.*?summary in place of the artifact.*?"
            r"single highest-leverage remaining gap",
            re.I | re.S,
        ),
    ),
    (
        "adaptive token-efficient critic allocation",
        re.compile(
            r"Use a quick, token-efficient critic configuration by default.*?"
            r"Reserve expansive reasoning.*?context.*?turns.*?tool breadth.*?token investment.*?"
            r"lead and build-related descendants.*?Give an ordinary critic only.*?"
            r"enough tools and context to inspect the real artifact directly.*?"
            r"concise verdict.*?concrete evidence.*?one highest-leverage gap.*?"
            r"Do not spend critic turns on implementation.*?open-ended redesign.*?broad exploratory research.*?"
            r"generating the fix",
            re.I | re.S,
        ),
    ),
    (
        "warranted critic escalation without review degradation",
        re.compile(
            r"Critic efficiency is an adaptive default.*?not a universal numeric token, turn, or model cap.*?"
            r"Escalate a critic’s model capability.*?only when a concrete review need warrants it.*?"
            r"large coupled state space.*?subtle reference comparison.*?accessibility.*?security.*?correctness.*?"
            r"conflicting evidence.*?inconclusive quick review.*?inspection format.*?Record the escalation reason.*?"
            r"cannot inspect the actual artifact.*?escalate.*?`BLOCKED`.*?never substitute a summary.*?lower the bar",
            re.I | re.S,
        ),
    ),
    (
        "evidence-based critic stopping",
        re.compile(
            r"new fresh critic.*?no skill-imposed number of rounds.*?"
            r"Stop only when.*?bar is met.*?materially actionable.*?genuine blocker.*?user stops.*?"
            r"Never stop merely because.*?predetermined round count",
            re.I | re.S,
        ),
    ),
    (
        "honest no-critic fallback",
        re.compile(
            r"fresh recursive delegation is unavailable.*?strongest artifact-grounded.*?"
            r"record that a fresh critic was unavailable.*?do not claim independent critic verification",
            re.I | re.S,
        ),
    ),
    (
        "quality revisions stay in one run",
        re.compile(
            r"internal quality gauntlet.*?internal revisions.*?same one-shot run.*?"
            r"not coordinator follow-ups or new experiments",
            re.I | re.S,
        ),
    ),
    (
        "gauntlet history separated from final verification",
        re.compile(
            r"worker-report\.json\.qualityGauntlet.*?artifact revision.*?"
            r"verification.*?final checks.*?NOT_READY.*?gauntlet history.*?"
            r"failed final verification.*?later `OK` artifact",
            re.I | re.S,
        ),
    ),
    ("no skill-imposed time, token, and tool limits", re.compile(r"no\s+skill-imposed.*?(?:time|token).*?(?:tool|tool-call)|no\s+(?:time|token).*?(?:tool|tool-call).*?(?:limit|budget)", re.I | re.S)),
    ("no goal-mode requirement", re.compile(r"goal[ -]?mode.*?(?:not|required|forbidden)|(?:not|required|forbidden).*?goal[ -]?mode", re.I | re.S)),
    (
        "run-local temporary containment",
        re.compile(
            r"Keep disposable working state.*?run’s `\.tmp/`.*?TMPDIR.*?TMP.*?TEMP.*?"
            r"Preserve `\.tmp/`.*?best effort.*?Durable project files.*?workspace/.*?never belongs.*?artifact",
            re.I | re.S,
        ),
    ),
    (
        "descendant temporary routing",
        re.compile(r"Every descendant receives.*?run-local temporary path.*?temporary-environment routing", re.I | re.S),
    ),
    (
        "temporary guidance excluded from prompts",
        re.compile(
            r"operational guidance.*?stay out of.*?actual prompt.*?artifact/PROMPT\.md",
            re.I | re.S,
        ),
    ),
    (
        "local-only external-publication authority",
        re.compile(
            r"Keep Remote Publication Off by Default.*?authorizes local creation.*?"
            r"never authorize an external write.*?Vercel Drop.*?Cloudflare Drop.*?"
            r"ChatGPT sites.*?GitHub.*?authenticated tool.*?do not count as permission.*?"
            r"explicit user instruction.*?specific external action and destination.*?"
            r"Never ask a lead, descendant, or critic.*?remote publication.*?remote repository mutation.*?"
            r"coordinator retains.*?only after.*?local artifact passes validation.*?"
            r"using `artifact/` only.*?nothing was uploaded, deployed, published, or pushed",
            re.I | re.S,
        ),
    ),
    (
        "local static-handoff verification semantics",
        re.compile(
            r"worker-report\.json\.artifact\.staticDeploymentVerified.*?"
            r"only.*?local static-handoff checks.*?never records or requires a live deployment.*?"
            r"may reach `OK` with no network publication",
            re.I | re.S,
        ),
    ),
    (
        "flat slugged timestamp run layout",
        re.compile(
            r"^  <YYYY-MM-DD-HH-MM-SS>-<experiment-slug>/\n.*?"
            r"(?:Create each run|create a new run) directly beneath.*?local timestamp plus.*?experiment-slug.*?"
            r"LibreOffice Writer.*?libreoffice-writer.*?--02.*?--03",
            re.I | re.M | re.S,
        ),
    ),
    (
        "raw identity metadata",
        re.compile(r"exact model, harness, and experiment names.*?digest-bound (?:identity )?keys.*?run\.json.*?receipt", re.I | re.S),
    ),
    ("relevance-gated catalogue matching", re.compile(r"genuinely relevant.*?optional baselines.*?no meaningful match.*?without.*?catalogue", re.I | re.S)),
    ("artifact prompt", re.compile(r"artifact/PROMPT\.md")),
    ("artifact entrypoint", re.compile(r"artifact/index\.html")),
    (
        "multi-file artifact allowance",
        re.compile(
            r"entrypoint rule.*?not a single-file rule.*?(?:asset directory|built script|stylesheet|media file)",
            re.I | re.S,
        ),
    ),
    ("drop-ready no-build handoff", re.compile(r"(?:drop-ready|static\s+(?:folder|host)).*?(?:no\s+(?:package\s+)?install|no\s+build|deployable)|(?:no\s+(?:package\s+)?install|no\s+build).*?(?:drop-ready|static\s+(?:folder|host))", re.I | re.S)),
)

PUBLICATION_AUTHORITY_SOURCES = (
    (
        "ambient capability treated as deployment authorization",
        re.compile(
            r"\b(?:credentials?|tokens?|tools?|CLIs?|MCP\s+(?:connectors?|servers?|tools?)|"
            r"environment|configuration|authenticated\s+sessions?)\b",
            re.I,
        ),
    ),
    (
        "worker granted remote-publication authority",
        re.compile(
            r"\b(?:leads?|descendants?|critics?|workers?|subagents?)\b",
            re.I,
        ),
    ),
    (
        "untrusted content treated as deployment authorization",
        re.compile(
            r"\b(?:actual\s+prompt|prompt\s+text|references?|repository\s+files?|artifacts?|"
            r"web\s+pages?|tool\s+output)\b",
            re.I,
        ),
    ),
    (
        "static handoff verification treated as live publication evidence",
        re.compile(r"\bstaticDeploymentVerified\b", re.I),
    ),
    (
        "portability treated as deployment authorization",
        re.compile(r"\b(?:drop-ready|deployment-ready|portable|portability)\b", re.I),
    ),
)

PUBLICATION_GRANT_RE = re.compile(
    r"\b(?:authoriz(?:e|es|ed|ation)|permit(?:s|ted)?|permission|allow(?:s|ed)?|"
    r"grant(?:s|ed)?|authority|entitl(?:e|es|ed)|sufficient)\b",
    re.I,
)
WORKER_PUBLICATION_MODAL_RE = re.compile(r"\b(?:may|can|should|must)\b", re.I)
STATIC_PUBLICATION_EVIDENCE_RE = re.compile(
    r"\b(?:means?|proves?|confirms?|records?|requires?|indicates?|shows?)\b",
    re.I,
)
REMOTE_PUBLICATION_ACTION_RE = re.compile(
    r"\b(?:deploy(?:ment|ed|ing|s)?|upload(?:ed|ing|s)?|publish(?:ed|ing|es)?|publication|"
    r"push(?:ed|ing|es)?|claim(?:ed|ing|s)?|remote\s+(?:write|mutation))\b",
    re.I,
)
PUBLICATION_SENTENCE_SPLIT_RE = re.compile(r"[.!?;\n]+")
PUBLICATION_CONTRAST_SPLIT_RE = re.compile(r"\b(?:but|however|yet|whereas|while)\b", re.I)
NEGATED_MATCH_PREFIX_RE = re.compile(
    r"(?:\b(?:no|not|never|without|cannot|can't|doesn't|isn't|aren't|"
    r"mustn't|shouldn't|wouldn't)\b(?:\W+\w+){0,5}\W*|"
    r"\b(?:does|is|are|must|should|would)\s+not\b(?:\W+\w+){0,5}\W*)$",
    re.I,
)
SCOPED_AUTHORIZATION_PREFIX_RE = re.compile(
    r"(?:\b(?:explicitly|separately|specifically|narrowly)\s+|"
    r"\buser(?:[- ]|['’]s\s+))$",
    re.I,
)

GUIDANCE_LEAK_DIRECTIVES = (
    (
        "lead-facing verbatim experience direction block",
        re.compile(r"EXPERIENCE DIRECTION\s*\(verbatim\)", re.I),
    ),
    (
        "instruction to copy internal direction into the lead prompt",
        re.compile(
            r"\b(?:copy|paste|append|add|include)\b.{0,240}"
            r"\b(?:experienceDirection|shared\s+(?:experience\s+)?direction)\b.{0,240}"
            r"\b(?:actual\s+prompt|lead\s+dispatch|PROMPT\.md|end\s+of\s+the\s+prompt|"
            r"second\s+(?:paragraph|block)|third\s+(?:paragraph|block))\b",
            re.I | re.S,
        ),
    ),
    (
        "instruction to add labelled generic guidance to the lead prompt",
        re.compile(
            r"\b(?:add|include|append|create)\b.{0,160}\b(?:labelled|labeled)\b.{0,120}"
            r"\b(?:block|paragraph)\b.{0,200}\b(?:visual|interaction)\b.{0,120}"
            r"\b(?:guidance|direction)\b",
            re.I | re.S,
        ),
    ),
)
NEGATED_GUIDANCE_DIRECTIVE = re.compile(
    r"\b(?:never|do\s+not|must\s+not|must\s+never|should\s+not)\b[^.!?;:\n]{0,100}$",
    re.I,
)
GUIDANCE_CLAUSE_BOUNDARY = re.compile(r"[.!?;:\n—–]+|\b(?:but|however|instead|then)\b", re.I)

FILE_RUNTIME_CONTRACTS = (
    (
        "agents/oneshot-critic.md",
        "fresh read-only critic contract",
        re.compile(
            r"independent, read-only critic.*?without inherited builder conversation.*?"
            r"Never accept a prose summary in place of.*?actual artifact.*?"
            r"single highest-leverage material gap.*?NOT_READY.*?READY.*?BLOCKED.*?"
            r"Do not edit the workspace or artifact",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-critic.md",
        "adaptive token-efficient critic role",
        re.compile(
            r"Resource and Output Discipline.*?quick, token-efficient critic by default.*?"
            r"fastest capable configuration.*?smallest sufficient reasoning depth.*?context.*?tool set.*?"
            r"inspect the real artifact directly.*?one review pass and one decision.*?"
            r"implementation.*?broad exploration.*?open-ended redesign.*?build-related descendants.*?"
            r"adaptive, not a fixed numeric token, turn, or model cap.*?"
            r"deeper critic is warranted.*?return `BLOCKED`.*?rather than grading a summary or lowering the bar",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-lead.md",
        "lead-owned quality gauntlet",
        re.compile(
            r"Quality Gauntlet.*?inspectable quality bar.*?"
            r"keep coupled.*?under one sequential owner.*?"
            r"create a critic with empty inherited builder history.*?"
            r"new fresh critic.*?no fixed critic-round budget.*?"
            r"never claim that an independent critic reviewed",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-lead.md",
        "lead same-run continuation and recovery",
        re.compile(
            r"Continuation and Recovery.*?timeout.*?steering message.*?side comment.*?same experiment.*?"
            r"keep the current run ID.*?workspace.*?artifact.*?accumulated work.*?"
            r"preserve `artifact/PROMPT\.md` byte-for-byte.*?"
            r"replacement recovery lead.*?proved.*?previous owner terminated.*?"
            r"Read the existing `run\.json`.*?workspace/.*?artifact/.*?before editing.*?"
            r"only active lead writer.*?make no edits.*?RECOVERY_AMBIGUOUS.*?RECOVERY_OWNER_ACTIVE",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-lead.md",
        "lead unbounded recursive-team capability contract",
        re.compile(
            r"Your Team.*?as many subagents as useful.*?"
            r"Every descendant may create and coordinate any number of further descendants.*?"
            r"permission continues at every generation.*?no skill-imposed per-parent count.*?"
            r"total descendant count.*?recursion-depth ceiling.*?"
            r"current concurrency or slot availability as scheduling state.*?"
            r"Do not reduce a build-related descendant’s reasoning.*?context.*?tools.*?turns.*?"
            r"further-delegation capability.*?Assign critics by the focused, token-efficient default.*?"
            r"escalate them when evidence warrants it",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-lead.md",
        "lead adaptive critic resource allocation",
        re.compile(
            r"Quality Gauntlet.*?quick, token-efficient critic configuration by default.*?"
            r"Reserve expansive reasoning.*?token investment for build-related descendants.*?"
            r"concise verdict.*?one highest-leverage gap.*?adaptive allocation policy.*?"
            r"not a fixed token, turn, or model cap.*?Escalate critic capability.*?"
            r"only for a concrete review need.*?Record why escalation was warranted.*?"
            r"cannot directly inspect.*?escalate.*?`BLOCKED`.*?never grade a summary or weaken the bar",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-lead.md",
        "lead recursive-team orchestration and monitoring",
        re.compile(
            r"accountable for clean orchestration, integration, and verification across the full tree.*?"
            r"clear task, owner, deliverable, dependencies, allowed write scope, and evidence target.*?"
            r"Track queued, active, completed, blocked, retried, and replaced branches.*?"
            r"account for every outcome-relevant branch.*?"
            r"whole-artifact integration and consistency pass",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-lead.md",
        "lead WebAssembly decision gate",
        re.compile(
            r"WebAssembly Decision.*?earned implementation choice.*?proven native library.*?"
            r"simplest credible JavaScript or TypeScript baseline.*?cold start.*?boundary-copy cost.*?"
            r"Keep DOM behavior.*?web layer.*?Worker.*?portable static envelope.*?"
            r"Never add.*?artifact/PROMPT\.md",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-lead.md",
        "lead temporary-file discipline",
        re.compile(
            r"Temporary-File Discipline.*?assigned run’s `\.tmp/`.*?TMPDIR.*?TMP.*?TEMP.*?"
            r"every descendant.*?best-effort containment.*?Preserve `\.tmp/`.*?"
            r"never copy `\.tmp/` into `artifact/`.*?Never add it.*?artifact/PROMPT\.md",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-lead.md",
        "lead local-only external-write boundary",
        re.compile(
            r"External-Write Boundary.*?authority is local-build-only.*?never upload, deploy, publish, push.*?"
            r"Vercel Drop.*?Cloudflare Drop.*?ChatGPT sites.*?GitHub.*?"
            r"Tool availability is capability, not authorization.*?"
            r"coordinator owns any separately authorized publication.*?"
            r"every descendant remain local-only.*?perform no external mutation",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-lead.md",
        "lead local static-handoff verification semantics",
        re.compile(
            r"artifact\.staticDeploymentVerified.*?local static-handoff verification.*?"
            r"never means a live deployment happened.*?never requires a network write.*?"
            r"entirely local run can be `OK`",
            re.I | re.S,
        ),
    ),
    (
        "agents/oneshot-critic.md",
        "critic local read-only external-write boundary",
        re.compile(
            r"External-Write Boundary.*?review is local and read-only.*?"
            r"Never upload, deploy, publish, push.*?Vercel Drop.*?Cloudflare Drop.*?"
            r"ChatGPT sites.*?GitHub.*?does not authorize.*?mutate an external service.*?"
            r"Do not use a live deployment as a review prerequisite",
            re.I | re.S,
        ),
    ),
    (
        "templates/worker-dispatch.md",
        "embedded fresh critic role",
        re.compile(
            r"Fresh Critic Role.*?complete current contents of `agents/oneshot-critic\.md`.*?"
            r"empty-history lead.*?without relying on ambient package discovery.*?"
            r"\{\{ONESHOT_CRITIC_ROLE\}\}",
            re.I | re.S,
        ),
    ),
    (
        "templates/worker-dispatch.md",
        "dispatch same-run recovery envelope",
        re.compile(
            r"Dispatch and Recovery Mode.*?Do not create a new dispatch for a resumable existing lead.*?"
            r"steering.*?side comments.*?current harness task.*?"
            r"replacement.*?prove that the prior owner terminated.*?committed receipt.*?prompt digest and byte count.*?"
            r"inspect and continue `workspace/`.*?must not clear, reinitialize, copy, or fork the run.*?"
            r"Never dispatch a replacement while another lead may still be active.*?"
            r"out of `artifact/PROMPT\.md`.*?\{\{RECOVERY_ENVELOPE\}\}",
            re.I | re.S,
        ),
    ),
    (
        "templates/worker-dispatch.md",
        "dispatch temporary-file envelope",
        re.compile(
            r"Operational Runtime Envelope.*?assigned `\.tmp/`.*?TMPDIR.*?TMP.*?TEMP.*?"
            r"every descendant.*?Preserve `\.tmp/`.*?Never copy `\.tmp/` into `artifact/`.*?"
            r"never add.*?artifact/PROMPT\.md",
            re.I | re.S,
        ),
    ),
    (
        "templates/worker-dispatch.md",
        "dispatch recursive-team envelope",
        re.compile(
            r"Recursive Team Envelope.*?as many descendant subagents.*?"
            r"Every descendant may create any number of further descendants.*?"
            r"no skill-imposed per-parent count.*?total descendant count.*?recursion-depth ceiling.*?"
            r"Protect the lead and build-related descendants from arbitrary economy settings.*?"
            r"do not disable, downgrade, or withhold available model or harness capabilities.*?"
            r"Critic descendants follow the adaptive critic allocation envelope.*?"
            r"Current concurrency or slot availability affects scheduling only.*?"
            r"monitor queued, active, completed, blocked, retried, and replaced branches.*?"
            r"whole-artifact integration pass.*?Keep this recursive-team material out.*?artifact/PROMPT\.md",
            re.I | re.S,
        ),
    ),
    (
        "templates/worker-dispatch.md",
        "dispatch adaptive critic allocation envelope",
        re.compile(
            r"Critic Allocation Envelope.*?quick, token-efficient critic configuration by default.*?"
            r"reserve expansive reasoning.*?token investment for build-related descendants.*?"
            r"inspect the real artifact directly.*?concise verdict.*?one highest-leverage gap.*?"
            r"Escalate critic capability.*?only when a concrete review need warrants it.*?"
            r"adaptive allocation rather than a fixed numeric cap.*?escalate or return `BLOCKED`.*?"
            r"Never trade away artifact-grounded review merely to save tokens.*?artifact/PROMPT\.md",
            re.I | re.S,
        ),
    ),
    (
        "templates/worker-dispatch.md",
        "dispatch local-only publication envelope",
        re.compile(
            r"Local-Only Publication Envelope.*?Build, test, validate, and package locally.*?"
            r"Never upload, deploy, publish, push.*?Vercel Drop.*?Cloudflare Drop.*?"
            r"ChatGPT sites.*?GitHub.*?Tool availability.*?do not grant authority.*?"
            r"coordinator retains.*?remote action.*?lead and every descendant always stop.*?artifact/.*?"
            r"Drop-ready.*?not permission to upload, deploy, publish, or push",
            re.I | re.S,
        ),
    ),
    (
        "templates/worker-dispatch.md",
        "conditional dispatch WebAssembly guidance",
        re.compile(
            r"Conditional WebAssembly Guidance.*?complete current contents of `references/wasm-selection\.md`.*?"
            r"justified narrow WASM core.*?bounded representative spike.*?ordinary web stack.*?"
            r"no plausible boundary.*?agents/oneshot-lead\.md.*?"
            r"Never append.*?artifact/PROMPT\.md.*?\{\{WASM_SELECTION_GUIDANCE\}\}",
            re.I | re.S,
        ),
    ),
    (
        "references/wasm-selection.md",
        "WebAssembly scenarios and static-artifact contract",
        re.compile(
            r"operational lead guidance only.*?Never append.*?artifact/PROMPT\.md.*?"
            r"Decision Gate.*?bounded spike.*?representative data.*?"
            r"Lead Contract When WASM Fits.*?Worker.*?5 MiB per-file limit.*?"
            r"Sample Scenarios.*?SQLite.*?Rust backend.*?prepared actual prompt remains unchanged",
            re.I | re.S,
        ),
    ),
    (
        "references/execution-protocol.md",
        "protocol remote-publication authority",
        re.compile(
            r"Remote Publication Authority.*?local portable build, not external publication.*?"
            r"Vercel Drop.*?Cloudflare Drop.*?ChatGPT sites.*?GitHub.*?"
            r"explicitly authorizes the specific external action and destination.*?"
            r"Leads, descendants, and critics remain local-only.*?coordinator retains.*?"
            r"post-validation step from `artifact/` only",
            re.I | re.S,
        ),
    ),
    (
        "references/execution-protocol.md",
        "protocol identity-safe same-run recovery",
        re.compile(
            r"Reconnect, Steering, and Same-Run Recovery.*?continuation by default.*?"
            r"reuse the existing harness task.*?run ID.*?workspace.*?do not call `scripts/prepare_run\.py`.*?"
            r"identity anchors agree.*?receipt.*?`\.commit` marker.*?prompt digest.*?byte count.*?"
            r"known task, lead, or run ID outranks.*?RECOVERY_AMBIGUOUS.*?"
            r"Resume the same harness task and owning lead whenever possible.*?"
            r"prior lead has terminated.*?single fresh no-history recovery lead.*?same namespace.*?"
            r"Only one lead may write an experiment namespace at a time.*?retry must be idempotent",
            re.I | re.S,
        ),
    ),
    (
        "references/execution-protocol.md",
        "protocol unbounded recursive-team scheduling and accountability",
        re.compile(
            r"recursive-team envelope is also lead-operational metadata.*?"
            r"Every descendant may create any number of further descendants.*?"
            r"without a skill-imposed per-parent, total-tree, or recursion-depth ceiling.*?"
            r"Protect the lead and build-related descendants from arbitrary economy settings.*?"
            r"do not disable, downgrade, or withhold model or harness capabilities.*?"
            r"Critic descendants use the adaptive allocation policy.*?"
            r"Temporary concurrency and slot availability govern scheduling only.*?"
            r"monitors their states and results.*?accounts for outcome-relevant work.*?"
            r"whole-artifact integration pass",
            re.I | re.S,
        ),
    ),
    (
        "references/execution-protocol.md",
        "protocol adaptive critic resource allocation",
        re.compile(
            r"Lead-Owned Quality Gauntlet.*?Default to a quick, token-efficient critic.*?"
            r"reserve expansive reasoning.*?token investment for build-related descendants.*?"
            r"adaptive allocation, not a fixed numeric token, turn, or model cap.*?"
            r"Escalate.*?only for a concrete review need.*?record the reason.*?"
            r"cannot inspect the actual artifact directly.*?escalate or return `BLOCKED`.*?"
            r"rather than grading a summary or weakening the bar",
            re.I | re.S,
        ),
    ),
    (
        "references/catalog-index.md",
        "catalog compatibility is not publication permission",
        re.compile(
            r"compatibility is not upload permission.*?Local building, indexing, and validation stop.*?"
            r"Cloudflare Drop.*?Vercel Drop.*?ChatGPT sites.*?GitHub.*?"
            r"explicitly authorizes that specific external action and destination.*?"
            r"Leads and critics never deploy.*?coordinator performs.*?from `artifact/` only",
            re.I | re.S,
        ),
    ),
    (
        "references/catalogue-authoring.md",
        "catalogue operational verbs remain simulated",
        re.compile(
            r"Catalogue verbs describe behavior inside the locally built experience.*?"
            r"publish.*?share.*?book.*?reserve.*?simulated states.*?"
            r"separately authorizes a specific live integration and target.*?"
            r"can never grant.*?external-write authority",
            re.I | re.S,
        ),
    ),
)


def parse_frontmatter(text: str) -> Dict[str, str]:
    """Parse the small scalar frontmatter contract without a YAML dependency."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}

    values: Dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line or line.startswith((" ", "\t", "#")) or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip()
        if len(value) >= 2 and value[:1] in ("'", '"') and value[-1:] == value[:1]:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def strip_code_blocks(text: str) -> str:
    return re.sub(r"```[\s\S]*?```", "", text)


def local_references(text: str) -> Set[str]:
    references: Set[str] = set()
    for match in LOCAL_REFERENCE_RE.finditer(strip_code_blocks(text)):
        reference = match.group(1).rstrip(".,:;)")
        if ".." not in Path(reference).parts:
            references.add(reference)
    return references


def read_json(path: Path, errors: List[str], root: Path) -> Optional[Any]:
    try:
        return parse_json_bounded(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        errors.append("invalid JSON in {}: {}".format(path.relative_to(root), exc))
        return None


def read_text(path: Path, errors: List[str], root: Path) -> Optional[str]:
    """Read package prose without letting malformed UTF-8 abort validation."""

    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append("invalid UTF-8 text in {}: {}".format(path.relative_to(root), exc))
        return None


def duplicate_values(values: Iterable[str]) -> Set[str]:
    seen: Set[str] = set()
    duplicates: Set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def as_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        normalized.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return normalized


def validate_catalogue(data: Any, errors: List[str]) -> None:
    """Check permanent catalogue identities and implementation-open prompts."""
    if not isinstance(data, Mapping):
        errors.append("assets/prompt-catalogue.json must contain an object")
        return
    if data.get("schemaVersion") != "1.2":
        errors.append("prompt catalogue schemaVersion must be 1.2")

    direction_value = data.get("experienceDirection")
    if isinstance(direction_value, str) and direction_value != direction_value.strip():
        errors.append("prompt catalogue experienceDirection must not contain surrounding whitespace")
    experience_direction = as_text(direction_value)
    if experience_direction is None:
        errors.append("prompt catalogue is missing experienceDirection")
    else:
        direction_digest = hashlib.sha256(experience_direction.encode("utf-8")).hexdigest()
        if direction_digest != CANONICAL_EXPERIENCE_DIRECTION_SHA256:
            errors.append(
                "prompt catalogue experienceDirection differs from the canonical reviewed direction; "
                "keep implementation choices open and update the validator digest only after deliberate review"
            )
        if "\n" in experience_direction or "\r" in experience_direction:
            errors.append("prompt catalogue experienceDirection must fit on one line")
        for reason, expression in IMPLEMENTATION_CONSTRAINTS:
            if expression.search(experience_direction):
                errors.append("prompt catalogue experienceDirection contains a {} constraint".format(reason))
        direction_requirements = (
            ("a visually led default", re.compile(r"\bvisually led\b", re.I)),
            ("an interaction-first default", re.compile(r"\binteraction-first\b", re.I)),
            ("motion or animation", re.compile(r"\b(?:motion|animation)\b", re.I)),
            ("concise text guidance", re.compile(r"\btext\b.*?\bconcise\b|\bconcise\b.*?\btext\b", re.I)),
            ("a text-rich format exception", re.compile(r"\b(?:landing page|CMS|publication|narrative archive)\b", re.I)),
            ("lead-owned technology and dependency choices", re.compile(r"\btechnology\b.*?\bdependency\b.*?\blead\b", re.I)),
        )
        for label, expression in direction_requirements:
            if not expression.search(experience_direction):
                errors.append("prompt catalogue experienceDirection is missing {}".format(label))

    mandate_value = data.get("completionMandate")
    if isinstance(mandate_value, str) and mandate_value != mandate_value.strip():
        errors.append("prompt catalogue completionMandate must not contain surrounding whitespace")
    completion_mandate = as_text(mandate_value)
    if completion_mandate is None:
        errors.append("prompt catalogue is missing completionMandate")
    else:
        mandate_digest = hashlib.sha256(completion_mandate.encode("utf-8")).hexdigest()
        if mandate_digest != CANONICAL_COMPLETION_MANDATE_SHA256:
            errors.append(
                "prompt catalogue completionMandate differs from the canonical reviewed mandate; "
                "update the validator digest only after deliberate review"
            )
        if "\n" in completion_mandate or "\r" in completion_mandate:
            errors.append("prompt catalogue completionMandate must fit on one line")
        for reason, expression in IMPLEMENTATION_CONSTRAINTS:
            if expression.search(completion_mandate):
                errors.append("prompt catalogue completionMandate contains a {} constraint".format(reason))
        mandate_requirements = (
            ("an explicit no-shortcuts requirement", re.compile(r"\bshortcuts\b", re.I)),
            ("an explicit anti-cookie-cutter requirement", re.compile(r"\bcookie-cutter\b", re.I)),
            ("no skill-imposed token budget", re.compile(r"\bno token budget limit\b", re.I)),
            ("replica, clone, and emulator coverage", re.compile(r"\breplicas?, clones?, and emulators?\b", re.I)),
            ("small-interaction fidelity", re.compile(r"\bsmallest meaningful interactions\b", re.I)),
            ("original-experience depth", re.compile(r"\boriginal experiences\b.*?\bequivalent depth\b", re.I)),
            ("subject-adapted expression", re.compile(r"\bnaturally\b.*?\bsubject\b", re.I)),
            ("implementation-open guidance", re.compile(r"\bnever prescribe a technology, library, framework, or workflow\b", re.I)),
        )
        for label, expression in mandate_requirements:
            if not expression.search(completion_mandate):
                errors.append("prompt catalogue completionMandate is missing {}".format(label))

    categories = data.get("categories")
    prompts = data.get("prompts")
    if not isinstance(categories, list):
        errors.append("prompt catalogue categories must be an array")
        categories = []
    if not isinstance(prompts, list):
        errors.append("prompt catalogue prompts must be an array")
        return

    category_ids: List[str] = []
    for index, category in enumerate(categories):
        if not isinstance(category, Mapping):
            errors.append("catalogue category {} must be an object".format(index))
            continue
        for field in ("id", "title", "description"):
            field_value = category.get(field)
            if isinstance(field_value, str) and field_value != field_value.strip():
                errors.append(
                    "catalogue category {} {} must not contain surrounding whitespace".format(
                        index,
                        field,
                    )
                )
        category_id = as_text(category.get("id"))
        title = as_text(category.get("title"))
        description = as_text(category.get("description"))
        if category_id is None or not SLUG_RE.fullmatch(category_id):
            errors.append("catalogue category {} has an invalid id".format(index))
        else:
            category_ids.append(category_id)
        if title is None:
            errors.append("catalogue category {} is missing a title".format(index))
        if description is None:
            errors.append("catalogue category {} is missing a description".format(index))
        elif "\n" in description or "\r" in description:
            errors.append("catalogue category {} description must fit on one line".format(index))
    duplicates = duplicate_values(category_ids)
    if duplicates:
        errors.append("catalogue contains duplicate category ids: {}".format(", ".join(sorted(duplicates))))
    known_categories = set(category_ids)

    if len(prompts) < FROZEN_CATALOGUE_PREFIX_COUNT:
        errors.append(
            "prompt catalogue must contain at least {} prompts (found {})".format(
                FROZEN_CATALOGUE_PREFIX_COUNT,
                len(prompts),
            )
        )
    if len(prompts) >= FROZEN_CATALOGUE_PREFIX_COUNT:
        frozen_prefix = json.dumps(
            prompts[:FROZEN_CATALOGUE_PREFIX_COUNT],
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        frozen_digest = hashlib.sha256(frozen_prefix).hexdigest()
        if frozen_digest != FROZEN_CATALOGUE_PREFIX_SHA256:
            errors.append(
                "catalogue entries ow-001 through ow-100 are a frozen append-only prefix; "
                "append new entries without editing, deleting, renumbering, or reordering the seed catalogue"
            )

    ids: List[str] = []
    slugs: List[str] = []
    titles: List[str] = []
    descriptions: List[str] = []
    prompt_texts: List[str] = []
    for index, item in enumerate(prompts):
        label = "catalogue prompt {}".format(index)
        if not isinstance(item, Mapping):
            errors.append("{} must be an object".format(label))
            continue
        for field in ("id", "slug", "title", "description", "category", "prompt"):
            field_value = item.get(field)
            if isinstance(field_value, str) and field_value != field_value.strip():
                errors.append("{} {} must not contain surrounding whitespace".format(label, field))
        prompt_id = as_text(item.get("id"))
        slug = as_text(item.get("slug"))
        title = as_text(item.get("title"))
        description = as_text(item.get("description"))
        category = as_text(item.get("category"))
        prompt = as_text(item.get("prompt"))
        tags = item.get("tags")
        expected_prompt_id = "ow-{:03d}".format(index + 1)

        if prompt_id is None or not PROMPT_ID_RE.fullmatch(prompt_id):
            errors.append("{} has an invalid stable id".format(label))
        else:
            ids.append(prompt_id)
            if prompt_id != expected_prompt_id:
                errors.append(
                    "{} must use the next append-only stable id {}".format(
                        label,
                        expected_prompt_id,
                    )
                )
        if slug is None or not SLUG_RE.fullmatch(slug):
            errors.append("{} has an invalid slug".format(label))
        else:
            slugs.append(slug)
        if title is None:
            errors.append("{} is missing a title".format(label))
        else:
            titles.append(title.casefold())
            if len(title) > 48 or len(title.split()) > 6:
                errors.append(
                    "{} title must be a plain label of at most 48 characters and 6 words".format(
                        label
                    )
                )
        if description is None:
            errors.append("{} is missing a description".format(label))
        else:
            descriptions.append(description.casefold())
            if "\n" in description or "\r" in description:
                errors.append("{} description must fit on one line".format(label))
            if len(description) > 140 or len(description.split()) > 18:
                errors.append(
                    "{} description must be scan-friendly: at most 140 characters and 18 words".format(
                        label
                    )
                )
        if category is None or category not in known_categories:
            errors.append("{} uses an undeclared category: {}".format(label, category or "missing"))
        if prompt is None:
            errors.append("{} is missing prompt text".format(label))
        else:
            prompt_texts.append(prompt.casefold())
            if not prompt.startswith("Create "):
                errors.append("{} must begin with a goal-led 'Create ' statement".format(label))
            for reason, expression in IMPLEMENTATION_CONSTRAINTS:
                if expression.search(prompt):
                    errors.append("{} contains a {} constraint".format(label, reason))
        if not isinstance(tags, list) or not tags:
            errors.append("{} must have non-empty tags".format(label))
        else:
            clean_tags = [tag for tag in tags if isinstance(tag, str) and SLUG_RE.fullmatch(tag)]
            if len(clean_tags) != len(tags):
                errors.append("{} has invalid tags".format(label))
            if len(set(clean_tags)) != len(clean_tags):
                errors.append("{} has duplicate tags".format(label))

    for field, values in (
        ("ids", ids),
        ("slugs", slugs),
        ("titles", titles),
        ("descriptions", descriptions),
        ("prompt texts", prompt_texts),
    ):
        duplicates = duplicate_values(values)
        if duplicates:
            errors.append("catalogue contains duplicate {}: {}".format(field, ", ".join(sorted(duplicates))))


def paragraph_blocks(text: str) -> List[str]:
    """Return prose and fenced-example blocks local to one instruction."""

    return [block for block in re.split(r"\n\s*\n", text) if block.strip()]


def directive_is_negated(block: str, directive_start: int) -> bool:
    """Distinguish a prohibition from the positive leak instruction it quotes."""

    clause_prefix = GUIDANCE_CLAUSE_BOUNDARY.split(block[:directive_start])[-1]
    return bool(NEGATED_GUIDANCE_DIRECTIVE.search(clause_prefix))


def overlapping_matches(expression: Pattern[str], text: str) -> Iterator[Match[str]]:
    """Yield every directive start, including actions nested in a wider match."""

    search_start = 0
    while search_start < len(text):
        match = expression.search(text, search_start)
        if match is None:
            return
        yield match
        search_start = match.start() + 1


def match_is_negated(clause: str, match: Match[str]) -> bool:
    """Return whether a nearby explicit negation governs one matched phrase."""

    prefix = clause[max(0, match.start() - 96) : match.start()]
    return bool(
        NEGATED_MATCH_PREFIX_RE.search(prefix)
        or SCOPED_AUTHORIZATION_PREFIX_RE.search(prefix)
    )


def unnegated_matches(expression: Pattern[str], clause: str) -> List[Match[str]]:
    """Return operative phrases rather than ones denied in the same clause."""

    return [
        match
        for match in expression.finditer(clause)
        if not match_is_negated(clause, match)
    ]


def publication_authority_contradictions(text: str) -> Iterator[str]:
    """Detect positive grants of publication authority without rejecting denials."""

    found: Set[str] = set()
    for sentence in PUBLICATION_SENTENCE_SPLIT_RE.split(text):
        for clause in PUBLICATION_CONTRAST_SPLIT_RE.split(sentence):
            action_matches = unnegated_matches(REMOTE_PUBLICATION_ACTION_RE, clause)
            if not action_matches:
                continue
            for label, source_expression in PUBLICATION_AUTHORITY_SOURCES:
                source_matches = list(source_expression.finditer(clause))
                if label in found or not source_matches:
                    continue
                if label == "worker granted remote-publication authority":
                    authority_expressions = (PUBLICATION_GRANT_RE, WORKER_PUBLICATION_MODAL_RE)
                elif label == "static handoff verification treated as live publication evidence":
                    authority_expressions = (STATIC_PUBLICATION_EVIDENCE_RE,)
                else:
                    authority_expressions = (PUBLICATION_GRANT_RE,)
                authority_matches = [
                    match
                    for expression in authority_expressions
                    for match in unnegated_matches(expression, clause)
                ]
                if any(
                    source.start() < authority.start() < action.start()
                    for source in source_matches
                    for authority in authority_matches
                    for action in action_matches
                ):
                    found.add(label)
                    yield label


def validate_runtime_contract(
    root: Path,
    errors: List[str],
    experience_direction: Optional[str],
    completion_mandate: Optional[str],
) -> None:
    paths = sorted(root.rglob("*.md"))
    texts: List[Tuple[Path, str]] = []
    for path in paths:
        part = read_text(path, errors, root)
        if part is not None:
            texts.append((path, part))
    skill_path = root / "SKILL.md"
    skill_text = next((part for path, part in texts if path == skill_path), "")
    for label, expression in RUNTIME_CONTRACTS:
        if not expression.search(skill_text):
            errors.append("SKILL.md runtime contract missing {}".format(label))

    text_by_relative_path = {
        path.relative_to(root).as_posix(): part for path, part in texts
    }
    for relative_path, label, expression in FILE_RUNTIME_CONTRACTS:
        if not expression.search(text_by_relative_path.get(relative_path, "")):
            errors.append("{} runtime contract missing {}".format(relative_path, label))

    for path, part in texts:
        relative_path = path.relative_to(root)
        if experience_direction is not None and experience_direction in part:
            errors.append(
                "{} copies the literal catalogue experienceDirection into lead-facing prose".format(
                    relative_path
                )
            )
        if completion_mandate is not None and completion_mandate in part:
            errors.append(
                "{} copies the literal catalogue completionMandate instead of adapting it to the subject".format(
                    relative_path
                )
            )
        for label in publication_authority_contradictions(part):
            errors.append(
                "{} contains contradictory remote-publication authority: {}".format(
                    relative_path,
                    label,
                )
            )
        for block in paragraph_blocks(part):
            for label, expression in GUIDANCE_LEAK_DIRECTIVES:
                for match in overlapping_matches(expression, block):
                    if not directive_is_negated(block, match.start()):
                        errors.append("{} contains {}".format(relative_path, label))
                        break


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 1

    root = Path(sys.argv[1]).resolve()
    errors: List[str] = []
    warnings: List[str] = []
    if not root.is_dir():
        print("not a directory: {}".format(root), file=sys.stderr)
        return 1

    for directory in REQUIRED_DIRS:
        if not (root / directory).is_dir():
            errors.append("missing directory: {}".format(directory))
    for file_name in REQUIRED_FILES:
        if not (root / file_name).is_file():
            errors.append("missing file: {}".format(file_name))

    skill_md = root / "SKILL.md"
    if skill_md.is_file():
        skill_text = read_text(skill_md, errors, root)
        if skill_text is not None:
            frontmatter = parse_frontmatter(skill_text)
            if frontmatter.get("name") != root.name:
                errors.append("frontmatter name must be {}".format(root.name))
            description = frontmatter.get("description")
            if not description:
                errors.append("frontmatter description missing")
            elif len(description) > 1024:
                errors.append("frontmatter description exceeds 1024 chars")
            if skill_text.count("\n") + 1 > 500:
                warnings.append("SKILL.md is over 500 lines")

    for markdown in root.rglob("*.md"):
        markdown_text = read_text(markdown, errors, root)
        if markdown_text is None:
            continue
        for reference in local_references(markdown_text):
            target = (root / reference).resolve()
            if root not in target.parents or not target.exists():
                errors.append("{} references missing file: {}".format(markdown.relative_to(root), reference))

    json_files = sorted(root.rglob("*.json"))
    json_data: Dict[Path, Any] = {}
    for json_file in json_files:
        data = read_json(json_file, errors, root)
        if data is not None:
            json_data[json_file] = data

    metadata = json_data.get(root / "metadata.json")
    if isinstance(metadata, Mapping) and metadata.get("version") != PACKAGE_VERSION:
        errors.append("metadata.json version must be {}".format(PACKAGE_VERSION))
    elif metadata is not None and not isinstance(metadata, Mapping):
        errors.append("metadata.json must contain an object")

    catalogue = json_data.get(root / "assets" / "prompt-catalogue.json")
    experience_direction: Optional[str] = None
    completion_mandate: Optional[str] = None
    if catalogue is not None:
        validate_catalogue(catalogue, errors)
        if isinstance(catalogue, Mapping):
            experience_direction = as_text(catalogue.get("experienceDirection"))
            completion_mandate = as_text(catalogue.get("completionMandate"))

    validate_runtime_contract(root, errors, experience_direction, completion_mandate)
    result = {"valid": not errors, "errors": errors, "warnings": warnings}
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
