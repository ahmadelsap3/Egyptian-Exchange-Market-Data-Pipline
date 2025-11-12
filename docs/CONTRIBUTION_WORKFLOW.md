Contribution Workflow
=====================

Branch strategy
---------------

- `main`: production, protected, only release PRs.
- `dev-test`: integration, all features merge here first.
- `feature/<scope>-<short-title>`: small vertical slices.

Commits
-------

- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`
- Keep commits focused; avoid large mixed changes.

Pull Requests
-------------

Checklist:

- Description: purpose + approach + test evidence (screenshots/logs)
- Linked issue (if exists)
- Self-review done
- Added/updated tests & docs
- No secrets committed
- CI green

Reviews
-------

- Minimum 2 approvals.
- Use comments for suggestions; request changes only for correctness/security/test coverage.
- Pair can co-author PR (`Co-authored-by:` trailers).

Issue tracking
--------------

- Use GitHub Issues with labels: `ingest`, `streaming`, `dbt`, `spark`, `airflow`, `infra`, `docs`, `quality`.
- Link PRs to issues via `Fixes #<id>` when closing.

Testing layers
--------------

- Unit: functions/classes (fast) – pytest.
- Integration: Kafka → S3, Spark transforms – docker-compose environment.
- Data quality: dbt tests & Great Expectations.
- End-to-end: Airflow DAG run.

Environment setup
-----------------

1. Copy `.env.example` → `.env`.
2. Run `docker compose up -d` (later when compose file exists).
3. Execute unit tests: `pytest -q`.

Releases
--------

- Open PR from `dev-test` → `main` titled `release: v0.x.y`.
- Tag after merge: `git tag v0.x.y && git push --tags`.

Security & secrets
------------------

- Never commit `.env` or credentials.
- Rotate keys quarterly.

Coding standards (initial)
--------------------------

- Python: black + flake8 + isort.
- SQL (dbt): uppercase keywords, snake_case identifiers.
- Logging: JSON structured logs with fields: `timestamp`, `level`, `service`, `event`.
