// Centralized UI strings. Technical source names (Open-Meteo, INCOIS, RSMC,
// GEBCO, Marine Regions, WDPA) and numeric values are NEVER translated - they
// come straight from the backend.

import type { LanguageCode } from "../types/api";

export type StringKey =
  | "app.subtitle"
  | "landing.brand.tagline"
  | "landing.hero.headline"
  | "landing.hero.subtext"
  | "landing.hero.ctaPrimary"
  | "landing.hero.ctaSecondary"
  | "landing.hero.disclaimer"
  | "landing.pipeline.title"
  | "landing.pipeline.step.query"
  | "landing.pipeline.step.agents"
  | "landing.pipeline.step.fabric"
  | "landing.pipeline.step.arbitration"
  | "landing.pipeline.step.risk"
  | "landing.pipeline.step.decision"
  | "landing.pipeline.step.output"
  | "landing.pipeline.note"
  | "landing.sources.title"
  | "landing.sources.note"
  | "landing.sources.weather"
  | "landing.sources.ocean"
  | "landing.sources.sst"
  | "landing.sources.chl"
  | "landing.sources.pfz"
  | "landing.sources.gis"
  | "landing.sources.safety"
  | "landing.sources.evidence"
  | "landing.why.title"
  | "landing.why.item1"
  | "landing.why.item2"
  | "landing.why.item3"
  | "landing.why.item4"
  | "landing.why.item5"
  | "landing.why.item6"
  | "landing.why.item7"
  | "landing.why.item8"
  | "landing.preview.title"
  | "landing.preview.decision"
  | "landing.preview.safety"
  | "landing.preview.suitability"
  | "landing.preview.route"
  | "landing.preview.evidence"
  | "landing.preview.cta"
  | "landing.footer.tagline"
  | "landing.footer.problem"
  | "landing.footer.sponsor"
  | "header.stakeholder"
  | "header.boatClass"
  | "header.boatClassNotSet"
  | "header.language"
  | "boatClass.traditionalNonmotorized"
  | "boatClass.smallMotorized"
  | "boatClass.mediumMechanized"
  | "boatClass.largeMechanized"
  | "pfz.withinRange"
  | "pfz.outOfRange"
  | "header.connection"
  | "header.dataStatus"
  | "conn.online"
  | "conn.degraded"
  | "conn.offline"
  | "conn.checking"
  | "chat.title"
  | "chat.placeholder"
  | "chat.send"
  | "chat.clear"
  | "chat.retry"
  | "chat.suggested"
  | "chat.analyzing"
  | "chat.analyzingLong"
  | "chat.errorTitle"
  | "chat.emptyTitle"
  | "chat.emptyHint"
  | "chat.you"
  | "chat.orca"
  | "panel.decision"
  | "panel.risk"
  | "panel.suitability"
  | "panel.evidence"
  | "panel.conflicts"
  | "panel.reference"
  | "panel.provenance"
  | "panel.alerts"
  | "panel.activity"
  | "panel.explanation"
  | "panel.report"
  | "tab.decision"
  | "tab.details"
  | "tab.evidence"
  | "tab.provenance"
  | "tab.alerts"
  | "tab.activity"
  | "panel.marineDetails"
  | "nav.sections"
  | "nav.returnToWorkspace"
  | "nav.engineRoom"
  | "nav.sos"
  | "panel.engineRoom"
  | "sos.title"
  | "sos.lead"
  | "sos.disclaimer"
  | "sos.step1.title"
  | "sos.category.flooding"
  | "sos.category.fire"
  | "sos.category.collision"
  | "sos.category.manOverboard"
  | "sos.category.disabled"
  | "sos.category.medical"
  | "sos.category.severeWeather"
  | "sos.category.security"
  | "sos.step2.title"
  | "sos.vesselName"
  | "sos.vesselNamePlaceholder"
  | "sos.personsAboard"
  | "sos.boatClassHint"
  | "sos.gps.get"
  | "sos.gps.requesting"
  | "sos.gps.denied"
  | "sos.gps.unavailable"
  | "sos.gps.notYet"
  | "sos.step3.title"
  | "sos.step3.selectFirst"
  | "sos.action.speak"
  | "sos.action.copy"
  | "sos.action.copied"
  | "sos.action.copyUnsupported"
  | "sos.action.call"
  | "sos.action.sms"
  | "sos.action.whatsapp"
  | "sos.checklist.title"
  | "sos.checklist.lead"
  | "sos.checklist.epirb"
  | "sos.checklist.sart"
  | "sos.checklist.liferaft"
  | "sos.checklist.pfd"
  | "sos.checklist.grabbag"
  | "sos.checklist.fireExtinguisher"
  | "sos.checklist.firstAid"
  | "sos.checklist.radioCharged"
  | "phase.understanding"
  | "phase.collection"
  | "phase.core"
  | "phase.route"
  | "phase.intelligence"
  | "phase.output"
  | "kind.llm"
  | "kind.deterministic"
  | "kind.data"
  | "stage.understand"
  | "stage.normalize"
  | "stage.plan"
  | "stage.weather"
  | "stage.ocean"
  | "stage.gis"
  | "stage.environment"
  | "stage.advisory"
  | "stage.fabric"
  | "stage.temporal"
  | "stage.fusion"
  | "stage.arbitration"
  | "stage.conflicts"
  | "stage.suitability"
  | "stage.risk"
  | "stage.policy"
  | "stage.decision"
  | "stage.route"
  | "stage.route.reasonNotAllowed"
  | "stage.route.reasonNotRequested"
  | "stage.alerts"
  | "stage.whatif"
  | "stage.pfz"
  | "stage.productivity"
  | "stage.environmentalComparison"
  | "stage.environmentalStability"
  | "stage.environmentalAnomaly"
  | "stage.environmentalNeighbourhood"
  | "stage.environmentalEvidence"
  | "stage.research"
  | "stage.provenance"
  | "stage.explain"
  | "stage.assemble"
  | "activity.parallelNote"
  | "activity.intelligenceSummary"
  | "activity.showAll"
  | "activity.hideAll"
  | "engine.title"
  | "engine.subtitle"
  | "engine.noQuery"
  | "engine.thisTurn"
  | "engine.sources.title"
  | "engine.sources.desc"
  | "engine.fabric.title"
  | "engine.fabric.desc"
  | "engine.agents.title"
  | "engine.agents.desc"
  | "engine.core.title"
  | "engine.core.desc"
  | "engine.core.safetyNote"
  | "engine.output.title"
  | "engine.output.desc"
  | "engine.agent.understand.desc"
  | "engine.agent.weather.desc"
  | "engine.agent.ocean.desc"
  | "engine.agent.gis.desc"
  | "engine.agent.risk.desc"
  | "engine.agent.explain.desc"
  | "engine.agent.route.desc"
  | "decision.safetyStatus"
  | "decision.primaryFactors"
  | "decision.dataConfidence"
  | "decision.noSafeTitle"
  | "decision.noSafeBody"
  | "decision.missingConflicting"
  | "decision.warning.advisoryUnavailable"
  | "decision.warning.geofenceUnavailable"
  | "decision.warning.factorUnavailable"
  | "decision.warning.factorUnavailableCritical"
  | "riskFactor.wave"
  | "riskFactor.wind"
  | "riskFactor.lightningProxy"
  | "riskFactor.cycloneProxy"
  | "risk.overall"
  | "risk.contributing"
  | "risk.missingCritical"
  | "risk.dataSufficiency"
  | "risk.notComputed"
  | "suitability.derived"
  | "suitability.pfzNote"
  | "panel.advisory"
  | "advisory.distinctNote"
  | "advisory.area"
  | "advisory.status.no_warning"
  | "advisory.status.caution"
  | "advisory.status.do_not_venture"
  | "advisory.availability.unavailable"
  | "advisory.availability.expired"
  | "advisory.availability.not_yet_valid"
  | "advisory.availability.no_location_match"
  | "advisory.valid"
  | "advisory.validFrom"
  | "advisory.retrieved"
  | "advisory.retrievedLive"
  | "advisory.source"
  | "advisory.notApplicable"
  | "panel.geofence"
  | "geofence.status.inside"
  | "geofence.status.clear"
  | "geofence.status.unavailable"
  | "geofence.note.inside"
  | "geofence.note.clear"
  | "geofence.note.unavailable"
  | "panel.environmental"
  | "env.productivity"
  | "env.sst"
  | "env.chlorophyll"
  | "env.tide"
  | "env.tide.note"
  | "env.chlClass"
  | "env.confidence"
  | "env.dataSufficiency"
  | "env.limitations"
  | "env.derived"
  | "env.noFish"
  | "env.unavailable"
  | "env.suggestions"
  | "env.suggestion.historical"
  | "env.suggestion.seasonal"
  | "env.suggestion.combine"
  | "env.mapPoint"
  | "env.cmp.title"
  | "env.cmp.now"
  | "env.cmp.reference"
  | "env.cmp.delta"
  | "env.cmp.window"
  | "env.cmp.validity"
  | "env.cmp.higher"
  | "env.cmp.lower"
  | "env.cmp.unchanged"
  | "env.cmp.unknown"
  | "env.cmp.unavailable"
  | "env.cmp.note"
  | "env.ev.title"
  | "env.ev.status"
  | "env.ev.summary"
  | "env.ev.current"
  | "env.ev.historical"
  | "env.ev.source"
  | "env.ev.dataset"
  | "env.ev.observed"
  | "env.ev.validity"
  | "env.ev.distance"
  | "env.ev.tier"
  | "env.ev.reproducibility"
  | "env.ev.opticalHint"
  | "env.ev.bundle"
  | "env.ev.copyJson"
  | "env.ev.copied"
  | "env.ev.status.adequate"
  | "env.ev.status.limited"
  | "env.ev.status.insufficient"
  | "env.ev.status.unavailable"
  | "env.stab.title"
  | "env.stab.observations"
  | "env.stab.range"
  | "env.stab.median"
  | "env.stab.iqr"
  | "env.stab.quartiles"
  | "env.stab.coverage"
  | "env.stab.gaps"
  | "env.stab.insufficientProfile"
  | "env.stab.note"
  | "env.stab.status.adequate"
  | "env.stab.status.limited"
  | "env.stab.status.insufficient"
  | "env.stab.status.unavailable"
  | "env.nbhd.title"
  | "env.nbhd.pixels"
  | "env.nbhd.range"
  | "env.nbhd.median"
  | "env.nbhd.iqr"
  | "env.nbhd.nearest"
  | "env.nbhd.coverage"
  | "env.nbhd.placement"
  | "env.nbhd.placement.within"
  | "env.nbhd.placement.above"
  | "env.nbhd.placement.below"
  | "env.nbhd.placement.na"
  | "env.nbhd.insufficientProfile"
  | "env.nbhd.note"
  | "env.nbhd.status.adequate"
  | "env.nbhd.status.limited"
  | "env.nbhd.status.insufficient"
  | "env.nbhd.status.unavailable"
  | "env.anom.title"
  | "env.anom.subtitle"
  | "env.anom.percentile"
  | "env.anom.percentileSuffix"
  | "env.anom.range"
  | "env.anom.median"
  | "env.anom.diffFromMedian"
  | "env.anom.observations"
  | "env.anom.currentUnavailable"
  | "env.anom.insufficientProfile"
  | "env.anom.howCalculated"
  | "env.anom.methodologyFallback"
  | "env.anom.status.ok"
  | "env.anom.status.currentUnavailable"
  | "env.anom.status.insufficientHistory"
  | "env.anom.class.below"
  | "env.anom.class.within"
  | "env.anom.class.above"
  | "env.anom2.current"
  | "env.anom2.recentMedian"
  | "env.anom2.difference"
  | "env.anom2.position"
  | "env.anom2.dataCoverage"
  | "env.anom2.lastDays"
  | "env.anom2.daysLabel"
  | "env.anom2.windowLabel"
  | "env.anom2.dataUnavailable"
  | "env.anom2.insufficientData"
  | "env.anom2.isAbove"
  | "env.anom2.isWithin"
  | "env.anom2.isBelow"
  | "panel.route"
  | "route.status"
  | "route.distance"
  | "route.cost"
  | "route.violations"
  | "route.noneTitle"
  | "route.reason"
  | "route.notRequested"
  | "route.validated"
  | "route.marineAware"
  | "route.marineAwareNote"
  | "route.marinePenalty"
  | "evidence.source"
  | "evidence.type"
  | "evidence.status"
  | "evidence.tier"
  | "evidence.none"
  | "conflict.detected"
  | "conflict.none"
  | "conflict.type"
  | "conflict.severity"
  | "conflict.resolution"
  | "conflict.safetyAffected"
  | "reference.pfzTitle"
  | "reference.snapshot"
  | "reference.validUntil"
  | "reference.view"
  | "reference.notOrca"
  | "reference.none"
  | "provenance.title"
  | "provenance.why"
  | "provenance.none"
  | "provenance.inspect"
  | "alerts.none"
  | "alerts.proxyNote"
  | "activity.title"
  | "activity.done"
  | "activity.skipped"
  | "activity.pending"
  | "activity.failed"
  | "activity.timingMeasured"
  | "activity.timingUnavailable"
  | "activity.correlation"
  | "activity.total"
  | "explanation.why"
  | "explanation.disclaimer"
  | "verdict.why"
  | "verdict.location"
  | "verdict.observed"
  | "verdict.riskBreakdown"
  | "verdict.fullExplanation"
  | "verdict.envContext"
  | "verdict.operationalDetail"
  | "verdict.whatIf"
  | "evidence.reviewed"
  | "map.layers"
  | "map.legend"
  | "map.legend.live"
  | "map.legend.reference"
  | "map.legend.derived"
  | "map.legend.demo"
  | "map.legend.missing"
  | "map.noGeometry"
  | "map.orcaRoute"
  | "map.noRoute"
  | "map.origin"
  | "map.destination"
  | "map.routeDestinationN"
  | "tab.trip"
  | "panel.tripPlanner"
  | "panel.routeComparison"
  | "panel.routeAnalytics"
  | "trip.origin"
  | "trip.destination"
  | "trip.departure"
  | "trip.availableTime"
  | "trip.workDuration"
  | "trip.vesselSpeed"
  | "trip.vesselSpeedHint"
  | "trip.returnDeadline"
  | "trip.optional"
  | "trip.unit.minutes"
  | "trip.unit.knots"
  | "trip.feasibility.title"
  | "trip.status.FEASIBLE"
  | "trip.status.INFEASIBLE_TIME"
  | "trip.status.INFEASIBLE_RETURN_DEADLINE"
  | "trip.status.BLOCKED_ROUTE"
  | "trip.status.NO_SAFE_RECOMMENDATION"
  | "trip.status.MISSING_DATA"
  | "trip.time.departure"
  | "trip.time.outbound"
  | "trip.time.work"
  | "trip.time.return"
  | "trip.time.total"
  | "trip.time.available"
  | "trip.time.remaining"
  | "trip.time.estimatedReturn"
  | "trip.time.returnBy"
  | "trip.time.buffer"
  | "trip.caution"
  | "trip.safetyWindowNote"
  | "trip.pfzReferenceLabel"
  | "trip.noRoute"
  | "route.compare.title"
  | "route.compare.baseline"
  | "route.compare.baselineBlocked"
  | "route.compare.orca"
  | "route.compare.metric"
  | "route.compare.distance"
  | "route.compare.violations"
  | "route.compare.feasible"
  | "route.compare.yes"
  | "route.compare.no"
  | "route.compare.explanation"
  | "route.compare.loading"
  | "route.compare.unavailable"
  | "route.compare.noRoute"
  | "route.compare.baselineLabel"
  | "route.compare.definitionNote"
  | "analytics.distance"
  | "analytics.waypoints"
  | "analytics.violations"
  | "analytics.feasible"
  | "analytics.safetyStatus"
  | "analytics.constrainedSegmentsAvoided"
  | "tour.tripPlanner.title"
  | "tour.tripPlanner.body"
  | "tour.routeCompare.title"
  | "tour.routeCompare.body"
  | "layer.group.marineBase"
  | "layer.group.orcaAnalysis"
  | "layer.group.fishingEnvironment"
  | "layer.badge.orca"
  | "layer.badge.incois"
  | "layer.badge.live"
  | "layer.badge.pointData"
  | "layer.source.reference"
  | "layer.source.orca"
  | "layer.source.incois"
  | "layer.source.live"
  | "layer.risk"
  | "layer.coastline"
  | "layer.eez"
  | "layer.protected_areas"
  | "layer.geofences"
  | "layer.route"
  | "layer.pfz"
  | "layer.pfz.noGeometry"
  | "layer.pfz.noLocationMatch"
  | "layer.pfz.checking"
  | "layer.pfz.zoneCount"
  | "layer.pfz.landingCentreOnly"
  | "layer.sst"
  | "layer.chlorophyll"
  | "layer.sst.available"
  | "layer.sst.unavailable"
  | "layer.chlorophyll.available"
  | "layer.chlorophyll.unavailable"
  | "layer.environmentalSuitability"
  | "layer.environmentalSuitability.noLocation"
  | "map.layers.expand"
  | "map.layers.collapse"
  | "map.layers.active"
  | "layer.desc.coastline"
  | "layer.desc.eez"
  | "layer.desc.protected_areas"
  | "layer.desc.geofences"
  | "layer.desc.risk"
  | "layer.desc.route"
  | "layer.desc.environmental"
  | "layer.desc.environmentalSuitability"
  | "layer.desc.pfz"
  | "env.suitability.title"
  | "env.suitability.disclaimer"
  | "env.suitability.insufficientData"
  | "env.suitability.legend.low"
  | "env.suitability.legend.moderate"
  | "env.suitability.legend.high"
  | "gps.use"
  | "gps.requesting"
  | "gps.granted"
  | "gps.denied"
  | "gps.unavailable"
  | "gps.markerLabel"
  | "pfz.selectedTitle"
  | "pfz.selectedTitleMulti"
  | "pfz.selectedMarkerLabel"
  | "pfz.selectedMarkerLabelMulti"
  | "pfz.navigate"
  | "pfz.navigateMulti"
  | "pfz.removeSelection"
  | "pfz.notSafetyNote"
  | "pfz.clearSelection"
  | "pfz.cannotRoute"
  | "pfz.direction"
  | "pfz.bearing"
  | "pfz.distance"
  | "pfz.depth"
  | "pfz.forecast"
  | "pfz.validUntil"
  | "pfz.officialSource"
  | "pfz.ranked.title"
  | "pfz.ranked.subtitle"
  | "pfz.ranked.distanceKm"
  | "pfz.ranked.restricted"
  | "pfz.ranked.projected"
  | "pfz.ranked.selectHint"
  | "pfz.ranked.markerTooltip"
  | "pfz.ranked.empty"
  | "pfz.ranked.unavailable"
  | "pfz.ranked.noLocationMatch"
  | "pfz.ranked.landingCentreOnly"
  | "pfz.ranked.checking"
  | "pfz.ranked.available"
  | "pfz.ranked.layerHidden"
  | "pfz.ranked.expand"
  | "pfz.ranked.collapse"
  | "route.myLocationToPfz"
  | "route.myLocationToPfzs"
  | "route.myLocationToPfzZone"
  | "mapSidebar.toggleShow"
  | "mapSidebar.toggleHide"
  | "mapTools.title"
  | "routeControls.title"
  | "routeControls.noSelection"
  | "routeControls.destination"
  | "routeControls.pfzLabel"
  | "routeControls.computing"
  | "routeControls.notRoutedYet"
  | "routeControls.statusAvailable"
  | "routeControls.statusBlocked"
  | "routeControls.statusUnavailable"
  | "routeControls.waypoints"
  | "routeControls.routeButton"
  | "routeControls.viewRoute"
  | "routeControls.expand"
  | "routeControls.collapse"
  | "routeControls.originAdjusted"
  | "env.interp"
  | "env.interp.limited"
  | "env.interp.limitedNote"
  | "env.ev.qualityNote"
  | "voice.mic.start"
  | "voice.mic.stop"
  | "voice.mic.unsupported"
  | "voice.mic.error"
  | "voice.mic.permissionDenied"
  | "voice.mic.deviceUnavailable"
  | "voice.mic.insecureContext"
  | "voice.listening"
  | "voice.tts.play"
  | "voice.tts.stop"
  | "voice.tts.unsupported"
  | "voice.speaking"
  | "tour.start"
  | "tour.skip"
  | "tour.back"
  | "tour.next"
  | "tour.finish"
  | "tour.stepOf"
  | "tour.overview.title"
  | "tour.overview.body"
  | "tour.ask.title"
  | "tour.ask.body"
  | "tour.liveData.title"
  | "tour.liveData.body"
  | "tour.decision.title"
  | "tour.decision.body"
  | "tour.why.title"
  | "tour.why.body"
  | "tour.safety.title"
  | "tour.safety.body"
  | "tour.replay.title"
  | "tour.replay.body"
  | "tour.route.title"
  | "tour.route.body"
  | "tour.evidence.title"
  | "tour.evidence.body"
  | "tour.environmental.title"
  | "tour.environmental.body"
  | "tour.engineRoom.title"
  | "tour.engineRoom.body"
  | "evidence.export"
  | "evidence.export.success"
  | "evidence.export.failure"
  | "replay.title"
  | "replay.emptyNote"
  | "replay.intro"
  | "replay.explore"
  | "replay.building"
  | "replay.genericError"
  | "replay.noTimestamps"
  | "replay.bannerTitle"
  | "replay.bannerSubtitle"
  | "replay.windowLabel"
  | "replay.howItWorks"
  | "replay.howItWorksBody"
  | "replay.forecastAt"
  | "replay.timestampSlider"
  | "replay.trajectoryLabel"
  | "replay.changeFromPrevious"
  | "replay.baselineNote"
  | "replay.decisionStable"
  | "replay.decisionStableBody"
  | "replay.whyChanged"
  | "replay.decisionChangedBadge"
  | "replay.whatChanged"
  | "replay.riskDeltaLabel"
  | "replay.safetyTriggerLabel"
  | "replay.wave"
  | "replay.wind"
  | "replay.sst"
  | "replay.risk"
  | "replay.safety"
  | "replay.decisionRemains"
  | "replay.riskFactorsAt"
  | "replay.total"
  | "replay.safetyCheck"
  | "replay.deterministicSafety"
  | "replay.safetyRuleSingular"
  | "replay.safetyRulePlural"
  | "replay.pipelineCaption"
  | "replay.previous"
  | "replay.next"
  | "replay.pause"
  | "replay.playLabel"
  | "replay.dataCoverage"
  | "replay.disclaimerBody"
  | "replay.noPreviousHour"
  | "replay.vsPrev"
  | "replay.legendProceed"
  | "replay.legendCaution"
  | "replay.legendDoNotProceed"
  | "replay.chartTitle"
  | "replay.chartInsufficientData"
  | "replay.previewSuffix"
  | "replay.chartRowAria"
  | "common.expand"
  | "common.collapse"
  | "common.print"
  | "common.close"
  | "common.na"
  | "nav.authority"
  | "authority.title"
  | "authority.subtitle"
  | "authority.dataEdition.live"
  | "authority.dataEdition.demo"
  | "authority.edition.live"
  | "authority.edition.demo"
  | "authority.demoFixtureNotice"
  | "authority.detail.demoFixtureNotice"
  | "authority.updated"
  | "authority.refresh"
  | "authority.loading"
  | "authority.error"
  | "authority.retry"
  | "authority.locationsMonitored"
  | "authority.activeWarnings"
  | "authority.statusDistribution"
  | "authority.map"
  | "authority.mapLegend"
  | "authority.attentionRequired"
  | "authority.noAttention"
  | "authority.locations"
  | "authority.locationsTable.location"
  | "authority.locationsTable.status"
  | "authority.locationsTable.warning"
  | "authority.locationsTable.data"
  | "authority.locationsTable.updated"
  | "authority.warnings"
  | "authority.noWarnings"
  | "authority.dataHealth"
  | "authority.dataHealth.weather"
  | "authority.dataHealth.marine"
  | "authority.noLocations"
  | "authority.noLocationsHint"
  | "authority.selectLocation"
  | "authority.detail.wave"
  | "authority.detail.wind"
  | "authority.detail.warnings"
  | "authority.detail.geofence"
  | "authority.detail.dataConfidence"
  | "authority.detail.decision"
  | "authority.detail.evidence"
  | "authority.detail.evidenceSources"
  | "authority.detail.openToday"
  | "authority.detail.planTrip"
  | "authority.detail.viewSystem"
  | "authority.detail.viewTrace"
  | "authority.detail.viewEvidence"
  | "authority.detail.viewReplay"
  | "authority.detail.exportEvidence"
  | "authority.detail.source"
  | "authority.detail.derivedSource"
  | "authority.geofence.clear"
  | "authority.geofence.inside"
  | "authority.geofence.unavailable"
  | "authority.attentionCategory.official_warning"
  | "authority.attentionCategory.extreme"
  | "authority.attentionCategory.high"
  | "authority.attentionCategory.blocked"
  | "authority.attentionCategory.geofence"
  | "authority.attentionCategory.data_quality"
  | "authority.attentionCategory.unavailable";

type Table = Record<StringKey, string>;

