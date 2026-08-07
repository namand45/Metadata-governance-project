-- Databricks notebook source
CREATE OR REPLACE TABLE metadata_governance.silver.silver_metadata_columns
AS
WITH deduped AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY TRIM(table_id), TRIM(column_id) ORDER BY column_id) AS rn
  FROM metadata_governance.bronze.raw_metadata
  WHERE column_id IS NOT NULL
    AND table_id  IS NOT NULL
)
SELECT
  TRIM(column_id)                                        AS column_id,
  TRIM(column_name)                                      AS column_name,
  NULLIF(TRIM(column_desc), '')                          AS column_desc,
  NULLIF(TRIM(term_name), '')                            AS term_name,
  NULLIF(TRIM(term_description), '')                     AS term_description,
  NULLIF(INITCAP(TRIM(security_classification)), '')     AS security_classification,
  TRY_CAST(critical_data_element_flag AS BOOLEAN)        AS critical_data_element_flag,
  TRY_CAST(pii_flag AS BOOLEAN)                          AS pii_flag,
  NULLIF(TRIM(term_subdomain), '')                       AS term_subdomain,
  NULLIF(TRIM(data_steward), '')                         AS data_steward,
  TRIM(table_id)                                         AS table_id,
  TRIM(table_name)                                       AS table_name,
  NULLIF(TRIM(table_desc), '')                           AS table_desc,
  TRIM(table_owner_in_source)                            AS table_owner_in_source,
  TRIM(schema_id)                                        AS schema_id,
  TRIM(schema_name)                                      AS schema_name,
  TRIM(database_id)                                      AS database_id,
  TRIM(database_name)                                    AS database_name,
  TRIM(system_id)                                        AS system_id,
  TRIM(system_name)                                      AS system_name,
  NULLIF(TRIM(location), '')                             AS location,
  TRY_CAST(total_record_count AS BIGINT)                 AS total_record_count,
  TRY_CAST(invalid_record_count AS BIGINT)               AS invalid_record_count,
  NULLIF(TRIM(tag_name), '')                             AS tag_name,
  NULLIF(TRIM(tag_value), '')                            AS tag_value,
  NULLIF(INITCAP(TRIM(certification_level)), '')         AS certification_level,
  CONCAT_WS('.',
    COALESCE(TRIM(system_name),   'unknown_system'),
    COALESCE(TRIM(database_name), 'unknown_database'),
    COALESCE(TRIM(schema_name),   'unknown_schema'),
    TRIM(table_name)
  )                                                       AS logical_table_key,
  current_timestamp()                                    AS _silver_loaded_at
FROM deduped
WHERE rn = 1;

-- COMMAND ----------

-- MAGIC %python
-- MAGIC bronze_count = spark.sql(
-- MAGIC     "SELECT record_count FROM metadata_governance.bronze.ingestion_log ORDER BY ingested_at DESC LIMIT 1"
-- MAGIC ).collect()[0]["record_count"]
-- MAGIC
-- MAGIC silver_count = spark.table("metadata_governance.silver.silver_metadata_columns").count()
-- MAGIC
-- MAGIC print(f"Bronze record count: {bronze_count}")
-- MAGIC print(f"Silver record count: {silver_count}")
-- MAGIC
-- MAGIC if silver_count != bronze_count:
-- MAGIC     dropped = bronze_count - silver_count
-- MAGIC     print(f"{dropped} record(s) removed between Bronze and Silver (null IDs and/or true duplicates).")
-- MAGIC else:
-- MAGIC     print(f"Record counts match exactly: {silver_count}")

-- COMMAND ----------

-- MAGIC %python
-- MAGIC import sys
-- MAGIC sys.path.append("/Workspace/Users/shanaya.mehra@genpact.com/Metadata-Project-MyWorkspace")
-- MAGIC from src.validations.rules import get_standard_column_count, check_structural_compliance

-- COMMAND ----------

-- MAGIC %python
-- MAGIC agg_df = spark.sql("""
-- MAGIC     SELECT
-- MAGIC         logical_table_key,
-- MAGIC         ANY_VALUE(table_name) AS table_name,
-- MAGIC         ANY_VALUE(table_desc) AS table_desc,
-- MAGIC         ANY_VALUE(schema_name) AS schema_name,
-- MAGIC         ANY_VALUE(database_name) AS database_name,
-- MAGIC         ANY_VALUE(system_name) AS system_name,
-- MAGIC         ANY_VALUE(location) AS location,
-- MAGIC         MAX(CASE WHEN tag_name = 'domain' THEN tag_value END) AS domain,
-- MAGIC         ANY_VALUE(certification_level) AS certification_level,
-- MAGIC         MAX(total_record_count) AS total_record_count,
-- MAGIC         MAX(invalid_record_count) AS invalid_record_count,
-- MAGIC         COUNT(DISTINCT column_id) AS column_count,
-- MAGIC         SUM(CASE WHEN column_desc IS NULL THEN 1 ELSE 0 END) AS columns_missing_desc,
-- MAGIC         SUM(CASE WHEN pii_flag = TRUE THEN 1 ELSE 0 END) AS pii_column_count,
-- MAGIC         (MAX(CASE WHEN data_steward IS NOT NULL THEN 1 ELSE 0 END) = 1) AS has_data_steward,
-- MAGIC         (MAX(CASE WHEN table_desc IS NOT NULL THEN 1 ELSE 0 END) = 1) AS has_table_desc,
-- MAGIC         (MAX(CASE WHEN tag_name IS NOT NULL THEN 1 ELSE 0 END) = 1) AS has_source_tag,
-- MAGIC         (MAX(CASE WHEN security_classification IS NOT NULL THEN 1 ELSE 0 END) = 1) AS has_security_classification
-- MAGIC     FROM metadata_governance.silver.silver_metadata_columns
-- MAGIC     GROUP BY logical_table_key
-- MAGIC """)
-- MAGIC
-- MAGIC standard_count = get_standard_column_count(agg_df)
-- MAGIC table_profile = check_structural_compliance(agg_df, standard_count)
-- MAGIC table_profile.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("metadata_governance.silver.silver_table_profile")

-- COMMAND ----------

SELECT COUNT(*) FROM metadata_governance.silver.silver_table_profile;