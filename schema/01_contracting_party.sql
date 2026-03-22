-- ContractingParty -- organizations

CREATE TABLE IF NOT EXISTS "ContractingParty" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name                        text NOT NULL,
  dir3                        text,
  nif                         text,
  platform_id                 text,
  website_uri                 text,
  contracting_party_type_code text,
  activity_code               text,
  buyer_profile_uri           text,
  contact_name                text,
  contact_telephone           text,
  contact_telefax             text,
  contact_email               text,
  city_name                   text,
  postal_zone                 text,
  address_line                text,
  country_code                text,
  agent_party_id              text,
  agent_party_name            text,
  parent_hierarchy            jsonb
);

-- Partial unique indexes for identity resolution
CREATE UNIQUE INDEX IF NOT EXISTS uix_contracting_party_dir3
  ON "ContractingParty" (dir3) WHERE dir3 IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uix_contracting_party_platform_id
  ON "ContractingParty" (platform_id) WHERE platform_id IS NOT NULL;
