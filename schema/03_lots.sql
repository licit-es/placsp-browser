-- ProcurementProjectLot -- lots

CREATE TABLE IF NOT EXISTS "ProcurementProjectLot" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  lot_number                  text NOT NULL,
  name                        text,
  total_amount                decimal,
  tax_exclusive_amount        decimal,
  currency_id                 text,
  nuts_code                   text,
  country_subentity           text,
  UNIQUE (contract_folder_status_id, lot_number)
);

CREATE INDEX IF NOT EXISTS idx_ppl_cfs_id ON "ProcurementProjectLot" (contract_folder_status_id);

-- CpvClassification -- CPV codes (1:N from folder or lot)

CREATE TABLE IF NOT EXISTS "CpvClassification" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  lot_id                      uuid REFERENCES "ProcurementProjectLot" ON DELETE CASCADE,
  item_classification_code    text NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cpv_cfs_id ON "CpvClassification" (contract_folder_status_id);
CREATE INDEX IF NOT EXISTS idx_cpv_lot_id ON "CpvClassification" (lot_id);

-- RealizedLocation -- locations (1:N from lot)

CREATE TABLE IF NOT EXISTS "RealizedLocation" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lot_id                      uuid NOT NULL REFERENCES "ProcurementProjectLot" ON DELETE CASCADE,
  nuts_code                   text,
  country_subentity           text,
  country_code                text,
  city_name                   text,
  postal_zone                 text,
  street_name                 text
);

CREATE INDEX IF NOT EXISTS idx_rl_lot_id ON "RealizedLocation" (lot_id);
