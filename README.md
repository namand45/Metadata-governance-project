# Metadata-governance-project

Metadata-driven governance and validation platform — Databricks + Unity Catalog + GitHub capstone project.

## Overview

This platform automates data governance validation across a Bronze → Silver → Gold pipeline on Databricks, governed by Unity Catalog. It surfaces data health through two deliverables:

- **AI Metadata Assistant** — a Genie-based conversational assistant that answers structural and quality questions, flags non-compliance, and recommends fixes
- **Governance Dashboard** — a stakeholder-facing view showing completeness %, maturity distribution, and PII/stewardship coverage

Both deliverables read only from the Gold layer, so they always agree on shared metrics.

## Team & Ownership

| Workstream | Owner |
| Metadata & Governance Logic | Naman Dewan |
| Data Engineering (Bronze/Silver/Gold, CI/CD) | Anirudh Uppili Mukundan |
| AI Metadata Assistant | Kabir Gulati |
| Governance Dashboard | Shanaya Mehra |


## Folder Structure

- `pipelines/` — Bronze → Silver → Gold data pipeline code (ingestion, transformation, validation logic)
- `assistant/` — AI Metadata Assistant (Genie-based conversational interface)
- `dashboard/` — Governance Dashboard (stakeholder-facing UI and metrics)
- `ci-cd/` — GitHub Actions workflows and Databricks Asset Bundle configs
- `docs/` — Supporting documentation, architecture notes, and diagrams

## Workflow

- All changes go through a pull request — no direct pushes to `main`
- Every PR requires at least one review from another team member
- Branch protection is enforced on `main`

## Timeline

Two-week sprint. See `docs/` for the full Day 1–14 schedule and milestones. 
