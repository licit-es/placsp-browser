-- DocumentReference -- all documents, unified

CREATE TABLE IF NOT EXISTS document_reference (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES contract_folder_status ON DELETE CASCADE,
  publication_status_id       uuid REFERENCES publication_status ON DELETE CASCADE,
  source_type                 text NOT NULL,
  filename                    text,
  uri                         text,
  document_hash               text,
  document_type_code          text,
  UNIQUE (contract_folder_status_id, source_type, uri)
);

CREATE INDEX IF NOT EXISTS idx_dr_cfs_id ON document_reference (contract_folder_status_id);
CREATE INDEX IF NOT EXISTS idx_dr_ps_id ON document_reference (publication_status_id);
