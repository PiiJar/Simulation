"""
Unified data loading layer for simulation data.
Supports both CSV (legacy) and JSON (future) formats.
"""

import os
import json
import pandas as pd
from typing import Dict, Any, Optional
from pathlib import Path


class SimulationDataLoader:
    """
    Central data loader that abstracts CSV vs JSON.
    All modules should use this instead of direct pd.read_csv().
    """
    
    def __init__(self, output_dir: str, source_format: str = "csv"):
        """
        Args:
            output_dir: Simulation output directory
            source_format: "csv" or "json"
        """
        self.output_dir = Path(output_dir)
        self.source_format = source_format
        self.init_dir = self.output_dir / "initialization"
        self.cpsat_dir = self.output_dir / "cp_sat"
        self.reports_dir = self.output_dir / "reports"
        
        # Cache for loaded data
        self._cache: Dict[str, Any] = {}
    
    def load_stations(self) -> pd.DataFrame:
        """Load stations configuration."""
        if "stations" in self._cache:
            return self._cache["stations"]
        
        if self.source_format == "csv":
            df = self._read_csv_lenient(self.init_dir / "stations.csv")
        else:
            df = self._load_from_json("stations")
        
        self._cache["stations"] = df
        return df
    
    def load_transporters(self) -> pd.DataFrame:
        """Load transporters configuration."""
        if "transporters" in self._cache:
            return self._cache["transporters"]
        
        if self.source_format == "csv":
            df = pd.read_csv(self.init_dir / "transporters.csv")
        else:
            df = self._load_from_json("transporters")
        
        self._cache["transporters"] = df
        return df
    
    def load_production(self) -> pd.DataFrame:
        """Load production batches."""
        if "production" in self._cache:
            return self._cache["production"]
        
        if self.source_format == "csv":
            df = pd.read_csv(self.init_dir / "production.csv")
        else:
            df = self._load_from_json("production")
        
        self._cache["production"] = df
        return df
    
    def load_transporter_physics(self, transporter_id: int) -> pd.DataFrame:
        """Load physics profile for a transporter."""
        key = f"physics_{transporter_id}"
        if key in self._cache:
            return self._cache[key]
        
        if self.source_format == "csv":
            file_name = f"transporters_{transporter_id}_physics.csv"
            df = pd.read_csv(self.init_dir / file_name)
        else:
            df = self._load_from_json(f"transporter_physics_{transporter_id}")
        
        self._cache[key] = df
        return df
    
    def load_transporter_task_areas(self, transporter_id: int) -> pd.DataFrame:
        """Load task areas for a transporter."""
        key = f"task_areas_{transporter_id}"
        if key in self._cache:
            return self._cache[key]
        
        if self.source_format == "csv":
            file_name = f"transporters_{transporter_id}_task_areas.csv"
            df = pd.read_csv(self.init_dir / file_name)
        else:
            df = self._load_from_json(f"transporter_task_areas_{transporter_id}")
        
        self._cache[key] = df
        return df
    
    def load_treatment_program(self, program_name: str) -> pd.DataFrame:
        """Load treatment program."""
        key = f"program_{program_name}"
        if key in self._cache:
            return self._cache[key]
        
        if self.source_format == "csv":
            file_name = f"treatment_program_{program_name}.csv"
            df = pd.read_csv(self.init_dir / file_name)
        else:
            df = self._load_from_json(f"treatment_program_{program_name}")
        
        self._cache[key] = df
        return df
    
    def load_batch_schedule(self) -> pd.DataFrame:
        """Load CP-SAT batch schedule results."""
        if "batch_schedule" in self._cache:
            return self._cache["batch_schedule"]
        
        if self.source_format == "csv":
            df = pd.read_csv(self.cpsat_dir / "cp_sat_batch_schedule.csv")
        else:
            df = self._load_from_json("results/batch_schedule")
        
        self._cache["batch_schedule"] = df
        return df
    
    def load_transporter_schedule(self) -> pd.DataFrame:
        """Load CP-SAT transporter schedule results."""
        if "transporter_schedule" in self._cache:
            return self._cache["transporter_schedule"]
        
        if self.source_format == "csv":
            df = pd.read_csv(self.cpsat_dir / "cp_sat_transporter_schedule.csv")
        else:
            df = self._load_from_json("results/transporter_schedule")
        
        self._cache["transporter_schedule"] = df
        return df
    
    def load_station_schedule(self) -> pd.DataFrame:
        """Load CP-SAT station schedule results."""
        if "station_schedule" in self._cache:
            return self._cache["station_schedule"]
        
        if self.source_format == "csv":
            df = pd.read_csv(self.cpsat_dir / "cp_sat_station_schedule.csv")
        else:
            df = self._load_from_json("results/station_schedule")
        
        self._cache["station_schedule"] = df
        return df
    
    def load_transporter_phases(self) -> pd.DataFrame:
        """Load transporter movement phases."""
        if "transporter_phases" in self._cache:
            return self._cache["transporter_phases"]
        
        if self.source_format == "csv":
            df = pd.read_csv(self.reports_dir / "transporter_phases.csv")
        else:
            df = self._load_from_json("results/transporter_phases")
        
        self._cache["transporter_phases"] = df
        return df
    
    def load_detailed_movements(self, transporter_id: int) -> pd.DataFrame:
        """Load detailed transporter movements."""
        key = f"movements_{transporter_id}"
        if key in self._cache:
            return self._cache[key]
        
        if self.source_format == "csv":
            file_name = f"transporter_{transporter_id}_detailed_movements.csv"
            df = pd.read_csv(self.reports_dir / file_name)
        else:
            df = self._load_from_json(f"results/transporter_{transporter_id}_movements")
        
        self._cache[key] = df
        return df
    
    def load_customer_plant_info(self) -> Dict[str, str]:
        """Load customer and plant information."""
        if "customer_plant" in self._cache:
            return self._cache["customer_plant"]
        
        if self.source_format == "csv":
            df = pd.read_csv(self.init_dir / "customer_and_plant.csv")
            info = {
                "customer": df['Customer'].iloc[0],
                "plant": df['Plant'].iloc[0]
            }
        else:
            config = self._load_json_file("simulation_config.json")
            info = {
                "customer": config["metadata"]["customer"],
                "plant": config["metadata"]["plant"]
            }
        
        self._cache["customer_plant"] = info
        return info
    
    def get_all_config_data(self) -> Dict[str, Any]:
        """
        Get all configuration data as a structured dictionary.
        This is the foundation for prepare_report_data().
        """
        return {
            "metadata": self.load_customer_plant_info(),
            "stations": self.load_stations().to_dict(orient='records'),
            "transporters": self.load_transporters().to_dict(orient='records'),
            "production": self.load_production().to_dict(orient='records'),
        }
    
    def _read_csv_lenient(self, path: Path) -> pd.DataFrame:
        """Read CSV with lenient parsing for numeric columns."""
        df = pd.read_csv(path, dtype=str)
        df.columns = df.columns.str.strip()
        
        # Coerce common numeric columns
        for c in ['Number', 'Tank', 'Group', 'X Position', 'Dropping_Time', 'Device_delay']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        
        # Convert to integers where appropriate
        for c in ['Number', 'Tank', 'Group']:
            if c in df.columns:
                df[c] = df[c].fillna(0).astype(int)
        
        return df
    
    def _load_from_json(self, key: str) -> pd.DataFrame:
        """Load data from JSON structure."""
        config_file = self.output_dir / "simulation_data.json"
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"JSON data file not found: {config_file}\n"
                f"Run conversion: python convert_csv_to_json.py {self.output_dir}"
            )
        
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        # Navigate nested structure
        parts = key.split('/')
        obj = data
        for part in parts:
            obj = obj[part]
        
        return pd.DataFrame(obj)
    
    def _load_json_file(self, filename: str) -> Dict[str, Any]:
        """Load entire JSON file."""
        path = self.output_dir / filename
        with open(path, 'r') as f:
            return json.load(f)
    
    def export_to_json(self, output_file: Optional[str] = None):
        """
        Export all current data to JSON format.
        This is for CSV → JSON migration.
        """
        if output_file is None:
            output_file = self.output_dir / "simulation_data.json"
        
        data = {
            "metadata": {
                **self.load_customer_plant_info(),
                "source_format": "json",
                "version": "1.0"
            },
            "configuration": {
                "stations": self.load_stations().to_dict(orient='records'),
                "transporters": self.load_transporters().to_dict(orient='records'),
                "production": self.load_production().to_dict(orient='records'),
            },
            "results": {
                "batch_schedule": self.load_batch_schedule().to_dict(orient='records'),
                "transporter_schedule": self.load_transporter_schedule().to_dict(orient='records'),
                "station_schedule": self.load_station_schedule().to_dict(orient='records'),
                "transporter_phases": self.load_transporter_phases().to_dict(orient='records'),
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Exported simulation data to JSON: {output_file}")
        return output_file


def get_data_loader(output_dir: str, prefer_json: bool = False) -> SimulationDataLoader:
    """
    Factory function to get appropriate data loader.
    
    Args:
        output_dir: Simulation output directory
        prefer_json: If True, use JSON if available, else fallback to CSV
    
    Returns:
        SimulationDataLoader instance
    """
    json_file = Path(output_dir) / "simulation_data.json"
    
    if prefer_json and json_file.exists():
        return SimulationDataLoader(output_dir, source_format="json")
    else:
        return SimulationDataLoader(output_dir, source_format="csv")
