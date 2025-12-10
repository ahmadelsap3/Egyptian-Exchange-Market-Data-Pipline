# Egyptian Exchange Market Data Pipeline

End-to-end data pipeline for Egyptian Stock Exchange (EGX) with batch processing, real-time streaming, and dbt transformations.

## Architecture

### Batch Pipeline (Historical Data)
```
Kaggle/S3 → AWS → Python Batch Processor → Snowflake (Bronze) 
    → dbt (Silver/Gold) → Power BI
```

### Streaming Pipeline (Real-Time Data)
```
Yahoo Finance API → Kafka → Apache Spark → TimescaleDB → Grafana
```

Both pipelines orchestrated with Apache Airflow + Docker.

## Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- Snowflake account
- AWS account (for S3)

### Setup

Clone and install dependencies:
```bash
git clone https://github.com/ahmadelsap3/Egyptian-Exchange-Market-Data-Pipline.git
cd Egyptian-Exchange-Market-Data-Pipline
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Start Streaming Pipeline
```bash
cd egx_streaming_pipeline
docker-compose up -d
```
Access Grafana dashboard: http://localhost:3000 (admin/admin)

### Run Batch Processing
```bash
python extract/batch_processor.py --bucket egx-data-bucket --since 7
```

### Run dbt Transformations
```bash
cd egyptian_stocks
dbt run
dbt test
```

## Components

### 1. Batch Processing
**Source**: `extract/batch_processor.py`
- Pulls CSV files from S3 or Kaggle
- Loads into Snowflake OPERATIONAL schema
- Scheduled daily via Airflow

### 2. Real-Time Streaming
**Location**: `egx_streaming_pipeline/`
- **Producer** (`producer/egx_producer.py`): Generates mock EGX data for 25 stocks + 4 indices
- **Kafka**: Message broker on port 9092
- **Spark Processor** (`spark-processor/egx_spark_job.py`): Stream processing with Spark 3.4.1
- **TimescaleDB**: PostgreSQL time-series database
- **Grafana**: Real-time dashboard with auto-refresh

Market hours: Sunday-Thursday 10:00-14:30 Cairo time

### 3. dbt Transformations
**Project**: `egyptian_stocks/`

**Staging Layer** (Bronze):
- `stg_companies.sql` - Company master data
- `stg_prices.sql` - Stock prices
- `stg_finance.sql` - Financial statements

**Silver Layer** (Dimensions & Facts):
- `dim_company.sql`, `dim_sector.sql`, `dim_industry.sql`, `dim_location.sql`, `dim_currency.sql`, `dim_date.sql`
- `fct_prices.sql` - Daily stock prices fact table
- `fct_financials.sql` - Financial metrics fact table

**Marts Layer** (Analytics):
- `company_overview.sql` - Company profiles with latest metrics
- `price_summary.sql` - Price analytics and trends

### 4. Orchestration
**Location**: `airflow/dags/`
- `egx_full_pipeline.py` - Main DAG running batch + dbt daily at 1 AM Cairo time
- `dbt_scheduled_transformations.py` - dbt-only transformations

## Project Structure

```
Egyptian-Exchange-Market-Data-Pipline/
├── airflow/
│   └── dags/
│       ├── egx_full_pipeline.py
│       └── dbt_scheduled_transformations.py
├── egx_streaming_pipeline/
│   ├── docker-compose.yml
│   ├── producer/
│   │   └── egx_producer.py
│   ├── spark-processor/
│   │   └── egx_spark_job.py
│   └── grafana/
│       └── dashboards/
│           └── egx-live.json
├── egyptian_stocks/
│   └── models/
│       ├── staging/
│       │   ├── stg_companies.sql
│       │   ├── stg_prices.sql
│       │   └── stg_finance.sql
│       ├── silver/
│       │   ├── dim_company.sql
│       │   ├── dim_sector.sql
│       │   ├── dim_industry.sql
│       │   ├── fct_prices.sql
│       │   └── fct_financials.sql
│       └── marts/
│           ├── company_overview.sql
│           └── price_summary.sql
├── extract/
│   ├── batch_processor.py
│   ├── meta_finance_scrape.py
│   ├── kaggle/
│   │   └── download_kaggle.py
│   └── aws/
│       └── connect_aws.py
├── scripts/
│   └── loaders/
│       ├── load_all_data_batch.py
│       ├── load_index_membership.py
│       └── load_market_stats.py
├── iam/
│   ├── bootstrap_admin.py
│   ├── create_bucket.sh
│   └── setup_aws_iam.sh
├── sql/
│   └── 00_create_database_from_scratch.sql
└── docs/
    ├── ARCHITECTURE.md
    └── EGX_INDICES.md
