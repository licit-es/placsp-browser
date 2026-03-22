-- ValidNoticeInfo -- publication notices

CREATE TABLE IF NOT EXISTS "ValidNoticeInfo" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_folder_status_id   uuid NOT NULL REFERENCES "ContractFolderStatus" ON DELETE CASCADE,
  notice_type_code            text,
  notice_issue_date           date
);

CREATE INDEX IF NOT EXISTS idx_vni_cfs_id ON "ValidNoticeInfo" (contract_folder_status_id);

-- PublicationStatus -- media publications (1:N per notice)

CREATE TABLE IF NOT EXISTS "PublicationStatus" (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  valid_notice_info_id        uuid NOT NULL REFERENCES "ValidNoticeInfo" ON DELETE CASCADE,
  publication_media_name      text
);

CREATE INDEX IF NOT EXISTS idx_ps_vni_id ON "PublicationStatus" (valid_notice_info_id);
