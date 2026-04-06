import asyncio
import json
import os
import time
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

# Existing Persistence and Store
import db as database 
from websocket_handler import ConnectionManager

# New Modular Services
from backend.ingestion.live_stream import OpenSkyTilingIngestor
from history_manager import history_manager
from alerts_engine import AnomalyDetector
from ws_broadcaster import WSBroadcaster

load_dotenv()

# ----------------- App Setup -----------------
app = FastAPI(title="OpenSkyHunter LifeCycle")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

box_ingestor = OpenSkyTilingIngestor()
ws_manager = ConnectionManager()
broadcaster = WSBroadcaster(ws_manager)

# ----------------- 1. Aircraft Expiry Job (Every 30s) -----------------
async def background_cleanup_job():
    """
    Step 1: If now - last_contact > 180 sec -> delete from live_aircraft.
    Step 2: If aircraft expired -> delete its alerts.
    """
    print("Cleanup Job: Running every 30s.")
    while True:
        try:
            # Executes the logic defined in db.py:run_expiry_cleanup()
            await asyncio.to_thread(database.run_expiry_cleanup)
        except Exception as e:
            print(f"Cleanup Job Error: {e}")
        
        # Runs every 30 seconds
        await asyncio.sleep(30)

# ----------------- Ingestion Loop (10s) -----------------
async def background_ingestion_loop():
    """
    Step 4: Recalculate threat_score each ingestion.
    Note: We process new states and overwrite DB entries, thus resetting previous flags.
    """
    while True:
        try:
            states = await asyncio.to_thread(box_ingestor.fetch_all_regions)
            updates = box_ingestor.process_and_merge(states)
            
            if updates:
                detector = AnomalyDetector(history_manager.fast_cache)
                
                def process_updates():
                    for ac in updates[:1000]:
                        # Step 4: THREAT SCORE RECALCULATION
                        # We analyze each aircraft fresh every cycle.
                        my_alerts = detector.detect(ac)
                        anomaly_reasons = [a.message for a in my_alerts]
                        threat_score = len(my_alerts) * 20
                        
                        # Part 3/4: Database overwrite (Update Live + Add to History)
                        history_manager.update_history(ac, threat_score, anomaly_reasons)
                        
                        # Persist new alerts incrementally
                        for alert_obj in my_alerts:
                            database.save_alert_to_db({
                                "hex": alert_obj.hex,
                                "callsign": alert_obj.callsign,
                                "severity": alert_obj.severity,
                                "message": alert_obj.message
                            })
                
                await asyncio.to_thread(process_updates)
            
        except Exception as e:
            print(f"Ingestion Loop Error: {str(e)}")
        
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    database.init_db()
    # Lifecycle Management Tasks
    asyncio.create_task(background_ingestion_loop())
    asyncio.create_task(background_cleanup_job()) # Step 1 & 2
    asyncio.create_task(broadcaster.start())

# ----------------- API Routes -----------------

@app.get("/aircraft/alerts/live")
async def get_live_alerts(since: Optional[float] = Query(None)):
    """
    Step 3: Only show alerts where now - alert.created_at < 120 sec.
    Note: Filtering logic is enforced inside database.get_alerts_since().
    """
    if since is None:
        return []
    
    return database.get_alerts_since(since)

@app.get("/aircraft/live")
@app.get("/aircraft/live/all")
async def get_live():
    return database.get_live_aircraft_from_db()

@app.get("/aircraft/flights/{icao}")
async def get_aircraft_path(icao: str):
    return {
        "hex": icao,
        "path": database.get_aircraft_history(icao, 30)
    }

@app.get("/aircraft/status/all")
async def get_system_status():
    return box_ingestor.get_status()

# WebSocket broadcaster
@app.websocket("/ws/aircraft/live")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
