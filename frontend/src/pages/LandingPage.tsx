import { useEffect, useRef, useState } from "react";
import { LANGUAGES, useI18n } from "../i18n";
import type { LanguageCode } from "../types/api";
import { useScrollCraft } from "../scrollcraft/useScrollCraft";
import { PipelineSchematic } from "../scrollcraft/PipelineSchematic";
import { OrcaMark } from "../scrollcraft/OrcaMark";
import { OceanScene, type OceanLayerKey, usePrefersReducedMotion } from "../scrollcraft/OceanScene";
import { useActProgress } from "../scrollcraft/useActProgress";
import { AgentConvergence } from "../scrollcraft/AgentConvergence";
import { SignalFlow } from "../scrollcraft/SignalFlow";
import { RoutePeak } from "../scrollcraft/RoutePeak";
import { ProvenanceChain } from "../scrollcraft/ProvenanceChain";

const PIPELINE_STEPS = [
  "landing.pipeline.step.query",
  "landing.pipeline.step.agents",
  "landing.pipeline.step.fabric",
  "landing.pipeline.step.arbitration",
  "landing.pipeline.step.risk",
  "landing.pipeline.step.decision",
  "landing.pipeline.step.output",
] as const;

const SOURCES = [
  "landing.sources.weather",
  "landing.sources.ocean",
  "landing.sources.sst",
  "landing.sources.chl",
  "landing.sources.pfz",
  "landing.sources.gis",
  "landing.sources.safety",
  "landing.sources.evidence",
] as const;

// The data-fusion backdrop excludes "hazards"/"reasoning" - those stay
// reserved for their own later movements (the Hazard chapter and the Hero's
// closing beat) rather than appearing here as passive texture.
const FUSION_OCEAN_LAYERS: OceanLayerKey[] = [
  "surface",
  "grid",
  "coastline",
  "dataPoints",
  "currents",
  "wind",
  "sst",
  "chlorophyll",
];

// Real backend data-source groupings (docs/architecture.md, pipelineStages.ts)
// - reuses the existing landing.sources.* keys where the concept already has
// one (sst/chl/pfz), rather than inventing a near-duplicate string.
const FUSION_GROUPS = [
  {
    key: "landing.fusion.group.ocean",
    items: ["landing.sources.sst", "landing.fusion.item.waves", "landing.fusion.item.currents"],
  },
  {
    key: "landing.fusion.group.weather",
    items: ["landing.fusion.item.wind", "landing.fusion.item.storms", "landing.fusion.item.visibility"],
  },
  {
    key: "landing.fusion.group.fisheries",
    items: ["landing.sources.chl", "landing.sources.pfz", "landing.fusion.item.productivity"],
  },
  {
    key: "landing.fusion.group.geosafety",
    items: [
      "landing.fusion.item.boundaries",
      "landing.fusion.item.restrictedZones",
      "landing.fusion.item.hazards",
    ],
  },
] as const;

// Real specialist agents (backend/app/agents/*.py - see docs/architecture.md
// §2), not invented personas. risk_suitability.py is the agent that actually
// produces the fishing-suitability figure, so it's labelled by what it does
// rather than borrowing the "Fisheries" word used for the data group above.
const AGENTS = [
  "landing.agents.weather",
  "landing.agents.ocean",
  "landing.agents.gis",
  "landing.agents.suitability",
] as const;

// Real deterministic pipeline stages (backend/app/orchestration/graph.py):
// normalize -> fusion -> arbitration -> conflicts -> risk -> route ->
// decision. Reuses the existing landing.pipeline.step.* keys for the three
// stages already named there rather than adding near-duplicate strings.
const SIGNAL_STEPS = [
  { key: "landing.signal.step.raw", conflict: false },
  { key: "landing.signal.step.normalize", conflict: false },
  { key: "landing.signal.step.fuse", conflict: false },
  { key: "landing.pipeline.step.arbitration", conflict: false },
  { key: "landing.signal.step.conflicts", conflict: true },
  { key: "landing.pipeline.step.risk", conflict: false },
  { key: "landing.signal.step.route", conflict: false },
  { key: "landing.pipeline.step.decision", conflict: false },
] as const;

