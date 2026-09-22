"""Power BI Semantic Model Schema and Relationship Definition.
Describes the exact Star Schema relationships, table cardinalities, and cross-filter directions
for loading the exported CSVs into Power BI Desktop or Fabric.
"""
from typing import List, Dict

STAR_SCHEMA_RELATIONSHIPS: List[Dict[str, str]] = [
    # 1. Fact Inventory Health (Latest Snapshot)
    {
        "from_table": "pbi_fact_inventory_health",
        "from_column": "sku_id",
        "to_table": "pbi_dim_product",
        "to_column": "sku_id",
        "cardinality": "ManyToOne",
        "cross_filter": "Single"
    },
    {
        "from_table": "pbi_fact_inventory_health",
        "from_column": "store_id",
        "to_table": "pbi_dim_store",
        "to_column": "store_id",
        "cardinality": "ManyToOne",
        "cross_filter": "Single"
    },
    {
        "from_table": "pbi_fact_inventory_health",
        "from_column": "date_key",
        "to_table": "pbi_dim_date",
        "to_column": "date_key",
        "cardinality": "ManyToOne",
        "cross_filter": "Single"
    },
    # 2. Store to City Dimension Hierarchy
    {
        "from_table": "pbi_dim_store",
        "from_column": "city_id",
        "to_table": "pbi_dim_city",
        "to_column": "city_id",
        "cardinality": "ManyToOne",
        "cross_filter": "Single"
    },
    # 3. Fact Replenishment Queue
    {
        "from_table": "pbi_fact_replenishment_queue",
        "from_column": "sku_id",
        "to_table": "pbi_dim_product",
        "to_column": "sku_id",
        "cardinality": "ManyToOne",
        "cross_filter": "Single"
    },
    {
        "from_table": "pbi_fact_replenishment_queue",
        "from_column": "store_id",
        "to_table": "pbi_dim_store",
        "to_column": "store_id",
        "cardinality": "ManyToOne",
        "cross_filter": "Single"
    },
    # 4. Fact Redistribution Recommendations
    {
        "from_table": "pbi_fact_redistribution_recommendations",
        "from_column": "sku_id",
        "to_table": "pbi_dim_product",
        "to_column": "sku_id",
        "cardinality": "ManyToOne",
        "cross_filter": "Single"
    },
    {
        "from_table": "pbi_fact_redistribution_recommendations",
        "from_column": "destination_store_id",
        "to_table": "pbi_dim_store",
        "to_column": "store_id",
        "cardinality": "ManyToOne",
        "cross_filter": "Single"
    },
    # 5. Fact Action Queue
    {
        "from_table": "pbi_fact_action_queue",
        "from_column": "sku_id",
        "to_table": "pbi_dim_product",
        "to_column": "sku_id",
        "cardinality": "ManyToOne",
        "cross_filter": "Single"
    }
]

def get_schema_summary() -> str:
    lines = ["# Power BI Star Schema Relationships:"]
    for r in STAR_SCHEMA_RELATIONSHIPS:
        lines.append(f"- {r['from_table']}.{r['from_column']} -> {r['to_table']}.{r['to_column']} ({r['cardinality']})")
    return "\n".join(lines)
