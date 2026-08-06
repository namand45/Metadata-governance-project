"""
Unit tests for the validation logic in src/validations/.
Runs against a local Spark session — no Databricks connection,
no compute quota consumed.
"""
import pytest
from pyspark.sql import SparkSession

from src.common.schema import TIER2_FIELDS, EXPECTED_MISSING_PCT
from src.validations.rules import (
    get_standard_column_count,
    check_structural_compliance,
)
from src.validations.checks import (
    calculate_row_completeness,
    flag_pii_non_compliant,
    flag_unowned,
    flag_uncertified,
    calculate_maturity_tier,
)


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder
        .master("local[1]")
        .appName("validation-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    yield session
    session.stop()


COLUMN_SCHEMA = (
    "column_desc string, table_desc string, data_steward string, "
    "security_classification string, term_subdomain string, "
    "certification_level string, pii_flag boolean"
)


def column_df(spark, rows):
    return spark.createDataFrame(rows, schema=COLUMN_SCHEMA)


def tables_df(spark):
    rows = [(f"table_{i}", 10) for i in range(10)] + [("odd_one_out", 2)]
    return spark.createDataFrame(rows, schema="table_name string, column_count int")


# --- completeness scoring (Governance Rules, section 2) ---

def test_fully_populated_row_scores_100(spark):
    df = column_df(spark, [("desc", "tdesc", "Jane", "Internal", "Sales", "Certified", True)])
    row = calculate_row_completeness(df).collect()[0]
    assert row["tier2_filled_count"] == 6
    assert row["row_completeness_pct"] == 100.0


def test_all_governance_fields_null_scores_zero(spark):
    df = column_df(spark, [(None, None, None, None, None, None, True)])
    row = calculate_row_completeness(df).collect()[0]
    assert row["tier2_filled_count"] == 0
    assert row["row_completeness_pct"] == 0.0


def test_four_of_six_scores_two_thirds(spark):
    df = column_df(spark, [(None, None, "Jane", "Internal", "Sales", "Certified", True)])
    row = calculate_row_completeness(df).collect()[0]
    assert row["tier2_filled_count"] == 4
    assert round(row["row_completeness_pct"], 2) == 66.67


# --- PII compliance (section 4) ---

def test_pii_without_classification_is_flagged(spark):
    df = column_df(spark, [("d", "td", "Jane", None, "Sales", "Certified", True)])
    assert flag_pii_non_compliant(df).collect()[0]["pii_non_compliant"]


def test_pii_with_classification_is_not_flagged(spark):
    df = column_df(spark, [("d", "td", "Jane", "Internal", "Sales", "Certified", True)])
    assert not flag_pii_non_compliant(df).collect()[0]["pii_non_compliant"]


def test_non_pii_without_classification_is_not_flagged(spark):
    df = column_df(spark, [("d", "td", "Jane", None, "Sales", "Certified", False)])
    assert not flag_pii_non_compliant(df).collect()[0]["pii_non_compliant"]


# --- stewardship (section 5) and certification (section 6) ---

def test_missing_steward_is_unowned(spark):
    df = column_df(spark, [("d", "td", None, "Internal", "Sales", "Certified", True)])
    assert flag_unowned(df).collect()[0]["unowned"]


def test_present_steward_is_not_unowned(spark):
    df = column_df(spark, [("d", "td", "Jane", "Internal", "Sales", "Certified", True)])
    assert not flag_unowned(df).collect()[0]["unowned"]


def test_missing_certification_is_uncertified(spark):
    df = column_df(spark, [("d", "td", "Jane", "Internal", "Sales", None, True)])
    assert flag_uncertified(df).collect()[0]["uncertified"]


# --- maturity classification (section 3) ---

@pytest.mark.parametrize("pct,expected", [
    (100.0, "High"), (90.0, "High"), (89.9, "Medium"),
    (50.0, "Medium"), (49.9, "Low"), (0.0, "Low"),
])
def test_maturity_boundaries(spark, pct, expected):
    df = spark.createDataFrame([(pct,)], schema="table_completeness_pct double")
    assert calculate_maturity_tier(df).collect()[0]["maturity_tier"] == expected


# --- structural standard (Requirements, Objective 1) ---

def test_standard_is_the_most_common_column_count(spark):
    assert get_standard_column_count(tables_df(spark)) == 10


def test_outlier_table_is_flagged_non_compliant(spark):
    df = tables_df(spark)
    standard = get_standard_column_count(df)
    result = {
        r["table_name"]: r["is_structurally_compliant"]
        for r in check_structural_compliance(df, standard).collect()
    }
    assert not result["odd_one_out"]
    assert all(v for k, v in result.items() if k != "odd_one_out")


# --- specification constants ---

def test_six_tier2_fields_defined():
    assert len(TIER2_FIELDS) == 6


def test_expected_missing_rates_cover_all_tier2_fields():
    assert set(EXPECTED_MISSING_PCT) == set(TIER2_FIELDS)
