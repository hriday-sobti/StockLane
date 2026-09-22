import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from python.common.config import load_config
from python.inventory.inventory_health import calculate_inventory_health_and_risk
from python.replenishment.replenishment_engine import generate_replenishment_recommendations
from python.redistribution.redistribution_engine import run_redistribution_engine
from python.simulation.scenario_engine import run_scenario_simulator

def build_excel_scenario_model():
    cfg = load_config()
    export_path = "reports/stocklane_scenario_model.xlsx"
    os.makedirs("reports", exist_ok=True)
    
    # Read core analytical exports
    health_df = pd.read_csv("powerbi/exports/pbi_fact_inventory_health.csv")
    scen_df = pd.read_csv("powerbi/exports/pbi_scenario_stress_testing.csv")
    action_df = pd.read_csv("powerbi/exports/pbi_fact_action_queue.csv")
    redist_df = pd.read_csv("powerbi/exports/pbi_fact_redistribution_recommendations.csv")
    repl_df = pd.read_csv("powerbi/exports/pbi_fact_replenishment_queue.csv")
    
    with pd.ExcelWriter(export_path, engine="openpyxl") as writer:
        scen_df.to_excel(writer, sheet_name="Stress_Scenarios", index=False)
        action_df.head(100).to_excel(writer, sheet_name="Top_Action_Queue", index=False)
        redist_df.head(100).to_excel(writer, sheet_name="Redistribution_Transfers", index=False)
        repl_df.head(100).to_excel(writer, sheet_name="Replenishment_Orders", index=False)
        health_df[["store_name", "sku_name", "category", "closing_stock", "safety_stock", "reorder_point", "days_of_cover", "hours_to_stockout", "stockout_risk_score", "risk_level"]].head(200).to_excel(writer, sheet_name="Inventory_Health_Sample", index=False)
        
    print(f"Generated Excel scenario model: {export_path}")

if __name__ == "__main__":
    build_excel_scenario_model()
