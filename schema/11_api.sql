-- Search infrastructure and presentation views
-- Tables are for ETL ingestion; views are the API's interface.

-- =================================================================
-- SEARCH INFRASTRUCTURE
-- =================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

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
CREATE INDEX IF NOT EXISTS idx_cp_name_trgm
  ON contracting_party USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_wp_name_trgm
  ON winning_party USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_sc_cfs_updated
  ON status_change (contract_folder_status_id, updated);

-- winning_party.identifier: empresa subquery counts, empresa_upsert trigger
CREATE INDEX IF NOT EXISTS idx_wp_identifier
  ON winning_party (identifier);

-- tender_result: v_licitacion LATERAL picks latest by award_date DESC
CREATE INDEX IF NOT EXISTS idx_tr_cfs_award
  ON tender_result (contract_folder_status_id, award_date DESC NULLS LAST);

-- cpv_classification: prefix LIKE search in /buscar CPV filter
CREATE INDEX IF NOT EXISTS idx_cpv_code_prefix
  ON cpv_classification (item_classification_code text_pattern_ops);

-- =================================================================
-- EMPRESA (canonical companies, derived from winning_party)
-- =================================================================

CREATE TABLE IF NOT EXISTS empresa (
  nif     text PRIMARY KEY,
  nombre  text NOT NULL,
  ciudad  text,
  tipo    text
);

-- Trigger: upsert empresa on every winning_party INSERT.
-- Prefers non-UTE names; among same kind picks the longest (most complete).
CREATE OR REPLACE FUNCTION empresa_upsert() RETURNS trigger AS $$
DECLARE
  _current text;
BEGIN
  IF NEW.identifier IS NULL THEN
    RETURN NEW;
  END IF;

  -- Try insert first; if row exists, conditionally update.
  INSERT INTO empresa (nif, nombre, ciudad, tipo)
  VALUES (NEW.identifier, NEW.name, NEW.city_name, NEW.company_type_code)
  ON CONFLICT (nif) DO NOTHING;

  IF NOT FOUND THEN
    SELECT nombre INTO _current FROM empresa WHERE nif = NEW.identifier;
    -- Prefer non-UTE over UTE; among same kind prefer longer name.
    IF (_current ~* '^U\.?T\.?E\.?\s' AND NEW.name !~* '^U\.?T\.?E\.?\s')
       OR ((_current ~* '^U\.?T\.?E\.?\s') = (NEW.name ~* '^U\.?T\.?E\.?\s')
           AND length(NEW.name) > length(_current))
    THEN
      UPDATE empresa
      SET nombre = NEW.name, ciudad = NEW.city_name, tipo = NEW.company_type_code
      WHERE nif = NEW.identifier;
    END IF;
  END IF;

  RETURN NEW;
END $$ LANGUAGE plpgsql SET search_path = public;

DO $$ BEGIN
  CREATE TRIGGER empresa_upsert_trigger
    AFTER INSERT ON winning_party
    FOR EACH ROW EXECUTE FUNCTION empresa_upsert();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_empresa_nombre_trgm
  ON empresa USING gin(nombre gin_trgm_ops);

-- =================================================================
-- PRESENTATION VIEWS
-- =================================================================

