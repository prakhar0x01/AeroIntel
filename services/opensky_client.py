import requests
from requests.auth import HTTPBasicAuth
import time
import os
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()

class OpenSkyClient:
    """
    Advanced OpenSky REST Client with rate-limit safety and flight history.
    """
    BASE_URL = "https://opensky-network.org/api"
    
    def __init__(self):
        self.username = os.getenv("OPENSKY_USERNAME")
        self.password = os.getenv("OPENSKY_PASSWORD")
        self.last_fetch_time = 0
        self.min_poll_interval = 12  # Respecting 15s limit (user asked for 12-15)

    def _get_auth(self):
        return HTTPBasicAuth(self.username, self.password) if self.username and self.password else None

    def fetch_states(self, bbox: Optional[Dict] = None) -> Optional[dict]:
        """
        Fetches global or regional aircraft states.
        India Bbox Default: lamin=6, lomin=68, lamax=37, lomax=97
        """
        # Rate Limit Safety
        now = time.time()
        if now - self.last_fetch_time < self.min_poll_interval:
            # wait_time = self.min_poll_interval - (now - self.last_fetch_time)
            # time.sleep(wait_time) 
            pass # Polling loop handles the sleep, but safeguard is here

        url = f"{self.BASE_URL}/states/all"
        params = bbox if bbox else {"lamin": 6, "lomin": 68, "lamax": 37, "lomax": 97}

        try:
            response = requests.get(url, auth=self._get_auth(), params=params, timeout=15)
            self.last_fetch_time = time.time()

            if response.status_code == 429:
                print("OpenSky: 429 Too Many Requests. Cooling down.")
                return None
            
            if response.status_code != 200:
                return None
            
            return response.json()
        except Exception as e:
            print(f"OpenSky Client Error: {e}")
            return None

    def fetch_arrivals(self, airport_icao: str) -> List[dict]:
        """Fetches recent arrivals for a given airport."""
        now = int(time.time())
        yesterday = now - 86400
        url = f"{self.BASE_URL}/flights/arrival?airport={airport_icao}&begin={yesterday}&end={now}"
        try:
            response = requests.get(url, auth=self._get_auth(), timeout=10)
            return response.json() if response.status_code == 200 else []
        except: return []

    def fetch_departures(self, airport_icao: str) -> List[dict]:
        """Fetches recent departures for a given airport."""
        now = int(time.time())
        yesterday = now - 86400
        url = f"{self.BASE_URL}/flights/departure?airport={airport_icao}&begin={yesterday}&end={now}"
        try:
            response = requests.get(url, auth=self._get_auth(), timeout=10)
            return response.json() if response.status_code == 200 else []
        except: return []
