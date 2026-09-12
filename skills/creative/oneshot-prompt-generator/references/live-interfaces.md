# Live Interface Dissection

Use this reference for websites, web apps, local HTML, and interactive prototypes. The goal is a behaviorally faithful specification, not a screenshot inventory.

## Inspection Sequence

1. Establish the accessible surface: public routes, authenticated boundaries, locale, viewport, and whether local source or runtime files are available.
2. Traverse primary navigation and representative secondary routes. Record hierarchy, persistent shell elements, route transitions, and content patterns.
3. Inspect the rendered page and, when available, its DOM and accessibility tree. Use computed or source values for exact measurements and tokens when the prompt needs them; do not estimate a precise value from appearance alone.
4. Exercise safe controls: menus, tabs, filters, accordions, dialogs, carousels, forms with non-sensitive dummy input, keyboard navigation, and back/forward behavior.
5. Capture secondary states: hover, focus, active, selected, loading, empty, validation, success, error, disabled, offline, permission, and dismissal behavior.
6. Compare meaningful viewports. Observe reflow and component substitution rather than listing device widths mechanically.
7. Inspect asset identity, font use, media treatment, motion, reduced-motion behavior, and performance-sensitive details that affect the experience.

Do not submit real forms, create accounts, publish content, purchase, send messages, accept destructive confirmations, or alter remote data merely to reveal a state. Prefer source inspection, local replay, harmless inputs, or a clearly marked unknown.

## Coverage Map

For each route or major view, record:

- entry route and how users reach it
- purpose, primary action, and supporting actions
- section order, containers, columns, alignment, and scroll behavior
- exact high-signal copy and data
- repeated components and variants
- interaction triggers, state changes, feedback, and dismissal
- keyboard and focus behavior when observable
- responsive transformations
- loading, empty, error, permission, and success paths
- transitions to other routes, overlays, or persistent state

Treat network calls, storage, analytics, and framework internals as implementation evidence only when they change observable behavior or the user explicitly needs technical fidelity.

## Prompt Translation

Describe the interface as a connected system:

- Name the persistent shell before route-specific content.
- State relationships and proportions, not isolated CSS adjectives.
- Express interactions as trigger → transition → feedback → resulting state.
- State which behaviors were exercised and which the future session must reconstruct coherently.
- Require direct comparison at the observed viewports and through the recorded state transitions.

Do not prescribe the source framework simply because it is detectable. Preserve it only when the user asks for technical replication or compatibility depends on it.

**Complete when:** every major route and state has a place in the evidence ledger, responsive behavior is observed or bounded, and the prompt describes one coherent interface rather than disconnected screens.
