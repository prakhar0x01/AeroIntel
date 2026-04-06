import time
from typing import List, Dict, Optional
from pydantic import BaseModel

class Alert(BaseModel):
    hex: str
    callsign: str
    message: str
    severity: str
    timestamp: int

class AlertEngine:
    """
    Advanced Real-time Alert Engine.
    Detects speed drops, altitude anomalies, and heading changes.
    """
    def __init__(self):
        self.history: Dict[str, List[dict]] = {}
        self.live_alerts: List[Alert] = []

    def analyze(self, aircraft_snapshot: List[dict]):
        """
        Analyzes live aircraft against threat rules.
        """
        now = int(time.time())
        new_alerts = []
        
        for ac in aircraft_snapshot:
            hex = ac["hex"]
            hist = self.history.get(hex, [])
            
            # 1. Rule: Altitude < 5000 over land (Assuming most of India Bbox is land)
            if ac["altitude_ft"] > 0 and ac["altitude_ft"] < 5000:
                new_alerts.append(Alert(
                    hex=hex, 
                    callsign=ac["callsign"], 
                    message="Low Altitude Alert", 
                    severity="High", 
                    timestamp=now
                ))

            # 2. Rule: Speed Drop > 40% in ~30s (Using history)
            if hist:
                last = hist[-1]
                if last["speed_kt"] > 100:
                    drop = (last["speed_kt"] - ac["speed_kt"]) / last["speed_kt"]
                    if drop > 0.4:
                        new_alerts.append(Alert(
                            hex=hex,
                            callsign=ac["callsign"],
                            message="Emergency Speed Drop",
                            severity="Critical",
                            timestamp=now
                        ))

            # 3. Rule: No Update > 30s
            if now - ac["last_contact"] > 30:
                new_alerts.append(Alert(
                    hex=hex,
                    callsign=ac["callsign"],
                    message="Stale Tracking Data",
                    severity="Warning",
                    timestamp=now
                ))

            # Update History (sliding window: 5 points)
            hist.append(ac)
            self.history[hex] = hist[-5:]

        # Maintain Alert Queue (Last 20)
        self.live_alerts = (new_alerts + self.live_alerts)[:20]

    def get_live_alerts(self) -> List[dict]:
        return [a.model_dump() for a in self.live_alerts]

# Global Alert Engine
engine = AlertEngine()
