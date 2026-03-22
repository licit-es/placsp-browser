-- TenderResult -- results

CREATE TABLE IF NOT EXISTS "TenderResult" (
  id                                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id         uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  lot_id                            uuid REFERENCES "ProcurementProjectLot" ON DELETE CASCADE,
  result_code                       text,
  description                       text,
  award_date                        date,
  received_tender_quantity          integer,
  lower_tender_amount               decimal,
  higher_tender_amount              decimal,
  sme_awarded_indicator             boolean,
  abnormally_low_tenders_indicator  boolean,
  start_date                        date,
  smes_received_tender_quantity     integer,
  eu_nationals_received_quantity    integer,
  non_eu_nationals_received_qty     integer,
  awarded_owner_nationality_code    text,
  subcontract_rate                  decimal,
  subcontract_description           text,
  -- AwardedTenderedProject (inlined, 1:1)
  awarded_tax_exclusive_amount      decimal,
  awarded_payable_amount            decimal,
  awarded_currency_id               text,
  awarded_lot_number                text
);

CREATE INDEX IF NOT EXISTS idx_tr_cfs_id ON "TenderResult" (contract_folder_status_id);
CREATE INDEX IF NOT EXISTS idx_tr_lot_id ON "TenderResult" (lot_id);

-- WinningParty -- adjudicatarios (1:N per tender_result)

CREATE TABLE IF NOT EXISTS "WinningParty" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tender_result_id            uuid NOT NULL REFERENCES "TenderResult" ON DELETE CASCADE,
  identifier                  text,
  identifier_scheme           text,
  name                        text NOT NULL,
  nuts_code                   text,
  city_name                   text,
  postal_zone                 text,
  country_code                text,
  company_type_code           text
);

CREATE INDEX IF NOT EXISTS idx_wp_tr_id ON "WinningParty" (tender_result_id);

-- Contract -- formalized contracts (1:0..1 per tender_result)

CREATE TABLE IF NOT EXISTS "Contract" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tender_result_id            uuid NOT NULL UNIQUE REFERENCES "TenderResult" ON DELETE CASCADE,
  contract_number             text,
  issue_date                  date
);
