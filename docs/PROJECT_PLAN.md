Project Plan and Team Collaboration
==================================

Team: Ahmed Elsaba, Karim Yasser, Alaa Hamam, Ahmed Arnos, Eslam Shatto

Working together (no single-owner tasks)
---------------------------------------

- Pair/mob rotation: always work in pairs, rotate pairs daily. One day per week, do a 60–90 min mob session to align on tricky parts.
- Thin vertical slices: each "feature" spans extract → bronze → transform → serve. Keep PRs small (<400 LOC) and merge often.
- Definition of Done: code + tests + docs + run locally via docker-compose + PR approvals (2) + passing checks.

Branches and releases
---------------------

- Feature branches → PR to `dev-test` → integration testing → release PR to `main`.
- Tag releases on `main` as v0.x.y.

Milestones (suggested 10–12 weeks)
----------------------------------

Week 1–2: Foundations

- Repo scaffolding, .env, .gitignore, PR templates, contribution workflow
- Decide cloud account ownership and costs; choose S3-compatible storage (AWS S3 or MinIO locally)

Week 3–4: Ingestion layer

- Kaggle batch extractor with data catalog
- Kafka + scraper PoC for EGX website → topic `egx_ticks`

Week 5–6: Bronze/Silver

- S3 bucket layout and partitions
- Spark Structured Streaming job (Kafka → Parquet in Silver)
- dbt project bootstrap with sources and first staging models

Week 7–8: Warehouse and orchestration

- Snowflake schemas (BRONZE/SILVER/GOLD), stages, file formats
- dbt marts (fact_trades, dim_symbol, dim_calendar) with tests
- Airflow DAGs: batch ingest, dbt runs, daily maintenance

Week 9: Data quality and observability

- dbt tests + Great Expectations (optional)
- Central logging, error handling, basic alerts

Week 10: Dashboards and polish

- Power BI (or alternative) dashboards: price trends, volume heatmap, top movers
- Backfills, README/docs polish, demo script

Risks and mitigations
---------------------

- EGX scraping instability → cache pages, exponential backoff, respect robots.txt and legal constraints
- Costs → use small Snowflake warehouse for dev; sample data in dev-test
- Team bandwidth → keep slices small; daily 10–15 min sync; use issues to track blockers
