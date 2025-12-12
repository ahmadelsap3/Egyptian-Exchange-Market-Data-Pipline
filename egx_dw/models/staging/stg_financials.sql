{{
  config(
    materialized='incremental',
    unique_key=['company_id', 'quarter']
  )
}}

-- Staging for financial statements from FINANCE_RAW (JSON) joined with stg_companies
WITH financials AS (
    SELECT
        RAW:_ingest_symbol::STRING as symbol,
        RAW:quarter::DATE as quarter,
        RAW:fiscal_year::INTEGER as fiscal_year,
        RAW:fiscal_quarter::INTEGER as fiscal_quarter,
        RAW:total_revenue::FLOAT as total_revenue,
        RAW:gross_profit::FLOAT as gross_profit,
        RAW:net_income::FLOAT as net_income,
        RAW:eps::FLOAT as eps,
        RAW:operating_expense::FLOAT as operating_expense,
        RAW:total_assets::FLOAT as total_assets,
        RAW:total_liabilities::FLOAT as total_liabilities,
        RAW:free_cash_flow::FLOAT as free_cash_flow,
        LOAD_TS as ingested_at
    FROM {{ source('operational', 'FINANCE_RAW') }}
),

companies AS (
    SELECT * FROM {{ ref('stg_companies') }}
)

SELECT 
    -- surrogate key generation could happen here if needed, but using natural keys for now
    c.symbol,
    c.company_name,
    c.sector,
    f.quarter,
    f.fiscal_year,
    f.fiscal_quarter,
    COALESCE(f.total_revenue, 0) as total_revenue,
    COALESCE(f.gross_profit, 0) as gross_profit,
    COALESCE(f.net_income, 0) as net_income,
    COALESCE(f.eps, 0) as eps,
    COALESCE(f.operating_expense, 0) as operating_expense,
    COALESCE(f.total_assets, 0) as total_assets,
    COALESCE(f.total_liabilities, 0) as total_liabilities,
    COALESCE(f.free_cash_flow, 0) as free_cash_flow,
    -- Derived metrics
    CASE 
        WHEN COALESCE(f.total_revenue, 0) > 0 THEN (COALESCE(f.gross_profit, 0) / f.total_revenue) * 100 
        ELSE 0
    END as gross_margin_pct,
    CASE 
        WHEN f.total_revenue > 0 THEN (f.net_income / f.total_revenue) * 100 
        ELSE NULL 
    END as net_margin_pct,
    CASE 
        WHEN f.total_assets > 0 THEN (f.net_income / f.total_assets) * 100 
        ELSE NULL 
    END as roa_pct,
    CASE
        WHEN f.total_liabilities > 0 
        THEN f.total_assets / f.total_liabilities
        ELSE NULL
    END as debt_to_asset_ratio,
    f.ingested_at,
    CURRENT_TIMESTAMP() as updated_at
FROM financials f
LEFT JOIN companies c ON f.symbol = c.symbol
WHERE f.quarter IS NOT NULL
{% if is_incremental() %}
  AND f.ingested_at > (SELECT COALESCE(MAX(ingested_at), '1900-01-01'::timestamp) FROM {{ this }})
{% endif %}
