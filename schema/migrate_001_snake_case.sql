-- Migration 001: Rename PascalCase tables to snake_case
-- Idempotent: uses DO block to check existence before renaming.

DO $$
DECLARE
  renames constant text[][] := ARRAY[
    ['ContractingParty',          'contracting_party'],
    ['ContractFolderStatus',      'contract_folder_status'],
    ['ProcurementProjectLot',     'procurement_project_lot'],
    ['CpvClassification',         'cpv_classification'],
    ['RealizedLocation',          'realized_location'],
    ['TenderResult',              'tender_result'],
    ['WinningParty',              'winning_party'],
    ['Contract',                  'contract'],
    ['AwardingCriteria',          'awarding_criteria'],
    ['FinancialGuarantee',        'financial_guarantee'],
    ['QualificationRequirement',  'qualification_requirement'],
    ['BusinessClassification',    'business_classification'],
    ['ExecutionCondition',        'execution_condition'],
    ['ValidNoticeInfo',           'valid_notice_info'],
    ['PublicationStatus',         'publication_status'],
    ['DocumentReference',         'document_reference'],
    ['ContractModification',      'contract_modification'],
    ['StatusChange',              'status_change'],
    ['EtlSyncState',              'etl_sync_state'],
    ['EtlFailedEntries',          'etl_failed_entries']
  ];
  r text[];
BEGIN
  FOREACH r SLICE 1 IN ARRAY renames LOOP
    IF EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = r[1]
    ) THEN
      EXECUTE format('ALTER TABLE %I RENAME TO %I', r[1], r[2]);
      RAISE NOTICE 'Renamed % -> %', r[1], r[2];
    END IF;
  END LOOP;
END $$;