const en: Table = {
  "app.subtitle": "Marine Intelligence",
  "landing.brand.tagline": "Oceanic Reasoning & Collaborative Agents",
  "landing.hero.headline": "Ocean Intelligence. Reasoned Decisions. Safer Marine Operations.",
  "landing.hero.subtext":
    "ORCA brings weather, ocean, environmental, advisory and geospatial evidence together through collaborative AI agents and deterministic safety rules to support marine decisions.",
  "landing.hero.ctaPrimary": "Launch ORCA",
  "landing.hero.ctaSecondary": "How ORCA Reasons",
  "landing.hero.disclaimer":
    "A decision-support system for the human decision-maker — not a replacement for official warnings, autonomous navigation, or guaranteed catch prediction.",
  "landing.pipeline.title": "How ORCA Reasons",
  "landing.pipeline.step.query": "User Query",
  "landing.pipeline.step.agents": "Collaborative AI Agents",
  "landing.pipeline.step.fabric": "Marine Data Fabric",
  "landing.pipeline.step.arbitration": "Evidence Arbitration",
  "landing.pipeline.step.risk": "Deterministic Risk & Safety",
  "landing.pipeline.step.decision": "Decision",
  "landing.pipeline.step.output": "Evidence + Route + Explanation",
  "landing.pipeline.note":
    "AI reasons about the query. Deterministic code computes and enforces safety. Evidence supports the decision. The human makes the final call.",
  "landing.sources.title": "What ORCA Reasons Over",
  "landing.sources.note":
    "Not every source is live at all times. ORCA always discloses whether a value is live, reference, demo, or unavailable.",
  "landing.sources.weather": "Weather",
  "landing.sources.ocean": "Oceanographic Conditions",
  "landing.sources.sst": "Sea Surface Temperature",
  "landing.sources.chl": "Chlorophyll-a",
  "landing.sources.pfz": "PFZ / Advisory References",
  "landing.sources.gis": "GIS & Geofencing",
  "landing.sources.safety": "Marine Safety Constraints",
  "landing.sources.evidence": "Environmental Evidence",
  "landing.why.title": "Why ORCA",
  "landing.why.item1": "Collaborative marine AI agents",
  "landing.why.item2": "Deterministic safety enforcement",
  "landing.why.item3": "Evidence-backed decisions",
  "landing.why.item4": "Conflict-aware reasoning",
  "landing.why.item5": "Constraint-aware routing",
  "landing.why.item6": "Decision provenance",
  "landing.why.item7": "Replayable decisions",
  "landing.why.item8": "Human remains the final decision maker",
  "landing.preview.title": "Inside a Decision",
  "landing.preview.decision": "Decision",
  "landing.preview.safety": "Safety",
  "landing.preview.suitability": "Fishing Suitability",
  "landing.preview.route": "Route",
  "landing.preview.evidence": "Evidence",
  "landing.preview.cta": "Enter ORCA",
  "landing.footer.tagline": "Marine Ecosystem Reasoning with Collaborative Agents",
  "landing.footer.problem": "SIH26176",
  "landing.footer.sponsor": "ISRO",
  "header.stakeholder": "Context",
  "header.boatClass": "Boat class",
  "header.boatClassNotSet": "Not set",
  "header.language": "Language",
  "boatClass.traditionalNonmotorized": "Traditional / non-motorised craft",
  "boatClass.smallMotorized": "Small motorised boat (under 10 m)",
  "boatClass.mediumMechanized": "Medium mechanised boat (10-15 m)",
  "boatClass.largeMechanized": "Large mechanised vessel (over 15 m)",
  "pfz.withinRange": "Within your boat's range",
  "pfz.outOfRange": "Beyond your boat's declared range",
  "header.connection": "Backend",
  "header.dataStatus": "Data",
  "conn.online": "Online",
  "conn.degraded": "Degraded",
  "conn.offline": "Backend unavailable",
  "conn.checking": "Checking…",
  "chat.title": "Ask ORCA",
  "chat.placeholder": "Ask a marine question…",
  "chat.send": "Send",
  "chat.clear": "Clear",
  "chat.retry": "Retry",
  "chat.suggested": "Suggested questions",
  "chat.analyzing": "ORCA is analyzing marine conditions…",
  "chat.analyzingLong":
    "Still working — ORCA runs weather, ocean and risk reasoning before answering; some queries take a little longer.",
  "chat.errorTitle": "Request failed",
  "chat.emptyTitle": "Start a marine assessment",
  "chat.emptyHint": "Pick a context above, then ask a question or choose a suggestion.",
  "chat.you": "You",
  "chat.orca": "ORCA",
  "panel.decision": "Decision",
  "panel.risk": "Marine Risk",
  "panel.suitability": "Fishing Suitability",
  "panel.evidence": "Evidence",
  "panel.conflicts": "Evidence Conflicts",
  "panel.reference": "Official References",
  "panel.provenance": "Decision Provenance",
  "panel.alerts": "Alerts",
  "panel.activity": "ORCA Activity",
  "panel.explanation": "Why this decision?",
  "panel.report": "Report",
  "tab.decision": "Decision",
  "tab.details": "Details",
  "tab.evidence": "Evidence",
  "tab.provenance": "Provenance",
  "tab.alerts": "Alerts",
  "tab.activity": "Activity",
  "panel.marineDetails": "Marine Details",
  "nav.sections": "Sections",
  "nav.returnToWorkspace": "Return to Workspace",
  "nav.engineRoom": "Engine Room",
  "nav.sos": "Emergency (SOS)",
  "sos.title": "Emergency Distress",
  "sos.lead": "Build a standard Mayday radio script and reach the Indian Coast Guard - works even with a weak signal, and needs no ORCA query first.",
  "sos.disclaimer": "This page composes a distress message for you to send yourself (by voice call, radio, SMS or WhatsApp). It does not contact anyone automatically and does not replace VHF Channel 16 or a real Coast Guard call in a genuine emergency.",
  "sos.step1.title": "1. What is the emergency?",
  "sos.category.flooding": "Taking on water",
  "sos.category.fire": "Fire on board",
  "sos.category.collision": "Collision",
  "sos.category.manOverboard": "Man overboard",
  "sos.category.disabled": "Disabled / adrift",
  "sos.category.medical": "Medical emergency",
  "sos.category.severeWeather": "Severe weather",
  "sos.category.security": "Piracy / security threat",
  "sos.step2.title": "2. Your details",
  "sos.vesselName": "Vessel name",
  "sos.vesselNamePlaceholder": "e.g. Matsya Rani",
  "sos.personsAboard": "Persons on board",
  "sos.boatClassHint": "Boat class on file: {cls}",
  "sos.gps.get": "Get my position",
  "sos.gps.requesting": "Getting position...",
  "sos.gps.denied": "Location permission denied - enter your position by radio from memory if you can.",
  "sos.gps.unavailable": "Location is not available on this device.",
  "sos.gps.notYet": "Position not yet acquired.",
  "sos.step3.title": "3. Send for help",
  "sos.step3.selectFirst": "Select an emergency type above to generate your distress message.",
  "sos.action.speak": "Read aloud",
  "sos.action.copy": "Copy text",
  "sos.action.copied": "Copied",
  "sos.action.copyUnsupported": "Copy isn't available on this device - please read or photograph the message above.",
  "sos.action.call": "Call Coast Guard ({number})",
  "sos.action.sms": "Share by SMS",
  "sos.action.whatsapp": "Share by WhatsApp",
  "sos.checklist.title": "Pre-departure safety checklist",
  "sos.checklist.lead": "Saved on this device only. Check before every trip.",
  "sos.checklist.epirb": "EPIRB (emergency beacon) on board and tested",
  "sos.checklist.sart": "SART / radar transponder on board",
  "sos.checklist.liferaft": "Life raft on board and in date",
  "sos.checklist.pfd": "Life jackets (PFDs) for every person on board",
  "sos.checklist.grabbag": "Grab-bag packed (torch, whistle, flares, water)",
  "sos.checklist.fireExtinguisher": "Fire extinguisher on board and checked",
  "sos.checklist.firstAid": "First-aid kit on board",
  "sos.checklist.radioCharged": "VHF radio / phone fully charged",
  "panel.engineRoom": "ORCA Engine Room",
  "phase.understanding": "Understanding",
  "phase.collection": "Parallel Data Collection",
  "phase.core": "Deterministic Reasoning Core",
  "phase.route": "Routing",
  "phase.intelligence": "Environmental & Reference Intelligence",
  "phase.output": "Output & Provenance",
  "kind.llm": "LLM interpretation",
  "kind.deterministic": "Deterministic",
  "kind.data": "Data intelligence",
  "stage.understand": "Query Understanding",
  "stage.normalize": "Normalize / resolve location",
  "stage.plan": "Execution Planning",
  "stage.weather": "Weather Intelligence",
  "stage.ocean": "Oceanographic Intelligence",
  "stage.gis": "GIS & Geofencing",
  "stage.environment": "Ocean-colour agent",
  "stage.advisory": "Marine advisory agent",
  "stage.fabric": "Marine Data Fabric",
  "stage.temporal": "Temporal Validity Gate",
  "stage.fusion": "Spatial-Temporal Fusion",
  "stage.arbitration": "Evidence Arbitration",
  "stage.conflicts": "Conflict Detection",
  "stage.suitability": "Fishing Suitability Engine",
  "stage.risk": "Risk Engine",
  "stage.policy": "Policy & Safety Guard",
  "stage.decision": "Decision Engine",
  "stage.route": "Route Agent (A*)",
  "stage.route.reasonNotAllowed": "safety status does not permit routing",
  "stage.route.reasonNotRequested": "no route requested",
  "stage.alerts": "Alert Synthesis",
  "stage.whatif": "What-if Simulation",
  "stage.pfz": "PFZ Reference Lookup",
  "stage.productivity": "Environmental Productivity",
  "stage.environmentalComparison": "Environmental Comparison",
  "stage.environmentalStability": "Environmental Stability",
  "stage.environmentalAnomaly": "Environmental Anomaly Lens",
  "stage.environmentalNeighbourhood": "Environmental Neighbourhood",
  "stage.environmentalEvidence": "Environmental Evidence & Reproducibility",
  "stage.research": "Research Mode",
  "stage.provenance": "Provenance Graph",
  "stage.explain": "Evidence & Explanation",
  "stage.assemble": "Assemble Response",
  "activity.parallelNote": "{ran} of {total} parallel branches ran",
  "activity.intelligenceSummary": "{ran} ran · {skipped} not applicable to this query",
  "activity.showAll": "Show all stages",
  "activity.hideAll": "Hide inapplicable stages",
  "engine.title": "ORCA Engine Room",
  "engine.subtitle": "How ORCA is constructed - live status overlaid for the current turn",
  "engine.noQuery": "No query yet. Ask ORCA a question to overlay this turn's live status.",
  "engine.thisTurn": "This turn",
  "engine.sources.title": "Data Sources",
  "engine.sources.desc": "External providers ORCA reads from, each stamped with its live, cached, reference or demo status.",
  "engine.fabric.title": "Marine Data Fabric",
  "engine.fabric.desc": "Normalises every agent result, gates it by validity window, fuses and arbitrates disagreement.",
  "engine.agents.title": "Specialized Agents",
  "engine.agents.desc": "Seven agent modules. Two interpret with an LLM; the rest are deterministic or pure data intelligence.",
  "engine.core.title": "Deterministic Reasoning Core",
  "engine.core.desc": "No LLM, no network, no randomness. Same input and configuration always produce the same output.",
  "engine.core.safetyNote": "Hard geofence → missing evidence → SEVERE → HIGH/MODERATE → ALLOWED. The LLM cannot change this outcome.",
  "engine.output.title": "Output",
  "engine.output.desc": "The decision, an optional route, the provenance graph and a grounded explanation reach chat, map, alerts and reports.",
  "engine.agent.understand.desc": "Language detection, intent & entity extraction",
  "engine.agent.weather.desc": "Wind, precipitation, forecast conditions",
  "engine.agent.ocean.desc": "Wave height, period, sea state",
  "engine.agent.gis.desc": "Geofences, EEZ, protected areas, depth",
  "engine.agent.risk.desc": "Deterministic risk & suitability coordination",
  "engine.agent.explain.desc": "Grounded natural-language explanation",
  "engine.agent.route.desc": "A* planning with hard-geofence validation",
  "decision.safetyStatus": "Safety status",
  "decision.primaryFactors": "Primary factors",
  "decision.dataConfidence": "Data confidence",
  "decision.noSafeTitle": "NO SAFE RECOMMENDATION",
  "decision.noSafeBody":
    "Critical evidence required for a reliable safety decision is unavailable or unresolved. ORCA will not fabricate a recommendation.",
  "decision.missingConflicting": "Missing / conflicting evidence",
  "decision.warning.advisoryUnavailable":
    "No active official advisory is currently available for this location. ORCA is using the latest available weather, ocean and safety data.",
  "decision.warning.geofenceUnavailable":
    "Some geofence data is unavailable; the assessment is based only on verified available constraints.",
  "decision.warning.factorUnavailable":
    "No {factor} data is currently available; the overall score reflects only the factors ORCA could verify.",
  "decision.warning.factorUnavailableCritical":
    "Safety-critical {factor} data is unavailable; ORCA applies a conservative safety margin until it can be verified.",
  "riskFactor.wave": "wave height",
  "riskFactor.wind": "wind speed",
  "riskFactor.lightningProxy": "lightning/thunderstorm",
  "riskFactor.cycloneProxy": "cyclone",
  "risk.overall": "Overall risk",
  "risk.contributing": "Contributing factors",
  "risk.missingCritical": "Missing safety-critical data",
  "risk.dataSufficiency": "Data sufficiency",
  "risk.notComputed": "Risk was not computed for this query.",
  "suitability.derived": "ORCA-derived — separate from operational safety",
  "suitability.pfzNote": "PFZ reference",
  "panel.advisory": "Official Marine Advisory",
  "advisory.distinctNote":
    "IMD advisory reference — an optional official source, separate from ORCA's computed risk assessment below.",
  "advisory.area": "Marine area",
  "advisory.status.no_warning": "No Warning",
  "advisory.status.caution": "Caution",
  "advisory.status.do_not_venture": "Fishermen advised not to venture into the sea",
  "advisory.availability.unavailable":
    "Optional IMD advisory reference unavailable; ORCA's independent safety assessment remains active.",
  "advisory.availability.expired": "Advisory has expired",
  "advisory.availability.not_yet_valid": "Advisory not yet in force",
  "advisory.availability.no_location_match": "No official advisory area for this location",
  "advisory.valid": "Valid",
  "advisory.validFrom": "Valid from",
  "advisory.retrieved": "Retrieved",
  "advisory.retrievedLive": "Live",
  "advisory.source": "Source",
  "advisory.notApplicable": "Not applicable to the requested time",
  "panel.geofence": "Geofence Check",
  "geofence.status.inside": "Inside a restricted area",
  "geofence.status.clear": "Geofence validation: CLEAR",
  "geofence.status.unavailable": "Geofence validation unavailable",
  "geofence.note.inside":
    "This location is inside a hard-restricted geofenced zone; ORCA's safety decision and routing already reflect this.",
  "geofence.note.clear":
    "ORCA checked this location against its currently loaded spatial reference data and found no hard-restricted-zone constraint triggered.",
  "geofence.note.unavailable":
    "Geofence data is currently unavailable, so restricted-area clearance could not be verified for this location. This is not the same as the area being clear.",
  "panel.environmental": "Environmental Context",
  "env.productivity": "Environmental productivity potential",
  "env.sst": "Sea-surface temperature",
  "env.chlorophyll": "Chlorophyll-a",
  "env.tide": "Modelled sea level",
  "env.tide.note": "Modelled sea-level signal, not an official tide-gauge observation. Not for coastal navigation.",
  "env.chlClass": "Chlorophyll level",
  "env.confidence": "Confidence",
  "env.dataSufficiency": "Data sufficiency",
  "env.limitations": "Limitations",
  "env.derived": "ORCA-derived from chlorophyll-a alone — environmental context only, never a safety input. SST is context, not a driver.",
  "env.noFish": "Chlorophyll-a reflects phytoplankton biomass. It is not a measure of fish presence, abundance or catch.",
  "env.unavailable": "unavailable",
  "env.suggestions": "Researcher next steps",
  "env.suggestion.historical": "Compare with historical climatology for this location and season.",
  "env.suggestion.seasonal": "Inspect seasonal phytoplankton patterns before reading a single snapshot.",
  "env.suggestion.combine": "Combine with in-situ nutrient, salinity or primary-productivity observations.",
  "env.mapPoint": "Environmental sample point",
  "env.cmp.title": "Compared with an earlier observation",
  "env.cmp.now": "now",
  "env.cmp.reference": "reference",
  "env.cmp.delta": "difference",
  "env.cmp.window": "Reference window",
  "env.cmp.validity": "validity",
  "env.cmp.higher": "higher than reference",
  "env.cmp.lower": "lower than reference",
  "env.cmp.unchanged": "unchanged from reference",
  "env.cmp.unknown": "not comparable",
  "env.cmp.unavailable": "A temporal comparison could not be computed.",
  "env.cmp.note": "The reference is an ORCA-computed value over a recent past window, not a climatological normal. A single difference is not a trend.",
  "env.ev.title": "Evidence & reproducibility",
  "env.ev.status": "Evidence quality",
  "env.ev.summary": "Summary",
  "env.ev.current": "current",
  "env.ev.historical": "historical / reference",
  "env.ev.source": "source",
  "env.ev.dataset": "dataset",
  "env.ev.observed": "observed",
  "env.ev.validity": "validity",
  "env.ev.distance": "pixel distance",
  "env.ev.tier": "tier",
  "env.ev.reproducibility": "reproducibility",
  "env.ev.opticalHint": "Coastal-water context",
  "env.ev.bundle": "Reproducibility bundle",
  "env.ev.copyJson": "Copy as JSON",
  "env.ev.copied": "Copied",
  "env.ev.status.adequate": "ADEQUATE",
  "env.ev.status.limited": "LIMITED",
  "env.ev.status.insufficient": "INSUFFICIENT",
  "env.ev.status.unavailable": "UNAVAILABLE",
  "env.stab.title": "Dispersion & coverage",
  "env.stab.observations": "observations",
  "env.stab.range": "range",
  "env.stab.median": "median",
  "env.stab.iqr": "IQR",
  "env.stab.quartiles": "Q1 / Q3",
  "env.stab.coverage": "coverage",
  "env.stab.gaps": "gaps",
  "env.stab.insufficientProfile":
    "Fewer than three observations in the window - no dispersion statistics were computed.",
  "env.stab.note":
    "This describes observed environmental data coverage and dispersion within a bounded window. It is not a trend, a forecast or a fishing indicator.",
  "env.stab.status.adequate": "ADEQUATE",
  "env.stab.status.limited": "LIMITED",
  "env.stab.status.insufficient": "INSUFFICIENT",
  "env.stab.status.unavailable": "UNAVAILABLE",
  "env.nbhd.title": "Local representativeness",
  "env.nbhd.pixels": "nearby pixels",
  "env.nbhd.range": "range",
  "env.nbhd.median": "median",
  "env.nbhd.iqr": "IQR",
  "env.nbhd.nearest": "nearest valid pixel",
  "env.nbhd.coverage": "coverage",
  "env.nbhd.placement": "central pixel",
  "env.nbhd.placement.within": "within the nearby range",
  "env.nbhd.placement.above": "above the nearby range",
  "env.nbhd.placement.below": "below the nearby range",
  "env.nbhd.placement.na": "not placed",
  "env.nbhd.insufficientProfile":
    "Fewer than three valid nearby pixels on this composite - no neighbourhood statistics were computed.",
  "env.nbhd.note":
    "This only compares the single central chlorophyll-a pixel with the valid nearby pixels on the same satellite composite. It is a descriptive representativeness check, not a spatial map, a productivity estimate or a fishing indicator.",
  "env.nbhd.status.adequate": "ADEQUATE",
  "env.nbhd.status.limited": "LIMITED",
  "env.nbhd.status.insufficient": "INSUFFICIENT",
  "env.nbhd.status.unavailable": "UNAVAILABLE",
  "env.anom.title": "Environmental Anomaly Lens",
  "env.anom.subtitle": "Recent-distribution analysis · position within recent observations",
  "env.anom.percentile": "Percentile",
  "env.anom.percentileSuffix": "th percentile",
  "env.anom.range": "range",
  "env.anom.median": "median",
  "env.anom.diffFromMedian": "vs median",
  "env.anom.observations": "observations",
  "env.anom.currentUnavailable":
    "The current observation is unavailable; no recent-distribution position could be determined.",
  "env.anom.insufficientProfile":
    "Fewer than three valid historical observations in the window - no recent-distribution position was computed.",
  "env.anom.howCalculated": "How is this calculated?",
  "env.anom.methodologyFallback":
    "The current observation is positioned against valid observations from the existing bounded recent window. Invalid or missing values are excluded, never interpolated. A minimum of three valid historical observations is required.",
  "env.anom.status.ok": "POSITIONED",
  "env.anom.status.currentUnavailable": "UNAVAILABLE",
  "env.anom.status.insufficientHistory": "INSUFFICIENT",
  "env.anom.class.below": "BELOW RECENT RANGE",
  "env.anom.class.within": "WITHIN RECENT DISTRIBUTION",
  "env.anom.class.above": "ABOVE RECENT RANGE",
  "env.anom2.current": "Current",
  "env.anom2.recentMedian": "Recent median",
  "env.anom2.difference": "Difference",
  "env.anom2.position": "Position",
  "env.anom2.dataCoverage": "Data coverage",
  "env.anom2.lastDays": "Last",
  "env.anom2.daysLabel": "days",
  "env.anom2.windowLabel": "{days}-DAY OBSERVATION WINDOW",
  "env.anom2.dataUnavailable": "DATA UNAVAILABLE",
  "env.anom2.insufficientData": "INSUFFICIENT DATA",
  "env.anom2.isAbove": "is above the recent interquartile range.",
  "env.anom2.isWithin": "is within the recent distribution.",
  "env.anom2.isBelow": "is below the recent interquartile range.",
  "panel.route": "Route",
  "route.status": "Status",
  "route.distance": "Distance",
  "route.cost": "Grid path cost",
  "route.violations": "Hard geofence violations",
  "route.noneTitle": "NO SAFE ROUTE",
  "route.reason": "Reason",
  "route.notRequested": "No routing was requested for this query.",
  "route.validated": "Route validated by ORCA Route Agent",
  "tab.trip": "Trip",
  "panel.tripPlanner": "Fisher Trip Planner",
  "panel.routeComparison": "Route Comparison",
  "panel.routeAnalytics": "Route Analytics",
  "trip.origin": "Origin",
  "trip.destination": "Destination",
  "trip.departure": "Departure",
  "trip.availableTime": "Available trip time",
  "trip.workDuration": "Fishing / work duration",
  "trip.vesselSpeed": "Vessel speed",
  "trip.vesselSpeedHint": "Travel time requires a vessel speed.",
  "trip.returnDeadline": "Return by (optional)",
  "trip.optional": "optional",
  "trip.unit.minutes": "min",
  "trip.unit.knots": "kn",
  "trip.feasibility.title": "Trip Feasibility",
  "trip.status.FEASIBLE": "TRIP FEASIBLE",
  "trip.status.INFEASIBLE_TIME": "NOT ENOUGH TIME",
  "trip.status.INFEASIBLE_RETURN_DEADLINE": "RETURN DEADLINE EXCEEDED",
  "trip.status.BLOCKED_ROUTE": "BLOCKED",
  "trip.status.NO_SAFE_RECOMMENDATION": "NO SAFE RECOMMENDATION",
  "trip.status.MISSING_DATA": "MORE INFORMATION NEEDED",
  "trip.time.departure": "Departure",
  "trip.time.outbound": "Outbound",
  "trip.time.work": "Fishing / work",
  "trip.time.return": "Return",
  "trip.time.total": "Total",
  "trip.time.available": "Available",
  "trip.time.remaining": "Remaining",
  "trip.time.estimatedReturn": "Estimated return",
  "trip.time.returnBy": "Return by",
  "trip.time.buffer": "Buffer",
  "trip.caution": "The current decision is CAUTION - review conditions before departing.",
  "trip.safetyWindowNote": "Current decision applies to the evaluated time.",
  "trip.pfzReferenceLabel": "REFERENCE / OFFICIAL ADVISORY DATA — not generated by ORCA",
  "trip.noRoute": "Plan a route first (ask ORCA or select a destination on the map) to use the Trip Planner.",
  "route.compare.title": "Direct vs ORCA Route",
  "route.compare.baseline": "BASELINE (straight line)",
  "route.compare.baselineBlocked": "BASELINE (blocked)",
  "route.compare.orca": "ORCA ROUTE",
  "route.compare.metric": "Metric",
  "route.compare.distance": "Distance",
  "route.compare.violations": "Hard violations",
  "route.compare.feasible": "Feasible",
  "route.compare.yes": "YES",
  "route.compare.no": "NO",
  "route.compare.explanation": "ORCA route is {diff} longer because the direct line crosses: {names}",
  "route.compare.loading": "Computing baseline comparison…",
  "route.compare.unavailable": "Baseline comparison unavailable.",
  "route.compare.noRoute": "No route to compare yet.",
  "route.compare.baselineLabel": "Baseline = the straight geodesic line between origin and destination - not a routing algorithm, only a reference for comparison.",
  "route.compare.definitionNote": "\"Direct\" means the unconstrained straight line - not a recommended or safe route.",
  "analytics.distance": "Total distance",
  "analytics.waypoints": "Waypoints",
  "analytics.violations": "Hard geofence violations",
  "analytics.feasible": "Route feasible",
  "analytics.safetyStatus": "Safety status",
  "analytics.constrainedSegmentsAvoided": "Restricted crossings avoided vs. direct line",
  "tour.tripPlanner.title": "Fisher Trip Planner",
  "tour.tripPlanner.body": "Set your available time, fishing duration and vessel speed to see a deterministic trip feasibility check for the current route.",
  "tour.routeCompare.title": "Route Comparison",
  "tour.routeCompare.body": "Compare the ORCA constraint-aware route with the direct straight-line baseline - distance, time and restricted-area crossings, side by side.",
  "route.marineAware": "Marine-aware route",
  "route.marineAwareNote": "Wave/wind conditions included in route cost",
  "route.marinePenalty": "Marine cost penalty",
  "evidence.source": "Source",
  "evidence.type": "Type",
  "evidence.status": "Status",
  "evidence.tier": "Tier",
  "evidence.none": "No evidence records for this query.",
  "conflict.detected": "Evidence conflict detected",
  "conflict.none": "No conflicts detected.",
  "conflict.type": "Type",
  "conflict.severity": "Severity",
  "conflict.resolution": "Resolution",
  "conflict.safetyAffected": "Safety-critical",
  "reference.pfzTitle": "INCOIS PFZ",
  "reference.snapshot": "Reference snapshot",
  "reference.validUntil": "Valid until",
  "reference.view": "View advisory",
  "reference.notOrca":
    "Official reference snapshot. NOT an ORCA-derived prediction.",
  "reference.none": "No official references attached to this query.",
  "provenance.title": "How ORCA reached this decision",
  "provenance.why": "Query → Evidence → Reasoning → Safety → Decision",
  "provenance.none": "No provenance graph available for this query.",
  "provenance.inspect": "Select a node to inspect",
  "alerts.none": "No alerts for this query.",
  "alerts.proxyNote":
    "Thunderstorm and cyclone indications are model-derived proxies, not certified real-time detection.",
  "activity.title": "Agent execution",
  "activity.done": "done",
  "activity.skipped": "skipped",
  "activity.pending": "not run",
  "activity.failed": "failed",
  "activity.timingMeasured": "Per-stage timing is measured server-side (elapsed, not simulated).",
  "activity.timingUnavailable": "Execution status only — no per-stage timing in this response.",
  "activity.correlation": "Correlation ID",
  "activity.total": "Total measured",
  "explanation.why": "Why this decision?",
  "explanation.disclaimer":
    "ORCA is a decision-support system. Verify official marine and weather advisories before operational action.",
  "verdict.why": "Why",
  "verdict.location": "Location",
  "verdict.observed": "Conditions observed",
  "verdict.riskBreakdown": "Risk breakdown",
  "verdict.fullExplanation": "Full explanation",
  "verdict.envContext": "Environmental & research context",
  "verdict.operationalDetail": "Operational detail",
  "verdict.whatIf": "What-if simulation",
  "evidence.reviewed": "evidence records reviewed",
  "map.layers": "Map layers",
  "map.legend": "Data provenance",
  "map.legend.live": "Live observation / forecast",
  "map.legend.reference": "Official reference snapshot",
  "map.legend.derived": "Computed by ORCA",
  "map.legend.demo": "Illustrative / demo data",
  "map.legend.missing": "Unavailable",
  "map.noGeometry": "No geometry available for this query.",
  "map.orcaRoute": "ORCA Route",
  "map.noRoute": "No safe route",
  "map.origin": "Origin",
  "map.destination": "Destination",
  "map.routeDestinationN": "PFZ {n} of {count}",
  "layer.group.marineBase": "Marine base",
  "layer.group.orcaAnalysis": "ORCA analysis",
  "layer.group.fishingEnvironment": "Fishing & environment",
  "layer.badge.orca": "ORCA",
  "layer.badge.incois": "INCOIS",
  "layer.badge.live": "LIVE",
  "layer.badge.pointData": "POINT DATA",
  "layer.source.reference": "Official reference layer",
  "layer.source.orca": "Computed by ORCA",
  "layer.source.incois": "INCOIS official reference",
  "layer.source.live": "Live observation",
  "layer.risk": "Risk",
  "layer.coastline": "Coastline",
  "layer.eez": "Indian EEZ",
  "layer.protected_areas": "Protected areas",
  "layer.geofences": "Geofences",
  "layer.route": "Route",
  "layer.pfz": "INCOIS PFZ Reference",
  "layer.pfz.noLocationMatch": "No official INCOIS PFZ advisory matches this exact location.",
  "layer.pfz.checking": "Checking official INCOIS PFZ availability…",
  "layer.pfz.noGeometry":
    "Official INCOIS reference unavailable for map rendering at this location.",
  "layer.pfz.zoneCount": "Official INCOIS reference — {count} zone(s)",
  "layer.pfz.landingCentreOnly":
    "No PFZ zone advisory for today — showing the nearest official INCOIS reference landing centre.",
  "layer.sst": "Sea surface temperature",
  "layer.chlorophyll": "Chlorophyll-a",
  "layer.sst.available":
    "Open-Meteo Marine value — shown on the Environmental sample point marker (no gridded overlay).",
  "layer.sst.unavailable":
    "SST unavailable for this query — no valid Open-Meteo Marine value.",
  "layer.chlorophyll.available":
    "NOAA CoastWatch (VIIRS) value — shown on the Environmental sample point marker (no gridded overlay).",
  "layer.chlorophyll.unavailable":
    "Chlorophyll-a unavailable — likely satellite cloud / data coverage or validity constraints. No value is shown.",
  "layer.environmentalSuitability": "ORCA Environmental Suitability",
  "layer.environmentalSuitability.noLocation": "Ask ORCA about a location first to load this layer.",
  "map.layers.expand": "Show map layer controls",
  "map.layers.collapse": "Hide map layer controls",
  "map.layers.active": "{count} on",
  "layer.desc.coastline": "India's coastal boundary",
  "layer.desc.eez": "India's exclusive economic zone",
  "layer.desc.protected_areas": "Marine/coastal protected regions",
  "layer.desc.geofences": "Restricted hard-exclusion boundaries",
  "layer.desc.risk": "ORCA safety risk assessment",
  "layer.desc.route": "ORCA evaluated route — not a guaranteed safe path",
  "layer.desc.environmental": "Environmental sample point for this query",
  "layer.desc.environmentalSuitability": "CHL-based spatial suitability grid (research/reference context)",
  "layer.desc.pfz": "Official INCOIS PFZ reference — not ORCA-derived",
  "env.suitability.title": "ORCA Environmental Suitability",
  "env.suitability.disclaimer": "Environmental context only — not a fish-presence or safety prediction.",
  "env.suitability.insufficientData": "Insufficient environmental data for a suitability visualization here.",
  "env.suitability.legend.low": "Low",
  "env.suitability.legend.moderate": "Moderate",
  "env.suitability.legend.high": "Higher",
  "gps.use": "Use my current location",
  "gps.requesting": "Requesting location…",
  "gps.granted": "Using your current location",
  "gps.denied": "Location permission denied",
  "gps.unavailable": "Current location unavailable",
  "gps.markerLabel": "My current location",
  "pfz.selectedTitle": "INCOIS PFZ Reference selected",
  "pfz.selectedTitleMulti": "{count} INCOIS PFZ references selected",
  "pfz.selectedMarkerLabel": "Selected PFZ reference",
  "pfz.selectedMarkerLabelMulti": "Selected PFZ {n}",
  "pfz.navigate": "Navigate to this PFZ",
  "pfz.navigateMulti": "Route through all {count} selected PFZs",
  "pfz.removeSelection": "Remove selection {n}",
  "pfz.notSafetyNote": "PFZ reference is not a safety recommendation.",
  "pfz.clearSelection": "Clear selection",
  "pfz.cannotRoute": "Selected PFZ reference cannot be safely routed to.",
  "pfz.direction": "Direction",
  "pfz.bearing": "Bearing",
  "pfz.distance": "Distance",
  "pfz.depth": "Depth",
  "pfz.forecast": "Forecast",
  "pfz.validUntil": "Valid until",
  "pfz.officialSource": "Official INCOIS reference",
  "pfz.ranked.title": "Ranked PFZ zones",
  "pfz.ranked.subtitle": "Nearest official INCOIS zones, ranked by distance",
  "pfz.ranked.distanceKm": "{km} km away",
  "pfz.ranked.restricted": "Restricted",
  "pfz.ranked.projected": "Computed reference",
  "pfz.ranked.selectHint": "Select a zone to highlight it on the map",
  "pfz.ranked.markerTooltip": "PFZ zone {n} — {km} km",
  "pfz.ranked.empty": "No matched PFZ zones near this location",
  "pfz.ranked.unavailable": "No official INCOIS PFZ reference is currently available for this location or date. ORCA does not generate or estimate PFZ locations. You can still assess sea-going safety and environmental conditions separately.",
  "pfz.ranked.noLocationMatch": "No official INCOIS PFZ advisory matches this exact location today. You can still assess sea-going safety and environmental conditions separately.",
  "pfz.ranked.landingCentreOnly": "No ranked PFZ zone lines match this location today. A nearest official INCOIS reference landing centre is shown on the map and in the chat answer instead.",
  "pfz.ranked.checking": "Checking for official INCOIS PFZ zones…",
  "pfz.ranked.available": "{count} available",
  "pfz.ranked.layerHidden": "PFZ layer is hidden — turn on INCOIS PFZ Reference in Map Layers to see and select these zones.",
  "pfz.ranked.expand": "Show ranked PFZ zones",
  "pfz.ranked.collapse": "Hide ranked PFZ zones",
  "route.myLocationToPfz": "My Location → INCOIS PFZ Reference",
  "route.myLocationToPfzs": "My Location → {count} selected INCOIS PFZ References",
  "route.myLocationToPfzZone": "My Location → INCOIS PFZ #{n}",
  "mapSidebar.toggleShow": "Show map sidebar",
  "mapSidebar.toggleHide": "Hide map sidebar",
  "mapTools.title": "Map Tools",
  "routeControls.title": "Route Controls",
  "routeControls.noSelection": "Select a ranked PFZ zone to route there.",
  "routeControls.destination": "Destination",
  "routeControls.pfzLabel": "INCOIS PFZ #{n}",
  "routeControls.computing": "Computing route…",
  "routeControls.notRoutedYet": "Not yet routed to this destination.",
  "routeControls.statusAvailable": "ROUTE AVAILABLE",
  "routeControls.statusBlocked": "BLOCKED",
  "routeControls.statusUnavailable": "ROUTE UNAVAILABLE",
  "routeControls.waypoints": "Waypoints",
  "routeControls.routeButton": "Route to PFZ #{n}",
  "routeControls.viewRoute": "View Route",
  "routeControls.expand": "Show route controls",
  "routeControls.collapse": "Hide route controls",
  "routeControls.originAdjusted": "Routing origin: nearest navigable sea cell (reference origin is on land)",
  "env.interp": "Productivity interpretation",
  "env.interp.limited": "LIMITED",
  "env.interp.limitedNote":
    "Chlorophyll-a unavailable; environmental productivity potential cannot be assessed.",
  "env.ev.qualityNote":
    "Whether the underlying SST / chlorophyll-a observations are valid, sourced and timestamped — separate from whether productivity could be interpreted.",
  "voice.mic.start": "Speak your question",
  "voice.mic.stop": "Stop listening",
  "voice.mic.unsupported": "Speech input is not supported in this browser",
  "voice.mic.error": "Microphone recording failed — you can still type your question",
  "voice.mic.permissionDenied":
    "Microphone permission denied — allow access in your browser to use voice input, or type your question",
  "voice.mic.deviceUnavailable": "No microphone device found — you can still type your question",
  "voice.mic.insecureContext":
    "Voice input needs a secure (HTTPS or localhost) connection — you can still type your question",
  "voice.listening": "Listening…",
  "voice.tts.play": "Read aloud",
  "voice.tts.stop": "Stop reading",
  "voice.tts.unsupported": "Read aloud is not supported in this browser",
  "voice.speaking": "Speaking…",
  "tour.start": "Start Tour",
  "tour.skip": "Skip",
  "tour.back": "Back",
  "tour.next": "Next",
  "tour.finish": "Finish",
  "tour.stepOf": "{current} of {total}",
  "tour.overview.title": "Welcome to ORCA",
  "tour.overview.body":
    "ORCA is a marine decision-support system for fishers, disaster managers and researchers. This tour walks through the real interface — nothing here is a mock-up.",
  "tour.ask.title": "Ask a marine question",
  "tour.ask.body":
    "Type a question here, or pick one of the suggested queries below. Your question goes through ORCA's real pipeline — understanding, data collection, deterministic risk and safety evaluation, then a decision.",
  "tour.liveData.title": "Live marine & weather data",
  "tour.liveData.body":
    "This panel controls the map layers — live wave, wind, sea-surface temperature and official INCOIS/IMD reference data ORCA fetches for your query location.",
  "tour.decision.title": "The decision",
  "tour.decision.body":
    "Once ORCA has an answer, this card shows the operational verdict — PROCEED, PROCEED WITH CAUTION or DO NOT PROCEED — computed deterministically, never guessed by the AI.",
  "tour.why.title": "Why this decision?",
  "tour.why.body":
    "These are the actual reasons behind the verdict, taken directly from the Risk Engine and Safety Guard — never an invented explanation.",
  "tour.safety.title": "Safety guard",
  "tour.safety.body":
    "Safety is evaluated separately from risk by a deterministic Safety Guard, and can override everything else — the one thing the AI layer can never change.",
  "tour.replay.title": "Decision replay",
  "tour.replay.body":
    "Explore how this same decision evolves hour by hour across the forecast window — re-run through the identical deterministic pipeline, never a second live decision.",
  "tour.route.title": "Route planning",
  "tour.route.body":
    "When a route is requested, ORCA plans it against real geofences, protected areas and marine conditions, and refuses a route that crosses a hard safety boundary.",
  "tour.evidence.title": "Evidence & provenance",
  "tour.evidence.body":
    "Every value ORCA used to reach this decision is listed here with its source, tier and validity, so the decision can be independently checked.",
  "tour.environmental.title": "Environmental research",
  "tour.environmental.body":
    "For researchers: sea-surface temperature, chlorophyll-a and related context — descriptive only, never used to predict a catch or guarantee a fishing outcome.",
  "tour.engineRoom.title": "Engine Room",
  "tour.engineRoom.body":
    "ORCA's actual architecture, and for the last query, the real agent execution trace — exactly which steps ran, in what order, and how long each took.",
  "evidence.export": "Export Evidence",
  "evidence.export.success": "Evidence exported",
  "evidence.export.failure": "Evidence export failed",
  "replay.title": "Decision replay",
  "replay.emptyNote":
    "Run an assessment first, then explore how the decision evolves over the available forecast window here.",
  "replay.intro":
    "See how marine conditions, risk and the deterministic decision evolve across the available hourly forecast - derived from the same forecast data already fetched for this assessment.",
  "replay.explore": "Explore decision over time →",
  "replay.building": "Building replay...",
  "replay.genericError": "The decision replay could not be run.",
  "replay.noTimestamps": "No forecast timestamps were available to replay.",
  "replay.bannerTitle": "ORCA DECISION REPLAY",
  "replay.bannerSubtitle": "How the marine decision evolves over time",
  "replay.windowLabel": "FORECAST · {hours}H",
  "replay.howItWorks": "How it works",
  "replay.howItWorksBody":
    "Replay evaluates each available forecast hour through the same deterministic Risk → Safety → Decision pipeline. It does not create a second live decision.",
  "replay.forecastAt": "FORECAST · {time}",
  "replay.timestampSlider": "Replay timestamp",
  "replay.trajectoryLabel": "Hourly decision trajectory",
  "replay.changeFromPrevious": "Change from previous hour",
  "replay.baselineNote": "Baseline timestamp — no previous hour available.",
  "replay.decisionStable": "Decision stable",
  "replay.decisionStableBody": "Decision remains {decision} across this interval.",
  "replay.whyChanged": "Why did the decision change?",
  "replay.decisionChangedBadge": "DECISION CHANGED",
  "replay.whatChanged": "What changed?",
  "replay.riskDeltaLabel": "Risk",
  "replay.safetyTriggerLabel": "Safety rule triggered:",
  "replay.wave": "Wave",
  "replay.wind": "Wind",
  "replay.sst": "SST",
  "replay.risk": "Risk",
  "replay.safety": "Safety",
  "replay.decisionRemains": "Decision remains {decision}",
  "replay.riskFactorsAt": "Risk factors — {time}",
  "replay.total": "Total",
  "replay.safetyCheck": "Safety check",
  "replay.deterministicSafety": "DETERMINISTIC SAFETY",
  "replay.safetyRuleSingular": "Safety rule",
  "replay.safetyRulePlural": "Safety rules",
  "replay.pipelineCaption": "Risk Engine → Safety Guard → Decision",
  "replay.previous": "Previous",
  "replay.next": "Next",
  "replay.pause": "Pause",
  "replay.playLabel": "REPLAY {hours}H",
  "replay.dataCoverage": "Data coverage",
  "replay.disclaimerBody":
    "{label}. This walks forecast data already fetched for this assessment through ORCA's deterministic Risk, Safety and Decision engines - it is not a second live decision.",
  "replay.noPreviousHour": "no previous hour",
  "replay.vsPrev": "vs prev",
  "replay.legendProceed": "Proceed",
  "replay.legendCaution": "Caution",
  "replay.legendDoNotProceed": "Do not proceed",
  "replay.chartTitle": "Marine conditions & risk over time",
  "replay.chartInsufficientData": "Not enough forecast hours were returned to plot a trend.",
  "replay.previewSuffix": "(preview)",
  "replay.chartRowAria": "{label} over the replay window",
  "common.expand": "Expand",
  "common.collapse": "Collapse",
  "common.print": "Print / export",
  "common.close": "Close",
  "common.na": "n/a",

  // Milestone 5 - Authority / Operational Intelligence Dashboard
  "nav.authority": "Authority",
  "authority.title": "Coastal Operations",
  "authority.subtitle": "Operational overview across monitored coastal locations",
  "authority.dataEdition.live": "LIVE",
  "authority.dataEdition.demo": "DEMO DATA",
  "authority.demoFixtureNotice":
    "DEMO FIXTURE DATA — every location's status below is generated from a deterministic demo fixture, not a live evaluation of that location right now. The map and table still show each location's real position.",
  "authority.detail.demoFixtureNotice":
    "DEMO FIXTURE — this status was evaluated from a deterministic demo fixture, not from live conditions at {name} right now.",
  "authority.edition.live": "Live",
  "authority.edition.demo": "Demo data",
  "authority.updated": "Updated {time}",
  "authority.refresh": "Refresh",
  "authority.loading": "Loading coastal operations…",
  "authority.error": "Could not load the coastal operational overview.",
  "authority.retry": "Retry",
  "authority.locationsMonitored": "Locations monitored",
  "authority.activeWarnings": "Active warnings",
  "authority.statusDistribution": "Current Conditions",
  "authority.map": "Operational Map",
  "authority.mapLegend": "Status",
  "authority.attentionRequired": "Attention Required",
  "authority.noAttention": "No locations currently need attention.",
  "authority.locations": "Locations",
  "authority.locationsTable.location": "Location",
  "authority.locationsTable.status": "Status",
  "authority.locationsTable.warning": "Warning",
  "authority.locationsTable.data": "Data",
  "authority.locationsTable.updated": "Updated",
  "authority.warnings": "Official Warnings",
  "authority.noWarnings": "No active official warnings.",
  "authority.dataHealth": "Data Health",
  "authority.dataHealth.weather": "Weather",
  "authority.dataHealth.marine": "Marine",
  "authority.noLocations": "No operational locations available.",
  "authority.noLocationsHint": "ORCA could not evaluate any curated coastal location right now.",
  "authority.selectLocation": "Select a location for details",
  "authority.detail.wave": "Wave",
  "authority.detail.wind": "Wind",
  "authority.detail.warnings": "Warnings",
  "authority.detail.geofence": "Geofence",
  "authority.detail.dataConfidence": "Data confidence",
  "authority.detail.decision": "Decision",
  "authority.detail.evidence": "Evidence",
  "authority.detail.evidenceSources": "{count} sources",
  "authority.detail.openToday": "Open Today View",
  "authority.detail.planTrip": "Plan Trip",
  "authority.detail.viewSystem": "View System",
  "authority.detail.viewTrace": "View Execution Trace",
  "authority.detail.viewEvidence": "View Evidence",
  "authority.detail.viewReplay": "Decision Replay",
  "authority.detail.exportEvidence": "Export Evidence",
  "authority.detail.source": "Source",
  "authority.detail.derivedSource": "ORCA deterministic rule",
  "authority.geofence.clear": "No current violation",
  "authority.geofence.inside": "Inside restricted area",
  "authority.geofence.unavailable": "Unavailable",
  "authority.attentionCategory.official_warning": "Official warning",
  "authority.attentionCategory.extreme": "Extreme risk",
  "authority.attentionCategory.high": "High risk",
  "authority.attentionCategory.blocked": "Blocked",
  "authority.attentionCategory.geofence": "Geofence",
  "authority.attentionCategory.data_quality": "Data quality",
  "authority.attentionCategory.unavailable": "Unavailable",
};

