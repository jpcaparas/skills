# Research notes

Use this reference to explain or revise the skill's defaults. Do not turn the research into a claim that every person with ADHD has the same needs.

## Evidence model

Keep four kinds of support distinct:

1. **Accessibility guidance** identifies broadly useful design patterns for people with cognitive, learning, memory, or attention barriers.
2. **Clinical guidance and studies** support professional interventions or describe average group differences. They do not prove that one response format treats ADHD.
3. **Practical inference** adapts those patterns to agent communication, such as keeping current state beside the next step.
4. **Personal preference** outranks a population-level default for an individual user.

This skill is a communication accommodation. It is not a clinical intervention.

## Strong foundations

### Clear, separated steps

W3C cognitive-accessibility guidance recommends clear instructions located near the activity, complete step sequences, concise wording, and examples when they help. Its separate-instruction guidance notes that numbered, clearly separated steps reduce the need to divide and track a procedure in working memory.

- [Use Clear Step-by-step Instructions](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o4p07-step-instructions/)
- [Separate Each Instruction](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o3p09-separated-instructions/)
- [Do Not Rely on Users Calculations or Memorizing Information](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o6p05-low-cognition/)

**Skill implication:** number ordered work, keep prerequisites with the step, and avoid instructions that depend on recall from an earlier turn.

### Visible position and re-entry

W3C recommends showing completed, current, and pending steps so users can reorient after distraction without restarting. Its focus guidance also recommends clear headings, short critical paths, fewer distractions, and preparation information at the start of a task.

- [Make Each Step Clear](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o1p04-clear-steps/)
- [Help Users Focus](https://www.w3.org/WAI/WCAG2/supplemental/objectives/o5-user-focus/)
- [Limit Interruptions](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o5p01-minimal-interruptions/)

**Skill implication:** use compact progress state for long or resumed tasks, suppress unsolicited tangents, and omit progress machinery from short answers.

### Organization, planning, and time-management support

NICE recognizes that ADHD may affect organization, time management, motivation, and adherence, while emphasizing individual goals, strengths, environmental modifications, and shared decisions. Randomized and meta-analytic evidence supports structured cognitive-behavioral approaches for some adults with ADHD, including organization, planning, and time-management skills.

- [NICE NG87 recommendations](https://www.nice.org.uk/guidance/ng87/chapter/recommendations)
- [Adult ADHD CBT systematic review and meta-analysis](https://pubmed.ncbi.nlm.nih.gov/27554190/)
- [Metacognitive therapy randomized trial](https://pubmed.ncbi.nlm.nih.gov/20231319/)
- [CBT model for adults with ADHD](https://pmc.ncbi.nlm.nih.gov/articles/PMC3874265/)

**Skill implication:** externalize plans and priorities, but do not describe the skill as therapy or claim that a formatting pattern treats symptoms.

### Heterogeneity and working memory

A meta-analysis reports average working-memory differences in adults with ADHD, with variation across people and tasks. NICE likewise centers individual goals and circumstances.

- [Adult ADHD working-memory meta-analysis](https://pubmed.ncbi.nlm.nih.gov/23688211/)
- [NICE NG87 recommendations](https://www.nice.org.uk/guidance/ng87/chapter/recommendations)

**Skill implication:** reduce unnecessary memory demands while making every default overridable. Do not state that a user's working memory is “small.”

### Time estimates

Research reports group-level time-perception differences in ADHD, but this does not make “time blindness” a universal trait or justify fabricated estimates.

- [ADHD time-perception meta-analysis](https://pubmed.ncbi.nlm.nih.gov/38145491/)

**Skill implication:** use grounded ranges, assumptions, and checkpoints. Concrete but unsupported numbers are less trustworthy than an explicit unknown.

### Reminders and user control

W3C recommends making reminders easy to set for time-sensitive events, while stating that reminders should be user-requested and personalized because unwanted reminders can become another barrier.

- [Provide Reminders](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o7p07-reminders/)

**Skill implication:** offer reminder support where useful; never create reminders or notifications without authority and the required details.

### Neutral, preference-aware language

NICE discusses stigma and labeling and recommends shared, individualized support. NIH writing guidance recommends destigmatizing language and respecting stated preferences.

- [NICE NG87 recommendations](https://www.nice.org.uk/guidance/ng87/chapter/recommendations)
- [NIH person-first and destigmatizing language](https://www.nih.gov/nih-style-guide/person-first-destigmatizing-language)

**Skill implication:** avoid blame and biological clichés, do not infer a diagnosis, and follow the user's preferred identity language when known.

## Useful but opt-in practices

Timers, body doubling, rewards, gamification, recurring check-ins, and extremely small “starter steps” may help some people. The sources above do not establish them as universally effective agent behaviors.

Offer these as optional tools only when they fit the user's context. Do not explain them through simplified dopamine claims, impose accountability, or create monitoring the user did not request.

## Upstream adaptation

This skill substantially adapts [`ayghri/i-have-adhd`](https://github.com/ayghri/i-have-adhd) at commit [`72c33eee81ea439cf01991e93729adfce2ffc99e`](https://github.com/ayghri/i-have-adhd/tree/72c33eee81ea439cf01991e93729adfce2ffc99e). The full MIT notice and the preserved/changed behavior summary are in `THIRD_PARTY_NOTICES.md`.

## Portability basis

The portable package follows the [Agent Skills specification](https://agentskills.io/specification): `SKILL.md` owns the behavior, `name` and `description` define discovery metadata, and relative references stay inside the package. Harness-specific invocation flags are deliberately absent.
