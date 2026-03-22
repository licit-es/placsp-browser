-- DocumentReference -- all documents, unified

CREATE TABLE IF NOT EXISTS "DocumentReference" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  publication_status_id       uuid REFERENCES "PublicationStatus" ON DELETE CASCADE,
  source_type                 text NOT NULL,
  filename                    text,
  uri                         text,
  document_hash               text,
  document_type_code          text,
  UNIQUE (contract_folder_status_id, source_type, uri)
);

CREATE INDEX IF NOT EXISTS idx_dr_cfs_id ON "DocumentReference" (contract_folder_status_id);
CREATE INDEX IF NOT EXISTS idx_dr_ps_id ON "DocumentReference" (publication_status_id);
