# Databricks notebook source
import sys
sys.path.append("/Workspace/Users/shanaya.mehra@genpact.com/Metadata-Project-MyWorkspace")
from src.validations.checks import (
    calculate_row_completeness,
    flag_pii_non_compliant,
    flag_unowned,
    flag_uncertified,
    calculate_maturity_tier,
)
from pyspark.sql.functions import avg, sum as spark_sum, count, round as spark_round, col

# COMMAND ----------

#column-level
df = spark.table("metadata_governance.silver.silver_metadata_columns")

column_detail = calculate_row_completeness(df)
column_detail = flag_pii_non_compliant(column_detail)
column_detail = flag_unowned(column_detail)
column_detail = flag_uncertified(column_detail)

column_detail = column_detail.select(
    "column_id", "column_name", "table_id", "logical_table_key", "table_name", "schema_name",
    "database_name", "system_name", "pii_flag", "critical_data_element_flag",
    "security_classification", "data_steward", "certification_level",
    "row_completeness_pct", "pii_non_compliant", "unowned", "uncertified"
)

column_detail.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("metadata_governance.gold.column_governance_detail")

# COMMAND ----------

import sys
sys.path.append("/Workspace/Users/shanaya.mehra@genpact.com/Metadata-Project-MyWorkspace")
from src.validations.checks import (
    calculate_row_completeness,
    flag_pii_non_compliant,
    flag_unowned,
    flag_uncertified,
    calculate_maturity_tier,
)

# COMMAND ----------

#table-level
from pyspark.sql.functions import avg, sum as spark_sum, count, round as spark_round, col

silver_profile = spark.table("metadata_governance.silver.silver_table_profile").select(
    "logical_table_key", "column_count", "standard_column_count", "is_structurally_compliant"
)

table_summary = column_detail.groupBy("logical_table_key", "table_name", "schema_name", "database_name", "system_name").agg(
    spark_round(avg("row_completeness_pct"), 2).alias("table_completeness_pct"),
    count("column_id").alias("total_columns"),
    spark_sum(col("pii_non_compliant").cast("int")).alias("pii_non_compliant_count"),
    spark_sum(col("unowned").cast("int")).alias("unowned_count"),
    spark_sum(col("uncertified").cast("int")).alias("uncertified_count")
)

table_summary = calculate_maturity_tier(table_summary)

table_summary = table_summary.join(silver_profile, on="logical_table_key", how="left")

table_summary.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("metadata_governance.gold.table_governance_summary")

# COMMAND ----------

# MAGIC %sql
# MAGIC --database-level
# MAGIC CREATE OR REPLACE TABLE metadata_governance.gold.database_governance_summary
# MAGIC AS
# MAGIC SELECT
# MAGIC   COALESCE(database_name, 'unknown_database') AS database_name,
# MAGIC   system_name,
# MAGIC   schema_name,
# MAGIC   COUNT(*)                                                          AS total_tables,
# MAGIC   SUM(total_columns)                                                AS total_columns,
# MAGIC   ROUND(AVG(table_completeness_pct), 1)                             AS avg_completeness_pct,
# MAGIC   SUM(pii_non_compliant_count)                                      AS total_pii_noncompliant,
# MAGIC   SUM(unowned_count)                                                AS total_unowned_columns,
# MAGIC   SUM(uncertified_count)                                            AS total_uncertified_columns,
# MAGIC   SUM(CASE WHEN maturity_tier = 'High' THEN 1 ELSE 0 END)           AS high_maturity_table_count,
# MAGIC   SUM(CASE WHEN maturity_tier = 'Medium' THEN 1 ELSE 0 END)         AS medium_maturity_table_count,
# MAGIC   SUM(CASE WHEN maturity_tier = 'Low' THEN 1 ELSE 0 END)            AS low_maturity_table_count,
# MAGIC   ROUND(100.0 * SUM(CASE WHEN is_structurally_compliant THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_structurally_compliant
# MAGIC FROM metadata_governance.gold.table_governance_summary
# MAGIC GROUP BY COALESCE(database_name, 'unknown_database'), system_name, schema_name;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM metadata_governance.gold.column_governance_detail LIMIT 20;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM metadata_governance.gold.table_governance_summary LIMIT 20;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM metadata_governance.gold.database_governance_summary LIMIT 20;