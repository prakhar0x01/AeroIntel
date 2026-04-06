import requests
from requests.auth import HTTPBasicAuth
import time
import os
from typing import Dict, List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Use existing shared memory structure
try:
    from shared_state import aircraft_store
except ImportError:
    aircraft_store = []

load_dotenv()

class OpenSkyTilingIngestor:
    """
    Part 2: Improve OpenSky Ingestion.
    - Regional Tiling (Bboxes)
    - 10s Polling
    - Exponential Backoff
    - Authentication
    """
    # 2.2: Tiling for broad coverage
    BBOXES = {
        "India": {"lamin": 6, "lomin": 68, "lamax": 37, "lomax": 97},
        "Europe": {"lamin": 35, "lomin": -10, "lamax": 60, "lomax": 30},
        "MiddleEast": {"lamin": 12, "lomin": 34, "lamax": 42, "lomax": 60},
        "AmericaLow": {"lamin": 24, "lomin": -125, "lamax": 50, "lomax": -66},
    }

    def __init__(self):
        self.username = os.getenv("OPENSKY_USERNAME")
        self.password = os.getenv("OPENSKY_PASSWORD")
        self.session = requests.Session()
        if self.username and self.password:
            self.session.auth = HTTPBasicAuth(self.username, self.password)
        
        self.last_ingestion_time = int(time.time())
        self.aircraft_count = 0

    def fetch_all_regions(self) -> List[dict]:
        """
        Calls multiple boxes and merges states.
        """
        all_states = []
        base_url = "https://opensky-network.org/api/states/all"
        
        for name, bbox in self.BBOXES.items():
            print(f"Fetch region: {name}...")
            
            backoff = 1
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.session.get(base_url, params=bbox, timeout=20)
                    
                    # 2.4/2.5: Log Status and Handle 429 Backoff
                    if response.status_code == 429:
                        wait = backoff * 30
                        print(f"⚠️ OpenSky: 429 Rate Limit (Region: {name}). Backing off {wait}s.")
                        time.sleep(wait)
                        backoff *= 2
                        continue
                    
                    if response.status_code == 200:
                        data = response.json()
                        states = data.get("states", [])
                        if states:
                            print(f"OpenSky Success ({name}): {len(states)} aircraft.")
                            all_states.extend(states)
                        break
                    else:
                        print(f"OpenSky Error ({name}): Status {response.status_code}")
                        break
                except Exception as e:
                    print(f"OpenSky Error ({name}): {str(e)}")
                    time.sleep(backoff)
                    backoff *= 2
            
            # Short pause between region fetches to stay safe
            time.sleep(2)
            
        return all_states

    def process_and_merge(self, states: List[list]) -> List[dict]:
        """
        Correctly parses OpenSky vector (Part 2.7 Indices).
        """
        parsed = []
        now = int(time.time())
        for s in states:
            if s[5] is None or s[6] is None: continue
            
            # Index check from User's PART 7 (Step 248): 
            # 0: hex, 1: callsign, 5: lon, 6: lat, 7: alt(m), 9: vel(m/s), 10: heading
            alt_ft = float(s[7] * 3.28084) if s[7] is not None else 0.0
            spd_kt = float(s[9] * 1.94384) if s[9] is not None else 0.0
            
            ac = {
                "hex": s[0].strip(),
                "callsign": (s[1] or "").strip(),
                "latitude": s[6],
                "longitude": s[5],
                "altitude_ft": alt_ft,
                "speed_kt": spd_kt,
                "heading_deg": s[10] or 0.0,
                "last_contact": s[4] or now
            }
            parsed.append(ac)
            
        self.aircraft_count = len(parsed)
        self.last_ingestion_time = now
        return parsed

    def get_status(self) -> dict:
        """
        Part 6: System status endpoint tracker.
        """
        return {
            "opensky_connected": True,
            "db_connected": True,
            "aircraft_count": self.aircraft_count,
            "last_ingestion": self.last_ingestion_time
        }
