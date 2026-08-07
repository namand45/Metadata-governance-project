# Databricks notebook source
display(dbutils.fs.ls("/Volumes/metadata_governance/bronze/raw_data/"))

# COMMAND ----------

files = dbutils.fs.ls("/Volumes/metadata_governance/bronze/raw_data/")
for f in files:
    print(f.name)

# COMMAND ----------

# MAGIC %pip install openpyxl
# MAGIC

# COMMAND ----------

import pandas as pd

pdf = pd.read_excel("/Volumes/metadata_governance/bronze/raw_data/metadata_realistic_10k 1 2 (1).xlsx")
df = spark.createDataFrame(pdf)
df.display()


# COMMAND ----------

df.printSchema()

# COMMAND ----------

df.write.mode("overwrite").saveAsTable("metadata_governance.bronze.raw_metadata")

# COMMAND ----------

from pyspark.sql.functions import current_timestamp, lit

row_count = df.count()
print(f"Ingested {row_count} records from source file")

log_entry = spark.createDataFrame([(row_count,)], ["record_count"]) \
    .withColumn("ingested_at", current_timestamp()) \
    .withColumn("source_file", lit("metadata_realistic_10k 1 2 (1).xlsx"))

log_entry.write.mode("append").saveAsTable("metadata_governance.bronze.ingestion_log")

# COMMAND ----------

spark.sql("SELECT * FROM metadata_governance.bronze.raw_metadata LIMIT 10").display()

# COMMAND ----------

spark.sql("SELECT * FROM metadata_governance.bronze.ingestion_log ORDER BY ingested_at DESC").display()