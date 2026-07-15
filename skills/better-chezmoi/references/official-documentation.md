# Official documentation corpus

Use this reference when a command or flag is version-sensitive, the bundled snapshot needs refreshing, or the user wants official chezmoi documentation searched locally.

## Authority order

1. Installed `chezmoi <command> --help` for executable syntax on the current machine.
2. Live official pages at `https://www.chezmoi.io/` for current behavior and examples.
3. Official GitHub release notes for a newly introduced or changed flag.
4. Bundled snapshot for fast offline search and branch-specific context.

The snapshot is evidence retrieved at a point in time, not a version lock. Preserve retrieval metadata and source URLs in `references/official-docs/manifest.json`.

## Search the bundled snapshot

```sh
python3 scripts/official_docs.py search "dry-run"
python3 scripts/official_docs.py search "persistent state lock" --limit 20
python3 scripts/official_docs.py list
```

Search output names the page and line number. Open only the matching snapshot file, then confirm exact flags against local help.

## Compare with live official pages

```sh
python3 scripts/official_docs.py refresh
```

This fetches the curated official page set into a temporary staging directory, validates every article, compares content hashes with the committed corpus, and reports added, changed, removed, and unchanged pages. It does not replace the snapshot.

Use `--output PATH` to compare against another corpus. Network or HTTP failure is an operational failure, not evidence that the existing snapshot is current.

## Publish a refresh

```sh
python3 scripts/official_docs.py refresh --write
python3 scripts/official_docs.py check
```

`--write` stages and validates the complete corpus, moves the prior directory to a recovery backup, publishes the staged directory, and restores the backup if publication fails. It refuses a partial fetch. Review the resulting diff for lost headings, examples, source URL changes, and unexpectedly large churn before release.

Publishing the default installed snapshot can fail on a read-only installation. In that case, use `--output` with a writable directory and search it through `--docs`.

## Change the page set

The typed `DOCUMENT_SOURCES` tuple in `scripts/official_docs.py` owns the page inventory. Add a page only when a real invocation branch needs it. Each source needs a stable slug, one official HTTPS URL, and a branch label.

After changing the inventory:

1. run `refresh --write`
2. run `check`
3. run the package validator and tests
4. update disclosure evals if a new branch becomes reachable

## Scraper boundaries

- Uses only Python's standard library and official `chezmoi.io` HTTPS pages.
- Extracts the `<article class="md-content__inner md-typeset">` region and produces Markdown-like text optimized for local search.
- Preserves headings, paragraphs, links, lists, tables as readable rows, and preformatted command blocks.
- Records SHA-256 hashes and sitemap `lastmod` values where available.
- Does not execute code examples, invoke chezmoi, follow arbitrary off-site links, or scrape search results.

## Completion checks

- Every configured page has a non-empty generated file and matching manifest hash.
- The manifest records retrieval time, source URL, branch, output path, and site last-modified value when published.
- Live refresh either passes completely or leaves the prior corpus byte-for-byte intact.
- Exact commands remain checked against the installed binary.

## Sources

- [Official sitemap](https://www.chezmoi.io/sitemap.xml)
- [Official command reference](https://www.chezmoi.io/reference/commands/)
- [Official user guide](https://www.chezmoi.io/user-guide/)
- [Official releases](https://github.com/twpayne/chezmoi/releases)

## See also

- `references/commands.md` for local/current version boundaries
- `references/daily-workflows.md` for curated daily use
