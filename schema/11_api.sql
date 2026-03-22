-- Search infrastructure and API views

-- pg_trgm for fuzzy name matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- FTS: stored tsvector on contract_folder_status (name + summary)
ALTER TABLE contract_folder_status
  ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE OR REPLACE FUNCTION cfs_search_update() RETURNS trigger AS $$
BEGIN
  NEW.search_vector := to_tsvector('spanish',
    coalesce(NEW.name, '') || ' ' || coalesce(NEW.summary, '')
  );
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DO $$ BEGIN
  CREATE TRIGGER cfs_search_trigger
    BEFORE INSERT OR UPDATE OF name, summary ON contract_folder_status
    FOR EACH ROW EXECUTE FUNCTION cfs_search_update();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_cfs_search
  ON contract_folder_status USING gin(search_vector);

-- Trigram indexes for fuzzy matching on names
CREATE INDEX IF NOT EXISTS idx_cp_name_trgm
  ON contracting_party USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_wp_name_trgm
  ON winning_party USING gin(name gin_trgm_ops);

-- Flat view: one row per licitación, ready for search results
CREATE OR REPLACE VIEW v_licitacion AS
SELECT
  cfs.id,
  cfs.contract_folder_id AS expediente,
  cfs.name AS titulo,
  cfs.summary AS descripcion,
  cfs.updated AS fecha_publicacion,
  cfs.status_code AS estado,
  cfs.type_code AS tipo_contrato,
  cfs.procedure_code AS procedimiento,
  cfs.urgency_code AS tramitacion,
  cfs.tax_exclusive_amount AS presupuesto_sin_iva,
  cfs.total_amount AS presupuesto_con_iva,
  cfs.estimated_overall_contract_amount AS valor_estimado,
  cfs.submission_deadline_date AS fecha_limite,
  cfs.submission_deadline_time AS hora_limite,
  cfs.duration_measure AS duracion,
  cfs.duration_unit_code AS duracion_unidad,
  cfs.nuts_code AS lugar_nuts,
  cfs.country_subentity AS lugar_subentidad,
  cfs.funding_program_code,
  cfs.funding_program_name AS programa_financiacion,
  cfs.contracting_system_code AS sistema_contratacion,
  cfs.allowed_subcontract_rate AS tasa_subcontratacion,
  cfs.search_vector,

  -- Organo
  cp.id AS organo_id,
  cp.name AS organo,
  cp.nif AS organo_nif,
  cp.contracting_party_type_code AS organo_tipo,

  -- CPV principal (first folder-level)
  (SELECT cc.item_classification_code
   FROM cpv_classification cc
   WHERE cc.contract_folder_status_id = cfs.id AND cc.lot_id IS NULL
   ORDER BY cc.id LIMIT 1) AS cpv_principal,

  -- Result (latest)
  tr.award_date AS fecha_adjudicacion,
  tr.awarded_tax_exclusive_amount AS importe_adjudicacion,
  tr.received_tender_quantity AS num_licitadores,
  tr.result_code,

  -- Adjudicatario
  wp.name AS adjudicatario,
  wp.identifier AS adjudicatario_nif,

  -- Formalizacion
  ct.issue_date AS fecha_formalizacion,

  -- Aggregates
  (SELECT count(*)::int FROM procurement_project_lot l
   WHERE l.contract_folder_status_id = cfs.id) AS num_lotes,
  EXISTS(SELECT 1 FROM document_reference dr
   WHERE dr.contract_folder_status_id = cfs.id) AS tiene_documentos

FROM contract_folder_status cfs
LEFT JOIN contracting_party cp ON cp.id = cfs.contracting_party_id
LEFT JOIN LATERAL (
  SELECT * FROM tender_result t
  WHERE t.contract_folder_status_id = cfs.id
  ORDER BY t.award_date DESC NULLS LAST
  LIMIT 1
) tr ON true
LEFT JOIN LATERAL (
  SELECT name, identifier FROM winning_party
  WHERE tender_result_id = tr.id
  LIMIT 1
) wp ON true
LEFT JOIN LATERAL (
  SELECT issue_date FROM contract
  WHERE tender_result_id = tr.id
  LIMIT 1
) ct ON true;
