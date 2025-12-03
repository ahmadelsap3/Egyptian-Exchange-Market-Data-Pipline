{{ config(
    materialized='view' 
) }}

WITH source_data AS (

    SELECT 
        -- الأعمدة اللي بتيجي مباشرة من الجدول الخام
        trade_date,
        stock_symbol,
        closing_price,
        open_price,
        high_price,
        low_price,
        
        -- تحويل عمود Volume وإعطائه الاسم النهائي
        -- استخدام CAST لضمان دقة الأرقام الكبيرة (المليارات)
        CAST(
            TRY_TO_NUMBER(REPLACE(REPLACE(volume, 'M', 'E6'), 'K', 'E3'))
            AS DECIMAL(38, 0) -- نوع رقمي يدعم الأرقام الصحيحة الكبيرة
        ) AS volume,
        
        -- تحويل عمود Change % وإعطائه الاسم النهائي
        -- استخدام CAST لضمان دقة الأرقام العشرية السالبة والموجبة
       CAST(
            ((REPLACE(change_percent, '%', '')) / 100)
            AS DECIMAL(18, 6)
        ) AS change_pct
    



    FROM {{ source('egx_raw', 'egx30_history_data') }} 
)

SELECT * FROM source_data



