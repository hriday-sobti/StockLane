"""End-to-End Orchestrator Pipeline for StockLane.
Executes the full 26-stage analytical pipeline:
  1. Load Configuration
  2. Generate Synthetic Dimensions
  3. Generate Synthetic Latent Demand
  4. Simulate Inventory, Sales, Replenishments, Transfers
  5. Inject Controlled Raw Anomalies
  6. Validate Raw Data & Quarantine Bad Records
  7. Produce Cleaned & Validated Datasets
  8. Initialize PostgreSQL / DuckDB Schemas
  9. Load Core Relational Tables
  10. Execute Analytical SQL Views
  11. Feature Engineering & Chronological Forecast Evaluation
  12. Generate 14-Day Production Forecasts
  13. Calculate Inventory Health, Safety Stock, Reorder Point
  14. Evaluate Stockout & Overstock Risk
  15. Generate Constrained Replenishment Recommendations
  16. Execute Explainable Greedy Redistribution Engine
  17. Run Intervention Impact Simulation
  18. Run Demand Stress Scenarios (+10% to +50%)
  19. Root-Cause Analysis Classification
  20. Assemble Prioritized Action Queue
  21. Reconcile Cross-Layer KPIs (Python vs SQL vs BI)
  22. Export Power BI Analytical Datasets
  23. Generate Executive Summary & Fact Sheet
"""
import sys
import time
from pathlib import Path
import pandas as pd

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from python.common.config import load_config
from python.common.logger import setup_logger
from python.generation.generate_dimensions import generate_dimensions
from python.generation.generate_demand import generate_demand
from python.generation.simulate_inventory import simulate_sales_and_inventory
from python.validation.data_validator import inject_raw_anomalies, validate_and_quarantine
from python.database.db_manager import DatabaseManager
from python.forecasting.forecast_engine import run_forecasting_pipeline
from python.inventory.inventory_health import calculate_inventory_health_and_risk
from python.replenishment.replenishment_engine import generate_replenishment_recommendations
from python.redistribution.redistribution_engine import run_redistribution_engine
from python.simulation.scenario_engine import simulate_intervention_impact, run_scenario_simulator, classify_root_causes
from python.inventory.action_queue import build_action_queue
from python.reporting.reconciliation import reconcile_kpis
from powerbi.export_powerbi import export_powerbi_tables

logger = setup_logger("StockLanePipeline")

