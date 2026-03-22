-- Catalog tables (cat_*)
-- All use: code text PK, description text, active boolean NOT NULL DEFAULT false

CREATE TABLE IF NOT EXISTS cat_status_code (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_type_code (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_procedure_code (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_urgency_code (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_result_code (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_contracting_system (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_nuts (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_cpv (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_contracting_authority_type (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_activity_code (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_country_code (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_sub_type_code (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_awarding_criteria_type (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_awarding_criteria_sub_type (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_evaluation_criteria_type (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_declaration_type (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_funding_program (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_national_legislation (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_guarantee_type (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_execution_requirement (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_part_presentation (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_submission_method (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_notice_type (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS cat_document_type (
  code        text PRIMARY KEY,
  description text,
  active      boolean NOT NULL DEFAULT false
);
