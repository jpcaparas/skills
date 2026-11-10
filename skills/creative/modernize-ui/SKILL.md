---
name: modernize-ui
description: "Modernises the UI of an existing website or app: faster, better looking, accessible to WCAG, consistent across browsers and viewports, with fallbacks and polyfills so older browsers keep working. Use for /modernize-ui, a facelift, refresh or redesign of a dated interface, or a UI audit. Shows every planned change with before and after renders before editing. Not for building a new interface or fixing a single component."
---

# Modernize UI

Reworks the interface of an existing project so it is faster, better looking, usable to WCAG 2.2 AA and the same in every browser and viewport, without breaking the browsers it works in today.

The project is edited only after the user approves a catalogue: one page that lists every intended change beside renders of each page before and after. When the user says to skip the catalogue, only the plan and its approval (steps 2 to 5 below) are skipped. The untouched site is still captured before the first edit, and the finished work is still captured and built with `build_catalogue.py --fail-on-regression`, which is the regression check as well as the page and runs without `--plan`. Both captures are the full default run.

## Dials

Take each dial from the request. A request that names a mode, asks for an audit or says to use the defaults is enough to start: the dials it leaves out take their defaults, and the first reply says which defaults were used. Any other request gets one message before anything is captured or edited, with the host's question tool if it has one, asking for all four dials, showing each default and saying in a line what each mode lets change.

- **Audit first** (default: no). Capture the site, build the catalogue from that run alone, report what is wrong with the measurements behind it, change nothing, then ask for the mode.
- **Mode** (default: `refresh`). The mode sets what may visibly change.
  - `preserve`: a visitor should not notice a redesign. Fix what is broken, slow or irritating: sideways scroll, layout shift, render-blocking scripts, oversized images, dead CSS and JavaScript, keyboard traps, missing names and focus styles, motion nobody can pause. The after renders differ from the before renders only where a defect was fixed, and each visible difference is its own change in the plan, including a brand colour darkened to pass contrast.
  - `refresh`: the same brand, palette, typefaces, content and page structure, brought up to date. Spacing, type scale, component styling, states, motion and responsive behaviour may change, and dated patterns (float grids, auto-rotating carousels, `div` buttons, plugin-driven widgets) are replaced with what the platform now does itself. This is the mode for a site built around 2020.
  - `reimagine`: a new visual direction for layout, type, colour, motion and every component. Content, features, URLs and brand marks stay unless the user releases them.
- **Pages** (default: all of them). Every route, one page per template when a template repeats, plus the states a visitor meets: open menu, dialog, form error, empty list, signed-in view.
- **Browser floor** (default: what the project supports today). See Older browsers.

No mode touches copy, prices, legal text, routes, form submission, analytics, SEO metadata or the backend unless the user asks. List them under `out_of_scope` in the plan so the user sees the boundary. Copy is every word a visitor already reads, down to option text, placeholders and button labels. A fix that has to add wording, such as a label, alt text or an error message, quotes the new words in its plan entry.

## The catalogue

Both scripts print their options with `--help`. `capture.py` renders pages and writes screenshots plus a `manifest.json` of what each render measured: sideways overflow, console errors, failed requests, axe failures, LCP, CLS, request count and transfer size. `build_catalogue.py` pairs two runs with the plan.

```bash
python scripts/capture.py --pages pages.json --out runs/before --axe tools/node_modules/axe-core/axe.min.js
python scripts/capture.py --pages pages-proposal.json --out runs/after --axe tools/node_modules/axe-core/axe.min.js --mockup
python scripts/build_catalogue.py --before runs/before --after runs/after --plan plan.json --out catalogue --fail-on-regression
```

1. Capture the untouched site first. Its numbers are the evidence for every change, and they cannot be recovered after an edit.
2. Write `plan.json` with one entry per defect and its fix, so the user can strike any one of them. Missing alt text, unlabelled fields and missing `autocomplete` are three entries, not one "forms and images" entry; the same fix on several elements is one entry. `why` quotes what the before run measured ("home overflows by 295px at 320 wide"), or the line of the project's source that shows the defect when the manifest has no number for it ("`.col { float: left }` in style.css"), not a general principle. A medium or high risk needs a `risk_note` saying what could break.
3. Build the proposal without editing the project's working tree. Inject a stylesheet and script into the live pages with `--overlay-css` and `--overlay-js` when that is enough; otherwise change a copy of the project (a git worktree or a scratch copy), serve it on another port and capture it with `--mockup`. The after renders are real HTML and CSS in real browsers. A generated image or a description is not a dry run.
4. Build the catalogue and give the user `catalogue/index.html`, served or opened. In the reply, give the totals, the changes by id, two or three before and after pairs, anything that was not rendered, and each number the after run makes worse with its reason, for example transfer size raised by a web font. Ask which ids to drop.
5. Approval covers the listed ids. A change found later is added to the plan and asked about.
6. Implement in the project the way the project is written: its components, tokens, build and tests. Capture the real implementation as a new after run and rebuild with `--fail-on-regression`, which exits 1 when the after run has a new accessibility failure, console error, failed request, sideways scroll or missing render.

Done means that build exits 0 on current engines and on the floor engines, the project's own checks pass, and every approved id is implemented or reported as not done. The closing reply covers the real after run the way step 4 covers the proposal.

Keep runs, plans and catalogues in a scratch or ignored directory, not in the project's tracked files.

## Rendering

Install what the work needs without asking, into a scratch directory outside the project's own dependencies. Adding a dependency to the project is a change and belongs in the plan.

```bash
python3 -m venv tools/venv && tools/venv/bin/pip install playwright
tools/venv/bin/python -m playwright install --with-deps chromium firefox webkit
npm install --prefix tools axe-core
```

