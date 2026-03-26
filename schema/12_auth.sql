-- Authentication, user management, and audit logging

-- ===================================================================
-- API_USER
-- ===================================================================

CREATE TABLE IF NOT EXISTS api_user (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email         text NOT NULL UNIQUE,
  nombre        text NOT NULL,
  password_hash text NOT NULL,
  role          text NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

-- ===================================================================
-- API_KEY
-- ===================================================================

CREATE TABLE IF NOT EXISTS api_key (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid NOT NULL REFERENCES api_user(id) ON DELETE CASCADE,
  key_hash      text NOT NULL UNIQUE,
  key_prefix    text NOT NULL,
  nombre        text NOT NULL DEFAULT 'default',
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  last_used_at  timestamptz,
  expires_at    timestamptz
);

CREATE INDEX IF NOT EXISTS idx_api_key_hash_active
  ON api_key (key_hash) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_api_key_user
  ON api_key (user_id);

-- ===================================================================
-- AUDIT_LOG
-- ===================================================================

CREATE TABLE IF NOT EXISTS audit_log (
  id              bigserial PRIMARY KEY,
  user_id         uuid REFERENCES api_user(id) ON DELETE SET NULL,
  api_key_id      uuid REFERENCES api_key(id) ON DELETE SET NULL,
  method          text NOT NULL,
  path            text NOT NULL,
  status_code     smallint NOT NULL,
  duration_ms     integer NOT NULL,
  ip_address      inet,
  user_agent      text,
  request_params  jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_created
  ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_user
  ON audit_log (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_path
  ON audit_log (path, created_at DESC);
