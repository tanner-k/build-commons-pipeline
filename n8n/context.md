# n8n/

Workflow JSON exports — import into self-hosted n8n, then attach credentials in the UI (creds never live in these files). Plumbing only: schedule triggers, HTTP calls, Postgres reads/writes. generate.json = Stage 2 asset fan-out + render trigger; publish.json = Stage 5; analytics.json = Stage 6 ingest.
