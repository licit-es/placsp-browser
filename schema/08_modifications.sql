-- ContractModification -- amendments

CREATE TABLE IF NOT EXISTS "ContractModification" (
  id                              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id       uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_cm_cfs_id ON "ContractModification" (contract_folder_status_id);

-- StatusChange -- folder status timeline (append-only)

CREATE TABLE IF NOT EXISTS "StatusChange" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  status_code                 text NOT NULL,
  updated                     timestamptz NOT NULL,
  recorded_at                 timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sc_cfs_id ON "StatusChange" (contract_folder_status_id);
