# Procedures and safety instructions

Use this reference for work steps, maintenance tasks, notes inside procedures, warnings, cautions, and other risk instructions.

## Procedure contract

A procedure tells the reader what to do. Preserve the task’s real execution order and prerequisites.

For each source step, identify:

- prerequisite state
- actor when the source names one
- action
- object
- location
- method or tool
- quantity, limit, or acceptance criterion
- simultaneous or ordered relationship to another action
- resulting state

If one of these elements is unclear and affects the task, do not repair it through grammar. Ask for the technical fact.

## Transform each work step

1. Put a prerequisite condition first when the reader must know it before acting.
2. Follow the condition with the command.
3. Use the imperative form for the command.
4. Write one instruction in each sentence.
5. Keep actions together only when the source establishes that they occur at the same time.
6. Use active voice and name the object of the action.
7. Keep each procedure and safety sentence within 20 words under the official Issue 9 counting rules.
8. Move explanatory information to a descriptive statement or note only when it is not an instruction.

Do not infer sequence from the order of clauses alone when the source is ambiguous. Preserve explicit words such as `before`, `after`, `while`, `until`, and `then` until the technical relationship is verified.

Count every required action and required state before you draft. Coordinated verbs, infinitives, and compound states can contain more than one instruction even when one imperative phrase introduces them. Split them and repeat their shared condition when necessary. Do not imply an order between simultaneous or unordered prerequisites.

## Conditions

Start with the condition when it controls whether, when, or how the reader does the action.

Candidate pattern:

```text
If <verified condition>, <imperative command>.
```

Do not convert:

- `unless` into `if` without checking polarity
- `<` into `≤`
- `after` into `before`
- a permission into a requirement
- a recommendation into a command

If a condition is long, split the information so the reader can identify it before the command without changing the logic.

## One instruction per sentence

Split coordinated actions when each can occur independently.

Source:

```text
Disconnect the power supply, remove the cover, and inspect the connector.
```

Candidate rewrite:

```text
Disconnect the power supply.
Remove the cover.
Do an inspection of the connector.
```

The final verb choice still requires dictionary and terminology verification. Preserve two actions in one sentence only when the source proves that they occur at the same time.

## Notes

A note gives information. It does not contain a hidden command.

If a source note tells the reader to act:

1. move the instruction to a work step
2. keep supporting information in the note
3. preserve any relationship between them

Do not invent a work step when the source only describes a fact.

## Safety instructions

Treat safety content as high-consequence source material. Identify:

- the supplied risk level or signal word
- the condition or hazardous action
- the required mitigation
- the hazard
- the supported consequence
- any mandated wording or symbol

The official aerospace/defense distinction is:

- warning: risk of injury or death
- caution: risk of damage to objects

Other industries can use different terms or categories. Preserve the source organization’s governed level. Do not upgrade or downgrade it from the wording alone.

Write the safety instruction in this order when the governing directive permits it:

1. risk level
2. command or condition
3. risk or possible result

Candidate pattern:

```text
WARNING: BEFORE YOU <HAZARDOUS ACTION>, <REQUIRED MITIGATION>.
<SUPPORTED HAZARD OR CONSEQUENCE>.
```

Uppercase is a formatting choice, not an STE language rule. Follow the applicable publication or safety directive.

## Mandated safety or legal wording

When another authority controls exact wording:

- keep the controlled text unchanged unless the user has authority to revise it
- record the conflict between the mandated wording and the STE candidate
- provide a separate proposal for the legal, safety, or terminology owner
- do not present the proposal as an approved replacement

## Procedure verification

Check every step against the source:

- prerequisite preserved
- command force preserved
- one instruction unless actions are verified as simultaneous
- no coordinated verb or compound state hides an additional instruction
- execution order preserved
- imperative form used
- active voice used
- 20-word limit checked with official counting rules
- measurements, identifiers, tools, and locations unchanged
- notes contain information only

For safety instructions, also check:

- signal word or risk level preserved
- mitigation precedes the hazardous action when required
- hazard and consequence remain source-supported
- no severity, injury, death, fire, explosion, or damage claim was invented
- applicable external directive or owner approved the final wording