-- v_licitacion: one row per tender, all codes resolved to labels
-- NOTE: if columns change, run DROP VIEW v_licitacion CASCADE manually first.
CREATE OR REPLACE VIEW v_licitacion AS
SELECT
  cfs.id,
  cfs.contract_folder_id AS expediente,
  cfs.name AS titulo,
  cfs.summary AS descripcion,
  cfs.link AS url_place,
  cfs.updated AS fecha_actualizacion,
  COALESCE(hist.first_seen, cfs.updated) AS fecha_publicacion,
  COALESCE(hist.timeline, '[]'::jsonb) AS historial_estados,
  cfs.search_vector,

  -- Raw codes (for indexed filtering)
  cfs.status_code,
  cfs.type_code,
  cfs.procedure_code,

  -- Codes resolved to labels (for display)
  COALESCE(cat_sc.description, cfs.status_code) AS estado,
  COALESCE(cat_tc.description, cfs.type_code) AS tipo_contrato,
  COALESCE(cat_pc.description, cfs.procedure_code) AS procedimiento,
  COALESCE(cat_uc.description, cfs.urgency_code) AS tramitacion,
  COALESCE(cat_cs.description, cfs.contracting_system_code) AS sistema_contratacion,

  -- Economic
  cfs.tax_exclusive_amount AS presupuesto_sin_iva,
  cfs.total_amount AS presupuesto_con_iva,
  cfs.estimated_overall_contract_amount AS valor_estimado,

  -- Temporal
  cfs.submission_deadline_date AS fecha_limite,
  cfs.submission_deadline_time AS hora_limite,
  cfs.duration_measure AS duracion,
  cfs.duration_unit_code AS duracion_unidad,

  -- Geographic
  COALESCE(cat_nuts.description, cfs.nuts_code) AS lugar_nuts,
  cfs.country_subentity AS lugar_subentidad,

  -- Other
  cfs.funding_program_code,
  COALESCE(cat_fp.description, cfs.funding_program_name) AS programa_financiacion,
  cfs.allowed_subcontract_rate AS tasa_subcontratacion,

  -- Organo
  cp.id AS organo_id,
  cp.name AS organo,
  cp.nif AS organo_nif,
  COALESCE(cat_cat.description, cp.contracting_party_type_code) AS organo_tipo,

  -- CPV principal (with description)
  cpv_sub.cpv_principal,
  cpv_sub.cpv_principal_desc,

  -- Result (latest)
  tr.award_date AS fecha_adjudicacion,
  tr.awarded_tax_exclusive_amount AS importe_adjudicacion,
  tr.received_tender_quantity AS num_licitadores,
  COALESCE(cat_rc.description, tr.result_code) AS resultado,

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
-- Status timeline (first publication + full history)
LEFT JOIN LATERAL (
  SELECT
    min(sc.updated) AS first_seen,
    jsonb_agg(jsonb_build_object(
      'estado', COALESCE(cat_sc2.description, sc.status_code),
      'fecha', sc.updated
    ) ORDER BY sc.updated) AS timeline
  FROM status_change sc
  LEFT JOIN cat_status_code cat_sc2 ON cat_sc2.code = sc.status_code
  WHERE sc.contract_folder_status_id = cfs.id
) hist ON true
-- Catalog lookups
LEFT JOIN cat_status_code     cat_sc   ON cat_sc.code   = cfs.status_code
LEFT JOIN cat_type_code       cat_tc   ON cat_tc.code   = cfs.type_code
LEFT JOIN cat_procedure_code  cat_pc   ON cat_pc.code   = cfs.procedure_code
LEFT JOIN cat_urgency_code    cat_uc   ON cat_uc.code   = cfs.urgency_code
LEFT JOIN cat_contracting_system cat_cs ON cat_cs.code  = cfs.contracting_system_code
LEFT JOIN cat_nuts            cat_nuts ON cat_nuts.code  = cfs.nuts_code
LEFT JOIN cat_funding_program cat_fp   ON cat_fp.code   = cfs.funding_program_code
LEFT JOIN cat_contracting_authority_type cat_cat ON cat_cat.code = cp.contracting_party_type_code
-- CPV principal with description
LEFT JOIN LATERAL (
  SELECT cc.item_classification_code AS cpv_principal,
         cat_cpv.description AS cpv_principal_desc
  FROM cpv_classification cc
  LEFT JOIN cat_cpv ON cat_cpv.code = cc.item_classification_code
  WHERE cc.contract_folder_status_id = cfs.id AND cc.lot_id IS NULL
  ORDER BY cc.id LIMIT 1
) cpv_sub ON true
-- Tender result (latest)
LEFT JOIN LATERAL (
  SELECT * FROM tender_result t
  WHERE t.contract_folder_status_id = cfs.id
  ORDER BY t.award_date DESC NULLS LAST LIMIT 1
) tr ON true
LEFT JOIN cat_result_code cat_rc ON cat_rc.code = tr.result_code
LEFT JOIN LATERAL (
  SELECT name, identifier FROM winning_party
  WHERE tender_result_id = tr.id LIMIT 1
) wp ON true
LEFT JOIN LATERAL (
  SELECT issue_date FROM contract
  WHERE tender_result_id = tr.id LIMIT 1
) ct ON true;


-- v_criterio: awarding criteria with resolved type codes
CREATE OR REPLACE VIEW v_criterio AS
SELECT
  ac.id,
  ac.contract_folder_status_id AS licitacion_id,
  ac.lot_id AS lote_id,
  COALESCE(cat_act.description, ac.criteria_type_code) AS tipo,
  COALESCE(cat_acst.description, ac.criteria_sub_type_code) AS subtipo,
  ac.description AS descripcion,
  ac.weight_numeric AS peso,
  ac.note AS nota
FROM awarding_criteria ac
LEFT JOIN cat_awarding_criteria_type cat_act
  ON cat_act.code = ac.criteria_type_code
LEFT JOIN cat_awarding_criteria_sub_type cat_acst
  ON cat_acst.code = ac.criteria_sub_type_code;


-- v_solvencia: qualification requirements with resolved codes
CREATE OR REPLACE VIEW v_solvencia AS
SELECT
  qr.id,
  qr.contract_folder_status_id AS licitacion_id,
  qr.lot_id AS lote_id,
  qr.origin_type AS origen,
  COALESCE(cat_ect.description, qr.evaluation_criteria_type_code) AS tipo_evaluacion,
  qr.description AS descripcion,
  qr.threshold_quantity AS umbral,
  qr.personal_situation AS situacion_personal,
  qr.operating_years_quantity AS anios_experiencia,
  qr.employee_quantity AS num_empleados
