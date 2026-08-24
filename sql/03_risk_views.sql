CREATE OR REPLACE VIEW vw_risk_alerts AS

SELECT
    SHA2(
        CONCAT(
            week_start,
            product,
            company
        ),
        256
    ) AS alert_id,

    week_start AS alert_date,
    product,
    company,
    complaint_count AS current_value,

    ROUND(
        rolling_4_week_average,
        2
    ) AS baseline_value,

    week_over_week_growth,
    anomaly_z_score,
    alert_level,

    CONCAT(
        company,
        ' recorded ',
        complaint_count,
        ' ',
        product,
        ' complaints versus a baseline of ',
        ROUND(rolling_4_week_average, 2),
        '. Weekly growth was ',
        week_over_week_growth,
        '%.'
    ) AS alert_explanation

FROM vw_company_risk_signals

WHERE data_status = 'Complete'
  AND baseline_weeks >= 3
  AND complaint_count >= 20
   AND DATE_ADD(week_start, INTERVAL 6 DAY) <=
      DATE_SUB(
          (
              SELECT MAX(complaint_date)
              FROM vw_daily_product_metrics
          ),
          INTERVAL 21 DAY
      )

  AND alert_level IN (
      'Watch',
      'Warning',
      'Critical'
  );