const hi: Table = {
  ...en,
  "app.subtitle": "समुद्री बुद्धिमत्ता",
  "landing.brand.tagline": "महासागरीय तर्क एवं सहयोगी एजेंट",
  "landing.hero.headline": "समुद्री बुद्धिमत्ता। तर्कसंगत निर्णय। सुरक्षित समुद्री संचालन।",
  "landing.hero.subtext":
    "ORCA मौसम, समुद्र, पर्यावरण, परामर्श और भू-स्थानिक साक्ष्य को सहयोगी AI एजेंटों और निश्चयात्मक सुरक्षा नियमों के माध्यम से एक साथ लाकर समुद्री निर्णयों में सहायता करता है।",
  "landing.hero.ctaPrimary": "ORCA लॉन्च करें",
  "landing.hero.ctaSecondary": "ORCA कैसे तर्क करता है",
  "landing.hero.disclaimer":
    "यह मानव निर्णयकर्ता के लिए एक निर्णय-सहायता प्रणाली है — आधिकारिक चेतावनियों, स्वायत्त नेविगेशन, या गारंटीकृत मछली पकड़ने की भविष्यवाणी का विकल्प नहीं।",
  "landing.pipeline.title": "ORCA कैसे तर्क करता है",
  "landing.pipeline.step.query": "उपयोगकर्ता प्रश्न",
  "landing.pipeline.step.agents": "सहयोगी AI एजेंट",
  "landing.pipeline.step.fabric": "समुद्री डेटा फैब्रिक",
  "landing.pipeline.step.arbitration": "साक्ष्य मध्यस्थता",
  "landing.pipeline.step.risk": "निश्चयात्मक जोखिम और सुरक्षा",
  "landing.pipeline.step.decision": "निर्णय",
  "landing.pipeline.step.output": "साक्ष्य + मार्ग + स्पष्टीकरण",
  "landing.pipeline.note":
    "AI प्रश्न पर तर्क करता है। निश्चयात्मक कोड सुरक्षा की गणना और प्रवर्तन करता है। साक्ष्य निर्णय का समर्थन करता है। अंतिम निर्णय मनुष्य लेता है।",
  "landing.sources.title": "ORCA किन आंकड़ों पर तर्क करता है",
  "landing.sources.note":
    "हर स्रोत हर समय लाइव नहीं होता। ORCA हमेशा बताता है कि कोई मान लाइव, संदर्भ, डेमो, या अनुपलब्ध है।",
  "landing.sources.weather": "मौसम",
  "landing.sources.ocean": "समुद्री स्थितियाँ",
  "landing.sources.sst": "समुद्र सतह तापमान",
  "landing.sources.chl": "क्लोरोफिल-a",
  "landing.sources.pfz": "PFZ / परामर्श संदर्भ",
  "landing.sources.gis": "GIS और जियोफेंसिंग",
  "landing.sources.safety": "समुद्री सुरक्षा बाधाएँ",
  "landing.sources.evidence": "पर्यावरणीय साक्ष्य",
  "landing.why.title": "ORCA क्यों",
  "landing.why.item1": "सहयोगी समुद्री AI एजेंट",
  "landing.why.item2": "निश्चयात्मक सुरक्षा प्रवर्तन",
  "landing.why.item3": "साक्ष्य-समर्थित निर्णय",
  "landing.why.item4": "विरोधाभास-जागरूक तर्क",
  "landing.why.item5": "बाधा-जागरूक मार्ग निर्धारण",
  "landing.why.item6": "निर्णय उद्भव-श्रृंखला (प्रोवेनन्स)",
  "landing.why.item7": "पुनः चलाने योग्य निर्णय",
  "landing.why.item8": "अंतिम निर्णयकर्ता सदैव मनुष्य",
  "landing.preview.title": "एक निर्णय के भीतर",
  "landing.preview.decision": "निर्णय",
  "landing.preview.safety": "सुरक्षा",
  "landing.preview.suitability": "मछली पकड़ने की उपयुक्तता",
  "landing.preview.route": "मार्ग",
  "landing.preview.evidence": "साक्ष्य",
  "landing.preview.cta": "ORCA में प्रवेश करें",
  "landing.footer.tagline": "सहयोगी एजेंटों के साथ समुद्री पारिस्थितिकी तंत्र तर्क",
  "landing.footer.problem": "SIH26176",
  "landing.footer.sponsor": "ISRO",
  "header.stakeholder": "संदर्भ",
  "header.boatClass": "नाव वर्ग",
  "header.boatClassNotSet": "निर्धारित नहीं",
  "header.language": "भाषा",
  "boatClass.traditionalNonmotorized": "पारंपरिक / बिना इंजन वाली नाव",
  "boatClass.smallMotorized": "छोटी मोटर नाव (10 मीटर से कम)",
  "boatClass.mediumMechanized": "मध्यम यांत्रिक नाव (10-15 मीटर)",
  "boatClass.largeMechanized": "बड़ा यांत्रिक जहाज़ (15 मीटर से अधिक)",
  "pfz.withinRange": "आपकी नाव की सीमा के भीतर",
  "pfz.outOfRange": "आपकी नाव की घोषित सीमा से परे",
  "header.connection": "बैकएंड",
  "header.dataStatus": "डेटा",
  "conn.online": "ऑनलाइन",
  "conn.degraded": "आंशिक",
  "conn.offline": "बैकएंड उपलब्ध नहीं",
  "conn.checking": "जाँच हो रही है…",
  "chat.title": "ORCA से पूछें",
  "chat.placeholder": "एक समुद्री प्रश्न पूछें…",
  "chat.send": "भेजें",
  "chat.clear": "साफ़ करें",
  "chat.retry": "फिर कोशिश करें",
  "chat.suggested": "सुझाए गए प्रश्न",
  "chat.analyzing": "ORCA समुद्री परिस्थितियों का विश्लेषण कर रहा है…",
  "chat.analyzingLong":
    "अभी भी काम जारी है — उत्तर देने से पहले ORCA मौसम, समुद्र और जोखिम विश्लेषण करता है; कुछ प्रश्नों में थोड़ा अधिक समय लग सकता है।",
  "chat.errorTitle": "अनुरोध विफल",
  "chat.emptyTitle": "समुद्री आकलन शुरू करें",
  "chat.emptyHint": "ऊपर एक संदर्भ चुनें, फिर प्रश्न पूछें या सुझाव चुनें।",
  "chat.you": "आप",
  "chat.orca": "ORCA",
  "panel.decision": "निर्णय",
  "panel.risk": "समुद्री जोखिम",
  "panel.suitability": "मछली पकड़ने की उपयुक्तता",
  "panel.evidence": "साक्ष्य",
  "panel.conflicts": "साक्ष्य विरोध",
  "panel.reference": "आधिकारिक संदर्भ",
  "panel.provenance": "निर्णय की उत्पत्ति",
  "panel.alerts": "चेतावनियाँ",
  "panel.activity": "ORCA गतिविधि",
  "panel.explanation": "यह निर्णय क्यों?",
  "panel.report": "रिपोर्ट",
  "tab.decision": "निर्णय",
  "tab.details": "विवरण",
  "tab.evidence": "साक्ष्य",
  "tab.provenance": "उत्पत्ति",
  "tab.alerts": "चेतावनियाँ",
  "tab.activity": "गतिविधि",
  "panel.marineDetails": "समुद्री विवरण",
  "nav.sections": "अनुभाग",
  "nav.returnToWorkspace": "वर्कस्पेस पर लौटें",
  "nav.engineRoom": "इंजन रूम",
  "nav.sos": "आपातकाल (SOS)",
  "sos.title": "आपातकालीन संकट संदेश",
  "sos.lead": "एक मानक मेडे रेडियो संदेश तैयार करें और भारतीय तटरक्षक बल से संपर्क करें - कमज़ोर सिग्नल में भी काम करता है, और पहले किसी ORCA प्रश्न की ज़रूरत नहीं।",
  "sos.disclaimer": "यह पृष्ठ आपके लिए एक संकट संदेश तैयार करता है जिसे आप स्वयं भेजते हैं (कॉल, रेडियो, SMS या WhatsApp द्वारा)। यह अपने आप किसी से संपर्क नहीं करता और वास्तविक आपातकाल में VHF चैनल 16 या तटरक्षक बल को सीधे कॉल करने का विकल्प नहीं है।",
  "sos.step1.title": "1. आपातकाल क्या है?",
  "sos.category.flooding": "नाव में पानी भर रहा है",
  "sos.category.fire": "नाव में आग लगी है",
  "sos.category.collision": "टक्कर",
  "sos.category.manOverboard": "व्यक्ति समुद्र में गिरा",
  "sos.category.disabled": "नाव खराब / बहाव में",
  "sos.category.medical": "चिकित्सा आपातकाल",
  "sos.category.severeWeather": "गंभीर मौसम",
  "sos.category.security": "समुद्री डकैती / सुरक्षा खतरा",
  "sos.step2.title": "2. आपकी जानकारी",
  "sos.vesselName": "नाव का नाम",
  "sos.vesselNamePlaceholder": "उदा. मत्स्य रानी",
  "sos.personsAboard": "नाव पर लोगों की संख्या",
  "sos.boatClassHint": "दर्ज नाव वर्ग: {cls}",
  "sos.gps.get": "मेरी स्थिति प्राप्त करें",
  "sos.gps.requesting": "स्थिति प्राप्त हो रही है...",
  "sos.gps.denied": "स्थान अनुमति अस्वीकृत - यदि संभव हो तो अपनी स्थिति याद से रेडियो पर बताएँ।",
  "sos.gps.unavailable": "इस डिवाइस पर स्थान उपलब्ध नहीं है।",
  "sos.gps.notYet": "स्थिति अभी प्राप्त नहीं हुई।",
  "sos.step3.title": "3. मदद के लिए भेजें",
  "sos.step3.selectFirst": "अपना संकट संदेश बनाने के लिए ऊपर आपातकाल का प्रकार चुनें।",
  "sos.action.speak": "ज़ोर से पढ़ें",
  "sos.action.copy": "टेक्स्ट कॉपी करें",
  "sos.action.copied": "कॉपी हो गया",
  "sos.action.copyUnsupported": "इस डिवाइस पर कॉपी उपलब्ध नहीं है - कृपया ऊपर दिया संदेश पढ़ें या उसकी फ़ोटो लें।",
  "sos.action.call": "तटरक्षक बल को कॉल करें ({number})",
  "sos.action.sms": "SMS से साझा करें",
  "sos.action.whatsapp": "WhatsApp से साझा करें",
  "sos.checklist.title": "यात्रा-पूर्व सुरक्षा जांच-सूची",
  "sos.checklist.lead": "केवल इस डिवाइस पर सहेजी गई। हर यात्रा से पहले जांचें।",
  "sos.checklist.epirb": "EPIRB (आपातकालीन बीकन) नाव पर है और जांचा गया है",
  "sos.checklist.sart": "SART / रडार ट्रांसपोंडर नाव पर है",
  "sos.checklist.liferaft": "लाइफ राफ्ट नाव पर है और वैध है",
  "sos.checklist.pfd": "हर व्यक्ति के लिए लाइफ जैकेट (PFD) मौजूद है",
  "sos.checklist.grabbag": "ग्रैब-बैग तैयार है (टॉर्च, सीटी, फ्लेयर, पानी)",
  "sos.checklist.fireExtinguisher": "अग्निशामक यंत्र नाव पर है और जांचा गया है",
  "sos.checklist.firstAid": "प्राथमिक चिकित्सा किट नाव पर है",
  "sos.checklist.radioCharged": "VHF रेडियो / फ़ोन पूरी तरह चार्ज है",
  "panel.engineRoom": "ORCA इंजन रूम",
  "phase.understanding": "समझ",
  "phase.collection": "समानांतर डेटा संग्रहण",
  "phase.core": "निश्चित तर्क कोर",
  "phase.route": "मार्ग नियोजन",
  "phase.intelligence": "पर्यावरणीय एवं संदर्भ बुद्धिमत्ता",
  "phase.output": "परिणाम एवं उत्पत्ति",
  "kind.llm": "LLM व्याख्या",
  "kind.deterministic": "निश्चित",
  "kind.data": "डेटा बुद्धिमत्ता",
  "stage.understand": "प्रश्न समझ एजेंट",
  "stage.normalize": "स्थान सामान्यीकरण/समाधान",
  "stage.plan": "निष्पादन योजना एजेंट",
  "stage.weather": "मौसम बुद्धिमत्ता",
  "stage.ocean": "समुद्र विज्ञान बुद्धिमत्ता",
  "stage.gis": "GIS एवं जियोफेंसिंग",
  "stage.environment": "समुद्र-रंग एजेंट",
  "stage.advisory": "समुद्री सलाह एजेंट",
  "stage.fabric": "समुद्री डेटा फैब्रिक",
  "stage.temporal": "अस्थायी वैधता गेट",
  "stage.fusion": "स्थानिक-अस्थायी संलयन",
  "stage.arbitration": "साक्ष्य मध्यस्थता",
  "stage.conflicts": "विरोध पहचान",
  "stage.suitability": "मत्स्य उपयुक्तता इंजन",
  "stage.risk": "जोखिम इंजन",
  "stage.policy": "नीति एवं सुरक्षा गार्ड",
  "stage.decision": "निर्णय इंजन",
  "stage.route": "मार्ग एजेंट (A*)",
  "stage.route.reasonNotAllowed": "सुरक्षा स्थिति मार्ग की अनुमति नहीं देती",
  "stage.route.reasonNotRequested": "कोई मार्ग अनुरोधित नहीं",
  "stage.alerts": "चेतावनी संश्लेषण",
  "stage.whatif": "व्हाट-इफ सिमुलेशन",
  "stage.pfz": "PFZ संदर्भ खोज",
  "stage.productivity": "पर्यावरणीय उत्पादकता",
  "stage.environmentalComparison": "पर्यावरणीय तुलना",
  "stage.environmentalStability": "पर्यावरणीय स्थिरता",
  "stage.environmentalAnomaly": "पर्यावरणीय विसंगति लेंस",
  "stage.environmentalNeighbourhood": "पर्यावरणीय पड़ोस",
  "stage.environmentalEvidence": "पर्यावरणीय साक्ष्य एवं पुनरुत्पादनीयता",
  "stage.research": "अनुसंधान मोड",
  "stage.provenance": "उत्पत्ति ग्राफ",
  "stage.explain": "साक्ष्य एवं व्याख्या",
  "stage.assemble": "प्रतिक्रिया संयोजन",
  "activity.parallelNote": "{total} में से {ran} समानांतर शाखाएँ चलीं",
  "activity.intelligenceSummary": "{ran} चलीं · {skipped} इस प्रश्न पर लागू नहीं",
  "activity.showAll": "सभी चरण दिखाएँ",
  "activity.hideAll": "अलागू चरण छिपाएँ",
  "engine.title": "ORCA इंजन रूम",
  "engine.subtitle": "ORCA कैसे बना है - वर्तमान प्रश्न की लाइव स्थिति सहित",
  "engine.noQuery": "अभी कोई प्रश्न नहीं। इस प्रश्न की लाइव स्थिति देखने हेतु ORCA से कुछ पूछें।",
  "engine.thisTurn": "यह प्रश्न",
  "engine.sources.title": "डेटा स्रोत",
  "engine.sources.desc": "बाहरी स्रोत जिनसे ORCA डेटा पढ़ता है, प्रत्येक की लाइव, कैश, संदर्भ या डेमो स्थिति के साथ।",
  "engine.fabric.title": "समुद्री डेटा फैब्रिक",
  "engine.fabric.desc": "हर एजेंट परिणाम को सामान्य करता है, वैधता खिड़की से जाँचता है, साक्ष्य को मिलाता और मध्यस्थता करता है।",
  "engine.agents.title": "विशिष्ट एजेंट",
  "engine.agents.desc": "सात एजेंट मॉड्यूल। दो LLM से व्याख्या करते हैं; शेष निश्चित या शुद्ध डेटा बुद्धिमत्ता हैं।",
  "engine.core.title": "निश्चित तर्क कोर",
  "engine.core.desc": "कोई LLM नहीं, कोई नेटवर्क नहीं, कोई यादृच्छिकता नहीं। समान इनपुट व कॉन्फ़िगरेशन हमेशा समान परिणाम देते हैं।",
  "engine.core.safetyNote": "हार्ड जियोफेंस → अनुपलब्ध साक्ष्य → SEVERE → HIGH/MODERATE → ALLOWED। LLM यह परिणाम नहीं बदल सकता।",
  "engine.output.title": "परिणाम",
  "engine.output.desc": "निर्णय, वैकल्पिक मार्ग, उत्पत्ति ग्राफ और एक प्रामाणिक व्याख्या चैट, मानचित्र, चेतावनी और रिपोर्ट तक पहुँचते हैं।",
  "engine.agent.understand.desc": "भाषा पहचान, आशय एवं इकाई निष्कर्षण",
  "engine.agent.weather.desc": "हवा, वर्षा, पूर्वानुमान स्थितियाँ",
  "engine.agent.ocean.desc": "लहर ऊँचाई, अवधि, समुद्री स्थिति",
  "engine.agent.gis.desc": "जियोफेंस, EEZ, संरक्षित क्षेत्र, गहराई",
  "engine.agent.risk.desc": "निश्चित जोखिम एवं उपयुक्तता समन्वय",
  "engine.agent.explain.desc": "प्रामाणिक प्राकृतिक-भाषा व्याख्या",
  "engine.agent.route.desc": "हार्ड-जियोफेंस सत्यापन सहित A* योजना",
  "decision.safetyStatus": "सुरक्षा स्थिति",
  "decision.primaryFactors": "मुख्य कारक",
  "decision.dataConfidence": "डेटा विश्वास",
  "decision.noSafeTitle": "कोई सुरक्षित अनुशंसा नहीं",
  "decision.noSafeBody":
    "विश्वसनीय सुरक्षा निर्णय के लिए आवश्यक महत्वपूर्ण साक्ष्य उपलब्ध या हल नहीं हैं। ORCA अनुशंसा नहीं गढ़ेगा।",
  "decision.missingConflicting": "अनुपलब्ध / विरोधाभासी साक्ष्य",
  "decision.warning.advisoryUnavailable":
    "इस स्थान के लिए फ़िलहाल कोई सक्रिय आधिकारिक परामर्श उपलब्ध नहीं है। ORCA नवीनतम उपलब्ध मौसम, समुद्री और सुरक्षा डेटा का उपयोग कर रहा है।",
  "decision.warning.geofenceUnavailable":
    "कुछ जियोफेंस डेटा उपलब्ध नहीं है; आकलन केवल सत्यापित उपलब्ध बाधाओं पर आधारित है।",
  "decision.warning.factorUnavailable":
    "{factor} डेटा फ़िलहाल उपलब्ध नहीं है; समग्र स्कोर केवल उन कारकों को दर्शाता है जिन्हें ORCA सत्यापित कर सका।",
  "decision.warning.factorUnavailableCritical":
    "सुरक्षा-महत्वपूर्ण {factor} डेटा उपलब्ध नहीं है; जब तक इसे सत्यापित नहीं किया जा सकता, ORCA एक सतर्क सुरक्षा मार्जिन लागू करता है।",
  "riskFactor.wave": "लहर की ऊँचाई",
  "riskFactor.wind": "हवा की गति",
  "riskFactor.lightningProxy": "बिजली/आंधी",
  "riskFactor.cycloneProxy": "चक्रवात",
  "risk.overall": "कुल जोखिम",
  "risk.contributing": "योगदान करने वाले कारक",
  "risk.missingCritical": "अनुपलब्ध सुरक्षा-महत्वपूर्ण डेटा",
  "risk.dataSufficiency": "डेटा पर्याप्तता",
  "risk.notComputed": "इस प्रश्न के लिए जोखिम की गणना नहीं की गई।",
  "suitability.derived": "ORCA-निर्मित — सुरक्षा से अलग",
  "suitability.pfzNote": "PFZ संदर्भ",
  "panel.advisory": "आधिकारिक समुद्री सलाह",
  "advisory.distinctNote":
    "IMD सलाह संदर्भ — यह एक वैकल्पिक आधिकारिक स्रोत है, नीचे दिए गए ORCA के अपने गणना किए गए जोखिम आकलन से अलग।",
  "advisory.area": "समुद्री क्षेत्र",
  "advisory.status.no_warning": "कोई चेतावनी नहीं",
  "advisory.status.caution": "सावधानी",
  "advisory.status.do_not_venture": "मछुआरों को समुद्र में न जाने की सलाह",
  "advisory.availability.unavailable":
    "वैकल्पिक IMD सलाह संदर्भ अनुपलब्ध है; ORCA का स्वतंत्र सुरक्षा आकलन सक्रिय है।",
  "advisory.availability.expired": "सलाह समाप्त हो चुकी है",
  "advisory.availability.not_yet_valid": "सलाह अभी प्रभावी नहीं है",
  "advisory.availability.no_location_match": "इस स्थान के लिए कोई आधिकारिक सलाह क्षेत्र नहीं",
  "advisory.valid": "मान्य",
  "advisory.validFrom": "इस समय से मान्य",
  "advisory.retrieved": "प्राप्त किया गया",
  "advisory.retrievedLive": "लाइव",
  "advisory.source": "स्रोत",
  "advisory.notApplicable": "अनुरोधित समय पर लागू नहीं",
  "panel.geofence": "जियोफेंस जांच",
  "geofence.status.inside": "प्रतिबंधित क्षेत्र के भीतर",
  "geofence.status.clear": "जियोफेंस सत्यापन: स्पष्ट (CLEAR)",
  "geofence.status.unavailable": "जियोफेंस सत्यापन अनुपलब्ध",
  "geofence.note.inside":
    "यह स्थान एक कठोर-प्रतिबंधित जियोफेंस क्षेत्र के भीतर है; ORCA का सुरक्षा निर्णय और मार्ग-निर्धारण पहले से ही इसे दर्शाते हैं।",
  "geofence.note.clear":
    "ORCA ने इस स्थान की जांच अपने वर्तमान में लोड किए गए स्थानिक संदर्भ डेटा के विरुद्ध की और कोई कठोर-प्रतिबंधित-क्षेत्र बाधा सक्रिय नहीं पाई।",
  "geofence.note.unavailable":
    "जियोफेंस डेटा फिलहाल अनुपलब्ध है, इसलिए इस स्थान के लिए प्रतिबंधित-क्षेत्र मंजूरी सत्यापित नहीं की जा सकी। यह क्षेत्र के स्पष्ट (clear) होने के समान नहीं है।",
  "panel.environmental": "पर्यावरणीय संदर्भ",
  "env.productivity": "पर्यावरणीय उत्पादकता क्षमता",
  "env.sst": "समुद्री सतह तापमान",
  "env.chlorophyll": "क्लोरोफिल-a",
  "env.tide": "मॉडल-आधारित समुद्र-स्तर",
  "env.tide.note": "मॉडल-व्युत्पन्न समुद्र-स्तर संकेत, आधिकारिक ज्वार-गेज प्रेक्षण नहीं। तटीय नौवहन के लिए नहीं।",
  "env.chlClass": "क्लोरोफिल स्तर",
  "env.confidence": "विश्वास",
  "env.dataSufficiency": "डेटा पर्याप्तता",
  "env.limitations": "सीमाएँ",
  "env.derived": "केवल क्लोरोफिल-a से ORCA-निर्मित — केवल पर्यावरणीय संदर्भ, सुरक्षा इनपुट नहीं। SST संदर्भ है, चालक नहीं।",
  "env.noFish": "क्लोरोफिल-a पादपप्लवक जैवभार दर्शाता है। यह मछली की उपस्थिति, बहुतायत या पकड़ का माप नहीं है।",
  "env.unavailable": "अनुपलब्ध",
  "env.suggestions": "शोधकर्ता के अगले कदम",
  "env.suggestion.historical": "इस स्थान और मौसम के लिए ऐतिहासिक जलवायु-विज्ञान से तुलना करें।",
  "env.suggestion.seasonal": "एकल स्नैपशॉट पढ़ने से पहले मौसमी पादपप्लवक पैटर्न की जाँच करें।",
  "env.suggestion.combine": "स्थल-स्थित पोषक, लवणता या प्राथमिक-उत्पादकता प्रेक्षणों के साथ मिलाएँ।",
  "env.mapPoint": "पर्यावरणीय नमूना बिंदु",
  "env.cmp.title": "पहले के प्रेक्षण से तुलना",
  "env.cmp.now": "अभी",
  "env.cmp.reference": "संदर्भ",
  "env.cmp.delta": "अंतर",
  "env.cmp.window": "संदर्भ अवधि",
  "env.cmp.validity": "वैधता",
  "env.cmp.higher": "संदर्भ से अधिक",
  "env.cmp.lower": "संदर्भ से कम",
  "env.cmp.unchanged": "संदर्भ से अपरिवर्तित",
  "env.cmp.unknown": "तुलनीय नहीं",
  "env.cmp.unavailable": "सामयिक तुलना नहीं की जा सकी।",
  "env.cmp.note": "संदर्भ हाल की एक पिछली अवधि पर ORCA-गणित मान है, कोई जलवायु सामान्य नहीं। एक अंतर कोई प्रवृत्ति नहीं।",
  "env.ev.title": "साक्ष्य और पुनरुत्पादकता",
  "env.ev.status": "साक्ष्य गुणवत्ता",
  "env.ev.summary": "सारांश",
  "env.ev.current": "वर्तमान",
  "env.ev.historical": "ऐतिहासिक / संदर्भ",
  "env.ev.source": "स्रोत",
  "env.ev.dataset": "डेटासेट",
  "env.ev.observed": "प्रेक्षण समय",
  "env.ev.validity": "वैधता",
  "env.ev.distance": "पिक्सेल दूरी",
  "env.ev.tier": "श्रेणी",
  "env.ev.reproducibility": "पुनरुत्पादकता",
  "env.ev.opticalHint": "तटीय-जल संदर्भ",
  "env.ev.bundle": "पुनरुत्पादकता बंडल",
  "env.ev.copyJson": "JSON के रूप में कॉपी करें",
  "env.ev.copied": "कॉपी किया गया",
  "env.ev.status.adequate": "पर्याप्त",
  "env.ev.status.limited": "सीमित",
  "env.ev.status.insufficient": "अपर्याप्त",
  "env.ev.status.unavailable": "अनुपलब्ध",
  "env.stab.title": "फैलाव और कवरेज",
  "env.stab.observations": "प्रेक्षण",
  "env.stab.range": "परिसर",
  "env.stab.median": "माध्यिका",
  "env.stab.iqr": "IQR",
  "env.stab.quartiles": "Q1 / Q3",
  "env.stab.coverage": "कवरेज",
  "env.stab.gaps": "अंतराल",
  "env.stab.insufficientProfile":
    "अवधि में तीन से कम प्रेक्षण - कोई परिक्षेपण आँकड़े नहीं निकाले गए।",
  "env.stab.note":
    "यह एक सीमित अवधि के भीतर प्रेक्षित पर्यावरणीय डेटा की कवरेज और फैलाव का वर्णन करता है। यह कोई प्रवृत्ति, पूर्वानुमान या मछली पकड़ने का संकेतक नहीं है।",
  "env.stab.status.adequate": "पर्याप्त",
  "env.stab.status.limited": "सीमित",
  "env.stab.status.insufficient": "अपर्याप्त",
  "env.stab.status.unavailable": "अनुपलब्ध",
  "env.nbhd.title": "स्थानीय प्रतिनिधित्वशीलता",
  "env.nbhd.pixels": "निकटवर्ती पिक्सेल",
  "env.nbhd.range": "परिसर",
  "env.nbhd.median": "माध्यिका",
  "env.nbhd.iqr": "IQR",
  "env.nbhd.nearest": "निकटतम मान्य पिक्सेल",
  "env.nbhd.coverage": "कवरेज",
  "env.nbhd.placement": "केंद्रीय पिक्सेल",
  "env.nbhd.placement.within": "निकटवर्ती परिसर के भीतर",
  "env.nbhd.placement.above": "निकटवर्ती परिसर से ऊपर",
  "env.nbhd.placement.below": "निकटवर्ती परिसर से नीचे",
  "env.nbhd.placement.na": "स्थान नहीं दिया गया",
  "env.nbhd.insufficientProfile":
    "इस कम्पोज़िट पर तीन से कम मान्य निकटवर्ती पिक्सेल - कोई नेबरहुड आँकड़े नहीं निकाले गए।",
  "env.nbhd.note":
    "यह केवल एकल केंद्रीय क्लोरोफिल-a पिक्सेल की तुलना उसी उपग्रह कम्पोज़िट पर मान्य निकटवर्ती पिक्सेल से करता है। यह एक वर्णनात्मक प्रतिनिधित्वशीलता जाँच है, कोई स्थानिक मानचित्र, उत्पादकता अनुमान या मछली पकड़ने का संकेतक नहीं।",
  "env.nbhd.status.adequate": "पर्याप्त",
  "env.nbhd.status.limited": "सीमित",
  "env.nbhd.status.insufficient": "अपर्याप्त",
  "env.nbhd.status.unavailable": "अनुपलब्ध",
  "env.anom.title": "पर्यावरणीय असामान्यता लेंस",
  "env.anom.subtitle": "हाल के वितरण का विश्लेषण · हाल के प्रेक्षणों के भीतर स्थिति",
  "env.anom.percentile": "प्रतिशतक",
  "env.anom.percentileSuffix": "वां प्रतिशतक",
  "env.anom.range": "परिसर",
  "env.anom.median": "माध्यिका",
  "env.anom.diffFromMedian": "माध्यिका से",
  "env.anom.observations": "प्रेक्षण",
  "env.anom.currentUnavailable":
    "वर्तमान प्रेक्षण अनुपलब्ध है; हाल के वितरण में कोई स्थिति निर्धारित नहीं की जा सकी।",
  "env.anom.insufficientProfile":
    "अवधि में तीन से कम मान्य ऐतिहासिक प्रेक्षण - हाल के वितरण में कोई स्थिति नहीं निकाली गई।",
  "env.anom.howCalculated": "यह कैसे गणना की जाती है?",
  "env.anom.methodologyFallback":
    "वर्तमान प्रेक्षण को मौजूदा सीमित हाल की अवधि के मान्य प्रेक्षणों के विरुद्ध स्थित किया जाता है। अमान्य या अनुपलब्ध मान बाहर रखे जाते हैं, कभी प्रक्षेपित नहीं किए जाते। न्यूनतम तीन मान्य ऐतिहासिक प्रेक्षण आवश्यक हैं।",
  "env.anom.status.ok": "स्थिति निर्धारित",
  "env.anom.status.currentUnavailable": "अनुपलब्ध",
  "env.anom.status.insufficientHistory": "अपर्याप्त",
  "env.anom.class.below": "हाल की सीमा से नीचे",
  "env.anom.class.within": "हाल के वितरण के भीतर",
  "env.anom.class.above": "हाल की सीमा से ऊपर",
  "env.anom2.current": "वर्तमान",
  "env.anom2.recentMedian": "हाल की माध्यिका",
  "env.anom2.difference": "अंतर",
  "env.anom2.position": "स्थिति",
  "env.anom2.dataCoverage": "डेटा कवरेज",
  "env.anom2.lastDays": "पिछले",
  "env.anom2.daysLabel": "दिन",
  "env.anom2.windowLabel": "{days}-दिन अवलोकन विंडो",
  "env.anom2.dataUnavailable": "डेटा अनुपलब्ध",
  "env.anom2.insufficientData": "अपर्याप्त डेटा",
  "env.anom2.isAbove": "हाल की इंटरक्वार्टाइल सीमा से ऊपर है।",
  "env.anom2.isWithin": "हाल के वितरण के भीतर है।",
  "env.anom2.isBelow": "हाल की इंटरक्वार्टाइल सीमा से नीचे है।",
  "panel.route": "मार्ग",
  "route.status": "स्थिति",
  "route.distance": "दूरी",
  "route.cost": "ग्रिड पथ लागत",
  "route.violations": "हार्ड जियोफेंस उल्लंघन",
  "route.noneTitle": "कोई सुरक्षित मार्ग नहीं",
  "route.reason": "कारण",
  "route.notRequested": "इस प्रश्न के लिए मार्ग नहीं माँगा गया।",
  "route.validated": "ORCA मार्ग एजेंट द्वारा सत्यापित मार्ग",
  "tab.trip": "यात्रा",
  "panel.tripPlanner": "मछुआरा यात्रा योजनाकार",
  "panel.routeComparison": "मार्ग तुलना",
  "panel.routeAnalytics": "मार्ग विश्लेषण",
  "trip.origin": "प्रस्थान स्थान",
  "trip.destination": "गंतव्य",
  "trip.departure": "प्रस्थान",
  "trip.availableTime": "उपलब्ध यात्रा समय",
  "trip.workDuration": "मछली पकड़ने / कार्य अवधि",
  "trip.vesselSpeed": "नाव की गति",
  "trip.vesselSpeedHint": "यात्रा समय के लिए नाव की गति आवश्यक है।",
  "trip.returnDeadline": "वापसी समय (वैकल्पिक)",
  "trip.optional": "वैकल्पिक",
  "trip.unit.minutes": "मिनट",
  "trip.unit.knots": "नॉट",
  "trip.feasibility.title": "यात्रा व्यवहार्यता",
  "trip.status.FEASIBLE": "यात्रा व्यवहार्य है",
  "trip.status.INFEASIBLE_TIME": "पर्याप्त समय नहीं",
  "trip.status.INFEASIBLE_RETURN_DEADLINE": "वापसी समय सीमा पार",
  "trip.status.BLOCKED_ROUTE": "अवरुद्ध",
  "trip.status.NO_SAFE_RECOMMENDATION": "कोई सुरक्षित अनुशंसा नहीं",
  "trip.status.MISSING_DATA": "अधिक जानकारी आवश्यक",
  "trip.time.departure": "प्रस्थान",
  "trip.time.outbound": "जाने का समय",
  "trip.time.work": "मछली पकड़ना / कार्य",
  "trip.time.return": "वापसी",
  "trip.time.total": "कुल",
  "trip.time.available": "उपलब्ध",
  "trip.time.remaining": "शेष",
  "trip.time.estimatedReturn": "अनुमानित वापसी",
  "trip.time.returnBy": "वापसी समय सीमा",
  "trip.time.buffer": "अतिरिक्त समय",
  "trip.caution": "वर्तमान निर्णय सावधानी है - रवाना होने से पहले स्थितियों की समीक्षा करें।",
  "trip.safetyWindowNote": "वर्तमान निर्णय मूल्यांकित समय पर लागू होता है।",
  "trip.pfzReferenceLabel": "संदर्भ / आधिकारिक परामर्श डेटा — ORCA द्वारा उत्पन्न नहीं",
  "trip.noRoute": "यात्रा योजनाकार का उपयोग करने के लिए पहले एक मार्ग बनाएं (ORCA से पूछें या मानचित्र पर गंतव्य चुनें)।",
  "route.compare.title": "सीधा बनाम ORCA मार्ग",
  "route.compare.baseline": "आधार रेखा (सीधी रेखा)",
  "route.compare.baselineBlocked": "आधार रेखा (अवरुद्ध)",
  "route.compare.orca": "ORCA मार्ग",
  "route.compare.metric": "मापदंड",
  "route.compare.distance": "दूरी",
  "route.compare.violations": "हार्ड उल्लंघन",
  "route.compare.feasible": "व्यवहार्य",
  "route.compare.yes": "हाँ",
  "route.compare.no": "नहीं",
  "route.compare.explanation": "ORCA मार्ग {diff} लंबा है क्योंकि सीधी रेखा इनसे होकर गुजरती है: {names}",
  "route.compare.loading": "आधार रेखा तुलना गणना हो रही है…",
  "route.compare.unavailable": "आधार रेखा तुलना उपलब्ध नहीं है।",
  "route.compare.noRoute": "तुलना के लिए अभी कोई मार्ग नहीं है।",
  "route.compare.baselineLabel": "आधार रेखा = प्रस्थान और गंतव्य के बीच सीधी भौगोलिक रेखा - यह कोई रूटिंग एल्गोरिदम नहीं, केवल तुलना के लिए एक संदर्भ है।",
  "route.compare.definitionNote": "\"सीधा\" का अर्थ है अप्रतिबंधित सीधी रेखा - यह कोई अनुशंसित या सुरक्षित मार्ग नहीं है।",
  "analytics.distance": "कुल दूरी",
  "analytics.waypoints": "पड़ाव बिंदु",
  "analytics.violations": "हार्ड जियोफेंस उल्लंघन",
  "analytics.feasible": "मार्ग व्यवहार्य",
  "analytics.safetyStatus": "सुरक्षा स्थिति",
  "analytics.constrainedSegmentsAvoided": "सीधी रेखा की तुलना में टाले गए प्रतिबंधित क्षेत्र",
  "tour.tripPlanner.title": "मछुआरा यात्रा योजनाकार",
  "tour.tripPlanner.body": "वर्तमान मार्ग के लिए निर्धारक यात्रा व्यवहार्यता जांच देखने हेतु अपना उपलब्ध समय, मछली पकड़ने की अवधि और नाव की गति सेट करें।",
  "tour.routeCompare.title": "मार्ग तुलना",
  "tour.routeCompare.body": "ORCA के बाधा-जागरूक मार्ग की तुलना सीधी आधार रेखा से करें - दूरी, समय और टाले गए प्रतिबंधित क्षेत्र, साथ-साथ।",
  "route.marineAware": "समुद्री-जागरूक मार्ग",
  "route.marineAwareNote": "लहर/हवा की स्थिति मार्ग लागत में शामिल",
  "route.marinePenalty": "समुद्री लागत दंड",
  "evidence.source": "स्रोत",
  "evidence.type": "प्रकार",
  "evidence.status": "स्थिति",
  "evidence.tier": "स्तर",
  "evidence.none": "इस प्रश्न के लिए कोई साक्ष्य नहीं।",
  "conflict.detected": "साक्ष्य विरोध पाया गया",
  "conflict.none": "कोई विरोध नहीं मिला।",
  "conflict.type": "प्रकार",
  "conflict.severity": "गंभीरता",
  "conflict.resolution": "समाधान",
  "conflict.safetyAffected": "सुरक्षा-महत्वपूर्ण",
  "reference.pfzTitle": "INCOIS PFZ",
  "reference.snapshot": "संदर्भ स्नैपशॉट",
  "reference.validUntil": "मान्य तिथि तक",
  "reference.view": "सलाह देखें",
  "reference.notOrca": "आधिकारिक संदर्भ स्नैपशॉट। ORCA द्वारा उत्पन्न पूर्वानुमान नहीं।",
  "reference.none": "इस प्रश्न से कोई आधिकारिक संदर्भ संलग्न नहीं।",
  "provenance.title": "ORCA इस निर्णय तक कैसे पहुँचा",
  "provenance.why": "प्रश्न → साक्ष्य → तर्क → सुरक्षा → निर्णय",
  "provenance.none": "इस प्रश्न के लिए कोई उत्पत्ति ग्राफ़ नहीं।",
  "provenance.inspect": "निरीक्षण हेतु एक नोड चुनें",
  "alerts.none": "इस प्रश्न के लिए कोई चेतावनी नहीं।",
  "alerts.proxyNote":
    "आंधी और चक्रवात संकेत मॉडल-आधारित प्रॉक्सी हैं, प्रमाणित वास्तविक-समय पहचान नहीं।",
  "activity.title": "एजेंट निष्पादन",
  "activity.done": "पूर्ण",
  "activity.skipped": "छोड़ा गया",
  "activity.pending": "नहीं चला",
  "activity.failed": "विफल",
  "activity.timingMeasured": "प्रति-चरण समय सर्वर पर मापा गया (वास्तविक, अनुकरण नहीं)।",
  "activity.timingUnavailable": "केवल निष्पादन स्थिति — इस उत्तर में प्रति-चरण समय नहीं।",
  "activity.correlation": "सहसंबंध आईडी",
  "activity.total": "कुल मापा गया",
  "explanation.why": "यह निर्णय क्यों?",
  "explanation.disclaimer":
    "ORCA एक निर्णय-समर्थन प्रणाली है। परिचालन कार्रवाई से पहले आधिकारिक समुद्री और मौसम सलाह की पुष्टि करें।",
  "verdict.why": "क्यों",
  "verdict.location": "स्थान",
  "verdict.observed": "स्थितियाँ प्रेक्षित",
  "verdict.riskBreakdown": "जोखिम विवरण",
  "verdict.fullExplanation": "पूरा स्पष्टीकरण",
  "verdict.envContext": "पर्यावरण एवं शोध संदर्भ",
  "verdict.operationalDetail": "परिचालन विवरण",
  "verdict.whatIf": "काल्पनिक परिदृश्य अनुकरण",
  "evidence.reviewed": "साक्ष्य रिकॉर्ड समीक्षित",
  "map.layers": "मानचित्र परतें",
  "map.legend": "डेटा उत्पत्ति",
  "map.legend.live": "लाइव अवलोकन / पूर्वानुमान",
  "map.legend.reference": "आधिकारिक संदर्भ स्नैपशॉट",
  "map.legend.derived": "ORCA द्वारा गणना",
  "map.legend.demo": "उदाहरण / डेमो डेटा",
  "map.legend.missing": "अनुपलब्ध",
  "map.noGeometry": "इस प्रश्न के लिए कोई ज्यामिति उपलब्ध नहीं।",
  "map.orcaRoute": "ORCA मार्ग",
  "map.noRoute": "कोई सुरक्षित मार्ग नहीं",
  "map.origin": "आरंभ",
  "map.destination": "गंतव्य",
  "map.routeDestinationN": "PFZ {n} / {count}",
  "layer.group.marineBase": "समुद्री आधार",
  "layer.group.orcaAnalysis": "ORCA विश्लेषण",
  "layer.group.fishingEnvironment": "मत्स्यन एवं पर्यावरण",
  "layer.badge.orca": "ORCA",
  "layer.badge.incois": "INCOIS",
  "layer.badge.live": "लाइव",
  "layer.badge.pointData": "बिंदु डेटा",
  "layer.source.reference": "आधिकारिक संदर्भ परत",
  "layer.source.orca": "ORCA द्वारा गणना",
  "layer.source.incois": "INCOIS आधिकारिक संदर्भ",
  "layer.source.live": "लाइव अवलोकन",
  "layer.risk": "जोखिम",
  "layer.coastline": "तटरेखा",
  "layer.eez": "भारतीय EEZ",
  "layer.protected_areas": "संरक्षित क्षेत्र",
  "layer.geofences": "जियोफेंस",
  "layer.route": "मार्ग",
  "layer.pfz": "INCOIS PFZ संदर्भ",
  "layer.pfz.noLocationMatch": "इस सटीक स्थान के लिए कोई आधिकारिक INCOIS PFZ सलाह उपलब्ध नहीं है।",
  "layer.pfz.checking": "आधिकारिक INCOIS PFZ उपलब्धता जांची जा रही है…",
  "layer.pfz.noGeometry": "इस स्थान के लिए आधिकारिक INCOIS संदर्भ मानचित्र पर उपलब्ध नहीं है।",
  "layer.pfz.zoneCount": "आधिकारिक INCOIS संदर्भ — {count} क्षेत्र",
  "layer.pfz.landingCentreOnly":
    "आज के लिए कोई PFZ क्षेत्र सलाह नहीं है — निकटतम आधिकारिक INCOIS संदर्भ लैंडिंग केंद्र दिखाया जा रहा है।",
  "layer.sst": "समुद्र सतह तापमान",
  "layer.chlorophyll": "क्लोरोफिल-a",
  "layer.sst.available":
    "Open-Meteo Marine मान — Environmental सैंपल-पॉइंट मार्कर पर दिखाया गया (कोई ग्रिड ओवरले नहीं)।",
  "layer.sst.unavailable":
    "इस क्वेरी के लिए SST अनुपलब्ध — कोई मान्य Open-Meteo Marine मान नहीं।",
  "layer.chlorophyll.available":
    "NOAA CoastWatch (VIIRS) मान — Environmental सैंपल-पॉइंट मार्कर पर दिखाया गया (कोई ग्रिड ओवरले नहीं)।",
  "layer.chlorophyll.unavailable":
    "क्लोरोफिल-a अनुपलब्ध — संभवतः उपग्रह बादल / डेटा कवरेज या वैधता सीमाओं के कारण। कोई मान नहीं दिखाया गया।",
  "layer.environmentalSuitability": "ORCA पर्यावरणीय उपयुक्तता",
  "layer.environmentalSuitability.noLocation": "इस लेयर को लोड करने के लिए पहले ORCA से किसी स्थान के बारे में पूछें।",
  "map.layers.expand": "मानचित्र परत नियंत्रण दिखाएं",
  "map.layers.collapse": "मानचित्र परत नियंत्रण छिपाएं",
  "map.layers.active": "{count} सक्रिय",
  "layer.desc.coastline": "भारत की तटीय सीमा",
  "layer.desc.eez": "भारत का विशेष आर्थिक क्षेत्र",
  "layer.desc.protected_areas": "समुद्री/तटीय संरक्षित क्षेत्र",
  "layer.desc.geofences": "प्रतिबंधित कठोर-बहिष्करण सीमाएं",
  "layer.desc.risk": "ORCA सुरक्षा जोखिम आकलन",
  "layer.desc.route": "ORCA द्वारा मूल्यांकित मार्ग — सुरक्षित मार्ग की गारंटी नहीं",
  "layer.desc.environmental": "इस प्रश्न के लिए पर्यावरणीय नमूना बिंदु",
  "layer.desc.environmentalSuitability": "CHL-आधारित स्थानिक उपयुक्तता ग्रिड (शोध/संदर्भ संदर्भ)",
  "layer.desc.pfz": "आधिकारिक INCOIS PFZ संदर्भ — ORCA-व्युत्पन्न नहीं",
  "env.suitability.title": "ORCA पर्यावरणीय उपयुक्तता",
  "env.suitability.disclaimer": "केवल पर्यावरणीय संदर्भ — यह मछली-उपस्थिति या सुरक्षा भविष्यवाणी नहीं है।",
  "env.suitability.insufficientData": "यहाँ उपयुक्तता विज़ुअलाइज़ेशन के लिए पर्याप्त पर्यावरणीय डेटा उपलब्ध नहीं है।",
  "env.suitability.legend.low": "कम",
  "env.suitability.legend.moderate": "मध्यम",
  "env.suitability.legend.high": "अधिक",
  "gps.use": "मेरा वर्तमान स्थान उपयोग करें",
  "gps.requesting": "स्थान का अनुरोध किया जा रहा है…",
  "gps.granted": "आपके वर्तमान स्थान का उपयोग किया जा रहा है",
  "gps.denied": "स्थान की अनुमति अस्वीकृत",
  "gps.unavailable": "वर्तमान स्थान उपलब्ध नहीं है",
  "gps.markerLabel": "मेरा वर्तमान स्थान",
  "pfz.selectedTitle": "INCOIS PFZ संदर्भ चयनित",
  "pfz.selectedTitleMulti": "{count} INCOIS PFZ संदर्भ चयनित",
  "pfz.selectedMarkerLabel": "चयनित PFZ संदर्भ",
  "pfz.selectedMarkerLabelMulti": "चयनित PFZ {n}",
  "pfz.navigate": "इस PFZ की ओर मार्ग बनाएं",
  "pfz.navigateMulti": "सभी {count} चयनित PFZ के माध्यम से मार्ग बनाएं",
  "pfz.removeSelection": "चयन {n} हटाएं",
  "pfz.notSafetyNote": "PFZ संदर्भ कोई सुरक्षा सिफारिश नहीं है।",
  "pfz.clearSelection": "चयन साफ़ करें",
  "pfz.cannotRoute": "चयनित PFZ संदर्भ तक सुरक्षित रूप से मार्ग नहीं बनाया जा सकता।",
  "pfz.direction": "दिशा",
  "pfz.bearing": "दिक्मान",
  "pfz.distance": "दूरी",
  "pfz.depth": "गहराई",
  "pfz.forecast": "पूर्वानुमान",
  "pfz.validUntil": "मान्य तक",
  "pfz.officialSource": "आधिकारिक INCOIS संदर्भ",
  "pfz.ranked.title": "क्रमबद्ध PFZ क्षेत्र",
  "pfz.ranked.subtitle": "निकटतम आधिकारिक INCOIS क्षेत्र, दूरी के अनुसार क्रमबद्ध",
  "pfz.ranked.distanceKm": "{km} किमी दूर",
  "pfz.ranked.restricted": "प्रतिबंधित",
  "pfz.ranked.projected": "परिकलित संदर्भ",
  "pfz.ranked.selectHint": "मानचित्र पर हाइलाइट करने के लिए एक क्षेत्र चुनें",
  "pfz.ranked.markerTooltip": "PFZ क्षेत्र {n} — {km} किमी",
  "pfz.ranked.empty": "इस स्थान के निकट कोई मिलान PFZ क्षेत्र नहीं",
  "pfz.ranked.unavailable": "इस स्थान या तिथि के लिए फिलहाल कोई आधिकारिक INCOIS PFZ संदर्भ उपलब्ध नहीं है। ORCA कोई PFZ स्थान नहीं बनाता या अनुमान नहीं लगाता। आप फिर भी समुद्र में जाने की सुरक्षा और पर्यावरणीय स्थितियों का आकलन अलग से कर सकते हैं।",
  "pfz.ranked.noLocationMatch": "आज इस सटीक स्थान के लिए कोई आधिकारिक INCOIS PFZ सलाह उपलब्ध नहीं है। आप फिर भी समुद्र में जाने की सुरक्षा और पर्यावरणीय स्थितियों का आकलन अलग से कर सकते हैं।",
  "pfz.ranked.landingCentreOnly": "आज इस स्थान के लिए कोई क्रमबद्ध PFZ क्षेत्र रेखा मेल नहीं खाती। इसके बजाय मानचित्र और चैट उत्तर में निकटतम आधिकारिक INCOIS संदर्भ लैंडिंग केंद्र दिखाया गया है।",
  "pfz.ranked.checking": "आधिकारिक INCOIS PFZ क्षेत्रों की जांच की जा रही है…",
  "pfz.ranked.available": "{count} उपलब्ध",
  "pfz.ranked.layerHidden": "PFZ परत छिपी है — इन क्षेत्रों को देखने और चुनने के लिए मानचित्र परतों में INCOIS PFZ संदर्भ चालू करें।",
  "pfz.ranked.expand": "क्रमबद्ध PFZ क्षेत्र दिखाएं",
  "pfz.ranked.collapse": "क्रमबद्ध PFZ क्षेत्र छिपाएं",
  "route.myLocationToPfz": "मेरा स्थान → INCOIS PFZ संदर्भ",
  "route.myLocationToPfzs": "मेरा स्थान → {count} चयनित INCOIS PFZ संदर्भ",
  "route.myLocationToPfzZone": "मेरा स्थान → INCOIS PFZ #{n}",
  "mapSidebar.toggleShow": "मानचित्र साइडबार दिखाएं",
  "mapSidebar.toggleHide": "मानचित्र साइडबार छिपाएं",
  "mapTools.title": "मानचित्र उपकरण",
  "routeControls.title": "मार्ग नियंत्रण",
  "routeControls.noSelection": "वहां मार्ग बनाने के लिए एक क्रमबद्ध PFZ क्षेत्र चुनें।",
  "routeControls.destination": "गंतव्य",
  "routeControls.pfzLabel": "INCOIS PFZ #{n}",
  "routeControls.computing": "मार्ग की गणना हो रही है…",
  "routeControls.notRoutedYet": "अभी तक इस गंतव्य के लिए मार्ग नहीं बनाया गया।",
  "routeControls.statusAvailable": "मार्ग उपलब्ध",
  "routeControls.statusBlocked": "अवरुद्ध",
  "routeControls.statusUnavailable": "मार्ग अनुपलब्ध",
  "routeControls.waypoints": "वेपॉइंट",
  "routeControls.routeButton": "PFZ #{n} की ओर मार्ग बनाएं",
  "routeControls.viewRoute": "मार्ग देखें",
  "routeControls.expand": "मार्ग नियंत्रण दिखाएं",
  "routeControls.collapse": "मार्ग नियंत्रण छिपाएं",
  "routeControls.originAdjusted": "मार्ग उद्गम: निकटतम नौवहन योग्य समुद्री सेल (संदर्भ उद्गम भूमि पर है)",
  "env.interp": "उत्पादकता व्याख्या",
  "env.interp.limited": "सीमित",
  "env.interp.limitedNote":
    "क्लोरोफिल-a अनुपलब्ध; पर्यावरणीय उत्पादकता क्षमता का आकलन नहीं किया जा सकता।",
  "env.ev.qualityNote":
    "क्या अंतर्निहित SST / क्लोरोफिल-a अवलोकन मान्य, स्रोतित और समयांकित हैं — यह इससे अलग है कि उत्पादकता की व्याख्या हो सकी या नहीं।",
  "voice.mic.start": "अपना प्रश्न बोलें",
  "voice.mic.stop": "सुनना बंद करें",
  "voice.mic.unsupported": "इस ब्राउज़र में वाक् इनपुट समर्थित नहीं है",
  "voice.mic.error": "माइक्रोफ़ोन रिकॉर्डिंग विफल — आप फिर भी प्रश्न टाइप कर सकते हैं",
  "voice.mic.permissionDenied":
    "माइक्रोफ़ोन अनुमति अस्वीकृत — वॉइस इनपुट उपयोग करने के लिए ब्राउज़र में अनुमति दें, या प्रश्न टाइप करें",
  "voice.mic.deviceUnavailable": "कोई माइक्रोफ़ोन डिवाइस नहीं मिला — आप फिर भी प्रश्न टाइप कर सकते हैं",
  "voice.mic.insecureContext":
    "वॉइस इनपुट के लिए सुरक्षित (HTTPS या localhost) कनेक्शन आवश्यक है — आप फिर भी प्रश्न टाइप कर सकते हैं",
  "voice.listening": "सुन रहा है…",
  "voice.tts.play": "ज़ोर से पढ़ें",
  "voice.tts.stop": "पढ़ना बंद करें",
  "voice.tts.unsupported": "इस ब्राउज़र में ज़ोर से पढ़ना समर्थित नहीं है",
  "voice.speaking": "बोल रहा है…",
  "tour.start": "टूर शुरू करें",
  "tour.skip": "छोड़ें",
  "tour.back": "पीछे",
  "tour.next": "आगे",
  "tour.finish": "समाप्त",
  "tour.stepOf": "{total} में से {current}",
  "tour.overview.title": "ORCA में आपका स्वागत है",
  "tour.overview.body":
    "ORCA मछुआरों, आपदा प्रबंधकों और शोधकर्ताओं के लिए एक समुद्री निर्णय-सहायता प्रणाली है। यह टूर वास्तविक इंटरफ़ेस से होकर गुज़रता है — यहाँ कुछ भी नकली नहीं है।",
  "tour.ask.title": "समुद्री प्रश्न पूछें",
  "tour.ask.body":
    "यहाँ अपना प्रश्न टाइप करें, या नीचे दिए गए सुझाए गए प्रश्नों में से कोई चुनें। आपका प्रश्न ORCA की वास्तविक प्रक्रिया से गुज़रता है — समझ, डेटा संग्रह, नियतात्मक जोखिम व सुरक्षा मूल्यांकन, फिर निर्णय।",
  "tour.liveData.title": "लाइव समुद्री और मौसम डेटा",
  "tour.liveData.body":
    "यह पैनल मानचित्र परतों को नियंत्रित करता है — लाइव लहर, हवा, समुद्र-सतह तापमान और आधिकारिक INCOIS/IMD संदर्भ डेटा जो ORCA आपके प्रश्न स्थान के लिए प्राप्त करता है।",
  "tour.decision.title": "निर्णय",
  "tour.decision.body":
    "जब ORCA के पास उत्तर होता है, तो यह कार्ड परिचालन निर्णय दिखाता है — आगे बढ़ें, सावधानी से आगे बढ़ें, या आगे न बढ़ें — जो नियतात्मक रूप से गणना किया जाता है, AI द्वारा अनुमानित नहीं।",
  "tour.why.title": "यह निर्णय क्यों?",
  "tour.why.body":
    "ये निर्णय के पीछे के वास्तविक कारण हैं, सीधे रिस्क इंजन और सेफ्टी गार्ड से लिए गए — कभी भी गढ़ा हुआ स्पष्टीकरण नहीं।",
  "tour.safety.title": "सुरक्षा गार्ड",
  "tour.safety.body":
    "सुरक्षा का मूल्यांकन जोखिम से अलग, एक नियतात्मक सेफ्टी गार्ड द्वारा किया जाता है, और यह बाकी सब कुछ ओवरराइड कर सकता है — यह एकमात्र चीज़ है जिसे AI परत कभी नहीं बदल सकती।",
  "tour.replay.title": "निर्णय रीप्ले",
  "tour.replay.body":
    "देखें कि यही निर्णय पूर्वानुमान अवधि में घंटे-दर-घंटे कैसे बदलता है — वही नियतात्मक प्रक्रिया दोबारा चलाई जाती है, यह कभी दूसरा लाइव निर्णय नहीं है।",
  "tour.route.title": "मार्ग योजना",
  "tour.route.body":
    "जब मार्ग का अनुरोध किया जाता है, तो ORCA इसे वास्तविक जियोफ़ेंस, संरक्षित क्षेत्रों और समुद्री परिस्थितियों के विरुद्ध योजना बनाता है, और किसी सख्त सुरक्षा सीमा को पार करने वाले मार्ग को अस्वीकार करता है।",
  "tour.evidence.title": "साक्ष्य और उद्गम",
  "tour.evidence.body":
    "इस निर्णय तक पहुँचने के लिए ORCA द्वारा उपयोग किया गया हर मान यहाँ उसके स्रोत, स्तर और वैधता के साथ सूचीबद्ध है, ताकि निर्णय की स्वतंत्र रूप से जाँच की जा सके।",
  "tour.environmental.title": "पर्यावरणीय शोध",
  "tour.environmental.body":
    "शोधकर्ताओं के लिए: समुद्र-सतह तापमान, क्लोरोफिल-a और संबंधित संदर्भ — केवल वर्णनात्मक, कभी भी पकड़ के अनुमान या मछली पकड़ने के परिणाम की गारंटी के लिए उपयोग नहीं किया जाता।",
  "tour.engineRoom.title": "इंजन रूम",
  "tour.engineRoom.body":
    "ORCA की वास्तविक संरचना, और पिछले प्रश्न के लिए, वास्तविक एजेंट निष्पादन ट्रेस — बिल्कुल कौन से चरण चले, किस क्रम में, और प्रत्येक में कितना समय लगा।",
  "evidence.export": "साक्ष्य निर्यात करें",
  "evidence.export.success": "साक्ष्य निर्यात किया गया",
  "evidence.export.failure": "साक्ष्य निर्यात विफल",
  "replay.title": "निर्णय रीप्ले",
  "replay.emptyNote":
    "पहले एक आकलन चलाएँ, फिर यहाँ देखें कि उपलब्ध पूर्वानुमान अवधि में निर्णय कैसे बदलता है।",
  "replay.intro":
    "देखें कि समुद्री परिस्थितियाँ, जोखिम और नियतात्मक निर्णय उपलब्ध घंटेवार पूर्वानुमान में कैसे बदलते हैं — इस आकलन के लिए पहले से प्राप्त उसी पूर्वानुमान डेटा से लिया गया।",
  "replay.explore": "समय के साथ निर्णय देखें →",
  "replay.building": "रीप्ले तैयार किया जा रहा है...",
  "replay.genericError": "निर्णय रीप्ले नहीं चलाया जा सका।",
  "replay.noTimestamps": "रीप्ले के लिए कोई पूर्वानुमान समय उपलब्ध नहीं था।",
  "replay.bannerTitle": "ORCA निर्णय रीप्ले",
  "replay.bannerSubtitle": "समुद्री निर्णय समय के साथ कैसे बदलता है",
  "replay.windowLabel": "पूर्वानुमान · {hours} घं",
  "replay.howItWorks": "यह कैसे काम करता है",
  "replay.howItWorksBody":
    "रीप्ले हर उपलब्ध पूर्वानुमान घंटे का उसी नियतात्मक रिस्क → सेफ्टी → निर्णय प्रक्रिया से मूल्यांकन करता है। यह दूसरा लाइव निर्णय नहीं बनाता।",
  "replay.forecastAt": "पूर्वानुमान · {time}",
  "replay.timestampSlider": "रीप्ले समय",
  "replay.trajectoryLabel": "घंटेवार निर्णय प्रक्षेपवक्र",
  "replay.changeFromPrevious": "पिछले घंटे से परिवर्तन",
  "replay.baselineNote": "आधार समय — कोई पिछला घंटा उपलब्ध नहीं है।",
  "replay.decisionStable": "निर्णय स्थिर है",
  "replay.decisionStableBody": "इस अंतराल में निर्णय {decision} बना हुआ है।",
  "replay.whyChanged": "निर्णय क्यों बदला?",
  "replay.decisionChangedBadge": "निर्णय बदल गया",
  "replay.whatChanged": "क्या बदला?",
  "replay.riskDeltaLabel": "जोखिम",
  "replay.safetyTriggerLabel": "सक्रिय सुरक्षा नियम:",
  "replay.wave": "लहर",
  "replay.wind": "हवा",
  "replay.sst": "समुद्र सतह तापमान",
  "replay.risk": "जोखिम",
  "replay.safety": "सुरक्षा",
  "replay.decisionRemains": "निर्णय {decision} बना हुआ है",
  "replay.riskFactorsAt": "जोखिम कारक — {time}",
  "replay.total": "कुल",
  "replay.safetyCheck": "सुरक्षा जाँच",
  "replay.deterministicSafety": "नियतात्मक सुरक्षा",
  "replay.safetyRuleSingular": "सुरक्षा नियम",
  "replay.safetyRulePlural": "सुरक्षा नियम",
  "replay.pipelineCaption": "रिस्क इंजन → सेफ्टी गार्ड → निर्णय",
  "replay.previous": "पिछला",
  "replay.next": "अगला",
  "replay.pause": "रोकें",
  "replay.playLabel": "रीप्ले {hours} घं",
  "replay.dataCoverage": "डेटा कवरेज",
  "replay.disclaimerBody":
    "{label}। यह इस आकलन के लिए पहले से प्राप्त पूर्वानुमान डेटा को ORCA के नियतात्मक रिस्क, सेफ्टी और निर्णय इंजनों से गुज़ारता है — यह दूसरा लाइव निर्णय नहीं है।",
  "replay.noPreviousHour": "कोई पिछला घंटा नहीं",
  "replay.vsPrev": "पिछले की तुलना में",
  "replay.legendProceed": "आगे बढ़ें",
  "replay.legendCaution": "सावधानी",
  "replay.legendDoNotProceed": "आगे न बढ़ें",
  "replay.chartTitle": "समुद्री परिस्थितियाँ और जोखिम समय के साथ",
  "replay.chartInsufficientData": "रुझान दिखाने के लिए पर्याप्त पूर्वानुमान घंटे उपलब्ध नहीं थे।",
  "replay.previewSuffix": "(पूर्वावलोकन)",
  "replay.chartRowAria": "रीप्ले अवधि में {label}",
  "common.expand": "विस्तृत करें",
  "common.collapse": "संक्षिप्त करें",
  "common.print": "प्रिंट / निर्यात",
  "common.close": "बंद करें",
  "common.na": "उपलब्ध नहीं",

  // Milestone 5 - Authority / Operational Intelligence Dashboard
  "nav.authority": "प्राधिकरण",
  "authority.title": "तटीय संचालन",
  "authority.subtitle": "निगरानी किए गए तटीय स्थानों का परिचालन अवलोकन",
  "authority.dataEdition.live": "लाइव",
  "authority.dataEdition.demo": "डेमो डेटा",
  "authority.demoFixtureNotice":
    "डेमो फ़िक्सचर डेटा — नीचे प्रत्येक स्थान की स्थिति एक निश्चित डेमो फ़िक्सचर से बनाई गई है, न कि उस स्थान की अभी की वास्तविक (लाइव) स्थितियों से। मानचित्र और तालिका अब भी हर स्थान की वास्तविक स्थिति दिखाते हैं।",
  "authority.detail.demoFixtureNotice":
    "डेमो फ़िक्सचर — यह स्थिति एक निश्चित डेमो फ़िक्सचर से आंकी गई है, {name} की अभी की वास्तविक (लाइव) स्थितियों से नहीं।",
  "authority.edition.live": "लाइव",
  "authority.edition.demo": "डेमो डेटा",
  "authority.updated": "अद्यतन {time}",
  "authority.refresh": "ताज़ा करें",
  "authority.loading": "तटीय संचालन लोड हो रहा है…",
  "authority.error": "तटीय परिचालन अवलोकन लोड नहीं हो सका।",
  "authority.retry": "पुनः प्रयास करें",
  "authority.locationsMonitored": "निगरानी किए गए स्थान",
  "authority.activeWarnings": "सक्रिय चेतावनियाँ",
  "authority.statusDistribution": "वर्तमान स्थितियाँ",
  "authority.map": "परिचालन मानचित्र",
  "authority.mapLegend": "स्थिति",
  "authority.attentionRequired": "ध्यान देने योग्य",
  "authority.noAttention": "फ़िलहाल किसी स्थान पर ध्यान देने की आवश्यकता नहीं है।",
  "authority.locations": "स्थान",
  "authority.locationsTable.location": "स्थान",
  "authority.locationsTable.status": "स्थिति",
  "authority.locationsTable.warning": "चेतावनी",
  "authority.locationsTable.data": "डेटा",
  "authority.locationsTable.updated": "अद्यतन",
  "authority.warnings": "आधिकारिक चेतावनियाँ",
  "authority.noWarnings": "कोई सक्रिय आधिकारिक चेतावनी नहीं है।",
  "authority.dataHealth": "डेटा स्वास्थ्य",
  "authority.dataHealth.weather": "मौसम",
  "authority.dataHealth.marine": "समुद्री",
  "authority.noLocations": "कोई परिचालन स्थान उपलब्ध नहीं है।",
  "authority.noLocationsHint": "ORCA अभी किसी भी चयनित तटीय स्थान का मूल्यांकन नहीं कर सका।",
  "authority.selectLocation": "विवरण हेतु एक स्थान चुनें",
  "authority.detail.wave": "लहर",
  "authority.detail.wind": "हवा",
  "authority.detail.warnings": "चेतावनियाँ",
  "authority.detail.geofence": "जियोफेंस",
  "authority.detail.dataConfidence": "डेटा विश्वसनीयता",
  "authority.detail.decision": "निर्णय",
  "authority.detail.evidence": "साक्ष्य",
  "authority.detail.evidenceSources": "{count} स्रोत",
  "authority.detail.openToday": "आज का दृश्य खोलें",
  "authority.detail.planTrip": "यात्रा योजना बनाएं",
  "authority.detail.viewSystem": "सिस्टम देखें",
  "authority.detail.viewTrace": "निष्पादन ट्रेस देखें",
  "authority.detail.viewEvidence": "साक्ष्य देखें",
  "authority.detail.viewReplay": "निर्णय रीप्ले",
  "authority.detail.exportEvidence": "साक्ष्य निर्यात करें",
  "authority.detail.source": "स्रोत",
  "authority.detail.derivedSource": "ORCA नियतात्मक नियम",
  "authority.geofence.clear": "कोई वर्तमान उल्लंघन नहीं",
  "authority.geofence.inside": "प्रतिबंधित क्षेत्र के भीतर",
  "authority.geofence.unavailable": "अनुपलब्ध",
  "authority.attentionCategory.official_warning": "आधिकारिक चेतावनी",
  "authority.attentionCategory.extreme": "अत्यधिक जोखिम",
  "authority.attentionCategory.high": "उच्च जोखिम",
  "authority.attentionCategory.blocked": "अवरुद्ध",
  "authority.attentionCategory.geofence": "जियोफेंस",
  "authority.attentionCategory.data_quality": "डेटा गुणवत्ता",
  "authority.attentionCategory.unavailable": "अनुपलब्ध",
};

