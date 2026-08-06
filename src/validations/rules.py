"""
Structural standard checks.
Converted from validations/rules.ipynb — logic unchanged.
"""
from pyspark.sql.functions import col, desc, lit


def get_standard_column_count(table_profile_df):
    result = (
        table_profile_df.groupBy("column_count").count()
        .orderBy(desc("count"), desc("column_count"))
        .first()
    )
    return result["column_count"]


def check_structural_compliance(table_profile_df, standard_column_count):
    return table_profile_df.withColumn(
        "standard_column_count", lit(standard_column_count)
    ).withColumn(
        "is_structurally_compliant",
        col("column_count") == standard_column_count
    )
