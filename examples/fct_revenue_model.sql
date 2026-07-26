-- ============================================================
-- Synex AI — Sample Generated dbt SQL Model
-- Dataset:   prod.sales.fct_revenue
-- Dialect:   Snowflake
-- Generated: by GPT-4o via OpenRouter, grounded in DataHub metadata
-- PII Cols:  customer_email, customer_phone (SHA2-256 masked)
-- ============================================================

WITH source AS (

    -- Pull from the canonical staging layer resolved via DataHub lineage
    SELECT * FROM {{ ref('stg_orders') }}

),

masked AS (

    SELECT
        order_id,
        order_date,
        order_status,

        -- Governance: SHA2-256 applied to Tier-1 PII fields (DataHub tag: urn:li:tag:PII)
        SHA2(customer_email, 256)   AS customer_email_hashed,
        SHA2(customer_phone, 256)   AS customer_phone_hashed,

        -- Non-PII business fields — no masking required
        product_id,
        product_category,
        quantity,
        unit_price,

        -- Derived revenue metric
        quantity * unit_price        AS gross_revenue_usd,

        -- Lineage audit columns
        _loaded_at,
        _source_system

    FROM source
    WHERE order_status != 'CANCELLED'    -- Exclude cancelled rows per business rule

),

final AS (

    SELECT
        *,
        -- 7-day rolling average of gross revenue (partition by product_category)
        AVG(gross_revenue_usd) OVER (
            PARTITION BY product_category
            ORDER BY order_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS revenue_7d_rolling_avg,

        -- Row-level audit
        CURRENT_TIMESTAMP()             AS dbt_updated_at

    FROM masked

)

SELECT * FROM final
