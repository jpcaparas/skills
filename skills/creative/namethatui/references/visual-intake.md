# Visual intake

Use this route for screenshots, mockups, screen recordings, or a live interface whose behavior is only partly visible. The objective is to extract evidence without pretending an image proves interaction semantics.

## Analyse locally

Use the active model's native/local image understanding or the harness's first-party image viewer. Do not upload the image to an external recognition, OCR, or vision service.

If the input is a live page, use read-only browser inspection to supplement the image:

- snapshot the accessibility tree
- inspect visible labels and relationships
- read relevant element attributes
- observe an already-open state
- interact only when the user authorised inspection and the action is reversible and non-destructive

Avoid logins, submissions, purchases, destructive controls, or state changes that are not needed to identify the pattern.

## Visual clue pass

Record what is genuinely visible:

1. **Anchor** — Is the element attached to a trigger, centered in the viewport, inline with content, or flush with an edge?
2. **Layer** — Does it sit above the page? Is there a scrim/backdrop? Is underlying content dimmed?
3. **Shape and scale** — Tiny label, compact card, floating list, full-height panel, bottom surface, or full-screen task?
4. **Controls** — Text field, close button, chevron, drag handle, action rows, checkmarks, tabs, pagination dots, or disclosure indicators?
5. **Visible state** — Selected, expanded, loading, disabled, destructive, temporary, nested, or scrollable?
6. **Relationship** — Does the content look like help, choices, commands, status, navigation, or a separate workflow?
7. **Platform chrome** — Browser, iOS, Android, macOS, Windows, or a recognizable design-system convention?

Quote visible text only when it helps explain the component's job. Do not infer private data or inaccessible off-screen content.

## Separate observation from inference

Use two short ledgers:

- **Observed:** “A compact panel is anchored under a three-dot button and contains action rows.”
- **Inferred:** “Likely an overflow menu or menu button; keyboard behavior is not visible.”

Never infer these from pixels alone:

- whether focus moves or is trapped
- exact keyboard interactions
- whether outside content is inert
- whether a list sets a value or invokes a command
- whether unseen content is virtualized
- the implementation library or native class

Ask one behavior question only when it changes the family: “Does choosing a row set the field's value, or run an action?”

## From pixels to search terms

Translate appearance into behavior-rich phrases:

| Weak visual phrase | Better research clue |
| --- | --- |
| “little floating box” | “anchored non-modal surface with interactive content” |
| “dropdown” | “button opens a list of actions” or “field opens selectable values” |
| “dark layer behind popup” | “dimmed backdrop that makes outside content inert” |
| “moving gray blocks” | “content-shaped loading placeholders before data arrives” |
| “panel from the bottom” | “mobile edge-presented surface with a drag handle and actions” |

## Completion check

The visual route is complete when:

- observed and inferred facts are separate
- at least two visible clues support each candidate
- invisible behavior is not presented as fact
- no image was sent to a third-party vision service
