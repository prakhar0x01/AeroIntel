import time
import math
from typing import Dict, List, Optional
from pydantic import BaseModel

class AircraftState(BaseModel):
    hex: str
    callsign: Optional[str] = ""
    latitude: float
    longitude: float
    altitude_ft: float
    speed_kt: float
    heading_deg: float
    last_contact: int
    threat_score: float = 0.0
    anomaly_reasons: List[str] = []

class AircraftStore:
    """
    Thread-safe, in-memory aircraft cache. (User: NO DB for live map).
    """
    def __init__(self):
        # We use a Dict[icao24, AircraftState]
        self.aircraft_cache: Dict[str, AircraftState] = {}
        self.last_update_ts = 0

    def update(self, new_states: List[AircraftState]):
        """
        Updates cache with fresh snapshots.
        """
        now = int(time.time())
        for state in new_states:
            self.aircraft_cache[state.hex] = state
        self.last_update_ts = now
        self._cleanup(now)

    def _cleanup(self, now: int):
        """Removes aircraft not seen for > 120s."""
        expired = [h for h, ac in self.aircraft_cache.items() if now - ac.last_contact > 120]
        for h in expired:
            del self.aircraft_cache[h]

    def get_all(self, interpolate: bool = False) -> List[dict]:
        """
        Returns snapshot, optionally with 1s position interpolation.
        Interpolates using speed and heading if delta > 1s.
        """
        now = time.time()
        results = []
        
        for ac in self.aircraft_cache.values():
            data = ac.model_dump()
            
            if interpolate and ac.speed_kt > 0:
                # Basic dead reckoning interpolation
                delta_t = now - ac.last_contact
                if delta_t > 0 and delta_t < 120: # Sanity check
                    # spd_kt * 0.514444 (m/s) * delta_t (s) = dist (m)
                    # degrees = m / 111320 (approx)
                    dist_deg = (ac.speed_kt * 0.514444 * delta_t) / 111320.0
                    
                    # Heading rotation
                    rad = math.radians(ac.heading_deg)
                    data["latitude"] += dist_deg * math.cos(rad)
                    data["longitude"] += dist_deg * math.sin(rad)
            
            results.append(data)
        
        return results

# Global Store Instance
store = AircraftStore()
