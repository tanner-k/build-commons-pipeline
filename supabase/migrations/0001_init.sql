-- 0001_init.sql — pipeline state, analytics, taste library, templates (spec §5)
-- Apply via Supabase SQL editor or `supabase db push`.

create extension if not exists "pgcrypto";

create table if not exists videos (
    id uuid primary key default gen_random_uuid(),
    status text not null default 'ideation'
        check (status in (
            'ideation', 'scripted', 'assets_ready', 'rendered',
            'qa_pending', 'approved', 'rejected', 'published'
        )),
    template text
        check (template in ('explainer', 'tutorial', 'listicle', 'comparison')),
    topic text,
    hook text,
    script_json jsonb,
    asset_urls jsonb,
    render_url text,
    platform_ids jsonb,          -- {"youtube": "...", "tiktok": "...", "instagram": "..."}
    qa_notes text,               -- rejection notes feed Stage 2/3 retry
    created_at timestamptz not null default now(),
    published_at timestamptz
);

create index if not exists videos_status_idx on videos (status);

create table if not exists analytics (
    id bigint generated always as identity primary key,
    video_id uuid not null references videos (id) on delete cascade,
    platform text not null
        check (platform in ('youtube', 'tiktok', 'instagram')),
    captured_at timestamptz not null default now(),
    views int,
    avg_view_duration_s double precision,
    retention_curve jsonb,       -- [{"t_s": 0.0, "fraction": 1.0}, ...]
    ctr double precision,
    likes int,
    shares int,
    follows_attributed int
);

create index if not exists analytics_video_idx on analytics (video_id, platform, captured_at);

create table if not exists taste_library (
    id uuid primary key default gen_random_uuid(),
    source_url text,
    niche text,
    transcript text,
    hook_text text,
    hook_type text
        check (hook_type in ('question', 'bold_claim', 'curiosity_gap', 'demo')),
    why_it_works text,
    views bigint,
    added_by text not null default 'manual'
        check (added_by in ('manual', 'analyst_agent')),
    created_at timestamptz not null default now()
);

create table if not exists templates (
    name text primary key,
    version int not null default 1,
    created_at timestamptz not null default now(),
    retired_at timestamptz,
    avg_retention double precision   -- updated by analyst agent
);

insert into templates (name)
values ('explainer'), ('tutorial'), ('listicle'), ('comparison')
on conflict (name) do nothing;