def run_pipeline():
    start_time = time.time()
    logger.info("==================================================")
    logger.info("Starting StockLane Analytical Pipeline Execution")
    logger.info("==================================================")
    
    # Stage 1: Load configuration
    logger.info("[01/22] Loading centralized configuration...")
    config = load_config()
    
    # Stage 2: Generate dimensions
    logger.info("[02/22] Generating synthetic dimensions (Cities, Stores, SKUs, Dates, Events, Promotions)...")
    dimensions = generate_dimensions(config)
    logger.info(f"Generated {len(dimensions['dim_city'])} cities, {len(dimensions['dim_store'])} stores, {len(dimensions['dim_product'])} SKUs, {len(dimensions['dim_date'])} dates.")
    
    # Stage 3: Generate demand
    logger.info("[03/22] Generating synthetic latent demand engine (Velocity, Seasonality, Events, Noise)...")
    df_demand = generate_demand(dimensions, config)
    logger.info(f"Generated {len(df_demand):,} latent demand observations.")
    
    # Stage 4: Simulate inventory and operations
    logger.info("[04/22] Simulating daily inventory progression, sales fulfillment, disruptions, and replenishments...")
    df_sales, df_inventory, df_replenishment, df_transfers, df_sales_plan = simulate_sales_and_inventory(dimensions, df_demand, config)
    logger.info(f"Simulated {len(df_sales):,} sales rows and {len(df_inventory):,} inventory tracking records.")
    
    # Stage 5: Inject raw anomalies
    logger.info("[05/22] Injecting controlled anomalies into raw staging layer...")
    raw_sales, raw_inv = inject_raw_anomalies(df_sales, df_inventory, config)
    
    # Stage 6: Validate & Quarantine
    logger.info("[06/22] Running data validation engine and isolating invalid records into quarantine...")
    clean_dict, quarantine_dict, val_report = validate_and_quarantine(
        dimensions, raw_sales, raw_inv, df_demand, df_replenishment, df_transfers, df_sales_plan
    )
    logger.info(f"Validation complete. Quarantined {val_report['quarantined_sales_rows']} sales rows and {val_report['quarantined_inventory_rows']} inventory rows.")
    
    # Save raw, clean, and quarantine data
    raw_dir = Path(config["paths"]["raw_dir"])
    proc_dir = Path(config["paths"]["processed_dir"])
    quar_dir = Path(config["paths"]["quarantine_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    proc_dir.mkdir(parents=True, exist_ok=True)
    quar_dir.mkdir(parents=True, exist_ok=True)
    
    clean_sales = clean_dict["fact_sales"]
    clean_inv = clean_dict["fact_inventory"]
    
    # Stage 7: Initialize Database & Load Core Tables
    logger.info("[07/22] Initializing relational database and loading dimension & fact tables...")
    db_mgr = DatabaseManager(config)
    db_mgr.initialize_schema()
    
    for dim_name, df_dim in dimensions.items():
        db_mgr.load_table("core", dim_name, df_dim)
    for fact_name, df_fact in clean_dict.items():
        db_mgr.load_table("core", fact_name, df_fact)
        
    # Stage 8: Create Analytical SQL Views
    logger.info("[08/22] Creating analytical SQL views (window functions, rolling velocity, DoC, risk)...")
    sql_views_path = project_root / "sql" / "views" / "02_analytical_views.sql"
    with open(sql_views_path, "r", encoding="utf-8") as f:
        sql_views_content = f.read()
    # Execute view creation statements
    for stmt in sql_views_content.split(";"):
        if stmt.strip():
            db_mgr.execute_sql(stmt)
    logger.info("Analytical SQL views successfully deployed.")
    
    # Stage 9: Forecasting Evaluation & Production Forecasts
    logger.info("[09/22] Running time-series feature engineering and chronological holdout validation...")
    benchmark_results, df_forecast = run_forecasting_pipeline(df_demand, config)
    logger.info(f"Forecasting evaluated. Best model selected: {benchmark_results['selected_best_model']} with WAPE: {benchmark_results[benchmark_results['selected_best_model']]['WAPE']*100:.2f}%.")
    
    # Stage 10: Inventory Health & Risk Engine
    logger.info("[10/22] Calculating inventory health, safety stock (Z=1.645), ROP, and stockout risk score (0-100)...")
    df_health = calculate_inventory_health_and_risk(dimensions, clean_inv, df_forecast, config)
    
    # Stage 11: Constrained Replenishment Engine
    logger.info("[11/22] Generating constrained replenishment recommendations (MOQ, Case Packs, Capacity Buffer)...")
    df_repl_queue = generate_replenishment_recommendations(df_health, config)
    logger.info(f"Generated {len(df_repl_queue)} prioritized replenishment recommendations.")
    
    # Stage 12: Greedy Redistribution Engine
    logger.info("[12/22] Running explainable greedy redistribution engine (Surplus Store -> Impending Shortage Store)...")
    df_transfers_rec = run_redistribution_engine(dimensions, df_health, config)
    logger.info(f"Identified {len(df_transfers_rec)} feasible inter-store redistribution opportunities.")
    
    # Stage 13: Intervention Simulation
    logger.info("[13/22] Simulating intervention impact (Before vs After availability, stockout hours, avoided lost sales)...")
    impact_summary = simulate_intervention_impact(df_health, df_repl_queue, df_transfers_rec)
    logger.info(f"Intervention simulation: Avoids ${impact_summary['total_simulated_lost_sales_avoided']:,.2f} in projected lost sales.")
    
    # Stage 14: Demand Stress Scenarios
    logger.info("[14/22] Running stress-testing scenario simulator (+10% to +50% demand shock)...")
    df_scenarios = run_scenario_simulator(df_health)
    
    # Stage 15: Root Cause Classification
    logger.info("[15/22] Classifying historical root causes of stockout episodes...")
    df_root_causes = classify_root_causes(clean_sales, clean_inv, df_replenishment, dimensions)
    
    # Stage 16: Action Queue Assembly
    logger.info("[16/22] Assembling consolidated operational action queue...")
    df_action_queue = build_action_queue(df_health, df_repl_queue, df_transfers_rec)
    logger.info(f"Action queue assembled with {len(df_action_queue)} prioritized items.")
    
    # Stage 17: KPI Reconciliation
    logger.info("[17/22] Reconciling authoritative KPIs across Python, SQL, and Power BI...")
    recon_results = reconcile_kpis(clean_sales, clean_inv, df_replenishment, db_mgr)
    logger.info(f"Reconciliation status: {'ALL PASS' if recon_results['all_metrics_reconciled'] else 'WARNING: Mismatch'}")
    
    # Stage 18: Power BI Exports
    logger.info("[18/22] Exporting clean analytical datasets for Power BI operational dashboards...")
    export_powerbi_tables(dimensions, df_health, df_repl_queue, df_transfers_rec, df_action_queue, df_scenarios, df_root_causes, config)
    
    # Stage 19: Generate Executive Findings & Fact Sheet
    logger.info("[19/22] Generating fact sheet and validation reports...")
    elapsed = time.time() - start_time
    
    fact_sheet = {
        "Cities": len(dimensions["dim_city"]),
        "Stores": len(dimensions["dim_store"]),
        "SKUs": len(dimensions["dim_product"]),
        "Simulation_Days": len(dimensions["dim_date"]),
        "Total_Sales_Observations": len(clean_sales),
        "Overall_Availability_Pct": recon_results["metrics"]["Availability_Percent"]["Python"],
        "Overall_Fill_Rate_Pct": recon_results["metrics"]["Fill_Rate_Percent"]["Python"],
        "Stockout_Rate_Pct": recon_results["metrics"]["Stockout_Rate_Percent"]["Python"],
        "Total_Fulfilled_Revenue": recon_results["metrics"]["Total_Revenue"]["Python"],
        "Total_Lost_Units": recon_results["metrics"]["Total_Cancelled_Units"]["Python"],
        "Selected_Forecast_Model": benchmark_results["selected_best_model"],
        "Forecast_WAPE_Pct": round(benchmark_results[benchmark_results["selected_best_model"]]["WAPE"] * 100.0, 2),
        "Forecast_MAE": benchmark_results[benchmark_results["selected_best_model"]]["MAE"],
        "Forecast_RMSE": benchmark_results[benchmark_results["selected_best_model"]]["RMSE"],
        "Critical_Risk_SKUs_Current": int((df_health["stockout_risk_score"] >= 80).sum()),
        "High_Risk_SKUs_Current": int((df_health["stockout_risk_score"] >= 60).sum()),
        "Replenishment_Recommendations_Count": len(df_repl_queue),
        "Redistribution_Transfer_Opportunities": len(df_transfers_rec),
        "Simulated_Lost_Sales_Avoided": impact_summary["total_simulated_lost_sales_avoided"],
        "Pipeline_Runtime_Seconds": round(elapsed, 2)
    }
    
    # Write Executive Summary
    rep_dir = Path(config["paths"]["reports_dir"])
    rep_dir.mkdir(parents=True, exist_ok=True)
    
    with open(rep_dir / "fact_sheet.yaml", "w", encoding="utf-8") as f:
        import yaml
        yaml.dump(fact_sheet, f, sort_keys=False)
        
    logger.info("==================================================")
    logger.info(f"Pipeline finished successfully in {elapsed:.2f} seconds!")
    logger.info("==================================================")
    return fact_sheet, recon_results

if __name__ == "__main__":
    run_pipeline()
