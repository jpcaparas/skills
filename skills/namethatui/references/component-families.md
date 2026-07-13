# Component families

Use this reference after forming initial candidates. Compare behavior first; visual styling and vendor vocabulary come second.

## Overlays and temporary surfaces

### Tooltip, toggletip, popover, dialog

| Pattern | Defining behavior | Closest distinction | Primary example |
| --- | --- | --- | --- |
| Tooltip | Brief, non-interactive help shown on hover or keyboard focus; focus stays on the trigger | Interactive content points to a popover or toggletip | [WAI-ARIA tooltip](https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/) |
| Toggletip | User-invoked contextual help that may contain interactive content; the term is design-system-specific | Unlike a tooltip, it is intentionally opened and can accept focus | [Carbon toggletip](https://carbondesignsystem.com/components/toggletip/usage/) |
| Popover | Anchored, usually non-modal surface with contextual information or controls | A dialog represents a separate task or blocks the page | [MDN Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API), [Fluent popover](https://fluent2.microsoft.design/components/web/react/core/popover/usage) |
| Dialog / modal | Separate overlaid task or decision; modal variants make outside content inert and manage focus inside | A popover remains contextual and usually non-blocking | [WAI-ARIA modal dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) |
| Alert dialog | Modal interruption carrying an important message that requires a response | An alert announces information without moving focus | [WAI-ARIA alert dialog](https://www.w3.org/WAI/ARIA/apg/patterns/alertdialog/) |

### Scrim, backdrop, overlay

The dim or translucent layer behind a modal surface is commonly called a **scrim**, **backdrop**, or **modal overlay**. Its job is to de-emphasize or disable the underlying content and communicate modality. Name the surface and the layer separately: “a modal dialog over a dimmed scrim.”

“Overlay” is ambiguous: it can mean the layer, the whole floating surface, or a rendering mechanism. Prefer scrim/backdrop when the user means the dark layer itself.

### Drawer, sheet, sidebar, panel

| Pattern | Defining behavior | What changes the name | Primary example |
| --- | --- | --- | --- |
| Sidebar | Persistent region within the page layout, commonly for navigation or complementary content | If it temporarily slides over content, drawer or panel is likelier | [Carbon UI shell left panel](https://carbondesignsystem.com/components/UI-shell-left-panel/usage/) |
| Navigation drawer | Edge-attached navigation surface, persistent on wide layouts or temporary on compact layouts | Its primary job is navigation | [Material navigation drawer](https://m3.material.io/components/navigation-drawer/overview) |
| Drawer / side sheet / panel | Temporary or supplementary surface that slides from a side | Vendor systems choose different aliases | [Fluent drawer](https://fluent2.microsoft.design/components/web/react/core/drawer/usage) |
| Bottom sheet | Mobile surface presented from the bottom for supporting content, choices, or a task | An action sheet is a platform-specific choice/action variant | [Material bottom sheets](https://m3.material.io/components/bottom-sheets/overview) |

## Choices, commands, and search

### Menu, listbox, select, combobox

| Pattern | Defining behavior | Key question | Primary example |
| --- | --- | --- | --- |
| Menu / menu button | Offers commands or actions; choosing an item invokes something | Does selection run an action rather than set a field value? | [WAI-ARIA menu button](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/) |
| Listbox | Presents options and selects one or more values | Is the list itself the selection control? | [WAI-ARIA listbox](https://www.w3.org/WAI/ARIA/apg/patterns/listbox/) |
| Select | Closed field/control for choosing from known values | Can the user type arbitrary/filtering text? | [MDN select](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/select) |
| Combobox | Input or value field with an associated popup, commonly a listbox | Does typing or opening the field reveal candidates? | [WAI-ARIA combobox](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/) |
| Autocomplete / typeahead | Product-language aliases emphasizing suggestions while typing | Often implemented with combobox semantics; do not imply they are separate standards | [MDN aria-autocomplete](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-autocomplete) |

### Overflow menu, context menu, command palette

- **Overflow menu / more-actions menu:** a menu opened from an ellipsis or “more” button for secondary actions. “Kebab” and “meatballs” describe icon orientation, not the interaction pattern.
- **Context menu:** commands for the object or region under the pointer/focus, often opened by right-click, Control-click, or a context-menu key.
- **Command palette:** a search-led action launcher, often opened by a keyboard shortcut. It is commonly a composition of dialog, combobox/search input, and listbox/menu-like command results. The selected row runs a command rather than setting a field value.

## Navigation and view switching

### Tabs, segmented control, content switcher

| Pattern | Defining behavior | Closest distinction | Primary example |
| --- | --- | --- | --- |
| Tabs | A tablist controls layered tab panels, one panel visible at a time | The labels represent content sections | [WAI-ARIA tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) |
| Segmented control | Compact set of closely related modes, values, or actions, especially in Apple interfaces | It can change state or a subview without tab-panel semantics | [Apple segmented controls](https://developer.apple.com/design/human-interface-guidelines/segmented-controls) |
| Content switcher | Vendor term for switching among related content views | Attribute the term to the design system | [Carbon content switcher](https://carbondesignsystem.com/components/content-switcher/usage/) |

Navigation rail, sidebar navigation, bottom navigation, and tab bars may look similar. Distinguish them by placement, information hierarchy, and whether they navigate to destinations or switch panels within one context.

### Breadcrumb, stepper, pagination

- **Breadcrumb:** path back through a hierarchy. [WAI-ARIA breadcrumb](https://www.w3.org/WAI/ARIA/apg/patterns/breadcrumb/)
- **Stepper / progress tracker:** ordered stages in a process; it may indicate status without permitting navigation.
- **Pagination:** divides a collection into pages and navigates among them. It is not an activity progress indicator.

## Reveal and hierarchy

| Pattern | Defining behavior | Closest distinction | Primary example |
| --- | --- | --- | --- |
| Disclosure | One control shows or hides one related content region | A single reveal need not be called an accordion | [WAI-ARIA disclosure](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/) |
| Accordion | Coordinated vertical set of disclosure sections, usually with headings | Multiple related reveal sections make the family | [WAI-ARIA accordion](https://www.w3.org/WAI/ARIA/apg/patterns/accordion/) |
| Disclosure triangle | Small rotating triangle used to reveal nested children, especially in tree/outline views | Name the tree or outline as the parent pattern | [Apple outline view](https://developer.apple.com/design/human-interface-guidelines/outline-views) |
| Tree view | Hierarchical list with expandable parent nodes and directional-key navigation | A nested visual list without tree behavior may just be grouped navigation | [WAI-ARIA tree view](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/) |

## Status, notifications, and progress

### Alert, banner, toast, snackbar

| Pattern | Defining behavior | Closest distinction | Primary example |
| --- | --- | --- | --- |
| Alert | Important brief message announced without moving focus | It need not be visually floating or timed | [WAI-ARIA alert](https://www.w3.org/WAI/ARIA/apg/patterns/alert/) |
| Notification banner / message bar | Persistent page- or context-level information, warning, or success state | Remains until addressed or dismissed | [GOV.UK notification banner](https://design-system.service.gov.uk/components/notification-banner/) |
| Toast | Temporary, non-blocking feedback about an action or system event | Usually disappears and should not carry a required decision | [Fluent toast](https://fluent2.microsoft.design/components/web/react/core/toast/usage) |
| Snackbar | Material term for brief feedback that can include one action | Attribute the term to Material rather than treating it as universal | [Material snackbar](https://m3.material.io/components/snackbar/overview) |

### Skeleton, spinner, progress, meter

| Pattern | Defining behavior | Primary example |
| --- | --- | --- |
| Skeleton / shimmer | Content-shaped placeholders reserve layout while content loads | [Open UI skeleton research](https://open-ui.org/components/skeleton.research/) |
| Spinner / activity indicator | Indeterminate work with no meaningful completion value | [Apple progress indicators](https://developer.apple.com/design/human-interface-guidelines/progress-indicators) |
| Progress bar/ring | Determinate completion with a measurable current value | [MDN progress](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/progress) |
| Meter / gauge | A value within a known range, not task completion | [WAI-ARIA meter](https://www.w3.org/WAI/ARIA/apg/patterns/meter/) |

## Collections and scrolling

- **Carousel:** sequentially exposes a subset of slides, usually with previous/next controls or position indicators. [WAI-ARIA carousel](https://www.w3.org/WAI/ARIA/apg/patterns/carousel/)
- **Feed / infinite scroll:** loads more content as the reader advances. [WAI-ARIA feed](https://www.w3.org/WAI/ARIA/apg/patterns/feed/)
- **Virtual list:** rendering optimization that keeps only visible items mounted. It is not reliably identifiable from a static screenshot.
- **Data grid:** interactive tabular structure with cell-level directional navigation or editing. A static table is not a data grid. [WAI-ARIA grid](https://www.w3.org/WAI/ARIA/apg/patterns/grid/)

## Binary and small selection controls

- **Checkbox:** independent on/off selection; several can be selected.
- **Radio group:** one choice from a mutually exclusive set.
- **Switch / toggle:** immediate binary state, often on/off; not merely a differently styled checkbox.
- **Chip / pill / tag:** compact label-like object whose behavior may be selection, filtering, input tokenization, or status. The shape alone does not determine the name.
- **Badge:** compact count or status attached to another object; generally not an input.
- **Slider / range:** chooses a value along a continuum.
- **Spinbutton / stepper input:** chooses a discrete value with increment/decrement controls.

Use the candidate's behavior to choose among these, then attribute vendor-specific wording.

## Native primitive rule

Return native classes, HTML elements, or ARIA roles only when they help the user's platform:

- Common name: “context menu”
- Platform term: “macOS context menu”
- Native primitive: “AppKit `NSMenu`”

The common name explains the pattern; the primitive helps implementation. Do not infer the primitive from appearance alone.
