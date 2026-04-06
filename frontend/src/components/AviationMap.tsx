'use client';

import React, { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import 'leaflet-rotatedmarker';

// Standardized Aircraft State (Part 1.1 + Part 4)
interface AircraftState {
  hex: string;
  callsign: string;
  latitude: number;
  longitude: number;
  altitude_ft: number;
  speed_kt: number;
  heading_deg: number;
  last_contact: number;
  threat_score: number;
  anomaly_reasons: string[];
}

const AircraftMarkersLayer: React.FC<{ 
    aircraft: Record<string, AircraftState> 
    onSelect: (hex: string) => void
}> = ({ aircraft, onSelect }) => {
  const map = useMap();
  const markersRef = useRef<Record<string, L.Marker>>({});

  useEffect(() => {
    const currentHexes = new Set(Object.keys(aircraft));
    
    // 1. Cleanup removed aircraft
    Object.keys(markersRef.current).forEach(hex => {
      if (!currentHexes.has(hex)) {
        markersRef.current[hex].remove();
        delete markersRef.current[hex];
      }
    });

    // 2. Part 4: Update aircraft positions from socket stream
    Object.values(aircraft).forEach(ac => {
      const position: L.LatLngExpression = [ac.latitude, ac.longitude];

      if (markersRef.current[ac.hex]) {
        const marker = markersRef.current[ac.hex];
        marker.setLatLng(position);
        
        // Part 4: Rotate aircraft icon using heading_deg
        (marker as any).setRotationAngle(ac.heading_deg || 0);
        
        if (marker.isPopupOpen()) {
           marker.getPopup()?.setContent(createPopupHTML(ac));
        }
      } else {
        const marker = L.marker(position, {
          icon: getAircraftIcon(ac.threat_score, ac.hex),
          rotationAngle: ac.heading_deg || 0,
          rotationOrigin: 'center center'
        } as any);

        marker.bindPopup(createPopupHTML(ac), { minWidth: 220 });
        
        // Part 4: Draw trail using /aircraft/flights/{icao} (Triggered on Click)
        marker.on('click', () => { onSelect(ac.hex); });

        marker.addTo(map);
        markersRef.current[ac.hex] = marker;
      }
    });
  }, [aircraft, map, onSelect]);

  return null;
};

// --- Helper Functions ---

const getAircraftIcon = (threatScore: number, hex: string) => {
    let color = '#38bdf8'; 
    if (threatScore > 30) color = '#facc15'; 
    if (threatScore > 60) color = '#ef4444'; 
  
    return L.divIcon({
      html: `
        <div style="color: ${color}; filter: drop-shadow(0 0 3px rgba(0,0,0,0.8));">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-4.5l8 2.5z"/>
          </svg>
        </div>`,
      className: 'aircraft-icon',
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
};

const createPopupHTML = (ac: AircraftState) => {
    const lastSeen = new Date(ac.last_contact * 1000).toLocaleTimeString();
    return `
        <div style="font-family: 'Inter', sans-serif; padding: 10px; color: #f8fafc;">
            <div style="border-bottom: 1px solid #475569; padding-bottom: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: baseline;">
                <b style="font-size: 16px; color: #38bdf8;">${ac.callsign || 'N/A'}</b>
                <span style="font-size: 11px; color: #94a3b8;">${ac.hex.toUpperCase()}</span>
            </div>
            <div style="display: grid; grid-template-columns: 90px 1fr; gap: 6px; font-size: 12px;">
                <span style="color: #94a3b8;">Altitude:</span> <b>${ac.altitude_ft?.toLocaleString()} ft</b>
                <span style="color: #94a3b8;">Speed:</span> <b>${ac.speed_kt?.toLocaleString()} kt</b>
                <span style="color: #94a3b8;">Heading:</span> <b>${ac.heading_deg?.toFixed(1)}°</b>
                <span style="color: #94a3b8;">Updated:</span> <b>${lastSeen}</b>
                <span style="color: #94a3b8;">Risk Level:</span> <b style="color: ${ac.threat_score > 30 ? '#facc15' : '#22c55e'}">${Math.round(ac.threat_score)}%</b>
            </div>
        </div>
    `;
};

interface AviationMapProps {
    onSelect: (hex: string) => void;
    selectedHex?: string | null;
}

const AviationMap: React.FC<AviationMapProps> = ({ onSelect, selectedHex }) => {
  const [aircraft, setAircraft] = useState<Record<string, AircraftState>>({});
  const [trail, setTrail] = useState<[number, number][]>([]);

  useEffect(() => {
    // 1. Snapshot fetch from legacy/alias route
    fetch('http://localhost:8000/aircraft/live/all')
      .then(res => res.json())
      .then(data => {
        const initialMap = data.reduce((acc: any, ac: any) => ({ ...acc, [ac.hex]: ac }), {});
        setAircraft(initialMap);
      })
      .catch(err => console.error("Initial load err", err));

    // 2. Real-time movement from WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/aircraft/live');
    ws.onmessage = (event) => {
      try {
        const updates: AircraftState[] = JSON.parse(event.data);
        setAircraft(prev => {
          const next = { ...prev };
          updates.forEach(ac => { next[ac.hex] = ac; });
          return next;
        });
      } catch (e) {
        console.error("WS Parse err", e);
      }
    };

    return () => ws.close();
  }, []);

  // Sync Trail when selectedHex changes (from page props)
  useEffect(() => {
    if (!selectedHex) {
        setTrail([]);
        return;
    }
    fetch(`http://localhost:8000/aircraft/flights/${selectedHex}`)
      .then(res => res.json())
      .then(data => {
          if (data.path) {
              setTrail(data.path.map((p: any) => [p.lat, p.lon]));
          }
      })
      .catch(err => console.error("Trail fetch err", err));
  }, [selectedHex]);

  return (
    <div className="w-full h-full relative" id="tracking-canvas-container">
      {/* 1. Leaflet Canvas Only */}
      <MapContainer 
        center={[20, 0]} 
        zoom={3} 
        className="w-full h-full bg-[#0a0f1e] transition-all"
        scrollWheelZoom={true}
      >
        <TileLayer 
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        <AircraftMarkersLayer aircraft={aircraft} onSelect={onSelect} />
        
        {/* Draw flight trail */}
        {selectedHex && trail.length > 0 && (
            <Polyline 
                positions={trail} 
                pathOptions={{ color: '#38bdf8', weight: 2, dashArray: '5, 5', opacity: 0.7 }} 
            />
        )}
      </MapContainer>

      <style jsx global>{`
        .leaflet-popup-content-wrapper {
          background-color: #111827 !important;
          color: #f1f5f9 !important;
          border-radius: 8px !important;
          border: 1px solid #374151 !important;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4) !important;
        }
        .leaflet-popup-tip {
          background-color: #111827 !important;
        }
      `}</style>
    </div>
  );
};

export default AviationMap;
