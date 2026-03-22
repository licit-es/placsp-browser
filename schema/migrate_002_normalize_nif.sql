-- Normalize winning_party.identifier (NIF/CIF):
--   1. Uppercase + strip hyphens for valid single NIFs
--   2. Fix swapped identifier/name fields
--   3. Null out garbage values (-, TEMP-*, empty)

BEGIN;

-- Step 1: Null out garbage identifiers
UPDATE winning_party
SET identifier = NULL
WHERE identifier IN ('-', '')
   OR identifier LIKE 'TEMP-%';

-- Step 2: Fix swapped name/identifier
-- Pattern: identifier looks like a company name, name looks like a NIF
UPDATE winning_party
SET identifier = UPPER(REPLACE(REPLACE(name, '-', ''), ' ', '')),
    name = identifier
WHERE identifier IS NOT NULL
  AND name IS NOT NULL
  AND identifier !~ '^[A-Za-z]\d{7,8}[A-Za-z0-9]?$'
  AND identifier !~ '^\d{8}[A-Za-z]$'
  AND UPPER(REPLACE(REPLACE(name, '-', ''), ' ', ''))
      ~ '^[A-Z]\d{7,8}[A-Z0-9]?$|^\d{8}[A-Z]$';

-- Step 3: Normalize valid NIFs (uppercase, strip hyphens)
UPDATE winning_party
SET identifier = UPPER(REPLACE(REPLACE(identifier, '-', ''), ' ', ''))
WHERE identifier IS NOT NULL
  AND UPPER(REPLACE(REPLACE(identifier, '-', ''), ' ', ''))
      ~ '^[A-Z]\d{7,8}[A-Z0-9]?$|^\d{8}[A-Z]$'
  AND identifier IS DISTINCT FROM
      UPPER(REPLACE(REPLACE(identifier, '-', ''), ' ', ''));

-- Step 4: Uppercase remaining identifiers (UTEs etc.)
UPDATE winning_party
SET identifier = UPPER(TRIM(identifier))
WHERE identifier IS NOT NULL
  AND identifier IS DISTINCT FROM UPPER(TRIM(identifier));

COMMIT;