// A calmer, chlorophyll-focused backdrop for the suitability chapter, rather
// than the busier full data-fusion set.
const PFZ_OCEAN_LAYERS: OceanLayerKey[] = ["surface", "grid", "coastline", "dataPoints", "chlorophyll"];

const SUITABILITY_LEVELS = ["poor", "marginal", "moderate", "good"] as const;

// The hazard layer is deliberately reserved out of every earlier movement's
// backdrop (see FUSION_OCEAN_LAYERS/PFZ_OCEAN_LAYERS comments) so this is the
// first and only place it appears.
const HAZARD_BASE_LAYERS: OceanLayerKey[] = ["surface", "grid", "coastline", "dataPoints"];

// The same quiet backdrop the Hero opens on - returning to it for the Final
// section is the deliberate "calm after the peak" the spec asks for.
const FINAL_OCEAN_LAYERS: OceanLayerKey[] = ["surface", "grid", "coastline", "dataPoints"];

// Real pipeline phases (backend/app/orchestration/graph.py; see the actual
// ProvenanceViewer.tsx's STAGE_ORDER) - reuses existing landing.pipeline.step.*
// keys for the phases already named there.
const PROVENANCE_NODES = [
  { labelKey: "landing.pipeline.step.query", detailKey: "landing.provenance.detail.query" },
  { labelKey: "landing.pipeline.step.agents", detailKey: "landing.provenance.detail.agents" },
  { labelKey: "landing.provenance.label.evidence", detailKey: "landing.provenance.detail.evidence" },
  { labelKey: "landing.provenance.label.reasoning", detailKey: "landing.provenance.detail.reasoning" },
  { labelKey: "landing.provenance.label.risk", detailKey: "landing.provenance.detail.risk" },
  { labelKey: "landing.provenance.label.safety", detailKey: "landing.provenance.detail.safety" },
  { labelKey: "landing.pipeline.step.decision", detailKey: "landing.provenance.detail.decision" },
  { labelKey: "landing.pipeline.step.output", detailKey: "landing.provenance.detail.output" },
] as const;

const WHY_ITEMS = [
  "landing.why.item1",
  "landing.why.item2",
  "landing.why.item3",
  "landing.why.item4",
  "landing.why.item5",
  "landing.why.item6",
  "landing.why.item7",
  "landing.why.item8",
] as const;

const CHAPTER_KEYS = [
  "landing.chapter.mission",
  "landing.fusion.title",
  "landing.agents.title",
  "landing.signal.title",
  "landing.pfz.title",
  "landing.hazard.title",
  "landing.route.title",
  "landing.pipeline.title",
  "landing.sources.title",
  "landing.why.title",
  "landing.preview.title",
  "landing.provenance.title",
  "landing.evidenceTiers.title",
  "landing.chapter.close",
] as const;

/**
 * The first screen a judge sees. Purely presentational - zero backend
 * requests (see spec section 39) - it only reads i18n state already provided
 * by I18nProvider. "Launch ORCA" / "Enter ORCA" hand off to WorkspacePage via
 * onEnter; nothing here computes risk/decision data itself.
 *
 * Built per scrollcraft/builds/orca-landing/BRIEF.md: chaptered-editorial
 * grammar (hard cuts between chapters, a folio nav instead of a fixed bar, a
 * colophon close), CSS/SVG-only (no generated video - see the brief's asset
 * decision), with the self-drawing pipeline schematic as the signature move.
 * Every string below is an existing i18n key; no content or number was
 * invented for this pass.
 */
