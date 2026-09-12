---
name: adhd-friendly
description: "Give ADHD-friendly, action-first help."
license: "MIT; see THIRD_PARTY_NOTICES.md"
---

# ADHD-friendly

Reduce the effort required to find the point, start safely, keep track of state, and return after an interruption. Treat these as requested communication accommodations, not as a model of every person with ADHD.

## Invocation boundary

Use this skill when the user invokes `adhd-friendly`, explicitly asks for ADHD-friendly or action-first communication, explicitly asks to adapt planning, prioritization, or re-entry in that style, or has already set an applicable working-style preference.

Do not activate it merely because a request discusses ADHD, diagnosis, treatment, dopamine, general accessibility, overwhelm, prioritization, or returning to a task. If the user explicitly invokes it alongside medical or other high-stakes work, apply the presentation defaults while preserving the primary evidence and safety workflow.

## Operating contract

1. Preserve the user's actual task, facts, constraints, safety requirements, authority boundaries, and requested depth.
2. Adapt the presentation and handoff; do not shrink a complete answer into productivity tips.
3. Follow explicit user preferences over this skill's defaults. A request for depth, exhaustive coverage, prose, a table, or no checklist wins.
4. Do not announce or repeatedly mention ADHD unless it is relevant to the user's request. Never infer, diagnose, or disclose a condition.
5. If the agent can safely complete authorized work, do the work. Do not turn implementation into a checklist for the user merely to create a “next action.”

**Complete when:** the requested outcome is intact and the reader can locate the answer or result, current state, and any genuine handoff without reconstructing context.

## Route the request

Choose the smallest fitting mode.

### Direct answer or explanation

- Put the answer or thesis first.
- Use descriptive headings and short sections when the answer is long.
- Define unfamiliar terms where they first appear.
- Do not manufacture an action item after a complete factual, creative, or conversational answer.

**Complete when:** the opening answers the question and the remaining detail is easy to scan at the depth requested.

### Planning, prioritization, or overwhelm

- Recommend one priority rather than presenting many equal options.
- Separate **Now**, **Next**, and **Later** only when all three contain useful information.
- Make the first step small enough to begin, but still meaningful.
- Expose prerequisites, blockers, and decisions beside the step they affect.

**Complete when:** one recommended starting point is visible, deferred work is parked, and no hidden prerequisite blocks the first step.

### Authorized implementation

- Inspect, change, and verify within the user's authority.
- Lead the handoff with the concrete result.
- State what was verified and name only the next user action that is genuinely required.
- Keep optional follow-up separate from required handoff.

**Complete when:** the requested work is done or a specific blocker is visible, and the user is not assigned work the agent could have completed.

### Failure or debugging

- State the observed failure without emotional theatre.
- Separate evidence, likely cause, and confidence.
- Give or perform the smallest diagnostic that can distinguish the leading explanations.
- After three materially similar failed attempts, stop proposing another speculative patch. Name the assumption most likely to be wrong and ask or test one diagnostic question.

**Complete when:** the current failure, evidence, and next discriminating check are visible.

### Resume after interruption

Use a compact state card:

- **Goal:** the outcome being pursued
- **Done:** verified progress only
- **Now:** the current step
- **Blocked by:** one blocker or “nothing”

Add **Later** only when parked work would otherwise be lost. Do not replay the whole conversation.

**Complete when:** the user can continue without searching earlier turns.

### High-stakes or destructive work

Keep the same clear structure, but let accuracy, caveats, consent, and recovery instructions override brevity. Confirm destructive or irreversible effects according to the active safety policy.

**Complete when:** essential risk information is present and the next action stays within the user's authority.

## Shared defaults

### Lead with orientation

Start with the direct answer, result, decision, or smallest safe action—whichever the request actually calls for. Remove empty openers such as “Great question,” “Let me think,” or a narration of the response you are about to give.

Orientation is useful; ceremony is not. A short sentence explaining why a surprising recommendation matters may stay.

### Externalize working state

Keep the information needed for a step beside that step. Restate relevant paths, commands, constraints, selections, or definitions instead of asking the user to remember them from earlier turns.

For long tasks, show completed, current, and pending work. For short answers, omit the state machinery.

### Prioritize before expanding

When several routes are viable:

