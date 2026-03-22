#!/bin/bash
set -euo pipefail

# Apply all schema files in order via psql.
# Usage: ./schema/apply.sh [DATABASE_URL]
# Falls back to DATABASE_URL env var if no argument given.

DB_URL="${1:-${DATABASE_URL:-}}"

if [ -z "$DB_URL" ]; then
  echo "Usage: ./schema/apply.sh <DATABASE_URL>"
  echo "  or set DATABASE_URL environment variable"
  exit 1
fi

SCHEMA_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Applying schema from $SCHEMA_DIR ..."

cat \
  "$SCHEMA_DIR"/00_functions.sql \
  "$SCHEMA_DIR"/01_contracting_party.sql \
  "$SCHEMA_DIR"/02_contract_folder_status.sql \
  "$SCHEMA_DIR"/03_lots.sql \
  "$SCHEMA_DIR"/04_results.sql \
  "$SCHEMA_DIR"/05_terms.sql \
  "$SCHEMA_DIR"/06_notices.sql \
  "$SCHEMA_DIR"/07_documents.sql \
  "$SCHEMA_DIR"/08_modifications.sql \
  "$SCHEMA_DIR"/09_etl.sql \
  "$SCHEMA_DIR"/10_catalog.sql \
  "$SCHEMA_DIR"/11_api.sql \
| psql "$DB_URL" --single-transaction --set ON_ERROR_STOP=on

echo "Schema applied."

# Seed catalog reference data (idempotent, ON CONFLICT DO UPDATE)
if [ -f "$SCHEMA_DIR/seed.sql" ]; then
  echo "Seeding catalogs ..."
  psql "$DB_URL" -f "$SCHEMA_DIR/seed.sql" --set ON_ERROR_STOP=on
  echo "Catalogs seeded."
fi

# Create read-only API user (idempotent)
API_PASS="${API_PASSWORD:-licit_readonly}"
psql "$DB_URL" --set ON_ERROR_STOP=on <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'licit_api') THEN
    CREATE ROLE licit_api LOGIN PASSWORD '${API_PASS}';
  END IF;
END \$\$;
GRANT CONNECT ON DATABASE licit TO licit_api;
GRANT USAGE ON SCHEMA public TO licit_api;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO licit_api;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO licit_api;
SQL
echo "API user ready."

echo "Done."
