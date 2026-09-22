"""Central configuration loader for StockLane."""
import os
from pathlib import Path
from typing import Any, Dict
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def load_config(config_path: str = "config/project_config.yaml") -> Dict[str, Any]:
    full_path = PROJECT_ROOT / config_path
    if not full_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config

def get_project_root() -> Path:
    return PROJECT_ROOT
