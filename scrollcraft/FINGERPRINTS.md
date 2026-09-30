# Fingerprints

Every site you build with **scroll-craft** gets one row here, appended after it
ships. The registry exists so your next build can prove it is a different page
rather than a re-skin of one you already made.

This file is **yours**. It starts empty on purpose: the gate is about not
repeating *yourself*, so it has nothing to say until you have built something.

The rules and the gate live in the skill's
`references/uniqueness.md`. Short version:

**A new build must differ from EVERY row below on at least 4 of the 6
dimensions.** Four against each row individually, not four on average across the
table. If a planned build fails, change the plan. Never edit a row to make room
for it.

The six dimensions are: **grammar**, **nav treatment**, **hero device**,
**act-sequence shape**, **close pattern**, **signature move**.

Dimension 6 is free, because a signature move is unique by definition. So the
gate really asks for three more out of the remaining five, and a build that
changes only grammar and world will fail it.

---

## The registry

| Build | Grammar | Nav treatment | Hero device | Act-sequence shape | Close pattern | Signature move | World | Port |
|---|---|---|---|---|---|---|---|---|
| orca-landing | Chaptered editorial | Folio (chapter number + title, margin-anchored, IntersectionObserver-driven) | Title page - plain type on hard-cut ground, no media above the fold | 6 chapters, hard cuts, no drift interpolation; one `pin` (peak) + `flow`×4 + colophon; ~6 viewport-heights total | Colophon: CTA as a line of underlined running text, not a button island | Self-drawing SVG pipeline schematic (`stroke-dashoffset` driven from the pinned act's `--sc-p`, reading ORCA's real 7-node pipeline) | Technical drawing (ink-line schematic) for the peak chapter; existing dark `--orca-*` canvas elsewhere - no photography/video (CSS/SVG-only build, no kie.ai/ffmpeg in this environment) | React/Vite SPA page (frontend/src/pages/LandingPage.tsx), not a standalone static site |

*(First build in this registry - nothing to clear against.)*

---

## What is taken

Add a bullet here whenever a build claims something a later build should avoid
reusing: a grammar, a nav treatment, a close pattern, a signature move, an
act-count-and-length band. The shared columns are what the next build inherits
as a constraint, so writing them down is the whole point.

- Chaptered editorial grammar, folio nav, and colophon close are now taken by
  `orca-landing` - the next ORCA build should reach for a different grammar
  (live surface fits the actual authenticated workspace well) rather than
  reusing this shape.
- The self-drawing SVG schematic signature move is taken.

---

## Appending a row

After shipping, add one line to the table and one bullet to **What is taken** if
the build claimed something new. Fill every column. Say what the build shares
with existing rows.

Rows are append-only. A build that has been superseded stays in the table,
because the space it occupies is still occupied.

---

## Worked example

The skill's author kept a registry of twelve builds across eight page grammars.
If you want to see what a filled-in table looks like, and which shapes tend to
collide, read `EXAMPLES.md` in the scroll-craft repository. Treat it as
illustration only: those rows are somebody else's builds and they do **not**
constrain yours.
