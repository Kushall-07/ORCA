import { useCallback, useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { ApiError, fetchAuthorityOverview } from "../services/apiClient";
import { AuthorityMap } from "../maps/AuthorityMap";
import { DataTierBadge, Disclaimer, EmptyNote, SeverityBadge, Spinner } from "../components/common";
import type { AssessmentSection } from "../components/nav/navItems";
import type { AttentionItem, AuthorityOverview, LocationOverview } from "../types/authority";
import type { QueryResponse } from "../types/api";
import { AuthorityLocationDetail } from "./AuthorityLocationDetail";

const STATUS_ROWS: { key: keyof AuthorityOverview["status_counts"]; label: string }[] = [
  { key: "safe", label: "SAFE" },
  { key: "caution", label: "CAUTION" },
  { key: "high", label: "HIGH" },
  { key: "extreme", label: "EXTREME" },
  { key: "no_safe_recommendation", label: "NO_SAFE_RECOMMENDATION" },
  { key: "blocked", label: "BLOCKED" },
  { key: "unavailable", label: "UNAVAILABLE" },
];

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

/**
 * Milestone 5 - Authority / Operational Intelligence Dashboard.
 *
 * A presentation/aggregation VIEW over the existing deterministic pipeline
 * (see backend app.authority) - it fetches ONE already-aggregated overview
 * (no client-side risk/decision computation) and never polls: a manual
 * refresh button is the only way to re-fetch.
 */
export function AuthorityDashboard({
  onOpenLocation,
}: {
  /** Hands the selected location's full QueryResponse to the existing
   * workspace (Today/Trip/System/Activity), see WorkspacePage.tsx. */
  onOpenLocation: (detail: QueryResponse, page: AssessmentSection, label: string) => void;
}) {
  const { t, statusLabel, tierLabel } = useI18n();
  const [edition, setEdition] = useState<"live" | "demo">("live");
  const [overview, setOverview] = useState<AuthorityOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    fetchAuthorityOverview(edition, controller.signal)
      .then((result) => {
        setOverview(result);
        setLoading(false);
        setSelectedId((prev) =>
          prev && result.locations.some((l) => l.location_id === prev) ? prev : null,
        );
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : t("authority.error"));
        setLoading(false);
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [edition, refreshTick]);

  const onRefresh = useCallback(() => setRefreshTick((n) => n + 1), []);

  const selected: LocationOverview | null =
    overview?.locations.find((l) => l.location_id === selectedId) ?? null;

  const onOpen = (page: AssessmentSection) => {
    if (selected?.detail) {
      onOpenLocation(selected.detail, page, `Authority: ${selected.name} current conditions`);
    }
  };

  const attentionByCategory = (item: AttentionItem) =>
    t(`authority.attentionCategory.${item.category}` as never);

  return (
    <div className="authority">
      <header className="authority__header">
        <div>
          <h2 className="authority__title">{t("authority.title")}</h2>
          <p className="authority__subtitle">{t("authority.subtitle")}</p>
        </div>
        <div className="authority__header-actions">
          <div className="authority__edition" role="group" aria-label={t("authority.dataEdition.live")}>
            <button
              type="button"
              className={`segmented__item ${edition === "live" ? "is-active" : ""}`}
              onClick={() => setEdition("live")}
            >
              {t("authority.edition.live")}
            </button>
            <button
              type="button"
              className={`segmented__item ${edition === "demo" ? "is-active" : ""}`}
              onClick={() => setEdition("demo")}
            >
              {t("authority.edition.demo")}
            </button>
          </div>
          {overview && (
            <span className={`data-edition-badge data-edition-badge--${overview.data_edition.toLowerCase()}`}>
              {overview.data_edition === "DEMO" ? t("authority.dataEdition.demo") : t("authority.dataEdition.live")}
            </span>
          )}
          {overview && (
            <span className="authority__updated">
              {t("authority.updated", { time: formatTime(overview.generated_at) })}
            </span>
          )}
          <button type="button" className="btn btn--ghost btn--small" onClick={onRefresh} disabled={loading}>
            {t("authority.refresh")}
          </button>
        </div>
      </header>

      {overview?.data_edition === "DEMO" && (
        <Disclaimer>{t("authority.demoFixtureNotice")}</Disclaimer>
      )}

      {loading && !overview && <Spinner label={t("authority.loading")} />}

      {error && !loading && (
        <div className="authority__error">
          <p>{error}</p>
          <button type="button" className="btn btn--small" onClick={onRefresh}>
            {t("authority.retry")}
          </button>
        </div>
      )}

      {overview && overview.location_count === 0 && (
        <EmptyNote>
          <strong>{t("authority.noLocations")}</strong>
          <br />
          {t("authority.noLocationsHint")}
        </EmptyNote>
      )}

      {overview && overview.location_count > 0 && (
        <>
          <section className="authority__stats" aria-label={t("authority.statusDistribution")}>
            <div className="authority-stat authority-stat--primary">
              <span className="authority-stat__value">{overview.location_count}</span>
              <span className="authority-stat__label">{t("authority.locationsMonitored")}</span>
            </div>
            <div className="authority-stat authority-stat--primary">
              <span className="authority-stat__value">
                {overview.attention.filter((a) => a.category === "official_warning").length}
              </span>
              <span className="authority-stat__label">{t("authority.activeWarnings")}</span>
            </div>
            {STATUS_ROWS.filter((row) => overview.status_counts[row.key] > 0).map((row) => (
              <div className="authority-stat" key={row.key}>
                <span className="authority-stat__value">{overview.status_counts[row.key]}</span>
                <span className="authority-stat__label">
                  <SeverityBadge severity={row.label} label={statusLabel(row.label)} />
                </span>
              </div>
            ))}
          </section>

          <div className="authority__grid">
            <section className="authority__map-card" aria-label={t("authority.map")}>
              <h3 className="rail__group-label">{t("authority.map")}</h3>
              <div className="authority-map-frame">
                <AuthorityMap
                  locations={overview.locations}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                />
              </div>
              <ul className="authority-map-legend" aria-label={t("authority.mapLegend")}>
                {(["SAFE", "CAUTION", "HIGH", "EXTREME", "NO_SAFE_RECOMMENDATION", "BLOCKED"] as const).map(
                  (s) => (
                    <li key={s}>
                      <SeverityBadge severity={s} label={statusLabel(s)} />
                    </li>
                  ),
                )}
              </ul>
            </section>

            <section className="authority__attention" aria-label={t("authority.attentionRequired")}>
              <h3 className="rail__group-label">{t("authority.attentionRequired")}</h3>
              {overview.attention.length === 0 ? (
                <EmptyNote>{t("authority.noAttention")}</EmptyNote>
              ) : (
                <ul className="authority-attention-list">
                  {overview.attention.map((item, i) => (
                    <li key={`${item.location_id}-${item.category}-${i}`}>
                      <button
                        type="button"
                        className="authority-attention-item"
                        onClick={() => setSelectedId(item.location_id)}
                      >
                        <SeverityBadge severity={item.status} label={attentionByCategory(item)} />
                        <span className="authority-attention-item__name">{item.name}</span>
                        <span className="authority-attention-item__reason">{item.reason}</span>
                        <span className="authority-attention-item__source">
                          {t("authority.detail.source")}: {item.source}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="authority__locations" aria-label={t("authority.locations")}>
            <h3 className="rail__group-label">{t("authority.locations")}</h3>
            <div className="authority-table-wrap">
              <table className="authority-table">
                <thead>
                  <tr>
                    <th>{t("authority.locationsTable.location")}</th>
                    <th>{t("authority.locationsTable.status")}</th>
                    <th>{t("authority.locationsTable.warning")}</th>
                    <th>{t("authority.locationsTable.data")}</th>
                    <th>{t("authority.locationsTable.updated")}</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.locations.map((loc) => (
                    <tr
                      key={loc.location_id}
                      className={loc.location_id === selectedId ? "is-selected" : ""}
                      onClick={() => setSelectedId(loc.location_id)}
                    >
                      <td>{loc.name}</td>
                      <td>
                        <SeverityBadge severity={loc.status} label={statusLabel(loc.status)} />
                      </td>
                      <td>{loc.warnings.length > 0 ? loc.warnings.join("; ") : t("common.na")}</td>
                      <td>
                        {loc.weather_tier ? (
                          <DataTierBadge tier={loc.weather_tier} label={tierLabel(loc.weather_tier)} />
                        ) : (
                          t("common.na")
                        )}
                      </td>
                      <td>{formatTime(overview.generated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="authority__detail" aria-live="polite">
            {selected ? (
              <AuthorityLocationDetail
                location={selected}
                dataEdition={overview.data_edition}
                onOpen={onOpen}
              />
            ) : (
              <EmptyNote>{t("authority.selectLocation")}</EmptyNote>
            )}
          </section>

          <section className="authority__data-health" aria-label={t("authority.dataHealth")}>
            <h3 className="rail__group-label">{t("authority.dataHealth")}</h3>
            <dl className="kv-list">
              <div className="kv">
                <dt className="kv__k">{t("authority.dataHealth.weather")}</dt>
                <dd className="kv__v">
                  {overview.locations.filter((l) => l.weather_tier === "LIVE").length}/
                  {overview.location_count} {tierLabel("LIVE")}
                </dd>
              </div>
              <div className="kv">
                <dt className="kv__k">{t("authority.dataHealth.marine")}</dt>
                <dd className="kv__v">
                  {overview.locations.filter((l) => l.ocean_tier === "LIVE").length}/
                  {overview.location_count} {tierLabel("LIVE")}
                </dd>
              </div>
              <div className="kv">
                <dt className="kv__k">{t("authority.activeWarnings")}</dt>
                <dd className="kv__v">
                  {overview.attention.filter((a) => a.category === "official_warning").length}
                </dd>
              </div>
            </dl>
          </section>
        </>
      )}
    </div>
  );
}
