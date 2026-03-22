-- AwardingCriteria -- evaluation criteria (1:N from folder or lot)

CREATE TABLE IF NOT EXISTS "AwardingCriteria" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  lot_id                      uuid REFERENCES "ProcurementProjectLot" ON DELETE CASCADE,
  criteria_type_code          text,
  criteria_sub_type_code      text,
  description                 text,
  weight_numeric              decimal,
  note                        text
);

CREATE INDEX IF NOT EXISTS idx_ac_cfs_id ON "AwardingCriteria" (contract_folder_status_id);
CREATE INDEX IF NOT EXISTS idx_ac_lot_id ON "AwardingCriteria" (lot_id);

-- FinancialGuarantee -- guarantees (folder-level only)

CREATE TABLE IF NOT EXISTS "FinancialGuarantee" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  guarantee_type_code         text,
  amount_rate                 decimal,
  liability_amount            decimal,
  currency_id                 text
);

CREATE INDEX IF NOT EXISTS idx_fg_cfs_id ON "FinancialGuarantee" (contract_folder_status_id);

-- QualificationRequirement -- tenderer requirements

CREATE TABLE IF NOT EXISTS "QualificationRequirement" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  lot_id                      uuid REFERENCES "ProcurementProjectLot" ON DELETE CASCADE,
  origin_type                 text NOT NULL,
  evaluation_criteria_type_code text,
  description                 text,
  threshold_quantity          decimal,
  personal_situation          text,
  operating_years_quantity    integer,
  employee_quantity           integer
);

CREATE INDEX IF NOT EXISTS idx_qr_cfs_id ON "QualificationRequirement" (contract_folder_status_id);
CREATE INDEX IF NOT EXISTS idx_qr_lot_id ON "QualificationRequirement" (lot_id);

-- BusinessClassification -- classification scheme (folder-level)

CREATE TABLE IF NOT EXISTS "BusinessClassification" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  code_value                  text NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bc_cfs_id ON "BusinessClassification" (contract_folder_status_id);

-- ExecutionCondition -- contract execution requirements (folder-level)

CREATE TABLE IF NOT EXISTS "ExecutionCondition" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  name                        text,
  execution_requirement_code  text,
  description                 text
);

CREATE INDEX IF NOT EXISTS idx_ec_cfs_id ON "ExecutionCondition" (contract_folder_status_id);
