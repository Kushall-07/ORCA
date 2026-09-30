"""Authentication: verifying Clerk-issued session tokens and resolving them
to an app-side Supabase profile.

Clerk (not this backend) owns signup, login, password and session issuance -
the frontend (`@clerk/clerk-react`) talks to Clerk directly and this backend
never sees a password. This package only verifies a session token Clerk
already issued (see `dependencies.get_current_user`) and looks up/creates the
matching profile row in Supabase (see `profiles.py`) - the one small table
ORCA keeps there. This gates *who may use* ORCA - it is never a source of
safety-critical numbers and sits outside the agent/deterministic-core
pipeline described in docs/architecture.md.
"""
