-- ============================================================
-- ORCA - Supabase schema
-- Run this once in your Supabase project's SQL editor (or via `supabase db
-- push` if you use the CLI). Idempotent - safe to re-run.
-- ============================================================
--
-- The ONLY table ORCA keeps in Supabase: a small app-side profile row keyed
-- by the Clerk user id (see backend/app/auth/profiles.py). Clerk remains the
-- sole source of truth for identity, password and session state - this
-- table exists so the backend has somewhere to attach app-specific fields to
-- a user later. ORCA's own self-hosted Postgres/PostGIS (GIS layers,
-- sessions, etc.) is a completely separate database and is untouched by
-- this - see docker/postgis/init.sql.

create table if not exists public.profiles (
    clerk_user_id text primary key,
    email         text not null,
    created_at    timestamptz not null default now()
);

comment on table public.profiles is
    'App-side profile keyed by Clerk user id. Clerk owns identity/auth; this is the only user-related table ORCA keeps in Supabase.';

-- This table is only ever read/written by the backend using the Supabase
-- service_role key (which bypasses RLS), never by the frontend directly - so
-- RLS stays enabled with no permissive policies, the secure default.
alter table public.profiles enable row level security;