const kn: Table = {
  ...en,
  "app.subtitle": "ಸಮುದ್ರ ಗುಪ್ತಚರ್ಯೆ",
  "landing.brand.tagline": "ಸಾಗರ ತಾರ್ಕಿಕತೆ ಮತ್ತು ಸಹಯೋಗಿ ಏಜೆಂಟ್‌ಗಳು",
  "landing.hero.headline": "ಸಾಗರ ಬುದ್ಧಿಮತ್ತೆ. ತಾರ್ಕಿಕ ನಿರ್ಧಾರಗಳು. ಸುರಕ್ಷಿತ ಸಮುದ್ರ ಕಾರ್ಯಾಚರಣೆಗಳು.",
  "landing.hero.subtext":
    "ORCA ಹವಾಮಾನ, ಸಾಗರ, ಪರಿಸರ, ಸಲಹಾ ಮತ್ತು ಭೂ-ಪ್ರಾದೇಶಿಕ ಸಾಕ್ಷ್ಯಗಳನ್ನು ಸಹಯೋಗಿ AI ಏಜೆಂಟ್‌ಗಳು ಮತ್ತು ನಿಶ್ಚಿತ ಸುರಕ್ಷತಾ ನಿಯಮಗಳ ಮೂಲಕ ಒಟ್ಟುಗೂಡಿಸಿ ಸಮುದ್ರ ನಿರ್ಧಾರಗಳಿಗೆ ಸಹಾಯ ಮಾಡುತ್ತದೆ.",
  "landing.hero.ctaPrimary": "ORCA ಪ್ರಾರಂಭಿಸಿ",
  "landing.hero.ctaSecondary": "ORCA ಹೇಗೆ ತರ್ಕಿಸುತ್ತದೆ",
  "landing.hero.disclaimer":
    "ಇದು ಮಾನವ ನಿರ್ಧಾರ ತೆಗೆದುಕೊಳ್ಳುವವರಿಗಾಗಿ ಒಂದು ನಿರ್ಧಾರ-ಬೆಂಬಲ ವ್ಯವಸ್ಥೆ — ಅಧಿಕೃತ ಎಚ್ಚರಿಕೆಗಳು, ಸ್ವಾಯತ್ತ ಸಂಚರಣೆ, ಅಥವಾ ಖಾತರಿಪಡಿಸಿದ ಮೀನುಗಾರಿಕೆ ಮುನ್ಸೂಚನೆಗೆ ಪರ್ಯಾಯವಲ್ಲ.",
  "landing.pipeline.title": "ORCA ಹೇಗೆ ತರ್ಕಿಸುತ್ತದೆ",
  "landing.pipeline.step.query": "ಬಳಕೆದಾರರ ಪ್ರಶ್ನೆ",
  "landing.pipeline.step.agents": "ಸಹಯೋಗಿ AI ಏಜೆಂಟ್‌ಗಳು",
  "landing.pipeline.step.fabric": "ಸಮುದ್ರ ದತ್ತಾಂಶ ಫ್ಯಾಬ್ರಿಕ್",
  "landing.pipeline.step.arbitration": "ಸಾಕ್ಷ್ಯ ಮಧ್ಯಸ್ಥಿಕೆ",
  "landing.pipeline.step.risk": "ನಿಶ್ಚಿತ ಅಪಾಯ ಮತ್ತು ಸುರಕ್ಷತೆ",
  "landing.pipeline.step.decision": "ನಿರ್ಧಾರ",
  "landing.pipeline.step.output": "ಸಾಕ್ಷ್ಯ + ಮಾರ್ಗ + ವಿವರಣೆ",
  "landing.pipeline.note":
    "AI ಪ್ರಶ್ನೆಯ ಬಗ್ಗೆ ತರ್ಕಿಸುತ್ತದೆ. ನಿಶ್ಚಿತ ಕೋಡ್ ಸುರಕ್ಷತೆಯನ್ನು ಲೆಕ್ಕಹಾಕುತ್ತದೆ ಮತ್ತು ಜಾರಿಗೊಳಿಸುತ್ತದೆ. ಸಾಕ್ಷ್ಯ ನಿರ್ಧಾರವನ್ನು ಬೆಂಬಲಿಸುತ್ತದೆ. ಅಂತಿಮ ನಿರ್ಧಾರವನ್ನು ಮಾನವ ತೆಗೆದುಕೊಳ್ಳುತ್ತಾನೆ.",
  "landing.sources.title": "ORCA ಯಾವ ದತ್ತಾಂಶದ ಮೇಲೆ ತರ್ಕಿಸುತ್ತದೆ",
  "landing.sources.note":
    "ಪ್ರತಿ ಮೂಲವೂ ಯಾವಾಗಲೂ ಲೈವ್ ಆಗಿರುವುದಿಲ್ಲ. ಒಂದು ಮೌಲ್ಯ ಲೈವ್, ಉಲ್ಲೇಖ, ಡೆಮೊ, ಅಥವಾ ಲಭ್ಯವಿಲ್ಲ ಎಂಬುದನ್ನು ORCA ಯಾವಾಗಲೂ ಬಹಿರಂಗಪಡಿಸುತ್ತದೆ.",
  "landing.sources.weather": "ಹವಾಮಾನ",
  "landing.sources.ocean": "ಸಾಗರ ಪರಿಸ್ಥಿತಿಗಳು",
  "landing.sources.sst": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ",
  "landing.sources.chl": "ಕ್ಲೋರೊಫಿಲ್-a",
  "landing.sources.pfz": "PFZ / ಸಲಹಾ ಉಲ್ಲೇಖಗಳು",
  "landing.sources.gis": "GIS ಮತ್ತು ಜಿಯೋಫೆನ್ಸಿಂಗ್",
  "landing.sources.safety": "ಸಮುದ್ರ ಸುರಕ್ಷತಾ ನಿರ್ಬಂಧಗಳು",
  "landing.sources.evidence": "ಪರಿಸರ ಸಾಕ್ಷ್ಯ",
  "landing.why.title": "ORCA ಏಕೆ",
  "landing.why.item1": "ಸಹಯೋಗಿ ಸಮುದ್ರ AI ಏಜೆಂಟ್‌ಗಳು",
  "landing.why.item2": "ನಿಶ್ಚಿತ ಸುರಕ್ಷತಾ ಜಾರಿ",
  "landing.why.item3": "ಸಾಕ್ಷ್ಯ-ಬೆಂಬಲಿತ ನಿರ್ಧಾರಗಳು",
  "landing.why.item4": "ವಿರೋಧಾಭಾಸ-ಅರಿವಿನ ತಾರ್ಕಿಕತೆ",
  "landing.why.item5": "ನಿರ್ಬಂಧ-ಅರಿವಿನ ಮಾರ್ಗ ನಿರ್ಧಾರಣೆ",
  "landing.why.item6": "ನಿರ್ಧಾರ ಮೂಲದ ದಾಖಲೆ",
  "landing.why.item7": "ಮರುಪ್ಲೇ ಮಾಡಬಹುದಾದ ನಿರ್ಧಾರಗಳು",
  "landing.why.item8": "ಅಂತಿಮ ನಿರ್ಧಾರ ತೆಗೆದುಕೊಳ್ಳುವವನು ಯಾವಾಗಲೂ ಮಾನವ",
  "landing.preview.title": "ಒಂದು ನಿರ್ಧಾರದ ಒಳಗೆ",
  "landing.preview.decision": "ನಿರ್ಧಾರ",
  "landing.preview.safety": "ಸುರಕ್ಷತೆ",
  "landing.preview.suitability": "ಮೀನುಗಾರಿಕೆ ಸೂಕ್ತತೆ",
  "landing.preview.route": "ಮಾರ್ಗ",
  "landing.preview.evidence": "ಸಾಕ್ಷ್ಯ",
  "landing.preview.cta": "ORCA ಪ್ರವೇಶಿಸಿ",
  "landing.footer.tagline": "ಸಹಯೋಗಿ ಏಜೆಂಟ್‌ಗಳೊಂದಿಗೆ ಸಮುದ್ರ ಪರಿಸರ ವ್ಯವಸ್ಥೆ ತಾರ್ಕಿಕತೆ",
  "landing.footer.problem": "SIH26176",
  "landing.footer.sponsor": "ISRO",
  "header.stakeholder": "ಸಂದರ್ಭ",
  "header.boatClass": "ದೋಣಿ ವರ್ಗ",
  "header.boatClassNotSet": "ಹೊಂದಿಸಿಲ್ಲ",
  "header.language": "ಭಾಷೆ",
  "boatClass.traditionalNonmotorized": "ಸಾಂಪ್ರದಾಯಿಕ / ಎಂಜಿನ್ ಇಲ್ಲದ ದೋಣಿ",
  "boatClass.smallMotorized": "ಸಣ್ಣ ಮೋಟಾರು ದೋಣಿ (10 ಮೀ ಗಿಂತ ಕಡಿಮೆ)",
  "boatClass.mediumMechanized": "ಮಧ್ಯಮ ಯಾಂತ್ರಿಕ ದೋಣಿ (10-15 ಮೀ)",
  "boatClass.largeMechanized": "ದೊಡ್ಡ ಯಾಂತ್ರಿಕ ಹಡಗು (15 ಮೀ ಗಿಂತ ಹೆಚ್ಚು)",
  "pfz.withinRange": "ನಿಮ್ಮ ದೋಣಿಯ ವ್ಯಾಪ್ತಿಯೊಳಗೆ",
  "pfz.outOfRange": "ನಿಮ್ಮ ದೋಣಿಯ ಘೋಷಿತ ವ್ಯಾಪ್ತಿಯ ಆಚೆ",
  "header.connection": "ಬ್ಯಾಕೆಂಡ್",
  "header.dataStatus": "ದತ್ತಾಂಶ",
  "conn.online": "ಆನ್‌ಲೈನ್",
  "conn.degraded": "ಭಾಗಶಃ",
  "conn.offline": "ಬ್ಯಾಕೆಂಡ್ ಲಭ್ಯವಿಲ್ಲ",
  "conn.checking": "ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…",
  "chat.title": "ORCA ಗೆ ಕೇಳಿ",
  "chat.placeholder": "ಸಮುದ್ರ ಪ್ರಶ್ನೆ ಕೇಳಿ…",
  "chat.send": "ಕಳುಹಿಸಿ",
  "chat.clear": "ಅಳಿಸಿ",
  "chat.retry": "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
  "chat.suggested": "ಸೂಚಿತ ಪ್ರಶ್ನೆಗಳು",
  "chat.analyzing": "ORCA ಸಮುದ್ರ ಪರಿಸ್ಥಿತಿಗಳನ್ನು ವಿಶ್ಲೇಷಿಸುತ್ತಿದೆ…",
  "chat.analyzingLong":
    "ಇನ್ನೂ ಕೆಲಸ ನಡೆಯುತ್ತಿದೆ — ಉತ್ತರಿಸುವ ಮೊದಲು ORCA ಹವಾಮಾನ, ಸಮುದ್ರ ಮತ್ತು ಅಪಾಯ ವಿಶ್ಲೇಷಣೆ ನಡೆಸುತ್ತದೆ; ಕೆಲವು ಪ್ರಶ್ನೆಗಳಿಗೆ ಸ್ವಲ್ಪ ಹೆಚ್ಚು ಸಮಯ ಬೇಕಾಗಬಹುದು.",
  "chat.errorTitle": "ವಿನಂತಿ ವಿಫಲವಾಗಿದೆ",
  "chat.emptyTitle": "ಸಮುದ್ರ ಮೌಲ್ಯಮಾಪನ ಪ್ರಾರಂಭಿಸಿ",
  "chat.emptyHint": "ಮೇಲೆ ಸಂದರ್ಭ ಆರಿಸಿ, ನಂತರ ಪ್ರಶ್ನೆ ಕೇಳಿ ಅಥವಾ ಸಲಹೆ ಆರಿಸಿ.",
  "chat.you": "ನೀವು",
  "chat.orca": "ORCA",
  "panel.decision": "ನಿರ್ಣಯ",
  "panel.risk": "ಸಮುದ್ರ ಅಪಾಯ",
  "panel.suitability": "ಮೀನುಗಾರಿಕೆ ಸೂಕ್ತತೆ",
  "panel.evidence": "ಸಾಕ್ಷ್ಯ",
  "panel.conflicts": "ಸಾಕ್ಷ್ಯ ಸಂಘರ್ಷ",
  "panel.reference": "ಅಧಿಕೃತ ಉಲ್ಲೇಖಗಳು",
  "panel.provenance": "ನಿರ್ಣಯದ ಮೂಲ",
  "panel.alerts": "ಎಚ್ಚರಿಕೆಗಳು",
  "panel.activity": "ORCA ಚಟುವಟಿಕೆ",
  "panel.explanation": "ಈ ನಿರ್ಣಯ ಏಕೆ?",
  "panel.report": "ವರದಿ",
  "tab.decision": "ನಿರ್ಣಯ",
  "tab.details": "ವಿವರಗಳು",
  "tab.evidence": "ಸಾಕ್ಷ್ಯ",
  "tab.provenance": "ಮೂಲ",
  "tab.alerts": "ಎಚ್ಚರಿಕೆ",
  "tab.activity": "ಚಟುವಟಿಕೆ",
  "panel.marineDetails": "ಸಮುದ್ರ ವಿವರಗಳು",
  "nav.sections": "ವಿಭಾಗಗಳು",
  "nav.returnToWorkspace": "ಕಾರ್ಯಕ್ಷೇತ್ರಕ್ಕೆ ಹಿಂತಿರುಗಿ",
  "nav.engineRoom": "ಎಂಜಿನ್ ಕೊಠಡಿ",
  "nav.sos": "ತುರ್ತು (SOS)",
  "sos.title": "ತುರ್ತು ಸಂಕಷ್ಟ ಸಂದೇಶ",
  "sos.lead": "ಪ್ರಮಾಣಿತ ಮೇಡೇ ರೇಡಿಯೊ ಸಂದೇಶವನ್ನು ಸಿದ್ಧಪಡಿಸಿ ಮತ್ತು ಭಾರತೀಯ ಕರಾವಳಿ ರಕ್ಷಣಾ ಪಡೆಯನ್ನು ಸಂಪರ್ಕಿಸಿ - ದುರ್ಬಲ ಸಿಗ್ನಲ್‌ನಲ್ಲೂ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತದೆ, ಮೊದಲು ORCA ಪ್ರಶ್ನೆಯ ಅಗತ್ಯವಿಲ್ಲ.",
  "sos.disclaimer": "ಈ ಪುಟವು ನಿಮಗಾಗಿ ಸಂಕಷ್ಟ ಸಂದೇಶವನ್ನು ಸಿದ್ಧಪಡಿಸುತ್ತದೆ, ಅದನ್ನು ನೀವೇ ಕಳುಹಿಸಬೇಕು (ಕರೆ, ರೇಡಿಯೊ, SMS ಅಥವಾ WhatsApp ಮೂಲಕ). ಇದು ತಾನಾಗಿಯೇ ಯಾರನ್ನೂ ಸಂಪರ್ಕಿಸುವುದಿಲ್ಲ ಮತ್ತು ನಿಜವಾದ ತುರ್ತು ಪರಿಸ್ಥಿತಿಯಲ್ಲಿ VHF ಚಾನೆಲ್ 16 ಅಥವಾ ನೇರ ಕರಾವಳಿ ರಕ್ಷಣಾ ಕರೆಗೆ ಬದಲಿಯಲ್ಲ.",
  "sos.step1.title": "1. ತುರ್ತು ಪರಿಸ್ಥಿತಿ ಏನು?",
  "sos.category.flooding": "ದೋಣಿಯಲ್ಲಿ ನೀರು ತುಂಬುತ್ತಿದೆ",
  "sos.category.fire": "ದೋಣಿಯಲ್ಲಿ ಬೆಂಕಿ",
  "sos.category.collision": "ಡಿಕ್ಕಿ",
  "sos.category.manOverboard": "ವ್ಯಕ್ತಿ ಸಮುದ್ರಕ್ಕೆ ಬಿದ್ದಿದ್ದಾರೆ",
  "sos.category.disabled": "ದೋಣಿ ಕೆಟ್ಟಿದೆ / ತೇಲುತ್ತಿದೆ",
  "sos.category.medical": "ವೈದ್ಯಕೀಯ ತುರ್ತುಸ್ಥಿತಿ",
  "sos.category.severeWeather": "ತೀವ್ರ ಹವಾಮಾನ",
  "sos.category.security": "ಕಡಲ್ಗಳ್ಳತನ / ಭದ್ರತಾ ಬೆದರಿಕೆ",
  "sos.step2.title": "2. ನಿಮ್ಮ ವಿವರಗಳು",
  "sos.vesselName": "ದೋಣಿಯ ಹೆಸರು",
  "sos.vesselNamePlaceholder": "ಉದಾ. ಮತ್ಸ್ಯ ರಾಣಿ",
  "sos.personsAboard": "ದೋಣಿಯಲ್ಲಿರುವ ಜನರ ಸಂಖ್ಯೆ",
  "sos.boatClassHint": "ದಾಖಲಾದ ದೋಣಿ ವರ್ಗ: {cls}",
  "sos.gps.get": "ನನ್ನ ಸ್ಥಳ ಪಡೆಯಿರಿ",
  "sos.gps.requesting": "ಸ್ಥಳ ಪಡೆಯಲಾಗುತ್ತಿದೆ...",
  "sos.gps.denied": "ಸ್ಥಳ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ - ಸಾಧ್ಯವಾದರೆ ನಿಮ್ಮ ಸ್ಥಳವನ್ನು ನೆನಪಿನಿಂದ ರೇಡಿಯೊದಲ್ಲಿ ತಿಳಿಸಿ.",
  "sos.gps.unavailable": "ಈ ಸಾಧನದಲ್ಲಿ ಸ್ಥಳ ಲಭ್ಯವಿಲ್ಲ.",
  "sos.gps.notYet": "ಸ್ಥಳ ಇನ್ನೂ ಪಡೆದಿಲ್ಲ.",
  "sos.step3.title": "3. ಸಹಾಯಕ್ಕಾಗಿ ಕಳುಹಿಸಿ",
  "sos.step3.selectFirst": "ನಿಮ್ಮ ಸಂಕಷ್ಟ ಸಂದೇಶ ರಚಿಸಲು ಮೇಲೆ ತುರ್ತು ಪ್ರಕಾರ ಆಯ್ಕೆಮಾಡಿ.",
  "sos.action.speak": "ಗಟ್ಟಿಯಾಗಿ ಓದಿ",
  "sos.action.copy": "ಪಠ್ಯ ನಕಲಿಸಿ",
  "sos.action.copied": "ನಕಲಿಸಲಾಗಿದೆ",
  "sos.action.copyUnsupported": "ಈ ಸಾಧನದಲ್ಲಿ ನಕಲಿಸುವಿಕೆ ಲಭ್ಯವಿಲ್ಲ - ದಯವಿಟ್ಟು ಮೇಲಿನ ಸಂದೇಶವನ್ನು ಓದಿ ಅಥವಾ ಫೋಟೋ ತೆಗೆಯಿರಿ.",
  "sos.action.call": "ಕರಾವಳಿ ರಕ್ಷಣಾ ಪಡೆಗೆ ಕರೆ ಮಾಡಿ ({number})",
  "sos.action.sms": "SMS ಮೂಲಕ ಹಂಚಿಕೊಳ್ಳಿ",
  "sos.action.whatsapp": "WhatsApp ಮೂಲಕ ಹಂಚಿಕೊಳ್ಳಿ",
  "sos.checklist.title": "ಪ್ರಯಾಣ-ಪೂರ್ವ ಸುರಕ್ಷತಾ ಪರಿಶೀಲನಾ ಪಟ್ಟಿ",
  "sos.checklist.lead": "ಈ ಸಾಧನದಲ್ಲಿ ಮಾತ್ರ ಉಳಿಸಲಾಗಿದೆ. ಪ್ರತಿ ಪ್ರಯಾಣದ ಮೊದಲು ಪರಿಶೀಲಿಸಿ.",
  "sos.checklist.epirb": "EPIRB (ತುರ್ತು ಬೀಕನ್) ದೋಣಿಯಲ್ಲಿದೆ ಮತ್ತು ಪರೀಕ್ಷಿಸಲಾಗಿದೆ",
  "sos.checklist.sart": "SART / ರಾಡಾರ್ ಟ್ರಾನ್ಸ್‌ಪಾಂಡರ್ ದೋಣಿಯಲ್ಲಿದೆ",
  "sos.checklist.liferaft": "ಲೈಫ್ ರಾಫ್ಟ್ ದೋಣಿಯಲ್ಲಿದೆ ಮತ್ತು ಮಾನ್ಯವಾಗಿದೆ",
  "sos.checklist.pfd": "ಪ್ರತಿಯೊಬ್ಬರಿಗೂ ಲೈಫ್ ಜಾಕೆಟ್ (PFD) ಇದೆ",
  "sos.checklist.grabbag": "ಗ್ರ್ಯಾಬ್-ಬ್ಯಾಗ್ ಸಿದ್ಧವಾಗಿದೆ (ಟಾರ್ಚ್, ಸೀಟಿ, ಫ್ಲೇರ್, ನೀರು)",
  "sos.checklist.fireExtinguisher": "ಅಗ್ನಿಶಾಮಕ ದೋಣಿಯಲ್ಲಿದೆ ಮತ್ತು ಪರೀಕ್ಷಿಸಲಾಗಿದೆ",
  "sos.checklist.firstAid": "ಪ್ರಥಮ ಚಿಕಿತ್ಸಾ ಕಿಟ್ ದೋಣಿಯಲ್ಲಿದೆ",
  "sos.checklist.radioCharged": "VHF ರೇಡಿಯೊ / ಫೋನ್ ಪೂರ್ಣ ಚಾರ್ಜ್ ಆಗಿದೆ",
  "panel.engineRoom": "ORCA ಎಂಜಿನ್ ಕೊಠಡಿ",
  "phase.understanding": "ಗ್ರಹಿಕೆ",
  "phase.collection": "ಸಮಾನಾಂತರ ಡೇಟಾ ಸಂಗ್ರಹಣೆ",
  "phase.core": "ನಿಶ್ಚಿತ ತರ್ಕ ಕೋರ್",
  "phase.route": "ಮಾರ್ಗ ಯೋಜನೆ",
  "phase.intelligence": "ಪರಿಸರ ಮತ್ತು ಉಲ್ಲೇಖ ಬುದ್ಧಿಮತ್ತೆ",
  "phase.output": "ಫಲಿತಾಂಶ ಮತ್ತು ಮೂಲ",
  "kind.llm": "LLM ವ್ಯಾಖ್ಯಾನ",
  "kind.deterministic": "ನಿಶ್ಚಿತ",
  "kind.data": "ಡೇಟಾ ಬುದ್ಧಿಮತ್ತೆ",
  "stage.understand": "ಪ್ರಶ್ನೆ ಗ್ರಹಿಕೆ ಏಜೆಂಟ್",
  "stage.normalize": "ಸ್ಥಳ ಸಾಮಾನ್ಯೀಕರಣ/ಪರಿಹಾರ",
  "stage.plan": "ಕಾರ್ಯಗತಗೊಳಿಸುವಿಕೆ ಯೋಜನಾ ಏಜೆಂಟ್",
  "stage.weather": "ಹವಾಮಾನ ಬುದ್ಧಿಮತ್ತೆ",
  "stage.ocean": "ಸಮುದ್ರಶಾಸ್ತ್ರ ಬುದ್ಧಿಮತ್ತೆ",
  "stage.gis": "GIS ಮತ್ತು ಜಿಯೋಫೆನ್ಸಿಂಗ್",
  "stage.environment": "ಸಮುದ್ರ-ಬಣ್ಣ ಏಜೆಂಟ್",
  "stage.advisory": "ಸಮುದ್ರ ಸಲಹಾ ಏಜೆಂಟ್",
  "stage.fabric": "ಸಾಗರ ದತ್ತಾಂಶ ಫ್ಯಾಬ್ರಿಕ್",
  "stage.temporal": "ತಾತ್ಕಾಲಿಕ ಸಿಂಧುತ್ವ ಗೇಟ್",
  "stage.fusion": "ಪ್ರಾದೇಶಿಕ-ತಾತ್ಕಾಲಿಕ ಸಂಯೋಜನೆ",
  "stage.arbitration": "ಸಾಕ್ಷ್ಯ ಮಧ್ಯಸ್ಥಿಕೆ",
  "stage.conflicts": "ಸಂಘರ್ಷ ಪತ್ತೆ",
  "stage.suitability": "ಮೀನುಗಾರಿಕೆ ಸೂಕ್ತತೆ ಎಂಜಿನ್",
  "stage.risk": "ಅಪಾಯ ಎಂಜಿನ್",
  "stage.policy": "ನೀತಿ ಮತ್ತು ಸುರಕ್ಷತಾ ಗಾರ್ಡ್",
  "stage.decision": "ನಿರ್ಧಾರ ಎಂಜಿನ್",
  "stage.route": "ಮಾರ್ಗ ಏಜೆಂಟ್ (A*)",
  "stage.route.reasonNotAllowed": "ಸುರಕ್ಷತಾ ಸ್ಥಿತಿ ಮಾರ್ಗಕ್ಕೆ ಅನುಮತಿಸುವುದಿಲ್ಲ",
  "stage.route.reasonNotRequested": "ಯಾವುದೇ ಮಾರ್ಗ ವಿನಂತಿಸಿಲ್ಲ",
  "stage.alerts": "ಎಚ್ಚರಿಕೆ ಸಂಶ್ಲೇಷಣೆ",
  "stage.whatif": "ವಾಟ್-ಇಫ್ ಸಿಮ್ಯುಲೇಶನ್",
  "stage.pfz": "PFZ ಉಲ್ಲೇಖ ಹುಡುಕಾಟ",
  "stage.productivity": "ಪರಿಸರ ಉತ್ಪಾದಕತೆ",
  "stage.environmentalComparison": "ಪರಿಸರ ಹೋಲಿಕೆ",
  "stage.environmentalStability": "ಪರಿಸರ ಸ್ಥಿರತೆ",
  "stage.environmentalAnomaly": "ಪರಿಸರ ವೈಪರೀತ್ಯ ಲೆನ್ಸ್",
  "stage.environmentalNeighbourhood": "ಪರಿಸರ ನೆರೆಹೊರೆ",
  "stage.environmentalEvidence": "ಪರಿಸರ ಸಾಕ್ಷ್ಯ ಮತ್ತು ಪುನರುತ್ಪಾದನೀಯತೆ",
  "stage.research": "ಸಂಶೋಧನಾ ಮೋಡ್",
  "stage.provenance": "ಮೂಲ ಗ್ರಾಫ್",
  "stage.explain": "ಸಾಕ್ಷ್ಯ ಮತ್ತು ವಿವರಣೆ",
  "stage.assemble": "ಪ್ರತಿಕ್ರಿಯೆ ಜೋಡಣೆ",
  "activity.parallelNote": "{total} ರಲ್ಲಿ {ran} ಸಮಾನಾಂತರ ಶಾಖೆಗಳು ಚಾಲನೆಯಾದವು",
  "activity.intelligenceSummary": "{ran} ಚಾಲನೆಯಾದವು · {skipped} ಈ ಪ್ರಶ್ನೆಗೆ ಅನ್ವಯಿಸುವುದಿಲ್ಲ",
  "activity.showAll": "ಎಲ್ಲಾ ಹಂತಗಳನ್ನು ತೋರಿಸಿ",
  "activity.hideAll": "ಅನ್ವಯಿಸದ ಹಂತಗಳನ್ನು ಮರೆಮಾಡಿ",
  "engine.title": "ORCA ಎಂಜಿನ್ ಕೊಠಡಿ",
  "engine.subtitle": "ORCA ಹೇಗೆ ನಿರ್ಮಿತವಾಗಿದೆ - ಪ್ರಸ್ತುತ ಪ್ರಶ್ನೆಯ ಲೈವ್ ಸ್ಥಿತಿಯೊಂದಿಗೆ",
  "engine.noQuery": "ಇನ್ನೂ ಯಾವುದೇ ಪ್ರಶ್ನೆ ಇಲ್ಲ. ಈ ಪ್ರಶ್ನೆಯ ಲೈವ್ ಸ್ಥಿತಿ ನೋಡಲು ORCA ಗೆ ಪ್ರಶ್ನೆ ಕೇಳಿ.",
  "engine.thisTurn": "ಈ ಪ್ರಶ್ನೆ",
  "engine.sources.title": "ಡೇಟಾ ಮೂಲಗಳು",
  "engine.sources.desc": "ORCA ಓದುವ ಬಾಹ್ಯ ಮೂಲಗಳು, ಪ್ರತಿಯೊಂದೂ ಲೈವ್, ಕ್ಯಾಶ್, ಉಲ್ಲೇಖ ಅಥವಾ ಡೆಮೊ ಸ್ಥಿತಿಯೊಂದಿಗೆ.",
  "engine.fabric.title": "ಸಾಗರ ದತ್ತಾಂಶ ಫ್ಯಾಬ್ರಿಕ್",
  "engine.fabric.desc": "ಪ್ರತಿ ಏಜೆಂಟ್ ಫಲಿತಾಂಶವನ್ನು ಸಾಮಾನ್ಯಗೊಳಿಸುತ್ತದೆ, ಸಿಂಧುತ್ವ ಕಿಟಕಿಯ ಮೂಲಕ ಪರಿಶೀಲಿಸುತ್ತದೆ, ಸಾಕ್ಷ್ಯವನ್ನು ಸಂಯೋಜಿಸಿ ಮಧ್ಯಸ್ಥಿಕೆ ವಹಿಸುತ್ತದೆ.",
  "engine.agents.title": "ವಿಶೇಷ ಏಜೆಂಟ್‌ಗಳು",
  "engine.agents.desc": "ಏಳು ಏಜೆಂಟ್ ಮಾಡ್ಯೂಲ್‌ಗಳು. ಎರಡು LLM ಮೂಲಕ ವ್ಯಾಖ್ಯಾನಿಸುತ್ತವೆ; ಉಳಿದವು ನಿಶ್ಚಿತ ಅಥವಾ ಶುದ್ಧ ಡೇಟಾ ಬುದ್ಧಿಮತ್ತೆ.",
  "engine.core.title": "ನಿಶ್ಚಿತ ತರ್ಕ ಕೋರ್",
  "engine.core.desc": "LLM ಇಲ್ಲ, ನೆಟ್‌ವರ್ಕ್ ಇಲ್ಲ, ಯಾದೃಚ್ಛಿಕತೆ ಇಲ್ಲ. ಒಂದೇ ಇನ್‌ಪುಟ್ ಮತ್ತು ಕಾನ್ಫಿಗರೇಶನ್ ಯಾವಾಗಲೂ ಒಂದೇ ಫಲಿತಾಂಶ ನೀಡುತ್ತವೆ.",
  "engine.core.safetyNote": "ಹಾರ್ಡ್ ಜಿಯೋಫೆನ್ಸ್ → ಕಾಣೆಯಾದ ಸಾಕ್ಷ್ಯ → SEVERE → HIGH/MODERATE → ALLOWED. LLM ಈ ಫಲಿತಾಂಶವನ್ನು ಬದಲಾಯಿಸಲಾಗುವುದಿಲ್ಲ.",
  "engine.output.title": "ಫಲಿತಾಂಶ",
  "engine.output.desc": "ನಿರ್ಧಾರ, ಐಚ್ಛಿಕ ಮಾರ್ಗ, ಮೂಲ ಗ್ರಾಫ್ ಮತ್ತು ಆಧಾರಸಹಿತ ವಿವರಣೆ ಚಾಟ್, ನಕ್ಷೆ, ಎಚ್ಚರಿಕೆಗಳು ಮತ್ತು ವರದಿಗಳನ್ನು ತಲುಪುತ್ತವೆ.",
  "engine.agent.understand.desc": "ಭಾಷಾ ಪತ್ತೆ, ಉದ್ದೇಶ ಮತ್ತು ಘಟಕ ಹೊರತೆಗೆಯುವಿಕೆ",
  "engine.agent.weather.desc": "ಗಾಳಿ, ಮಳೆ, ಮುನ್ಸೂಚನೆ ಪರಿಸ್ಥಿತಿಗಳು",
  "engine.agent.ocean.desc": "ಅಲೆಯ ಎತ್ತರ, ಅವಧಿ, ಸಮುದ್ರ ಸ್ಥಿತಿ",
  "engine.agent.gis.desc": "ಜಿಯೋಫೆನ್ಸ್, EEZ, ಸಂರಕ್ಷಿತ ಪ್ರದೇಶಗಳು, ಆಳ",
  "engine.agent.risk.desc": "ನಿಶ್ಚಿತ ಅಪಾಯ ಮತ್ತು ಸೂಕ್ತತೆ ಸಮನ್ವಯ",
  "engine.agent.explain.desc": "ಆಧಾರಸಹಿತ ಸ್ವಾಭಾವಿಕ-ಭಾಷೆ ವಿವರಣೆ",
  "engine.agent.route.desc": "ಹಾರ್ಡ್-ಜಿಯೋಫೆನ್ಸ್ ಪರಿಶೀಲನೆಯೊಂದಿಗೆ A* ಯೋಜನೆ",
  "decision.safetyStatus": "ಸುರಕ್ಷತಾ ಸ್ಥಿತಿ",
  "decision.primaryFactors": "ಮುಖ್ಯ ಅಂಶಗಳು",
  "decision.dataConfidence": "ದತ್ತಾಂಶ ವಿಶ್ವಾಸ",
  "decision.noSafeTitle": "ಸುರಕ್ಷಿತ ಶಿಫಾರಸು ಇಲ್ಲ",
  "decision.noSafeBody":
    "ವಿಶ್ವಾಸಾರ್ಹ ಸುರಕ್ಷತಾ ನಿರ್ಣಯಕ್ಕೆ ಅಗತ್ಯವಿರುವ ನಿರ್ಣಾಯಕ ಸಾಕ್ಷ್ಯ ಲಭ್ಯವಿಲ್ಲ ಅಥವಾ ಪರಿಹರಿಸಲಾಗಿಲ್ಲ. ORCA ಶಿಫಾರಸನ್ನು ರಚಿಸುವುದಿಲ್ಲ.",
  "decision.missingConflicting": "ಲಭ್ಯವಿಲ್ಲದ / ವಿರೋಧಾತ್ಮಕ ಸಾಕ್ಷ್ಯ",
  "decision.warning.advisoryUnavailable":
    "ಈ ಸ್ಥಳಕ್ಕೆ ಪ್ರಸ್ತುತ ಯಾವುದೇ ಸಕ್ರಿಯ ಅಧಿಕೃತ ಸಲಹೆ ಲಭ್ಯವಿಲ್ಲ. ORCA ಇತ್ತೀಚಿನ ಲಭ್ಯವಿರುವ ಹವಾಮಾನ, ಸಾಗರ ಮತ್ತು ಸುರಕ್ಷತಾ ದತ್ತಾಂಶವನ್ನು ಬಳಸುತ್ತಿದೆ.",
  "decision.warning.geofenceUnavailable":
    "ಕೆಲವು ಜಿಯೋಫೆನ್ಸ್ ದತ್ತಾಂಶ ಲಭ್ಯವಿಲ್ಲ; ಮೌಲ್ಯಮಾಪನವು ಪರಿಶೀಲಿಸಲಾದ ಲಭ್ಯ ನಿರ್ಬಂಧಗಳನ್ನು ಮಾತ್ರ ಆಧರಿಸಿದೆ.",
  "decision.warning.factorUnavailable":
    "{factor} ದತ್ತಾಂಶ ಪ್ರಸ್ತುತ ಲಭ್ಯವಿಲ್ಲ; ಒಟ್ಟಾರೆ ಅಂಕವು ORCA ಪರಿಶೀಲಿಸಬಹುದಾದ ಅಂಶಗಳನ್ನು ಮಾತ್ರ ಪ್ರತಿಬಿಂಬಿಸುತ್ತದೆ.",
  "decision.warning.factorUnavailableCritical":
    "ಸುರಕ್ಷತಾ-ನಿರ್ಣಾಯಕ {factor} ದತ್ತಾಂಶ ಲಭ್ಯವಿಲ್ಲ; ಇದನ್ನು ಪರಿಶೀಲಿಸುವವರೆಗೆ ORCA ಒಂದು ಸಂಪ್ರದಾಯಶೀಲ ಸುರಕ್ಷತಾ ಅಂಚನ್ನು ಅನ್ವಯಿಸುತ್ತದೆ.",
  "riskFactor.wave": "ಅಲೆಯ ಎತ್ತರ",
  "riskFactor.wind": "ಗಾಳಿಯ ವೇಗ",
  "riskFactor.lightningProxy": "ಮಿಂಚು/ಗುಡುಗು",
  "riskFactor.cycloneProxy": "ಚಂಡಮಾರುತ",
  "risk.overall": "ಒಟ್ಟು ಅಪಾಯ",
  "risk.contributing": "ಕೊಡುಗೆ ನೀಡುವ ಅಂಶಗಳು",
  "risk.missingCritical": "ಲಭ್ಯವಿಲ್ಲದ ಸುರಕ್ಷತಾ-ನಿರ್ಣಾಯಕ ದತ್ತಾಂಶ",
  "risk.dataSufficiency": "ದತ್ತಾಂಶ ಸಮರ್ಪಕತೆ",
  "risk.notComputed": "ಈ ಪ್ರಶ್ನೆಗೆ ಅಪಾಯ ಲೆಕ್ಕಹಾಕಲಾಗಿಲ್ಲ.",
  "suitability.derived": "ORCA-ಪಡೆದ — ಸುರಕ್ಷತೆಯಿಂದ ಪ್ರತ್ಯೇಕ",
  "suitability.pfzNote": "PFZ ಉಲ್ಲೇಖ",
  "panel.advisory": "ಅಧಿಕೃತ ಸಮುದ್ರ ಸಲಹೆ",
  "advisory.distinctNote":
    "IMD ಸಲಹಾ ಉಲ್ಲೇಖ — ಇದು ಒಂದು ಐಚ್ಛಿಕ ಅಧಿಕೃತ ಮೂಲವಾಗಿದ್ದು, ಕೆಳಗಿನ ORCA ದ ಸ್ವಂತ ಲೆಕ್ಕಾಚಾರದ ಅಪಾಯದ ಮೌಲ್ಯಮಾಪನದಿಂದ ಪ್ರತ್ಯೇಕವಾಗಿದೆ.",
  "advisory.area": "ಸಮುದ್ರ ಪ್ರದೇಶ",
  "advisory.status.no_warning": "ಎಚ್ಚರಿಕೆ ಇಲ್ಲ",
  "advisory.status.caution": "ಎಚ್ಚರಿಕೆ",
  "advisory.status.do_not_venture": "ಮೀನುಗಾರರು ಸಮುದ್ರಕ್ಕೆ ಹೋಗದಂತೆ ಸಲಹೆ",
  "advisory.availability.unavailable":
    "ಐಚ್ಛಿಕ IMD ಸಲಹಾ ಉಲ್ಲೇಖ ಲಭ್ಯವಿಲ್ಲ; ORCA ದ ಸ್ವತಂತ್ರ ಸುರಕ್ಷತಾ ಮೌಲ್ಯಮಾಪನ ಸಕ್ರಿಯವಾಗಿದೆ.",
  "advisory.availability.expired": "ಸಲಹೆ ಅವಧಿ ಮುಗಿದಿದೆ",
  "advisory.availability.not_yet_valid": "ಸಲಹೆ ಇನ್ನೂ ಜಾರಿಯಲ್ಲಿಲ್ಲ",
  "advisory.availability.no_location_match": "ಈ ಸ್ಥಳಕ್ಕೆ ಯಾವುದೇ ಅಧಿಕೃತ ಸಲಹೆ ಪ್ರದೇಶವಿಲ್ಲ",
  "advisory.valid": "ಮಾನ್ಯ",
  "advisory.validFrom": "ಈ ಸಮಯದಿಂದ ಮಾನ್ಯ",
  "advisory.retrieved": "ಪಡೆಯಲಾಗಿದೆ",
  "advisory.retrievedLive": "ಲೈವ್",
  "advisory.source": "ಮೂಲ",
  "advisory.notApplicable": "ವಿನಂತಿಸಿದ ಸಮಯಕ್ಕೆ ಅನ್ವಯಿಸುವುದಿಲ್ಲ",
  "panel.geofence": "ಜಿಯೋಫೆನ್ಸ್ ಪರಿಶೀಲನೆ",
  "geofence.status.inside": "ನಿರ್ಬಂಧಿತ ಪ್ರದೇಶದೊಳಗೆ",
  "geofence.status.clear": "ಜಿಯೋಫೆನ್ಸ್ ಪರಿಶೀಲನೆ: ಸ್ಪಷ್ಟ (CLEAR)",
  "geofence.status.unavailable": "ಜಿಯೋಫೆನ್ಸ್ ಪರಿಶೀಲನೆ ಲಭ್ಯವಿಲ್ಲ",
  "geofence.note.inside":
    "ಈ ಸ್ಥಳವು ಕಠಿಣ-ನಿರ್ಬಂಧಿತ ಜಿಯೋಫೆನ್ಸ್ ವಲಯದೊಳಗಿದೆ; ORCA ದ ಸುರಕ್ಷತಾ ನಿರ್ಧಾರ ಮತ್ತು ಮಾರ್ಗ ಯೋಜನೆ ಈಗಾಗಲೇ ಇದನ್ನು ಪ್ರತಿಬಿಂಬಿಸುತ್ತದೆ.",
  "geofence.note.clear":
    "ORCA ಈ ಸ್ಥಳವನ್ನು ಪ್ರಸ್ತುತ ಲೋಡ್ ಮಾಡಲಾದ ಪ್ರಾದೇಶಿಕ ಉಲ್ಲೇಖ ದತ್ತಾಂಶದ ವಿರುದ್ಧ ಪರಿಶೀಲಿಸಿದೆ ಮತ್ತು ಯಾವುದೇ ಕಠಿಣ-ನಿರ್ಬಂಧಿತ-ವಲಯ ನಿರ್ಬಂಧ ಸಕ್ರಿಯಗೊಂಡಿಲ್ಲ ಎಂದು ಕಂಡುಕೊಂಡಿದೆ.",
  "geofence.note.unavailable":
    "ಜಿಯೋಫೆನ್ಸ್ ದತ್ತಾಂಶ ಪ್ರಸ್ತುತ ಲಭ್ಯವಿಲ್ಲ, ಆದ್ದರಿಂದ ಈ ಸ್ಥಳಕ್ಕೆ ನಿರ್ಬಂಧಿತ-ಪ್ರದೇಶ ಕ್ಲಿಯರೆನ್ಸ್ ಅನ್ನು ಪರಿಶೀಲಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ಇದು ಪ್ರದೇಶ ಸ್ಪಷ್ಟ (clear) ಎಂದು ಅರ್ಥವಲ್ಲ.",
  "panel.environmental": "ಪರಿಸರ ಸಂದರ್ಭ",
  "env.productivity": "ಪರಿಸರ ಉತ್ಪಾದಕತೆ ಸಾಮರ್ಥ್ಯ",
  "env.sst": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ",
  "env.chlorophyll": "ಕ್ಲೋರೊಫಿಲ್-a",
  "env.tide": "ಮಾದರಿ ಆಧಾರಿತ ಸಮುದ್ರ ಮಟ್ಟ",
  "env.tide.note": "ಮಾದರಿ-ಪಡೆದ ಸಮುದ್ರ ಮಟ್ಟದ ಸಂಕೇತ, ಅಧಿಕೃತ ಉಬ್ಬರವಿಳಿತ-ಗೇಜ್ ವೀಕ್ಷಣೆ ಅಲ್ಲ. ಕರಾವಳಿ ಸಂಚರಣೆಗೆ ಅಲ್ಲ.",
  "env.chlClass": "ಕ್ಲೋರೊಫಿಲ್ ಮಟ್ಟ",
  "env.confidence": "ವಿಶ್ವಾಸ",
  "env.dataSufficiency": "ದತ್ತಾಂಶ ಸಮರ್ಪಕತೆ",
  "env.limitations": "ಮಿತಿಗಳು",
  "env.derived": "ಕೇವಲ ಕ್ಲೋರೊಫಿಲ್-a ನಿಂದ ORCA-ಪಡೆದ — ಕೇವಲ ಪರಿಸರ ಸಂದರ್ಭ, ಸುರಕ್ಷತಾ ಇನ್‌ಪುಟ್ ಅಲ್ಲ. SST ಸಂದರ್ಭ, ಚಾಲಕವಲ್ಲ.",
  "env.noFish": "ಕ್ಲೋರೊಫಿಲ್-a ಪ್ಲವಕ ಜೀವರಾಶಿಯನ್ನು ಪ್ರತಿಬಿಂಬಿಸುತ್ತದೆ. ಇದು ಮೀನಿನ ಇರುವಿಕೆ, ಸಮೃದ್ಧಿ ಅಥವಾ ಹಿಡಿತದ ಅಳತೆ ಅಲ್ಲ.",
  "env.unavailable": "ಲಭ್ಯವಿಲ್ಲ",
  "env.suggestions": "ಸಂಶೋಧಕರ ಮುಂದಿನ ಹಂತಗಳು",
  "env.suggestion.historical": "ಈ ಸ್ಥಳ ಮತ್ತು ಋತುವಿಗೆ ಐತಿಹಾಸಿಕ ಹವಾಮಾನಶಾಸ್ತ್ರದೊಂದಿಗೆ ಹೋಲಿಸಿ.",
  "env.suggestion.seasonal": "ಒಂದೇ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್ ಓದುವ ಮೊದಲು ಋತುಮಾನ ಪ್ಲವಕ ಮಾದರಿಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
  "env.suggestion.combine": "ಸ್ಥಳೀಯ ಪೋಷಕಾಂಶ, ಲವಣತೆ ಅಥವಾ ಪ್ರಾಥಮಿಕ-ಉತ್ಪಾದಕತೆ ವೀಕ್ಷಣೆಗಳೊಂದಿಗೆ ಸಂಯೋಜಿಸಿ.",
  "env.mapPoint": "ಪರಿಸರ ಮಾದರಿ ಬಿಂದು",
  "env.cmp.title": "ಹಿಂದಿನ ವೀಕ್ಷಣೆಯೊಂದಿಗೆ ಹೋಲಿಕೆ",
  "env.cmp.now": "ಈಗ",
  "env.cmp.reference": "ಉಲ್ಲೇಖ",
  "env.cmp.delta": "ವ್ಯತ್ಯಾಸ",
  "env.cmp.window": "ಉಲ್ಲೇಖ ಅವಧಿ",
  "env.cmp.validity": "ಮಾನ್ಯತೆ",
  "env.cmp.higher": "ಉಲ್ಲೇಖಕ್ಕಿಂತ ಹೆಚ್ಚು",
  "env.cmp.lower": "ಉಲ್ಲೇಖಕ್ಕಿಂತ ಕಡಿಮೆ",
  "env.cmp.unchanged": "ಉಲ್ಲೇಖದಿಂದ ಬದಲಾಗಿಲ್ಲ",
  "env.cmp.unknown": "ಹೋಲಿಸಲಾಗದು",
  "env.cmp.unavailable": "ತಾತ್ಕಾಲಿಕ ಹೋಲಿಕೆ ಮಾಡಲಾಗಲಿಲ್ಲ.",
  "env.cmp.note": "ಉಲ್ಲೇಖವು ಇತ್ತೀಚಿನ ಹಿಂದಿನ ಅವಧಿಯ ORCA-ಗಣಿತ ಮೌಲ್ಯ, ಹವಾಮಾನ ಸಾಮಾನ್ಯವಲ್ಲ. ಒಂದು ವ್ಯತ್ಯಾಸ ಪ್ರವೃತ್ತಿಯಲ್ಲ.",
  "env.ev.title": "ಸಾಕ್ಷ್ಯ ಮತ್ತು ಪುನರುತ್ಪಾದನೀಯತೆ",
  "env.ev.status": "ಸಾಕ್ಷ್ಯ ಗುಣಮಟ್ಟ",
  "env.ev.summary": "ಸಾರಾಂಶ",
  "env.ev.current": "ಪ್ರಸ್ತುತ",
  "env.ev.historical": "ಐತಿಹಾಸಿಕ / ಉಲ್ಲೇಖ",
  "env.ev.source": "ಮೂಲ",
  "env.ev.dataset": "ದತ್ತಾಂಶ ಸೆಟ್",
  "env.ev.observed": "ವೀಕ್ಷಣೆ ಸಮಯ",
  "env.ev.validity": "ಮಾನ್ಯತೆ",
  "env.ev.distance": "ಪಿಕ್ಸೆಲ್ ಅಂತರ",
  "env.ev.tier": "ಶ್ರೇಣಿ",
  "env.ev.reproducibility": "ಪುನರುತ್ಪಾದನೀಯತೆ",
  "env.ev.opticalHint": "ಕರಾವಳಿ-ನೀರಿನ ಸಂದರ್ಭ",
  "env.ev.bundle": "ಪುನರುತ್ಪಾದನೀಯತೆ ಬಂಡಲ್",
  "env.ev.copyJson": "JSON ಆಗಿ ನಕಲಿಸಿ",
  "env.ev.copied": "ನಕಲಿಸಲಾಗಿದೆ",
  "env.ev.status.adequate": "ಸಮರ್ಪಕ",
  "env.ev.status.limited": "ಸೀಮಿತ",
  "env.ev.status.insufficient": "ಅಸಮರ್ಪಕ",
  "env.ev.status.unavailable": "ಲಭ್ಯವಿಲ್ಲ",
  "env.stab.title": "ಪ್ರಸರಣ ಮತ್ತು ವ್ಯಾಪ್ತಿ",
  "env.stab.observations": "ವೀಕ್ಷಣೆಗಳು",
  "env.stab.range": "ವ್ಯಾಪ್ತಿ",
  "env.stab.median": "ಮಧ್ಯಂಕ",
  "env.stab.iqr": "IQR",
  "env.stab.quartiles": "Q1 / Q3",
  "env.stab.coverage": "ವ್ಯಾಪ್ತಿ",
  "env.stab.gaps": "ಅಂತರಗಳು",
  "env.stab.insufficientProfile":
    "ಅವಧಿಯಲ್ಲಿ ಮೂರಕ್ಕಿಂತ ಕಡಿಮೆ ವೀಕ್ಷಣೆಗಳು - ಯಾವುದೇ ಪ್ರಸರಣ ಅಂಕಿಅಂಶಗಳನ್ನು ಲೆಕ್ಕಿಸಲಾಗಿಲ್ಲ.",
  "env.stab.note":
    "ಇದು ಸೀಮಿತ ಅವಧಿಯೊಳಗೆ ವೀಕ್ಷಿಸಿದ ಪರಿಸರ ದತ್ತಾಂಶದ ವ್ಯಾಪ್ತಿ ಮತ್ತು ಪ್ರಸರಣವನ್ನು ವಿವರಿಸುತ್ತದೆ. ಇದು ಪ್ರವೃತ್ತಿ, ಮುನ್ಸೂಚನೆ ಅಥವಾ ಮೀನುಗಾರಿಕೆ ಸೂಚಕವಲ್ಲ.",
  "env.stab.status.adequate": "ಸಮರ್ಪಕ",
  "env.stab.status.limited": "ಸೀಮಿತ",
  "env.stab.status.insufficient": "ಅಸಮರ್ಪಕ",
  "env.stab.status.unavailable": "ಲಭ್ಯವಿಲ್ಲ",
  "env.nbhd.title": "ಸ್ಥಳೀಯ ಪ್ರಾತಿನಿಧ್ಯ",
  "env.nbhd.pixels": "ಸಮೀಪದ ಪಿಕ್ಸೆಲ್‌ಗಳು",
  "env.nbhd.range": "ವ್ಯಾಪ್ತಿ",
  "env.nbhd.median": "ಮಧ್ಯಂಕ",
  "env.nbhd.iqr": "IQR",
  "env.nbhd.nearest": "ಹತ್ತಿರದ ಮಾನ್ಯ ಪಿಕ್ಸೆಲ್",
  "env.nbhd.coverage": "ವ್ಯಾಪ್ತಿ",
  "env.nbhd.placement": "ಕೇಂದ್ರ ಪಿಕ್ಸೆಲ್",
  "env.nbhd.placement.within": "ಸಮೀಪದ ವ್ಯಾಪ್ತಿಯೊಳಗೆ",
  "env.nbhd.placement.above": "ಸಮೀಪದ ವ್ಯಾಪ್ತಿಗಿಂತ ಮೇಲೆ",
  "env.nbhd.placement.below": "ಸಮೀಪದ ವ್ಯಾಪ್ತಿಗಿಂತ ಕೆಳಗೆ",
  "env.nbhd.placement.na": "ಸ್ಥಾನ ನೀಡಲಾಗಿಲ್ಲ",
  "env.nbhd.insufficientProfile":
    "ಈ ಕಾಂಪೊಸಿಟ್‌ನಲ್ಲಿ ಮೂರಕ್ಕಿಂತ ಕಡಿಮೆ ಮಾನ್ಯ ಸಮೀಪದ ಪಿಕ್ಸೆಲ್‌ಗಳು - ಯಾವುದೇ ನೆರೆಹೊರೆ ಅಂಕಿಅಂಶಗಳನ್ನು ಲೆಕ್ಕಿಸಲಾಗಿಲ್ಲ.",
  "env.nbhd.note":
    "ಇದು ಕೇವಲ ಒಂದೇ ಕೇಂದ್ರ ಕ್ಲೋರೊಫಿಲ್-a ಪಿಕ್ಸೆಲ್ ಅನ್ನು ಅದೇ ಉಪಗ್ರಹ ಕಾಂಪೊಸಿಟ್‌ನಲ್ಲಿ ಮಾನ್ಯ ಸಮೀಪದ ಪಿಕ್ಸೆಲ್‌ಗಳೊಂದಿಗೆ ಹೋಲಿಸುತ್ತದೆ. ಇದು ವಿವರಣಾತ್ಮಕ ಪ್ರಾತಿನಿಧ್ಯ ಪರಿಶೀಲನೆ, ಸ್ಥಳೀಯ ನಕ್ಷೆ, ಉತ್ಪಾದಕತೆ ಅಂದಾಜು ಅಥವಾ ಮೀನುಗಾರಿಕೆ ಸೂಚಕವಲ್ಲ.",
  "env.nbhd.status.adequate": "ಸಮರ್ಪಕ",
  "env.nbhd.status.limited": "ಸೀಮಿತ",
  "env.nbhd.status.insufficient": "ಅಸಮರ್ಪಕ",
  "env.nbhd.status.unavailable": "ಲಭ್ಯವಿಲ್ಲ",
  "env.anom.title": "ಪರಿಸರ ಅಸಾಮಾನ್ಯ ಮಸೂರ",
  "env.anom.subtitle": "ಇತ್ತೀಚಿನ-ವಿತರಣೆ ವಿಶ್ಲೇಷಣೆ · ಇತ್ತೀಚಿನ ವೀಕ್ಷಣೆಗಳೊಳಗಿನ ಸ್ಥಾನ",
  "env.anom.percentile": "ಶತಮಾನಾಂಕ",
  "env.anom.percentileSuffix": "ನೇ ಶತಮಾನಾಂಕ",
  "env.anom.range": "ವ್ಯಾಪ್ತಿ",
  "env.anom.median": "ಮಧ್ಯಂಕ",
  "env.anom.diffFromMedian": "ಮಧ್ಯಂಕದಿಂದ",
  "env.anom.observations": "ವೀಕ್ಷಣೆಗಳು",
  "env.anom.currentUnavailable":
    "ಪ್ರಸ್ತುತ ವೀಕ್ಷಣೆ ಲಭ್ಯವಿಲ್ಲ; ಇತ್ತೀಚಿನ ವಿತರಣೆಯಲ್ಲಿ ಸ್ಥಾನವನ್ನು ನಿರ್ಧರಿಸಲಾಗಲಿಲ್ಲ.",
  "env.anom.insufficientProfile":
    "ಅವಧಿಯಲ್ಲಿ ಮೂರಕ್ಕಿಂತ ಕಡಿಮೆ ಮಾನ್ಯ ಐತಿಹಾಸಿಕ ವೀಕ್ಷಣೆಗಳು - ಇತ್ತೀಚಿನ ವಿತರಣೆಯ ಸ್ಥಾನವನ್ನು ಲೆಕ್ಕಿಸಲಾಗಿಲ್ಲ.",
  "env.anom.howCalculated": "ಇದನ್ನು ಹೇಗೆ ಲೆಕ್ಕಹಾಕಲಾಗುತ್ತದೆ?",
  "env.anom.methodologyFallback":
    "ಪ್ರಸ್ತುತ ವೀಕ್ಷಣೆಯನ್ನು ಅಸ್ತಿತ್ವದಲ್ಲಿರುವ ಸೀಮಿತ ಇತ್ತೀಚಿನ ಅವಧಿಯ ಮಾನ್ಯ ವೀಕ್ಷಣೆಗಳ ವಿರುದ್ಧ ಇರಿಸಲಾಗುತ್ತದೆ. ಅಮಾನ್ಯ ಅಥವಾ ಲಭ್ಯವಿಲ್ಲದ ಮೌಲ್ಯಗಳನ್ನು ಹೊರಗಿಡಲಾಗುತ್ತದೆ, ಎಂದಿಗೂ ಪ್ರಕ್ಷೇಪಿಸಲಾಗುವುದಿಲ್ಲ. ಕನಿಷ್ಠ ಮೂರು ಮಾನ್ಯ ಐತಿಹಾಸಿಕ ವೀಕ್ಷಣೆಗಳು ಅಗತ್ಯವಿದೆ.",
  "env.anom.status.ok": "ಸ್ಥಾನ ನಿರ್ಧರಿಸಲಾಗಿದೆ",
  "env.anom.status.currentUnavailable": "ಲಭ್ಯವಿಲ್ಲ",
  "env.anom.status.insufficientHistory": "ಅಸಮರ್ಪಕ",
  "env.anom.class.below": "ಇತ್ತೀಚಿನ ವ್ಯಾಪ್ತಿಗಿಂತ ಕೆಳಗೆ",
  "env.anom.class.within": "ಇತ್ತೀಚಿನ ವಿತರಣೆಯೊಳಗೆ",
  "env.anom.class.above": "ಇತ್ತೀಚಿನ ವ್ಯಾಪ್ತಿಗಿಂತ ಮೇಲೆ",
  "env.anom2.current": "ಪ್ರಸ್ತುತ",
  "env.anom2.recentMedian": "ಇತ್ತೀಚಿನ ಮಧ್ಯಂಕ",
  "env.anom2.difference": "ವ್ಯತ್ಯಾಸ",
  "env.anom2.position": "ಸ್ಥಾನ",
  "env.anom2.dataCoverage": "ಡೇಟಾ ವ್ಯಾಪ್ತಿ",
  "env.anom2.lastDays": "ಕಳೆದ",
  "env.anom2.daysLabel": "ದಿನಗಳು",
  "env.anom2.windowLabel": "{days}-ದಿನಗಳ ವೀಕ್ಷಣಾ ವಿಂಡೋ",
  "env.anom2.dataUnavailable": "ಡೇಟಾ ಲಭ್ಯವಿಲ್ಲ",
  "env.anom2.insufficientData": "ಅಸಮರ್ಪಕ ಡೇಟಾ",
  "env.anom2.isAbove": "ಇತ್ತೀಚಿನ ಇಂಟರ್‌ಕ್ವಾರ್ಟೈಲ್ ವ್ಯಾಪ್ತಿಗಿಂತ ಮೇಲಿದೆ.",
  "env.anom2.isWithin": "ಇತ್ತೀಚಿನ ವಿತರಣೆಯೊಳಗೆ ಇದೆ.",
  "env.anom2.isBelow": "ಇತ್ತೀಚಿನ ಇಂಟರ್‌ಕ್ವಾರ್ಟೈಲ್ ವ್ಯಾಪ್ತಿಗಿಂತ ಕೆಳಗಿದೆ.",
  "panel.route": "ಮಾರ್ಗ",
  "route.status": "ಸ್ಥಿತಿ",
  "route.distance": "ದೂರ",
  "route.cost": "ಗ್ರಿಡ್ ಪಥ ವೆಚ್ಚ",
  "route.violations": "ಹಾರ್ಡ್ ಜಿಯೋಫೆನ್ಸ್ ಉಲ್ಲಂಘನೆಗಳು",
  "route.noneTitle": "ಸುರಕ್ಷಿತ ಮಾರ್ಗ ಇಲ್ಲ",
  "route.reason": "ಕಾರಣ",
  "route.notRequested": "ಈ ಪ್ರಶ್ನೆಗೆ ಮಾರ್ಗ ವಿನಂತಿಸಲಾಗಿಲ್ಲ.",
  "route.validated": "ORCA ಮಾರ್ಗ ಏಜೆಂಟ್‌ನಿಂದ ಮೌಲ್ಯೀಕರಿಸಲಾಗಿದೆ",
  "tab.trip": "ಪ್ರಯಾಣ",
  "panel.tripPlanner": "ಮೀನುಗಾರ ಪ್ರಯಾಣ ಯೋಜಕ",
  "panel.routeComparison": "ಮಾರ್ಗ ಹೋಲಿಕೆ",
  "panel.routeAnalytics": "ಮಾರ್ಗ ವಿಶ್ಲೇಷಣೆ",
  "trip.origin": "ಆರಂಭಿಕ ಸ್ಥಳ",
  "trip.destination": "ಗಮ್ಯಸ್ಥಾನ",
  "trip.departure": "ಹೊರಡುವ ಸಮಯ",
  "trip.availableTime": "ಲಭ್ಯವಿರುವ ಪ್ರಯಾಣ ಸಮಯ",
  "trip.workDuration": "ಮೀನುಗಾರಿಕೆ / ಕೆಲಸದ ಅವಧಿ",
  "trip.vesselSpeed": "ದೋಣಿಯ ವೇಗ",
  "trip.vesselSpeedHint": "ಪ್ರಯಾಣ ಸಮಯಕ್ಕೆ ದೋಣಿಯ ವೇಗ ಅಗತ್ಯವಿದೆ.",
  "trip.returnDeadline": "ಹಿಂತಿರುಗುವ ಸಮಯ (ಐಚ್ಛಿಕ)",
  "trip.optional": "ಐಚ್ಛಿಕ",
  "trip.unit.minutes": "ನಿಮಿಷ",
  "trip.unit.knots": "ನಾಟ್",
  "trip.feasibility.title": "ಪ್ರಯಾಣ ಕಾರ್ಯಸಾಧ್ಯತೆ",
  "trip.status.FEASIBLE": "ಪ್ರಯಾಣ ಕಾರ್ಯಸಾಧ್ಯ",
  "trip.status.INFEASIBLE_TIME": "ಸಾಕಷ್ಟು ಸಮಯವಿಲ್ಲ",
  "trip.status.INFEASIBLE_RETURN_DEADLINE": "ಹಿಂತಿರುಗುವ ಗಡುವು ಮೀರಿದೆ",
  "trip.status.BLOCKED_ROUTE": "ನಿರ್ಬಂಧಿಸಲಾಗಿದೆ",
  "trip.status.NO_SAFE_RECOMMENDATION": "ಸುರಕ್ಷಿತ ಶಿಫಾರಸು ಇಲ್ಲ",
  "trip.status.MISSING_DATA": "ಹೆಚ್ಚಿನ ಮಾಹಿತಿ ಅಗತ್ಯ",
  "trip.time.departure": "ಹೊರಡುವ ಸಮಯ",
  "trip.time.outbound": "ಹೋಗುವ ಸಮಯ",
  "trip.time.work": "ಮೀನುಗಾರಿಕೆ / ಕೆಲಸ",
  "trip.time.return": "ಹಿಂತಿರುಗುವಿಕೆ",
  "trip.time.total": "ಒಟ್ಟು",
  "trip.time.available": "ಲಭ್ಯವಿದೆ",
  "trip.time.remaining": "ಉಳಿದಿದೆ",
  "trip.time.estimatedReturn": "ಅಂದಾಜು ಹಿಂತಿರುಗುವಿಕೆ",
  "trip.time.returnBy": "ಹಿಂತಿರುಗುವ ಗಡುವು",
  "trip.time.buffer": "ಹೆಚ್ಚುವರಿ ಸಮಯ",
  "trip.caution": "ಪ್ರಸ್ತುತ ನಿರ್ಣಯ ಎಚ್ಚರಿಕೆ ಆಗಿದೆ - ಹೊರಡುವ ಮೊದಲು ಪರಿಸ್ಥಿತಿಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
  "trip.safetyWindowNote": "ಪ್ರಸ್ತುತ ನಿರ್ಣಯವು ಮೌಲ್ಯಮಾಪನ ಮಾಡಿದ ಸಮಯಕ್ಕೆ ಅನ್ವಯಿಸುತ್ತದೆ.",
  "trip.pfzReferenceLabel": "ಉಲ್ಲೇಖ / ಅಧಿಕೃತ ಸಲಹಾ ಡೇಟಾ — ORCA ರಚಿಸಿಲ್ಲ",
  "trip.noRoute": "ಪ್ರಯಾಣ ಯೋಜಕವನ್ನು ಬಳಸಲು ಮೊದಲು ಮಾರ್ಗವನ್ನು ಯೋಜಿಸಿ (ORCA ಅನ್ನು ಕೇಳಿ ಅಥವಾ ನಕ್ಷೆಯಲ್ಲಿ ಗಮ್ಯಸ್ಥಾನ ಆಯ್ಕೆಮಾಡಿ).",
  "route.compare.title": "ನೇರ ಮಾರ್ಗ ವಿರುದ್ಧ ORCA ಮಾರ್ಗ",
  "route.compare.baseline": "ಮೂಲರೇಖೆ (ನೇರ ರೇಖೆ)",
  "route.compare.baselineBlocked": "ಮೂಲರೇಖೆ (ನಿರ್ಬಂಧಿಸಲಾಗಿದೆ)",
  "route.compare.orca": "ORCA ಮಾರ್ಗ",
  "route.compare.metric": "ಮಾಪನ",
  "route.compare.distance": "ದೂರ",
  "route.compare.violations": "ಹಾರ್ಡ್ ಉಲ್ಲಂಘನೆಗಳು",
  "route.compare.feasible": "ಕಾರ್ಯಸಾಧ್ಯ",
  "route.compare.yes": "ಹೌದು",
  "route.compare.no": "ಇಲ್ಲ",
  "route.compare.explanation": "ORCA ಮಾರ್ಗವು {diff} ಉದ್ದವಾಗಿದೆ ಏಕೆಂದರೆ ನೇರ ರೇಖೆಯು ಇವುಗಳ ಮೂಲಕ ಹಾದುಹೋಗುತ್ತದೆ: {names}",
  "route.compare.loading": "ಮೂಲರೇಖೆ ಹೋಲಿಕೆ ಲೆಕ್ಕಾಚಾರ ಆಗುತ್ತಿದೆ…",
  "route.compare.unavailable": "ಮೂಲರೇಖೆ ಹೋಲಿಕೆ ಲಭ್ಯವಿಲ್ಲ.",
  "route.compare.noRoute": "ಹೋಲಿಸಲು ಇನ್ನೂ ಯಾವುದೇ ಮಾರ್ಗವಿಲ್ಲ.",
  "route.compare.baselineLabel": "ಮೂಲರೇಖೆ = ಆರಂಭಿಕ ಸ್ಥಳ ಮತ್ತು ಗಮ್ಯಸ್ಥಾನದ ನಡುವಿನ ನೇರ ಭೌಗೋಳಿಕ ರೇಖೆ - ಇದು ಮಾರ್ಗ ಅಲ್ಗಾರಿದಮ್ ಅಲ್ಲ, ಕೇವಲ ಹೋಲಿಕೆಗಾಗಿ ಒಂದು ಉಲ್ಲೇಖ.",
  "route.compare.definitionNote": "\"ನೇರ\" ಎಂದರೆ ಅನಿರ್ಬಂಧಿತ ನೇರ ರೇಖೆ - ಇದು ಶಿಫಾರಸು ಮಾಡಿದ ಅಥವಾ ಸುರಕ್ಷಿತ ಮಾರ್ಗವಲ್ಲ.",
  "analytics.distance": "ಒಟ್ಟು ದೂರ",
  "analytics.waypoints": "ಮಾರ್ಗ ಬಿಂದುಗಳು",
  "analytics.violations": "ಹಾರ್ಡ್ ಜಿಯೋಫೆನ್ಸ್ ಉಲ್ಲಂಘನೆಗಳು",
  "analytics.feasible": "ಮಾರ್ಗ ಕಾರ್ಯಸಾಧ್ಯ",
  "analytics.safetyStatus": "ಸುರಕ್ಷತಾ ಸ್ಥಿತಿ",
  "analytics.constrainedSegmentsAvoided": "ನೇರ ರೇಖೆಗೆ ಹೋಲಿಸಿದರೆ ತಪ್ಪಿಸಿದ ನಿರ್ಬಂಧಿತ ಪ್ರದೇಶಗಳು",
  "tour.tripPlanner.title": "ಮೀನುಗಾರ ಪ್ರಯಾಣ ಯೋಜಕ",
  "tour.tripPlanner.body": "ಪ್ರಸ್ತುತ ಮಾರ್ಗಕ್ಕೆ ನಿರ್ಣಾಯಕ ಪ್ರಯಾಣ ಕಾರ್ಯಸಾಧ್ಯತೆ ತಪಾಸಣೆ ನೋಡಲು ನಿಮ್ಮ ಲಭ್ಯವಿರುವ ಸಮಯ, ಮೀನುಗಾರಿಕೆ ಅವಧಿ ಮತ್ತು ದೋಣಿಯ ವೇಗವನ್ನು ಹೊಂದಿಸಿ.",
  "tour.routeCompare.title": "ಮಾರ್ಗ ಹೋಲಿಕೆ",
  "tour.routeCompare.body": "ORCA ದ ನಿರ್ಬಂಧ-ಜಾಗೃತ ಮಾರ್ಗವನ್ನು ನೇರ ಮೂಲರೇಖೆಯೊಂದಿಗೆ ಹೋಲಿಸಿ - ದೂರ, ಸಮಯ ಮತ್ತು ತಪ್ಪಿಸಿದ ನಿರ್ಬಂಧಿತ ಪ್ರದೇಶಗಳು, ಒಟ್ಟಿಗೆ.",
  "route.marineAware": "ಸಮುದ್ರ-ಜಾಗೃತ ಮಾರ್ಗ",
  "route.marineAwareNote": "ಅಲೆ/ಗಾಳಿ ಸ್ಥಿತಿಗಳು ಮಾರ್ಗ ವೆಚ್ಚದಲ್ಲಿ ಸೇರಿಸಲಾಗಿದೆ",
  "route.marinePenalty": "ಸಮುದ್ರ ವೆಚ್ಚ ದಂಡ",
  "evidence.source": "ಮೂಲ",
  "evidence.type": "ಪ್ರಕಾರ",
  "evidence.status": "ಸ್ಥಿತಿ",
  "evidence.tier": "ಶ್ರೇಣಿ",
  "evidence.none": "ಈ ಪ್ರಶ್ನೆಗೆ ಯಾವುದೇ ಸಾಕ್ಷ್ಯ ಇಲ್ಲ.",
  "conflict.detected": "ಸಾಕ್ಷ್ಯ ಸಂಘರ್ಷ ಪತ್ತೆಯಾಗಿದೆ",
  "conflict.none": "ಯಾವುದೇ ಸಂಘರ್ಷ ಇಲ್ಲ.",
  "conflict.type": "ಪ್ರಕಾರ",
  "conflict.severity": "ತೀವ್ರತೆ",
  "conflict.resolution": "ಪರಿಹಾರ",
  "conflict.safetyAffected": "ಸುರಕ್ಷತಾ-ನಿರ್ಣಾಯಕ",
  "reference.pfzTitle": "INCOIS PFZ",
  "reference.snapshot": "ಉಲ್ಲೇಖ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್",
  "reference.validUntil": "ಮಾನ್ಯತೆ",
  "reference.view": "ಸಲಹೆ ವೀಕ್ಷಿಸಿ",
  "reference.notOrca": "ಅಧಿಕೃತ ಉಲ್ಲೇಖ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್. ORCA-ಪಡೆದ ಮುನ್ಸೂಚನೆ ಅಲ್ಲ.",
  "reference.none": "ಈ ಪ್ರಶ್ನೆಗೆ ಯಾವುದೇ ಅಧಿಕೃತ ಉಲ್ಲೇಖ ಇಲ್ಲ.",
  "provenance.title": "ORCA ಈ ನಿರ್ಣಯಕ್ಕೆ ಹೇಗೆ ತಲುಪಿತು",
  "provenance.why": "ಪ್ರಶ್ನೆ → ಸಾಕ್ಷ್ಯ → ತರ್ಕ → ಸುರಕ್ಷತೆ → ನಿರ್ಣಯ",
  "provenance.none": "ಈ ಪ್ರಶ್ನೆಗೆ ಮೂಲ ಗ್ರಾಫ್ ಇಲ್ಲ.",
  "provenance.inspect": "ಪರಿಶೀಲಿಸಲು ನೋಡ್ ಆರಿಸಿ",
  "alerts.none": "ಈ ಪ್ರಶ್ನೆಗೆ ಎಚ್ಚರಿಕೆ ಇಲ್ಲ.",
  "alerts.proxyNote":
    "ಗುಡುಗು ಮತ್ತು ಚಂಡಮಾರುತ ಸೂಚನೆಗಳು ಮಾದರಿ-ಆಧಾರಿತ ಪ್ರಾಕ್ಸಿಗಳು, ಪ್ರಮಾಣೀಕೃತ ನೈಜ-ಸಮಯ ಪತ್ತೆ ಅಲ್ಲ.",
  "activity.title": "ಏಜೆಂಟ್ ಕಾರ್ಯಗತಿ",
  "activity.done": "ಪೂರ್ಣ",
  "activity.skipped": "ಬಿಟ್ಟುಬಿಡಲಾಗಿದೆ",
  "activity.pending": "ನಡೆದಿಲ್ಲ",
  "activity.failed": "ವಿಫಲ",
  "activity.timingMeasured": "ಪ್ರತಿ-ಹಂತದ ಸಮಯವನ್ನು ಸರ್ವರ್‌ನಲ್ಲಿ ಅಳೆಯಲಾಗಿದೆ (ನೈಜ, ಅನುಕರಣೆ ಅಲ್ಲ).",
  "activity.timingUnavailable": "ಕಾರ್ಯಗತಿ ಸ್ಥಿತಿ ಮಾತ್ರ — ಈ ಪ್ರತಿಕ್ರಿಯೆಯಲ್ಲಿ ಪ್ರತಿ-ಹಂತದ ಸಮಯ ಇಲ್ಲ.",
  "activity.correlation": "ಸಂಬಂಧ ಐಡಿ",
  "activity.total": "ಒಟ್ಟು ಅಳತೆ",
  "explanation.why": "ಈ ನಿರ್ಣಯ ಏಕೆ?",
  "explanation.disclaimer":
    "ORCA ಒಂದು ನಿರ್ಣಯ-ಬೆಂಬಲ ವ್ಯವಸ್ಥೆ. ಕಾರ್ಯಾಚರಣೆಯ ಮೊದಲು ಅಧಿಕೃತ ಸಮುದ್ರ ಮತ್ತು ಹವಾಮಾನ ಸಲಹೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
  "verdict.why": "ಏಕೆ",
  "verdict.location": "ಸ್ಥಳ",
  "verdict.observed": "ಸ್ಥಿತಿಗಳು ದಾಖಲಾಗಿವೆ",
  "verdict.riskBreakdown": "ಅಪಾಯ ವಿವರ",
  "verdict.fullExplanation": "ಪೂರ್ಣ ವಿವರಣೆ",
  "verdict.envContext": "ಪರಿಸರ ಮತ್ತು ಸಂಶೋಧನಾ ಸಂದರ್ಭ",
  "verdict.operationalDetail": "ಕಾರ್ಯಾಚರಣೆ ವಿವರ",
  "verdict.whatIf": "ಊಹಾತ್ಮಕ ಸನ್ನಿವೇಶ ಸಿಮ್ಯುಲೇಶನ್",
  "evidence.reviewed": "ಸಾಕ್ಷ್ಯ ದಾಖಲೆಗಳು ಪರಿಶೀಲಿಸಲಾಗಿದೆ",
  "map.layers": "ನಕ್ಷೆ ಪದರಗಳು",
  "map.legend": "ದತ್ತಾಂಶ ಮೂಲ",
  "map.legend.live": "ನೈಜ ಅವಲೋಕನ / ಮುನ್ಸೂಚನೆ",
  "map.legend.reference": "ಅಧಿಕೃತ ಉಲ್ಲೇಖ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್",
  "map.legend.derived": "ORCA ಲೆಕ್ಕಹಾಕಿದ",
  "map.legend.demo": "ಉದಾಹರಣೆ / ಡೆಮೊ ದತ್ತಾಂಶ",
  "map.legend.missing": "ಲಭ್ಯವಿಲ್ಲ",
  "map.noGeometry": "ಈ ಪ್ರಶ್ನೆಗೆ ಜ್ಯಾಮಿತಿ ಲಭ್ಯವಿಲ್ಲ.",
  "map.orcaRoute": "ORCA ಮಾರ್ಗ",
  "map.noRoute": "ಸುರಕ್ಷಿತ ಮಾರ್ಗ ಇಲ್ಲ",
  "map.origin": "ಆರಂಭ",
  "map.destination": "ಗಮ್ಯ",
  "map.routeDestinationN": "PFZ {n} / {count}",
  "layer.group.marineBase": "ಸಮುದ್ರ ಆಧಾರ",
  "layer.group.orcaAnalysis": "ORCA ವಿಶ್ಲೇಷಣೆ",
  "layer.group.fishingEnvironment": "ಮೀನುಗಾರಿಕೆ ಮತ್ತು ಪರಿಸರ",
  "layer.badge.orca": "ORCA",
  "layer.badge.incois": "INCOIS",
  "layer.badge.live": "ಲೈವ್",
  "layer.badge.pointData": "ಪಾಯಿಂಟ್ ಡೇಟಾ",
  "layer.source.reference": "ಅಧಿಕೃತ ಉಲ್ಲೇಖ ಪದರ",
  "layer.source.orca": "ORCA ಲೆಕ್ಕಹಾಕಿದ",
  "layer.source.incois": "INCOIS ಅಧಿಕೃತ ಉಲ್ಲೇಖ",
  "layer.source.live": "ಲೈವ್ ಅವಲೋಕನ",
  "layer.risk": "ಅಪಾಯ",
  "layer.coastline": "ಕರಾವಳಿ",
  "layer.eez": "ಭಾರತೀಯ EEZ",
  "layer.protected_areas": "ಸಂರಕ್ಷಿತ ಪ್ರದೇಶಗಳು",
  "layer.geofences": "ಜಿಯೋಫೆನ್ಸ್",
  "layer.route": "ಮಾರ್ಗ",
  "layer.pfz": "INCOIS PFZ ಉಲ್ಲೇಖ",
  "layer.pfz.noLocationMatch": "ಈ ನಿಖರ ಸ್ಥಳಕ್ಕೆ ಯಾವುದೇ ಅಧಿಕೃತ INCOIS PFZ ಸಲಹೆ ಹೊಂದಿಕೆಯಾಗುವುದಿಲ್ಲ.",
  "layer.pfz.checking": "ಅಧಿಕೃತ INCOIS PFZ ಲಭ್ಯತೆಯನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…",
  "layer.pfz.noGeometry": "ಈ ಸ್ಥಳಕ್ಕೆ ಅಧಿಕೃತ INCOIS ಉಲ್ಲೇಖ ನಕ್ಷೆಯಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
  "layer.pfz.zoneCount": "ಅಧಿಕೃತ INCOIS ಉಲ್ಲೇಖ — {count} ವಲಯ(ಗಳು)",
  "layer.pfz.landingCentreOnly":
    "ಇಂದಿಗೆ ಯಾವುದೇ PFZ ವಲಯ ಸಲಹೆ ಇಲ್ಲ — ಹತ್ತಿರದ ಅಧಿಕೃತ INCOIS ಉಲ್ಲೇಖ ಲ್ಯಾಂಡಿಂಗ್ ಕೇಂದ್ರವನ್ನು ತೋರಿಸಲಾಗುತ್ತಿದೆ.",
  "layer.sst": "ಸಮುದ್ರ ಮೇಲ್ಮೈ ತಾಪಮಾನ",
  "layer.chlorophyll": "ಕ್ಲೋರೊಫಿಲ್-a",
  "layer.sst.available":
    "Open-Meteo Marine ಮೌಲ್ಯ — Environmental ಮಾದರಿ-ಬಿಂದು ಗುರುತಿನ ಮೇಲೆ ತೋರಿಸಲಾಗಿದೆ (ಗ್ರಿಡ್ ಓವರ್‌ಲೇ ಇಲ್ಲ).",
  "layer.sst.unavailable":
    "ಈ ಪ್ರಶ್ನೆಗೆ SST ಲಭ್ಯವಿಲ್ಲ — ಮಾನ್ಯ Open-Meteo Marine ಮೌಲ್ಯ ಇಲ್ಲ.",
  "layer.chlorophyll.available":
    "NOAA CoastWatch (VIIRS) ಮೌಲ್ಯ — Environmental ಮಾದರಿ-ಬಿಂದು ಗುರುತಿನ ಮೇಲೆ ತೋರಿಸಲಾಗಿದೆ (ಗ್ರಿಡ್ ಓವರ್‌ಲೇ ಇಲ್ಲ).",
  "layer.chlorophyll.unavailable":
    "ಕ್ಲೋರೊಫಿಲ್-a ಲಭ್ಯವಿಲ್ಲ — ಬಹುಶಃ ಉಪಗ್ರಹ ಮೋಡ / ದತ್ತಾಂಶ ವ್ಯಾಪ್ತಿ ಅಥವಾ ಮಾನ್ಯತೆ ಮಿತಿಗಳ ಕಾರಣ. ಯಾವುದೇ ಮೌಲ್ಯ ತೋರಿಸಲಾಗಿಲ್ಲ.",
  "layer.environmentalSuitability": "ORCA ಪರಿಸರ ಸೂಕ್ತತೆ",
  "layer.environmentalSuitability.noLocation": "ಈ ಲೇಯರ್ ಲೋಡ್ ಮಾಡಲು ಮೊದಲು ORCA ಗೆ ಒಂದು ಸ್ಥಳದ ಬಗ್ಗೆ ಕೇಳಿ.",
  "map.layers.expand": "ನಕ್ಷೆ ಪದರ ನಿಯಂತ್ರಣಗಳನ್ನು ತೋರಿಸಿ",
  "map.layers.collapse": "ನಕ್ಷೆ ಪದರ ನಿಯಂತ್ರಣಗಳನ್ನು ಮರೆಮಾಡಿ",
  "map.layers.active": "{count} ಸಕ್ರಿಯ",
  "layer.desc.coastline": "ಭಾರತದ ಕರಾವಳಿ ಗಡಿ",
  "layer.desc.eez": "ಭಾರತದ ವಿಶೇಷ ಆರ್ಥಿಕ ವಲಯ",
  "layer.desc.protected_areas": "ಸಮುದ್ರ/ಕರಾವಳಿ ಸಂರಕ್ಷಿತ ಪ್ರದೇಶಗಳು",
  "layer.desc.geofences": "ನಿರ್ಬಂಧಿತ ಕಠಿಣ-ಹೊರಗಿಡುವಿಕೆ ಗಡಿಗಳು",
  "layer.desc.risk": "ORCA ಸುರಕ್ಷತಾ ಅಪಾಯ ಮೌಲ್ಯಮಾಪನ",
  "layer.desc.route": "ORCA ಮೌಲ್ಯಮಾಪನ ಮಾಡಿದ ಮಾರ್ಗ — ಸುರಕ್ಷಿತ ಮಾರ್ಗದ ಖಾತರಿ ಅಲ್ಲ",
  "layer.desc.environmental": "ಈ ಪ್ರಶ್ನೆಗಾಗಿ ಪರಿಸರ ಮಾದರಿ ಬಿಂದು",
  "layer.desc.environmentalSuitability": "CHL-ಆಧಾರಿತ ಪ್ರಾದೇಶಿಕ ಸೂಕ್ತತೆ ಗ್ರಿಡ್ (ಸಂಶೋಧನೆ/ಉಲ್ಲೇಖ ಸಂದರ್ಭ)",
  "layer.desc.pfz": "ಅಧಿಕೃತ INCOIS PFZ ಉಲ್ಲೇಖ — ORCA-ಪಡೆದದ್ದಲ್ಲ",
  "env.suitability.title": "ORCA ಪರಿಸರ ಸೂಕ್ತತೆ",
  "env.suitability.disclaimer": "ಕೇವಲ ಪರಿಸರ ಸಂದರ್ಭ — ಇದು ಮೀನು-ಇರುವಿಕೆ ಅಥವಾ ಸುರಕ್ಷತಾ ಮುನ್ಸೂಚನೆ ಅಲ್ಲ.",
  "env.suitability.insufficientData": "ಇಲ್ಲಿ ಸೂಕ್ತತೆ ದೃಶ್ಯೀಕರಣಕ್ಕೆ ಸಾಕಷ್ಟು ಪರಿಸರ ದತ್ತಾಂಶ ಇಲ್ಲ.",
  "env.suitability.legend.low": "ಕಡಿಮೆ",
  "env.suitability.legend.moderate": "ಮಧ್ಯಮ",
  "env.suitability.legend.high": "ಹೆಚ್ಚು",
  "gps.use": "ನನ್ನ ಪ್ರಸ್ತುತ ಸ್ಥಳವನ್ನು ಬಳಸಿ",
  "gps.requesting": "ಸ್ಥಳವನ್ನು ವಿನಂತಿಸಲಾಗುತ್ತಿದೆ…",
  "gps.granted": "ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಸ್ಥಳವನ್ನು ಬಳಸಲಾಗುತ್ತಿದೆ",
  "gps.denied": "ಸ್ಥಳದ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ",
  "gps.unavailable": "ಪ್ರಸ್ತುತ ಸ್ಥಳ ಲಭ್ಯವಿಲ್ಲ",
  "gps.markerLabel": "ನನ್ನ ಪ್ರಸ್ತುತ ಸ್ಥಳ",
  "pfz.selectedTitle": "INCOIS PFZ ಉಲ್ಲೇಖ ಆಯ್ಕೆಯಾಗಿದೆ",
  "pfz.selectedTitleMulti": "{count} INCOIS PFZ ಉಲ್ಲೇಖಗಳು ಆಯ್ಕೆಯಾಗಿವೆ",
  "pfz.selectedMarkerLabel": "ಆಯ್ಕೆಮಾಡಿದ PFZ ಉಲ್ಲೇಖ",
  "pfz.selectedMarkerLabelMulti": "ಆಯ್ಕೆಮಾಡಿದ PFZ {n}",
  "pfz.navigate": "ಈ PFZ ಗೆ ಮಾರ್ಗ ನಿರ್ದೇಶನ",
  "pfz.navigateMulti": "ಎಲ್ಲಾ {count} ಆಯ್ಕೆಮಾಡಿದ PFZ ಗಳ ಮೂಲಕ ಮಾರ್ಗ ನಿರ್ದೇಶನ",
  "pfz.removeSelection": "ಆಯ್ಕೆ {n} ತೆಗೆದುಹಾಕಿ",
  "pfz.notSafetyNote": "PFZ ಉಲ್ಲೇಖವು ಸುರಕ್ಷತಾ ಶಿಫಾರಸು ಅಲ್ಲ.",
  "pfz.clearSelection": "ಆಯ್ಕೆ ತೆರವುಗೊಳಿಸಿ",
  "pfz.cannotRoute": "ಆಯ್ಕೆಮಾಡಿದ PFZ ಉಲ್ಲೇಖಕ್ಕೆ ಸುರಕ್ಷಿತವಾಗಿ ಮಾರ್ಗ ನಿರ್ದೇಶನ ಮಾಡಲಾಗುವುದಿಲ್ಲ.",
  "pfz.direction": "ದಿಕ್ಕು",
  "pfz.bearing": "ಬೇರಿಂಗ್",
  "pfz.distance": "ದೂರ",
  "pfz.depth": "ಆಳ",
  "pfz.forecast": "ಮುನ್ಸೂಚನೆ",
  "pfz.validUntil": "ಮಾನ್ಯವಾಗಿರುವವರೆಗೆ",
  "pfz.officialSource": "ಅಧಿಕೃತ INCOIS ಉಲ್ಲೇಖ",
  "pfz.ranked.title": "ಶ್ರೇಣೀಕೃತ PFZ ವಲಯಗಳು",
  "pfz.ranked.subtitle": "ಹತ್ತಿರದ ಅಧಿಕೃತ INCOIS ವಲಯಗಳು, ದೂರದ ಆಧಾರದ ಮೇಲೆ ಶ್ರೇಣೀಕರಿಸಲಾಗಿದೆ",
  "pfz.ranked.distanceKm": "{km} ಕಿ.ಮೀ ದೂರದಲ್ಲಿ",
  "pfz.ranked.restricted": "ನಿರ್ಬಂಧಿತ",
  "pfz.ranked.projected": "ಲೆಕ್ಕಹಾಕಿದ ಉಲ್ಲೇಖ",
  "pfz.ranked.selectHint": "ನಕ್ಷೆಯಲ್ಲಿ ಹೈಲೈಟ್ ಮಾಡಲು ಒಂದು ವಲಯವನ್ನು ಆಯ್ಕೆಮಾಡಿ",
  "pfz.ranked.markerTooltip": "PFZ ವಲಯ {n} — {km} ಕಿ.ಮೀ",
  "pfz.ranked.empty": "ಈ ಸ್ಥಳದ ಬಳಿ ಯಾವುದೇ ಹೊಂದಾಣಿಕೆಯಾದ PFZ ವಲಯಗಳಿಲ್ಲ",
  "pfz.ranked.unavailable": "ಈ ಸ್ಥಳ ಅಥವಾ ದಿನಾಂಕಕ್ಕೆ ಪ್ರಸ್ತುತ ಯಾವುದೇ ಅಧಿಕೃತ INCOIS PFZ ಉಲ್ಲೇಖ ಲಭ್ಯವಿಲ್ಲ. ORCA ಯಾವುದೇ PFZ ಸ್ಥಳವನ್ನು ರಚಿಸುವುದಿಲ್ಲ ಅಥವಾ ಅಂದಾಜಿಸುವುದಿಲ್ಲ. ನೀವು ಇನ್ನೂ ಸಮುದ್ರಕ್ಕೆ ಹೋಗುವ ಸುರಕ್ಷತೆ ಮತ್ತು ಪರಿಸರ ಪರಿಸ್ಥಿತಿಗಳನ್ನು ಪ್ರತ್ಯೇಕವಾಗಿ ಮೌಲ್ಯಮಾಪನ ಮಾಡಬಹುದು.",
  "pfz.ranked.noLocationMatch": "ಇಂದು ಈ ನಿಖರ ಸ್ಥಳಕ್ಕೆ ಯಾವುದೇ ಅಧಿಕೃತ INCOIS PFZ ಸಲಹೆ ಹೊಂದಿಕೆಯಾಗುವುದಿಲ್ಲ. ನೀವು ಇನ್ನೂ ಸಮುದ್ರಕ್ಕೆ ಹೋಗುವ ಸುರಕ್ಷತೆ ಮತ್ತು ಪರಿಸರ ಪರಿಸ್ಥಿತಿಗಳನ್ನು ಪ್ರತ್ಯೇಕವಾಗಿ ಮೌಲ್ಯಮಾಪನ ಮಾಡಬಹುದು.",
  "pfz.ranked.landingCentreOnly": "ಇಂದು ಈ ಸ್ಥಳಕ್ಕೆ ಯಾವುದೇ ಕ್ರಮಾಂಕಿತ PFZ ವಲಯ ರೇಖೆ ಹೊಂದಾಣಿಕೆಯಾಗುವುದಿಲ್ಲ. ಬದಲಿಗೆ ನಕ್ಷೆ ಮತ್ತು ಚಾಟ್ ಉತ್ತರದಲ್ಲಿ ಹತ್ತಿರದ ಅಧಿಕೃತ INCOIS ಉಲ್ಲೇಖ ಲ್ಯಾಂಡಿಂಗ್ ಕೇಂದ್ರವನ್ನು ತೋರಿಸಲಾಗಿದೆ.",
  "pfz.ranked.checking": "ಅಧಿಕೃತ INCOIS PFZ ವಲಯಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…",
  "pfz.ranked.available": "{count} ಲಭ್ಯವಿದೆ",
  "pfz.ranked.layerHidden": "PFZ ಪದರ ಮರೆಯಾಗಿದೆ — ಈ ವಲಯಗಳನ್ನು ನೋಡಲು ಮತ್ತು ಆಯ್ಕೆಮಾಡಲು ನಕ್ಷೆ ಪದರಗಳಲ್ಲಿ INCOIS PFZ ಉಲ್ಲೇಖವನ್ನು ಆನ್ ಮಾಡಿ.",
  "pfz.ranked.expand": "ಶ್ರೇಣೀಕೃತ PFZ ವಲಯಗಳನ್ನು ತೋರಿಸಿ",
  "pfz.ranked.collapse": "ಶ್ರೇಣೀಕೃತ PFZ ವಲಯಗಳನ್ನು ಮರೆಮಾಡಿ",
  "route.myLocationToPfz": "ನನ್ನ ಸ್ಥಳ → INCOIS PFZ ಉಲ್ಲೇಖ",
  "route.myLocationToPfzs": "ನನ್ನ ಸ್ಥಳ → {count} ಆಯ್ಕೆಮಾಡಿದ INCOIS PFZ ಉಲ್ಲೇಖಗಳು",
  "route.myLocationToPfzZone": "ನನ್ನ ಸ್ಥಳ → INCOIS PFZ #{n}",
  "mapSidebar.toggleShow": "ನಕ್ಷೆ ಸೈಡ್‌ಬಾರ್ ತೋರಿಸಿ",
  "mapSidebar.toggleHide": "ನಕ್ಷೆ ಸೈಡ್‌ಬಾರ್ ಮರೆಮಾಡಿ",
  "mapTools.title": "ನಕ್ಷೆ ಪರಿಕರಗಳು",
  "routeControls.title": "ಮಾರ್ಗ ನಿಯಂತ್ರಣಗಳು",
  "routeControls.noSelection": "ಅಲ್ಲಿಗೆ ಮಾರ್ಗ ನಿರ್ದೇಶನಕ್ಕಾಗಿ ಶ್ರೇಣೀಕೃತ PFZ ವಲಯವನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
  "routeControls.destination": "ಗಮ್ಯಸ್ಥಾನ",
  "routeControls.pfzLabel": "INCOIS PFZ #{n}",
  "routeControls.computing": "ಮಾರ್ಗವನ್ನು ಲೆಕ್ಕಹಾಕಲಾಗುತ್ತಿದೆ…",
  "routeControls.notRoutedYet": "ಈ ಗಮ್ಯಸ್ಥಾನಕ್ಕೆ ಇನ್ನೂ ಮಾರ್ಗ ನಿರ್ದೇಶನ ಮಾಡಿಲ್ಲ.",
  "routeControls.statusAvailable": "ಮಾರ್ಗ ಲಭ್ಯವಿದೆ",
  "routeControls.statusBlocked": "ನಿರ್ಬಂಧಿತ",
  "routeControls.statusUnavailable": "ಮಾರ್ಗ ಲಭ್ಯವಿಲ್ಲ",
  "routeControls.waypoints": "ವೇಪಾಯಿಂಟ್‌ಗಳು",
  "routeControls.routeButton": "PFZ #{n} ಗೆ ಮಾರ್ಗ ನಿರ್ದೇಶನ",
  "routeControls.viewRoute": "ಮಾರ್ಗ ವೀಕ್ಷಿಸಿ",
  "routeControls.expand": "ಮಾರ್ಗ ನಿಯಂತ್ರಣಗಳನ್ನು ತೋರಿಸಿ",
  "routeControls.collapse": "ಮಾರ್ಗ ನಿಯಂತ್ರಣಗಳನ್ನು ಮರೆಮಾಡಿ",
  "routeControls.originAdjusted": "ಮಾರ್ಗ ಮೂಲ: ಹತ್ತಿರದ ನೌಕಾಯಾನ ಯೋಗ್ಯ ಸಮುದ್ರ ಕೋಶ (ಉಲ್ಲೇಖ ಮೂಲವು ಭೂಮಿಯಲ್ಲಿದೆ)",
  "env.interp": "ಉತ್ಪಾದಕತೆ ವ್ಯಾಖ್ಯಾನ",
  "env.interp.limited": "ಸೀಮಿತ",
  "env.interp.limitedNote":
    "ಕ್ಲೋರೊಫಿಲ್-a ಲಭ್ಯವಿಲ್ಲ; ಪರಿಸರ ಉತ್ಪಾದಕತೆ ಸಾಮರ್ಥ್ಯವನ್ನು ಅಂದಾಜಿಸಲಾಗದು.",
  "env.ev.qualityNote":
    "ಆಧಾರವಾಗಿರುವ SST / ಕ್ಲೋರೊಫಿಲ್-a ಅವಲೋಕನಗಳು ಮಾನ್ಯ, ಮೂಲಸಹಿತ ಮತ್ತು ಸಮಯಮುದ್ರಿತವೇ ಎಂಬುದು — ಉತ್ಪಾದಕತೆಯನ್ನು ವ್ಯಾಖ್ಯಾನಿಸಬಹುದೇ ಎಂಬುದರಿಂದ ಬೇರೆ.",
  "voice.mic.start": "ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಮಾತನಾಡಿ",
  "voice.mic.stop": "ಆಲಿಸುವುದನ್ನು ನಿಲ್ಲಿಸಿ",
  "voice.mic.unsupported": "ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಇನ್‌ಪುಟ್ ಬೆಂಬಲಿತವಲ್ಲ",
  "voice.mic.error": "ಮೈಕ್ರೊಫೋನ್ ರೆಕಾರ್ಡಿಂಗ್ ವಿಫಲವಾಗಿದೆ — ನೀವು ಇನ್ನೂ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಬಹುದು",
  "voice.mic.permissionDenied":
    "ಮೈಕ್ರೊಫೋನ್ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ — ಧ್ವನಿ ಇನ್‌ಪುಟ್ ಬಳಸಲು ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಅನುಮತಿ ನೀಡಿ, ಅಥವಾ ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ",
  "voice.mic.deviceUnavailable": "ಯಾವುದೇ ಮೈಕ್ರೊಫೋನ್ ಸಾಧನ ಕಂಡುಬಂದಿಲ್ಲ — ನೀವು ಇನ್ನೂ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಬಹುದು",
  "voice.mic.insecureContext":
    "ಧ್ವನಿ ಇನ್‌ಪುಟ್‌ಗೆ ಸುರಕ್ಷಿತ (HTTPS ಅಥವಾ localhost) ಸಂಪರ್ಕ ಅಗತ್ಯವಿದೆ — ನೀವು ಇನ್ನೂ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಬಹುದು",
  "voice.listening": "ಆಲಿಸುತ್ತಿದೆ…",
  "voice.tts.play": "ಗಟ್ಟಿಯಾಗಿ ಓದಿ",
  "voice.tts.stop": "ಓದುವುದನ್ನು ನಿಲ್ಲಿಸಿ",
  "voice.tts.unsupported": "ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಗಟ್ಟಿಯಾಗಿ ಓದುವುದು ಬೆಂಬಲಿತವಲ್ಲ",
  "voice.speaking": "ಮಾತನಾಡುತ್ತಿದೆ…",
  "tour.start": "ಪ್ರವಾಸ ಪ್ರಾರಂಭಿಸಿ",
  "tour.skip": "ಬಿಟ್ಟುಬಿಡಿ",
  "tour.back": "ಹಿಂದೆ",
  "tour.next": "ಮುಂದೆ",
  "tour.finish": "ಮುಗಿಸಿ",
  "tour.stepOf": "{total} ರಲ್ಲಿ {current}",
  "tour.overview.title": "ORCA ಗೆ ಸುಸ್ವಾಗತ",
  "tour.overview.body":
    "ORCA ಮೀನುಗಾರರು, ವಿಪತ್ತು ನಿರ್ವಾಹಕರು ಮತ್ತು ಸಂಶೋಧಕರಿಗಾಗಿ ಒಂದು ಸಮುದ್ರ ನಿರ್ಧಾರ-ಬೆಂಬಲ ವ್ಯವಸ್ಥೆ. ಈ ಪ್ರವಾಸ ನಿಜವಾದ ಇಂಟರ್‌ಫೇಸ್ ಮೂಲಕ ಸಾಗುತ್ತದೆ — ಇಲ್ಲಿ ಏನೂ ನಕಲಿಯಲ್ಲ.",
  "tour.ask.title": "ಸಮುದ್ರ ಪ್ರಶ್ನೆ ಕೇಳಿ",
  "tour.ask.body":
    "ಇಲ್ಲಿ ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ, ಅಥವಾ ಕೆಳಗಿನ ಸೂಚಿತ ಪ್ರಶ್ನೆಗಳಲ್ಲಿ ಒಂದನ್ನು ಆರಿಸಿ. ನಿಮ್ಮ ಪ್ರಶ್ನೆ ORCA ದ ನಿಜವಾದ ಪ್ರಕ್ರಿಯೆಯ ಮೂಲಕ ಹೋಗುತ್ತದೆ — ಗ್ರಹಿಕೆ, ಡೇಟಾ ಸಂಗ್ರಹ, ನಿರ್ಣಾಯಕ ಅಪಾಯ ಮತ್ತು ಸುರಕ್ಷತಾ ಮೌಲ್ಯಮಾಪನ, ನಂತರ ನಿರ್ಣಯ.",
  "tour.liveData.title": "ಲೈವ್ ಸಮುದ್ರ ಮತ್ತು ಹವಾಮಾನ ಡೇಟಾ",
  "tour.liveData.body":
    "ಈ ಪ್ಯಾನೆಲ್ ನಕ್ಷೆ ಪದರಗಳನ್ನು ನಿಯಂತ್ರಿಸುತ್ತದೆ — ಲೈವ್ ಅಲೆ, ಗಾಳಿ, ಸಮುದ್ರ-ಮೇಲ್ಮೈ ತಾಪಮಾನ ಮತ್ತು ಅಧಿಕೃತ INCOIS/IMD ಉಲ್ಲೇಖ ಡೇಟಾ ORCA ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಸ್ಥಳಕ್ಕಾಗಿ ಪಡೆಯುತ್ತದೆ.",
  "tour.decision.title": "ನಿರ್ಣಯ",
  "tour.decision.body":
    "ORCA ಬಳಿ ಉತ್ತರ ಇದ್ದಾಗ, ಈ ಕಾರ್ಡ್ ಕಾರ್ಯಾಚರಣೆ ನಿರ್ಣಯವನ್ನು ತೋರಿಸುತ್ತದೆ — ಮುಂದುವರಿಯಿರಿ, ಎಚ್ಚರಿಕೆಯಿಂದ ಮುಂದುವರಿಯಿರಿ, ಅಥವಾ ಮುಂದುವರಿಯಬೇಡಿ — ಇದನ್ನು ನಿರ್ಣಾಯಕವಾಗಿ ಲೆಕ್ಕಹಾಕಲಾಗುತ್ತದೆ, AI ಊಹಿಸುವುದಿಲ್ಲ.",
  "tour.why.title": "ಈ ನಿರ್ಣಯ ಏಕೆ?",
  "tour.why.body":
    "ಇವು ನಿರ್ಣಯದ ಹಿಂದಿನ ನಿಜವಾದ ಕಾರಣಗಳು, ನೇರವಾಗಿ ರಿಸ್ಕ್ ಎಂಜಿನ್ ಮತ್ತು ಸೇಫ್ಟಿ ಗಾರ್ಡ್‌ನಿಂದ ತೆಗೆದುಕೊಳ್ಳಲಾಗಿದೆ — ಎಂದಿಗೂ ಸೃಷ್ಟಿಸಿದ ವಿವರಣೆಯಲ್ಲ.",
  "tour.safety.title": "ಸುರಕ್ಷತಾ ಕಾವಲು",
  "tour.safety.body":
    "ಸುರಕ್ಷತೆಯನ್ನು ಅಪಾಯದಿಂದ ಪ್ರತ್ಯೇಕವಾಗಿ ಒಂದು ನಿರ್ಣಾಯಕ ಸೇಫ್ಟಿ ಗಾರ್ಡ್ ಮೌಲ್ಯಮಾಪನ ಮಾಡುತ್ತದೆ, ಮತ್ತು ಇದು ಉಳಿದೆಲ್ಲವನ್ನೂ ಅತಿಕ್ರಮಿಸಬಹುದು — AI ಪದರ ಎಂದಿಗೂ ಬದಲಾಯಿಸಲಾಗದ ಏಕೈಕ ವಿಷಯ ಇದು.",
  "tour.replay.title": "ನಿರ್ಣಯ ರಿಪ್ಲೇ",
  "tour.replay.body":
    "ಮುನ್ಸೂಚನೆ ಅವಧಿಯುದ್ದಕ್ಕೂ ಇದೇ ನಿರ್ಣಯ ಗಂಟೆಗಂಟೆಗೆ ಹೇಗೆ ಬದಲಾಗುತ್ತದೆ ಎಂಬುದನ್ನು ಅನ್ವೇಷಿಸಿ — ಅದೇ ನಿರ್ಣಾಯಕ ಪ್ರಕ್ರಿಯೆಯನ್ನು ಮರುಚಲಾಯಿಸಲಾಗುತ್ತದೆ, ಎಂದಿಗೂ ಎರಡನೇ ಲೈವ್ ನಿರ್ಣಯವಲ್ಲ.",
  "tour.route.title": "ಮಾರ್ಗ ಯೋಜನೆ",
  "tour.route.body":
    "ಮಾರ್ಗವನ್ನು ವಿನಂತಿಸಿದಾಗ, ORCA ಅದನ್ನು ನಿಜವಾದ ಜಿಯೋಫೆನ್ಸ್, ಸಂರಕ್ಷಿತ ಪ್ರದೇಶಗಳು ಮತ್ತು ಸಮುದ್ರ ಪರಿಸ್ಥಿತಿಗಳ ವಿರುದ್ಧ ಯೋಜಿಸುತ್ತದೆ, ಮತ್ತು ಕಠಿಣ ಸುರಕ್ಷತಾ ಗಡಿಯನ್ನು ದಾಟುವ ಮಾರ್ಗವನ್ನು ನಿರಾಕರಿಸುತ್ತದೆ.",
  "tour.evidence.title": "ಸಾಕ್ಷ್ಯ ಮತ್ತು ಮೂಲ",
  "tour.evidence.body":
    "ಈ ನಿರ್ಣಯವನ್ನು ತಲುಪಲು ORCA ಬಳಸಿದ ಪ್ರತಿಯೊಂದು ಮೌಲ್ಯವನ್ನು ಇಲ್ಲಿ ಅದರ ಮೂಲ, ಹಂತ ಮತ್ತು ಸಿಂಧುತ್ವದೊಂದಿಗೆ ಪಟ್ಟಿ ಮಾಡಲಾಗಿದೆ, ಇದರಿಂದ ನಿರ್ಣಯವನ್ನು ಸ್ವತಂತ್ರವಾಗಿ ಪರಿಶೀಲಿಸಬಹುದು.",
  "tour.environmental.title": "ಪರಿಸರ ಸಂಶೋಧನೆ",
  "tour.environmental.body":
    "ಸಂಶೋಧಕರಿಗಾಗಿ: ಸಮುದ್ರ-ಮೇಲ್ಮೈ ತಾಪಮಾನ, ಕ್ಲೋರೊಫಿಲ್-a ಮತ್ತು ಸಂಬಂಧಿತ ಸಂದರ್ಭ — ಕೇವಲ ವಿವರಣಾತ್ಮಕ, ಹಿಡಿತ ಊಹಿಸಲು ಅಥವಾ ಮೀನುಗಾರಿಕೆ ಫಲಿತಾಂಶದ ಖಾತರಿಗಾಗಿ ಎಂದಿಗೂ ಬಳಸಲಾಗುವುದಿಲ್ಲ.",
  "tour.engineRoom.title": "ಎಂಜಿನ್ ಕೊಠಡಿ",
  "tour.engineRoom.body":
    "ORCA ದ ನಿಜವಾದ ವಾಸ್ತುಶಿಲ್ಪ, ಮತ್ತು ಕೊನೆಯ ಪ್ರಶ್ನೆಗಾಗಿ, ನಿಜವಾದ ಏಜೆಂಟ್ ಕಾರ್ಯಗತಗೊಳಿಸುವಿಕೆ ಜಾಡು — ಯಾವ ಹಂತಗಳು, ಯಾವ ಕ್ರಮದಲ್ಲಿ ಮತ್ತು ಪ್ರತಿಯೊಂದಕ್ಕೂ ಎಷ್ಟು ಸಮಯ ತೆಗೆದುಕೊಂಡಿತು ಎಂಬುದನ್ನು ನಿಖರವಾಗಿ ತೋರಿಸುತ್ತದೆ.",
  "evidence.export": "ಸಾಕ್ಷ್ಯವನ್ನು ರಫ್ತು ಮಾಡಿ",
  "evidence.export.success": "ಸಾಕ್ಷ್ಯ ರಫ್ತು ಮಾಡಲಾಗಿದೆ",
  "evidence.export.failure": "ಸಾಕ್ಷ್ಯ ರಫ್ತು ವಿಫಲವಾಗಿದೆ",
  "replay.title": "ನಿರ್ಣಯ ರಿಪ್ಲೇ",
  "replay.emptyNote":
    "ಮೊದಲು ಒಂದು ಮೌಲ್ಯಮಾಪನ ನಡೆಸಿ, ನಂತರ ಇಲ್ಲಿ ಲಭ್ಯವಿರುವ ಮುನ್ಸೂಚನೆ ಅವಧಿಯಲ್ಲಿ ನಿರ್ಣಯ ಹೇಗೆ ಬದಲಾಗುತ್ತದೆ ಎಂಬುದನ್ನು ಅನ್ವೇಷಿಸಿ.",
  "replay.intro":
    "ಸಮುದ್ರ ಪರಿಸ್ಥಿತಿಗಳು, ಅಪಾಯ ಮತ್ತು ನಿರ್ಣಾಯಕ ನಿರ್ಣಯ ಲಭ್ಯವಿರುವ ಗಂಟೆವಾರು ಮುನ್ಸೂಚನೆಯಲ್ಲಿ ಹೇಗೆ ಬದಲಾಗುತ್ತವೆ ಎಂಬುದನ್ನು ನೋಡಿ — ಈ ಮೌಲ್ಯಮಾಪನಕ್ಕಾಗಿ ಈಗಾಗಲೇ ಪಡೆದ ಅದೇ ಮುನ್ಸೂಚನೆ ಡೇಟಾದಿಂದ ಪಡೆಯಲಾಗಿದೆ.",
  "replay.explore": "ಸಮಯದೊಂದಿಗೆ ನಿರ್ಣಯವನ್ನು ಅನ್ವೇಷಿಸಿ →",
  "replay.building": "ರಿಪ್ಲೇ ಸಿದ್ಧಪಡಿಸಲಾಗುತ್ತಿದೆ...",
  "replay.genericError": "ನಿರ್ಣಯ ರಿಪ್ಲೇ ಚಲಾಯಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.",
  "replay.noTimestamps": "ರಿಪ್ಲೇ ಮಾಡಲು ಯಾವುದೇ ಮುನ್ಸೂಚನೆ ಸಮಯಗಳು ಲಭ್ಯವಿರಲಿಲ್ಲ.",
  "replay.bannerTitle": "ORCA ನಿರ್ಣಯ ರಿಪ್ಲೇ",
  "replay.bannerSubtitle": "ಸಮುದ್ರ ನಿರ್ಣಯ ಸಮಯದೊಂದಿಗೆ ಹೇಗೆ ಬದಲಾಗುತ್ತದೆ",
  "replay.windowLabel": "ಮುನ್ಸೂಚನೆ · {hours} ಗಂ",
  "replay.howItWorks": "ಇದು ಹೇಗೆ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತದೆ",
  "replay.howItWorksBody":
    "ರಿಪ್ಲೇ ಪ್ರತಿ ಲಭ್ಯವಿರುವ ಮುನ್ಸೂಚನೆ ಗಂಟೆಯನ್ನು ಅದೇ ನಿರ್ಣಾಯಕ ರಿಸ್ಕ್ → ಸೇಫ್ಟಿ → ನಿರ್ಣಯ ಪ್ರಕ್ರಿಯೆಯ ಮೂಲಕ ಮೌಲ್ಯಮಾಪನ ಮಾಡುತ್ತದೆ. ಇದು ಎರಡನೇ ಲೈವ್ ನಿರ್ಣಯವನ್ನು ಸೃಷ್ಟಿಸುವುದಿಲ್ಲ.",
  "replay.forecastAt": "ಮುನ್ಸೂಚನೆ · {time}",
  "replay.timestampSlider": "ರಿಪ್ಲೇ ಸಮಯ",
  "replay.trajectoryLabel": "ಗಂಟೆವಾರು ನಿರ್ಣಯ ಪಥ",
  "replay.changeFromPrevious": "ಹಿಂದಿನ ಗಂಟೆಯಿಂದ ಬದಲಾವಣೆ",
  "replay.baselineNote": "ಮೂಲ ಸಮಯ — ಯಾವುದೇ ಹಿಂದಿನ ಗಂಟೆ ಲಭ್ಯವಿಲ್ಲ.",
  "replay.decisionStable": "ನಿರ್ಣಯ ಸ್ಥಿರವಾಗಿದೆ",
  "replay.decisionStableBody": "ಈ ಅವಧಿಯಲ್ಲಿ ನಿರ್ಣಯ {decision} ಆಗಿಯೇ ಉಳಿದಿದೆ.",
  "replay.whyChanged": "ನಿರ್ಣಯ ಏಕೆ ಬದಲಾಯಿತು?",
  "replay.decisionChangedBadge": "ನಿರ್ಣಯ ಬದಲಾಗಿದೆ",
  "replay.whatChanged": "ಏನು ಬದಲಾಯಿತು?",
  "replay.riskDeltaLabel": "ಅಪಾಯ",
  "replay.safetyTriggerLabel": "ಸಕ್ರಿಯ ಸುರಕ್ಷತಾ ನಿಯಮ:",
  "replay.wave": "ಅಲೆ",
  "replay.wind": "ಗಾಳಿ",
  "replay.sst": "ಸಮುದ್ರ-ಮೇಲ್ಮೈ ತಾಪಮಾನ",
  "replay.risk": "ಅಪಾಯ",
  "replay.safety": "ಸುರಕ್ಷತೆ",
  "replay.decisionRemains": "ನಿರ್ಣಯ {decision} ಆಗಿಯೇ ಉಳಿದಿದೆ",
  "replay.riskFactorsAt": "ಅಪಾಯ ಅಂಶಗಳು — {time}",
  "replay.total": "ಒಟ್ಟು",
  "replay.safetyCheck": "ಸುರಕ್ಷತಾ ಪರಿಶೀಲನೆ",
  "replay.deterministicSafety": "ನಿರ್ಣಾಯಕ ಸುರಕ್ಷತೆ",
  "replay.safetyRuleSingular": "ಸುರಕ್ಷತಾ ನಿಯಮ",
  "replay.safetyRulePlural": "ಸುರಕ್ಷತಾ ನಿಯಮಗಳು",
  "replay.pipelineCaption": "ರಿಸ್ಕ್ ಎಂಜಿನ್ → ಸೇಫ್ಟಿ ಗಾರ್ಡ್ → ನಿರ್ಣಯ",
  "replay.previous": "ಹಿಂದಿನ",
  "replay.next": "ಮುಂದಿನ",
  "replay.pause": "ವಿರಾಮ",
  "replay.playLabel": "ರಿಪ್ಲೇ {hours} ಗಂ",
  "replay.dataCoverage": "ಡೇಟಾ ವ್ಯಾಪ್ತಿ",
  "replay.disclaimerBody":
    "{label}. ಇದು ಈ ಮೌಲ್ಯಮಾಪನಕ್ಕಾಗಿ ಈಗಾಗಲೇ ಪಡೆದ ಮುನ್ಸೂಚನೆ ಡೇಟಾವನ್ನು ORCA ದ ನಿರ್ಣಾಯಕ ರಿಸ್ಕ್, ಸೇಫ್ಟಿ ಮತ್ತು ನಿರ್ಣಯ ಎಂಜಿನ್‌ಗಳ ಮೂಲಕ ನಡೆಸುತ್ತದೆ — ಇದು ಎರಡನೇ ಲೈವ್ ನಿರ್ಣಯವಲ್ಲ.",
  "replay.noPreviousHour": "ಹಿಂದಿನ ಗಂಟೆ ಇಲ್ಲ",
  "replay.vsPrev": "ಹಿಂದಿನದಕ್ಕೆ ಹೋಲಿಸಿದರೆ",
  "replay.legendProceed": "ಮುಂದುವರಿಯಿರಿ",
  "replay.legendCaution": "ಎಚ್ಚರಿಕೆ",
  "replay.legendDoNotProceed": "ಮುಂದುವರಿಯಬೇಡಿ",
  "replay.chartTitle": "ಸಮುದ್ರ ಪರಿಸ್ಥಿತಿಗಳು ಮತ್ತು ಅಪಾಯ ಸಮಯದೊಂದಿಗೆ",
  "replay.chartInsufficientData": "ಪ್ರವೃತ್ತಿ ತೋರಿಸಲು ಸಾಕಷ್ಟು ಮುನ್ಸೂಚನೆ ಗಂಟೆಗಳು ಸಿಗಲಿಲ್ಲ.",
  "replay.previewSuffix": "(ಪೂರ್ವವೀಕ್ಷಣೆ)",
  "replay.chartRowAria": "ರಿಪ್ಲೇ ಅವಧಿಯಲ್ಲಿ {label}",
  "common.expand": "ವಿಸ್ತರಿಸಿ",
  "common.collapse": "ಸಂಕುಚಿಸಿ",
  "common.print": "ಮುದ್ರಿಸಿ / ರಫ್ತು",
  "common.close": "ಮುಚ್ಚಿ",
  "common.na": "ಲಭ್ಯವಿಲ್ಲ",

  // Milestone 5 - Authority / Operational Intelligence Dashboard
  "nav.authority": "ಪ್ರಾಧಿಕಾರ",
  "authority.title": "ಕರಾವಳಿ ಕಾರ್ಯಾಚರಣೆಗಳು",
  "authority.subtitle": "ಮೇಲ್ವಿಚಾರಣೆ ಮಾಡಿದ ಕರಾವಳಿ ಸ್ಥಳಗಳ ಕಾರ್ಯಾಚರಣಾ ಅವಲೋಕನ",
  "authority.dataEdition.live": "ನೈಜ",
  "authority.dataEdition.demo": "ಡೆಮೊ ಡೇಟಾ",
  "authority.demoFixtureNotice":
    "ಡೆಮೊ ಫಿಕ್ಸ್ಚರ್ ಡೇಟಾ — ಕೆಳಗಿನ ಪ್ರತಿ ಸ್ಥಳದ ಸ್ಥಿತಿಯನ್ನು ನಿಗದಿತ ಡೆಮೊ ಫಿಕ್ಸ್ಚರ್‌ನಿಂದ ರಚಿಸಲಾಗಿದೆ, ಆ ಸ್ಥಳದ ಈಗಿನ ನೈಜ (ಲೈವ್) ಪರಿಸ್ಥಿತಿಗಳಿಂದ ಅಲ್ಲ. ನಕ್ಷೆ ಮತ್ತು ಪಟ್ಟಿ ಇನ್ನೂ ಪ್ರತಿ ಸ್ಥಳದ ನೈಜ ಸ್ಥಾನವನ್ನು ತೋರಿಸುತ್ತವೆ.",
  "authority.detail.demoFixtureNotice":
    "ಡೆಮೊ ಫಿಕ್ಸ್ಚರ್ — ಈ ಸ್ಥಿತಿಯನ್ನು ನಿಗದಿತ ಡೆಮೊ ಫಿಕ್ಸ್ಚರ್‌ನಿಂದ ಮೌಲ್ಯಮಾಪನ ಮಾಡಲಾಗಿದೆ, {name} ನ ಈಗಿನ ನೈಜ (ಲೈವ್) ಪರಿಸ್ಥಿತಿಗಳಿಂದ ಅಲ್ಲ.",
  "authority.edition.live": "ನೈಜ",
  "authority.edition.demo": "ಡೆಮೊ ಡೇಟಾ",
  "authority.updated": "ನವೀಕರಿಸಲಾಗಿದೆ {time}",
  "authority.refresh": "ರಿಫ್ರೆಶ್",
  "authority.loading": "ಕರಾವಳಿ ಕಾರ್ಯಾಚರಣೆಗಳು ಲೋಡ್ ಆಗುತ್ತಿದೆ…",
  "authority.error": "ಕರಾವಳಿ ಕಾರ್ಯಾಚರಣಾ ಅವಲೋಕನವನ್ನು ಲೋಡ್ ಮಾಡಲಾಗಲಿಲ್ಲ.",
  "authority.retry": "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
  "authority.locationsMonitored": "ಮೇಲ್ವಿಚಾರಣೆ ಮಾಡಿದ ಸ್ಥಳಗಳು",
  "authority.activeWarnings": "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು",
  "authority.statusDistribution": "ಪ್ರಸ್ತುತ ಪರಿಸ್ಥಿತಿಗಳು",
  "authority.map": "ಕಾರ್ಯಾಚರಣಾ ನಕ್ಷೆ",
  "authority.mapLegend": "ಸ್ಥಿತಿ",
  "authority.attentionRequired": "ಗಮನ ಅಗತ್ಯವಿದೆ",
  "authority.noAttention": "ಪ್ರಸ್ತುತ ಯಾವುದೇ ಸ್ಥಳಕ್ಕೆ ಗಮನ ಅಗತ್ಯವಿಲ್ಲ.",
  "authority.locations": "ಸ್ಥಳಗಳು",
  "authority.locationsTable.location": "ಸ್ಥಳ",
  "authority.locationsTable.status": "ಸ್ಥಿತಿ",
  "authority.locationsTable.warning": "ಎಚ್ಚರಿಕೆ",
  "authority.locationsTable.data": "ಡೇಟಾ",
  "authority.locationsTable.updated": "ನವೀಕರಿಸಲಾಗಿದೆ",
  "authority.warnings": "ಅಧಿಕೃತ ಎಚ್ಚರಿಕೆಗಳು",
  "authority.noWarnings": "ಯಾವುದೇ ಸಕ್ರಿಯ ಅಧಿಕೃತ ಎಚ್ಚರಿಕೆ ಇಲ್ಲ.",
  "authority.dataHealth": "ಡೇಟಾ ಆರೋಗ್ಯ",
  "authority.dataHealth.weather": "ಹವಾಮಾನ",
  "authority.dataHealth.marine": "ಸಮುದ್ರ",
  "authority.noLocations": "ಯಾವುದೇ ಕಾರ್ಯಾಚರಣಾ ಸ್ಥಳಗಳು ಲಭ್ಯವಿಲ್ಲ.",
  "authority.noLocationsHint": "ORCA ಪ್ರಸ್ತುತ ಯಾವುದೇ ಆಯ್ದ ಕರಾವಳಿ ಸ್ಥಳವನ್ನು ಮೌಲ್ಯಮಾಪನ ಮಾಡಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.",
  "authority.selectLocation": "ವಿವರಗಳಿಗಾಗಿ ಒಂದು ಸ್ಥಳವನ್ನು ಆಯ್ಕೆಮಾಡಿ",
  "authority.detail.wave": "ಅಲೆ",
  "authority.detail.wind": "ಗಾಳಿ",
  "authority.detail.warnings": "ಎಚ್ಚರಿಕೆಗಳು",
  "authority.detail.geofence": "ಜಿಯೋಫೆನ್ಸ್",
  "authority.detail.dataConfidence": "ಡೇಟಾ ವಿಶ್ವಾಸಾರ್ಹತೆ",
  "authority.detail.decision": "ನಿರ್ಣಯ",
  "authority.detail.evidence": "ಪುರಾವೆ",
  "authority.detail.evidenceSources": "{count} ಮೂಲಗಳು",
  "authority.detail.openToday": "ಇಂದಿನ ವೀಕ್ಷಣೆ ತೆರೆಯಿರಿ",
  "authority.detail.planTrip": "ಪ್ರಯಾಣ ಯೋಜಿಸಿ",
  "authority.detail.viewSystem": "ಸಿಸ್ಟಮ್ ವೀಕ್ಷಿಸಿ",
  "authority.detail.viewTrace": "ಎಕ್ಸಿಕ್ಯೂಶನ್ ಟ್ರೇಸ್ ವೀಕ್ಷಿಸಿ",
  "authority.detail.viewEvidence": "ಪುರಾವೆ ವೀಕ್ಷಿಸಿ",
  "authority.detail.viewReplay": "ನಿರ್ಣಯ ರಿಪ್ಲೇ",
  "authority.detail.exportEvidence": "ಪುರಾವೆ ರಫ್ತು ಮಾಡಿ",
  "authority.detail.source": "ಮೂಲ",
  "authority.detail.derivedSource": "ORCA ನಿರ್ಣಾಯಕ ನಿಯಮ",
  "authority.geofence.clear": "ಯಾವುದೇ ಪ್ರಸ್ತುತ ಉಲ್ಲಂಘನೆ ಇಲ್ಲ",
  "authority.geofence.inside": "ನಿರ್ಬಂಧಿತ ಪ್ರದೇಶದ ಒಳಗೆ",
  "authority.geofence.unavailable": "ಲಭ್ಯವಿಲ್ಲ",
  "authority.attentionCategory.official_warning": "ಅಧಿಕೃತ ಎಚ್ಚರಿಕೆ",
  "authority.attentionCategory.extreme": "ತೀವ್ರ ಅಪಾಯ",
  "authority.attentionCategory.high": "ಹೆಚ್ಚಿನ ಅಪಾಯ",
  "authority.attentionCategory.blocked": "ನಿರ್ಬಂಧಿಸಲಾಗಿದೆ",
  "authority.attentionCategory.geofence": "ಜಿಯೋಫೆನ್ಸ್",
  "authority.attentionCategory.data_quality": "ಡೇಟಾ ಗುಣಮಟ್ಟ",
  "authority.attentionCategory.unavailable": "ಲಭ್ಯವಿಲ್ಲ",
};

