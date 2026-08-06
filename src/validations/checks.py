"""
Completeness, certification and compliance checks.
Converted from validations/checks.ipynb — logic unchanged. TIER2_FIELDS and
the maturity thresholds now come from src/common/schema.py so there is one
definition rather than several.
"""
from pyspark.sql.functions import col, when, expr

from src.common.schema import (
    TIER2_FIELDS,
    MATURITY_HIGH_MIN,
    MATURITY_MEDIUM_MIN,
)


def calculate_row_completeness(df, tier2_fields=TIER2_FIELDS):
    """
    Adds tier2_filled_count and row_completeness_pct based on how many of the
    governance-quality fields are non-null for each row.
    """
    completeness_expr = " + ".join(
        [f"CASE WHEN {f} IS NOT NULL THEN 1 ELSE 0 END" for f in tier2_fields]
    )
    return df.withColumn(
        "tier2_filled_count", expr(completeness_expr)
    ).withColumn(
        "row_completeness_pct", (col("tier2_filled_count") / len(tier2_fields)) * 100
    )


def flag_pii_non_compliant(df):
    """True if a column is flagged as PII but has no security_classification."""
    return df.withColumn(
        "pii_non_compliant",
        when((col("pii_flag") == True) & (col("security_classification").isNull()), True)
        .otherwise(False)
    )


def flag_unowned(df):
    """True if a column has no data_steward assigned."""
    return df.withColumn(
        "unowned",
        when(col("data_steward").isNull(), True).otherwise(False)
    )


def flag_uncertified(df):
    """True if a column has no certification_level assigned."""
    return df.withColumn(
        "uncertified",
        when(col("certification_level").isNull(), True).otherwise(False)
    )


def calculate_maturity_tier(df, completeness_col="table_completeness_pct"):
    """Buckets a table into High (>=90), Medium (50-89) or Low (<50)."""
    return df.withColumn(
        "maturity_tier",
        when(col(completeness_col) >= MATURITY_HIGH_MIN, "High")
        .when(col(completeness_col) >= MATURITY_MEDIUM_MIN, "Medium")
        .otherwise("Low")
    )
