{{
  config(
    materialized='table'
  )
}}

-- Staging for company master data from RAW JSON
WITH source AS (
    SELECT 
        RAW:symbol::STRING as symbol,
        RAW:company_name::STRING as company_name,
        RAW:sector::STRING as sector,
        RAW:market_cap::FLOAT as market_cap,
        RAW:logo_url::STRING as logo_url,
        LOAD_TS as created_at
    FROM {{ source('operational', 'COMPANIES_RAW') }}
)

SELECT 
    symbol,
    COALESCE(company_name, 'Unknown Company') as company_name,
    COALESCE(sector, 'Unclassified') as sector,
    COALESCE(market_cap, 0) as market_cap,
    logo_url,
    created_at,
    CURRENT_TIMESTAMP() as updated_at
FROM source
WHERE symbol IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY created_at DESC) = 1
