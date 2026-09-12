# Gotchas

These are the mistakes that quietly erase the gains from a compact workflow.

## 1. `rg` missed the file

Symptom: the pattern is obviously present, but `rg` returns nothing.

Cause: hidden files, ignore rules, or the wrong root path.

Fix:

```bash
rg -n -F 'needle' path/
rg --hidden -n -F 'needle' path/
rg -u -n -F 'needle' path/
rg --debug -n -F 'needle' path/
```

## 2. `tree` turned a simple check into a wall of output

Symptom: the tree view is longer than the part of the repo you actually care about.

Cause: uncapped depth or a root path that is too broad.

Fix: cap depth early and use a narrower root. Prefer `rg --files` when you need filenames, not hierarchy.

## 3. Over-optimizing file reads

Symptom: five separate excerpts got opened from the same 35-line file.

Cause: blindly avoiding `cat` even after the exact short file was identified.

Fix: once the file is known, short, and central, a full read is cheaper than repeated slicing.

## 4. `git diff --stat` looked harmless but the logic was risky

Symptom: the summary shows only a few lines changed, but behavior still feels uncertain.

Cause: stats compress volume, not meaning.

Fix: inspect the affected path directly:

```bash
git diff -- path/to/file
git diff --cached -- path/to/file
```

## 5. `git add .` staged too much

Symptom: unrelated files ended up in the commit.

Cause: convenience won over scope discipline.

Fix:

```bash
git add -- path/to/file
git diff --cached --stat
git diff --cached -- path/to/file
```

## 6. `git push -u origin HEAD` failed

Symptom: push failed even though the commit exists locally.

Cause: no `origin`, detached `HEAD`, or a repository policy issue.

Fix: inspect the remote and branch situation first:

```bash
git remote -v
git branch --show-current
```

Then decide whether `HEAD` is still the right push target.

## 7. `npm test` ignored the runner flags

Symptom: the extra arguments never reached Jest, Vitest, or the underlying runner.

Cause: forgetting the `--` separator after `npm test`.

Fix:

```bash
npm test -- --runInBand
```

## 8. `docker ps` showed a container, so everything looked healthy

Symptom: the service is listed, but the actual app is broken.

Cause: process presence is not service health.

Fix: inspect the formatted `Status` field or move to a deeper container-specific health check only after `docker ps` establishes the inventory.

## 9. Machine-readable output was available but ignored

Symptom: a human-readable table had to be manually summarized or copied into another command.

Cause: default output was accepted even though structured output existed.

Fix: prefer `--json`, `--format '{{json .}}'`, or `jq -r` when another tool or script will consume the result.
