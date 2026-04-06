import time
from typing import List, Dict, Optional
from pydantic import BaseModel

class Alert(BaseModel):
    hex: str
    callsign: str
    message: str
    severity: str
    timestamp: int

class AnomalyDetector:
    """
    Part 1.2: Alerts Engine (REAL).
    Performs anomaly detection based on DB aircraft data history and current states.
    """
    def __init__(self, history_data: Dict[str, List[dict]]):
        self.history = history_data

    def detect(self, ac: dict) -> List[Alert]:
        """
        Runs real detection rules.
        """
        alerts = []
        now = int(time.time())
        hex_code = ac.get("hex", "N/A")
        callsign = ac.get("callsign", "N/A")
        
        # 1. Rule: Emergency Squawk (Not always available in basic vectors, 
        # but if we had it, we'd check here) - Assuming hex or callsign 
        # contains indicator if we parsed it earlier.
        # OpenSky returns 'squawk' in index 14 of states.
        
        # 2. Rule: Unrealistic speed > 700 knots
        if (ac.get("speed_kt") or 0) > 700:
            alerts.append(Alert(
                hex=hex_code,
                callsign=callsign,
                message="Unrealistic high speed detected (>700kts)",
                severity="High",
                timestamp=now
            ))
            
        # 3. Use History for Vertical & Teleport anomalies (Part 1.2)
        if hex_code in self.history and len(self.history[hex_code]) > 1:
            prev = self.history[hex_code][-1]
            
            # Vertical Anomaly: altitude change > 8000 ft in 10s
            # (Assuming 10s interval as per Part 2.3)
            alt_diff = abs(ac.get("altitude_ft", 0) - prev.get("alt", 0))
            if alt_diff > 8000:
                alerts.append(Alert(
                    hex=hex_code,
                    callsign=callsign,
                    message="Critical Vertical Anomaly (>8000ft Delta)",
                    severity="Critical",
                    timestamp=now
                ))
            
            # Teleport Anomaly: position jump > 50km in 5s
            # For simplicity, we use coordinate jump check. 
            # (In production, use haversine).
            # 0.5 degrees is roughly 50km.
            lat_diff = abs(ac.get("latitude", 0) - prev.get("lat", 0))
            lon_diff = abs(ac.get("longitude", 0) - prev.get("lon", 0))
            if lat_diff > 0.45 or lon_diff > 0.45:
                alerts.append(Alert(
                    hex=hex_code,
                    callsign=callsign,
                    message="Rapid Position Displacement Detected",
                    severity="Critical",
                    timestamp=now
                ))

        return alerts
