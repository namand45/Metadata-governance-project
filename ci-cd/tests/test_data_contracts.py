"""
Data contract tests for the metadata governance platform.

Expected values come from the Metadata Governance Rules specification.
If these fail, a change has altered the meaning of the data.
"""
import os
import pytest
from databricks import sql

CATALOG = "metadata_governance"
TOLERANCE = 0.5  # percentage points


@pytest.fixture(scope="session")
def conn():
    host = os.environ["DATABRICKS_HOST"].replace("https://", "").rstrip("/")
    connection = sql.connect(
        server_hostname=host,
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )
    yield connection
    connection.close()


def query(conn, statement):
    with conn.cursor() as cur:
        cur.execute(statement)
        return cur.fetchall()


def scalar(conn, statement):
    return query(conn, statement)[0][0]


# ---------------------------------------------------------------
# Contract 1 — no rows are silently lost between layers
# ---------------------------------------------------------------

def test_bronze_row_count(conn):
    count = scalar(conn, f"SELECT COUNT(*) FROM {CATALOG}.bronze.raw_metadata")
    assert count == 10000, f"Bronze has {count} rows, expected 10000"


def test_silver_preserves_all_bronze_rows(conn):
    bronze = scalar(conn, f"SELECT COUNT(*) FROM {CATALOG}.bronze.raw_metadata")
    silver = scalar(conn, f"SELECT COUNT(*) FROM {CATALOG}.silver.silver_metadata_columns")
    assert silver == bronze, f"Silver dropped {bronze - silver} rows"


def test_gold_preserves_all_silver_rows(conn):
    silver = scalar(conn, f"SELECT COUNT(*) FROM {CATALOG}.silver.silver_metadata_columns")
    gold = scalar(conn, f"SELECT COUNT(*) FROM {CATALOG}.gold.column_governance_detail")
    assert gold == silver, f"Gold dropped {silver - gold} rows"


# ---------------------------------------------------------------
# Contract 2 — governance gap rates match the written specification
# ---------------------------------------------------------------

EXPECTED_MISSING_PCT = {
    "column_desc": 9.8,
    "table_desc": 39.4,
    "data_steward": 26.6,
    "security_classification": 23.3,
    "term_subdomain": 32.1,
    "certification_level": 18.5,
}


@pytest.mark.parametrize("field,expected", list(EXPECTED_MISSING_PCT.items()))
def test_missing_rate_matches_spec(conn, field, expected):
    actual = float(scalar(conn, f"""
        SELECT ROUND(100.0 * SUM(CASE WHEN {field} IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2)
        FROM {CATALOG}.silver.silver_metadata_columns
    """))
    assert abs(actual - expected) <= TOLERANCE, (
        f"{field} missing rate is {actual}%, spec says {expected}%"
    )


def test_gold_unowned_rate_matches_spec(conn):
    actual = float(scalar(conn, f"""
        SELECT ROUND(100.0 * SUM(CASE WHEN unowned THEN 1 ELSE 0 END) / COUNT(*), 2)
        FROM {CATALOG}.gold.column_governance_detail
    """))
    assert abs(actual - 26.6) <= TOLERANCE, f"Unowned rate is {actual}%, spec says 26.6%"


def test_gold_uncertified_rate_matches_spec(conn):
    actual = float(scalar(conn, f"""
        SELECT ROUND(100.0 * SUM(CASE WHEN uncertified THEN 1 ELSE 0 END) / COUNT(*), 2)
        FROM {CATALOG}.gold.column_governance_detail
    """))
    assert abs(actual - 18.5) <= TOLERANCE, f"Uncertified rate is {actual}%, spec says 18.5%"


# ---------------------------------------------------------------
# Contract 3 — derived values are internally consistent
# ---------------------------------------------------------------

def test_completeness_within_valid_range(conn):
    bad = scalar(conn, f"""
        SELECT COUNT(*) FROM {CATALOG}.gold.column_governance_detail
        WHERE row_completeness_pct < 0 OR row_completeness_pct > 100
    """)
    assert bad == 0, f"{bad} rows have an impossible completeness score"


def test_maturity_tiers_are_valid_values(conn):
    rows = query(conn, f"SELECT DISTINCT maturity_tier FROM {CATALOG}.gold.table_governance_summary")
    tiers = {r[0] for r in rows}
    assert tiers <= {"High", "Medium", "Low"}, f"Unexpected maturity tiers: {tiers}"


def test_maturity_thresholds_applied_correctly(conn):
    bad = scalar(conn, f"""
        SELECT COUNT(*) FROM {CATALOG}.gold.table_governance_summary
        WHERE (table_completeness_pct >= 90 AND maturity_tier <> 'High')
           OR (table_completeness_pct >= 50 AND table_completeness_pct < 90 AND maturity_tier <> 'Medium')
           OR (table_completeness_pct < 50 AND maturity_tier <> 'Low')
    """)
    assert bad == 0, f"{bad} tables have a maturity tier inconsistent with their score"


def test_pii_noncompliant_cannot_exceed_pii_total(conn):
    total, noncompliant = query(conn, f"""
        SELECT SUM(CASE WHEN pii_flag = TRUE THEN 1 ELSE 0 END),
               SUM(CASE WHEN pii_non_compliant THEN 1 ELSE 0 END)
        FROM {CATALOG}.gold.column_governance_detail
    """)[0]
    assert noncompliant <= total, (
        f"{noncompliant} columns flagged non-compliant but only {total} are marked PII"
    )


# ---------------------------------------------------------------
# Contract 4 — schema stability (this is what protects the dashboard)
# ---------------------------------------------------------------

REQUIRED_COLUMNS = {
    f"{CATALOG}.gold.column_governance_detail": [
        "column_id", "column_name", "table_id", "table_name",
        "row_completeness_pct", "pii_non_compliant", "unowned", "uncertified",
    ],
    f"{CATALOG}.gold.table_governance_summary": [
        "table_id", "table_name", "table_completeness_pct", "total_columns",
        "pii_non_compliant_count", "unowned_count", "uncertified_count", "maturity_tier",
    ],
}


@pytest.mark.parametrize("table,required", list(REQUIRED_COLUMNS.items()))
def test_schema_contract(conn, table, required):
    rows = query(conn, f"DESCRIBE {table}")
    present = {r[0] for r in rows}
    missing = [c for c in required if c not in present]
    assert not missing, f"{table} is missing {missing} — this breaks the dashboard"