- The default run is Chromium, Firefox and WebKit at 320x568, 390x844, 768x1024, 1366x768 and 1920x1080. Widen it when the project calls for it; do not narrow it to save time. A browser that will not launch names the system library it lacks: install it (`playwright install-deps <browser>` with sudo, or unpack the package into the scratch directory and add it to `LD_LIBRARY_PATH`) before leaving the browser out, and name any browser left out in the reply. `--viewports` takes space-separated sizes. `chrome` and `msedge` are the branded builds (`playwright install chrome msedge`).
- Render a state by giving a page entry a `prepare` script that opens the menu or triggers the error. On a live site `prepare` must not submit a form or change data.
- A site with a dark theme or motion gets extra runs with `--color-scheme dark` and `--reduced-motion`, each paired into its own catalogue. Signed-in pages take `--storage-state`.
- Install Chromium without `--only-shell`; the script launches the full browser because the headless shell renders less like Chrome.
- Playwright's WebKit is not Safari on an iPhone, and Firefox cannot emulate touch. Say so when the user depends on either, and ask for a real device or a cloud browser account when it matters.
- An axe scan with no failures is not WCAG conformance. Also exercise by hand what a scan cannot see: keyboard order and focus visibility, reflow at 320 wide and 200% zoom, target size, accessible names that make sense, reduced motion, and error messages that are announced. Report "no failures in these checks", never "WCAG compliant".
- The manifest's LCP and CLS come from one cold load on this machine. Use them to compare before with after, not as field data, and add Lighthouse or the project's own performance tooling when the user wants more.

## Older browsers

The floor is the oldest set of browsers the result must work in. Take it from the user's answer, then the project's browserslist (`npx browserslist` prints it), then its build targets, and otherwise from the engines the current site works in. Modernising never raises the floor on its own: raising it is the user's decision, shown as its own `compatibility` change that says what stops working and for whom.

Each feature the floor lacks gets one of these, in this order of preference. The plan change that uses the feature names the feature, the browsers that lack it and which of the three covers them:

1. A fallback in the code itself: the older declaration first and the newer one after it, an `@supports` block, or a feature test in the script. It costs nothing in current browsers and cannot fail to load.
2. A build-time transform with tooling the project already has, pointed at its browserslist (Autoprefixer, postcss-preset-env, Lightning CSS, Babel or SWC with core-js by usage). Adding a build step to a project that has none is a `code` change with its own risk.
3. A runtime polyfill, when the result without it is not acceptable in the floor browsers. Copy a pinned version into the project and load it only when a feature test fails, so current browsers download nothing. It is its own `compatibility` change that states which browsers load it and how many bytes it is. Do not load polyfills from `polyfill.io`; that domain changed hands and served malware in June 2024.

Unsupported code does not always degrade one declaration at a time, and these are the breaks to look for:

- One unknown selector discards the whole rule it is listed in.
- A browser without `@layer`, CSS nesting or custom properties discards everything written with them.
- `@supports (gap: 1rem)` is true in browsers that support `gap` only in grid (Safari before 14.1), so it cannot guard flex `gap`.
- One piece of syntax an engine cannot parse, such as optional chaining, stops the whole script file.

A polyfill that loads is not a polyfill that works. Measured on 2026-11-10: `container-query-polyfill` 1.0.2 (30 kB) loaded in Firefox 108 with no console error and applied the layout on 5 of 36 loads, while a six-line `@supports not (container-type: inline-size)` fallback (269 bytes) applied it on 11 of 11. So the page must be acceptable when a polyfill does not run, and every polyfill is rendered in an engine that lacks the feature, over several loads, before it is called working.

Check the floor two ways:

- Statically: `npx doiuse --browsers "<browserslist query>" <css files>` lists the CSS features the floor lacks; a compat lint such as `eslint-plugin-compat` does the same for script APIs. This is the only check available for engines nothing here can run.
- Rendered: an older Playwright release bundles older engines. Install it in its own environment and run the same `capture.py` on the site before and after, then pair those two runs in their own catalogue with `--fail-on-regression`.

```bash
python3 -m venv tools/venv-old && tools/venv-old/bin/pip install 'playwright==1.30.0'
PLAYWRIGHT_BROWSERS_PATH=tools/browsers-old tools/venv-old/bin/python -m playwright install chromium firefox webkit
PLAYWRIGHT_BROWSERS_PATH=tools/browsers-old tools/venv-old/bin/python scripts/capture.py --pages pages.json --out runs/before-old --browsers chromium firefox
```

Playwright 1.30 carries Chromium 110, Firefox 108 and WebKit 16.4 (early 2023). On Python 3.11 the oldest release that runs `capture.py` is 1.27 (Chromium 107, Firefox 105); earlier ones do not install or hang. An old WebKit build may not launch on a current Linux because it needs system libraries the distribution has dropped (WebKit 16.4 on Debian 12, checked 2026-11-10); use the Playwright Docker image of the same version, or macOS. Render in every old engine that does launch, and report the rest by name. The catalogue names the engine versions each run used.

Internet Explorer 11, Safari before 16 and other engines older than these cannot be rendered this way. They need a real device or a cloud browser service the user provides access to. Without one, report them by name as "checked statically, not rendered" and do not claim they work.

A difference between engines is not always a defect. A feature that only refines, such as `text-wrap: balance`, moves line breaks in engines that have it and changes nothing else; note it and move on.

## Design

The look comes from the project, the user and whichever design skills are installed; in this library `interface-design-taste` chooses a direction and `preventing-ui-slop` lists what to leave out. "Modern" and "flashier" mean clearer hierarchy, type and spacing chosen on purpose, complete states for every control, and motion that explains a change and stops for reduced-motion users. They are not permission for gradients, glass, glow or a new component library.
