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

echo "Schema applied successfully."
