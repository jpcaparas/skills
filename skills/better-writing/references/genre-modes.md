# Genre modes

Choose the page shape from the reader's task. Sentence style cannot rescue the wrong genre.

## Quick chooser

| Reader task | Mode |
|---|---|
| Finish a technical task | guide, tutorial, or runbook |
| Find a fact quickly | reference documentation |
| Understand a system or trade-off | explanation or deep dive |
| Review a code change | pull request description |
| Decide what to build | product brief or specification |
| Record a durable technical choice | decision record or proposal |
| Make a business decision | memo or executive brief |
| Assess evidence and implications | report or analysis |
| Follow a person making meaning | essay or reflection |
| Decide whether to act or buy | landing or product page |
| Complete a small interaction | UI copy, error, or notification |
| Respond or coordinate | email, update, or release note |

## Guide, tutorial, or runbook

Reader needs: a finish line, prerequisites, ordered steps, exact artefacts, and verification.

Shape:

1. state what the reader will accomplish
2. list genuine prerequisites and starting state
3. give steps in executable order
4. explain only where explanation prevents error or supports transfer
5. show expected result and verification
6. add recovery or troubleshooting for likely failures

Protect commands, paths, identifiers, versions, and expected output. Never invent a missing step from convention.

Ending: verified success, rollback or recovery, then the next useful action.

Red flags: conceptual preamble before the task; hidden assumptions; magical placeholders; no check for success.

## Reference documentation

Reader needs: fast retrieval, completeness within scope, stable terminology, and edge conditions.

Shape:

- one entity or operation per section
- predictable headings
- signatures, fields, inputs, outputs, defaults, errors, and examples
- cross-links based on likely lookup paths

Do not turn reference into a tutorial. Keep examples exact and label pseudocode.

Ending: usually none; add related references, not a ceremonial conclusion.

## Explanation or deep dive

Reader needs: a mental model, mechanism, trade-offs, and consequences.

Shape:

1. name the central confusion or question
2. give the smallest useful model
3. develop one sub-question per section
4. use examples to dissolve confusion
5. compare alternatives where the difference changes a decision
6. end with the model's practical implication or boundary

Red flags: tutorial steps mixed into conceptual explanation; fact dump without a through-line; analogy replacing mechanism.

## Pull request description

Reviewer needs: what changed, why, behaviour, risk, verification, and rollout notes.

Shape:

- summary of the problem and change
- key implementation choices, not a file-by-file diary
- user-visible or operational impact
- tests actually run
- risks, migrations, feature flags, compatibility, and follow-up

Keep identifiers and commands exact. Do not claim tests, metrics, or compatibility checks that did not run.

Ending: the reviewer decision or special attention needed.

## Product brief or specification

Reader needs: the problem, affected users, desired outcome, boundaries, behaviour, and acceptance evidence.

Shape:

1. problem and evidence
2. users and jobs
3. outcome and success measures
4. scope and non-goals
5. behaviour, states, and edge cases
6. dependencies and risks
7. acceptance criteria and open decisions

Separate observed user need from proposed solution. Use `must`, `should`, and `may` consistently if requirements language is in scope.

Ending: unresolved decisions, owner, and next checkpoint.

## Decision record or proposal

Reader needs: context, options, decision, rationale, and consequences.

Shape:

- current state and forcing constraint
- decision criteria
- viable options and trade-offs
- recommendation or recorded decision
- consequences, reversibility, migration, and review date

Do not create false balance. Omit options that were never viable; include a rejected option when its rejection teaches a future reader something important.

Ending: decision status and follow-up conditions.

## Memo or executive brief

Reader needs: the point quickly, evidence that changes the call, and a decision or recommendation.

Shape:

1. thesis or decision in the first screen
2. what changed and why now
3. only the evidence material to the call
4. risks and counterarguments
5. recommendation, owner, or decision question

Use claim-driven headings. Bullets should compress trade-offs or actions, not decorate the page.

Red flags: scene-setting before the point; safe summary without a position; recommendation detached from evidence.

## Report or analysis

Reader needs: a trustworthy fact pattern, method or provenance, interpretation, and limits.

Shape:

- question and scope
- method, source, and limitations
- findings in an order that supports comprehension
- interpretation separated from observation
- implications proportionate to evidence

Attribute contested claims and preserve uncertainty. Put numbers before evaluative adjectives.

Ending: supported implication, decision, or open question—not a sermon.

## Essay or reflection

Reader needs: a person worth following, a live tension, and movement in understanding.

Shape may braid:

- scene or image
- reflection
- evidence or research
- reversal, complication, or return

The specific earns the universal. Research should change the narrator's understanding rather than decorate it.

Ending: an outward turn, changed image, or earned unresolved question.

Red flags: thesis paragraph wearing memoir clothes; invented intimacy; vulnerability that changes nothing; tidy life lesson.

## Landing or product page

Reader needs: a clear offer, relevance, proof, reduced uncertainty, and one main action.

Shape:

1. outcome and audience
2. problem or constraint in customer language
3. benefits tied to mechanisms
4. proof near the claim
5. objections, boundaries, comparison, or risk reduction
6. one primary call to action

Do not fabricate testimonials, metrics, customer language, or market position.

Ending: direct action and what happens next.

Red flags: several audiences with equal weight; praise without mechanism; features mistaken for benefits; generic `learn more` action.

## UI copy, error, or notification

Reader needs: orientation, consequence, and recovery in very little space.

For labels and buttons:

- name the action or destination
- keep terms consistent with the product
- avoid cleverness that slows recognition

For errors:

1. say what happened in user language
2. explain consequence if it is not obvious
3. give a safe recovery action
4. preserve useful diagnostic detail without exposing secrets

For destructive or irreversible actions, state the object and consequence before confirmation.

Red flags: blaming the user; `Something went wrong` with no recovery; success messages that merely say success; buttons labelled `OK` when a real action name fits.

## Email or coordination note

Reader needs: purpose, enough context, one clear ask or update, and timing.

Shape:

- purpose in the first one or two lines
- context only where it changes the response
- one primary ask, decision, or update
- owner and deadline when relevant

Ending: explicit next action or a natural courtesy.

Red flags: generic greeting theatre; buried ask; several unrelated requests; memo-length scene-setting.

## Release note or changelog entry

Reader needs: what changed, who is affected, whether action is required, and where to learn more.

Shape:

- user-visible change
- reason or benefit
- migration, compatibility, or action required
- known limitation
- relevant link

Do not copy commit messages verbatim. Translate implementation into user consequence without inventing a benefit.

## Genre gate

The page shape is right when:

- the opening gives the reader the orientation this mode requires
- the middle follows the mode's natural unit: steps, entities, claims, decisions, scenes, or interactions
- proof and explanation appear where the reader needs them
- the ending performs a real task rather than summarising by habit
- a reader would recognise the artefact without seeing its filename
