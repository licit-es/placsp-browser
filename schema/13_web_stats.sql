-- Landing page statistics (materialized, refreshed daily via pg_cron).

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_landing_stats AS
SELECT
  (SELECT count(*)       FROM mv_licitacion)               AS total_licitaciones,
  (SELECT count(*)       FROM contracting_party)            AS total_organos,
  (SELECT count(*)       FROM empresa)                      AS total_empresas,
  (SELECT coalesce(sum(presupuesto_sin_iva), 0)
     FROM mv_licitacion)                                    AS importe_total,
  (SELECT max(fecha_actualizacion)
     FROM mv_licitacion)                                    AS ultima_actualizacion;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_landing_stats
  ON mv_landing_stats (total_licitaciones);

CREATE OR REPLACE FUNCTION refresh_mv_landing_stats() RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY mv_landing_stats;
END $$ LANGUAGE plpgsql;

-- pg_cron: refresh daily at 05:00 UTC (after ETL hourly + catalog at 03:00).
CREATE EXTENSION IF NOT EXISTS pg_cron;

DO $$
BEGIN
  PERFORM cron.unschedule('refresh-mv-landing-stats');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

SELECT cron.schedule(
  'refresh-mv-landing-stats',
  '0 5 * * *',
  $$SELECT refresh_mv_landing_stats()$$
);
