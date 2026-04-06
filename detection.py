from typing import List, Dict, Optional
from pydantic import BaseModel
from haversine import haversine

class AircraftState(BaseModel):
    hex: str
    callsign: Optional[str] = None
    longitude: float
    latitude: float
    baro_altitude: Optional[float] = None
    velocity: Optional[float] = None
    true_track: Optional[float] = None
    last_contact: int
    threat_score: float = 0.0
    anomaly_reasons: List[str] = []

class Anomaly(BaseModel):
    category: str
    reason: str
    score_impact: float

class ThreatScore(BaseModel):
    hex: str
    overall_score: float
    anomalies: List[Anomaly]

class DetectionEngine:
    def analyze(self, current: AircraftState, history: List[AircraftState]) -> ThreatScore:
        anomalies = []
        
        # 1. Physical Jump Detection (Spoofing)
        if history:
            last = history[-1]
            dt = current.last_contact - last.last_contact
            if dt > 0:
                dist = haversine((last.latitude, last.longitude), (current.latitude, current.longitude))
                # 0.539957 converts km to nautical miles
                speed_knots = (dist / dt) * 3600 * 0.539957
                
                if speed_knots > 1500: # Mach 2.2+ is unrealistic for civil airframes
                    anomalies.append(Anomaly(
                        category="Physics", 
                        reason=f"Unrealistic jump speed: {int(speed_knots)} knots", 
                        score_impact=50.0
                    ))
        
        # Calculate final threat score
        total_score = min(sum(a.score_impact for a in anomalies), 100.0)
        return ThreatScore(hex=current.hex, overall_score=total_score, anomalies=anomalies)

class TrajectoryManager:
    def __init__(self):
        self.windows: Dict[str, List[AircraftState]] = {}
        self.WINDOW_SEC = 300

    def add(self, state: AircraftState):
        if state.hex not in self.windows:
            self.windows[state.hex] = []
        
        win = self.windows[state.hex]
        win.append(state)
        
        # Only keep last X seconds of data
        cutoff = state.last_contact - self.WINDOW_SEC
        self.windows[state.hex] = [p for p in win if p.last_contact >= cutoff]
        
        if len(win) >= 3:
            # Basic smoothing (simple moving average for V1)
            lats = [p.latitude for p in win[-3:]]
            lons = [p.longitude for p in win[-3:]]
            state.latitude = sum(lats) / len(lats)
            state.longitude = sum(lons) / len(lons)
            
        return state
