Architecture snapshot
=====================

Layers
------

- Raw sources: Kaggle (batch files), EGX website (stream via scraper)
- Bronze: S3 bucket with partitions (by dt, symbol)
- Silver: cleaned, typed datasets (Spark Structured Streaming + batch)
- Gold: Snowflake marts (facts/dimensions) for BI

Tools
-----

- Kafka for streaming ingestion
- Spark for streaming transforms
- dbt for batch transforms and tests
- Airflow for orchestration
- Docker for local environment and packaging

Data model (initial)
--------------------

- fact_trades(symbol_id, ts, price, volume, trade_id, source)
- dim_symbol(symbol_id, ticker, name, sector)
- dim_calendar(date_key, date, is_trading_day, week, month, year)

Quality gates
-------------

- Freshness on critical sources
- Uniqueness of trade_id within symbol per day
- Non-null price/volume with valid ranges
