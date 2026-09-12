# Gotchas

Use this reference for difficult source material and non-obvious failure modes.

## A shorter sentence can be less safe

Splitting a sentence can detach a condition, exception, or consequence from the action it controls.

After splitting, compare:

- condition scope
- negation
- sequence
- threshold polarity
- exception scope
- hazard and mitigation

Restore explicit connectors when the relationship would otherwise be lost.

## A simple synonym can be wrong

STE approval depends on meaning and part of speech, not familiarity. A shorter or more common word is not automatically approved for the intended use.

Verify the dictionary entry. If the dictionary is unavailable, keep the decision unverified.

## Specialized appearance is not terminology evidence

An unfamiliar word is not automatically a technical noun or technical verb. Require a drawing, parts source, specification, glossary, termbase, or terminology owner.

## Long official terms need governed handling

Do not cut a long technical noun into an invented short name. Introduce and shorten it only as the applicable terminology or publication rule permits.

## Passive voice can preserve truth

In descriptions, passive voice can be permitted when the agent is unknown. Do not invent an actor to force active voice.

In procedures, rewrite the instruction directly to the reader. If the real actor is another person or system, preserve that fact.

## `-ing` is not a raw suffix ban

An `-ing` form can have a permitted non-verb role or can occur inside a governed technical noun. Treat scanner matches as candidates and verify function in context.

## Parentheses and quoted text affect word count

Ordinary whitespace counts do not implement the Issue 9 counting rules. Use the official rules for:

- parenthetical text
- quoted text
- identifiers
- numbers with units
- proper nouns
- headings, labels, and placards
- hyphenated words
- vertical lists

The optional scanner gives a conservative estimate and reports this limitation.

## Mixed markup can corrupt protected content

Do not rewrite:

- code fences
- inline code
- shell commands
- URLs and endpoints
- XML or HTML tags
- variables and placeholders
- configuration and schema keys
- quoted output or labels

Rewrite only the surrounding natural-language prose. Compare protected literals character-for-character afterward.

## Selection markers are boundaries

When the user chooses text with markers or a range:

- preserve the markers
- rewrite the complete selected region
- preserve all outside text exactly
- keep headings and block order unless the selection includes them

Do not expand scope because adjacent prose has similar problems.

## Mandated wording can override a language preference

Safety, legal, regulatory, contractual, or publication authorities can control exact wording. Record the conflict and route a candidate replacement to the owner.

Do not change the controlled sentence and call it approved.

## Prior issues can conflict with Issue 9

Do not merge dictionary entries or rules from different issues without explicit authority. Report the source-version conflict and limit the result to one named issue.

## A tool result is not a conformance result

Surface diagnostics can miss:

- wrong approved meanings
- wrong parts of speech
- incorrect technical-term status
- unclear topic progression
- factual errors
- unsafe sequence
- external directive conflicts

They can also flag correct text. Human review against the official standard and governed terminology remains necessary.
