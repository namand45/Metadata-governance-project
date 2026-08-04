# Metadata-Driven Governance & Validation Platform

Genpact Data Engineering Capstone — Databricks (Free Edition) + Unity Catalog + GitHub

## Team

| Member | Responsibility |
|---|---|
| Naman Dewan | Metadata & Governance Logic — validation rules, completeness scoring, maturity classification, Gold layer, dashboard build |
| Anirudh Uppili Mukundan | Data Engineering — Bronze/Silver pipeline, CI/CD, Dev/Prod |
| Kabir Gulati | AI Metadata Assistant (Genie-based) |
| Shanaya Mehra | Governance Dashboard |

Managers: Anila Hoti, Greta Isufi

## What this project does

Ingests column-level metadata records, scores their governance quality against a defined rule set, classifies tables into maturity tiers, and surfaces the results in an interactive Databricks dashboard and an AI metadata assistant.

**Pipeline:** raw Excel → Bronze → Silver (cleaning) → Gold (governance scoring) → Dashboard / AI Assistant

## Architecture

Catalog: `metadata_governance` with `bronze`, `silver`, `gold` schemas.

| Layer | Table | Owner | Purpose |
|---|---|---|---|
| Bronze | `bronze.raw_metadata` | Anirudh | Raw ingest of the source Excel (10,000 rows × 26 columns) |
| Silver | `silver.silver_metadata_columns` | Anirudh | Cleaned records (TRIM, NULLIF empty→null, INITCAP, TRY_CAST) |
| Silver | `silver.silver_table_profile` | Anirudh | Silver-layer data-quality metrics (QA only — see "Two scoring formulas" below) |
| Gold | `gold.column_governance_detail` | Naman | One row per column: completeness score + governance flags + `logical_table_key` |
| Gold | `gold.table_governance_summary` | Naman | Legacy rollup by `table_id` (retained for comparison — see "Two grains" below) |
| Gold | `gold.table_governance_summary_logical` | Naman | **Official** rollup by logical table (system.database.schema.table_name) |

## Governance rules (official scoring)

Defined and owned by Naman; implemented in the Gold layer.

- **Tier 1 (structural, always populated, not scored):** column_id, column_name, table_id, table_name, schema_name, database_name, system_name
- **Tier 2 (governance-critical, drives scoring — 6 fields):** column_desc, table_desc, data_steward, security_classification, term_subdomain, certification_level
- **Completeness:** (non-null Tier 2 fields) / 6 × 100 per column record; averaged per table for the table score. All scores are multiples of 16.67.
- **Maturity tiers:** High ≥ 90 · Medium 50–89 · Low < 50
- **PII compliance:** `pii_flag = true AND security_classification IS NULL` → non-compliant
- **Stewardship:** `data_steward IS NULL` → unowned
- **Certification:** `certification_level IS NULL` → uncertified

### Two scoring formulas — which is official

`silver.silver_table_profile` (Anirudh) computes Silver-layer **QA metrics** using its own formula. The Gold-layer scoring above is the **official governance source of truth** — the dashboard and the AI assistant read exclusively from Gold. The Silver profile is retained for pipeline quality monitoring and is not comparable number-for-number with Gold scores.

## Two grains — table_id vs logical table

The source dataset's `table_id` is 1:1 with `column_id` (verified: every one of the 10,000 table_ids has exactly one column). It behaves as a row identifier, not a table key. The true table identity is the name hierarchy.

- **`table_governance_summary`** (legacy): grouped by `table_id` → 10,000 "tables" of 1 column each. Faithful to the provided key; retained for comparison and auditability.
- **`table_governance_summary_logical`** (official): grouped by `system_name.database_name.schema_name.table_name` → **1,887 logical tables, avg 5.3 columns, max 15**. Each has a readable key, e.g. `Snowflake.crm.gold.sales`, stored as `logical_table_key` (also added to `column_governance_detail`).

Null handling: 457 records have null `database_name`; these are bucketed explicitly as `unknown_database` (185 logical tables) rather than dropped — itself a governance finding.

Grain comparison (same underlying column scores, different rollup):

| Metric | table_id grain | logical grain |
|---|---|---|
| Tables | 10,000 | 1,887 |
| Columns | 10,000 | 10,000 |
| Avg completeness | 75.0% | 75.1% |
| Maturity High / Med / Low | 17.3 / 79.2 / 3.5 % | 4.5 / 95.0 / 0.6 % |

Open question (for management): at the logical grain, 95% of tables land in Medium — the 90/50 tier thresholds may need retuning to remain discriminating.

## Dashboard

Databricks Dashboard **"Metadata Governance – Executive Overview"** (published), reading from the Gold logical grain. Three levels:

1. **KPI row:** Total Tables (1.89K) · Columns (10K) · Completeness % (75.1) · Certified % (81.5) · Owned % (73.4) · Unlabeled Risk (217 PII columns without a security classification)
2. **Breakdown:** maturity donut · completeness-by-table (worst-first worklist) · compliance-risk exception table
3. **Drill-down:** column-level detail for one selected table, driven by a single-select **Select Table** filter bound to `logical_table_key` (two field bindings + one query parameter)

Dashboard definition and the five dataset queries are versioned in this repo (`.lvdash.json` + SQL files).

## Repository contents

- Gold layer notebook — builds `column_governance_detail`, both summary tables, plus inline validation queries (row counts, grain reconciliation, maturity distribution)
- Validation logic notebook (`02_validation_logic`) — the four governance rules tested against Bronze and Silver
- Dashboard definition (`.lvdash.json`)
- Dataset SQL: `exec_summary`, `maturity_distribution`, `completeness_by_table`, `compliance_risk`, `column_drilldown`, `table_governance_summary_logical`

## Workflow

- `main` is protected: all changes flow through a feature branch → pull request → 1 approval → merge. Force pushes and branch deletion are blocked.
- Databricks ↔ GitHub via a workspace Git folder; each team member authenticates with a personal access token (Databricks Settings → Linked Accounts).

## Known constraints

- **Databricks Free Edition:** no Account Console, no external S3 locations (native Unity Catalog Volumes used instead), one workspace per account (limits full Dev/Prod separation).
- **Synthetic dataset:** only 14 distinct table names across 1,887 logical tables — heavy name duplication is a property of the data. Some logical tables contain duplicate column names (merged duplicate metadata registrations); surfaced by the drill-down by design.
