from db import get_aircraft_history, save_aircraft_to_db
from typing import List, Dict

class HistoryManager:
    """
    Part 1.3: Flight history per ICAO.
    Part 3: Store aircraft history.
    """
    def __init__(self):
        # We also keep a very short in-memory cache for fast anomaly delta checks
        # between ingestion cycles.
        self.fast_cache: Dict[str, List[dict]] = {}

    def update_history(self, plane_data: dict, threat_score: float, anomaly_reasons: list):
        """
        Main entry point for storing.
        """
        # 1. Update In-Memory fast cache (for Anomaly detector)
        hex_code = plane_data["hex"]
        if hex_code not in self.fast_cache:
            self.fast_cache[hex_code] = []
        
        entry = {
            "lat": plane_data["latitude"],
            "lon": plane_data["longitude"],
            "alt": plane_data["altitude_ft"],
            "ts": plane_data["last_contact"]
        }
        self.fast_cache[hex_code].append(entry)
        # Limit in-memory to 5 points (Anomaly detection only needs few)
        self.fast_cache[hex_code] = self.fast_cache[hex_code][-5:]
        
        # 2. Persist to PostgreSQL (via db.py)
        # db.py's save_aircraft_to_db already handles the history table.
        save_aircraft_to_db(plane_data, threat_score, anomaly_reasons)

    def get_trajectory(self, icao: str, limit: int = 30) -> List[dict]:
        """
        Part 1.3: Return path/trajectory for drawing trail on map.
        """
        return get_aircraft_history(icao, limit)

# Global History Manager
history_manager = HistoryManager()