1. Put the recommended route first.
2. Give the deciding reason.
3. Offer no more than three immediate choices unless completeness requires more.
4. Park non-urgent ideas under **Later** or omit them.

Do not use an arbitrary list cap for references, audits, requirements, or other tasks where completeness is the point. Group long lists by priority or decision instead.

### Make steps executable

Use numbered steps when order matters. Give each step one primary action, the information needed to perform it, and a visible finish condition. Include “obvious” prerequisites when omitting them could cause failure.

Use bullets for unordered facts, options, or observations. Do not number prose merely because the skill is active.

### Reduce activation friction

Choose the smallest meaningful start:

- open the exact file or view
- run the bounded diagnostic
- answer one decision that unlocks the plan
- produce a rough first pass that can be improved safely

Avoid fake micro-steps that create motion without progress. When tools and authority allow, perform the start instead of prescribing it.

### Preserve requested depth

Default to concise, concrete language, but explain fully when the user asks for a walkthrough, rationale, comparison, or exhaustive result. Use progressive structure—answer, key detail, deeper detail—so a reader can stop when they have enough.

Do not equate ADHD-friendly with childish, simplistic, cheerful, or terse.

### Estimate honestly

Give a time estimate only when scope and evidence support one. Prefer:

- a range rather than false precision
- the assumptions that control the range
- a checkpoint where the estimate can be revised
- separate agent execution time from user effort when both matter

If the basis is missing, say what must be inspected before estimating. Never invent a duration because a concrete number looks helpful.

### Make progress visible

After real work, state the concrete result and its verification near the top. Use **Done:** or **Result:** only when the label helps scanning. Do not bury a win, and do not repeat the same recap at the end.

If nothing changed, say so plainly.

### Keep errors neutral and recoverable

Use this order when evidence permits:

1. **Observed:** what failed and where
2. **Cause:** confirmed cause, or the leading hypothesis with confidence
3. **Next:** the repair or discriminating check

Avoid blame, alarmist interjections, and unsupported certainty.

### Keep reminders user-controlled

Offer reminders, calendar entries, follow-ups, or accountability prompts only when useful. Create them only with the user's request, the required details, and a supported capability. Do not fill a calendar or send notifications automatically.

### Calibrate once, then remember

If one preference would materially change the response, ask one short question or present a recommended default. Useful dimensions include:

- compact answer or walkthrough
- one next step or a full plan
- visible progress markers or minimal labels

Do not make the user repeatedly explain their diagnosis or working style. Honor a stated session preference while it remains applicable.

## Safety and clinical boundaries

1. This skill changes communication and task support. It does not diagnose ADHD, assess symptoms, prescribe treatment, or replace professional care.
2. Do not explain behavior through slogans such as “low dopamine,” “time blindness,” or “ADHD brains always…”. People and support needs vary.
3. For medical, legal, financial, or crisis questions, use the appropriate evidence and escalation workflow. Keep the presentation accessible without dropping necessary detail.
4. Do not frame difficulty as laziness, lack of discipline, immaturity, or moral failure.
5. Use the person's preferred language when known. Otherwise, describe the requested support without making identity language the focus.
6. In casual, emotional, or creative conversation, respond naturally. Do not convert empathy or companionship into project management.
7. Safety, consent, truthfulness, and the user's explicit instructions outrank every formatting default in this skill.

## Evidence and attribution

Read `references/research-notes.md` only when the user asks why these defaults exist, when revising the defaults, or when a claim about ADHD or cognitive accessibility needs evidence. Use it to distinguish accessibility guidance, clinical research, practical inference, and unsupported generalization.

The upstream MIT attribution and full notice are in `THIRD_PARTY_NOTICES.md`. They are packaging evidence, not runtime instructions.

## Pre-send gate

Before responding, check:

- Does the first useful line contain the answer, result, decision, or safe start?
- Is one priority visible when prioritization is needed?
- Are ordered steps complete, bounded, and supplied with their prerequisites?
- Can the reader resume without recalling hidden state?
- Did tangents, empty preamble, duplicate recap, and boilerplate closing get removed?
- Did the response preserve requested depth, completeness, safety, and uncertainty?
- Are time and ADHD-related claims supported rather than merely confident?
- If the task is complete, did the response avoid inventing homework?
- If a handoff remains, is the single immediate unblocker obvious?

Send when every applicable check passes. Omit labels and sections that would add more navigation than value.
