-- ============================================================
-- ORCA - PostGIS initialisation
-- ============================================================
-- Executed once, on first startup of the postgres container
-- (mounted into /docker-entrypoint-initdb.d/). Idempotent so it is safe to
-- re-run manually. Real geometry is loaded later by scripts/ - Phase 1 only
-- establishes the extension and an empty, migration-friendly schema.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS gis;
COMMENT ON SCHEMA gis IS
    'Static marine GIS layers (coastline, EEZ, geofences, protected areas, bathymetry). Populated in later phases.';

-- Provenance marker carried by every layer so authoritative data can always be
-- distinguished from reference snapshots and illustrative/demo geometry.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'layer_authority') THEN
        CREATE TYPE gis.layer_authority AS ENUM ('authoritative', 'reference', 'demo');
    END IF;
END
$$;

-- ---- Placeholder layers (no rows in Phase 1) ----

CREATE TABLE IF NOT EXISTS gis.coastline (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       text,
    authority  gis.layer_authority NOT NULL DEFAULT 'demo',
    source     text,
    loaded_at  timestamptz NOT NULL DEFAULT now(),
    geom       geometry(MultiLineString, 4326)
);

CREATE TABLE IF NOT EXISTS gis.eez (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       text,
    sovereign  text,
    authority  gis.layer_authority NOT NULL DEFAULT 'demo',
    source     text,
    loaded_at  timestamptz NOT NULL DEFAULT now(),
    geom       geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS gis.geofence (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        text NOT NULL,
    kind        text NOT NULL DEFAULT 'restricted',   -- restricted | exclusion | advisory
    hard_block  boolean NOT NULL DEFAULT true,        -- true => absolute routing blocker
    authority   gis.layer_authority NOT NULL DEFAULT 'demo',
    source      text,
    loaded_at   timestamptz NOT NULL DEFAULT now(),
    geom        geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS gis.protected_area (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       text,
    wdpa_id    text,
    authority  gis.layer_authority NOT NULL DEFAULT 'reference',
    source     text,
    loaded_at  timestamptz NOT NULL DEFAULT now(),
    geom       geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS gis.bathymetry (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    depth_m    double precision,
    authority  gis.layer_authority NOT NULL DEFAULT 'demo',
    source     text,
    loaded_at  timestamptz NOT NULL DEFAULT now(),
    geom       geometry(Polygon, 4326)
);

-- Spatial indexes up front so later bulk loads do not need a migration.
CREATE INDEX IF NOT EXISTS coastline_geom_gix      ON gis.coastline      USING GIST (geom);
CREATE INDEX IF NOT EXISTS eez_geom_gix            ON gis.eez            USING GIST (geom);
CREATE INDEX IF NOT EXISTS geofence_geom_gix       ON gis.geofence       USING GIST (geom);
CREATE INDEX IF NOT EXISTS protected_area_geom_gix ON gis.protected_area USING GIST (geom);
CREATE INDEX IF NOT EXISTS bathymetry_geom_gix     ON gis.bathymetry     USING GIST (geom);
