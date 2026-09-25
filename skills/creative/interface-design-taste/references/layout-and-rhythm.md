# Layout And Rhythm

Layout quality is usually the first difference between a credible interface and a generic one.

## Start With Three Levels

1. **Page or screen frame**
   - what is fixed, what scrolls, what anchors the view
2. **Section grouping**
   - what belongs together, what must stay distinct
3. **Component internals**
   - label, value, action, metadata, and state

If these three levels do not agree, the interface feels noisy even with perfect colors.

## Composition Rules

### Clear priorities

A dominant zone often gives a screen focus:

- a hero claim
- a working canvas
- a table
- a form sequence
- a primary panel

Keep supporting controls from competing with the task. Comparison or monitoring views may instead need equally weighted peers; make their relationships explicit.

### Rhythm over raw whitespace

Whitespace only helps when it is patterned.

- repeat intervals intentionally
- let related elements sit closer together than unrelated ones
- enlarge gaps at hierarchy changes, not everywhere
- avoid equal spacing between every block on the page

### Use asymmetry with a job

Asymmetry works when it increases focus or pacing.

- good:
  - offsetting a hero against a strong image
  - widening the work surface while narrowing secondary chrome
- bad:
  - random misalignment
  - unbalanced empty corners

## Grid Guidance

### Marketing or editorial surfaces

- allow bigger scale jumps
- use a strong primary column and looser supporting columns
- let imagery or type bleed with intent

### Product and dashboard surfaces

- prefer predictable columns and repeated internal alignment
- use dense subgrids for tables, filters, and inspector panels
- reduce ornamental spacing before reducing clarity

### Desktop surfaces

- assume more secondary chrome:
  - sidebars
  - utility rails
  - inspectors
  - status bars
- design for resizing and awkward window widths
- let important panels hold their width before decorative sections do

## Card And Surface Use

Cards are not a default layout strategy.

Use cards when they help with:

- reordering independent units
- elevation against a busy field
- modular previews
- touch-friendly grouping

Avoid card overuse when:

- the screen is mostly operational
- the content is already structured by lines, tabs, or panes
- density matters more than object feel

Operational screens often improve when cards become:

- divider systems
- grouped rows
- split panes
- subtle section headers

## Hero And Landing Structure

For promotional surfaces:

- keep the headline readable at a glance
- avoid six-line heading blocks when width is available
- connect visual ideas through a clear composition, whether restrained or eclectic
- consider a calmer explanatory section after a dramatic hero when that improves pacing

## Dense Screen Rules

When a screen feels cramped:

1. reduce repeated chrome before shrinking type
2. collapse decorative wrappers before shrinking hit areas
3. check type choices for readability and numeric comparison at the needed density
4. align numbers and actions with strong vertical rails
5. reserve high-emphasis color for actual status or actions

## Responsive Collapse

Do not simply stack everything in source order.

- preserve the primary task path
- keep controls near the object they affect
- move secondary metadata below the main content
- simplify asymmetry early

For smaller widths, degrade from:

1. multi-panel
2. two-zone
3. single clear column

Not from:

1. rich layout
2. broken layout
3. emergency stack

## Quick Checks

If the screen still feels off, ask:

1. Which zone is too loud?
2. Which objects should share an edge but do not?
3. Which gaps are accidental?
4. Which containers can disappear entirely?

## See Also

- `typography-and-copy.md` for internal component hierarchy
- `platform-adaptation.md` for web versus desktop layout differences