FROM qualification_requirement qr
LEFT JOIN cat_evaluation_criteria_type cat_ect
  ON cat_ect.code = qr.evaluation_criteria_type_code;


-- v_documento: document references with resolved type codes
CREATE OR REPLACE VIEW v_documento AS
SELECT
  dr.id,
  dr.contract_folder_status_id AS licitacion_id,
  COALESCE(cat_dt.description, dr.document_type_code) AS tipo,
  dr.filename AS nombre,
  dr.uri AS url
FROM document_reference dr
LEFT JOIN cat_document_type cat_dt ON cat_dt.code = dr.document_type_code;


-- v_lote: lots with CPV descriptions
CREATE OR REPLACE VIEW v_lote AS
SELECT
  l.id,
  l.contract_folder_status_id AS licitacion_id,
  l.lot_number AS numero,
  l.name AS titulo,
  l.tax_exclusive_amount AS presupuesto_sin_iva,
  COALESCE(cat_nuts.description, l.nuts_code) AS lugar_nuts,
  l.country_subentity AS lugar_subentidad
FROM procurement_project_lot l
LEFT JOIN cat_nuts ON cat_nuts.code = l.nuts_code;


-- v_cpv: CPV codes with descriptions
CREATE OR REPLACE VIEW v_cpv AS
SELECT
  cc.id,
  cc.contract_folder_status_id AS licitacion_id,
  cc.lot_id AS lote_id,
  cc.item_classification_code AS codigo,
  COALESCE(cat_cpv.description, cc.item_classification_code) AS descripcion
FROM cpv_classification cc
LEFT JOIN cat_cpv ON cat_cpv.code = cc.item_classification_code;


-- v_adjudicacion: all adjudications (one row per winning party per result)
-- Used for empresa/organo stats — unlike v_licitacion which picks only the
-- latest result, this view exposes every award including per-lot results.
CREATE OR REPLACE VIEW v_adjudicacion AS
SELECT
  cfs.id AS licitacion_id,
  cfs.tax_exclusive_amount AS presupuesto_sin_iva,
  tr.awarded_tax_exclusive_amount AS importe_adjudicacion,
  tr.award_date AS fecha_adjudicacion,
  tr.received_tender_quantity AS num_licitadores,
  wp.name AS adjudicatario,
  wp.identifier AS adjudicatario_nif,
  cp.id AS organo_id,
  cp.name AS organo
FROM tender_result tr
JOIN contract_folder_status cfs ON cfs.id = tr.contract_folder_status_id
JOIN winning_party wp ON wp.tender_result_id = tr.id
LEFT JOIN contracting_party cp ON cp.id = cfs.contracting_party_id;

-- =================================================================
-- EMPRESA INITIAL POPULATION
-- Idempotent. Prefers non-UTE names, then longest.
-- =================================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM empresa LIMIT 1) THEN
    INSERT INTO empresa (nif, nombre, ciudad, tipo)
    SELECT DISTINCT ON (identifier)
      identifier, name, city_name, company_type_code
    FROM winning_party
    WHERE identifier IS NOT NULL
    ORDER BY identifier,
      CASE WHEN name ~* '^U\.?T\.?E\.?\s' THEN 1 ELSE 0 END,
      length(name) DESC NULLS LAST
    ON CONFLICT (nif) DO NOTHING;
  END IF;
END $$;

-- =================================================================
-- MATERIALIZED VIEW: mv_licitacion
-- Pre-computed snapshot of v_licitacion for fast API reads.
-- Refreshed after each ETL batch via refresh_mv_licitacion().
-- =================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_licitacion AS
SELECT * FROM v_licitacion;

-- Unique index required for REFRESH ... CONCURRENTLY (no lock on reads)
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_licitacion_id
  ON mv_licitacion (id);

-- Reproduce the search/filter indexes on the matview
CREATE INDEX IF NOT EXISTS idx_mv_licitacion_search
  ON mv_licitacion USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_mv_licitacion_updated
  ON mv_licitacion (fecha_actualizacion DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_mv_licitacion_status
  ON mv_licitacion (status_code);
CREATE INDEX IF NOT EXISTS idx_mv_licitacion_type_budget
  ON mv_licitacion (type_code, presupuesto_sin_iva);
CREATE INDEX IF NOT EXISTS idx_mv_licitacion_organo
  ON mv_licitacion (organo_id);
CREATE INDEX IF NOT EXISTS idx_mv_licitacion_adjudicatario
  ON mv_licitacion (adjudicatario_nif);

-- Function: refresh the matview. Called by ETL after batch completes.
-- CONCURRENTLY allows reads during refresh (requires the unique index).
CREATE OR REPLACE FUNCTION refresh_mv_licitacion() RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY mv_licitacion;
END $$ LANGUAGE plpgsql;
