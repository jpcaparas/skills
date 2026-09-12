# Blueprints

## Table of Contents

- [API Wrapper Blueprint](#api-wrapper-blueprint)
- [CLI Tool Blueprint](#cli-tool-blueprint)
- [Progressive Docs Blueprint](#progressive-docs-blueprint)
- [Skill Library Curation Blueprint](#skill-library-curation-blueprint)

---

## API Wrapper Blueprint

### When to Use

Use this blueprint when wrapping a REST API, GraphQL API, SDK, or another documented programmatic contract into a skill. The skill will help agents perform promised operations with the contract's real access, input, output, and failure semantics.

**Indicators:** The source material documents callable operations, their inputs and outputs, and their failure contract. The skill must produce working invocations through the selected client or protocol.

### Required Research Phase

Before writing a single line of the skill, gather:

1. **Access pattern, when required**
   - Identify the credential, identity, session, or local setup the selected contract actually requires
   - Distinguish server, client, delegated-user, and unauthenticated branches only when the promised operations expose them
   - Record where access material enters the invocation and how examples avoid disclosing it

2. **Contract location and versioning**
   - Identify the endpoint, schema, package, client, or other surface that owns each promised operation
   - Determine how that surface selects a version or dated contract, if it does
   - Record what the provider documents about unsupported or superseded versions
   - Pin the exact version or dated contract when the provider exposes one. If the service has no pinnable version, record the retrieval date and revalidation path instead of inventing stability.

3. **Promised-operation inventory** -- scope it to the invocation contract
   - List only the operations the skill promises to perform or route to
   - Group those operations by the user's goal rather than copying the provider's entire API index
   - Include lifecycle, search, admin, webhook, or asynchronous operations only when a promised branch needs them
   - Record important nearby operations as explicit non-goals when omitting them could mislead a consumer

4. **Traversal, when a promised operation returns partial collections or graphs**
   - Identify the continuation mechanism used by the selected contract
   - Record default and maximum batch sizes only when the provider defines them
   - Define termination, duplicate, ordering, and resume behavior needed by the promised workflow

5. **Limits, when remote or metered operations are promised**
   - Identify applicable rate, concurrency, payload, usage, or quota limits
   - Record how the selected contract communicates exhaustion or backpressure
   - Distinguish retryable from terminal outcomes using provider evidence

6. **Failure contract**
   - Document only the statuses, error payloads, exceptions, result variants, or callback failures the selected surface exposes
   - Preserve provider-specific error identifiers when they change recovery behavior
   - Determine whether an operation is safe to retry and whether the contract supports idempotency or deduplication

7. **Client or protocol selection**
   - Compare supported clients and direct protocol access only when more than one surface can satisfy the promised operation
   - Confirm the chosen surface is current for the target runtime or environment
   - Record which access, traversal, resilience, or serialization behavior the client handles automatically

8. **Gotchas** -- use primary documentation and the safest authorized verification rung to discover contract-specific traps. Depending on the selected surface, these may involve encoding parameters, request metadata, identifier spelling, absent-versus-empty values, expansion controls, callback ordering, or client-side defaults. Include only details evidenced for a promised operation.

### Illustrative Directory Structure

```
api-skill/
├── SKILL.md
├── references/       # Only the earned files below
│   ├── api.md        # Promised operation contract
│   ├── patterns.md   # Supported multi-step or resilience workflows
│   ├── configuration.md
│   └── gotchas.md
└── evals/
    └── evals.json
```

### Entry-Point Contract

Start from `templates/api-wrapper/SKILL.template.md`, then remove every branch and support surface the promised operations do not earn. Keep shared authentication and safety constraints inline. Route operation details, setup, workflows, and evidenced pitfalls through condition-and-purpose pointers only when those files exist. Add a verification script only when a safe reusable probe exists and its runtime is supported in the declared target environment.

### Reference File Organization

- **api.md**: One section per promised operation group. Each operation gets its contract identifier or signature, required and optional inputs, output and failure shape, and a verified invocation through the selected surface.
- **patterns.md**: Numbered workflow sections for the multi-step, asynchronous, traversal, event, or resilience flows the skill actually promises.
- **configuration.md**: Only the access, identity, dependency, environment, or client setup that promised operations require.
- **gotchas.md**: Evidenced entries with symptom, cause, and fix. Merge new evidence into the canonical rule and remove superseded wording.

### Verification Checklist

- [ ] Each claimed operation maps to current primary documentation
- [ ] Required access is confirmed against the selected contract; a live non-mutating probe is used only when credentials and authority permit it
- [ ] Every operation-map row has matching contract evidence and routed detail where detail is needed
- [ ] Any promised traversal documents its continuation and termination behavior
- [ ] Failure handling covers the outcomes and provider-specific identifiers the selected surface can return for promised operations
- [ ] Applicable limits are documented with a primary source or explicitly bounded observation
- [ ] A recommended client or package has a supported version or dated evidence
- [ ] Every invocation example includes the context required by its selected surface

---

## CLI Tool Blueprint

### When to Use

Use this blueprint when wrapping a command-line tool into a skill. The skill will help agents invoke the tool with its verified command hierarchy, options, inputs, outputs, and completion semantics in the promised environments.

**Indicators:** The user mentions a CLI tool by name. The source material is built-in help, manuals, generated command metadata, or primary CLI documentation. The skill must produce correct invocations for a named shell, process API, or command environment.

### Required Research Phase

1. **Subcommand discovery**
   - Use the tool's documented help or command-introspection mechanism and capture the relevant output
   - Inspect every subcommand or operation the skill promises to use
   - Identify the command hierarchy, including nested groups when present
   - Group commands by the user's goal rather than an assumed operation taxonomy

2. **Flag documentation**
   - Required vs optional flags per subcommand
   - Short vs long flag forms (`-v` vs `--verbose`)
   - Flags that take arguments vs boolean flags
   - Mutually exclusive flags
   - Global flags vs subcommand-specific flags
   - Default values for optional flags

3. **Version pinning**
   - Use the tool's documented version or build-identification mechanism and record the output
   - Check if flag syntax changed between versions (common source of broken examples)
   - Document the minimum supported version
   - If the tool auto-updates, note this in gotchas

4. **Execution-environment compatibility**
   - Identify the shells, operating systems, terminals, CI runners, or embedded environments promised by the skill
   - Verify quoting, escaping, path, and environment-variable behavior in each supported environment
   - Record stdin, stdout, stderr, and pipeline behavior only where the command map relies on it

5. **Output and completion contract**
   - Identify the actual human-readable and machine-readable formats the promised commands expose
   - Record the selector for a structured format only when the tool provides one
   - Distinguish stable machine output from presentation output before recommending parsing
   - Document the exit status, result object, or other completion signal used in each supported environment

### Illustrative Directory Structure

```
cli-skill/
├── SKILL.md
├── references/       # Only the earned files below
│   ├── commands.md   # Promised command surface
│   ├── patterns.md   # Supported multi-step workflows
│   ├── configuration.md
│   └── gotchas.md
└── evals/
    └── evals.json
```

Add `scripts/` only when a reusable check is safer than repeated ad hoc commands and its runtime is part of the declared target environment. Do not assume POSIX shell availability merely because the wrapped tool is a CLI.

### Entry-Point Contract

Start from `templates/cli-tool/SKILL.template.md`, then keep only the commands and routes promised by the invocation contract. Put the supported version or compatibility range, non-destructive defaults, and shared output expectations inline. Route command details, setup, workflows, and evidenced quirks to files that exist.

### Reference File Organization

- **commands.md**: One section per promised command group, with its verified synopsis, options, example, and result contract.
- **patterns.md**: Multi-step workflows and composition patterns supported by the selected execution environments.
- **configuration.md**: Only the installation, identity, configuration, completion, or environment setup the promised commands require.
- **gotchas.md**: Evidenced environment, quoting, version, option, result, and failure traps.

### Verification Checklist

- [ ] The documented command surface matches current help or primary documentation for the supported version or range
- [ ] Every command-map row is checked with current primary help or documentation, parsing, a documented preview, a disposable workspace, or another safe applicable rung
- [ ] Flag syntax is correct for the documented version (short and long forms)
- [ ] Any promised output selector is documented and tested
- [ ] Each documented installation path works in its supported environment
- [ ] Quoting and escaping are correct for every environment shown in examples
- [ ] Completion signals distinguish success from the failure outcomes the command map promises to handle

---

## Progressive Docs Blueprint

### When to Use

Use this blueprint for large reference skills covering many domains, products, or topics. The skill's primary value is organizing knowledge for efficient retrieval rather than wrapping a single API or tool.

**Indicators:** The subject has several distinct user goals or domains. No single API or CLI owns the whole job, and different invocations should load different reference material.

### Required Research Phase

1. **Domain mapping**
   - List every product, topic, or area promised by the invocation contract
   - Group by category (compute, storage, networking, security, etc.)
   - Identify cross-cutting concerns (auth, billing, monitoring) that span domains
   - Determine which material every branch shares and which material is branch-only

2. **Decision trees**
   - How does a user choose between products? (What question do they start with?)
   - Build a tree from the user's goal to the specific product
   - Multiple trees may be needed (by task, by scale, by cost, by feature)

3. **Access pattern**
   - Keep a flat peer set together when every invocation needs it
   - Use hub-and-spoke references when branches share a small core
   - Use repeated domain directories only when domains share the same real access surfaces
   - Compose multiple skills when jobs need independent invocation

4. **Cross-referencing plan**
   - Which domains reference each other?
   - Map useful transitions before writing
   - Point directly to the file that completes the current decision; avoid cycles or breadcrumb chains that make the reader assemble one answer across unrelated files

### Directory Structure

For domains that genuinely share setup, API, pattern, and gotcha access:

```
docs-skill/
SKILL.md
references/
  domain-a/
    README.md
    api.md
    patterns.md
    configuration.md
    gotchas.md
  domain-b/
    README.md
    api.md
    patterns.md
    configuration.md
    gotchas.md
  shared/
    auth.md
    conventions.md
evals/
  evals.json
```

Omit empty support files and directories. Decompose into a skill family only when the jobs need independent reachability, not at an arbitrary domain count.

### Entry-Point Contract

Start from `templates/progressive-docs/SKILL.template.md`, then model the real user branches rather than a product-count taxonomy. Keep shared selection rules inline. Add indexes, shared references, or repeated domain surfaces only when they shorten a demonstrated retrieval path.

### The 5-File Reference Structure

This optional layout offers up to five familiar surfaces (see `references/patterns.md` for details):

1. **README.md** -- overview, when to use, quick start, "See Also" links
2. **api.md** -- API reference (endpoints, methods, types, schemas)
3. **patterns.md** -- common workflows and integration patterns
4. **configuration.md** -- setup, config files, environment variables
5. **gotchas.md** -- pitfalls, limits, tribal knowledge

Create only surfaces that carry useful content. An empty or invented gotchas file is worse than a smaller honest structure.

### Cross-Referencing

- Add related-domain links only when the transition supports a realistic task
- Point to the file that answers the next question instead of forcing traversal through an index
- Keep each decision's rule, caveat, and example together; a reference may link onward for a separate decision
- Detect cycles that strand the reader or duplicate routing, but do not impose a numeric hop limit on a useful graph

### Verification Checklist

- [ ] Every routed branch points to an existing reference entry
- [ ] Every reference directory contains only earned, routed files
- [ ] Every branch has one owner, with precedence stated where overlap is unavoidable
- [ ] Cross-references resolve to real files
- [ ] Each branch reaches the material needed to complete its task without unrelated traversal
- [ ] Shared conventions remain inline or in a routed shared file according to actual branch use
- [ ] Any product index is complete for the promised scope and matches the directory structure
- [ ] Total SKILL.md is under 500 lines

---

## Skill Library Curation Blueprint

### When to Use

Use this blueprint when adding, improving, merging, promoting, renaming, moving, deprecating, or removing skills in an established collection.

Use `references/curation.md` as the canonical workflow. The matrix below records only the transition-specific evidence needed in addition to that shared process.

### Required Discovery

1. Read repository policy and discover its actual lifecycle states.
2. Inventory canonical skills, invocation descriptions, adjacent owners, wrappers, catalogs, registries, routers, installers, dependents, and evals.
3. Decide create, improve, merge, compose, or retire before editing.
4. Build an affected-surface ledger for every governed projection of the canonical skill.
5. Find the repo-native validation and fresh discovery commands.

### Change Matrix

| Transition | Required evidence |
|---|---|
| Create | A distinct invocation branch, no better existing owner, release evals, all active surfaces updated |
| Improve | Every old behavior accounted for, canonical rule updated in place, regressions covered |
| Merge | Trigger ownership resolved, dependents migrated, duplicate package and routes removed |
| Compose | Each child remains independently discoverable; dependency resolution and dependent revalidation pass |
| Promote | Release validation and behavioral evals pass; every active discovery surface includes it |
| Rename or move | Canonical path, wrappers, dependents, registries, routers, tests, and stale-name search agree |
| Deprecate or remove | Replacement or rationale recorded; active discovery and dependents reconciled |

## See Also

- `references/patterns.md` — branch ledgers, earned structure, and composition decisions
- `references/testing.md` — release, trigger, disclosure, and curation eval design
