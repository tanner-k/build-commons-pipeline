# supabase/

SQL migrations, applied manually via Supabase SQL editor or `supabase db push`. Tables: videos (pipeline state machine), analytics, taste_library, templates (spec §5). The `videos.status` CHECK constraint is the single definition of valid statuses.