export const STRINGS: Record<LanguageCode, Table> = { en, hi, kn };

// Localised labels for backend enum values (used consistently across panels).
export const DECISION_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: {
    PROCEED: "PROCEED",
    PROCEED_WITH_CAUTION: "CAUTION",
    DO_NOT_PROCEED: "DO NOT PROCEED",
    NO_SAFE_RECOMMENDATION: "NO SAFE RECOMMENDATION",
  },
  hi: {
    PROCEED: "आगे बढ़ें",
    PROCEED_WITH_CAUTION: "सावधानी",
    DO_NOT_PROCEED: "आगे न बढ़ें",
    NO_SAFE_RECOMMENDATION: "कोई सुरक्षित अनुशंसा नहीं",
  },
  kn: {
    PROCEED: "ಮುಂದುವರಿಯಿರಿ",
    PROCEED_WITH_CAUTION: "ಎಚ್ಚರಿಕೆ",
    DO_NOT_PROCEED: "ಮುಂದುವರಿಯಬೇಡಿ",
    NO_SAFE_RECOMMENDATION: "ಸುರಕ್ಷಿತ ಶಿಫಾರಸು ಇಲ್ಲ",
  },
};

export const RISK_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: { low: "LOW", moderate: "MODERATE", high: "HIGH", severe: "SEVERE" },
  hi: { low: "कम", moderate: "मध्यम", high: "अधिक", severe: "गंभीर" },
  kn: { low: "ಕಡಿಮೆ", moderate: "ಮಧ್ಯಮ", high: "ಹೆಚ್ಚು", severe: "ತೀವ್ರ" },
};

