-- ContractFolderStatus -- root entity

CREATE TABLE IF NOT EXISTS contract_folder_status (
  -- ATOM envelope
  entry_id                          text NOT NULL UNIQUE,
  title                             text,
  summary                           text,
  link                              text,
  updated                           timestamptz NOT NULL,
  feed_type                         text NOT NULL,

  -- ContractFolderStatus
  contract_folder_id                text,
  status_code                       text NOT NULL,
  contracting_party_id              uuid REFERENCES contracting_party,

  -- ProcurementProject (inlined, 1:1)
  name                              text,
  type_code                         text,
  sub_type_code                     text,
  estimated_overall_contract_amount decimal,
  total_amount                      decimal,
  tax_exclusive_amount              decimal,
  currency_id                       text,
  nuts_code                         text,
  country_subentity                 text,
  duration_measure                  integer,
  duration_unit_code                text,
  planned_start_date                date,
  planned_end_date                  date,
  option_validity_description       text,
  options_description               text,
  mix_contract_indicator            boolean,

  -- TenderingProcess (inlined, 1:1)
  procedure_code                    text,
  urgency_code                      text,
  submission_method_code            text,
  submission_deadline_date          date,
  submission_deadline_time          time,
  submission_deadline_description   text,
  document_availability_end_date    date,
  document_availability_end_time    time,
  contracting_system_code           text,
  part_presentation_code            text,
  auction_constraint_indicator      boolean,
  max_lot_presentation_quantity     integer,
  max_tenderer_awarded_lots_qty     integer,
  lots_combination_rights           text,
  over_threshold_indicator          boolean,
  participation_request_end_date    date,
  participation_request_end_time    time,
  short_list_limitation_description text,
  short_list_min_quantity           integer,
  short_list_expected_quantity      integer,
  short_list_max_quantity           integer,

  -- TenderingTerms scalar fields (inlined, 1:1)
  required_curricula_indicator      boolean,
  procurement_legislation_id        text,
  variant_constraint_indicator      boolean,
  price_revision_formula            text,
  funding_program_code              text,
  funding_program_name              text,
  funding_program_description       text,
  received_appeal_quantity          integer,
  tender_recipient_endpoint_id      text,
  allowed_subcontract_rate          decimal,
  allowed_subcontract_description   text,
  national_legislation_code         text,

  -- Infrastructure
  ted_uuid                          text,
  id                                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at                        timestamptz DEFAULT now()
);

DO $$ BEGIN
  CREATE TRIGGER guard_updated
    BEFORE UPDATE ON contract_folder_status
    FOR EACH ROW EXECUTE FUNCTION reject_unless_newer();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_cfs_contract_folder_id ON contract_folder_status (contract_folder_id);
CREATE INDEX IF NOT EXISTS idx_cfs_status_code ON contract_folder_status (status_code);
CREATE INDEX IF NOT EXISTS idx_cfs_contracting_party_id ON contract_folder_status (contracting_party_id);
CREATE INDEX IF NOT EXISTS idx_cfs_updated ON contract_folder_status (updated);
