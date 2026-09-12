# Research Rationale

This skill is based on stable web writing and accessibility guidance. Use this file when you need to justify why a scaffold should be lean, or when you need to decide whether text is optional decoration or required instruction.

## What The Sources Support

| Source | Practical rule |
| --- | --- |
| Nielsen Norman Group, [How Users Read on the Web](https://www.nngroup.com/articles/how-users-read-on-the-web/) | Users scan pages; use meaningful headings, bullets, one idea per paragraph, inverted-pyramid structure, and roughly half the word count of print-style copy. |
| Nielsen Norman Group, [Concise, Scannable, and Objective](https://www.nngroup.com/articles/concise-scannable-and-objective-how-to-write-for-the-web/) | Concise, scannable, objective copy improves measured usability more than promotional or bloated copy. |
| GOV.UK Service Manual, [Writing for user interfaces](https://www.gov.uk/service-manual/design/writing-for-user-interfaces) | Start with less, keep copy short and direct, put important words first, and drop unnecessary words. |
| W3C WAI, [Understanding WCAG 2.1 SC 3.3.2 Labels or Instructions](https://www.w3.org/WAI/WCAG21/Understanding/labels-or-instructions.html) | Inputs need labels or instructions, but too much instruction can also harm usability. The goal is enough information for task completion. |
| W3C WAI, [Form Instructions](https://www.w3.org/WAI/tutorials/forms/instructions/) | Provide relevant form instructions such as required/optional status, data formats, and control-level help. |
| Nielsen Norman Group, [Placeholders in Form Fields Are Harmful](https://www.nngroup.com/articles/form-design-placeholders/) | Placeholder text is not a reliable replacement for labels or persistent hints. |

## Design Implications

1. Scaffolds should not imitate finished marketing decks by filling every slot with text.
2. Headings and layout should carry structure before badges and subtitles are added.
3. Short copy should stay factual and specific; deleting words is not enough if the remaining copy is generic.
4. Form labels are part of task completion, not decorative text.
5. Placeholder text can be supplementary, but it should not carry the only instruction.
6. Long explanations often signal a UI problem. Fix the interface before adding instructional copy.

## Accessibility Boundary

When reducing text, separate three categories:

| Category | Examples | Default |
| --- | --- | --- |
| Decorative | `Features`, `New`, `Trusted by`, repeated eyebrow labels | Remove unless requested or meaningful |
| Structural | headings, nav items, table headers, tabs | Keep concise and descriptive |
| Operational | form labels, legends, helper text, errors, accessible names | Preserve or improve |

Do not remove operational text to satisfy a visual preference. If visible text would be redundant but assistive technology still needs a name, use an accessible naming pattern already established in the project.

## See Also

- `references/rules.md` for concrete budgets and audit checks.
