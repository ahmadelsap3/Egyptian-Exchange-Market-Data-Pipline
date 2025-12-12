{{
  config(
    materialized='incremental',
    unique_key=['symbol', 'trade_date', 'data_source']
  )
}}

-- Unified staging from PRICES_RAW (JSON) joined with stg_companies
WITH prices AS (
    SELECT
        RAW:_ingest_symbol::STRING as symbol,
        RAW:trade_date::DATE as trade_date,
        RAW:open::FLOAT as open_price,
        RAW:high::FLOAT as high_price,
        RAW:low::FLOAT as low_price,
        RAW:close::FLOAT as close_price,
        RAW:volume::INTEGER as volume,
        LOAD_TS as ingested_at
    FROM {{ source('operational', 'PRICES_RAW') }}
),

companies AS (
    SELECT * FROM {{ ref('stg_companies') }}
)

SELECT 
    p.symbol,
    c.company_name,
    c.sector,
    p.trade_date,
    COALESCE(p.open_price, p.close_price) as open_price,
    COALESCE(p.high_price, p.close_price) as high_price,
    COALESCE(p.low_price, p.close_price) as low_price,
    p.close_price,
    COALESCE(p.volume, 0) as volume,
    'BATCH_S3' as data_source,
    p.ingested_at,
    CURRENT_TIMESTAMP() as updated_at
FROM prices p
LEFT JOIN companies c ON p.symbol = c.symbol
WHERE p.trade_date IS NOT NULL
  AND p.close_price IS NOT NULL
{% if is_incremental() %}
  AND p.ingested_at > (SELECT COALESCE(MAX(ingested_at), '1900-01-01'::timestamp) FROM {{ this }})
{% endif %}
