-- 0002_enhancement.sql — raw-video enhancement track (manual track on-ramp).
-- Adds the enhance discriminator + front-half statuses; back half is shared.
-- Apply via Supabase SQL editor or `supabase db push` AFTER 0001_init.sql.

alter table videos
    add column if not exists kind text not null default 'generated'
        check (kind in ('generated', 'enhanced')),
    add column if not exists source_video_url text,   -- uploaded raw footage
    add column if not exists transcript jsonb,         -- [{"text","start_s","end_s"}, ...]
    add column if not exists enhancement_json jsonb;   -- the EnhancementPlan

-- Extend the status machine with the enhance front-half states. Postgres has no
-- "alter check constraint", so drop and recreate. Existing rows keep their status.
alter table videos drop constraint if exists videos_status_check;
alter table videos add constraint videos_status_check check (status in (
    'ideation', 'scripted', 'assets_ready', 'rendered',
    'qa_pending', 'approved', 'rejected', 'published',
    'uploaded', 'plan_ready', 'plan_approved'
));

create index if not exists videos_kind_status_idx on videos (kind, status);
