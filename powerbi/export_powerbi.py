"""Power BI Analytical Data Model, Measure Generator, and Exporter.
Exports cleanly partitioned analytical tables for Power BI:
  1. pbi_dim_date.csv
  2. pbi_dim_store.csv
  3. pbi_dim_product.csv
  4. pbi_dim_city.csv
  5. pbi_fact_inventory_health.csv (Latest snapshot for Command Center & Risk)
  6. pbi_fact_redistribution_recommendations.csv
  7. pbi_fact_replenishment_queue.csv
  8. pbi_fact_action_queue.csv
  9. pbi_scenario_stress_testing.csv
  10. pbi_root_cause_analysis.csv
"""
import os
from pathlib import Path
from typing import Dict, Any
import pandas as pd

def export_powerbi_tables(
    dimensions: Dict[str, pd.DataFrame],
    df_health: pd.DataFrame,
    df_repl_queue: pd.DataFrame,
    df_transfers: pd.DataFrame,
    df_action_queue: pd.DataFrame,
    df_scenarios: pd.DataFrame,
    df_root_causes: pd.DataFrame,
    config: Dict[str, Any]
):
    export_dir = Path(config.get("paths", {}).get("powerbi_dir", "powerbi/exports"))
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Dimensions
    dimensions["dim_date"].to_csv(export_dir / "pbi_dim_date.csv", index=False)
    dimensions["dim_store"].to_csv(export_dir / "pbi_dim_store.csv", index=False)
    dimensions["dim_product"].to_csv(export_dir / "pbi_dim_product.csv", index=False)
    dimensions["dim_city"].to_csv(export_dir / "pbi_dim_city.csv", index=False)
    
    # Analytical Fact Exports
    df_health.to_csv(export_dir / "pbi_fact_inventory_health.csv", index=False)
    df_repl_queue.to_csv(export_dir / "pbi_fact_replenishment_queue.csv", index=False)
    df_transfers.to_csv(export_dir / "pbi_fact_redistribution_recommendations.csv", index=False)
    df_action_queue.to_csv(export_dir / "pbi_fact_action_queue.csv", index=False)
    df_scenarios.to_csv(export_dir / "pbi_scenario_stress_testing.csv", index=False)
    if not df_root_causes.empty:
        df_root_causes.to_csv(export_dir / "pbi_root_cause_analysis.csv", index=False)
        
    return export_dir
