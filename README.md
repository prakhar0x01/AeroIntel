# AeroIntel

A real-time aircraft intelligence and anomaly detection platform built on top of live ADS-B state vectors from the **OpenSky Network**.

This project is **NOT a flight tracker clone**.  

It is an **aviation intelligence engine** that ingests raw ADS-B telemetry, builds a spatial database, detects anomalies, and streams live aircraft intelligence to an interactive map UI.

### NOTE - What is ADS-B

> **Automatic Dependent Surveillance–Broadcast (ADS-B)** is an advanced, satellite-based aviation surveillance technology where aircraft determine their position via GPS and periodically broadcast it—along with speed, altitude, and identity—to ground stations and other aircraft.

----------

## 🧠 What This Project Really Is

Other's Project:

> “Map + planes from API”

This Project:

> **ADS-B ingestion → spatial DB → anomaly engine → real-time intelligence UI**

This is the **foundation used by real surveillance / aviation analytics systems**.

----------

## 🏗️ System Architecture


```
OpenSky (ADS-B states)  
 ↓  
Ingestion Worker (polling + parsing)  
 ↓  
Database (aircraft state store)  
 ↓  
Detection / Alerts Engine  
 ↓  
REST + WebSocket APIs  
 ↓  
Next.js Intelligence UI (Leaflet Map)
```


----------

## 📡 Data Source

-   Live aircraft telemetry from **OpenSky Network** (via API)
-   State vectors: position, altitude, velocity, heading, squawk, callsign
-   Polled at fixed intervals
-   Parsed into structured aircraft state

----------

## ⚙️ Backend (FastAPI)

### Responsibilities

-   Poll OpenSky every N seconds
-   Parse and normalize ADS-B states
-   Store latest aircraft state
-   Detect anomalies
-   Expose REST endpoints
-   Broadcast live updates via WebSocket

----------

### Core Components

#### 1. Ingestion Worker

Continuously polls OpenSky and updates aircraft state.

Handles:

-   Rate limiting (429 handling)
-   JSON parsing failures
-   Retry/backoff
-   Bounding box optimization

----------

#### 2. Aircraft State Store

Each aircraft is tracked by **ICAO hex**:

```json
{  
 "icao": "488252",  
 "callsign": "SAH48P",  
 "lat": 28.44,  
 "lon": 77.02,  
 "altitude": 10668,  
 "velocity": 215.6,  
 "heading": 181.2,  
 "last_seen": "timestamp"  
}
```

----------


----------

## 🌐 Frontend (Next.js + Leaflet)

### Features

-   Dark tactical map
-   Aircraft plotted from live API
-   Real-time map updates
-   Alerts panel
-   System status panel
-   Intelligence dashboard

### Map Engine

Built with **Leaflet** and **OpenStreetMap** tiles.

Aircraft are rendered as markers using live state updates.

----------

## 🚨 Priority Alerts Panel

Right side panel displays:

-   ICAO
-   Callsign
-   Anomaly type
-   Timestamp
-   Risk level

Driven entirely from `/aircraft/alerts/live`.

----------

## 🔁 Real-Time Movement

Aircraft movement happens because:

-   Backend continuously updates positions
-   Frontend polls or listens via WebSocket
-   Map re-renders markers based on latest state

----------

## 🗃️ Database Role

Stores:

-   Latest aircraft state
-   Historical track for each ICAO
-   Alerts history

Enables:

-   Flight history lookup
-   Alert deduplication
-   Lifecycle management

----------


## 🧠 Why Aircraft Count Is Lower Than FlightRadar

Because **FlightRadar24**:

-   Uses thousands of private ADS-B receivers
-   Paid satellite feeds
-   ML-reconstructed tracks
-   Military + filtered data

You use **public OpenSky sample**.

This is expected.

----------

## 🧪 How to Run

### Backend

**`uvicorn app:app --reload  --port  8000`**

### Frontend

`npm run dev`

Visit:

`http://localhost:3000`

----------

## 🛰️ What This System Can Be Extended Into

-   Military aircraft detection
-   Suspicious flight behavior analysis
-   Airspace violation monitoring
-   Sector-based intelligence
-   Historical route reconstruction
-   ADS-B anomaly research

This is a **research-grade base**, not a toy.

----------


## 🧭 What Makes This Project Unique

What I didn’t build:

> “Flight map”

What I built:

> **ADS-B Intelligence Platform**

That’s the difference.

----------

## ❓ FAQ

### Is this like FlightRadar24?

No.

FR24 is a flight tracking UI.  
This is an **aircraft anomaly intelligence engine**.

----------

### Why fewer aircraft?

Because of OpenSky’s public sampling vs FR24’s private global network.

----------

### Why do alerts remain visible?

Because alerts are tied to last known state and TTL cleanup is not implemented yet.

----------

### Can aircraft be tracked historically?

Yes via `/aircraft/flights/{icao}`.

----------

### Why real-time feels slightly delayed?

OpenSky polling interval + network + rendering delay.

----------

### Can this be made production-grade?

Yes. Add:

-   Redis / Postgres
-   Proper TTL expiry
-   Authenticated OpenSky
-   Sector tiling
-   WebSocket only updates

----------

### What is the real value of this project?

Learning how **ADS-B intelligence systems** are built from raw telemetry.

----------

### What can be improved next?

-   Alert expiry lifecycle
-   Aircraft TTL removal
-   Sector-based polling
-   WebSocket streaming only
-   Risk scoring model