export const SUITABILITY_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: {
    unknown: "UNKNOWN",
    poor: "POOR",
    marginal: "MARGINAL",
    moderate: "MODERATE",
    good: "GOOD",
  },
  hi: {
    unknown: "अज्ञात",
    poor: "खराब",
    marginal: "सीमांत",
    moderate: "मध्यम",
    good: "अच्छी",
  },
  kn: {
    unknown: "ಅಜ್ಞಾತ",
    poor: "ಕಳಪೆ",
    marginal: "ಅಂಚಿನ",
    moderate: "ಮಧ್ಯಮ",
    good: "ಉತ್ತಮ",
  },
};

export const TIER_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: {
    LIVE: "LIVE",
    CACHE: "CACHED",
    REFERENCE: "REFERENCE",
    DEMO: "DEMO",
    MISSING: "MISSING",
  },
  hi: {
    LIVE: "लाइव",
    CACHE: "कैश",
    REFERENCE: "संदर्भ",
    DEMO: "डेमो",
    MISSING: "अनुपलब्ध",
  },
  kn: {
    LIVE: "ನೈಜ",
    CACHE: "ಕ್ಯಾಶ್",
    REFERENCE: "ಉಲ್ಲೇಖ",
    DEMO: "ಡೆಮೊ",
    MISSING: "ಇಲ್ಲ",
  },
};

