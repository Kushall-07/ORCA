# BRIEF — ORCA landing + login

**Self-authored from existing project analysis (architecture.md, existing
LandingPage.tsx/LoginPage.tsx copy, existing --orca-* theme tokens), with the
two open structural forks put to the user explicitly and answered before any
markup was written.** Not a from-scratch brand interview: ORCA already has an
established identity, real copy, real numbers, and a frozen backend the build
must not touch.

## 1. Vibe
Dark, controlled, technical. Not a consumer product — a scientific
decision-support instrument for coastal fishermen and marine authorities, SIH
hackathon, ISRO sponsor. References: a ship's chartplotter display; a patent
drawing; the existing dark teal/cyan `--orca-*` workspace theme already
shipped. Family: **premium-minimal**, leaning technical/editorial rather than
luxury-consumer.

**Correction during build:** an earlier draft of this brief cited a fisherman
count (813,431) as the "real stakes" line. That number is from a *different*,
unrelated project's landing copy read earlier in the session, not from ORCA's
own content - using it here would have been exactly the invented-statistic
failure taste.md forbids. Chapter 1 uses ORCA's own real existing subtext/
disclaimer copy instead (`landing.hero.subtext`, `landing.hero.disclaimer`) -
no number appears that isn't already in the shipped i18n strings.

## 2. The scroll journey (chapters, not sections)
1. **Title** — brand, tagline, the existing mission subtext and disclaimer.
2. **Pipeline** — the 7-stage reasoning pipeline, drawn as a technical diagram.
3. **Data sources** — the 8 real, named sources.
4. **Why ORCA** — the 8 safety-philosophy reasons, stated flatly.
5. **Preview** — a glimpse of the real decision/risk/route/evidence surface.
6. **Close** — sign in.

## 3. The energy curve
Quiet open (plain type, no video). Rises through the pipeline chapter (the
peak — the schematic drawing itself). Levels into trust/weight for sources and
philosophy. Lifts again slightly for the preview. Resolves quiet at the close.
Never loud the whole way, never flat the whole way.

## 4. The feeling curve
| Chapter | Feeling | Cause |
|---|---|---|
| Title | Recognition | Plain dark type stating ORCA's own mission/disclaimer copy, no hero image |
| Pipeline | **Clarity (peak)** | The 7-node schematic draws itself, `stroke-dashoffset` driven by scroll |
| Data sources | Trust | Named plainly, dimension-line/callout treatment |
| Why ORCA | Weight | Safety invariants stated flatly, no persuasion copy |
| Preview | Anticipation | Real interface pills, not stock screenshots |
| Close | Resolve | Quiet, a line of text and one button, not a spotlight |

## 5. The peak
> "It's the site where the whole decision pipeline draws itself as you scroll,
> like a blueprint coming to life."

Lives in the Pipeline chapter. Gets the longest scroll span (`data-sc-span
3.4`), the only SVG line-drawing on the page, and a quiet title chapter in
front of it for contrast.

## 6. The tell-someone sentence
"It's the site where the whole decision pipeline draws itself as you scroll,
like a blueprint coming to life."

## 7. Aesthetic range
Premium-minimal / technical-editorial. Earned by: a scientific instrument for
a disaster-management SIH problem, not a consumer brand.

## 8. Structure: one unbroken world, or distinct scenes?
**Distinct chapters** (confirmed by user over continuous-scroll-with-motion-only).
Chaptered editorial grammar: hard cuts between chapters, a folio nav (chapter
number + title, not a progress bar), title-page hero, colophon close.

## 9. Assets
**Confirmed by user: CSS/SVG only, no generated video/photography.** No
ffmpeg, no KIE_AI_API_KEY available in this environment; hero-depth.md
explicitly endorses native CSS/SVG-driven depth as a legitimate alternative to
generated footage. All imagery is authored SVG (the pipeline schematic, the
login art-panel depth planes) or CSS gradients, in the technical-drawing world
for the pipeline chapter and the existing dark canvas everywhere else.

## 10. Authored silence
The gap between the Title chapter and the Pipeline chapter (a full chapter
cut with no cue firing until the schematic act begins) is the silence before
the peak, so the drawing has something to be a change from. Not dead scroll.

## Grammar: chaptered editorial — why the other seven lost
- Filmic one-shot: the default every prior build reached for; ORCA's content
  is a method being explained, not one emotional consumer arc.
- Live surface: would require the preview pills to be real operable panels on
  real data — dishonest for a pre-login marketing page.
- Continuous world/worldflight: no literal geography to travel.
- Typographic poster: ORCA has a real diagram to show, not just a sentence.
- Split stage: no two-sided argument.
- Gallery/catalog: not a range of objects/variants.
- Rhythmic cutlist: wrong energy for a safety/scientific brief.

## Signature move
The self-drawing pipeline schematic (see §5). Coded in the page: an SVG whose
path `stroke-dashoffset` is driven from the act's `--sc-p`, with dimension-line
callouts (node labels) landing in sequence after the stroke passes each node.
Technical-drawing world, pairs with the schematic per uniqueness.md §3.

## Fingerprint gate
Registry was empty (first build in this workspace) — nothing to clear.

## Login page
Not a scroll narrative — a single-viewport utility screen (hero-depth.md:
working surfaces don't need an invented marketing hero). Scope: restrained
pointer-driven depth on the existing `.auth-gate__art` panel (2-3 parallax
planes replacing the flat gradient), gated to `(hover: hover) and
(pointer: fine)`, off under reduced motion. Clerk's `<SignIn>/<SignUp>` widgets
are untouched.
