-- ContractModification -- amendments

CREATE TABLE IF NOT EXISTS contract_modification (
  id                              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id       uuid NOT NULL REFERENCES contract_folder_status ON DELETE CASCADE,
  modification_number             text,
  contract_id                     text,
  note                            text,
  modification_duration_measure   integer,
  modification_duration_unit_code text,
  final_duration_measure          integer,
  final_duration_unit_code        text,
  modification_tax_exclusive_amount decimal,
  final_tax_exclusive_amount      decimal,
  currency_id                     text
);

CREATE INDEX IF NOT EXISTS idx_cm_cfs_id ON contract_modification (contract_folder_status_id);

-- StatusChange -- folder status timeline (append-only)

CREATE TABLE IF NOT EXISTS status_change (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES contract_folder_status ON DELETE CASCADE,
  status_code                 text NOT NULL,
  updated                     timestamptz NOT NULL,
  recorded_at                 timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sc_cfs_id ON status_change (contract_folder_status_id);