// Phase 9 Step 3 - descriptive chlorophyll-a trophic-magnitude bands. These are
// NOT fish-abundance / catch thresholds.
export const CHL_CLASS_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: {
    oligotrophic: "very low (oligotrophic)",
    low: "low",
    moderate: "moderate",
    elevated: "elevated",
    high: "very high",
  },
  hi: {
    oligotrophic: "बहुत कम (अल्पपोषी)",
    low: "कम",
    moderate: "मध्यम",
    elevated: "बढ़ा हुआ",
    high: "बहुत अधिक",
  },
  kn: {
    oligotrophic: "ಬಹಳ ಕಡಿಮೆ (ಒಲಿಗೊಟ್ರೋಫಿಕ್)",
    low: "ಕಡಿಮೆ",
    moderate: "ಮಧ್ಯಮ",
    elevated: "ಹೆಚ್ಚಿನ",
    high: "ಬಹಳ ಹೆಚ್ಚು",
  },
};

export const PRODUCTIVITY_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: { unknown: "UNKNOWN", low: "LOW", moderate: "MODERATE", elevated: "ELEVATED" },
  hi: { unknown: "अज्ञात", low: "कम", moderate: "मध्यम", elevated: "बढ़ा हुआ" },
  kn: { unknown: "ಅಜ್ಞಾತ", low: "ಕಡಿಮೆ", moderate: "ಮಧ್ಯಮ", elevated: "ಹೆಚ್ಚಿನ" },
};

