import os
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, func, ForeignKey, Index, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load Environment from .env
load_dotenv()

# Connection String:
# Uses DATABASE_URL from .env or defaults to local postgres
username = os.getlogin() if hasattr(os, "getlogin") else "prakharporwal"
default_db_url = f"postgresql://{username}@localhost:5432/opensky_hunter"
DATABASE_URL = os.getenv("DATABASE_URL", default_db_url)

# Setup Engine
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AircraftDB(Base):
    __tablename__ = "aircraft_live"
    
    hex = Column(String(10), primary_key=True, index=True)
    callsign = Column(String(10))
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Float)
    speed = Column(Float)
    heading = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    threat_score = Column(Float, default=0.0)
    anomaly_reasons = Column(String, default="") 

class AircraftHistory(Base):
    __tablename__ = "aircraft_history"
    id = Column(Integer, primary_key=True, index=True)
    hex = Column(String(10), index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Float)
    speed = Column(Float)
    heading = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class AlertDB(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    hex = Column(String(10), index=True)
    callsign = Column(String(10))
    alert_type = Column(String(50))
    severity = Column(String(20))
    message = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("Database Schema Ready.")
    except Exception as e:
        print(f"Database Schema Error: {e}")

# --- Requirement 1 & 2: Expiry Job Logic ---

def run_expiry_cleanup():
    """
    1. Aircraft expiry: last_contact > 180s
    2. Alert expiry: Delete alerts for expired aircraft
    """
    db = SessionLocal()
    try:
        # Step 1: Find hex codes of stale aircraft
        threshold = datetime.utcnow() - timedelta(seconds=180)
        stale_aircraft = db.query(AircraftDB).filter(AircraftDB.timestamp < threshold).all()
        stale_hexes = [ac.hex for ac in stale_aircraft]
        
        if stale_hexes:
            # Step 2: Delete alerts for these aircraft
            db.query(AlertDB).filter(AlertDB.hex.in_(stale_hexes)).delete(synchronize_session=False)
            
            # Step 1: Delete stale aircraft
            db.query(AircraftDB).filter(AircraftDB.hex.in_(stale_hexes)).delete(synchronize_session=False)
            
            db.commit()
            print(f"Cleanup Job: Expired {len(stale_hexes)} stale aircraft and their alerts.")
    except Exception as e:
        print(f"Cleanup Job Error: {e}")
        db.rollback()
    finally:
        db.close()

# --- Requirement 3: Conditional Alert Fetching ---

def get_alerts_since(since_ts: float):
    """
    3. Only show alerts where now - alert.created_at < 120 sec
    """
    db = SessionLocal()
    try:
        current_time = datetime.utcnow()
        # Enforce 120s limit on top of 'since' cursor
        expiry_threshold = current_time - timedelta(seconds=120)
        since_dt = datetime.fromtimestamp(since_ts)
        
        # Use the most restrictive of the two
        effective_since = max(since_dt, expiry_threshold)
        
        results = db.query(AlertDB)\
            .filter(AlertDB.created_at > effective_since)\
            .order_by(AlertDB.created_at.asc())\
            .all()
        
        return [{
            "hex": r.hex,
            "callsign": r.callsign,
            "alert_type": r.alert_type,
            "severity": r.severity,
            "message": r.message,
            "created_at": int(r.created_at.timestamp())
        } for r in results]
    except Exception as e:
        print(f"Alert Retrieval Error: {e}")
        return []
    finally:
        db.close()

# --- Normal DB Operations ---

def save_alert_to_db(alert_data: dict):
    db = SessionLocal()
    try:
        new_alert = AlertDB(
            hex=alert_data["hex"],
            callsign=alert_data.get("callsign", ""),
            alert_type=alert_data.get("alert_type", "anomaly"),
            severity=alert_data.get("severity", "medium"),
            message=alert_data["message"],
            created_at=datetime.utcnow()
        )
        db.add(new_alert)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def save_aircraft_to_db(plane_data: dict, threat_score: float, anomaly_reasons: list):
    """
    4. Recalculate threat_score each ingestion.
    Note: We overwrite the existing row, thus effectively recalculating.
    """
    db = SessionLocal()
    try:
        aircraft = db.query(AircraftDB).filter(AircraftDB.hex == plane_data["hex"]).first()
        if not aircraft:
            aircraft = AircraftDB(hex=plane_data["hex"])
            db.add(aircraft)
            
        aircraft.callsign = plane_data.get("callsign", "")
        aircraft.latitude = plane_data.get("latitude")
        aircraft.longitude = plane_data.get("longitude")
        aircraft.altitude = plane_data.get("altitude_ft", 0)
        aircraft.speed = plane_data.get("speed_kt", 0)
        aircraft.heading = plane_data.get("heading_deg", 0)
        
        last_contact = plane_data.get("last_contact", datetime.now().timestamp())
        ts = datetime.fromtimestamp(float(last_contact))
        aircraft.timestamp = ts
        
        # Step 4: Storing recalculated value
        aircraft.threat_score = threat_score
        aircraft.anomaly_reasons = ",".join(anomaly_reasons)
        
        history_entry = AircraftHistory(
            hex=plane_data["hex"],
            latitude=plane_data.get("latitude"),
            longitude=plane_data.get("longitude"),
            altitude=plane_data.get("altitude_ft", 0),
            speed=plane_data.get("speed_kt", 0),
            heading=plane_data.get("heading_deg", 0),
            timestamp=ts
        )
        db.add(history_entry)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def get_live_aircraft_from_db():
    db = SessionLocal()
    try:
        results = db.query(AircraftDB).all()
        return [{
            "hex": r.hex, "callsign": r.callsign, "latitude": r.latitude,
            "longitude": r.longitude, "altitude_ft": r.altitude,
            "speed_kt": r.speed, "heading_deg": r.heading,
            "last_contact": int(r.timestamp.timestamp()),
            "threat_score": r.threat_score,
            "anomaly_reasons": r.anomaly_reasons.split(",") if r.anomaly_reasons else []
        } for r in results]
    finally:
        db.close()

def get_aircraft_history(icao: str, limit: int = 30):
    db = SessionLocal()
    try:
        results = db.query(AircraftHistory)\
            .filter(AircraftHistory.hex == icao)\
            .order_by(AircraftHistory.timestamp.desc())\
            .limit(limit).all()
        return [{"lat": r.latitude, "lon": r.longitude} for r in reversed(results)]
    finally:
        db.close()
