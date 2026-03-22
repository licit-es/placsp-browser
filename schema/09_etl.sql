-- EtlSyncState -- pagination tracking

CREATE TABLE IF NOT EXISTS "EtlSyncState" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  feed_type                   text NOT NULL,
  year                        integer NOT NULL DEFAULT 0,
  page_url                    text NOT NULL,
  status                      text NOT NULL,
  entry_count                 integer,
  error_count                 integer,
  processed_at                timestamptz,
  UNIQUE (feed_type, year, page_url)
);

-- EtlFailedEntries -- entries that failed processing

CREATE TABLE IF NOT EXISTS "EtlFailedEntries" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  feed_type                   text NOT NULL,
  entry_id                    text NOT NULL,
  entry_updated               timestamptz,
  page_url                    text,
  error_type                  text NOT NULL,
  error_message               text NOT NULL,
  first_failed_at             timestamptz NOT NULL DEFAULT now(),
  last_failed_at              timestamptz NOT NULL DEFAULT now(),
  retry_count                 integer NOT NULL DEFAULT 1,
  resolved_at                 timestamptz
);

-- Partial unique: only one open failure per entry per feed
CREATE UNIQUE INDEX IF NOT EXISTS uix_failed_entry_open
  ON "EtlFailedEntries" (feed_type, entry_id) WHERE resolved_at IS NULL;