// Milestone 5 - the Authority dashboard's operational display buckets (see
// backend app.authority.aggregation.operational_status). These group the
// existing risk/safety/decision fields for display only - never a new scale.
export const STATUS_LABEL: Record<LanguageCode, Record<string, string>> = {
  en: {
    SAFE: "SAFE",
    CAUTION: "CAUTION",
    HIGH: "HIGH",
    EXTREME: "EXTREME",
    NO_SAFE_RECOMMENDATION: "NO SAFE RECOMMENDATION",
    BLOCKED: "BLOCKED",
    UNAVAILABLE: "UNAVAILABLE",
  },
  hi: {
    SAFE: "सुरक्षित",
    CAUTION: "सावधानी",
    HIGH: "उच्च जोखिम",
    EXTREME: "अत्यधिक जोखिम",
    NO_SAFE_RECOMMENDATION: "कोई सुरक्षित अनुशंसा नहीं",
    BLOCKED: "अवरुद्ध",
    UNAVAILABLE: "अनुपलब्ध",
  },
  kn: {
    SAFE: "ಸುರಕ್ಷಿತ",
    CAUTION: "ಎಚ್ಚರಿಕೆ",
    HIGH: "ಹೆಚ್ಚಿನ ಅಪಾಯ",
    EXTREME: "ತೀವ್ರ ಅಪಾಯ",
    NO_SAFE_RECOMMENDATION: "ಸುರಕ್ಷಿತ ಶಿಫಾರಸು ಇಲ್ಲ",
    BLOCKED: "ನಿರ್ಬಂಧಿಸಲಾಗಿದೆ",
    UNAVAILABLE: "ಲಭ್ಯವಿಲ್ಲ",
  },
};
