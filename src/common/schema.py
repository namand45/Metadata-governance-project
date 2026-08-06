"""
Metadata schema definitions shared by the pipeline, the validation rules
and the chatbot. Mirrors the Metadata Governance Rules specification.
"""

# Tier 1 — structural. Absence is a data integrity error, not a score.
TIER1_FIELDS = [
    "column_id",
    "column_name",
    "table_id",
    "table_name",
    "schema_name",
    "database_name",
    "system_name",
]

# Tier 2 — governance-critical. These drive the completeness score.
TIER2_FIELDS = [
    "column_desc",
    "table_desc",
    "data_steward",
    "security_classification",
    "term_subdomain",
    "certification_level",
]

# Maturity thresholds, applied to table-level completeness percentage.
MATURITY_HIGH_MIN = 95
MATURITY_MEDIUM_MIN = 50

# Certification level used when the source value is null.
DEFAULT_CERTIFICATION = "Uncertified"

# Observed missing rates from the specification, kept as regression baselines.
EXPECTED_MISSING_PCT = {
    "column_desc": 9.8,
    "table_desc": 39.4,
    "data_steward": 26.6,
    "security_classification": 23.3,
    "term_subdomain": 32.1,
    "certification_level": 18.5,
}
