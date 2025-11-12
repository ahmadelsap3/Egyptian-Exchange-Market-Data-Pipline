Egyptian Exchange Market Data Pipeline
=====================================

A graduation project to build an end‑to‑end data platform for EGX (Egyptian Exchange) market analytics. The pipeline ingests batch data (Kaggle) and near‑real‑time data (web scraping EGX), lands it in a Bronze layer (S3), transforms to Silver using Spark/dbt, and serves analytics in a Gold layer on Snowflake for dashboards.

## Team Members
Ahmed Elsaba (@ahmadelsap3), Karim Yasser, Aalaa Hamam, Ahmed Arnos, Eslam Shatto

Architecture overview
---------------------

- Extract: Kaggle datasets (batch) and EGX website stream (web scraping) → Kafka (stream)
- Load (Bronze): Land raw/ingested data into S3 with partitioning
- Transform (Silver):
  - Streaming: Spark Structured Streaming from Kafka → Silver
  - Batch: dbt transformations for curated models
- Serve (Gold): Snowflake as the data warehouse for BI
- Orchestrate: Apache Airflow
- Containerize: Docker

Branching model
---------------

- main: production (release‑ready). Protected branch.
- dev-test: integration branch for collaborative development and testing. All feature branches merge here via PRs.

Typical flow
------------

1. Create a feature branch from dev-test: `feature/<scope>-<short-title>`
2. Open a PR to dev-test; require 2 approvals and green checks.
3. Merge to dev-test; smoke test via Airflow/docker locally.
4. Promote to main via a release PR.

Getting started
---------------

1. Copy `.env.example` to `.env` and set required secrets.
2. Read `docs/PROJECT_PLAN.md` and `docs/CONTRIBUTION_WORKFLOW.md` to align on tasks and conventions.
3. Use the provided directory structure as placeholders until components are implemented.

Docs
----

- docs/PROJECT_PLAN.md – timeline, milestones, and shared work plan for five teammates.
- docs/CONTRIBUTION_WORKFLOW.md – branching, PR, commit conventions, and review checklist.
- docs/ARCHITECTURE.md – layers and data model at a glance.

Credits and reference
---------------------

We’ll use ideas and structure inspired by `@Deathslayer89/DTC_dataEngg/files/Stock-market-analytics` as a reference implementation.

---
*Last Updated: 2025-11-12*