```

## Data Schema

### TimescaleDB (Streaming Pipeline)
**Database**: `egx_market`  
**Hypertable**: `egx_stock_prices`

```sql
CREATE TABLE egx_stock_prices (
    time TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10),
    company_name VARCHAR(255),
    price NUMERIC(10,2),
    price_change_percent NUMERIC(5,2),
    volume BIGINT,
    market_status VARCHAR(10),
    index_name VARCHAR(50)
);
```

### Snowflake (Batch Pipeline)
**Database**: `EGX_OPERATIONAL_DB`

**Schemas**:
- `OPERATIONAL` - Raw batch data from S3
- `BRONZE` - Staging models (egyptian_stocks dbt)
- `SILVER` - Dimensional models
- `MARTS` - Analytics views

**Main Tables**:
- `TBL_COMPANY` - Company master data
- `TBL_STOCK_PRICE` - Historical prices
- `TBL_FINANCIAL` - Financial statements
- `TBL_INDEX` - Market indices
- `TBL_INDEX_MEMBERSHIP` - Index constituents

## Configuration

### Environment Variables
```bash
# Snowflake
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH

# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# Kafka (Streaming)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### dbt Profile
`egyptian_stocks/profiles.yml`:
```yaml
egyptian_stocks:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: ACCOUNTADMIN
      database: EGX_OPERATIONAL_DB
      warehouse: COMPUTE_WH
      schema: BRONZE
      threads: 4
```

## Monitoring

### Streaming Pipeline
Check Docker services:
```bash
cd egx_streaming_pipeline
docker-compose ps
docker logs egx-producer -f
docker logs egx-spark-processor -f
```

Access UIs:
- Grafana: http://localhost:3000 (admin/admin)
- Kafka UI: http://localhost:8090
- pgAdmin: http://localhost:5050

Query TimescaleDB:
```bash
docker exec -it egx-timescaledb psql -U postgres -d egx_market
```

```sql
SELECT COUNT(*) FROM egx_stock_prices;
SELECT DISTINCT ON (ticker) * FROM egx_stock_prices ORDER BY ticker, time DESC;
```

### Batch Pipeline
Check Airflow:
- UI: http://localhost:8081 (admin/admin)
- View DAG runs, task logs, execution history

Query Snowflake:
```sql
-- Check recent batch data
SELECT 
    COUNT(*) as records,
    MAX(CREATED_AT) as latest_record
FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_STOCK_PRICE
WHERE CREATED_AT > DATEADD(hour, -24, CURRENT_TIMESTAMP());
```

### dbt
```bash
cd egyptian_stocks
dbt run
dbt test
dbt docs generate
dbt docs serve  # View docs at http://localhost:8080
```

## Troubleshooting

### Streaming Pipeline Issues
```bash
# Check all services
cd egx_streaming_pipeline
docker-compose ps

# Restart services
docker-compose restart

# View logs
docker logs egx-producer -f
docker logs egx-spark-processor -f
docker logs egx-kafka -f
```

### No Data in Grafana
1. Check TimescaleDB: `SELECT COUNT(*) FROM egx_stock_prices;`
2. Verify Grafana datasource: Configuration → Data sources
3. Check panel queries: Edit panel → Query inspector

### Batch Processing Errors
```bash
# Check S3 connection
aws s3 ls s3://egx-data-bucket

# Check Snowflake connection
python -c "import snowflake.connector; print('OK')"

# Run with debug
python extract/batch_processor.py --bucket egx-data-bucket --since 1
```

### dbt Errors
```bash
cd egyptian_stocks
dbt debug  # Check connection
dbt compile  # Check SQL compilation
dbt run --debug  # Verbose logging
```

### Airflow DAG Issues
- Check DAG is enabled in UI
- View task logs: Click task → View Log
- Check connections: Admin → Connections
- Verify environment variables in docker-compose

## AWS Setup

IAM scripts in `iam/`:
- `bootstrap_admin.py` - Create admin IAM user
- `create_team_users.sh` - Create team IAM users
- `create_bucket.sh` - Create S3 bucket with versioning
- `setup_aws_iam.sh` - Complete IAM setup

Policies:
- `egx_team_upload_policy.json` - S3 upload permissions for team
- `snowflake-s3-read-policy.json` - Snowflake S3 read access
- `snowflake-trust-policy.json` - Cross-account trust policy

## Documentation

- `docs/ARCHITECTURE.md` - System architecture details
- `docs/PROJECT_STRUCTURE.md` - Complete file structure
- `docs/CLEANUP.md` - Data cleanup procedures
- `docs/EGX_INDICES.md` - EGX market indices reference
- `egx_streaming_pipeline/README.md` - Streaming pipeline guide (500+ lines)
- `docs/dbt/DBT_COMPLETION_REPORT.md` - dbt implementation details

## Requirements

Python packages (`requirements.txt`):
- `requests`, `beautifulsoup4` - Web scraping
- `kaggle` - Kaggle dataset downloads
- `kafka-python` - Kafka producer/consumer
- `boto3` - AWS S3 operations
- `snowflake-connector-python` - Snowflake operations
- `dbt-core`, `dbt-snowflake` - dbt transformations
- `pandas`, `numpy` - Data processing
- `egxpy` - EGX API client (from GitHub)

## Team

Ahmad Elsayed - [@ahmadelsap3](https://github.com/ahmadelsap3)

---

Project Status: Operational