export function LandingPage({ onEnter }: { onEnter: () => void }) {
  const { t, lang, setLang, suitabilityLabel } = useI18n();
  const rootRef = useRef<HTMLDivElement>(null);
  useScrollCraft(rootRef);

  // Hero scroll-transformation movement (Step B): OceanScene's layers reveal
  // as the reader scrolls through this pinned act, and a small phase label
  // (Global Ocean -> Indian Ocean -> Marine Data -> ORCA Reasoning) advances
  // alongside it - see scrollcraft/builds/orca-landing-v2/BRIEF.md.
  const heroStageRef = useRef<HTMLDivElement>(null);
  const heroProgress = useActProgress(heroStageRef);
  const heroPhaseKey =
    heroProgress < 0.25
      ? "landing.hero.phase.global"
      : heroProgress < 0.5
        ? "landing.hero.phase.indian"
        : heroProgress < 0.75
          ? "landing.hero.phase.data"
          : "landing.hero.phase.reasoning";

  // Agents movement (Step C): the four real collection agents activate in
  // turn as this pinned act's progress advances - see AgentConvergence.tsx.
  const agentsStageRef = useRef<HTMLDivElement>(null);
  const agentsProgress = useActProgress(agentsStageRef);

  // Signal-to-Decision movement (Step D): the self-drawing line's progress
  // is driven by this pinned act, same pattern as Agents/Pipeline.
  const signalStageRef = useRef<HTMLDivElement>(null);
  const signalProgress = useActProgress(signalStageRef);

  // Hazard/Safety movement (Step E): a darker OceanScene state narrates
  // destination -> safety analysis -> risk detected -> route reconsidered,
  // climaxing in the real NO_SAFE_RECOMMENDATION state (spec sections 9+13
  // are the same moment here, not built twice).
  const hazardStageRef = useRef<HTMLDivElement>(null);
  const hazardProgress = useActProgress(hazardStageRef);
  const hazardPhaseKey =
    hazardProgress < 0.25
      ? "landing.hazard.phase.destination"
      : hazardProgress < 0.5
        ? "landing.hazard.phase.analysis"
        : hazardProgress < 0.75
          ? "landing.hazard.phase.risk"
          : "landing.hazard.phase.reconsidered";
  const hazardLayers: OceanLayerKey[] =
    hazardProgress >= 0.5 ? [...HAZARD_BASE_LAYERS, "hazards"] : HAZARD_BASE_LAYERS;
  const hazardClimax = hazardProgress >= 0.85;

  // Route Peak (Step F): the page's primary visual centerpiece.
  const routeStageRef = useRef<HTMLDivElement>(null);
  const routeProgress = useActProgress(routeStageRef);

  // Final section (Step G): "Explore ORCA" re-enters the journey by
  // returning to the top rather than reloading the page.
  const finalReducedMotion = usePrefersReducedMotion();
  const handleExploreAgain = () => {
    window.scrollTo({ top: 0, behavior: finalReducedMotion ? "auto" : "smooth" });
  };

  // Minimal floating nav turns from transparent to a soft solid pill once
  // the reader has scrolled past the opening screen, per the spec's "subtle/
  // transparent-then-solid" nav request - no separate large navbar element.
  const [navSolid, setNavSolid] = useState(false);
  useEffect(() => {
    const onScroll = () => setNavSolid(window.scrollY > window.innerHeight * 0.6);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const [active, setActive] = useState(0);
  useEffect(() => {
    const sections = Array.from(
      rootRef.current?.querySelectorAll<HTMLElement>("[data-chapter]") ?? [],
    );
    if (!sections.length) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const idx = Number(entry.target.getAttribute("data-chapter"));
            if (!Number.isNaN(idx)) setActive(idx);
          }
        });
      },
      { rootMargin: "-45% 0px -45% 0px" },
    );
    sections.forEach((s) => io.observe(s));
    return () => io.disconnect();
  }, []);

  return (
    <div className="landing landing--chaptered" ref={rootRef}>
      <div className="sc-grain" aria-hidden="true" />

      {/* Chaptered editorial's nav: a folio in the margin (chapter number +
          title, updating as chapters pass), never a fixed wordmark+CTA bar. */}
      <nav className={`landing__folio ${navSolid ? "is-solid" : ""}`} aria-label="Chapters">
        <span className="landing__folio-index">{String(active + 1).padStart(2, "0")}</span>
        <span className="landing__folio-title">{t(CHAPTER_KEYS[active])}</span>
      </nav>

      <div className={`landing__utility ${navSolid ? "is-solid" : ""}`}>
        <label className="landing__lang">
          <span className="sr-only">{t("header.language")}</span>
          <select
            className="landing__lang-select"
            value={lang}
            onChange={(e) => setLang(e.target.value as LanguageCode)}
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="landing__signin" onClick={onEnter}>
          {t("auth.submit.login")}
        </button>
      </div>

      <main>
        {/* Chapter 1 - Mission / hero scroll-transformation. A pinned
            movement (same pin+sc-stage mechanism as the Pipeline peak below):
            OceanScene reveals grid -> coastline -> data points -> currents ->
            wind -> SST -> chlorophyll/PFZ -> hazards -> reasoning as the
            reader scrolls, while the title/copy stay put and fully readable
            throughout (a .sc-scrim keeps contrast under the text as the
            scene fills in). The headline/subtext/disclaimer/CTA content
            below is unchanged from the original build. */}
        <section
          className="landing__chapter landing__chapter--title"
          data-chapter={0}
          data-sc-act="pin"
          data-sc-span="3.2"
        >
          <div data-sc-stage className="sc-stage landing__hero-stage" ref={heroStageRef}>
            <OceanScene progress={heroProgress} mode="active" />
            <div className="sc-scrim landing__hero-scrim" aria-hidden="true" />

            <p className="landing__hero-phase" aria-hidden="true">{t(heroPhaseKey)}</p>
            <p className="landing__hero-demo-tag">{t("landing.hero.demoTag")}</p>

            <div className="landing__orca landing__orca--mission" aria-hidden="true">
              <OrcaMark />
            </div>
            <div className="sc-wrap">
              <p className="landing__eyebrow">{t("landing.brand.tagline")}</p>
              <h1 className="sc-display sc-display--xl landing__headline">
                {t("landing.hero.headline")}
              </h1>
              <p className="sc-body landing__subtext">{t("landing.hero.subtext")}</p>
              <p className="landing__disclaimer">{t("landing.hero.disclaimer")}</p>
              <div className="landing__cta-row">
                <button type="button" className="landing__cta landing__cta--primary" onClick={onEnter}>
                  {t("landing.hero.ctaPrimary")}
                </button>
              </div>
            </div>

            <div className="landing__hero-scrollcue" aria-hidden="true">
              <span className="landing__hero-scrollcue-track">
                <span
                  className="landing__hero-scrollcue-dot"
                  style={{ top: `${Math.round(heroProgress * 100)}%` }}
                />
              </span>
            </div>
          </div>
        </section>

        {/* Chapter 2 - Data fusion. "The ocean is not one dataset": the same
            OceanScene layers from the hero, now labelled by the real source
            groupings they belong to. A flow section (data-sc-in/stagger,
            same device as Sources/Why below) rather than a new pinned
            mechanism - the reveal-on-scroll-into-view is enough here. */}
        <section className="landing__chapter landing__chapter--fusion sc-section" data-chapter={1}>
          <OceanScene layers={FUSION_OCEAN_LAYERS} mode="active" className="landing__fusion-ocean" />
          <div className="sc-scrim landing__fusion-scrim" aria-hidden="true" />
          <div className="sc-wrap sc-stack" data-sc-in data-sc-stagger="80">
            <h2 className="sc-display sc-display--md">{t("landing.fusion.title")}</h2>
            <div className="landing__fusion-groups">
              {FUSION_GROUPS.map((group) => (
                <div key={group.key} className="landing__fusion-group">
                  <h3 className="landing__fusion-group-title">{t(group.key)}</h3>
                  <ul>
                    {group.items.map((itemKey) => (
                      <li key={itemKey}>{t(itemKey)}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <p className="sc-body landing__note">{t("landing.fusion.note")}</p>
          </div>
        </section>

        {/* Chapter 3 - Agents. Four real collection agents (see
            AgentConvergence.tsx) converge on ORCA as this pinned act
            progresses; the deterministic-vs-LLM caption is real page text,
            not gated behind finishing the scroll. */}
        <section
          className="landing__chapter landing__chapter--agents"
          data-chapter={2}
          data-sc-act="pin"
          data-sc-span="2.4"
        >
          <div data-sc-stage className="sc-stage landing__agents-stage" ref={agentsStageRef}>
            <p className="landing__folio-label">{t("landing.agents.title")}</p>
            <AgentConvergence
              className="sc-agents"
              agents={AGENTS.map((key) => ({ label: t(key) }))}
              progress={agentsProgress}
            />
            <p className="sc-body landing__note">{t("landing.agents.caption")}</p>
          </div>
        </section>

        {/* Chapter 4 - Signal to Decision. One evolving line (not a static
            flowchart): raw signals converge, a conflict appears and is
            resolved, then risk/route/decision follow - real deterministic
            stage names throughout (see SignalFlow.tsx). */}
        <section
          className="landing__chapter landing__chapter--signal"
          data-chapter={3}
          data-sc-act="pin"
          data-sc-span="2.8"
        >
          <div data-sc-stage className="sc-stage landing__signal-stage" ref={signalStageRef}>
            <p className="landing__folio-label">{t("landing.signal.title")}</p>
            <SignalFlow
              className="sc-schematic"
              nodes={SIGNAL_STEPS.map((s) => ({ label: t(s.key), conflict: s.conflict }))}
              progress={signalProgress}
            />
            <p className="sc-body landing__note">{t("landing.signal.note")}</p>
          </div>
        </section>

        {/* Chapter 5 - Fishing suitability / PFZ. A calmer, chlorophyll-led
            backdrop; real suitability levels (poor/marginal/moderate/good -
            see i18n's suitabilityLabel, the same words the workspace uses),
            not an invented LOW/MEDIUM/HIGH scale. Explicitly labelled demo/
            illustrative, since the landing page has no live query behind it. */}
        <section className="landing__chapter landing__chapter--pfz sc-section" data-chapter={4}>
          <OceanScene layers={PFZ_OCEAN_LAYERS} mode="active" className="landing__pfz-ocean" />
          <div className="sc-scrim landing__pfz-scrim" aria-hidden="true" />
          <div className="sc-wrap sc-stack" data-sc-in data-sc-stagger="80">
            <h2 className="sc-display sc-display--md">{t("landing.pfz.title")}</h2>
            <div className="landing__pfz-legend">
              {SUITABILITY_LEVELS.map((level) => (
                <span key={level} className={`landing__pfz-swatch landing__pfz-swatch--${level}`}>
                  {suitabilityLabel(level)}
                </span>
              ))}
            </div>
            <p className="landing__pfz-candidate">
              <span className="landing__pfz-candidate-dot" aria-hidden="true" />
              {t("landing.pfz.candidateZone")} — {t("landing.hero.demoTag")}
            </p>
            <p className="sc-body landing__note">{t("landing.pfz.note")}</p>
          </div>
        </section>

        {/* Chapter 6 - Hazard / Safety. A darker, higher-tension movement:
            destination -> safety analysis -> risk detected -> route
            reconsidered, climaxing in the real NO_SAFE_RECOMMENDATION state
            (reusing the exact same decision.noSafeTitle/Body copy the
            workspace uses - a restrained landing-specific treatment, not the
            real alert's red styling, per the spec's "not aggressive red"
            instruction). ORCA declining to recommend a route is presented as
            a deliberate capability here, not an error state. */}
        <section
          className="landing__chapter landing__chapter--hazard"
          data-chapter={5}
          data-sc-act="pin"
          data-sc-span="2.6"
        >
          <div data-sc-stage className="sc-stage landing__hazard-stage" ref={hazardStageRef}>
            <OceanScene progress={hazardProgress} layers={hazardLayers} mode="hazard" />
            <div className="sc-scrim landing__hazard-scrim" aria-hidden="true" />
            <div className="sc-wrap">
              <h2 className="sc-display sc-display--md">{t("landing.hazard.title")}</h2>
              <p className="landing__hazard-phase" aria-hidden="true">{t(hazardPhaseKey)}</p>
              <p className="sc-body landing__note">{t("landing.hazard.note")}</p>
              <div className={`landing__hazard-nsr ${hazardClimax ? "is-visible" : ""}`}>
                <strong>{t("decision.noSafeTitle")}</strong>
                <p>{t("decision.noSafeBody")}</p>
              </div>
            </div>
          </div>
        </section>

        {/* Chapter 7 - Route Peak. THE PRIMARY VISUAL PEAK (spec section 10):
            a straight shortest path crosses a hazard; ORCA's route
            self-draws around it. Always labelled illustrative - this never
            claims to be an operationally validated route. */}
        <section
          className="landing__chapter landing__chapter--route"
          data-chapter={6}
          data-sc-act="pin"
          data-sc-span="3"
        >
          <div data-sc-stage className="sc-stage landing__route-stage" ref={routeStageRef}>
            <div className="sc-wrap">
              <h2 className="sc-display sc-display--md">{t("landing.route.title")}</h2>
              <p className="landing__route-illustrative">{t("landing.route.illustrative")}</p>
            </div>
            <RoutePeak
              className="sc-route"
              progress={routeProgress}
              originLabel={t("landing.route.origin")}
              destinationLabel={t("landing.route.destination")}
              shortestLabel={t("landing.route.shortest")}
              orcaLabel={t("landing.route.orca")}
              hazardLabel={t("landing.route.hazardLabel")}
            />
            <p className="sc-body landing__note landing__route-note">{t("landing.route.note")}</p>
          </div>
        </section>

        {/* Chapter 8 - Pipeline. THE PEAK. A pinned stage holding while the
            bespoke self-drawing schematic (the signature move) assembles the
            real 7-node pipeline. Silence in front of it (chapter 1 ends
            plainly, no cue overlap) is the authored quiet this needs. */}
        <section
          className="landing__chapter landing__chapter--pipeline"
          data-chapter={7}
          data-sc-act="pin"
          data-sc-span="3.4"
        >
          <div data-sc-stage className="sc-stage landing__pipeline-stage">
            <p className="landing__folio-label">{t("landing.pipeline.title")}</p>
            <PipelineSchematic nodes={PIPELINE_STEPS.map((key) => ({ label: t(key) }))} />
            <p className="sc-body landing__note">{t("landing.pipeline.note")}</p>
          </div>
        </section>

        {/* Chapter 9 - Data sources. Museum-label treatment: named plainly,
            dimension-line callouts, not persuasion copy. */}
        <section
          className="landing__chapter landing__chapter--sources sc-section"
          data-chapter={8}
          data-sc-act="flow"
        >
          <div className="landing__orca landing__orca--sources" data-sc-parallax="0.5" aria-hidden="true">
            <OrcaMark />
          </div>
          <div className="sc-wrap sc-stack" data-sc-in data-sc-stagger="60">
            <h2 className="sc-display sc-display--md">{t("landing.sources.title")}</h2>
            <ul className="landing__dimension-list">
              {SOURCES.map((key) => (
                <li key={key} className="landing__dimension-item">
                  <span className="landing__dimension-tick" aria-hidden="true" />
                  <span>{t(key)}</span>
                </li>
              ))}
            </ul>
            <p className="sc-body landing__note">{t("landing.sources.note")}</p>
          </div>
        </section>

        {/* Chapter 10 - Why ORCA. A hard cut, marked with a reveal wipe on the
            heading rather than a crossfade - the chapter boundary device
            chaptered editorial actually leans on. */}
        <section
          className="landing__chapter landing__chapter--why sc-section"
          data-chapter={9}
          data-sc-act="flow"
        >
          <div className="landing__orca landing__orca--why" data-sc-parallax="-0.45" aria-hidden="true">
            <OrcaMark />
          </div>
          <div className="sc-wrap sc-stack" data-sc-in data-sc-stagger="60">
            <figure data-sc-reveal="up" data-sc-reveal-at="0.1 0.5" className="landing__reveal-heading">
              <h2 className="sc-display sc-display--md">{t("landing.why.title")}</h2>
            </figure>
            <ul className="landing__why-grid">
              {WHY_ITEMS.map((key) => (
                <li key={key} className="landing__why-item">
                  {t(key)}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Chapter 11 - Preview. A glimpse of the real surface. */}
        <section className="landing__chapter landing__chapter--preview sc-section" data-chapter={10}>
          <div className="sc-wrap sc-stack" data-sc-in data-sc-stagger="60">
            <h2 className="sc-display sc-display--md">{t("landing.preview.title")}</h2>
            <div className="landing__preview">
              <span className="landing__preview-pill landing__preview-pill--safe">
                {t("landing.preview.decision")}
              </span>
              <span className="landing__preview-pill">{t("landing.preview.safety")}</span>
              <span className="landing__preview-pill">{t("landing.preview.suitability")}</span>
              <span className="landing__preview-pill">{t("landing.preview.route")}</span>
              <span className="landing__preview-pill">{t("landing.preview.evidence")}</span>
            </div>
          </div>
        </section>

        {/* Chapter 12 - Decision provenance. Expandable nodes (real
            disclosure semantics, not a scroll device) tracing the real
            pipeline phases - demo content, never wired to a live query. */}
        <section className="landing__chapter landing__chapter--provenance sc-section" data-chapter={11}>
          <div className="sc-wrap sc-stack" data-sc-in data-sc-stagger="60">
            <h2 className="sc-display sc-display--md">{t("landing.provenance.title")}</h2>
            <ProvenanceChain
              nodes={PROVENANCE_NODES.map((n) => ({ label: t(n.labelKey), detail: t(n.detailKey) }))}
            />
            <p className="sc-body landing__note">{t("landing.provenance.note")}</p>
          </div>
        </section>

        {/* Chapter 13 - Evidence tiers. Official/Forecast/Derived, footnoted
            against the real Live/Cache/Reference/Demo/Missing tier
            vocabulary rather than inventing a parallel taxonomy. */}
        <section className="landing__chapter landing__chapter--evidence-tiers sc-section" data-chapter={12}>
          <div className="sc-wrap sc-stack" data-sc-in data-sc-stagger="60">
            <h2 className="sc-display sc-display--md">{t("landing.evidenceTiers.title")}</h2>
            <div className="landing__evidence-tiers">
              <div className="landing__evidence-tier">
                <h3>{t("landing.evidenceTiers.official")}</h3>
                <p>{t("landing.evidenceTiers.officialDesc")}</p>
              </div>
              <div className="landing__evidence-tier">
                <h3>{t("landing.evidenceTiers.forecast")}</h3>
                <p>{t("landing.evidenceTiers.forecastDesc")}</p>
              </div>
              <div className="landing__evidence-tier">
                <h3>{t("landing.evidenceTiers.derived")}</h3>
                <p>{t("landing.evidenceTiers.derivedDesc")}</p>
              </div>
            </div>
            <p className="sc-body landing__note">{t("landing.evidenceTiers.note")}</p>
          </div>
        </section>

        {/* Chapter 14 - Close / Final. A calm return after the peak - the
            same quiet OceanScene the Hero opened on, the ORCA wordmark, and
            two real CTAs (spec section 14) rather than the single inline-
            link this colophon used before. Everything the original colophon
            said is kept, just no longer squeezed into one run-on sentence. */}
        <footer
          className="landing__chapter landing__colophon"
          data-chapter={13}
          data-sc-act="flow"
        >
          <OceanScene layers={FINAL_OCEAN_LAYERS} mode="quiet" className="landing__final-ocean" />
          <div className="landing__orca landing__orca--close" data-sc-parallax="0.35" aria-hidden="true">
            <OrcaMark />
          </div>
          <div className="sc-wrap">
            <p className="landing__eyebrow">{t("landing.brand.tagline")}</p>
            <h2 className="sc-display sc-display--lg landing__final-wordmark">ORCA</h2>
            <p className="landing__colophon-mark">{t("landing.footer.tagline")}</p>
            <p className="landing__final-tagline">{t("landing.final.tagline")}</p>
            <div className="landing__cta-row">
              <button type="button" className="landing__cta landing__cta--primary" onClick={handleExploreAgain}>
                {t("landing.final.ctaPrimary")}
              </button>
              <button type="button" className="landing__cta landing__cta--ghost" onClick={onEnter}>
                {t("landing.preview.cta")}
              </button>
            </div>
            <p className="landing__colophon-meta">
              <span>{t("landing.footer.problem")}</span>
              <span>{t("landing.footer.sponsor")}</span>
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}

export default LandingPage;
