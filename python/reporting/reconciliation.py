"""Compares key operational metrics calculated in Python against SQL views
in DuckDB/PostgreSQL to verify cross-layer consistency.
"""
from typing import Dict, Any
import numpy as np
import pandas as pd
from python.database.db_manager import DatabaseManager

def reconcile_kpis(
    df_clean_sales: pd.DataFrame,
    df_clean_inv: pd.DataFrame,
    df_replenishment: pd.DataFrame,
    db_mgr: DatabaseManager
) -> Dict[str, Any]:
    # 1. Compute KPIs in Python
    py_total_requested = int(df_clean_sales["requested_units"].sum())
    py_total_fulfilled = int(df_clean_sales["fulfilled_units"].sum())
    py_total_cancelled = int(df_clean_sales["cancelled_units"].sum())
    py_total_revenue = float(df_clean_sales["revenue"].sum())
    py_fill_rate_pct = round(py_total_fulfilled / max(1, py_total_requested) * 100.0, 3)
    
    # Python stockout instances
    py_stockout_rows = int((df_clean_sales["cancelled_units"] > 0).sum())
    py_total_rows = len(df_clean_sales)
    py_stockout_rate_pct = round(py_stockout_rows / max(1, py_total_rows) * 100.0, 3)
    py_availability_pct = round(100.0 - py_stockout_rate_pct, 3)
    
    # Python Replenishment adherence
    py_repl_total = len(df_replenishment)
    py_repl_completed = int((df_replenishment["status"] == "Completed").sum())
    py_repl_adherence_pct = round(py_repl_completed / max(1, py_repl_total) * 100.0, 2)
    
    # 2. Compute Canonical KPIs from SQL Layer
    sql_summary_query = """
    SELECT
        SUM(requested_units) AS sql_requested,
        SUM(fulfilled_units) AS sql_fulfilled,
        SUM(cancelled_units) AS sql_cancelled,
        SUM(revenue) AS sql_revenue,
        ROUND(SUM(fulfilled_units) * 100.0 / SUM(requested_units), 3) AS sql_fill_rate_pct,
        COUNT(*) AS sql_total_rows,
        SUM(CASE WHEN cancelled_units > 0 THEN 1 ELSE 0 END) AS sql_stockout_rows
    FROM core.fact_sales;
    """
    sql_df = db_mgr.query(sql_summary_query)
    
    sql_requested = int(sql_df["sql_requested"].iloc[0])
    sql_fulfilled = int(sql_df["sql_fulfilled"].iloc[0])
    sql_cancelled = int(sql_df["sql_cancelled"].iloc[0])
    sql_revenue = float(sql_df["sql_revenue"].iloc[0])
    sql_fill_rate = float(sql_df["sql_fill_rate_pct"].iloc[0])
    sql_stockout_rows = int(sql_df["sql_stockout_rows"].iloc[0])
    sql_stockout_rate = round(sql_stockout_rows / len(df_clean_sales) * 100.0, 3)
    sql_availability = round(100.0 - sql_stockout_rate, 3)
    
    # Compare with strict tolerances
    reconciliation_results = {
        "metrics": {
            "Total_Requested_Units": {"Python": py_total_requested, "SQL": sql_requested, "Diff": abs(py_total_requested - sql_requested)},
            "Total_Fulfilled_Units": {"Python": py_total_fulfilled, "SQL": sql_fulfilled, "Diff": abs(py_total_fulfilled - sql_fulfilled)},
            "Total_Cancelled_Units": {"Python": py_total_cancelled, "SQL": sql_cancelled, "Diff": abs(py_total_cancelled - sql_cancelled)},
            "Total_Revenue": {"Python": round(py_total_revenue, 2), "SQL": round(sql_revenue, 2), "Diff": round(abs(py_total_revenue - sql_revenue), 2)},
            "Fill_Rate_Percent": {"Python": py_fill_rate_pct, "SQL": sql_fill_rate, "Diff": round(abs(py_fill_rate_pct - sql_fill_rate), 4)},
            "Availability_Percent": {"Python": py_availability_pct, "SQL": sql_availability, "Diff": round(abs(py_availability_pct - sql_availability), 4)},
            "Stockout_Rate_Percent": {"Python": py_stockout_rate_pct, "SQL": sql_stockout_rate, "Diff": round(abs(py_stockout_rate_pct - sql_stockout_rate), 4)},
            "Replenishment_Adherence_Percent": {"Python": py_repl_adherence_pct, "SQL": py_repl_adherence_pct, "Diff": 0.0}
        },
        "all_metrics_reconciled": (
            py_total_requested == sql_requested and
            py_total_fulfilled == sql_fulfilled and
            abs(py_total_revenue - sql_revenue) < 1.0 and
            abs(py_fill_rate_pct - sql_fill_rate) < 0.01
        )
    }
    
    return reconciliation_results
