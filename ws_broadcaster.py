import asyncio
import json
from db import get_live_aircraft_from_db
from websocket_handler import ConnectionManager

class WSBroadcaster:
    """
    Part 1.1: WebSocket live aircraft broadcaster.
    Part 4: Real-time movement on frontend (Stop polling REST).
    Every 2 seconds: Fetch all aircraft from DB, Broadcast to all.
    """
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.is_running = False

    async def start(self):
        """
        Background periodic task for broadcasting.
        """
        self.is_running = True
        print("WebSocket Broadcaster started: 2s interval.")
        while self.is_running:
            try:
                # 1. Fetch from DB (Source of Truth)
                aircraft = get_live_aircraft_from_db()
                
                # 2. Part 4: Add interpolation/rotation if needed? 
                # The user says "Rotate aircraft icon using heading_deg".
                # heading_deg is already in aircraft object from get_live_aircraft_from_db.
                
                # 3. Broadcast JSON
                if aircraft:
                    await self.manager.broadcast(json.dumps(aircraft))
                    
            except Exception as e:
                print(f"WS Broadcast Error: {e}")
            
            # Every 2 seconds
            await asyncio.sleep(2)

    def stop(self):
        self.is_running = False
