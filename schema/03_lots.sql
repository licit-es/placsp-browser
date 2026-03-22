-- ProcurementProjectLot -- lots

CREATE TABLE IF NOT EXISTS procurement_project_lot (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES contract_folder_status ON DELETE CASCADE,
  lot_number                  text NOT NULL,
  name                        text,
  total_amount                decimal,
  tax_exclusive_amount        decimal,
  currency_id                 text,
  nuts_code                   text,
  country_subentity           text,
  UNIQUE (contract_folder_status_id, lot_number)
);

CREATE INDEX IF NOT EXISTS idx_ppl_cfs_id ON procurement_project_lot (contract_folder_status_id);

-- CpvClassification -- CPV codes (1:N from folder or lot)

CREATE TABLE IF NOT EXISTS cpv_classification (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES contract_folder_status ON DELETE CASCADE,
  lot_id                      uuid REFERENCES procurement_project_lot ON DELETE CASCADE,
  item_classification_code    text NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cpv_cfs_id ON cpv_classification (contract_folder_status_id);
CREATE INDEX IF NOT EXISTS idx_cpv_lot_id ON cpv_classification (lot_id);

-- RealizedLocation -- locations (1:N from lot)

CREATE TABLE IF NOT EXISTS realized_location (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lot_id                      uuid NOT NULL REFERENCES procurement_project_lot ON DELETE CASCADE,
  nuts_code                   text,
  country_subentity           text,
  country_code                text,
  city_name                   text,
  postal_zone                 text,
  street_name                 text
);

CREATE INDEX IF NOT EXISTS idx_rl_lot_id ON realized_location (lot_id);
