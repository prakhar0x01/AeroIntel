import asyncio
import json
import requests
from db import save_aircraft_to_db, get_live_aircraft_from_db
from detection import DetectionEngine, TrajectoryManager, AircraftState

# Single instances for the ingestion loop
engine = DetectionEngine()
manager = TrajectoryManager()

def fetch_adsb():
    """
    Perform HTTP GET to the OpenSky endpoint and parse JSON response.
    Returns a list of aircraft dictionaries.
    """
    API_URL = "https://opensky-network.org/api/states/all"
    try:
        resp = requests.get(API_URL, timeout=10)
        if resp.status_code != 200:
            return []
            
        data = resp.json()
        states = data.get("states")
        if not states:
            return []
            
        aircraft_list = []
        # Limit to top 100 for V1 performance
        for s in states[:100]:
            if s[5] is None or s[6] is None:
                continue
                
            aircraft = {
                "hex": s[0],
                "callsign": s[1].strip() if s[1] else "N/A",
                "longitude": s[5],
                "latitude": s[6],
                "altitude_ft": s[7],
                "speed_kt": s[9],
                "heading_deg": s[10],
                "squawk": s[14],
                "last_contact": s[4]
            }
            aircraft_list.append(aircraft)
        return aircraft_list
    except Exception as e:
        print(f"Fetch Error: {e}")
        return []

async def run_ingestion_loop(ws_manager):
    """
    Main ingestion pipeline: 
    OpenSky -> fetch_adsb() -> Detection -> DB -> WebSocket -> UI
    """
    while True:
        try:
            # 1. Fetch real data
            planes = fetch_adsb()
            
            # 2. Process & Persist
            for p in planes:
                state = AircraftState(
                    hex=p["hex"],
                    callsign=p["callsign"],
                    longitude=p["longitude"],
                    latitude=p["latitude"],
                    baro_altitude=p["altitude_ft"],
                    velocity=p["speed_kt"],
                    true_track=p["heading_deg"],
                    last_contact=p["last_contact"]
                )
                
                # Window & Smooth
                smoothed = manager.add(state)
                history = manager.windows.get(p["hex"], [])[:-1]
                
                # Check for anomalies
                threat = engine.analyze(smoothed, history)
                
                # Save to Database (PostGIS)
                save_aircraft_to_db(
                    p, 
                    threat.overall_score, 
                    [a.reason for a in threat.anomalies]
                )

            # 3. Fetch from DB for Broadcaster (Ensures real data reaches UI)
            live_from_db = get_live_aircraft_from_db()
            
            # 4. Broadcast via WebSocket
            if live_from_db:
                await ws_manager.broadcast(json.dumps(live_from_db))
                
            print(f"Pipeline pulse: {len(live_from_db)} aircraft synced via DB.")
            
        except Exception as e:
            print(f"Ingestion heartbeat error: {e}")
            
        await asyncio.sleep(2)
